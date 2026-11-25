"""ADR file model: discovery, frontmatter/status parsing, title extraction.

MADR 4.0 keeps ``status``/``date``/``decision-makers`` in YAML frontmatter.
Older templates (MADR 3.x, adr-tools) use a ``## Status`` section; we accept
that as a fallback so an existing repository needs no migration.

The module is importable with the standard library alone.  When PyYAML is
installed it is used for frontmatter; otherwise a small parser covers the
subset that MADR emits (scalars, inline lists, block lists).
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import os
import re
from pathlib import Path
from typing import Any

try:  # optional: keep ``adr-index`` usable without any installed dependency
    import yaml as _yaml
except ImportError:  # pragma: no cover - exercised when PyYAML is absent
    _yaml = None

FILENAME_RE = re.compile(
    r"^(?P<number>\d{4})-(?P<slug>[a-z0-9]+(?:-[a-z0-9]+)*)\.md$"
)
SUPERSEDED_BY_RE = re.compile(r"^superseded\s+by\s+ADR-(\d{4})$", re.IGNORECASE)
STATUS_VALUES = ("proposed", "accepted", "rejected", "deprecated")
INDEX_HEADER = "# Architecture Decision Records"

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    "template",
    "templates",
}
SKIP_NAMES = {"index.md", "readme.md"}

_SUPERSEDES_BODY_RE = re.compile(
    r"(?im)^[ \t]*(?:[-*][ \t]*)?supersedes?[ \t]*:?[ \t]*(?:ADR[-\s]?)?(\d{4})\b"
)
_SOURCE_COMMIT_BODY_RE = re.compile(
    r"(?im)^[ \t]*(?:[-*][ \t]*)?(?:source-commits?|source|commit)"
    r"[ \t]*:?[ \t]*([0-9a-f]{7,40})\b"
)


@dataclasses.dataclass
class Adr:
    """One parsed ADR file."""

    path: Path
    relpath: str
    number: int | None
    slug: str
    title: str
    status: str
    date: str
    frontmatter: dict[str, Any]
    body: str
    supersedes: list[int]
    source_commits: list[str]
    filename_error: str | None = None

    @property
    def filename(self) -> str:
        return self.path.name

    @property
    def superseded_by(self) -> int | None:
        match = SUPERSEDED_BY_RE.match(self.status)
        return int(match.group(1)) if match else None

    @property
    def is_madr(self) -> bool:
        return "## Context and Problem Statement" in self.body


def normalize_text(text: str) -> str:
    """Normalize line endings so parsing is identical on every OS."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def iter_adr_files(adr_dir: Path, recursive: bool = True) -> list[Path]:
    """Return ADR markdown files, excluding indexes, READMEs and templates."""
    if not adr_dir.is_dir():
        return []
    pattern = "**/*.md" if recursive else "*.md"
    files: list[Path] = []
    for path in adr_dir.glob(pattern):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(adr_dir).parts[:-1]
        if any(
            part in SKIP_DIRS or part.startswith(".")
            for part in relative_parts
        ):
            continue
        if path.name.lower() in SKIP_NAMES:
            continue
        files.append(path)
    return sorted(files, key=lambda p: p.relative_to(adr_dir).as_posix())


def _scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    if value.lower() in {"null", "~", "none"}:
        return None
    return value


def _minimal_yaml(text: str) -> dict[str, Any]:
    """Parse the flat YAML subset MADR frontmatter uses.

    This is intentionally not a general YAML parser: unknown constructs are
    ignored rather than guessed.  PyYAML is used whenever it is available.
    """
    data: dict[str, Any] = {}
    key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line[:1] in {" ", "\t"}:
            if key is not None and stripped.startswith("- "):
                current = data.get(key)
                if not isinstance(current, list):
                    current = []
                    data[key] = current
                current.append(_scalar(stripped[2:]))
            continue
        match = re.match(r"^([A-Za-z0-9_.-]+)\s*:\s*(.*)$", line)
        if not match:
            continue
        key = match.group(1)
        value = match.group(2).strip()
        if not value:
            data[key] = []
        elif value.startswith("[") and value.endswith("]"):
            data[key] = [
                _scalar(item)
                for item in value[1:-1].split(",")
                if item.strip()
            ]
        else:
            data[key] = _scalar(value)
    return data


def _parse_yaml(text: str) -> dict[str, Any]:
    if _yaml is not None:
        try:
            parsed = _yaml.safe_load(text)
        except Exception:
            parsed = None
        if isinstance(parsed, dict):
            return parsed
    return _minimal_yaml(text)


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split ``---`` frontmatter from the markdown body."""
    text = normalize_text(text)
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text
    for index in range(1, len(lines)):
        if lines[index].strip() in {"---", "..."}:
            raw = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1 :])
            return _parse_yaml(raw), body
    return {}, text


def _section_value(body: str, heading: str) -> str:
    """First meaningful line of a ``## Heading`` section (legacy status)."""
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$", body, re.MULTILINE | re.IGNORECASE
    )
    if not match:
        return ""
    rest = body[match.end() :]
    next_heading = re.search(r"^##\s", rest, re.MULTILINE)
    block = rest[: next_heading.start()] if next_heading else rest
    for line in block.splitlines():
        value = line.strip().strip("*` ")
        if value and not value.startswith("<!--"):
            return value
    return ""


def normalize_status(value: Any) -> str:
    """Normalize a status cell to the MADR/CANONICAL vocabulary."""
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    if value is None:
        return ""
    status = str(value).strip().strip('"').strip("'").strip()
    if not status:
        return ""
    match = SUPERSEDED_BY_RE.match(status)
    if match:
        return f"superseded by ADR-{int(match.group(1)):04d}"
    lowered = status.lower()
    if lowered in STATUS_VALUES:
        return lowered
    if lowered in {"superseded", "superseded-by"}:
        return "superseded"
    if lowered in {"draft", "pending"}:
        return "proposed"
    return status


def _iso_date(value: Any) -> str:
    if isinstance(value, _dt.datetime):
        return value.date().isoformat()
    if isinstance(value, _dt.date):
        return value.isoformat()
    text = str(value or "").strip()
    if not text or text.startswith("{"):
        return ""
    return text


def extract_title(body: str) -> str:
    """First level-1 heading, without an ``ADR-0001:``-style prefix."""
    for line in body.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if not match:
            continue
        raw = re.sub(r"<!--.*?-->", "", match.group(1)).strip()
        raw = re.sub(r"^(?:ADR[-\s]?)?\d{3,4}\s*[:.\-\u2013\u2014]\s*", "", raw)
        return raw.strip()
    return ""


def _extract_supersedes(
    frontmatter: dict[str, Any], body: str
) -> list[int]:
    numbers: list[int] = []
    for key in ("supersedes", "superseded"):
        value = frontmatter.get(key)
        if value is None:
            continue
        values = value if isinstance(value, (list, tuple)) else [value]
        for item in values:
            match = re.search(r"(?:ADR[-\s]?)?(\d{4})\b", str(item), re.IGNORECASE)
            if match:
                numbers.append(int(match.group(1)))
    for match in _SUPERSEDES_BODY_RE.finditer(body):
        numbers.append(int(match.group(1)))
    return sorted(set(numbers))


def _extract_source_commits(
    frontmatter: dict[str, Any], body: str
) -> list[str]:
    """Commit SHAs recorded by ``adr-gen``, used to keep batch runs idempotent."""
    found: list[str] = []
    for key in ("source-commit", "source-commits", "source_commit"):
        value = frontmatter.get(key)
        if value is None:
            continue
        values = value if isinstance(value, (list, tuple)) else [value]
        for item in values:
            for match in re.findall(
                r"\b([0-9a-f]{7,40})\b", str(item), re.IGNORECASE
            ):
                found.append(match.lower())
    for match in _SOURCE_COMMIT_BODY_RE.finditer(body):
        found.append(match.group(1).lower())
    return list(dict.fromkeys(found))


def parse_adr(path: Path, adr_dir: Path) -> Adr:
    """Parse one ADR file.  Unreadable files surface as empty records."""
    relpath = path.relative_to(adr_dir).as_posix()
    match = FILENAME_RE.match(path.name)
    number = int(match.group("number")) if match else None
    slug = match.group("slug") if match else path.stem
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        text = ""
    frontmatter, body = split_frontmatter(text)
    status = normalize_status(frontmatter.get("status"))
    if not status:
        status = normalize_status(_section_value(body, "Status"))
    return Adr(
        path=path,
        relpath=relpath,
        number=number,
        slug=slug,
        title=extract_title(body),
        status=status,
        date=_iso_date(frontmatter.get("date")),
        frontmatter=frontmatter,
        body=body,
        supersedes=_extract_supersedes(frontmatter, body),
        source_commits=_extract_source_commits(frontmatter, body),
        filename_error=(
            None
            if match
            else "filename must match NNNN-kebab-slug.md (lowercase ASCII)"
        ),
    )


def load_adrs(adr_dir: Path, recursive: bool = True) -> list[Adr]:
    """Parse every ADR under *adr_dir*, sorted by number then path."""
    adrs = [parse_adr(path, adr_dir) for path in iter_adr_files(adr_dir, recursive)]
    adrs.sort(
        key=lambda a: (
            a.number is None,
            a.number if a.number is not None else 0,
            a.relpath,
        )
    )
    return adrs


def render_index(adrs: list[Adr]) -> str:
    """Render the deterministic ``index.md`` content.

    Accepted ADRs get no annotation; every other state is annotated so a
    reviewer can see at a glance which decisions are not in force yet.
    """
    valid = sorted(
        (adr for adr in adrs if adr.number is not None),
        key=lambda adr: adr.number,
    )
    lines = [INDEX_HEADER, ""]
    for adr in valid:
        title = adr.title or "(untitled)"
        annotation = "" if adr.status == "accepted" else f" ({adr.status or 'unknown status'})"
        lines.append(
            f"* [ADR-{adr.number:04d}]({adr.relpath}) - {title}{annotation}"
        )
    return "\n".join(lines).rstrip("\n") + "\n"


def write_if_changed(path: Path, content: str) -> bool:
    """Atomically write *content*; return False when the file is unchanged."""
    if path.exists():
        try:
            if path.read_text(encoding="utf-8") == content:
                return False
        except OSError:
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    os.replace(temporary, path)
    return True
