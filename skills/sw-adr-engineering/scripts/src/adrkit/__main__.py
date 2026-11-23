"""``python -m adrkit <command>`` umbrella entry point."""

from __future__ import annotations

import sys

from . import check, deps, gen, index, init

COMMANDS = {
    "init": init.main,
    "gen": gen.main,
    "index": index.main,
    "check": check.main,
    "deps": deps.main,
}

USAGE = """\
usage: python -m adrkit <command> [options]

commands:
  init    create docs/adr and the MADR 4.0 bare template
  gen     generate an ADR from a commit, text, or file
  index   regenerate docs/adr/index.md
  check   validate ADR structure (R1) and supersession links (R2)
  deps    report or install Python package dependencies
"""


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help", "help"}:
        print(USAGE)
        return 0
    command = args.pop(0)
    handler = COMMANDS.get(command)
    if handler is None:
        print(f"adrkit: unknown command {command!r}\n", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2
    return handler(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
