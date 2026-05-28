#!/usr/bin/env python3
"""Knowledge freshness tracking — detect, mark, and manage expired/superseded entries.

Usage:
    kb-freshness.py --list-stale              # List entries with decayed confidence
    kb-freshness.py --list-expired            # List entries past their expiry date
    kb-freshness.py --list-superseded         # List entries marked as superseded
    kb-freshness.py --list-deprecated         # List entries marked as deprecated
    kb-freshness.py --check <file>            # Freshness assessment for one entry
    kb-freshness.py --mark-superseded <file> --by <ref>   # Mark superseded
    kb-freshness.py --mark-expired <file>     # Mark as expired
    kb-freshness.py --mark-deprecated <file>  # Mark as deprecated
    kb-freshness.py --reactivate <file>       # Reactivate (set status back to active)
    kb-freshness.py --all                     # Show all entries with freshness status
"""

import argparse
import json
import os
import re
import sys
from datetime import date, datetime

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
_DEFAULT_KB_DIR = os.path.join(_PROJECT_ROOT, "_context", "memory", "sw-shared", "knowledge-base")

VALID_TYPES = {"pattern", "decision", "lesson", "api"}
TYPE_DIR_MAP = {
    "pattern": "patterns",
    "decision": "decisions",
    "lesson": "lessons",
    "api": "contracts",
}
VALID_STATUSES = {"active", "deprecated", "superseded", "expired"}
SKIP_FILES = {"index.md"}
SKIP_PREFIXES = (".", "_")

# Confidence decay rates (days per -1 confidence point)
DEFAULT_DECAY_RATES = {
    "observed": 60,        # -1 per 60 days
    "inferred": 30,        # -1 per 30 days
    "cross-model": 30,     # -1 per 30 days
    "user-stated": 0,      # no decay
}


def discover_kb_dir():
    if os.path.isdir(_DEFAULT_KB_DIR):
        return _DEFAULT_KB_DIR
    return None


def load_config(kb_dir):
    """Load freshness config from config.yaml if available."""
    config_path = os.path.join(os.path.dirname(kb_dir), "..", "..", "config.yaml")
    decay_rates = dict(DEFAULT_DECAY_RATES)
    stale_threshold = 90
    auto_expire_days = 365

    if os.path.exists(config_path):
        try:
            import yaml
            with open(config_path, encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            kb_cfg = cfg.get("kb", {}).get("freshness", {})
            if "confidence_decay" in kb_cfg:
                for src, rate in kb_cfg["confidence_decay"].items():
                    src_key = src.replace("_", "-") if "_" in src else src
                    decay_rates[src_key] = rate
            stale_threshold = kb_cfg.get("stale_threshold_days", stale_threshold)
            auto_expire_days = kb_cfg.get("auto_expire_days", auto_expire_days)
        except Exception:
            pass  # YAML not available or parse error, use defaults

    return decay_rates, stale_threshold, auto_expire_days


def extract_metadata(content):
    """Extract all freshness-relevant metadata from entry content.

    Returns dict with: title, type, created, author, source, confidence,
    status, supersedes, superseded_by, expires.
    """
    meta = {
        "title": "Untitled",
        "type": "unknown",
        "created": None,
        "created_date": None,
        "author": "unknown",
        "source": None,
        "confidence": None,
        "status": None,
        "supersedes": None,
        "superseded_by": None,
        "expires": None,
        "expires_date": None,
    }

    # Title
    m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if m:
        meta["title"] = m.group(1).strip()

    # Type
    m = re.search(r'\*\*Type:\*\*\s*(\w+)', content)
    if m:
        t = m.group(1).lower()
        if t in VALID_TYPES:
            meta["type"] = t

    # Created date
    for pat in [r'\*\*(?:Created|日期):\*\*\s*`?(\d{4}-\d{2}-\d{2})`?',
                r'\*\*Created:\*\*\s*(\d{4}-\d{2}-\d{2})']:
        m = re.search(pat, content)
        if m:
            meta["created"] = m.group(1)
            try:
                meta["created_date"] = datetime.strptime(m.group(1), "%Y-%m-%d").date()
            except ValueError:
                pass
            break

    # Author
    for pat in [r'\*\*(?:Author|决策者):\*\*\s*`?([^`\n]+?)`?\s*$',
                r'\*\*Author:\*\*\s*(\S+)']:
        m = re.search(pat, content, re.MULTILINE)
        if m:
            meta["author"] = m.group(1).strip()
            break

    # Source
    m = re.search(r'\*\*Source:\*\*\s*(\S+)', content)
    if m:
        meta["source"] = m.group(1)

    # Confidence
    m = re.search(r'\*\*Confidence:\*\*\s*(\d+)/10', content)
    if m:
        meta["confidence"] = int(m.group(1))

    # Status (both Chinese and English)
    m = re.search(r'\*\*(?:Status|状态):\*\*\s*`?(\w+)`?', content)
    if m:
        meta["status"] = m.group(1).lower()

    # Supersedes
    m = re.search(r'\*\*(?:Supersedes|替代):\*\*\s*`?([^`\n]+?)`?', content)
    if m:
        meta["supersedes"] = m.group(1).strip()

    # Superseded-By
    m = re.search(r'\*\*(?:Superseded-By|被替代):\*\*\s*`?([^`\n]+?)`?', content)
    if m:
        meta["superseded_by"] = m.group(1).strip()

    # Expires
    m = re.search(r'\*\*Expires:\*\*\s*`?(\d{4}-\d{2}-\d{2})`?', content)
    if m:
        meta["expires"] = m.group(1)
        try:
            meta["expires_date"] = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            pass

    return meta


def compute_effective_confidence(source, confidence, created_date, today, decay_rates):
    """Compute confidence after applying time-based decay.

    Returns (effective_confidence: int, decay_points: int, decay_details: str).
    """
    if confidence is None or created_date is None or source is None:
        return confidence, 0, "insufficient metadata for decay calculation"

    rate = decay_rates.get(source, 0)
    if rate <= 0:
        return confidence, 0, f"source '{source}' has no decay"

    days_elapsed = (today - created_date).days
    if days_elapsed <= 0:
        return confidence, 0, "entry created today"

    decay_points = days_elapsed // rate
    effective = max(1, confidence - decay_points)

    if decay_points > 0:
        detail = f"{days_elapsed}d elapsed, rate={rate}d/point, -{decay_points} confidence"
    else:
        detail = f"{days_elapsed}d elapsed, no decay yet (threshold {rate}d)"

    return effective, decay_points, detail


def scan_entries(kb_dir):
    """Scan all entries and return freshness data."""
    entries = []

    scope_roots = []
    ep = os.path.join(kb_dir, "_enterprise")
    if os.path.isdir(ep):
        scope_roots.append(("enterprise", ep))

    dp = os.path.join(kb_dir, "domains")
    if os.path.isdir(dp):
        for d in sorted(os.listdir(dp)):
            d_path = os.path.join(dp, d)
            if os.path.isdir(d_path) and not d.startswith("."):
                scope_roots.append(("domain", d_path))

    sp = os.path.join(kb_dir, "services")
    if os.path.isdir(sp):
        for s in sorted(os.listdir(sp)):
            s_path = os.path.join(sp, s)
            if os.path.isdir(s_path) and not s.startswith("."):
                scope_roots.append(("service", s_path))

    for scope_type, base_dir in scope_roots:
        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for fname in sorted(files):
                if fname in SKIP_FILES or fname.startswith(SKIP_PREFIXES):
                    continue
                if not fname.endswith(".md"):
                    continue

                filepath = os.path.join(root, fname)
                try:
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read()
                except (OSError, UnicodeDecodeError):
                    continue

                meta = extract_metadata(content)
                meta["filename"] = fname
                meta["filepath"] = filepath
                meta["relative_path"] = os.path.relpath(filepath, kb_dir)
                meta["scope"] = scope_type

                entries.append(meta)

    return entries


def compute_freshness(entries, today, decay_rates, stale_threshold, auto_expire_days):
    """Compute freshness assessment for all entries.

    Returns list of freshness records with: is_stale, is_expired, is_superseded,
    is_deprecated, effective_confidence, decay_detail, recommendation.
    """
    results = []
    for e in entries:
        rec = dict(e)
        rec["is_superseded"] = e.get("status") == "superseded"
        rec["is_deprecated"] = e.get("status") == "deprecated"
        rec["is_explicitly_expired"] = e.get("status") == "expired"

        # Check explicit expiry date
        rec["is_past_expiry"] = False
        if e["expires_date"] and today >= e["expires_date"]:
            rec["is_past_expiry"] = True

        # Compute effective confidence with decay
        eff_conf, decay_pts, decay_detail = compute_effective_confidence(
            e.get("source"), e.get("confidence"), e.get("created_date"), today, decay_rates
        )
        rec["effective_confidence"] = eff_conf
        rec["decay_points"] = decay_pts
        rec["decay_detail"] = decay_detail

        # Staleness detection
        rec["is_stale"] = False
        stale_reason = []

        if e["created_date"] is not None:
            age_days = (today - e["created_date"]).days
            rec["age_days"] = age_days

            if eff_conf is not None and eff_conf <= 5 and age_days > stale_threshold:
                rec["is_stale"] = True
                stale_reason.append(f"confidence decayed to {eff_conf} (was {e.get('confidence')}), "
                                   f"age={age_days}d > threshold={stale_threshold}d")

            if age_days > auto_expire_days:
                stale_reason.append(f"age={age_days}d > auto-expire threshold={auto_expire_days}d")
        else:
            rec["age_days"] = None
            if e.get("confidence") is None:
                rec["is_stale"] = True
                stale_reason.append("no creation date and no confidence metadata")

        rec["stale_reason"] = "; ".join(stale_reason) if stale_reason else None

        # Overall status
        if rec["is_superseded"]:
            rec["freshness_status"] = "superseded"
        elif rec["is_explicitly_expired"] or rec["is_past_expiry"]:
            rec["freshness_status"] = "expired"
        elif rec["is_deprecated"]:
            rec["freshness_status"] = "deprecated"
        elif rec["is_stale"]:
            rec["freshness_status"] = "stale"
        else:
            rec["freshness_status"] = "fresh"

        # Recommendation
        if rec["is_superseded"]:
            by = e.get("superseded_by", "unknown")
            rec["recommendation"] = f"Remove or archive. Superseded by: {by}"
        elif rec["is_explicitly_expired"]:
            rec["recommendation"] = "Remove or archive. Explicitly marked as expired."
        elif rec["is_past_expiry"]:
            rec["recommendation"] = f"Remove or archive. Expiry date {e.get('expires')} has passed."
        elif rec["is_deprecated"]:
            rec["recommendation"] = "Review and either update or remove. Marked as deprecated."
        elif rec["is_stale"]:
            rec["recommendation"] = "Review for accuracy. Confidence has decayed due to age."
        else:
            rec["recommendation"] = None

        results.append(rec)

    return results


def update_entry_status_file(filepath, new_status, superseded_by=None):
    """Modify an entry's status field in its markdown file.

    Returns (success: bool, message: str).
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except OSError as e:
        return False, f"Cannot read file: {e}"

    lines = content.split("\n")
    new_lines = []
    status_updated = False
    backlink_added = False
    in_frontmatter = True

    # Regex for both Chinese and English status fields
    status_pattern = re.compile(r'\*\*(?:状态|Status):\*\*\s*`?(\w+)`?')

    for i, line in enumerate(lines):
        m = status_pattern.match(line.strip())
        if m:
            key = "**状态:**" if "状态" in line else "**Status:**"
            new_lines.append(f"{key} `{new_status}`")
            status_updated = True
            # Check if we need to add a backlink right after
            if superseded_by and not backlink_added:
                next_is_superseded_by = False
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if "Superseded-By" in next_line or "被替代" in next_line:
                        next_is_superseded_by = True
                if not next_is_superseded_by:
                    new_lines.append(f"**Superseded-By:** `{superseded_by}`")
                    backlink_added = True
        elif line.strip().startswith("**Superseded-By:**") or line.strip().startswith("**被替代:**"):
            if superseded_by:
                new_lines.append(f"**Superseded-By:** `{superseded_by}`")
                backlink_added = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

        if line.startswith("## "):
            in_frontmatter = False

    if not status_updated:
        return False, "No status field found in entry. Entry may not have been created by kb-log.py."

    if superseded_by and not backlink_added:
        return False, "Status updated but could not add backlink."

    new_content = "\n".join(new_lines)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
    except OSError as e:
        return False, f"Cannot write updated entry: {e}"

    return True, f"Status updated to '{new_status}'"


def format_table(results, columns, col_headers):
    """Format results as a terminal table."""
    if not results:
        return "No results."

    # Compute column widths
    widths = [len(h) for h in col_headers]
    for r in results:
        for i, col in enumerate(columns):
            val = str(r.get(col, "")) if col in r else ""
            widths[i] = max(widths[i], min(len(val), 60))

    # Header
    header = "  ".join(h.ljust(w) for h, w in zip(col_headers, widths))
    sep = "  ".join("-" * w for w in widths)
    lines = [header, sep]

    for r in results:
        row = []
        for i, col in enumerate(columns):
            val = str(r.get(col, "")) if col in r else ""
            if len(val) > 60:
                val = val[:57] + "..."
            row.append(val.ljust(widths[i]))
        lines.append("  ".join(row))

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Knowledge freshness tracking — detect and manage expired/superseded entries.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kb-freshness.py --list-stale           List all stale entries
  kb-freshness.py --list-expired         List past-expiry entries
  kb-freshness.py --list-superseded      List superseded entries
  kb-freshness.py --all                  Show all entries with freshness
  kb-freshness.py --check patterns/old-pattern.md
  kb-freshness.py --mark-superseded patterns/old.md --by patterns/new.md
  kb-freshness.py --mark-expired lessons/done.md
  kb-freshness.py --reactivate patterns/still-valid.md
        """,
    )
    parser.add_argument("--list-stale", action="store_true",
                        help="List entries with decayed confidence")
    parser.add_argument("--list-expired", action="store_true",
                        help="List entries past their explicit expiry date")
    parser.add_argument("--list-superseded", action="store_true",
                        help="List entries marked as superseded")
    parser.add_argument("--list-deprecated", action="store_true",
                        help="List entries marked as deprecated")
    parser.add_argument("--all", action="store_true",
                        help="Show all entries with freshness status")
    parser.add_argument("--check", help="Freshness assessment for a specific entry (by relative path or filename)")
    parser.add_argument("--mark-superseded", help="Mark an entry as superseded (by relative path or filename)")
    parser.add_argument("--mark-expired", help="Mark an entry as expired (by relative path or filename)")
    parser.add_argument("--mark-deprecated", help="Mark an entry as deprecated (by relative path or filename)")
    parser.add_argument("--reactivate", help="Reactivate an entry (set status back to active)")
    parser.add_argument("--by", help="Reference to the entry that supersedes this one (used with --mark-superseded)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--kb-dir", help="Override knowledge base directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    kb_dir = args.kb_dir or discover_kb_dir()
    if not kb_dir or not os.path.isdir(kb_dir):
        print("Error: Knowledge base directory not found.", file=sys.stderr)
        sys.exit(1)

    decay_rates, stale_threshold, auto_expire_days = load_config(kb_dir)
    today = date.today()

    # --mark-* operations (single-entry mutations)
    mutation_ops = [
        ("--mark-superseded", args.mark_superseded, "superseded"),
        ("--mark-expired", args.mark_expired, "expired"),
        ("--mark-deprecated", args.mark_deprecated, "deprecated"),
        ("--reactivate", args.reactivate, "active"),
    ]

    for flag, target, new_status in mutation_ops:
        if target is None:
            continue

        # Resolve target to filepath
        target_path = None
        if os.path.exists(target):
            target_path = target
        elif os.path.exists(os.path.join(kb_dir, target)):
            target_path = os.path.join(kb_dir, target)
        else:
            # Search by filename
            for root, dirs, files in os.walk(kb_dir):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                if target in files:
                    target_path = os.path.join(root, target)
                    break

        if target_path is None:
            print(f"Error: Target entry not found: {target}", file=sys.stderr)
            sys.exit(1)

        superseded_by = args.by if flag == "--mark-superseded" and args.by else None
        ok, msg = update_entry_status_file(target_path, new_status, superseded_by)
        if ok:
            rel = os.path.relpath(target_path, kb_dir)
            if superseded_by:
                print(f"Marked '{rel}' as superseded (by: {superseded_by})")
            else:
                print(f"Marked '{rel}' as {new_status}")
        else:
            print(f"Error: {msg}", file=sys.stderr)
            sys.exit(1)
        return

    # --check single entry
    if args.check:
        target = args.check
        target_path = None
        if os.path.exists(target):
            target_path = target
        elif os.path.exists(os.path.join(kb_dir, target)):
            target_path = os.path.join(kb_dir, target)
        else:
            for root, dirs, files in os.walk(kb_dir):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                if target in files:
                    target_path = os.path.join(root, target)
                    break

        if target_path is None:
            print(f"Error: Entry not found: {target}", file=sys.stderr)
            sys.exit(1)

        try:
            with open(target_path, encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            print(f"Error: Cannot read file: {e}", file=sys.stderr)
            sys.exit(1)

        meta = extract_metadata(content)
        meta["filepath"] = target_path
        meta["relative_path"] = os.path.relpath(target_path, kb_dir)

        eff_conf, decay_pts, decay_detail = compute_effective_confidence(
            meta.get("source"), meta.get("confidence"), meta.get("created_date"), today, decay_rates
        )

        print(f"Freshness Assessment: {meta['relative_path']}")
        print("─" * 50)
        print(f"Title:       {meta['title']}")
        print(f"Type:        {meta['type']}")
        print(f"Status:      {meta.get('status', 'active')}")
        print(f"Created:     {meta.get('created', 'unknown')}")
        print(f"Author:      {meta.get('author', 'unknown')}")
        print(f"Source:      {meta.get('source', 'unknown')}")
        print(f"Confidence:  {meta.get('confidence', '?')}/10 (stored)")
        if meta.get("confidence") is not None and meta.get("created_date"):
            print(f"             {eff_conf}/10 (effective, after {decay_pts} point(s) decay)")
            print(f"Decay:       {decay_detail}")
        if meta.get("supersedes"):
            print(f"Supersedes:  {meta['supersedes']}")
        if meta.get("superseded_by"):
            print(f"Superseded-By: {meta['superseded_by']}")
        if meta.get("expires"):
            days_left = (meta["expires_date"] - today).days if meta["expires_date"] else "?"
            print(f"Expires:     {meta['expires']} ({days_left} days remaining)")
        if meta.get("created_date"):
            age = (today - meta["created_date"]).days
            print(f"Age:         {age} days")

        # Assessment
        print(f"\nAssessment:")
        if meta.get("status") == "superseded":
            print(f"  SUPERSEDED — This entry has been replaced.")
            print(f"  Recommendation: {meta.get('superseded_by', 'unknown')}")
        elif meta.get("status") == "expired":
            print(f"  EXPIRED — This entry is explicitly marked as expired.")
        elif meta.get("status") == "deprecated":
            print(f"  DEPRECATED — This entry is no longer recommended for use.")
        elif meta.get("expires_date") and today >= meta["expires_date"]:
            print(f"  EXPIRED — Expiry date {meta['expires']} has passed.")
        elif decay_pts > 0:
            print(f"  Confidence decay: {decay_pts} point(s) lost due to age.")
            if eff_conf <= 5:
                print(f"  STALE — Effective confidence {eff_conf}/10 is low. Recommend review or update.")
            else:
                print(f"  STILL FRESH — Effective confidence {eff_conf}/10 is acceptable.")
        else:
            print(f"  FRESH — No issues detected.")
        return

    # Scan all entries
    entries = scan_entries(kb_dir)
    results = compute_freshness(entries, today, decay_rates, stale_threshold, auto_expire_days)

    # Filter based on mode
    mode = "all"
    filter_func = None
    if args.list_stale:
        mode = "stale"
        filter_func = lambda r: r["is_stale"] and not r["is_superseded"] and not r["is_explicitly_expired"]
    elif args.list_expired:
        mode = "expired"
        filter_func = lambda r: r["is_explicitly_expired"] or r["is_past_expiry"]
    elif args.list_superseded:
        mode = "superseded"
        filter_func = lambda r: r["is_superseded"]
    elif args.list_deprecated:
        mode = "deprecated"
        filter_func = lambda r: r["is_deprecated"]

    if filter_func:
        results = [r for r in results if filter_func(r)]

    # JSON output
    if args.json:
        output = {
            "generated_at": datetime.now().isoformat(),
            "mode": mode,
            "total": len(results),
            "config": {
                "decay_rates": decay_rates,
                "stale_threshold_days": stale_threshold,
                "auto_expire_days": auto_expire_days,
            },
            "results": [],
        }
        for r in results:
            output["results"].append({
                "title": r["title"],
                "filename": r["filename"],
                "relative_path": r["relative_path"],
                "type": r["type"],
                "scope": r["scope"],
                "status": r.get("status", "active"),
                "freshness_status": r["freshness_status"],
                "created": r.get("created"),
                "age_days": r.get("age_days"),
                "source": r.get("source"),
                "confidence_stored": r.get("confidence"),
                "confidence_effective": r.get("effective_confidence"),
                "decay_points": r.get("decay_points"),
                "decay_detail": r.get("decay_detail"),
                "supersedes": r.get("supersedes"),
                "superseded_by": r.get("superseded_by"),
                "expires": r.get("expires"),
                "recommendation": r.get("recommendation"),
            })
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    # Human-readable output
    status_labels = {
        "stale": "Stale (Confidence Decayed)",
        "expired": "Expired",
        "superseded": "Superseded",
        "deprecated": "Deprecated",
        "all": "All Entries",
    }

    title = status_labels.get(mode, "All Entries")
    print(f"=== Knowledge Freshness: {title} ===")
    print(f"Total: {len(results)} entries")
    if args.verbose:
        print(f"Decay rates: {decay_rates}")
        print(f"Stale threshold: {stale_threshold}d, Auto-expire: {auto_expire_days}d")
    print()

    if not results:
        print("No entries found.")
        return

    columns = ["freshness_status", "title", "age_days", "effective_confidence", "status", "recommendation"]
    col_headers = ["Freshness", "Title", "Age(d)", "EffConf", "Status", "Recommendation"]

    # Simplify for display
    display_results = []
    for r in results:
        d = dict(r)
        eff = f"{d.get('effective_confidence', '?')}"
        if d.get("confidence") is not None:
            eff = f"{eff}"
        d["effective_confidence"] = f"{eff}/{d.get('confidence', '?')}" if d.get("confidence") else eff
        d["age_days"] = str(d.get("age_days", "?"))
        d["recommendation"] = d.get("recommendation", "") or ""
        display_results.append(d)

    print(format_table(display_results, columns, col_headers))
    print()

    # Summary
    summary = {}
    for r in results:
        fs = r["freshness_status"]
        summary[fs] = summary.get(fs, 0) + 1
    print("Summary by freshness status:")
    for status_name in ["fresh", "stale", "deprecated", "expired", "superseded"]:
        count = summary.get(status_name, 0)
        if count > 0:
            print(f"  {status_name}: {count}")
    total_non_fresh = sum(v for k, v in summary.items() if k != "fresh")
    if total_non_fresh > 0:
        print(f"\nTotal non-fresh entries: {total_non_fresh} — review recommended.")


if __name__ == "__main__":
    main()
