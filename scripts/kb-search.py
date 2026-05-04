#!/usr/bin/env python3
"""Knowledge base search — full-text search across all knowledge entries.

Usage:
    kb-search.py "authentication"
    kb-search.py "JWT token" --type pattern --json
    kb-search.py "数据库" --max-results 10 --verbose
"""

import argparse
import json
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

SKIP_FILES = {"index.md"}
SKIP_PREFIXES = (".", "_")


def discover_kb_dir():
    """Find the knowledge base directory relative to this script."""
    if os.path.isdir(_DEFAULT_KB_DIR):
        return _DEFAULT_KB_DIR
    return None


def score_entry(query, content, filepath):
    """Compute relevance score for a single entry.

    Scoring:
    - Title match (# heading): +10 per query word
    - Section heading match (## heading): +5 per query word
    - Body match: +1 per occurrence (capped at 10 per word)
    - Exact phrase match in title: +20
    - Recent entry (<=7 days): +2
    """
    query_lower = query.lower()
    query_words = set(query_lower.split())
    lines = content.split("\n")
    score = 0

    # Title match
    title_line = ""
    for line in lines:
        if line.startswith("# "):
            title_line = line
            break
    title_lower = title_line.lower()
    for word in query_words:
        if word in title_lower:
            score += 10

    # Exact phrase match in title
    if query_lower in title_lower:
        score += 20

    # Section heading match
    for line in lines:
        if line.startswith("## "):
            heading_lower = line.lower()
            for word in query_words:
                if word in heading_lower:
                    score += 5

    # Body match
    body = content.lower()
    for word in query_words:
        count = min(body.count(word), 10)
        score += count

    # Recent entry bonus
    created_match = re.search(r'\*\*(?:Created|日期):\*\*\s*`?(\d{4}-\d{2}-\d{2})`?', content)
    if not created_match:
        created_match = re.search(r'\*\*Created:\*\*\s*(\d{4}-\d{2}-\d{2})', content)
    if created_match:
        try:
            created_date = datetime.strptime(created_match.group(1), "%Y-%m-%d").date()
            delta = (date.today() - created_date).days
            if delta <= 7:
                score += 2
        except ValueError:
            pass

    return score


def _score_content(query_content, target_content):
    """Core structural scoring -- title, section heading, and body matches.

    This is the pure-content scoring used by both search (score_entry)
    and deduplication (compute_similarity). Excludes recency bonus.
    """
    query_lower = query_content.lower()
    query_words = set(query_lower.split())
    target_lower = target_content.lower()
    lines = target_content.split("\n")
    score = 0

    # Title match
    title_line = ""
    for line in lines:
        if line.startswith("# "):
            title_line = line
            break
    title_lower = title_line.lower()
    for word in query_words:
        if word in title_lower:
            score += 10

    # Exact phrase match in title
    if query_lower in title_lower:
        score += 20

    # Section heading match
    for line in lines:
        if line.startswith("## "):
            heading_lower = line.lower()
            for word in query_words:
                if word in heading_lower:
                    score += 5

    # Body match
    body = target_lower
    for word in query_words:
        count = min(body.count(word), 10)
        score += count

    return score


def compute_similarity(content_a, content_b):
    """Compute normalized similarity between two entry contents (0.0 to 1.0).

    Uses the same structural scoring as score_entry (title/section/body),
    normalized by self-score so that entry length does not bias results.
    Recency bonus is excluded -- similarity is about content, not age.

    Returns a float in [0.0, 1.0] where 1.0 means identical content.
    """
    if not content_a or not content_b:
        return 0.0
    raw_score = _score_content(content_a, content_b)
    self_score = _score_content(content_a, content_a)
    if self_score == 0:
        return 0.0
    return min(raw_score / self_score, 1.0)


def extract_excerpt(content, query_words, max_chars=200):
    """Extract a relevant excerpt around the first query word match."""
    body_lower = content.lower()
    best_pos = -1
    for word in query_words:
        pos = body_lower.find(word)
        if pos != -1 and (best_pos == -1 or pos < best_pos):
            best_pos = pos

    if best_pos == -1:
        # No match found, return beginning
        return content[:max_chars].strip()

    start = max(0, best_pos - 60)
    end = min(len(content), best_pos + max_chars - 60)
    excerpt = content[start:end].strip()
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(content):
        excerpt = excerpt + "..."
    return excerpt


def detect_type(filepath, content):
    """Detect entry type from file path and content."""
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
    """Extract title from first # heading."""
    for line in content.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled"


def search(kb_dir, query, type_filters=None, max_results=20, min_score=1):
    """Search the knowledge base and return scored results."""
    query_words = set(query.lower().split())
    results = []

    search_dirs = list(TYPE_DIR_MAP.values())
    # Also search services/
    services_dir = os.path.join(kb_dir, "services")
    if os.path.isdir(services_dir):
        search_dirs.append("services")

    for dir_name in search_dirs:
        search_path = os.path.join(kb_dir, dir_name)
        if not os.path.isdir(search_path):
            continue

        for root, dirs, files in os.walk(search_path):
            # Skip hidden dirs
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

                entry_type = detect_type(filepath, content)

                # Type filter
                if type_filters and entry_type not in type_filters:
                    continue

                score = score_entry(query, content, filepath)
                if score < min_score:
                    continue

                rel_path = os.path.relpath(filepath, kb_dir)
                title = extract_title(content)
                excerpt = extract_excerpt(content, query_words)

                results.append({
                    "filename": fname,
                    "relative_path": rel_path,
                    "type": entry_type,
                    "title": title,
                    "score": score,
                    "excerpt": excerpt,
                })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:max_results]


def main():
    parser = argparse.ArgumentParser(
        description="Search the knowledge base.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("query", help="Search query string")
    parser.add_argument("-t", "--type", dest="type_filters", action="append",
                        choices=sorted(VALID_TYPES), help="Filter by type (repeatable)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--max-results", type=int, default=20, help="Max results (default: 20)")
    parser.add_argument("--min-score", type=int, default=1, help="Minimum score threshold (default: 1)")
    parser.add_argument("--kb-dir", help="Override knowledge base directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    query = args.query.strip()
    if not query:
        print("Error: Query must not be empty.", file=sys.stderr)
        sys.exit(1)

    kb_dir = args.kb_dir or discover_kb_dir()
    if not kb_dir or not os.path.isdir(kb_dir):
        print("Error: Knowledge base directory not found.", file=sys.stderr)
        sys.exit(1)

    type_filters = set(args.type_filters) if args.type_filters else None

    results = search(kb_dir, query, type_filters=type_filters,
                     max_results=args.max_results, min_score=args.min_score)

    if args.json:
        output = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "total_results": len(results),
            "results": [{
                "filename": r["filename"],
                "relative_path": r["relative_path"],
                "type": r["type"],
                "title": r["title"],
                "score": r["score"],
                "excerpt": r["excerpt"],
            } for r in results],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    # Human-readable output
    print(f"Knowledge Base Search Results")
    print(f'Query: "{query}"')
    if type_filters:
        print(f"Filter: {', '.join(sorted(type_filters))}")
    print(f"Found {len(results)} results")
    print("─" * 60)

    if not results:
        print("No results found.")
        return

    for i, r in enumerate(results, 1):
        type_label = r["type"].upper() if r["type"] != "api" else "API"
        print(f"{i}. [{type_label}] {r['title']} (score: {r['score']})")
        print(f"   Path: {r['relative_path']}")
        print(f"   {r['excerpt']}")
        if args.verbose and i < len(results):
            print()


if __name__ == "__main__":
    main()
