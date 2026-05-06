#!/usr/bin/env python3
"""Knowledge base health dashboard — generates a comprehensive KB health report.

Generates text, HTML, or JSON reports showing entry distribution, confidence
levels, scope coverage, staleness analysis, recent activity, and missing gaps.

Usage:
    kb-health.py                        # Print text report to stdout
    kb-health.py --html                 # Generate HTML report to stdout
    kb-health.py --html --output kb-health.html  # Save HTML report
    kb-health.py --json                 # Machine-readable JSON report
    kb-health.py --watch                # Watch mode: print summary on each run
"""

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
_DEFAULT_KB_DIR = os.path.join(_PROJECT_ROOT, "_bmad", "memory", "hw-shared", "knowledge-base")

VALID_TYPES = {"pattern", "decision", "lesson", "api", "service"}
TYPE_DIR_MAP = {
    "pattern": "patterns",
    "decision": "decisions",
    "lesson": "lessons",
    "api": "contracts",
}
SCOPE_NAMES = ["_enterprise", "domains", "services"]
SKIP_FILES = {"index.md"}
SKIP_PREFIXES = (".", "_")


def discover_kb_dir():
    """Find the knowledge base directory relative to this script."""
    if os.path.isdir(_DEFAULT_KB_DIR):
        return _DEFAULT_KB_DIR
    return None


def extract_title(content):
    """Extract title from first # heading."""
    for line in content.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled"


def extract_type(filepath, content, scope_type, base_dir):
    """Detect entry type from file path and content."""
    # Try metadata first
    m = re.search(r'\*\*Type:\*\*\s*(\w+)', content)
    if m:
        t = m.group(1).lower()
        if t in VALID_TYPES:
            return t

    # Try directory structure
    rel = os.path.relpath(filepath, base_dir)
    for type_name, dir_name in TYPE_DIR_MAP.items():
        if f"/{dir_name}/" in rel or rel.startswith(f"{dir_name}/"):
            return type_name

    # ADR naming convention
    if os.path.basename(filepath).startswith("ADR-"):
        return "decision"

    # Service-level overview/api-endpoints/db-schema files
    if scope_type == "service":
        return "service"

    return "unknown"


def extract_created(content):
    """Extract creation date from entry content."""
    patterns = [
        r'\*\*(?:Created|日期):\*\*\s*`?(\d{4}-\d{2}-\d{2})`?',
        r'\*\*Created:\*\*\s*(\d{4}-\d{2}-\d{2})',
    ]
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            return m.group(1)
    return None


def extract_author(content):
    """Extract author from metadata."""
    patterns = [
        r'\*\*(?:Author|决策者):\*\*\s*`?([^`\n]+?)`?\s*$',
        r'\*\*Author:\*\*\s*(\S+)',
    ]
    for pat in patterns:
        m = re.search(pat, content, re.MULTILINE)
        if m:
            return m.group(1).strip()
    return None


def extract_source(content):
    """Extract source metadata from entry content."""
    m = re.search(r'\*\*Source:\*\*\s*(\w+)', content)
    if m:
        return m.group(1)
    return None


def extract_confidence(content):
    """Extract confidence metadata from entry content."""
    m = re.search(r'\*\*Confidence:\*\*\s*(\d+)/10', content)
    if m:
        return int(m.group(1))
    return None


def is_trusted(source, confidence):
    """Determine if a KB entry is trusted based on source and confidence.

    Trust rules:
    - user-stated, confidence >= 7: trusted
    - user-stated, confidence < 7: not trusted (low confidence from human is a red flag)
    - observed, confidence >= 8: trusted (high-confidence observation)
    - inferred: never trusted (requires human validation)
    - cross-model: never trusted (prompt injection risk)
    """
    if source == "user-stated" and confidence is not None and confidence >= 7:
        return True
    if source == "observed" and confidence is not None and confidence >= 8:
        return True
    return False


def extract_status(content):
    """Extract status from entry content (both Chinese and English)."""
    m = re.search(r'\*\*(?:Status|状态):\*\*\s*`?(\w+)`?', content)
    if m:
        return m.group(1).lower()
    return "active"


def extract_superseded_by(content):
    """Extract Superseded-By reference from entry content."""
    m = re.search(r'\*\*(?:Superseded-By|被替代):\*\*\s*`?([^`\n]+?)`?', content)
    if m:
        return m.group(1).strip()
    return None


def extract_expires(content):
    """Extract expiry date from entry content."""
    m = re.search(r'\*\*Expires:\*\*\s*`?(\d{4}-\d{2}-\d{2})`?', content)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            pass
    return None


def compute_confidence_decay(source, confidence, created_date, today=None):
    """Compute effective confidence after time-based decay.

    Decay rates:
    - observed: -1 per 60 days
    - inferred: -1 per 30 days
    - cross-model: -1 per 30 days
    - user-stated: no decay

    Returns (effective_confidence: int, decay_points: int).
    """
    if today is None:
        today = date.today()
    if confidence is None or created_date is None or source is None:
        return confidence, 0

    decay_rates = {
        "observed": 60,
        "inferred": 30,
        "cross-model": 30,
        "user-stated": 0,
    }
    rate = decay_rates.get(source, 0)
    if rate <= 0:
        return confidence, 0

    days_elapsed = (today - created_date).days
    if days_elapsed <= 0:
        return confidence, 0

    decay_points = days_elapsed // rate
    return max(1, confidence - decay_points), decay_points


def scan_kb(kb_dir):
    """Full KB scan, returns structured data."""
    entries = []

    # scope roots: (scope_name, scope_label, base_path)
    scope_roots = []

    # Enterprise
    ep = os.path.join(kb_dir, "_enterprise")
    if os.path.isdir(ep):
        scope_roots.append(("enterprise", "_enterprise", ep))

    # Domains
    dp = os.path.join(kb_dir, "domains")
    if os.path.isdir(dp):
        for d in sorted(os.listdir(dp)):
            d_path = os.path.join(dp, d)
            if os.path.isdir(d_path) and not d.startswith("."):
                scope_roots.append(("domain", f"domains/{d}", d_path))

    # Services
    sp = os.path.join(kb_dir, "services")
    if os.path.isdir(sp):
        for s in sorted(os.listdir(sp)):
            s_path = os.path.join(sp, s)
            if os.path.isdir(s_path) and not s.startswith("."):
                scope_roots.append(("service", f"services/{s}", s_path))

    # Also scan flat type directories for backward compatibility
    for dir_name in TYPE_DIR_MAP.values():
        flat_path = os.path.join(kb_dir, dir_name)
        if os.path.isdir(flat_path):
            scope_roots.append(("legacy", dir_name, flat_path))

    for scope_type, scope_label, base_dir in scope_roots:
        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for fname in files:
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

                rel_path = os.path.relpath(filepath, kb_dir)
                title = extract_title(content)
                entry_type = extract_type(filepath, content, scope_type, base_dir)
                created_str = extract_created(content)
                created_date = None
                if created_str:
                    try:
                        created_date = datetime.strptime(created_str, "%Y-%m-%d").date()
                    except ValueError:
                        pass
                author = extract_author(content)
                entry_source = extract_source(content)
                entry_confidence = extract_confidence(content)
                trusted = is_trusted(entry_source, entry_confidence) if entry_source is not None and entry_confidence is not None else None
                entry_status = extract_status(content)
                superseded_by = extract_superseded_by(content)
                expires_date = extract_expires(content)

                entries.append({
                    "title": title,
                    "filename": fname,
                    "relative_path": rel_path,
                    "type": entry_type,
                    "scope": scope_type,
                    "scope_label": scope_label,
                    "created": created_str,
                    "created_date": created_date,
                    "author": author or "unknown",
                    "source": entry_source or "unknown",
                    "confidence": entry_confidence,
                    "trusted": trusted,
                    "status": entry_status,
                    "superseded_by": superseded_by,
                    "expires_date": expires_date,
                    "filepath": filepath,
                })

    return entries


def compute_stats(entries):
    """Compute aggregate statistics."""
    total = len(entries)

    # By scope
    by_scope = {}
    for e in entries:
        s = e["scope"]
        by_scope[s] = by_scope.get(s, 0) + 1

    # By type
    by_type = {}
    for e in entries:
        t = e["type"]
        by_type[t] = by_type.get(t, 0) + 1

    # By confidence bucket
    by_confidence = {}
    for e in entries:
        c = e["confidence"]
        if c is None:
            bucket = "unknown"
        elif c <= 3:
            bucket = "1-3 (low)"
        elif c <= 6:
            bucket = "4-6 (medium)"
        else:
            bucket = "7-10 (high)"
        by_confidence[bucket] = by_confidence.get(bucket, 0) + 1

    # By source
    by_source = {}
    source_order = ["observed", "user-stated", "inferred", "cross-model", "unknown"]
    for e in entries:
        s = e["source"] if e["source"] in source_order else "unknown"
        by_source[s] = by_source.get(s, 0) + 1

    # By age bucket (based on created date)
    by_age = {"<30d": 0, "30-90d": 0, ">90d": 0, "unknown": 0}
    today = date.today()
    for e in entries:
        cd = e["created_date"]
        if cd is None:
            by_age["unknown"] += 1
        else:
            delta = (today - cd).days
            if delta < 30:
                by_age["<30d"] += 1
            elif delta <= 90:
                by_age["30-90d"] += 1
            else:
                by_age[">90d"] += 1

    # Trust metrics
    trusted_count = sum(1 for e in entries if e["trusted"] is True)
    not_trusted_count = sum(1 for e in entries if e["trusted"] is False)
    unknown_trust_count = sum(1 for e in entries if e["trusted"] is None)

    # Stale: effective confidence <= 5 and created > 90 days ago
    stale_count = 0
    for e in entries:
        cd = e["created_date"]
        c = e["confidence"]
        src = e["source"]
        if cd is not None and c is not None:
            eff_conf, decay_pts = compute_confidence_decay(src, c, cd, today)
            if eff_conf is not None and eff_conf <= 5 and (today - cd).days > 90:
                stale_count += 1
        elif cd is None and c is None:
            stale_count += 1

    # Freshness status breakdown
    superseded_count = sum(1 for e in entries if e.get("status") == "superseded")
    expired_count = sum(1 for e in entries if e.get("status") == "expired")
    deprecated_count = sum(1 for e in entries if e.get("status") == "deprecated")

    # Explicitly past-expiry
    past_expiry_count = sum(
        1 for e in entries
        if e.get("expires_date") is not None and today >= e["expires_date"]
    )

    # Also count entries that recently updated/created (< 7 days)
    recent_count = sum(
        1 for e in entries
        if e["created_date"] and (today - e["created_date"]).days <= 7
    )

    return {
        "total": total,
        "by_scope": by_scope,
        "by_type": by_type,
        "by_confidence": by_confidence,
        "by_source": by_source,
        "by_age": by_age,
        "trusted_count": trusted_count,
        "not_trusted_count": not_trusted_count,
        "unknown_trust_count": unknown_trust_count,
        "stale_count": stale_count,
        "superseded_count": superseded_count,
        "expired_count": expired_count,
        "deprecated_count": deprecated_count,
        "past_expiry_count": past_expiry_count,
        "recent_count": recent_count,
        "today": today.isoformat(),
    }


def parse_transaction_log(kb_dir, limit=50):
    """Parse .kb-log.jsonl for recent activity."""
    log_path = os.path.join(kb_dir, ".kb-log.jsonl")
    if not os.path.isfile(log_path):
        return []

    transactions = []
    try:
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    transactions.append(entry)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []

    transactions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return transactions[:limit]


def detect_gaps(entries):
    """Detect empty scope x type combinations."""
    all_scopes = ["enterprise", "domain", "service"]
    all_types = sorted(VALID_TYPES)

    filled = set()
    for e in entries:
        filled.add((e["scope"], e["type"]))

    gaps = []
    for scope in all_scopes:
        for etype in all_types:
            if (scope, etype) not in filled:
                gaps.append({"scope": scope, "type": etype})

    return gaps


def _confidence_decayed(entry, today):
    """Check if an entry has likely decayed confidence due to age.

    Uses the same decay algorithm as kb-freshness.py:
    - observed: -1 per 60 days
    - inferred: -1 per 30 days
    - cross-model: -1 per 30 days
    - user-stated: no decay

    Returns True if effective confidence <= 5 and age > 90 days,
    OR if no confidence/date metadata exists.
    """
    c = entry.get("confidence")
    cd = entry.get("created_date")
    src = entry.get("source")
    if c is None or cd is None:
        return True
    eff_conf, decay_pts = compute_confidence_decay(src, c, cd, today)
    if eff_conf is not None and eff_conf <= 5 and (today - cd).days > 90:
        return True
    return False


def generate_text_report(stats, entries, log, gaps):
    """Generate terminal-friendly text report."""
    lines = []
    today = date.today()

    lines.append("=" * 64)
    lines.append("  KNOWLEDGE BASE HEALTH REPORT")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 64)
    lines.append("")

    # --- KPI Summary ---
    lines.append("  KPI Summary")
    lines.append("  " + "-" * 56)
    lines.append(f"  Total entries:     {stats['total']:>4d}")
    lines.append(f"  Enterprise scope:  {stats['by_scope'].get('enterprise', 0):>4d}")
    lines.append(f"  Domain scope:      {stats['by_scope'].get('domain', 0):>4d}")
    lines.append(f"  Service scope:     {stats['by_scope'].get('service', 0):>4d}")
    lines.append(f"  Legacy scope:      {stats['by_scope'].get('legacy', 0):>4d}")
    lines.append(f"  Trusted entries:   {stats['trusted_count']:>4d}")
    lines.append(f"  Stale (decayed):   {stats['stale_count']:>4d}")
    lines.append(f"  Superseded:        {stats['superseded_count']:>4d}")
    lines.append(f"  Expired:           {stats['expired_count']:>4d}")
    lines.append(f"  Deprecated:        {stats['deprecated_count']:>4d}")
    lines.append(f"  Past expiry date:  {stats['past_expiry_count']:>4d}")
    lines.append(f"  Recent (<7d):      {stats['recent_count']:>4d}")
    lines.append("")

    # --- Type distribution ---
    lines.append("  Distribution by Type")
    lines.append("  " + "-" * 56)
    for t in sorted(VALID_TYPES):
        count = stats["by_type"].get(t, 0)
        pct = count / stats["total"] * 100 if stats["total"] > 0 else 0
        bar = "".rjust(count, "#")
        if count > 0:
            bar = "#" * count if count <= 40 else "#" * 40 + "..."
            bar = ("#" * min(count, 40)).ljust(40)
        lines.append(f"  {t:12s} {count:>4d} ({pct:5.1f}%)  {bar[:min(count, 40)]}")
    lines.append("")

    # --- Scope distribution ---
    lines.append("  Distribution by Scope")
    lines.append("  " + "-" * 56)
    for s in ["enterprise", "domain", "service", "legacy"]:
        count = stats["by_scope"].get(s, 0)
        pct = count / stats["total"] * 100 if stats["total"] > 0 else 0
        bar = "#" * min(count, 40)
        lines.append(f"  {s:12s} {count:>4d} ({pct:5.1f}%)  {bar}")
    lines.append("")

    # --- Confidence distribution ---
    lines.append("  Confidence Distribution")
    lines.append("  " + "-" * 56)
    for bucket in ["1-3 (low)", "4-6 (medium)", "7-10 (high)", "unknown"]:
        count = stats["by_confidence"].get(bucket, 0)
        pct = count / stats["total"] * 100 if stats["total"] > 0 else 0
        bar = "#" * min(count, 40)
        lines.append(f"  {bucket:16s} {count:>4d} ({pct:5.1f}%)  {bar}")
    lines.append("")

    # --- Source breakdown ---
    lines.append("  Source Breakdown")
    lines.append("  " + "-" * 56)
    for s in ["observed", "user-stated", "inferred", "cross-model", "unknown"]:
        count = stats["by_source"].get(s, 0)
        pct = count / stats["total"] * 100 if stats["total"] > 0 else 0
        lines.append(f"  {s:14s} {count:>4d} ({pct:5.1f}%)")
    lines.append("")

    # --- Age breakdown ---
    lines.append("  Age Distribution")
    lines.append("  " + "-" * 56)
    for bucket in ["<30d", "30-90d", ">90d", "unknown"]:
        count = stats["by_age"].get(bucket, 0)
        pct = count / stats["total"] * 100 if stats["total"] > 0 else 0
        bar = "#" * min(count, 40)
        lines.append(f"  {bucket:10s} {count:>4d} ({pct:5.1f}%)  {bar}")
    lines.append("")

    # --- Trust breakdown ---
    lines.append("  Trust Assessment")
    lines.append("  " + "-" * 56)
    lines.append(f"  Trusted:              {stats['trusted_count']:>4d}")
    lines.append(f"  Not trusted:          {stats['not_trusted_count']:>4d}")
    lines.append(f"  Unknown/undetermined: {stats['unknown_trust_count']:>4d}")
    lines.append(f"  Stale (confidence decayed): {stats['stale_count']:>4d}")
    lines.append("")

    # --- Gaps ---
    if gaps:
        lines.append("  Missing Scope x Type Combinations")
        lines.append("  " + "-" * 56)
        for g in gaps:
            lines.append(f"  [MISSING] scope={g['scope']:10s} type={g['type']:10s}")
        lines.append("")

    # --- Recent activity ---
    lines.append("  Recent Activity (last {})".format(len(log)))
    lines.append("  " + "-" * 56)
    if log:
        for tx in log:
            ts = tx.get("timestamp", "?")
            action = tx.get("action", "?")
            ttype = tx.get("type", "?")
            title = tx.get("title", "?")
            author = tx.get("author", "?")
            # Truncate timestamp for readability
            short_ts = ts[:19] if len(ts) > 19 else ts
            lines.append(f"  [{short_ts}] {action:16s} {ttype:10s} \"{title}\" ({author})")
    else:
        lines.append("  (No transaction log found)")
    lines.append("")

    # --- Entry listing by scope ---
    lines.append("  Entries by Scope")
    lines.append("  " + "-" * 56)
    for scope in ["enterprise", "domain", "service", "legacy"]:
        scope_entries = [e for e in entries if e["scope"] == scope]
        if not scope_entries:
            continue
        lines.append(f"  [{scope.upper()}]")
        for e in scope_entries:
            trusted_mark = "T" if e["trusted"] is True else (" " if e["trusted"] is False else "?")
            stale_mark = "S" if _confidence_decayed(e, today) else " "
            # Status markers: P=suPerseded, E=Expired, D=Deprecated
            entry_status = e.get("status", "active")
            if entry_status == "superseded":
                status_mark = "P"  # suPerseded
            elif entry_status == "expired":
                status_mark = "E"  # Expired
            elif entry_status == "deprecated":
                status_mark = "D"  # Deprecated
            else:
                status_mark = " "
            conf = e["confidence"] if e["confidence"] is not None else "-"
            src = e["source"] if e["source"] else "-"
            created = e["created"] or "----/--/--"
            lines.append(f"    [{trusted_mark}{stale_mark}{status_mark}] {e['type']:10s} conf={str(conf):>2s} src={src:12s} "
                         f"created={created}  {e['title']}")
        lines.append("")
    lines.append("")

    lines.append("=" * 64)
    lines.append("  End of Report")
    lines.append("=" * 64)
    return "\n".join(lines)


def _html_escape(text):
    """Escape HTML special characters."""
    if text is None:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _css_bar(value, max_value, color="#4CAF50"):
    """Generate an inline CSS bar div."""
    pct = (value / max_value * 100) if max_value > 0 else 0
    return (
        f'<div class="bar-container">'
        f'<div class="bar" style="width:{pct:.1f}%;background:{color};">'
        f'</div><span class="bar-label">{value}</span></div>'
    )


def _kpi_card(label, value, color="#3b82f6", subtitle=""):
    """Generate a KPI card HTML snippet."""
    return f"""\
    <div class="kpi-card" style="border-top: 3px solid {color};">
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{_html_escape(label)}</div>
        {f'<div class="kpi-subtitle">{_html_escape(subtitle)}</div>' if subtitle else ''}
    </div>"""


def generate_html_report(stats, entries, log, gaps):
    """Generate self-contained HTML dashboard."""
    today = date.today()

    # Prepare entry grouping
    entries_by_scope = {"enterprise": [], "domain": [], "service": [], "legacy": []}
    for e in entries:
        s = e["scope"]
        if s in entries_by_scope:
            entries_by_scope[s].append(e)

    # Max values for bar charts
    max_type = max(stats["by_type"].values()) if stats["by_type"] else 1
    max_scope = max(stats["by_scope"].values()) if stats["by_scope"] else 1
    max_conf = max(stats["by_confidence"].values()) if stats["by_confidence"] else 1
    max_age = max(stats["by_age"].values()) if stats["by_age"] else 1

    # Bar colors
    type_colors = {
        "pattern": "#4CAF50",
        "decision": "#2196F3",
        "lesson": "#FF9800",
        "api": "#9C27B0",
        "service": "#607D8B",
        "unknown": "#795548",
    }
    scope_colors = {
        "enterprise": "#3b82f6",
        "domain": "#8b5cf6",
        "service": "#06b6d4",
        "legacy": "#6b7280",
    }
    conf_colors = {
        "1-3 (low)": "#ef4444",
        "4-6 (medium)": "#f59e0b",
        "7-10 (high)": "#22c55e",
        "unknown": "#6b7280",
    }
    age_colors = {
        "<30d": "#22c55e",
        "30-90d": "#f59e0b",
        ">90d": "#ef4444",
        "unknown": "#6b7280",
    }

    # KPI values
    kpi_enterprise = stats["by_scope"].get("enterprise", 0)
    kpi_service = stats["by_scope"].get("service", 0)
    kpi_domain = stats["by_scope"].get("domain", 0)

    # HTML parts
    scope_charts = ""
    for s in ["enterprise", "domain", "service", "legacy"]:
        cnt = stats["by_scope"].get(s, 0)
        if cnt > 0:
            color = scope_colors.get(s, "#3b82f6")
            scope_charts += _css_bar(cnt, max_scope, color)

    type_charts = ""
    for t in ["pattern", "decision", "lesson", "api", "service", "unknown"]:
        cnt = stats["by_type"].get(t, 0)
        if cnt > 0:
            color = type_colors.get(t, "#6b7280")
            type_charts += f'<div class="chart-row"><span class="chart-label">{t}</span>{_css_bar(cnt, max_type, color)}</div>'

    conf_charts = ""
    for bucket in ["7-10 (high)", "4-6 (medium)", "1-3 (low)", "unknown"]:
        cnt = stats["by_confidence"].get(bucket, 0)
        color = conf_colors.get(bucket, "#6b7280")
        conf_charts += f'<div class="chart-row"><span class="chart-label">{bucket}</span>{_css_bar(cnt, max_conf, color)}</div>'

    age_charts = ""
    for bucket in ["<30d", "30-90d", ">90d", "unknown"]:
        cnt = stats["by_age"].get(bucket, 0)
        color = age_colors.get(bucket, "#6b7280")
        age_charts += f'<div class="chart-row"><span class="chart-label">{bucket}</span>{_css_bar(cnt, max_age, color)}</div>'

    # Source breakdown
    source_rows = ""
    for s in ["observed", "user-stated", "inferred", "cross-model", "unknown"]:
        cnt = stats["by_source"].get(s, 0)
        pct = cnt / stats["total"] * 100 if stats["total"] > 0 else 0
        source_rows += f"""\
        <tr>
            <td>{_html_escape(s)}</td>
            <td>{cnt}</td>
            <td>{pct:.1f}%</td>
        </tr>"""

    # Transaction log timeline
    log_rows = ""
    for tx in log:
        ts = tx.get("timestamp", "?")
        action = tx.get("action", "?")
        ttype = tx.get("type", "?")
        title = tx.get("title", "?")
        author = tx.get("author", "?")
        short_ts = ts[:19] if len(ts) > 19 else ts

        action_color = {
            "create": "#22c55e",
            "merge": "#3b82f6",
            "skipped-dedup": "#f59e0b",
            "delete": "#ef4444",
        }.get(action, "#6b7280")

        log_rows += f"""\
        <tr>
            <td class="log-ts">{_html_escape(short_ts)}</td>
            <td><span class="action-badge" style="background:{action_color};">{_html_escape(action)}</span></td>
            <td>{_html_escape(ttype)}</td>
            <td>{_html_escape(title)}</td>
            <td class="log-author">{_html_escape(author)}</td>
        </tr>"""

    # Missing matrix
    all_scopes = ["enterprise", "domain", "service"]
    all_types = sorted(VALID_TYPES)

    # Build a lookup
    filled = set()
    for e in entries:
        filled.add((e["scope"], e["type"]))

    matrix_cells = ""
    for etype in all_types:
        matrix_cells += f'<tr><td class="matrix-type">{etype}</td>'
        for scope in all_scopes:
            present = (scope, etype) in filled
            count = sum(1 for e in entries if e["scope"] == scope and e["type"] == etype)
            if present:
                matrix_cells += f'<td class="matrix-present" title="{count} entries">{count}</td>'
            else:
                matrix_cells += '<td class="matrix-missing" title="Missing">0</td>'
        matrix_cells += "</tr>\n"

    # Entry listing by scope
    entries_html = ""
    for scope in ["enterprise", "domain", "service", "legacy"]:
        scope_entries = entries_by_scope.get(scope, [])
        if not scope_entries:
            continue

        # Sort: by type, then by title
        scope_entries.sort(key=lambda e: (e["type"], e["title"].lower()))

        rows = ""
        for e in scope_entries:
            stale = _confidence_decayed(e, today)
            trust_icon = "&#10003;" if e["trusted"] is True else ("&#10007;" if e["trusted"] is False else "&#9872;")
            trust_class = "trust-yes" if e["trusted"] is True else ("trust-no" if e["trusted"] is False else "trust-unk")
            stale_class = "stale-yes" if stale else ""
            conf = str(e["confidence"]) if e["confidence"] is not None else "?"
            src = e["source"] if e["source"] else "?"
            created = e["created"] or "?"
            # Status marker
            entry_status = e.get("status", "active")
            if entry_status == "superseded":
                status_mark = "P"
                status_class = "status-superseded"
            elif entry_status == "expired":
                status_mark = "E"
                status_class = "status-expired"
            elif entry_status == "deprecated":
                status_mark = "D"
                status_class = "status-deprecated"
            else:
                status_mark = "-"
                status_class = ""
            rows += f"""\
            <tr class="{stale_class}">
                <td><span class="trust-badge {trust_class}">{trust_icon}</span></td>
                <td><span class="stale-badge">{'S' if stale else '-'}</span></td>
                <td><span class="status-badge {status_class}">{status_mark}</span></td>
                <td>{_html_escape(e['type'])}</td>
                <td class="entry-title-cell">{_html_escape(e['title'])}</td>
                <td>{conf}</td>
                <td>{_html_escape(src)}</td>
                <td>{_html_escape(created)}</td>
                <td class="entry-path">{_html_escape(e['relative_path'])}</td>
            </tr>"""

        scope_label = scope.upper()
        if scope == "enterprise":
            scope_label = "ENTERPRISE"
        elif scope == "domain":
            scope_label = "DOMAIN"
        elif scope == "service":
            scope_label = "SERVICE"
        elif scope == "legacy":
            scope_label = "LEGACY (flat)"

        entries_html += f"""\
        <div class="scope-section">
            <h2>{scope_label} <span class="scope-count">({len(scope_entries)} entries)</span></h2>
            <table class="entry-table">
                <thead>
                    <tr>
                        <th>T</th>
                        <th>S</th>
                        <th>St</th>
                        <th>Type</th>
                        <th>Title</th>
                        <th>Conf</th>
                        <th>Source</th>
                        <th>Created</th>
                        <th>Path</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>"""

    # Build full HTML
    html = f"""<!DOCTYPE html>

<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Knowledge Base Health Dashboard</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background: #0f172a;
    color: #e2e8f0;
    padding: 24px;
    line-height: 1.5;
  }}
  .container {{ max-width: 1280px; margin: 0 auto; }}

  h1 {{
    font-size: 1.75rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 4px;
  }}
  .subtitle {{
    font-size: 0.875rem;
    color: #94a3b8;
    margin-bottom: 24px;
  }}

  /* KPI Cards */
  .kpi-row {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 16px;
    margin-bottom: 28px;
  }}
  .kpi-card {{
    background: #1e293b;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
  }}
  .kpi-value {{
    font-size: 2rem;
    font-weight: 700;
    color: #f1f5f9;
  }}
  .kpi-label {{
    font-size: 0.8rem;
    color: #94a3b8;
    margin-top: 4px;
  }}
  .kpi-subtitle {{
    font-size: 0.7rem;
    color: #64748b;
    margin-top: 2px;
  }}

  /* Chart sections */
  .chart-section {{
    background: #1e293b;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
  }}
  .chart-section h2 {{
    font-size: 1rem;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid #334155;
  }}
  .chart-row {{
    display: flex;
    align-items: center;
    margin-bottom: 8px;
  }}
  .chart-label {{
    width: 140px;
    flex-shrink: 0;
    font-size: 0.85rem;
    color: #cbd5e1;
    text-align: right;
    padding-right: 12px;
  }}
  .bar-container {{
    flex: 1;
    height: 24px;
    background: #334155;
    border-radius: 4px;
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
  }}
  .bar {{
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
    min-width: 2px;
  }}
  .bar-label {{
    position: absolute;
    right: 8px;
    font-size: 0.8rem;
    font-weight: 600;
    color: #f1f5f9;
  }}

  /* Two-column layout */
  .charts-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 20px;
  }}
  @media (max-width: 800px) {{
    .charts-grid {{ grid-template-columns: 1fr; }}
  }}

  /* Tables */
  .data-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }}
  .data-table th {{
    text-align: left;
    padding: 8px 12px;
    color: #94a3b8;
    font-weight: 600;
    border-bottom: 1px solid #334155;
    white-space: nowrap;
  }}
  .data-table td {{
    padding: 8px 12px;
    border-bottom: 1px solid #1e293b;
  }}

  /* Transaction log */
  .log-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  .log-table th {{
    text-align: left;
    padding: 8px 12px;
    color: #94a3b8;
    font-weight: 600;
    border-bottom: 1px solid #334155;
  }}
  .log-table td {{ padding: 8px 12px; border-bottom: 1px solid #1e293b; }}
  .log-ts {{ color: #64748b; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.8rem; white-space: nowrap; }}
  .log-author {{ color: #94a3b8; font-size: 0.8rem; }}
  .action-badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    color: #fff;
  }}

  /* Missing matrix */
  .matrix-table {{ border-collapse: collapse; font-size: 0.85rem; width: 100%; }}
  .matrix-table th {{
    padding: 10px 16px;
    color: #94a3b8;
    font-weight: 600;
    border-bottom: 2px solid #334155;
    text-align: center;
  }}
  .matrix-table td {{
    padding: 10px 16px;
    text-align: center;
    border: 1px solid #334155;
  }}
  .matrix-type {{ text-align: left !important; color: #cbd5e1; font-weight: 500; }}
  .matrix-present {{ background: #064e3b; color: #6ee7b7; font-weight: 600; }}
  .matrix-missing {{ background: #7f1d1d; color: #fca5a5; font-weight: 700; }}

  /* Entry table */
  .scope-section {{ margin-bottom: 28px; }}
  .scope-section h2 {{
    font-size: 1.1rem;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 12px;
  }}
  .scope-count {{ color: #64748b; font-size: 0.85rem; font-weight: 400; }}
  .entry-table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
  .entry-table th {{
    text-align: left;
    padding: 8px 10px;
    color: #94a3b8;
    font-weight: 600;
    border-bottom: 1px solid #334155;
    white-space: nowrap;
  }}
  .entry-table td {{
    padding: 6px 10px;
    border-bottom: 1px solid #1e293b;
  }}
  .entry-table tr:hover {{ background: #1e293b; }}
  .entry-title-cell {{ color: #e2e8f0; max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .entry-path {{ color: #64748b; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.75rem; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}

  .trust-badge {{ font-size: 0.8rem; }}
  .trust-yes {{ color: #22c55e; }}
  .trust-no {{ color: #ef4444; }}
  .trust-unk {{ color: #f59e0b; }}

  .stale-badge {{
    display: inline-block;
    width: 18px;
    height: 18px;
    line-height: 18px;
    text-align: center;
    border-radius: 50%;
    font-size: 0.7rem;
    font-weight: 700;
  }}
  .stale-yes .stale-badge {{ background: #ef4444; color: #fff; }}
  .stale-yes td {{ color: #fca5a5; }}
  tr.stale-yes {{ background: #2d1a1a !important; }}

  /* Source section */
  .source-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  .source-table th {{
    text-align: left; padding: 8px 12px; color: #94a3b8; font-weight: 600;
    border-bottom: 1px solid #334155;
  }}
  .source-table td {{ padding: 8px 12px; border-bottom: 1px solid #1e293b; }}

  .footer {{
    margin-top: 40px;
    text-align: center;
    font-size: 0.75rem;
    color: #475569;
    border-top: 1px solid #1e293b;
    padding-top: 16px;
  }}
</style>
</head>
<body>
<div class="container">

<h1>KB Health Dashboard</h1>
<div class="subtitle">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} &middot; Knowledge Base Health Report</div>

<!-- KPI Cards -->
<div class="kpi-row">
{_kpi_card('Total Entries', stats['total'], '#3b82f6')}
{_kpi_card('Enterprise', kpi_enterprise, '#3b82f6')}
{_kpi_card('Domain', kpi_domain, '#8b5cf6')}
{_kpi_card('Service', kpi_service, '#06b6d4')}
{_kpi_card('Trusted', stats['trusted_count'], '#22c55e', f'{stats["not_trusted_count"]} not trusted')}
{_kpi_card('Stale', stats['stale_count'], '#ef4444', 'confidence decayed')}
{_kpi_card('Superseded', stats['superseded_count'], '#ef4444', 'replaced by newer')}
{_kpi_card('Expired', stats['expired_count'], '#dc2626', f'{stats["past_expiry_count"]} past date')}
{_kpi_card('Deprecated', stats['deprecated_count'], '#f59e0b', 'not recommended')}
{_kpi_card('Recent', stats['recent_count'], '#22c55e', 'created &lt;7d ago')}
</div>

<!-- Distribution charts -->
<div class="charts-grid">
  <div class="chart-section">
    <h2>Distribution by Type</h2>
    {type_charts}
  </div>
  <div class="chart-section">
    <h2>Distribution by Scope</h2>
    {scope_charts}
  </div>
  <div class="chart-section">
    <h2>Confidence Distribution</h2>
    {conf_charts}
  </div>
  <div class="chart-section">
    <h2>Age Distribution</h2>
    {age_charts}
  </div>
</div>

<!-- Source & Trust -->
<div class="charts-grid">
  <div class="chart-section">
    <h2>Source Breakdown</h2>
    <table class="source-table">
      <thead><tr><th>Source</th><th>Count</th><th>%</th></tr></thead>
      <tbody>{source_rows}</tbody>
    </table>
  </div>
  <div class="chart-section">
    <h2>Trust Assessment</h2>
    <table class="source-table">
      <thead><tr><th>Category</th><th>Count</th></tr></thead>
      <tbody>
        <tr><td>Trusted</td><td>{stats['trusted_count']}</td></tr>
        <tr><td>Not trusted</td><td>{stats['not_trusted_count']}</td></tr>
        <tr><td>Unknown/undetermined</td><td>{stats['unknown_trust_count']}</td></tr>
        <tr><td>Stale (confidence decayed)</td><td>{stats['stale_count']}</td></tr>
      </tbody>
    </table>
  </div>
</div>

<!-- Gap Matrix -->
<div class="chart-section">
  <h2>Scope x Type Coverage Matrix</h2>
  <p style="color:#94a3b8;font-size:0.85rem;margin-bottom:12px;">
    Red cells indicate missing combinations. Numbers show entry counts.
  </p>
  <table class="matrix-table">
    <thead><tr><th>Type / Scope</th><th>enterprise</th><th>domain</th><th>service</th></tr></thead>
    <tbody>{matrix_cells}</tbody>
  </table>
</div>

<!-- Transaction Log -->
<div class="chart-section">
  <h2>Recent Activity ({len(log)} transactions)</h2>
  <table class="log-table">
    <thead><tr><th>Timestamp</th><th>Action</th><th>Type</th><th>Title</th><th>Author</th></tr></thead>
    <tbody>{log_rows if log_rows else '<tr><td colspan="5" style="text-align:center;color:#64748b;padding:20px;">No transaction log found</td></tr>'}</tbody>
  </table>
</div>

<!-- Entry Listings -->
<div class="chart-section">
  <h2>Entry Directory</h2>
  <p style="color:#94a3b8;font-size:0.85rem;margin-bottom:12px;">
    T = Trusted (&#10003;=yes, &#10007;=no, &#9872;=unknown) &middot; S = Stale &middot; St = Status (P=suPerseded, E=Expired, D=Deprecated)
  </p>
  {entries_html}
</div>

<div class="footer">
  KB Health Dashboard &middot; Generated by kb-health.py
</div>

</div>
</body>
</html>"""
    return html


def generate_json_report(stats, entries, log, gaps):
    """Generate machine-readable JSON."""
    # Serialize date objects
    def serialize(obj):
        if isinstance(obj, date):
            return obj.isoformat()
        return obj

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kb_health": stats,
        "gaps": gaps,
        "recent_activity": log[:20],
        "entries": [],
    }

    for e in entries:
        report["entries"].append({
            "title": e["title"],
            "filename": e["filename"],
            "relative_path": e["relative_path"],
            "type": e["type"],
            "scope": e["scope"],
            "created": e["created"],
            "author": e["author"],
            "source": e["source"],
            "confidence": e["confidence"],
            "trusted": e["trusted"],
        })

    return json.dumps(report, ensure_ascii=False, indent=2, default=serialize)


def main():
    parser = argparse.ArgumentParser(
        description="Knowledge base health dashboard — comprehensive KB health report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kb-health.py                              Print text report to stdout
  kb-health.py --html                       Generate HTML report to stdout
  kb-health.py --html --output kb-health.html  Save HTML report
  kb-health.py --json                       Machine-readable JSON report
  kb-health.py --watch                      Print summary on each run
        """,
    )
    parser.add_argument("--html", action="store_true", help="Generate HTML report (default: text)")
    parser.add_argument("--json", action="store_true", help="Generate JSON report")
    parser.add_argument("--output", "-o", help="Write output to file instead of stdout")
    parser.add_argument("--watch", action="store_true", help="Watch mode: print summary on each run")
    parser.add_argument("--kb-dir", help="Override knowledge base directory")
    parser.add_argument("--log-limit", type=int, default=50, help="Max log entries (default: 50)")
    args = parser.parse_args()

    kb_dir = args.kb_dir or discover_kb_dir()
    if not kb_dir or not os.path.isdir(kb_dir):
        print("Error: Knowledge base directory not found.", file=sys.stderr)
        sys.exit(1)

    # Scan KB
    entries = scan_kb(kb_dir)
    stats = compute_stats(entries)
    log = parse_transaction_log(kb_dir, limit=args.log_limit)
    gaps = detect_gaps(entries)

    # Generate report
    if args.watch:
        # Print compact summary
        total = stats["total"]
        trusted = stats["trusted_count"]
        stale = stats["stale_count"]
        recent = stats["recent_count"]
        gaps_count = len(gaps)
        line = (
            f"[KB Health] {datetime.now().strftime('%H:%M:%S')} | "
            f"total={total} trusted={trusted} stale={stale} "
            f"recent={recent} gaps={gaps_count}"
        )
        print(line)
        return

    if args.json:
        output = generate_json_report(stats, entries, log, gaps)
    elif args.html:
        output = generate_html_report(stats, entries, log, gaps)
    else:
        output = generate_text_report(stats, entries, log, gaps)

    # Output
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Report written to {args.output}", file=sys.stderr)
        except OSError as e:
            print(f"Error writing output: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(output)


if __name__ == "__main__":
    main()
