"""adr-check: R1 (structure) and R2 (reference integrity) checks.

R3/R4 (code drift against a decision) are delegated to adr-drift; see
``references/adr-drift.md`` in the skill.  Keeping the two concerns apart is
deliberate: R1/R2 are pure Markdown checks and must stay dependency-free,
while drift checking needs language parsers.

Exit codes: 0 clean (warnings allowed unless --strict), 1 violations.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as _dt
import json
import re
import sys
from pathlib import Path

from .model import (
    STATUS_VALUES,
    Adr,
    load_adrs,
)

PLACEHOLDER_MARKERS = (
    "<!-- short title",
    "<!-- decision driver",
    "<!-- option",
    "<!-- title of option",
    'chosen option: ""',
    "<!-- describe the context",
)

REQUIRED_SECTIONS = (
    "Context and Problem Statement",
    "Decision Outcome",
)


@dataclasses.dataclass(frozen=True)
class Issue:
    rule: str
    level: str  # "error" | "warning"
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return dataclasses.asdict(self)


def _section_text(body: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$", body, re.MULTILINE | re.IGNORECASE
    )
    if not match:
        return ""
    rest = body[match.end() :]
    next_heading = re.search(r"^#{2,3}\s", rest, re.MULTILINE)
    block = rest[: next_heading.start()] if next_heading else rest
    return re.sub(r"<!--.*?-->", "", block, flags=re.DOTALL).strip()


def _numbering_ranges(numbers: list[int]) -> str:
    """Format sorted integers as compact ranges: 2-4, 7."""
    if not numbers:
        return ""
    ranges: list[str] = []
    start = previous = numbers[0]
    for number in numbers[1:] + [numbers[-1] + 2]:
        if number == previous + 1:
            previous = number
            continue
        ranges.append(
            f"{start:04d}" if start == previous else f"{start:04d}-{previous:04d}"
        )
        start = previous = number
    return ", ".join(f"ADR-{item}" for item in ranges)


def _valid_date(value: str) -> bool:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        _dt.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def check_adrs(adrs: list[Adr], adr_dir: Path) -> list[Issue]:
    """Return every R1/R2 issue, sorted by path then rule."""
    issues: list[Issue] = []
    by_number: dict[int, Adr] = {}

    for adr in adrs:
        if adr.filename_error:
            issues.append(
                Issue("R1.1", "error", adr.relpath, adr.filename_error)
            )
            continue

        assert adr.number is not None
        if adr.number in by_number:
            issues.append(
                Issue(
                    "R1.2",
                    "error",
                    adr.relpath,
                    f"duplicate ADR number {adr.number:04d} "
                    f"(also used by {by_number[adr.number].relpath})",
                )
            )
        else:
            by_number[adr.number] = adr

        if not adr.title:
            issues.append(
                Issue(
                    "R1.4",
                    "error",
                    adr.relpath,
                    "missing title (expected a level-1 heading: '# <title>')",
                )
            )

        if not adr.status:
            issues.append(
                Issue(
                    "R1.5",
                    "error",
                    adr.relpath,
                    "missing status (frontmatter 'status:' or '## Status' section)",
                )
            )
        elif adr.status == "superseded":
            issues.append(
                Issue(
                    "R1.6",
                    "error",
                    adr.relpath,
                    "status 'superseded' must name its replacement: "
                    "'superseded by ADR-NNNN'",
                )
            )
        elif adr.status not in STATUS_VALUES and adr.superseded_by is None:
            issues.append(
                Issue(
                    "R1.6",
                    "error",
                    adr.relpath,
                    f"invalid status {adr.status!r}; expected one of "
                    f"{', '.join(STATUS_VALUES)}, or 'superseded by ADR-NNNN'",
                )
            )

        if adr.date and not _valid_date(adr.date):
            issues.append(
                Issue(
                    "R1.7",
                    "warning",
                    adr.relpath,
                    f"date {adr.date!r} is not YYYY-MM-DD",
                )
            )

        lowered = adr.body.lower()
        markers = [marker for marker in PLACEHOLDER_MARKERS if marker in lowered]
        if markers:
            issues.append(
                Issue(
                    "R1.8",
                    "error",
                    adr.relpath,
                    "unfilled template placeholder(s): "
                    + ", ".join(repr(marker) for marker in markers),
                )
            )

        for heading in REQUIRED_SECTIONS:
            if not _section_text(adr.body, heading):
                issues.append(
                    Issue(
                        "R1.9",
                        "warning",
                        adr.relpath,
                        f"MADR section missing or empty: '## {heading}'",
                    )
                )

    if not adrs:
        issues.append(
            Issue("R1.0", "warning", str(adr_dir), "no ADR files found")
        )
    elif by_number:
        highest = max(by_number)
        missing = sorted(set(range(1, highest + 1)) - set(by_number))
        if missing:
            issues.append(
                Issue(
                    "R1.3",
                    "warning",
                    str(adr_dir),
                    f"numbering gap(s): {_numbering_ranges(missing)}",
                )
            )

    # ---- R2: supersession references -----------------------------------
    for adr in by_number.values():
        if adr.superseded_by is None:
            continue
        target_number = adr.superseded_by
        if target_number == adr.number:
            issues.append(
                Issue(
                    "R2.3",
                    "error",
                    adr.relpath,
                    f"ADR-{adr.number:04d} cannot be superseded by itself",
                )
            )
            continue
        target = by_number.get(target_number)
        if target is None:
            issues.append(
                Issue(
                    "R2.1",
                    "error",
                    adr.relpath,
                    f"status names ADR-{target_number:04d}, which does not exist",
                )
            )
            continue
        if adr.number not in target.supersedes:
            issues.append(
                Issue(
                    "R2.2",
                    "error",
                    adr.relpath,
                    f"ADR-{target_number:04d} does not link back; add "
                    f"'supersedes: ADR-{adr.number:04d}' to its frontmatter "
                    f"or a 'Supersedes ADR-{adr.number:04d}' line",
                )
            )
        if target.status != "accepted":
            issues.append(
                Issue(
                    "R2.5",
                    "warning",
                    adr.relpath,
                    f"replacement ADR-{target_number:04d} is "
                    f"{target.status or 'status-less'}, not accepted",
                )
            )

    for adr in by_number.values():
        for superseded in adr.supersedes:
            old = by_number.get(superseded)
            if old is not None and old.superseded_by != adr.number:
                issues.append(
                    Issue(
                        "R2.6",
                        "warning",
                        adr.relpath,
                        f"claims to supersede ADR-{superseded:04d}, but that "
                        f"ADR's status does not point back",
                    )
                )

    # ---- R2.4: cycles ---------------------------------------------------
    edges = {
        adr.number: adr.superseded_by
        for adr in by_number.values()
        if adr.superseded_by is not None
    }
    reported: set[frozenset[int]] = set()
    for start in sorted(edges):
        chain: list[int] = []
        current: int | None = start
        while current is not None and current in edges and current not in chain:
            chain.append(current)
            current = edges.get(current)
        if current is not None and current in chain:
            cycle = chain[chain.index(current) :]
            key = frozenset(cycle)
            if key in reported:
                continue
            reported.add(key)
            path = " -> ".join(f"ADR-{number:04d}" for number in cycle + [cycle[0]])
            issues.append(
                Issue(
                    "R2.4",
                    "error",
                    by_number[cycle[0]].relpath,
                    f"supersession cycle: {path}",
                )
            )

    issues.sort(key=lambda issue: (issue.path, issue.rule, issue.message))
    return issues


def _print_human(issues: list[Issue], adr_dir: Path) -> None:
    for issue in issues:
        print(
            f"{issue.path}: {issue.level.upper():7s} {issue.rule:4s} {issue.message}"
        )
    errors = sum(1 for issue in issues if issue.level == "error")
    warnings = sum(1 for issue in issues if issue.level == "warning")
    if issues:
        print()
    print(f"adr-check: {errors} error(s), {warnings} warning(s) in {adr_dir}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="adr-check",
        description="Validate ADR structure (R1) and supersession links (R2).",
    )
    parser.add_argument(
        "--dir", default="docs/adr", help="ADR directory (default: docs/adr)"
    )
    parser.add_argument(
        "--strict", action="store_true", help="treat warnings as errors"
    )
    parser.add_argument(
        "--json", action="store_true", help="machine-readable report on stdout"
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="only read *.md directly inside --dir",
    )
    args = parser.parse_args(argv)

    adr_dir = Path(args.dir)
    if not adr_dir.is_dir():
        print(f"adr-check: error: {adr_dir} is not a directory", file=sys.stderr)
        return 2

    adrs = load_adrs(adr_dir, recursive=not args.no_recursive)
    issues = check_adrs(adrs, adr_dir)
    errors = sum(1 for issue in issues if issue.level == "error")
    warnings = len(issues) - errors

    if args.json:
        print(
            json.dumps(
                {
                    "ok": errors == 0 and not (args.strict and warnings),
                    "errors": errors,
                    "warnings": warnings,
                    "adr_dir": str(adr_dir),
                    "issues": [issue.as_dict() for issue in issues],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        _print_human(issues, adr_dir)

    if errors:
        return 1
    if args.strict and warnings:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
