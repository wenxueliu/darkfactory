"""Runtime package dependency checks and on-demand installation.

``SKILL.md``'s ``metadata.external_dependencies`` lists **other skills**.
Python packages are a different axis: they are checked immediately before the
feature that needs them, and installed on demand when missing.  This keeps the
skill usable in a bare checkout (``PYTHONPATH=... python -m adrkit index``)
without forcing every consumer to pre-install optional packages.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import os
import subprocess
import sys
from typing import Callable


@dataclasses.dataclass(frozen=True)
class Package:
    name: str
    module: str
    spec: str
    purpose: str
    feature: str


PACKAGES: dict[str, Package] = {
    "openai": Package(
        name="openai",
        module="openai",
        spec="openai>=1.0",
        purpose="call an OpenAI-compatible model from adr-gen",
        feature="gen",
    ),
    "pyyaml": Package(
        name="pyyaml",
        module="yaml",
        spec="pyyaml>=6.0",
        purpose="full YAML frontmatter parsing (a stdlib fallback exists)",
        feature="check/index",
    ),
    "adr-drift": Package(
        name="adr-drift",
        module="adr_drift",
        spec="adr-drift==0.1.0",
        purpose="R3/R4 code-drift enforcement",
        feature="enforce",
    ),
}


class DependencyError(RuntimeError):
    """A package could not be installed automatically."""


Availability = Callable[[str], bool]
Installer = Callable[[str], None]


def available(name: str) -> bool:
    """True when the package's import module is importable."""
    package = PACKAGES.get(name)
    if package is None:
        raise KeyError(f"unknown package: {name}")
    try:
        return importlib.util.find_spec(package.module) is not None
    except (ImportError, ValueError):
        return False


def _pip_install(spec: str) -> None:
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        spec,
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode == 0:
        return
    detail = (result.stderr or result.stdout or "").strip().splitlines()[-6:]
    detail_text = " | ".join(detail) if detail else "pip returned a non-zero exit"
    raise DependencyError(
        f"could not install {spec}: {detail_text}\n"
        f"  run manually: {sys.executable} -m pip install {spec!r}\n"
        "  if pip is externally managed (PEP 668), use a virtualenv and point "
        "the commands at it"
    )


def ensure(
    names: list[str],
    *,
    install: bool = True,
    installer: Installer | None = None,
    availability: Availability | None = None,
    quiet: bool = False,
) -> tuple[list[str], list[str]]:
    """Ensure *names* are importable, installing them when allowed.

    Returns ``(installed, missing)``.  ``installed`` lists packages that were
    absent before and present after; ``missing`` lists packages still absent.
    """
    availability = availability or available
    installer = installer or _pip_install
    auto_install = os.environ.get("ADR_AUTO_INSTALL", "1").lower() not in {
        "0",
        "false",
        "no",
    }
    installed: list[str] = []
    missing: list[str] = []

    for name in names:
        package = PACKAGES.get(name)
        if package is None:
            raise KeyError(f"unknown package: {name}")
        if availability(name):
            continue
        if not install or not auto_install:
            missing.append(name)
            continue
        if not quiet:
            print(f"adrkit: installing {package.spec} ...", file=sys.stderr)
        try:
            installer(package.spec)
        except DependencyError as exc:
            if not quiet:
                print(f"adrkit: {exc}", file=sys.stderr)
            missing.append(name)
            continue
        importlib.invalidate_caches()
        if availability(name):
            installed.append(name)
            if not quiet:
                print(f"adrkit: installed {package.spec}", file=sys.stderr)
        else:
            missing.append(name)

    return installed, missing


def _state(name: str) -> str:
    return "available" if available(name) else "missing"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="adrkit deps",
        description=(
            "Report or install adrkit's Python package dependencies. "
            "Skill dependencies are declared in SKILL.md metadata; this "
            "command only handles packages."
        ),
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="install missing packages instead of only reporting",
    )
    parser.add_argument(
        "--only",
        metavar="NAME[,NAME]",
        help="limit to packages: openai, pyyaml, adr-drift",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.only:
        names = [part.strip() for part in args.only.split(",") if part.strip()]
    else:
        names = list(PACKAGES)
    unknown = [name for name in names if name not in PACKAGES]
    if unknown:
        print(
            f"adrkit deps: unknown package(s): {', '.join(unknown)}; "
            f"choose from {', '.join(PACKAGES)}",
            file=sys.stderr,
        )
        return 2

    installed, missing = ensure(names, install=args.install)
    report = {
        "installed": installed,
        "missing": missing,
        "packages": {
            name: {
                "state": _state(name),
                "spec": PACKAGES[name].spec,
                "module": PACKAGES[name].module,
                "feature": PACKAGES[name].feature,
                "purpose": PACKAGES[name].purpose,
            }
            for name in names
        },
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        for name in names:
            package = PACKAGES[name]
            print(
                f"adrkit: {name:10s} {_state(name):9s} "
                f"{package.spec:18s} {package.feature:8s} {package.purpose}"
            )
        if missing and not args.install:
            print(
                "adrkit: install missing packages with "
                "`python -m adrkit deps --install`",
                file=sys.stderr,
            )
        if missing and args.install:
            auto_install = os.environ.get("ADR_AUTO_INSTALL", "1").lower() not in {
                "0",
                "false",
                "no",
            }
            if not auto_install:
                print(
                    "adrkit: auto-install is disabled by ADR_AUTO_INSTALL=0",
                    file=sys.stderr,
                )
            else:
                print(
                    "adrkit: some packages are still missing; see the errors above",
                    file=sys.stderr,
                )

    return 1 if missing else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
