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
_DEFAULT_KB_DIR = os.path.join(_PROJECT_ROOT, "_bmad", "memory", "hw-shared", "knowledge-base")

VALID_TYPES = {"pattern", "decision", "lesson", "api"}
TYPE_DIR_MAP = {
    "pattern": "patterns",
    "decision": "decisions",
    "lesson": "lessons",
    "api": "api-contracts",
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
    """Scan all .md files in the knowledge base and extract metadata."""
    entries = []
    search_dirs = list(TYPE_DIR_MAP.items())
    # Also include services/
    services_dir = os.path.join(kb_dir, "services")
    if os.path.isdir(services_dir):
        search_dirs.append(("service", "services"))

    for type_name, dir_name in search_dirs:
        search_path = os.path.join(kb_dir, dir_name)
        if not os.path.isdir(search_path):
            continue

        for root, dirs, files in os.walk(search_path):
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

                # Determine type
                if type_name == "service":
                    entry_type = "service"
                elif fname.startswith("ADR-"):
                    entry_type = "decision"
                else:
                    entry_type = type_name

                created = extract_created(content)
                author = extract_author(content)

                entries.append({
                    "type": entry_type,
                    "title": title,
                    "filename": fname,
                    "relative_path": rel_path,
                    "created": created,
                    "author": author,
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
    """Rebuild index.md from scanned entries."""
    index_path = os.path.join(kb_dir, "index.md")
    today = date.today().isoformat()

    # Group entries by type
    patterns = [e for e in entries if e["type"] == "pattern"]
    decisions = [e for e in entries if e["type"] == "decision"]
    lessons = [e for e in entries if e["type"] == "lesson"]
    apis = [e for e in entries if e["type"] == "api"]
    services = [e for e in entries if e["type"] == "service"]

    # Sort: alphabetically for most; numerically descending for ADRs
    patterns.sort(key=lambda e: e["title"].lower())
    decisions.sort(key=lambda e: e["filename"], reverse=True)
    lessons.sort(key=lambda e: e.get("created", "0000"), reverse=True)
    apis.sort(key=lambda e: e["title"].lower())

    # Read existing overview (preserve top section)
    overview_lines = []
    if os.path.exists(index_path):
        with open(index_path, encoding="utf-8") as f:
            for line in f:
                if line.strip() == "## Patterns":
                    break
                overview_lines.append(line)

    lines = overview_lines

    # Patterns section
    lines.append("## Patterns\n\n")
    if patterns:
        for e in patterns:
            lines.append(f"- [{e['title']}]({e['relative_path']})\n")
    else:
        lines.append("_No patterns recorded yet._\n")
    lines.append("\n")

    # Architecture Decisions section
    lines.append("## Architecture Decisions\n\n")
    if decisions:
        for e in decisions:
            lines.append(f"- [{e['title']}]({e['relative_path']})\n")
    else:
        lines.append("_No ADRs recorded yet._\n")
    lines.append("\n")

    # Lessons Learned section
    lines.append("## Lessons Learned\n\n")
    if lessons:
        for e in lessons:
            lines.append(f"- [{e['title']}]({e['relative_path']})\n")
    else:
        lines.append("_No lessons recorded yet._\n")
    lines.append("\n")

    # API Contracts section
    lines.append("## API Contracts\n\n")
    if apis:
        for e in apis:
            lines.append(f"- [{e['title']}]({e['relative_path']})\n")
    else:
        lines.append("_No API contracts recorded yet._\n")
    lines.append("\n")

    # Service Knowledge section
    lines.append("## Service Knowledge\n\n")
    if services:
        # Group by service-id (first segment of relative_path after services/)
        svc_groups = {}
        for e in services:
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
        lines.append("_No service knowledge generated yet._\n")
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

    # Count by type
    counts = {}
    for e in entries:
        counts[e["type"]] = counts.get(e["type"], 0) + 1

    print(f"Total entries: {len(entries)}")
    for t in ["pattern", "decision", "lesson", "api", "service"]:
        if t in counts:
            label = {"pattern": "Patterns", "decision": "Decisions", "lesson": "Lessons",
                     "api": "API Contracts", "service": "Service entries"}[t]
            print(f"  {label}: {counts[t]}")

    # Validate
    if do_validate:
        total_issues = 0
        valid_count = 0
        for entry in entries:
            filepath = os.path.join(kb_dir, entry["relative_path"])
            issues = validate_entry(filepath)
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
            print(f"  [{e['type']}] {e['title']} ({e['relative_path']})")


if __name__ == "__main__":
    main()
