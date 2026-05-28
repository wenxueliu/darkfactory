#!/usr/bin/env python3
"""Knowledge base index maintenance — rebuild, validate, and detect orphans.

Usage:
    kb-index.py --rebuild
    kb-index.py --validate-only
    kb-index.py --detect-orphans
"""

import argparse
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
TYPE_LABEL_MAP = {
    "pattern": "Pattern",
    "decision": "Decision",
    "lesson": "Lesson",
    "api": "API",
}

SKIP_FILES = {"index.md"}
SKIP_PREFIXES = (".", "_")


def discover_kb_dir():
    """Find the knowledge base directory relative to this script."""
    if os.path.isdir(_DEFAULT_KB_DIR):
        return _DEFAULT_KB_DIR
    return None


def scan_entries(kb_dir):
    """Scan all .md files in the three-level knowledge base and extract metadata."""
    entries = []
    type_reverse_map = {v: k for k, v in TYPE_DIR_MAP.items()}

    # Determine scope roots to scan: list of (scope_type, base_path)
    scope_roots = []

    # 1. Enterprise scope: _enterprise/
    ep = os.path.join(kb_dir, "_enterprise")
    if os.path.isdir(ep):
        scope_roots.append(("enterprise", ep))

    # 2. Domain scope: domains/*/
    dp = os.path.join(kb_dir, "domains")
    if os.path.isdir(dp):
        for d in sorted(os.listdir(dp)):
            d_path = os.path.join(dp, d)
            if os.path.isdir(d_path) and not d.startswith("."):
                scope_roots.append(("domain", d_path))

    # 3. Service scope: services/*/
    sp = os.path.join(kb_dir, "services")
    if os.path.isdir(sp):
        for s in sorted(os.listdir(sp)):
            s_path = os.path.join(sp, s)
            if os.path.isdir(s_path) and not s.startswith("."):
                scope_roots.append(("service", s_path))

    # 4. Backward compat: flat type directories (e.g., patterns/, decisions/)
    for dir_name in TYPE_DIR_MAP.values():
        flat_path = os.path.join(kb_dir, dir_name)
        if os.path.isdir(flat_path):
            scope_roots.append(("legacy", flat_path))

    for scope_type, base_dir in scope_roots:
        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
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

                rel_path = os.path.relpath(filepath, kb_dir)
                title = extract_title(content)

                # Determine entry type
                if scope_type == "legacy":
                    if fname.startswith("ADR-"):
                        entry_type = "decision"
                    else:
                        rel_dir = os.path.relpath(root, kb_dir)
                        first_dir = rel_dir.split(os.sep)[0] if rel_dir != "." else ""
                        entry_type = type_reverse_map.get(first_dir, "unknown")
                else:
                    rel_from_scope = os.path.relpath(root, base_dir)
                    if rel_from_scope == ".":
                        # File directly in scope root (e.g., overview.md in service)
                        entry_type = "service"
                    else:
                        type_dir_name = rel_from_scope.split(os.sep)[0]
                        if type_dir_name in type_reverse_map:
                            entry_type = type_reverse_map[type_dir_name]
                        elif fname.startswith("ADR-"):
                            entry_type = "decision"
                        else:
                            entry_type = "service"

                created = extract_created(content)
                author = extract_author(content)

                entries.append({
                    "type": entry_type,
                    "title": title,
                    "filename": fname,
                    "relative_path": rel_path,
                    "created": created,
                    "author": author,
                    "scope": scope_type,
                })

    return entries


def extract_title(content):
    """Extract title from first # heading."""
    for line in content.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled"


def extract_created(content):
    """Extract creation date from metadata."""
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
    m = re.search(r'\*\*(?:Author|决策者):\*\*\s*`?([^`\n]+?)`?\s*$', content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def extract_confidence(content):
    """Extract confidence from entry content."""
    m = re.search(r'\*\*Confidence:\*\*\s*(\d+)/10', content)
    if m:
        return int(m.group(1))
    return None


def validate_entry(filepath):
    """Validate a single entry. Returns list of issues."""
    issues = []
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except OSError:
        return [f"Cannot read file: {filepath}"]

    rel = filepath

    # Check for title
    has_title = bool(re.search(r'^#\s+\S', content, re.MULTILINE))
    if not has_title:
        issues.append("Missing title (# heading)")

    # Check for type or decision-specific fields
    if "ADR-" in os.path.basename(filepath):
        # ADR-specific checks
        for section in ["背景", "决策", "理由"]:
            if f"## {section}" not in content:
                issues.append(f"Missing ADR section: ## {section}")
    else:
        # Generic checks
        for section in ["Summary", "Details", "Context"]:
            if f"## {section}" not in content:
                issues.append(f"Missing section: ## {section}")

    # Check created date
    created = extract_created(content)
    if not created:
        issues.append("Missing or invalid **Created:** date")
    else:
        try:
            datetime.strptime(created, "%Y-%m-%d")
        except ValueError:
            issues.append(f"Invalid date format: {created}")

    # Check author
    author = extract_author(content)
    if not author:
        issues.append("Missing **Author:** / **决策者:** field")

    # Check file ends with newline
    if content and not content.endswith("\n"):
        issues.append("File does not end with newline")

    return issues


def rebuild_index(kb_dir, entries):
    """Rebuild index.md from scanned entries, organized by scope."""
    index_path = os.path.join(kb_dir, "index.md")
    today = date.today().isoformat()

    # Read existing overview (preserve top section before first ## heading)
    overview_lines = []
    if os.path.exists(index_path):
        with open(index_path, encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("## "):
                    break
                overview_lines.append(line)

    lines = list(overview_lines)

    # Scope navigation
    lines.append("## Scope Navigation\n\n")
    has_enterprise = any(e.get("scope") == "enterprise" for e in entries)
    has_domain = any(e.get("scope") == "domain" for e in entries)
    has_service = any(e.get("scope") == "service" for e in entries)

    if has_enterprise:
        lines.append("- [Enterprise Knowledge](#enterprise-knowledge)\n")
    if has_domain:
        lines.append("- [Domain Knowledge](#domain-knowledge)\n")
    if has_service:
        lines.append("- [Service Knowledge](#service-knowledge)\n")
    lines.append("\n---\n\n")

    # Separate entries by scope
    enterprise_entries = [e for e in entries if e.get("scope") == "enterprise"]
    domain_entries = [e for e in entries if e.get("scope") == "domain"]
    service_entries = [e for e in entries if e.get("scope") == "service"]
    legacy_entries = [e for e in entries if e.get("scope") == "legacy"]

    # --- Enterprise Knowledge ---
    if enterprise_entries:
        lines.append("## Enterprise Knowledge\n\n")
        enterprise_patterns = [e for e in enterprise_entries if e["type"] == "pattern"]
        enterprise_decisions = [e for e in enterprise_entries if e["type"] == "decision"]
        enterprise_lessons = [e for e in enterprise_entries if e["type"] == "lesson"]
        enterprise_apis = [e for e in enterprise_entries if e["type"] == "api"]

        enterprise_patterns.sort(key=lambda e: e["title"].lower())
        enterprise_decisions.sort(key=lambda e: e["filename"], reverse=True)
        enterprise_lessons.sort(key=lambda e: e.get("created", "0000"), reverse=True)
        enterprise_apis.sort(key=lambda e: e["title"].lower())

        # Patterns
        lines.append("### Patterns\n\n")
        if enterprise_patterns:
            for e in enterprise_patterns:
                lines.append(f"- [{e['title']}]({e['relative_path']})\n")
        else:
            lines.append("_No patterns recorded yet._\n")
        lines.append("\n")

        # Architecture Decisions
        lines.append("### Architecture Decisions\n\n")
        if enterprise_decisions:
            for e in enterprise_decisions:
                lines.append(f"- [{e['title']}]({e['relative_path']})\n")
        else:
            lines.append("_No ADRs recorded yet._\n")
        lines.append("\n")

        # Lessons Learned
        lines.append("### Lessons Learned\n\n")
        if enterprise_lessons:
            for e in enterprise_lessons:
                lines.append(f"- [{e['title']}]({e['relative_path']})\n")
        else:
            lines.append("_No lessons recorded yet._\n")
        lines.append("\n")

        # API Contracts
        lines.append("### API Contracts\n\n")
        if enterprise_apis:
            for e in enterprise_apis:
                lines.append(f"- [{e['title']}]({e['relative_path']})\n")
        else:
            lines.append("_No API contracts recorded yet._\n")
        lines.append("\n---\n\n")

    # --- Domain Knowledge ---
    if domain_entries:
        lines.append("## Domain Knowledge\n\n")
        # Group by domain (second segment of relative_path after domains/)
        domain_groups = {}
        for e in domain_entries:
            parts = e["relative_path"].split("/")
            domain_name = parts[1] if len(parts) > 1 else "unknown"
            if domain_name not in domain_groups:
                domain_groups[domain_name] = []
            domain_groups[domain_name].append(e)

        for domain_name in sorted(domain_groups.keys()):
            dom_entries = domain_groups[domain_name]
            dom_patterns = [e for e in dom_entries if e["type"] == "pattern"]
            dom_decisions = [e for e in dom_entries if e["type"] == "decision"]
            dom_lessons = [e for e in dom_entries if e["type"] == "lesson"]

            dom_patterns.sort(key=lambda e: e["title"].lower())
            dom_decisions.sort(key=lambda e: e["filename"], reverse=True)
            dom_lessons.sort(key=lambda e: e.get("created", "0000"), reverse=True)

            lines.append(f"### {domain_name}\n\n")

            if dom_patterns:
                lines.append("**Patterns**\n\n")
                for e in dom_patterns:
                    lines.append(f"- [{e['title']}]({e['relative_path']})\n")
                lines.append("\n")

            if dom_decisions:
                lines.append("**Architecture Decisions**\n\n")
                for e in dom_decisions:
                    lines.append(f"- [{e['title']}]({e['relative_path']})\n")
                lines.append("\n")

            if dom_lessons:
                lines.append("**Lessons Learned**\n\n")
                for e in dom_lessons:
                    lines.append(f"- [{e['title']}]({e['relative_path']})\n")
                lines.append("\n")

        lines.append("---\n\n")

    # --- Service Knowledge ---
    if service_entries:
        lines.append("## Service Knowledge\n\n")
        # Group by service-id (second segment of relative_path after services/)
        svc_groups = {}
        for e in service_entries:
            parts = e["relative_path"].split("/")
            svc_id = parts[1] if len(parts) > 1 else "unknown"
            if svc_id not in svc_groups:
                svc_groups[svc_id] = []
            svc_groups[svc_id].append(e)

        for svc_id in sorted(svc_groups.keys()):
            lines.append(f"### {svc_id}\n\n")
            for e in sorted(svc_groups[svc_id], key=lambda x: x["filename"]):
                lines.append(f"- [{e['title']}]({e['relative_path']})\n")
            lines.append("\n")
    else:
        lines.append("## Service Knowledge\n\n")
        lines.append("_No service knowledge generated yet._\n")
        lines.append("\n")

    # --- Legacy entries (backward compat flat directories) ---
    if legacy_entries:
        lines.append("---\n\n")
        lines.append("## Legacy (Flat Structure)\n\n")

        legacy_patterns = [e for e in legacy_entries if e["type"] == "pattern"]
        legacy_decisions = [e for e in legacy_entries if e["type"] == "decision"]
        legacy_lessons = [e for e in legacy_entries if e["type"] == "lesson"]
        legacy_apis = [e for e in legacy_entries if e["type"] == "api"]

        legacy_patterns.sort(key=lambda e: e["title"].lower())
        legacy_decisions.sort(key=lambda e: e["filename"], reverse=True)
        legacy_lessons.sort(key=lambda e: e.get("created", "0000"), reverse=True)
        legacy_apis.sort(key=lambda e: e["title"].lower())

        if legacy_patterns:
            lines.append("### Patterns\n\n")
            for e in legacy_patterns:
                lines.append(f"- [{e['title']}]({e['relative_path']})\n")
            lines.append("\n")

        if legacy_decisions:
            lines.append("### Architecture Decisions\n\n")
            for e in legacy_decisions:
                lines.append(f"- [{e['title']}]({e['relative_path']})\n")
            lines.append("\n")

        if legacy_lessons:
            lines.append("### Lessons Learned\n\n")
            for e in legacy_lessons:
                lines.append(f"- [{e['title']}]({e['relative_path']})\n")
            lines.append("\n")

        if legacy_apis:
            lines.append("### API Contracts\n\n")
            for e in legacy_apis:
                lines.append(f"- [{e['title']}]({e['relative_path']})\n")
            lines.append("\n")

    # Update table
    lines.append("## 更新记录\n\n")
    lines.append("| 日期 | 更新内容 | 更新人 |\n")
    lines.append("|------|----------|--------|\n")
    lines.append(f"| {today} | Index rebuilt ({len(entries)} entries) | kb-index.py |\n")

    with open(index_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return True


def find_orphans(kb_dir, entries):
    """Find .md files not linked in index.md. Returns list of relative paths."""
    index_path = os.path.join(kb_dir, "index.md")
    if not os.path.exists(index_path):
        return [e["relative_path"] for e in entries]

    with open(index_path, encoding="utf-8") as f:
        index_content = f.read()

    orphans = []
    for entry in entries:
        rel = entry["relative_path"]
        fname = entry["filename"]
        if fname not in index_content and rel not in index_content:
            orphans.append(rel)

    return orphans


def main():
    parser = argparse.ArgumentParser(
        description="Rebuild or validate the knowledge base index.",
    )
    parser.add_argument("--rebuild", action="store_true", help="Rebuild index.md from scratch")
    parser.add_argument("--validate-only", action="store_true", help="Validate entries without modifying")
    parser.add_argument("--detect-orphans", action="store_true", help="Report orphan entries")
    parser.add_argument("--kb-dir", help="Override knowledge base directory")
    parser.add_argument("--check-staleness", action="store_true",
                        help="Check for stale entries (created >90 days, confidence <=5)")
    parser.add_argument("--health", action="store_true",
                        help="Print quick health summary after index operations")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    kb_dir = args.kb_dir or discover_kb_dir()
    if not kb_dir or not os.path.isdir(kb_dir):
        print("Error: Knowledge base directory not found.", file=sys.stderr)
        sys.exit(1)

    # Default: do everything
    do_rebuild = args.rebuild or (not args.validate_only and not args.detect_orphans)
    do_validate = args.validate_only or (not args.rebuild and not args.detect_orphans)
    do_orphans = args.detect_orphans or (not args.rebuild and not args.validate_only)

    entries = scan_entries(kb_dir)

    print(f"Index Report for knowledge-base/")
    print("─" * 40)

    # Count by type and scope
    counts = {}
    scope_counts = {}
    for e in entries:
        counts[e["type"]] = counts.get(e["type"], 0) + 1
        s = e.get("scope", "unknown")
        scope_counts[s] = scope_counts.get(s, 0) + 1

    print(f"Total entries: {len(entries)}")
    for t in ["pattern", "decision", "lesson", "api", "service"]:
        if t in counts:
            label = {"pattern": "Patterns", "decision": "Decisions", "lesson": "Lessons",
                     "api": "API Contracts", "service": "Service entries"}[t]
            print(f"  {label}: {counts[t]}")

    print(f"\nScope breakdown:")
    for s in ["enterprise", "domain", "service", "legacy"]:
        if s in scope_counts:
            print(f"  {s}: {scope_counts[s]}")

    # Validate
    if do_validate:
        total_issues = 0
        valid_count = 0
        stale_count = 0
        for entry in entries:
            filepath = os.path.join(kb_dir, entry["relative_path"])
            issues = validate_entry(filepath)

            # Staleness check
            if args.check_staleness and entry.get("created"):
                try:
                    created_date = datetime.strptime(entry["created"], "%Y-%m-%d").date()
                    delta = (date.today() - created_date).days
                    with open(filepath, encoding="utf-8") as f:
                        content = f.read()
                    confidence = extract_confidence(content)
                    if confidence is not None and confidence <= 5 and delta > 90:
                        stale_count += 1
                        issues.append(
                            f"可能过时: created {entry['created']} ({delta} days ago, "
                            f"confidence={confidence}/10)"
                        )
                except (ValueError, OSError):
                    pass

            if issues:
                total_issues += len(issues)
                print(f"\n  [ISSUES] {entry['relative_path']}:")
                for issue in issues:
                    print(f"    - {issue}")
            else:
                valid_count += 1

        print(f"\nValidation: {valid_count}/{len(entries)} entries valid")
        if total_issues > 0:
            print(f"Issues found: {total_issues}")
        if stale_count > 0:
            print(f"Stale entries: {stale_count} (may need review)")

    # Orphans
    if do_orphans:
        orphans = find_orphans(kb_dir, entries)
        if orphans:
            print(f"\nOrphans found: {len(orphans)}")
            for o in orphans:
                print(f"  - {o} (not linked in index.md)")
        else:
            print(f"\nOrphans: None")

    # Rebuild
    if do_rebuild:
        rebuild_index(kb_dir, entries)
        print(f"\nIndex rebuilt: index.md updated with {len(entries)} entries")

    # Detailed output
    if args.verbose:
        print(f"\nEntry details:")
        for e in entries:
            scope_tag = e.get("scope", "?")
            print(f"  [{e['type']}][{scope_tag}] {e['title']} ({e['relative_path']})")

    # Health summary
    if args.health:
        print(f"\n{'='*60}")
        print("KB Health Summary")
        print(f"{'='*60}")
        print(f"Total entries:    {len(entries)}")
        # By scope
        scope_counts = {}
        for e in entries:
            s = e.get("scope", "legacy")
            scope_counts[s] = scope_counts.get(s, 0) + 1
        for s in ["enterprise", "domain", "service", "legacy"]:
            if s in scope_counts:
                print(f"  {s}: {scope_counts[s]}")
        # By type
        type_counts = {}
        for e in entries:
            t = e.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        print(f"By type:")
        for t, c in sorted(type_counts.items()):
            print(f"  {t}: {c}")
        # Trusted count
        trusted = sum(1 for e in entries if e.get("trusted"))
        print(f"Trusted entries:  {trusted}")
        # Stale count (quick check)
        stale = 0
        for e in entries:
            if e.get("created") and e.get("confidence"):
                try:
                    d = datetime.strptime(e["created"], "%Y-%m-%d").date()
                    if (date.today() - d).days > 90 and e["confidence"] <= 5:
                        stale += 1
                except (ValueError, TypeError):
                    pass
        print(f"Stale entries:    {stale}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
