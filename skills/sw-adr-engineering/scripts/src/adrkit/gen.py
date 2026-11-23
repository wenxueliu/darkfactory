"""adr-gen: turn a commit, a decision statement, or a requirement into an ADR.

The pipeline is deliberately conservative:

1. signal filter (``assess``) skips noise-only changes;
2. recency injection (``adr_digest`` + recent commits) keeps the model from
   duplicating or contradicting an existing decision;
3. an OpenAI-compatible model fills the MADR 4.0 template;
4. the result is validated, forced to ``status: proposed`` (a human accepts
   it), written as the next number, and added to ``index.md``.

``--no-llm`` produces a scaffold instead of calling a model, so the workflow
still works offline.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as _dt
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Callable

from .model import (
    Adr,
    extract_title,
    load_adrs,
    normalize_text,
    split_frontmatter,
    write_if_changed,
)

DEFAULT_MODEL = "gpt-4o-mini"
SCORE_THRESHOLD = 3
MAX_DIFF_CHARS = 14_000
MAX_MESSAGE_CHARS = 6_000
RECENT_ADR_LIMIT = 10
RECENT_COMMIT_LIMIT = 8

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

NOISE_PATTERNS = (
    r"(^|/)(docs?|documentation)/",
    r"(^|/)(tests?|__tests__|spec|specs)/",
    r"(^|/)\.github/",
    r"(^|/)(LICENSE|CHANGELOG|CONTRIBUTING|CODE_OF_CONDUCT)(\.|$)",
    r"(^|/)(\.gitignore|\.gitattributes|\.editorconfig|\.prettierrc)$",
    r"\.(md|rst|txt|adoc|png|jpe?g|gif|svg|ico|webp|pdf)$",
    r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|Pipfile\.lock|Cargo\.lock|go\.sum|composer\.lock)$",
)
NOISE_RE = re.compile("|".join(NOISE_PATTERNS), re.IGNORECASE)

MANIFEST_RE = re.compile(
    r"(^|/)(pyproject\.toml|setup\.py|setup\.cfg|requirements[^/]*\.txt|Pipfile|"
    r"package\.json|go\.mod|Cargo\.toml|pom\.xml|build\.gradle(?:\.kts)?|"
    r"Gemfile|composer\.json)$",
    re.IGNORECASE,
)
INFRA_RE = re.compile(
    r"(^|/)(Dockerfile[^/]*|docker-compose[^/]*|\.dockerignore|Makefile|Justfile|"
    r"Procfile|\.github/workflows/|k8s/|kubernetes/|deploy/|helm/|charts/|"
    r"[^/]+\.tf)$",
    re.IGNORECASE,
)
MIGRATION_RE = re.compile(
    r"(^|/)(migrations?|alembic|db/migrate|schema)/|"
    r"schema\.(sql|prisma)$|\.sql$",
    re.IGNORECASE,
)
SECURITY_RE = re.compile(
    r"(^|/)(auth|security|permissions?|rbac|oauth|crypto)(/|\.|_)",
    re.IGNORECASE,
)
BOUNDARY_RE = re.compile(
    r"(^|/)(api|handlers|controllers|routes|adapters|ports|infra|core|domain)/",
    re.IGNORECASE,
)
ARCHITECTURE_WORDS_RE = re.compile(
    r"\b(migrat|switch|replac|adopt|introduc|remov|deprecat|extract|split|"
    r"merg|rewrit|redesign|monorepo|microservice)\w*",
    re.IGNORECASE,
)
DOMAIN_WORDS_RE = re.compile(
    r"\b(database|queue|broker|cache|auth|gateway|service|framework|runtime|"
    r"protocol|storage|deploy|infra)\w*",
    re.IGNORECASE,
)

REQUIRED_SECTIONS = (
    "## Context and Problem Statement",
    "## Decision Drivers",
    "## Considered Options",
    "## Decision Outcome",
)


class GenerationError(RuntimeError):
    """A user-actionable failure (missing key, git ref, model output...)."""


@dataclasses.dataclass
class Change:
    source: str  # "commit" | "text" | "file"
    message: str = ""
    files: list[tuple[str, str]] = dataclasses.field(default_factory=list)
    diff: str = ""
    commit: str = ""
    path: str = ""


@dataclasses.dataclass
class Signal:
    worth: bool
    score: int
    reasons: list[str]
    files: list[str]


@dataclasses.dataclass
class GenerationResult:
    status: str  # "written" | "preview" | "skipped"
    signal: Signal
    path: Path | None = None
    markdown: str = ""


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        text=True,
        capture_output=True,
        check=False,
    )


def repo_layout(repo: Path) -> str:
    try:
        entries = sorted(
            entry.name + ("/" if entry.is_dir() else "")
            for entry in Path(repo).iterdir()
            if not entry.name.startswith(".")
        )
    except OSError:
        return ""
    return ", ".join(entries[:30])


def recent_commits(repo: Path, limit: int = RECENT_COMMIT_LIMIT) -> list[str]:
    result = _git(repo, "log", f"-n{limit}", "--format=%h %s")
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def _parse_name_status(output: str) -> list[tuple[str, str]]:
    files: list[tuple[str, str]] = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            files.append((parts[0].strip(), parts[-1].strip()))
    return files


def git_change(repo: Path, ref: str) -> Change:
    resolved = _git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if resolved.returncode != 0:
        raise GenerationError(f"git ref not found: {ref}")
    commit = resolved.stdout.strip()

    message = _git(repo, "show", "-s", "--format=%B", commit).stdout.strip()
    name_status = _git(
        repo, "show", "--name-status", "--format=", "--find-renames", commit
    ).stdout
    files = _parse_name_status(name_status)

    diff = _git(
        repo, "show", "--format=", "--unified=2", "--no-color", commit
    ).stdout
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + "\n...[diff truncated]...\n"

    return Change(
        source="commit",
        message=message,
        files=files,
        diff=diff,
        commit=commit,
    )


def file_change(path: Path) -> Change:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise GenerationError(f"cannot read {path}: {exc}") from exc
    return Change(
        source="file",
        message=text,
        path=str(path),
    )


def text_change(text: str) -> Change:
    return Change(source="text", message=text)


def _is_noise(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return bool(NOISE_RE.search(normalized))


def assess(change: Change) -> Signal:
    """Decide whether a change is architecturally significant.

    Explicit inputs (``--from-text`` / ``--from-file``) always pass: the user
    already declared that there is a decision.  Commits are scored; only
    meaningful paths contribute, so a docs-only or lockfile-only commit is
    skipped instead of generating an ADR about nothing.
    """
    if change.source in {"text", "file"}:
        return Signal(True, 10, [f"explicit {change.source} input"], [])

    meaningful = [
        path
        for _status, path in change.files
        if not _is_noise(path)
    ]
    if not change.files:
        return Signal(False, 0, ["no file changes detected"], [])
    if not meaningful:
        return Signal(
            False,
            0,
            ["only docs/tests/assets/lockfiles changed"],
            [],
        )

    score = 0
    reasons: list[str] = []

    def award(points: int, reason: str) -> None:
        nonlocal score
        score += points
        reasons.append(f"{reason} (+{points})")

    if any(MANIFEST_RE.search(path) for path in meaningful):
        award(3, "dependency/build manifest changed")
    if any(INFRA_RE.search(path) for path in meaningful):
        award(4, "deployment/infrastructure changed")
    if any(MIGRATION_RE.search(path) for path in meaningful):
        award(5, "database migration or schema changed")
    if any(SECURITY_RE.search(path) for path in meaningful):
        award(3, "authentication/security code changed")
    if any(BOUNDARY_RE.search(path) for path in meaningful):
        award(2, "module boundary path changed")

    statuses = {status[0].upper() for status, _path in change.files}
    if "D" in statuses:
        award(4, "module/file deleted")
    if "R" in statuses:
        award(3, "module/file renamed")
    if any(
        status.upper().startswith("A") and "/" not in path
        for status, path in change.files
    ):
        award(3, "new top-level module added")

    keyword_points = 0
    if ARCHITECTURE_WORDS_RE.search(change.message):
        keyword_points += 2
        reasons.append("commit message states an architectural change (+2)")
    if DOMAIN_WORDS_RE.search(change.message):
        keyword_points += 2
        reasons.append("commit message names an architectural concern (+2)")
    score += min(keyword_points, 4)

    if len(meaningful) >= 15:
        award(1, "broad change surface")

    if not reasons:
        reasons.append("no architectural signal in paths or message")

    return Signal(score >= SCORE_THRESHOLD, score, reasons, meaningful)


def adr_digest(adrs: list[Adr], limit: int = RECENT_ADR_LIMIT) -> list[str]:
    newest = sorted(
        adrs, key=lambda adr: adr.number or 0, reverse=True
    )[:limit]
    digest: list[str] = []
    for adr in newest:
        status = adr.status or "unknown"
        date = f", {adr.date}" if adr.date else ""
        digest.append(
            f"- ADR-{adr.number:04d} [{status}{date}] {adr.title or '(untitled)'}"
        )
    return digest


def slugify(text: str, limit: int = 60) -> str:
    ascii_text = (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug[:limit].strip("-")


def derive_title(change: Change) -> str:
    if change.source == "file":
        for line in normalize_text(change.message).splitlines():
            match = re.match(r"^#\s+(.+?)\s*$", line)
            if match:
                return match.group(1).strip()[:90]
        if change.path:
            return Path(change.path).stem.replace("-", " ").replace("_", " ")[:90]
    subject = ""
    for line in normalize_text(change.message).splitlines():
        if line.strip():
            subject = line.strip()
            break
    subject = re.sub(r"^#{1,6}\s*", "", subject)
    subject = re.sub(
        r"^(?:feat|fix|chore|refactor|docs|test|build|ci|perf|revert)"
        r"(?:\([^)]*\))?!?:\s*",
        "",
        subject,
        flags=re.IGNORECASE,
    )
    subject = subject.strip()
    if subject:
        return subject[:90]
    if change.commit:
        return f"Record decision from {change.commit[:7]}"
    return "Record architectural decision"


def _fallback_slug(title: str, change: Change) -> str:
    candidate = slugify(title)
    if candidate:
        return candidate
    if change.commit:
        return f"decision-{change.commit[:8]}"
    return f"decision-{_dt.date.today():%Y%m%d}"


SYSTEM_PROMPT = """\
You are an expert software architect writing one Architecture Decision Record
in MADR 4.0 format.

Output contract (violating it makes the output unusable):
1. The first line MUST be exactly: SLUG: <kebab-case-ascii-slug>
   - 2-60 chars, lowercase ASCII letters/digits/hyphens only.
2. Then the ADR markdown, starting with YAML frontmatter delimited by "---".
3. Frontmatter keys: status, date, decision-makers, consulted, informed.
   - status MUST be "proposed".
   - date MUST be YYYY-MM-DD.
4. Required headings, in this order:
   "# <short title>"
   "## Context and Problem Statement"
   "## Decision Drivers"
   "## Considered Options"
   "## Decision Outcome"
   "### Consequences"
   "## More Information"
5. "## Considered Options" lists at least two real options.
6. "## Decision Outcome" starts with:
   Chosen option: "<option name>", because <specific justification>.
7. Be concrete: cite real files, modules, services, versions from the evidence.
   Never invent facts. Put uncertainty under "## More Information".
8. Do not duplicate an existing ADR from the digest. If this decision
   supersedes one, add "- Supersedes ADR-NNNN" under "## More Information".
9. No surrounding code fences, no preamble, no commentary after the ADR.
10. Write prose and bullet text in {language}; keep the MADR headings exactly
    as given (English).
"""


def _language_name(language: str) -> str:
    return "Simplified Chinese (简体中文)" if language == "zh" else "English"


def build_messages(
    change: Change,
    signal: Signal,
    digest: list[str],
    commits: list[str],
    layout: str,
    language: str,
) -> list[dict[str, str]]:
    evidence: list[str] = [
        "## Evidence",
        f"Source: {change.source}",
    ]
    if change.commit:
        evidence.append(f"Commit: {change.commit}")
    if change.path:
        evidence.append(f"Input file: {change.path}")
    if layout:
        evidence.append(f"Repository top level: {layout}")
    if change.files:
        evidence.append("Changed files (status path):")
        evidence.extend(f"- {status} {path}" for status, path in change.files[:60])
    if commits:
        evidence.append("Recent commits:")
        evidence.extend(f"- {line}" for line in commits)
    if digest:
        evidence.append("Existing ADRs (newest first; do not duplicate):")
        evidence.extend(digest)
    if change.message:
        message = change.message[:MAX_MESSAGE_CHARS]
        evidence.append("Decision input / commit message:")
        evidence.append(message)
    if change.diff:
        evidence.append("Diff (may be truncated):")
        evidence.append("```diff\n" + change.diff + "\n```")
    evidence.append(
        "Task: write ONE new ADR that records the architectural decision implied "
        "by this evidence. If the evidence does not support a decision, say so "
        "in the Decision Outcome rather than inventing one."
    )

    system = SYSTEM_PROMPT.format(language=_language_name(language))
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n".join(evidence)},
    ]


def call_llm(messages: list[dict[str, str]], model: str) -> str:
    api_key = os.environ.get("ADR_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise GenerationError(
            "no LLM API key: set ADR_LLM_API_KEY (or OPENAI_API_KEY), "
            "or pass --no-llm to write a scaffold"
        )
    try:
        from openai import OpenAI
    except ImportError:
        from .deps import ensure

        _installed, missing = ensure(["openai"])
        if missing:
            raise GenerationError(
                "openai is not installed and could not be installed "
                "automatically; run: python3 -m pip install 'openai>=1.0' "
                "or pass --no-llm"
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise GenerationError(
                f"openai is installed but cannot be imported: {exc}"
            ) from exc

    base_url = os.environ.get("ADR_LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
    client = (
        OpenAI(api_key=api_key, base_url=base_url)
        if base_url
        else OpenAI(api_key=api_key)
    )
    try:
        timeout = float(os.environ.get("ADR_LLM_TIMEOUT", "60"))
    except ValueError:
        timeout = 60.0
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.2,
        timeout=timeout,
    )
    content = response.choices[0].message.content
    if not content or not content.strip():
        raise GenerationError("LLM returned empty content")
    return content


def strip_code_fences(text: str) -> str:
    stripped = text.strip()
    match = re.fullmatch(r"```[A-Za-z0-9_-]*\n(.*?)\n```", stripped, re.DOTALL)
    return match.group(1).strip() if match else stripped


def _split_slug(text: str) -> tuple[str, str]:
    lines = text.splitlines()
    if lines and lines[0].strip().upper().startswith("SLUG:"):
        slug = lines[0].split(":", 1)[1].strip()
        return slug, "\n".join(lines[1:]).lstrip("\n")
    return "", text


def _patch_frontmatter(markdown: str) -> str:
    """Force status=proposed and ensure a date; keep the model's prose."""
    today = _dt.date.today().isoformat()
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", markdown, re.DOTALL)
    if not match:
        return f"---\nstatus: proposed\ndate: {today}\n---\n\n{markdown}"

    frontmatter = match.group(1)
    if re.search(r"(?m)^status\s*:", frontmatter):
        frontmatter = re.sub(
            r"(?m)^status\s*:.*$", "status: proposed", frontmatter, count=1
        )
    else:
        frontmatter = "status: proposed\n" + frontmatter

    if re.search(r"(?m)^date\s*:\s*$", frontmatter):
        frontmatter = re.sub(
            r"(?m)^date\s*:\s*$", f"date: {today}", frontmatter, count=1
        )
    elif not re.search(r"(?m)^date\s*:", frontmatter):
        frontmatter = f"date: {today}\n" + frontmatter

    return "---\n" + frontmatter + "\n---\n" + markdown[match.end() :]


def validate_generated(markdown: str) -> list[str]:
    errors: list[str] = []
    frontmatter, body = split_frontmatter(markdown)
    if not frontmatter:
        errors.append("missing YAML frontmatter")
    if not extract_title(body):
        errors.append("missing level-1 title")
    lowered = body.lower()
    for heading in REQUIRED_SECTIONS:
        if heading.lower() not in lowered:
            errors.append(f"missing section: {heading}")
    if "chosen option:" not in lowered:
        errors.append("Decision Outcome lacks 'Chosen option:'")
    return errors


def scaffold(title: str, change: Change, signal: Signal) -> str:
    today = _dt.date.today().isoformat()
    source = change.commit or change.path or change.source
    drivers = [
        reason
        for reason in signal.reasons
        if not reason.startswith("explicit ")
    ]
    driver_text = "\n".join(f"- {reason}" for reason in drivers) or "- TODO: decision driver"
    return f"""---
status: proposed
date: {today}
decision-makers:
consulted:
informed:
---

# {title}

## Context and Problem Statement

TODO: describe the context and the problem this decision addresses.

## Decision Drivers

{drivers}

## Considered Options

- Option A: TODO
- Option B: TODO

## Decision Outcome

Chosen option: "TODO", because TODO.

### Consequences

* Good, because TODO
* Bad, because TODO

## More Information

Source: {source}
"""


def _next_number(adrs: list[Adr]) -> int:
    numbers = [adr.number for adr in adrs if adr.number is not None]
    return max(numbers, default=0) + 1


def generate(
    change: Change,
    adr_dir: Path,
    repo: Path,
    *,
    slug: str | None = None,
    model: str = DEFAULT_MODEL,
    language: str = "zh",
    dry_run: bool = False,
    no_llm: bool = False,
    force: bool = False,
    update_index: bool = True,
    llm_fn: Callable[[list[dict[str, str]], str], str] | None = None,
) -> GenerationResult:
    signal = assess(change)
    if not signal.worth and not force:
        return GenerationResult(status="skipped", signal=signal)

    adr_dir = Path(adr_dir)
    adrs = load_adrs(adr_dir)

    title = derive_title(change)
    digest = adr_digest(adrs)
    commits = recent_commits(repo) if change.source == "commit" else []
    layout = repo_layout(repo)

    model_slug = ""
    if no_llm:
        markdown = scaffold(title, change, signal)
    else:
        messages = build_messages(
            change, signal, digest, commits, layout, language
        )
        caller = llm_fn or call_llm
        raw = caller(messages, model)
        model_slug, markdown = _split_slug(strip_code_fences(raw))
        markdown = _patch_frontmatter(markdown)
        errors = validate_generated(markdown)
        if errors:
            repair = messages + [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": (
                        "The output failed validation: "
                        + "; ".join(errors)
                        + ". Return the corrected ADR only, following the "
                        "output contract exactly."
                    ),
                },
            ]
            raw = caller(repair, model)
            repaired_slug, markdown = _split_slug(strip_code_fences(raw))
            model_slug = model_slug or repaired_slug
            markdown = _patch_frontmatter(markdown)
            errors = validate_generated(markdown)
            if errors:
                raise GenerationError(
                    "model output failed validation: " + "; ".join(errors)
                )

    final_slug = slug or model_slug or _fallback_slug(title, change)
    final_slug = slugify(final_slug) or _fallback_slug(title, change)
    number = _next_number(adrs)
    path = adr_dir / f"{number:04d}-{final_slug}.md"

    if dry_run:
        return GenerationResult(
            status="preview", signal=signal, path=path, markdown=markdown
        )

    if path.exists():
        raise GenerationError(f"refusing to overwrite existing file: {path}")

    adr_dir.mkdir(parents=True, exist_ok=True)
    if not write_if_changed(path, markdown):
        raise GenerationError(f"refusing to overwrite existing file: {path}")

    if update_index:
        from .index import regenerate

        regenerate(adr_dir, quiet=True)

    return GenerationResult(
        status="written", signal=signal, path=path, markdown=markdown
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="adr-gen",
        description="Generate a MADR 4.0 ADR from a commit, text, or file.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--from-commit",
        nargs="?",
        const="HEAD",
        metavar="SHA",
        help="generate from a git commit (default when omitted: HEAD)",
    )
    source.add_argument(
        "--from-text", metavar="TEXT", help="generate from a decision statement"
    )
    source.add_argument(
        "--from-file", metavar="PATH", help="generate from a requirement document"
    )
    parser.add_argument(
        "--dir", default="docs/adr", help="ADR directory (default: docs/adr)"
    )
    parser.add_argument(
        "--repo", default=".", help="repository root for git metadata (default: .)"
    )
    parser.add_argument("--slug", help="override the filename slug")
    parser.add_argument(
        "--model",
        default=os.environ.get("ADR_LLM_MODEL") or DEFAULT_MODEL,
        help=f"LLM model (default: {DEFAULT_MODEL} or ADR_LLM_MODEL)",
    )
    parser.add_argument(
        "--language",
        choices=["zh", "en"],
        default="zh",
        help="prose language; MADR headings stay English (default: zh)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the ADR instead of writing it"
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="write a deterministic scaffold instead of calling a model",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="generate even when the signal filter says the change is noise",
    )
    parser.add_argument(
        "--no-index", action="store_true", help="do not refresh index.md"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = Path(args.repo)
    adr_dir = Path(args.dir)

    try:
        if args.from_commit is not None:
            change = git_change(repo, args.from_commit)
        elif args.from_text is not None:
            change = text_change(args.from_text)
        else:
            change = file_change(Path(args.from_file))
    except GenerationError as exc:
        print(f"adr-gen: error: {exc}", file=sys.stderr)
        return 2

    try:
        result = generate(
            change,
            adr_dir,
            repo,
            slug=args.slug,
            model=args.model,
            language=args.language,
            dry_run=args.dry_run,
            no_llm=args.no_llm,
            force=args.force,
            update_index=not args.no_index,
        )
    except GenerationError as exc:
        print(f"adr-gen: error: {exc}", file=sys.stderr)
        return 1

    if result.status == "skipped":
        print(
            "adr-gen: skipped: change is not architecturally significant "
            f"(score {result.signal.score} < {SCORE_THRESHOLD})"
        )
        for reason in result.signal.reasons:
            print(f"  - {reason}")
        print("  use --force to generate anyway")
        return 0

    if result.status == "preview":
        print(result.markdown)
        print(f"---\nadr-gen: would write {result.path} (dry run)")
        return 0

    assert result.path is not None
    print(f"adr-gen: wrote {result.path} (status: proposed)")
    for reason in result.signal.reasons:
        print(f"  - {reason}")
    print("adr-gen: review the ADR and change status to 'accepted' when approved")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
