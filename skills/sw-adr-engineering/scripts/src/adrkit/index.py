"""adr-index: regenerate ``index.md`` deterministically.

The file is rewritten in full (never patched by anchors), so running the
command twice produces byte-identical output.  Only the standard library is
needed, which keeps the CI step dependency-free.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .model import load_adrs, render_index, write_if_changed


def regenerate(adr_dir: Path, quiet: bool = False) -> bool:
    """Write ``adr_dir/index.md``.  Return True when the file changed."""
    adr_dir = Path(adr_dir)
    adrs = load_adrs(adr_dir)
    invalid = [adr for adr in adrs if adr.number is None]
    if invalid:
        for adr in invalid:
            print(
                f"adr-index: warning: skipped {adr.relpath}: {adr.filename_error}",
                file=sys.stderr,
            )
    content = render_index(adrs)
    changed = write_if_changed(adr_dir / "index.md", content)
    if not quiet:
        if changed:
            print(f"adr-index: wrote {adr_dir / 'index.md'} ({len(adrs) - len(invalid)} ADRs)")
        else:
            print(f"adr-index: {adr_dir / 'index.md'} is up to date")
    return changed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="adr-index",
        description="Regenerate docs/adr/index.md from the ADR files.",
    )
    parser.add_argument(
        "--dir",
        default="docs/adr",
        help="ADR directory (default: docs/adr)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 when index.md is stale",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="only read *.md directly inside --dir",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    adr_dir = Path(args.dir)
    if not adr_dir.is_dir():
        print(f"adr-index: error: {adr_dir} is not a directory", file=sys.stderr)
        return 2

    adrs = load_adrs(adr_dir, recursive=not args.no_recursive)
    for adr in adrs:
        if adr.number is None:
            print(
                f"adr-index: warning: skipped {adr.relpath}: {adr.filename_error}",
                file=sys.stderr,
            )
    expected = render_index(adrs)
    index_path = adr_dir / "index.md"

    if args.check:
        try:
            current = index_path.read_text(encoding="utf-8")
        except OSError:
            current = None
        if current != expected:
            print(
                f"adr-index: {index_path} is stale; run adr-index --dir {adr_dir}",
                file=sys.stderr,
            )
            return 1
        print(f"adr-index: {index_path} is up to date")
        return 0

    changed = write_if_changed(index_path, expected)
    if changed:
        print(f"adr-index: wrote {index_path}")
    else:
        print(f"adr-index: {index_path} is up to date")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
