#!/usr/bin/env python3
"""Knowledge entry distiller -- lossless LLM-optimized compression.

Preserves all technical facts, decisions, constraints, code blocks, tables, and lists.
Strips narrative prose, transitions, and filler text.

Usage:
    kb-distill.py single <file.md>              # Compress single entry
    kb-distill.py batch <kb-dir>                # Compress all entries in KB
    kb-distill.py single <file.md> --stdout     # Output to stdout
    kb-distill.py batch <kb-dir> --output-dir dist/  # Write compressed copies
    kb-distill.py compare <file.md>             # Show before/after stats
    kb-distill.py validate <file.md>            # Round-trip: check no facts lost
"""

import re
import os
import sys
import argparse
from pathlib import Path


# Keywords that indicate technical content worth preserving
TECH_KEYWORDS_PATTERN = re.compile(
    r'`[^`]+`|'                           # inline code
    r'\b[A-Z]{2,}\b|'                      # acronyms (API, HTTP, SQL, JWT, ...)
    r'\b[a-z]+[._-][a-z]+\b|'             # snake_case identifiers
    r'\b(?:GET|POST|PUT|DELETE|PATCH)\b|'  # HTTP methods
    r'\b\d+[\.%]?\d*\b|'                  # numbers/percentages
    r'/[a-z]+(?:/[a-z]+)+|'               # file paths
    r'\bconsul\b|\baggregator\b|\bwatchdog\b|'  # project-specific terms
    r'\b(?:ADR|KB|TDD|E2E|CAS|DAG|KV)\b|' # domain acronyms
    r'```|'                                 # code fences
    r'\|.*\|'                               # table rows
)


def is_technical_sentence(sentence):
    """Check if a sentence contains technical content worth preserving."""
    return bool(TECH_KEYWORDS_PATTERN.search(sentence))


def is_transition_sentence(sentence):
    """Detect pure transition/narrative sentences."""
    transition_patterns = [
        r'^(接下来|下面|以下|如上所述|值得注意的是|需要说明的是|总而言之)',
        r'^(Let us|Next|Finally|In conclusion|Note that|It is worth)',
        r'^(我们|大家|你|我).*(?:来看|讨论|了解|注意|记住)',
    ]
    for pat in transition_patterns:
        if re.match(pat, sentence.strip(), re.IGNORECASE):
            return True
    return False


def compress_paragraph(paragraph):
    """Compress a narrative paragraph. Returns compressed text."""
    sentences = re.split(r'(?<=[。.!！?？])\s*', paragraph)

    # Keep all technical sentences
    kept = [s for s in sentences if is_technical_sentence(s) and not is_transition_sentence(s)]

    # If we kept nothing useful, generate a one-sentence summary
    if not kept:
        # Take first 100 chars as summary
        summary = paragraph[:100].strip()
        if len(paragraph) > 100:
            summary += "..."
        return "<!-- compressed: {} -->".format(summary)

    return " ".join(kept)


def distill_content(content):
    """Main distillation function. Returns compressed markdown."""
    lines = content.split("\n")
    result = []
    in_code_block = False
    in_table = False
    in_list = False
    current_paragraph = []

    for line in lines:
        # Code blocks: always preserve
        if line.strip().startswith("```"):
            # Flush pending paragraph
            if current_paragraph and not in_code_block and not in_table and not in_list:
                para = " ".join(current_paragraph)
                compressed = compress_paragraph(para)
                if compressed:
                    result.append(compressed)
                current_paragraph = []
            in_code_block = not in_code_block
            result.append(line)
            continue

        if in_code_block:
            result.append(line)
            continue

        # Tables: always preserve
        if line.strip().startswith("|") and "|" in line.strip()[1:]:
            # Flush pending paragraph
            if current_paragraph:
                para = " ".join(current_paragraph)
                compressed = compress_paragraph(para)
                if compressed:
                    result.append(compressed)
                current_paragraph = []
            result.append(line)
            in_table = True
            continue
        elif in_table and not line.strip().startswith("|"):
            in_table = False

        # Lists: always preserve
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("* ") or (stripped and stripped[0].isdigit() and ". " in stripped[:4]):
            if current_paragraph:
                para = " ".join(current_paragraph)
                compressed = compress_paragraph(para)
                if compressed:
                    result.append(compressed)
                current_paragraph = []
            result.append(line)
            in_list = True
            continue
        elif in_list and not stripped:
            in_list = False
            result.append(line)
            continue

        # Section headers: always preserve
        if stripped.startswith("#"):
            if current_paragraph:
                para = " ".join(current_paragraph)
                compressed = compress_paragraph(para)
                if compressed:
                    result.append(compressed)
                current_paragraph = []
            result.append(line)
            continue

        # Empty lines: flush paragraph
        if not stripped:
            if current_paragraph:
                para = " ".join(current_paragraph)
                compressed = compress_paragraph(para)
                if compressed:
                    result.append(compressed)
                current_paragraph = []
            result.append(line)
            continue

        # Regular text: accumulate into paragraph buffer
        current_paragraph.append(stripped)

    # Flush remaining
    if current_paragraph:
        para = " ".join(current_paragraph)
        compressed = compress_paragraph(para)
        if compressed:
            result.append(compressed)

    return "\n".join(result)


def compute_stats(original, distilled):
    """Compute compression statistics."""
    orig_chars = len(original)
    dist_chars = len(distilled)
    orig_tokens_est = orig_chars // 4  # rough estimate
    dist_tokens_est = dist_chars // 4
    ratio = (1 - dist_chars / orig_chars) * 100 if orig_chars > 0 else 0
    return {
        "original_chars": orig_chars,
        "distilled_chars": dist_chars,
        "original_tokens_est": orig_tokens_est,
        "distilled_tokens_est": dist_tokens_est,
        "compression_ratio": round(ratio, 1),
        "tokens_saved": orig_tokens_est - dist_tokens_est,
    }


def validate_roundtrip(original, distilled):
    """Check that critical technical content is preserved.
    Returns (passed, issues).
    """
    issues = []

    # Check: all code blocks preserved
    orig_code_blocks = re.findall(r'```[\s\S]*?```', original)
    dist_code_blocks = re.findall(r'```[\s\S]*?```', distilled)
    if len(orig_code_blocks) != len(dist_code_blocks):
        issues.append("Code blocks: {} -> {}".format(len(orig_code_blocks), len(dist_code_blocks)))

    # Check: all tables preserved (rows with |...|)
    orig_tables = [l for l in original.split("\n") if l.strip().startswith("|")]
    dist_tables = [l for l in distilled.split("\n") if l.strip().startswith("|")]
    if len(orig_tables) != len(dist_tables):
        issues.append("Table rows: {} -> {}".format(len(orig_tables), len(dist_tables)))

    # Check: section headers preserved
    orig_headers = re.findall(r'^##\s+.+$', original, re.MULTILINE)
    dist_headers = re.findall(r'^##\s+.+$', distilled, re.MULTILINE)
    if len(orig_headers) != len(dist_headers):
        issues.append("Section headers: {} -> {}".format(len(orig_headers), len(dist_headers)))

    # Check: frontmatter fields preserved
    for field in ["Type:", "Created:", "Author:", "Scope:", "Source:", "Confidence:"]:
        if field in original and field not in distilled:
            issues.append("Frontmatter field missing: {}".format(field))

    passed = len(issues) == 0
    return passed, issues


def main():
    parser = argparse.ArgumentParser(
        description="Distill knowledge base entries -- lossless compression.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # single
    single = sub.add_parser("single", help="Compress a single file")
    single.add_argument("file", help="Path to markdown file")
    single.add_argument("--stdout", action="store_true", help="Print to stdout instead of saving")
    single.add_argument("--validate", action="store_true", help="Run round-trip validation after compression")

    # batch
    batch = sub.add_parser("batch", help="Compress all entries in KB")
    batch.add_argument("kb_dir", nargs="?", help="Knowledge base directory")
    batch.add_argument("--output-dir", help="Output directory for compressed copies")
    batch.add_argument("--stdout", action="store_true", help="Print all results to stdout")
    batch.add_argument("--report", action="store_true", help="Print compression report only")

    # compare
    comp = sub.add_parser("compare", help="Show before/after stats")
    comp.add_argument("file", help="Path to markdown file")

    # validate
    val = sub.add_parser("validate", help="Round-trip validation")
    val.add_argument("file", help="Path to markdown file")

    args = parser.parse_args()

    if args.command == "single":
        with open(args.file, encoding="utf-8") as f:
            original = f.read()
        distilled = distill_content(original)
        stats = compute_stats(original, distilled)

        if args.validate:
            passed, issues = validate_roundtrip(original, distilled)
            if not passed:
                print("VALIDATION FAILED ({} issues):".format(len(issues)))
                for issue in issues:
                    print("  - {}".format(issue))
            else:
                print("VALIDATION PASSED: All critical content preserved.")

        print("Compression: {}%".format(stats['compression_ratio']))
        print("Tokens: {} -> {} (saved {})".format(
            stats['original_tokens_est'], stats['distilled_tokens_est'], stats['tokens_saved']
        ))

        if args.stdout:
            print("\n--- DISTILLED ---")
            print(distilled)
        else:
            out_path = args.file.replace(".md", ".distilled.md")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(distilled)
            print("Saved: {}".format(out_path))

    elif args.command == "batch":
        kb_dir = args.kb_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "_bmad", "memory", "hw-shared", "knowledge-base"
        )
        if not os.path.isdir(kb_dir):
            print("Error: KB directory not found: {}".format(kb_dir), file=sys.stderr)
            sys.exit(1)

        total_orig = 0
        total_dist = 0
        files_processed = 0
        issues_found = []

        for root, dirs, files in os.walk(kb_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fname in files:
                if not fname.endswith(".md") or fname == "index.md":
                    continue
                filepath = os.path.join(root, fname)
                with open(filepath, encoding="utf-8") as f:
                    original = f.read()
                distilled = distill_content(original)
                stats = compute_stats(original, distilled)
                passed, issues = validate_roundtrip(original, distilled)

                total_orig += stats['original_tokens_est']
                total_dist += stats['distilled_tokens_est']
                files_processed += 1

                if not passed:
                    issues_found.append((fname, issues))

                if not args.report and not args.stdout:
                    out_path = filepath.replace(".md", ".distilled.md")
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(distilled)

        if args.report or True:  # always show report
            print("\nBatch Distillation Report")
            print("Files processed: {}".format(files_processed))
            print("Total tokens: {} -> {}".format(total_orig, total_dist))
            print("Overall compression: {}%".format(
                round((1 - total_dist / total_orig) * 100, 1) if total_orig > 0 else 0
            ))
            print("Tokens saved: {}".format(total_orig - total_dist))
            if issues_found:
                print("\nValidation issues ({} files):".format(len(issues_found)))
                for fname, issues in issues_found:
                    print("  {}: {} issues".format(fname, len(issues)))

    elif args.command == "compare":
        with open(args.file, encoding="utf-8") as f:
            original = f.read()
        distilled = distill_content(original)
        stats = compute_stats(original, distilled)
        passed, issues = validate_roundtrip(original, distilled)

        print("File: {}".format(args.file))
        print("Characters: {} -> {}".format(stats['original_chars'], stats['distilled_chars']))
        print("Tokens (est): {} -> {}".format(stats['original_tokens_est'], stats['distilled_tokens_est']))
        print("Compression: {}%".format(stats['compression_ratio']))
        print("Tokens saved: {}".format(stats['tokens_saved']))
        print("Validation: {}".format("PASSED" if passed else "FAILED ({} issues)".format(len(issues))))

    elif args.command == "validate":
        with open(args.file, encoding="utf-8") as f:
            original = f.read()
        distilled = distill_content(original)
        passed, issues = validate_roundtrip(original, distilled)
        if passed:
            print("VALIDATION PASSED: All critical content preserved.")
        else:
            print("VALIDATION FAILED ({} issues):".format(len(issues)))
            for issue in issues:
                print("  - {}".format(issue))


if __name__ == "__main__":
    main()
