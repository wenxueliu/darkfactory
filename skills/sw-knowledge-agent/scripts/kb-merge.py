#!/usr/bin/env python3
"""Knowledge base deduplication and merging — scan for similar entries and merge them.

Usage:
    kb-merge.py --scan                        # Scan for similar pairs within same type
    kb-merge.py --scan --threshold 0.6        # Custom similarity threshold
    kb-merge.py --scan --cross-type            # Cross-type scan as well
    kb-merge.py --scan --json                  # JSON output (for agent consumption)
    kb-merge.py --merge <file1> <file2>        # Merge two entries
    kb-merge.py --merge <file1> <file2> --dry-run  # Preview merge without writing
    kb-merge.py --merge-all --threshold 0.7    # Auto-merge all pairs above threshold
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
_DEFAULT_KB_DIR = os.path.join(_PROJECT_ROOT, "_context", "memory", "sw-shared", "knowledge-base")

if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

# --- Inline similarity functions (shared with kb-search.py and kb-log.py) ---

def _score_content(query_content, target_content):
    """Core structural scoring: title, section heading, and body matches."""
    query_lower = query_content.lower()
    query_words = set(query_lower.split())
    target_lower = target_content.lower()
    lines = target_content.split("\n")
    score = 0

    title_line = ""
    for line in lines:
        if line.startswith("# "):
            title_line = line
            break
    title_lower = title_line.lower()
    for word in query_words:
        if word in title_lower:
            score += 10
    if query_lower in title_lower:
        score += 20
    for line in lines:
        if line.startswith("## "):
            heading_lower = line.lower()
            for word in query_words:
                if word in heading_lower:
                    score += 5
    body = target_lower
    for word in query_words:
        count = min(body.count(word), 10)
        score += count
    return score


def compute_similarity(content_a, content_b):
    """Compute normalized similarity between two entry contents (0.0 to 1.0)."""
    if not content_a or not content_b:
        return 0.0
    raw_score = _score_content(content_a, content_b)
    self_score = _score_content(content_a, content_a)
    if self_score == 0:
        return 0.0
    return min(raw_score / self_score, 1.0)

# --- End inline similarity functions ---

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

# Sections for different entry types
GENERIC_SECTIONS = ["Summary", "Details", "Context", "Usage", "Related"]
ADR_SECTIONS = ["背景", "决策", "理由", "考虑的替代方案", "后果"]


def discover_kb_dir():
    if os.path.isdir(_DEFAULT_KB_DIR):
        return _DEFAULT_KB_DIR
    return None


def detect_type(filepath, content):
    """Detect entry type from file path."""
    rel = filepath
    for type_name, dir_name in TYPE_DIR_MAP.items():
        if f"/{dir_name}/" in rel or rel.startswith(f"{dir_name}/"):
            return type_name
    # Fallback: check content
    type_match = re.search(r'\*\*Type:\*\*\s*(\w+)', content)
    if type_match:
        t = type_match.group(1).lower()
        if t in VALID_TYPES:
            return t
    return "unknown"


def extract_title(content):
    for line in content.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled"


def extract_section(content, section_name):
    """Extract the body of a named ## section from markdown content."""
    pattern = rf'^## {re.escape(section_name)}\s*$\n(.*?)(?=^## |\Z)'
    m = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""


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


def scan_entries(kb_dir):
    """Scan all .md entries and return list of (filepath, content, type) tuples."""
    entries = []
    for type_name, dir_name in TYPE_DIR_MAP.items():
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
                entries.append((filepath, content, type_name))
    return entries


def scan_similar_pairs(kb_dir, threshold=0.4, cross_type=False):
    """Find all similar entry pairs above the threshold.

    Returns list of dicts sorted by similarity descending.
    """
    entries = scan_entries(kb_dir)
    pairs = []

    for i in range(len(entries)):
        fp_i, content_i, type_i = entries[i]
        for j in range(i + 1, len(entries)):
            fp_j, content_j, type_j = entries[j]

            # By default only compare within same type
            if not cross_type and type_i != type_j:
                continue

            sim = compute_similarity(content_i, content_j)
            if sim >= threshold:
                pairs.append({
                    "file_a": fp_i,
                    "file_b": fp_j,
                    "title_a": extract_title(content_i),
                    "title_b": extract_title(content_j),
                    "type_a": type_i,
                    "type_b": type_j,
                    "similarity": round(sim, 3),
                })

    pairs.sort(key=lambda p: p["similarity"], reverse=True)
    return pairs


def merge_entries(filepath_a, filepath_b, kb_dir, dry_run=False):
    """Merge two entries into one. Returns (kept_filepath, merged_content, removed_filepath).

    For generic types (pattern/lesson/api): merges sections intelligently.
    For ADRs: refuses to merge, suggests --supersedes instead.
    """
    try:
        with open(filepath_a, encoding="utf-8") as f:
            content_a = f.read()
        with open(filepath_b, encoding="utf-8") as f:
            content_b = f.read()
    except OSError as e:
        print(f"Error reading files: {e}", file=sys.stderr)
        sys.exit(1)

    type_a = detect_type(filepath_a, content_a)
    type_b = detect_type(filepath_b, content_b)

    # ADRs are immutable records -- refuse to merge
    if type_a == "decision" or type_b == "decision":
        print("Error: ADR entries are immutable records and cannot be merged.", file=sys.stderr)
        print("Use kb-log.py decision --supersedes <N> to mark one ADR as superseding another.",
              file=sys.stderr)
        sys.exit(1)

    title_a = extract_title(content_a)
    title_b = extract_title(content_b)
    created_a = extract_created(content_a)
    created_b = extract_created(content_b)

    # Pick the more descriptive title (heuristic: longer, non-generic)
    if len(title_b) > len(title_a) and "Untitled" not in title_b:
        merged_title = title_b
    else:
        merged_title = title_a

    # Keep the older entry, remove the newer one
    if created_a and created_b and created_a <= created_b:
        kept_path, kept_content, removed_path = filepath_a, content_a, filepath_b
        kept_title, other_title = title_a, title_b
        other_content = content_b
    elif created_a and created_b:
        kept_path, kept_content, removed_path = filepath_b, content_b, filepath_a
        kept_title, other_title = title_b, title_a
        other_content = content_a
    else:
        # Can't determine age, keep file_a
        kept_path, kept_content, removed_path = filepath_a, content_a, filepath_b
        kept_title, other_title = title_a, title_b
        other_content = content_b

    # Merge sections
    today = date.today().isoformat()
    merged_lines = [f"# {merged_title}", ""]

    # Determine type label
    if type_a != "unknown":
        type_label = TYPE_LABEL_MAP.get(type_a, type_a.title())
    else:
        type_label = TYPE_LABEL_MAP.get(type_b, type_b.title())

    merged_lines.append(f"**Type:** {type_label}")
    merged_lines.append(f"**Created:** {created_a or created_b or today}")
    merged_lines.append(f"**Author:** [merged from '{os.path.basename(kept_path)}' and "
                        f"'{os.path.basename(removed_path)}' on {today}]")
    merged_lines.append("")

    for section in GENERIC_SECTIONS:
        merged_lines.append(f"## {section}")
        merged_lines.append("")
        sec_kept = extract_section(kept_content, section)
        sec_other = extract_section(other_content, section)

        if sec_kept and sec_other:
            # Both have content: keep the longer, or concatenate if complementary
            if section in ("Details", "Usage", "Related"):
                # These sections benefit from union
                if sec_kept.strip() == sec_other.strip():
                    merged_lines.append(sec_kept)
                else:
                    merged_lines.append(sec_kept)
                    merged_lines.append("")
                    merged_lines.append(f"<!-- Merged from {os.path.basename(removed_path)} -->")
                    merged_lines.append("")
                    merged_lines.append(sec_other)
            else:
                # Summary, Context: keep the richer version
                if len(sec_other) > len(sec_kept) * 1.5 and sec_other.strip() != sec_kept.strip():
                    merged_lines.append(sec_other)
                else:
                    merged_lines.append(sec_kept)
        elif sec_kept:
            merged_lines.append(sec_kept)
        elif sec_other:
            merged_lines.append(sec_other)
        else:
            merged_lines.append("_No content provided._")

        merged_lines.append("")

    merged_content = "\n".join(merged_lines)

    if dry_run:
        print(f"[Dry Run] Would merge:")
        print(f"  Keep:   {os.path.relpath(kept_path, kb_dir)}")
        print(f"  Remove: {os.path.relpath(removed_path, kb_dir)}")
        print(f"  Title:  {merged_title}")
        return kept_path, merged_content, removed_path

    # Write merged content to kept file
    with open(kept_path, "w", encoding="utf-8") as f:
        f.write(merged_content)

    # Remove the other file
    os.remove(removed_path)

    # Log the merge
    log_path = os.path.join(kb_dir, ".kb-log.jsonl")
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": "merge",
        "kept": os.path.relpath(kept_path, kb_dir),
        "removed": os.path.relpath(removed_path, kb_dir),
        "merged_title": merged_title,
        "similarity": round(compute_similarity(content_a, content_b), 3),
    }
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except OSError:
        pass

    return kept_path, merged_content, removed_path


def main():
    parser = argparse.ArgumentParser(
        description="Knowledge base deduplication and merging.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kb-merge.py --scan
  kb-merge.py --scan --threshold 0.6 --json
  kb-merge.py --merge patterns/auth-flow.md patterns/auth-pattern.md --dry-run
  kb-merge.py --merge-all --threshold 0.7
        """,
    )
    parser.add_argument("--scan", action="store_true",
                        help="Scan for similar entry pairs")
    parser.add_argument("--cross-type", action="store_true",
                        help="Include cross-type pairs in scan (default: same-type only)")
    parser.add_argument("--threshold", type=float, default=0.4,
                        help="Similarity threshold (0.0-1.0, default: 0.4)")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON (for --scan)")
    parser.add_argument("--merge", nargs=2, metavar=("FILE_A", "FILE_B"),
                        help="Merge two entries (paths relative to KB root or absolute)")
    parser.add_argument("--merge-all", action="store_true",
                        help="Auto-merge all pairs above threshold")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview merge without writing")
    parser.add_argument("--kb-dir", help="Override knowledge base directory")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output")
    args = parser.parse_args()

    kb_dir = args.kb_dir or discover_kb_dir()
    if not kb_dir or not os.path.isdir(kb_dir):
        print("Error: Knowledge base directory not found.", file=sys.stderr)
        sys.exit(1)

    # --merge mode: merge two specific files
    if args.merge:
        file_a, file_b = args.merge
        # Resolve relative paths from kb_dir
        if not os.path.isabs(file_a):
            file_a = os.path.join(kb_dir, file_a)
        if not os.path.isabs(file_b):
            file_b = os.path.join(kb_dir, file_b)

        if not os.path.exists(file_a):
            print(f"Error: File not found: {file_a}", file=sys.stderr)
            sys.exit(1)
        if not os.path.exists(file_b):
            print(f"Error: File not found: {file_b}", file=sys.stderr)
            sys.exit(1)

        kept, merged, removed = merge_entries(file_a, file_b, kb_dir, dry_run=args.dry_run)
        if not args.dry_run:
            print(f"Merged: {os.path.relpath(removed, kb_dir)} -> {os.path.relpath(kept, kb_dir)}")
            # Rebuild index after merge
            index_script = os.path.join(_SCRIPT_DIR, "kb-index.py")
            subprocess.run([sys.executable, index_script, "--kb-dir", kb_dir, "--rebuild"],
                           capture_output=True)
            print("Index rebuilt.")
        return

    # --scan mode (default if no other action)
    do_scan = args.scan or (not args.merge and not args.merge_all)
    if do_scan:
        pairs = scan_similar_pairs(kb_dir, threshold=args.threshold, cross_type=args.cross_type)

        if args.json:
            output = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "threshold": args.threshold,
                "cross_type": args.cross_type,
                "total_pairs": len(pairs),
                "pairs": [{
                    "file_a": os.path.relpath(p["file_a"], kb_dir),
                    "file_b": os.path.relpath(p["file_b"], kb_dir),
                    "title_a": p["title_a"],
                    "title_b": p["title_b"],
                    "type": f"{p['type_a']}<->{p['type_b']}",
                    "similarity": p["similarity"],
                } for p in pairs],
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return

        print(f"Scanning {len(scan_entries(kb_dir))} entries across types...")
        print(f"Threshold: {args.threshold:.0%}" + (" (cross-type)" if args.cross_type else " (same-type only)"))
        print("─" * 60)

        if not pairs:
            print("No similar pairs found.")
            return

        print(f"Similar pairs found: {len(pairs)}")
        print()
        for i, p in enumerate(pairs, 1):
            bar = "#" * max(1, int(p["similarity"] * 20))
            print(f"  {i}. [{p['similarity']:.0%}] {p['type_a']}/{p['type_b']}")
            print(f"     A: {p['title_a']} ({os.path.relpath(p['file_a'], kb_dir)})")
            print(f"     B: {p['title_b']} ({os.path.relpath(p['file_b'], kb_dir)})")
            print(f"     [{bar}]")
            print()

        print(f"To merge a pair: kb-merge.py --merge <file_a> <file_b>")
        print(f"To merge all:    kb-merge.py --merge-all --threshold {args.threshold}")

    # --merge-all mode
    if args.merge_all:
        pairs = scan_similar_pairs(kb_dir, threshold=args.threshold, cross_type=args.cross_type)
        if not pairs:
            print("No pairs to merge.")
            return

        merged_count = 0
        skipped_paths = set()
        for p in pairs:
            if p["file_a"] in skipped_paths or p["file_b"] in skipped_paths:
                continue
            try:
                kept, _, removed = merge_entries(p["file_a"], p["file_b"], kb_dir, dry_run=args.dry_run)
                skipped_paths.add(removed)
                merged_count += 1
                print(f"  Merged: {os.path.relpath(p['file_b'], kb_dir)} -> "
                      f"{os.path.relpath(p['file_a'], kb_dir)} ({p['similarity']:.0%})")
            except SystemExit:
                # ADR merge refused, skip
                skipped_paths.add(p["file_a"])
                skipped_paths.add(p["file_b"])
                continue

        print(f"\nMerged {merged_count} pair(s).")

        if not args.dry_run and merged_count > 0:
            index_script = os.path.join(_SCRIPT_DIR, "kb-index.py")
            subprocess.run([sys.executable, index_script, "--kb-dir", kb_dir, "--rebuild"],
                           capture_output=True)
            print("Index rebuilt.")


if __name__ == "__main__":
    main()
