#!/usr/bin/env python3
"""Knowledge base entry writer — creates Pattern, Decision (ADR), Lesson, and API entries.

Usage:
    kb-log.py pattern "My Pattern" --stdin <<'EOF'
    ## Summary
    What this pattern is about.
    ## Details
    ...
    EOF

    kb-log.py decision "Use JWT" --status accepted --stdin <<'EOF'
    ## 背景
    ...
    ## 决策
    ...
    EOF
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

# --- Inline similarity functions (shared with kb-search.py and kb-merge.py) ---

def _score_content(query_content, target_content):
    """Core structural scoring: title, section heading, and body matches.

    Pure-content scoring used by both search and deduplication.
    Excludes recency bonus.
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

    Uses structural scoring normalized by self-score so entry length
    does not bias results. Recency is excluded.
    """
    if not content_a or not content_b:
        return 0.0
    raw_score = _score_content(content_a, content_b)
    self_score = _score_content(content_a, content_a)
    if self_score == 0:
        return 0.0
    return min(raw_score / self_score, 1.0)

# --- End inline similarity functions ---

# Security: Prompt injection patterns that should block or flag knowledge entries
_PROMPT_INJECTION_PATTERNS = [
    # Instruction override patterns
    r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|directives?|commands?)",
    r"disregard\s+(all\s+)?(previous|above|prior)\s+(instructions?|directives?|commands?)",
    r"override\s+(all\s+)?(previous|system|safety)\s+(instructions?|directives?|rules?)",
    r"forget\s+(all\s+)?(previous|earlier|your)\s+(instructions?|training|prompts?)",
    # Role manipulation
    r"you\s+are\s+(now\s+)?(a\s+)?(different|new)\s+(ai|assistant|model|system|role)",
    r"your\s+(new\s+)?(role|identity|purpose)\s+is",
    r"pretend\s+(you\s+are|to\s+be)",
    r"act\s+(as\s+)?(if\s+you\s+are|like\s+a)",
    # System prompt extraction attempts
    r"(reveal|show|output|print|display|tell\s+me)\s+your\s+(system\s+)?(prompt|instructions?|rules?)",
    r"(what|all\s+of)\s+your\s+(system\s+)?(prompt|instructions?|rules?)",
    # Instruction injection via markup
    r"<(system_reminder|system-reminder|user_instructions|user-instructions)>",
    r"<function_results>",
    r"do-not-interpret-as-instructions",
    # Always/never bypass patterns
    r"always\s+(output|reply|respond|say)\s+(only|just)",
    r"never\s+(mention|say|output|show|reveal)",
    r"under\s+no\s+circumstances",
    r"regardless\s+of\s+(what|any)\s+(instructions?|rules?|policies?)",
    # Dangerous command injection in code blocks
    r"```(bash|sh|shell|python)\s*\n\s*(rm\s+-rf|sudo\s+|curl.*\|\s*(ba)?sh|wget.*-O\s*-.*\|)",
]


def scan_for_injection(content):
    """Scan content for prompt injection patterns.

    Returns (blocked: bool, findings: list[str]).
    blocked=True means high-confidence injection detected -- entry should be rejected.
    findings is a list of human-readable descriptions of what was detected.
    """
    findings = []
    high_severity_count = 0

    content_lower = content.lower()

    for pattern in _PROMPT_INJECTION_PATTERNS:
        matches = re.findall(pattern, content_lower, re.IGNORECASE)
        if matches:
            # Determine severity based on pattern position in list
            # First 6 patterns (instruction override) are HIGH severity
            # Middle patterns are MEDIUM
            # Last patterns (command injection) are HIGH only if in code blocks
            pattern_idx = _PROMPT_INJECTION_PATTERNS.index(pattern)

            if pattern_idx < 6:
                severity = "HIGH"
                high_severity_count += 1
            elif pattern_idx < 10:
                severity = "MEDIUM"
            else:
                # Command injection -- check if in code block context
                if "```" in content:
                    severity = "HIGH"
                    high_severity_count += 1
                else:
                    severity = "MEDIUM"

            findings.append(f"[{severity}] Pattern matched: {pattern[:60]}... -- count: {len(matches)}")

    blocked = high_severity_count > 0
    return blocked, findings


VALID_TYPES = {"pattern", "decision", "lesson", "api"}
VALID_ADR_STATUSES = {"proposed", "accepted", "deprecated", "superseded"}

SECTION_FIELDS_GENERIC = {
    "Summary": "",
    "Details": "",
    "Context": "",
    "Usage": "",
    "Related": "",
}

SECTION_FIELDS_ADR = {
    "背景": "",
    "决策": "",
    "理由": "",
    "考虑的替代方案": "",
    "后果": "",
}

TYPE_DIR_MAP = {
    "pattern": "patterns",
    "decision": "decisions",
    "lesson": "lessons",
    "api": "contracts",
}

SCOPE_DIR_PREFIX = {
    "enterprise": "_enterprise",
    "domain": "domains",
    "service": "services",
}

TYPE_LABEL_MAP = {
    "pattern": "Pattern",
    "decision": "Decision",
    "lesson": "Lesson",
    "api": "API",
}


def slugify(title):
    """Generate filename-friendly slug, preserving Chinese characters."""
    slug = title.strip()
    slug = re.sub(r'[\\/:*?"<>|]', "", slug)
    slug = re.sub(r'\s+', "-", slug)
    return slug


def discover_kb_dir():
    """Find the knowledge base directory relative to this script."""
    if os.path.isdir(_DEFAULT_KB_DIR):
        return _DEFAULT_KB_DIR
    return None


def next_adr_number(decisions_dir):
    """Find the highest existing ADR number and return next."""
    max_num = 0
    if not os.path.isdir(decisions_dir):
        return 1
    for fname in os.listdir(decisions_dir):
        m = re.match(r'ADR-(\d{4})-.+\.md$', fname)
        if m:
            num = int(m.group(1))
            if num > max_num:
                max_num = num
    return max_num + 1


def parse_sections_from_text(text, section_fields):
    """Parse markdown body into sections based on ## headings."""
    sections = {}
    current_section = None
    current_lines = []

    title_line = ""
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("# ") and not title_line:
            title_line = stripped
            continue
        m = re.match(r'^##\s+(.+)$', stripped)
        if m:
            if current_section:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = m.group(1)
            current_lines = []
        elif current_section:
            current_lines.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_lines).strip()

    return sections, title_line


def validate_entry(kb_type, sections, author, is_stdin_mode, source=None, confidence=None):
    """Validate required fields. Returns (errors, warnings)."""
    errors = []
    warnings = []

    if kb_type == "decision":
        required = ["背景", "决策", "理由"]
    else:
        required = ["Summary", "Details"]

    for field in required:
        content = sections.get(field, "").strip()
        if not content:
            errors.append(f"Missing required section: ## {field}")
        elif len(content) < 10:
            warnings.append(f"Section ## {field} is very short (< 10 chars)")

    if not author or not author.strip():
        errors.append("Author is required")

    if source is not None and source not in VALID_SOURCES:
        errors.append(f"Invalid source: '{source}'. Must be one of: {', '.join(sorted(VALID_SOURCES))}")

    if confidence is not None:
        if not isinstance(confidence, int) or confidence < 1 or confidence > 10:
            errors.append(f"Invalid confidence: '{confidence}'. Must be an integer between 1 and 10.")

    return errors, warnings


VALID_SOURCES = {"observed", "user-stated", "inferred", "cross-model"}


def compute_trusted(source, confidence):
    """Determine if a KB entry should be trusted based on source and confidence.

    Trust rules:
    - confidence <= 3: never trusted (regardless of source)
    - user-stated: trusted (human knowledge is trusted by default)
    - observed: not trusted (needs human validation)
    - inferred: not trusted (less reliable than observation)
    - cross-model: not trusted (prompt injection risk)
    """
    if confidence <= 3:
        return False
    if source == "user-stated":
        return True
    return False


def format_entry_generic(title, kb_type, author, sections, source="observed", confidence=5, scope="enterprise"):
    """Format a generic (Pattern/Lesson/API) entry."""
    today = date.today().isoformat()
    type_label = TYPE_LABEL_MAP.get(kb_type, kb_type.title())

    lines = [
        f"# {title}",
        "",
        f"**Type:** {type_label}",
        f"**Created:** {today}",
        f"**Scope:** {scope}",
        f"**Author:** {author}",
    ]
    if source and source != "observed":
        lines.append(f"**Source:** {source}")
    if confidence is not None and confidence != 5:
        lines.append(f"**Confidence:** {confidence}/10")

    for field in ["Summary", "Details", "Context", "Usage", "Related"]:
        content = sections.get(field, "").strip()
        lines.append("")
        lines.append(f"## {field}")
        lines.append("")
        if content:
            lines.append(content)
        else:
            lines.append("_No content provided._")

    lines.append("")
    return "\n".join(lines)


def format_entry_adr(title, author, sections, adr_num, status, supersedes, source="user-stated", confidence=10, scope="enterprise"):
    """Format an ADR entry following the ADR template."""
    today = date.today().isoformat()
    lines = [
        f"# ADR-{adr_num:04d}: {title}",
        "",
        f"**状态:** `{status}`",
        f"**日期:** `{today}`",
        f"**Scope:** {scope}",
        f"**决策者:** `{author}`",
    ]
    if source and source != "observed":
        lines.append(f"**Source:** {source}")
    if confidence is not None and confidence != 5:
        lines.append(f"**Confidence:** {confidence}/10")

    if supersedes is not None:
        lines.append(f"**替代:** `ADR-{supersedes:04d}`")

    lines.extend([
        "",
        "## 背景",
        "",
        sections.get("背景", "_No content provided._"),
        "",
        "## 决策",
        "",
        f"**我们决定:** {sections.get('决策', '_No content provided._')}",
        "",
        "## 理由",
        "",
        sections.get("理由", "_No content provided._"),
        "",
        "## 考虑的替代方案",
        "",
        sections.get("考虑的替代方案", "_No content provided._"),
        "",
        "## 后果",
        "",
        sections.get("后果", "_No content provided._"),
    ])

    if supersedes is not None:
        lines.extend([
            "",
            "## 相关 ADR",
            "",
            f"- `ADR-{supersedes:04d}`: 被本 ADR 替代",
        ])

    lines.append("")
    return "\n".join(lines)


def update_index(kb_dir, kb_type, title, filename, author, adr_num=None, scope="enterprise", scope_value=None):
    """Insert entry link into the index.md."""
    index_path = os.path.join(kb_dir, "index.md")
    if not os.path.exists(index_path):
        return False, "index.md not found"

    with open(index_path, encoding="utf-8") as f:
        lines = f.readlines()

    # Compute link path and section heading based on scope
    type_dir_name = TYPE_DIR_MAP[kb_type]

    if scope == "service":
        section_heading = "## Service Knowledge"
        svc_id = scope_value or "unknown"
        link_dir = f"services/{svc_id}/{type_dir_name}"
    elif scope == "domain":
        section_headings = {
            "pattern": "## Patterns",
            "decision": "## Architecture Decisions",
            "lesson": "## Lessons Learned",
            "api": "## API Contracts",
        }
        section_heading = section_headings[kb_type]
        domain_name = scope_value or "unknown"
        link_dir = f"domains/{domain_name}/{type_dir_name}"
    else:  # enterprise
        section_headings = {
            "pattern": "## Patterns",
            "decision": "## Architecture Decisions",
            "lesson": "## Lessons Learned",
            "api": "## API Contracts",
        }
        section_heading = section_headings[kb_type]
        link_dir = f"_enterprise/{type_dir_name}"

    if kb_type == "decision" and adr_num is not None:
        link_line = f"- [ADR-{adr_num:04d}: {title}]({link_dir}/ADR-{adr_num:04d}-{slugify(title)}.md)\n"
    else:
        link_line = f"- [{title}]({link_dir}/{filename})\n"

    # Find the section and insert
    new_lines = []
    updated = False
    for i, line in enumerate(lines):
        new_lines.append(line)
        if line.strip() == section_heading:
            # Skip until next section heading or empty line after links
            j = i + 1
            # Find insertion point: after the heading line, insert alphabetically
            inserted = False
            while j < len(lines):
                stripped = lines[j].strip()
                if stripped.startswith("## ") or (stripped.startswith("##") and not stripped.startswith("###")):
                    # Hit next section, insert before it
                    if not inserted:
                        new_lines.append(link_line)
                        new_lines.append("\n")
                        inserted = True
                        updated = True
                    break
                if stripped.startswith("- [") and not inserted:
                    if link_line.lower() < stripped.lower():
                        new_lines.append(link_line)
                        inserted = True
                        updated = True
                if j == i + 1 and not stripped:
                    # Empty line after heading, insert link right here
                    new_lines.append(link_line)
                    inserted = True
                    updated = True
                new_lines.append(lines[j])
                j += 1
            if not inserted and not updated:
                new_lines.append(link_line)
                updated = True
            break

    if not updated:
        return False, f"Section '{section_heading}' not found in index.md"

    # Update the update table
    today = date.today().isoformat()
    update_row = f"| {today} | {TYPE_LABEL_MAP.get(kb_type, kb_type)}: {title} | {author} |\n"

    final_lines = []
    table_updated = False
    for i, line in enumerate(new_lines):
        final_lines.append(line)
        if "| 日期 | 更新内容 | 更新人 |" in line:
            if i + 1 < len(new_lines) and "|---" in new_lines[i + 1]:
                final_lines.append(new_lines[i + 1])
                final_lines.append(update_row)
                # Skip the original separator line
                # Actually, we already appended the separator, now skip i+1
                # Handle by tracking skip
                table_updated = True
                continue
        if table_updated and new_lines[i - 1].startswith("|---") if i > 0 else False:
            continue

    if table_updated:
        # Rebuild: we already inserted correctly above, but there's a bug in the logic
        # Let's just use a simpler approach
        pass

    # Simpler approach: rebuild the file
    result_lines = []
    in_table = False
    header_found = False
    row_inserted = False
    for line in new_lines:
        if "| 日期 | 更新内容 | 更新人 |" in line:
            result_lines.append(line)
            header_found = True
            continue
        if header_found and line.strip().startswith("|---"):
            result_lines.append(line)
            in_table = True
            continue
        if header_found and in_table and line.strip().startswith("|"):
            if not row_inserted:
                result_lines.append(update_row)
                row_inserted = True
            result_lines.append(line)
            continue
        if header_found and in_table and not line.strip().startswith("|"):
            if not row_inserted:
                result_lines.append(update_row)
                row_inserted = True
            in_table = False
            header_found = False
            result_lines.append(line)
            continue
        result_lines.append(line)

    if header_found and not row_inserted:
        result_lines.append(update_row)
        # Also need a blank line after the update row to close the table
        result_lines.append("\n")

    with open(index_path, "w", encoding="utf-8") as f:
        f.writelines(result_lines)

    return True, None


def append_transaction_log(kb_dir, entry_data, action="create"):
    """Append an entry to the JSONL transaction log."""
    log_path = os.path.join(kb_dir, ".kb-log.jsonl")
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "type": entry_data["type"],
        "title": entry_data["title"],
        "filename": entry_data["filename"],
        "relative_path": entry_data["relative_path"],
        "author": entry_data["author"],
        "adr_number": entry_data.get("adr_num"),
        "source": entry_data.get("source"),
        "confidence": entry_data.get("confidence"),
        "trusted": entry_data.get("trusted"),
        "scope": entry_data.get("scope", "enterprise"),
    }
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        return True, None
    except OSError as e:
        return False, str(e)


def check_duplicates(kb_dir, kb_type, new_content, threshold=0.4, scope="enterprise", scope_value=None):
    """Scan existing entries of the same type for content similarity.

    Returns (blocked: bool, similar_entries: list[dict]).
    blocked is True when at least one entry exceeds 0.80 similarity.
    """
    type_dir_name = TYPE_DIR_MAP.get(kb_type)
    if not type_dir_name:
        return False, []

    if scope == "enterprise":
        search_path = os.path.join(kb_dir, "_enterprise", type_dir_name)
    elif scope == "domain":
        if not scope_value:
            return False, []
        search_path = os.path.join(kb_dir, "domains", scope_value, type_dir_name)
    elif scope == "service":
        if not scope_value:
            return False, []
        search_path = os.path.join(kb_dir, "services", scope_value, type_dir_name)
    else:
        search_path = os.path.join(kb_dir, type_dir_name)
    if not os.path.isdir(search_path):
        return False, []

    similar = []
    for root, dirs, files in os.walk(search_path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            if fname.startswith(".") or not fname.endswith(".md"):
                continue
            filepath = os.path.join(root, fname)
            try:
                with open(filepath, encoding="utf-8") as f:
                    existing_content = f.read()
            except (OSError, UnicodeDecodeError):
                continue

            sim = compute_similarity(new_content, existing_content)
            if sim >= threshold:
                title = "Untitled"
                for line in existing_content.split("\n"):
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break
                similar.append({
                    "filepath": filepath,
                    "filename": fname,
                    "title": title,
                    "similarity": round(sim, 3),
                    "excerpt": existing_content[:300].replace("\n", " ").strip(),
                })

    similar.sort(key=lambda e: e["similarity"], reverse=True)
    blocked = any(e["similarity"] >= 0.80 for e in similar)
    return blocked, similar


def main():
    parser = argparse.ArgumentParser(
        description="Create a knowledge base entry.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kb-log.py pattern "Circuit Breaker" --stdin
  kb-log.py decision "Use PostgreSQL" --status accepted --stdin
  kb-log.py lesson "Null Pointer Incident" --file lesson-body.md
  kb-log.py api "User Service OpenAPI" --stdin --dry-run
  kb-log.py pattern "Auth Pattern" --source user-stated --confidence 8 --stdin
  kb-log.py decision "DB Choice" --source user-stated --confidence 10 --stdin
  kb-log.py lesson "Cache Bug" --source observed --confidence 6 --stdin
        """,
    )
    parser.add_argument("type", choices=sorted(VALID_TYPES), help="Entry type")
    parser.add_argument("title", help="Entry title")
    parser.add_argument("-a", "--author", default="hw-knowledge-agent", help="Author identifier")
    parser.add_argument("-f", "--file", dest="file_path", help="Read entry body from markdown file")
    parser.add_argument("-s", "--stdin", action="store_true", help="Read entry body from stdin")
    parser.add_argument("--status", default="proposed", choices=sorted(VALID_ADR_STATUSES),
                        help="ADR status (decision only, default: proposed)")
    parser.add_argument("--supersedes", type=int, help="ADR number this decision supersedes")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--kb-dir", help="Override knowledge base directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--dedup-check", action="store_true",
                        help="Scan existing entries for similar content before creating")
    parser.add_argument("--dedup-threshold", type=float, default=0.4,
                        help="Similarity threshold for dedup warning (0.0-1.0, default: 0.4)")
    parser.add_argument("--auto-dedup", action="store_true",
                        help="Auto-skip creation if near-duplicate (>80%%) detected (non-interactive)")
    parser.add_argument("--source", choices=sorted(VALID_SOURCES),
                        default="observed",
                        help="Knowledge source (default: observed)")
    parser.add_argument("--confidence", type=int, default=5, choices=range(1, 11),
                        metavar="1-10",
                        help="Confidence score 1-10 (default: 5)")
    parser.add_argument("--skip-injection-check", action="store_true",
                        help="Bypass prompt injection scan (requires human review)")
    parser.add_argument("--scope", choices=["enterprise", "domain", "service"],
                        default="enterprise",
                        help="Knowledge scope (default: enterprise)")
    parser.add_argument("--domain", help="Domain name (required when --scope domain)")
    parser.add_argument("--service", help="Service ID (required when --scope service)")
    args = parser.parse_args()

    kb_type = args.type.lower()
    title = args.title.strip()

    if not title:
        print("Error: Title must not be empty.", file=sys.stderr)
        sys.exit(1)

    # Discover KB directory
    kb_dir = args.kb_dir or discover_kb_dir()
    if not kb_dir:
        print("Error: Knowledge base directory not found. Use --kb-dir to specify.", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(kb_dir):
        print(f"Error: Knowledge base directory not found: {kb_dir}", file=sys.stderr)
        sys.exit(1)

    # Read body content
    if args.stdin:
        body = sys.stdin.read()
    elif args.file_path:
        try:
            with open(args.file_path, encoding="utf-8") as f:
                body = f.read()
        except OSError as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Error: Use --stdin or --file to provide entry body.", file=sys.stderr)
        print("Example: kb-log.py pattern 'Title' --stdin <<'EOF'", file=sys.stderr)
        sys.exit(1)

    if not body.strip():
        print("Error: Entry body is empty.", file=sys.stderr)
        sys.exit(1)

    # Security scan for prompt injection (skip if --skip-injection-check is set)
    if not args.skip_injection_check:
        blocked, injection_findings = scan_for_injection(body)
        if injection_findings:
            if blocked:
                print("=== PROMPT INJECTION DETECTED ===", file=sys.stderr)
                print(f"Entry BLOCKED due to {len(injection_findings)} suspicious patterns:", file=sys.stderr)
                for finding in injection_findings:
                    print(f"  {finding}", file=sys.stderr)
                print("", file=sys.stderr)
                print("If this is a false positive (e.g., documenting a security pattern about prompt injection),", file=sys.stderr)
                print("use --skip-injection-check to bypass, after human review.", file=sys.stderr)
                sys.exit(1)
            else:
                print("=== PROMPT INJECTION WARNING ===", file=sys.stderr)
                print(f"Medium-severity patterns found ({len(injection_findings)}):", file=sys.stderr)
                for finding in injection_findings:
                    print(f"  {finding}", file=sys.stderr)
                print("Proceeding with creation but flagged for review.", file=sys.stderr)
                print("", file=sys.stderr)
    elif args.verbose:
        print("[Injection scan] Skipped (--skip-injection-check flag set).", file=sys.stderr)

    # Parse sections
    if kb_type == "decision":
        section_fields = SECTION_FIELDS_ADR
    else:
        section_fields = SECTION_FIELDS_GENERIC

    sections, parsed_title = parse_sections_from_text(body, section_fields)
    # Use parsed title if first heading found and matches
    if parsed_title:
        title_from_body = parsed_title.lstrip("#").strip()
        if title_from_body:
            title = title_from_body

    # Validate
    errors, warnings = validate_entry(kb_type, sections, args.author, args.stdin, args.source, args.confidence)
    if errors:
        for err in errors:
            print(f"Validation Error: {err}", file=sys.stderr)
        sys.exit(1)
    for warn in warnings:
        print(f"Validation Warning: {warn}", file=sys.stderr)

    # Generate filename
    slug = slugify(title)
    type_dir = TYPE_DIR_MAP[kb_type]
    adr_num = None

    # Compute scope-aware paths
    if args.scope == "enterprise":
        scope_dir = "_enterprise"
        scope_value = None
    elif args.scope == "domain":
        if not args.domain:
            print("Error: --domain is required when --scope=domain", file=sys.stderr)
            sys.exit(1)
        scope_dir = f"domains/{args.domain}"
        scope_value = args.domain
    elif args.scope == "service":
        if not args.service:
            print("Error: --service is required when --scope=service", file=sys.stderr)
            sys.exit(1)
        scope_dir = f"services/{args.service}"
        scope_value = args.service

    if kb_type == "decision":
        decisions_dir = os.path.join(kb_dir, scope_dir, "decisions")
        adr_num = next_adr_number(decisions_dir)
        filename = f"ADR-{adr_num:04d}-{slug}.md"
    else:
        filename = f"{slug}.md"

    filepath = os.path.join(kb_dir, scope_dir, type_dir, filename)

    # Format entry
    if kb_type == "decision":
        content = format_entry_adr(title, args.author, sections, adr_num, args.status, args.supersedes, args.source, args.confidence, args.scope)
    else:
        content = format_entry_generic(title, kb_type, args.author, sections, args.source, args.confidence, args.scope)

    # Dedup check — scan existing entries before creating
    if args.dedup_check or args.auto_dedup:
        blocked, similar = check_duplicates(kb_dir, kb_type, content, args.dedup_threshold, args.scope, scope_value)

        if similar:
            type_label = TYPE_LABEL_MAP.get(kb_type, kb_type)
            print(f"\n=== Dedup Check: {len(similar)} similar {type_label} entr{'y' if len(similar) == 1 else 'ies'} found ===")
            print()
            for i, e in enumerate(similar, 1):
                bar_len = min(int(e["similarity"] * 20), 20)
                bar = "█" * bar_len + "░" * (20 - bar_len)
                print(f"  {i}. [{bar}] {e['similarity']:.0%} — {e['title']}")
                print(f"     File: {e['filename']}")
                if e["excerpt"]:
                    snippet = e["excerpt"][:120] + ("..." if len(e["excerpt"]) > 120 else "")
                    print(f"     {snippet}")
                print()

            if blocked:
                if args.auto_dedup:
                    trusted = compute_trusted(args.source, args.confidence)
                    relative_path = f"{scope_dir}/{type_dir}/{filename}"
                    entry_data = {
                        "type": kb_type, "title": title,
                        "filename": filename, "author": args.author,
                        "adr_num": adr_num,
                        "source": args.source,
                        "confidence": args.confidence,
                        "trusted": trusted,
                        "scope": args.scope,
                        "relative_path": relative_path,
                    }
                    append_transaction_log(kb_dir, entry_data, action="skipped-dedup")
                    print(f"Skipped (near-duplicate detected, >80%): {title}")
                    return
                else:
                    print("BLOCKED: Near-duplicate detected (>=80% similarity).")
                    print("Use --auto-dedup to skip silently, or review and merge with kb-merge.py.")
                    sys.exit(1)

            # Below block threshold — warn but proceed
            print("[WARN] Similar entries found but below block threshold (80%). Proceeding with creation.")
            print()
        else:
            if args.verbose:
                print(f"[Dedup] No similar entries found (threshold: {args.dedup_threshold:.0%}).")

    # Dry run
    if args.dry_run:
        print(f"[Dry Run] Would create: {scope_dir}/{type_dir}/{filename}")
        print(f"[Dry Run] Would append to .kb-log.jsonl")
        print(f"[Dry Run] Would update index.md")
        if args.verbose:
            print("\n--- Entry Preview ---")
            print(content)
        return

    # Write entry file
    target_dir = os.path.join(kb_dir, scope_dir, type_dir)
    os.makedirs(target_dir, exist_ok=True)

    if os.path.exists(filepath):
        print(f"Error: Entry already exists: {filepath}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        print(f"Error writing entry: {e}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Created: {filepath}")

    # Update index
    ok, err_msg = update_index(kb_dir, kb_type, title, filename, args.author, adr_num, args.scope, scope_value)
    if not ok:
        print(f"Warning: Failed to update index: {err_msg}", file=sys.stderr)

    # Transaction log
    trusted = compute_trusted(args.source, args.confidence)
    relative_path = f"{scope_dir}/{type_dir}/{filename}"
    entry_data = {
        "type": kb_type,
        "title": title,
        "filename": filename,
        "author": args.author,
        "adr_num": adr_num,
        "source": args.source,
        "confidence": args.confidence,
        "trusted": trusted,
        "scope": args.scope,
        "relative_path": relative_path,
    }
    ok, err_msg = append_transaction_log(kb_dir, entry_data)
    if not ok:
        print(f"Warning: Failed to append transaction log: {err_msg}", file=sys.stderr)

    if adr_num:
        print(f"Created ADR-{adr_num:04d}: {title}")
    else:
        print(f"Created {kb_type} entry: {title}")


if __name__ == "__main__":
    main()
