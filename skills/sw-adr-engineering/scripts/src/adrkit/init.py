"""adr-init: create the ADR directory and the MADR 4.0 bare template.

Idempotent by design: re-running with an unchanged template is a no-op, and
a locally customized template is never overwritten without ``--force``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TEMPLATE_SOURCE = Path(__file__).with_name("templates") / "adr-template.md"


def initialize(adr_dir: Path, force: bool = False, quiet: bool = False) -> int:
    adr_dir = Path(adr_dir)
    template_dir = adr_dir / "template"
    target = template_dir / "adr-template.md"

    if not TEMPLATE_SOURCE.is_file():
        print(
            f"adr-init: error: bundled template missing at {TEMPLATE_SOURCE}",
            file=sys.stderr,
        )
        return 2

    content = TEMPLATE_SOURCE.read_text(encoding="utf-8")
    try:
        template_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"adr-init: error: cannot create {template_dir}: {exc}", file=sys.stderr)
        return 2

    if target.exists() and not force:
        try:
            existing = target.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"adr-init: error: cannot read {target}: {exc}", file=sys.stderr)
            return 2
        if existing == content:
            if not quiet:
                print(f"adr-init: {target} is already up to date")
            return 0
        print(
            f"adr-init: error: {target} exists and differs from the bundled "
            f"MADR template; re-run with --force to replace it",
            file=sys.stderr,
        )
        return 1

    target.write_text(content, encoding="utf-8", newline="\n")
    if not quiet:
        print(f"adr-init: wrote {target}")
        print(
            "adr-init: next -> adr-gen --from-text \"<decision>\" "
            f"--dir {adr_dir}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="adr-init",
        description="Create the ADR directory and the MADR 4.0 bare template.",
    )
    parser.add_argument(
        "--dir", default="docs/adr", help="ADR directory (default: docs/adr)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing template that differs from the bundled one",
    )
    parser.add_argument("--quiet", action="store_true", help="suppress output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return initialize(Path(args.dir), force=args.force, quiet=args.quiet)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
