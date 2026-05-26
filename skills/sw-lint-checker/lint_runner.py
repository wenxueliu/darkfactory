#!/usr/bin/env python3
"""Unified lint runner — auto-discovers languages from changed files,
invokes the matching checker class per language, and reports results.

Usage:
  python lint_runner.py [--files file1 file2 ...] [--auto-fix] [--max-iterations N] [--json]

  If --files is omitted, changed files are collected from ``git diff`` /
  ``git status`` automatically.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Inject the skill's own checkers onto the path so ``from checkers import ...``
# works even when lint_runner.py is invoked from a different working directory.
_SKILL_DIR = Path(__file__).resolve().parent
if str(_SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILL_DIR))

from checkers.base import Severity  # noqa: E402
from checkers import discover_checkers, checker_for_file  # noqa: E402

# -- files that should never be passed to a linter --------------------------

_SKIP_GLOBS = (
    "node_modules/**", "dist/**", "build/**", "out/**", ".git/**",
    "vendor/**", "__pycache__/**", "*.pyc", "*.pyo",
    "*.min.js", "*.min.css", "*.lock", "*-lock.*",
    "*.generated.*", "*.gen.*", "coverage/**", ".nyc_output/**",
    ".worktree/**", ".pytest_cache/**", ".next/**", ".turbo/**",
)
_SKIP_PREFIXES = tuple(
    p.rstrip("**").rstrip("/") for p in _SKIP_GLOBS if p.endswith("/**")
)


def _should_skip(path: str) -> bool:
    """True if *path* matches any skip rule."""
    base = os.path.basename(path)
    # Lock files
    if base in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
                "Cargo.lock", "Gemfile.lock", "Pipfile.lock"):
        return True
    # Minified files
    if base.endswith(".min.js") or base.endswith(".min.css"):
        return True
    # Python bytecode
    if base.endswith(".pyc") or base.endswith(".pyo"):
        return True
    # Generated markers
    if ".generated." in base or ".gen." in base:
        return True
    # Skip directories
    for prefix in _SKIP_PREFIXES:
        if path.startswith(prefix + "/") or path.startswith(prefix + "\\"):
            return True
    return False


# -- file collection --------------------------------------------------------

def _git_root() -> Path:
    """Return the git repository root, or cwd."""
    try:
        import subprocess
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True, stderr=subprocess.DEVNULL
        )
        return Path(out.strip())
    except Exception:
        return Path.cwd()


def collect_changed_files() -> list[str]:
    """Return changed file paths (relative to git root) from git.

    Tries ``git diff HEAD~1`` first, then ``git diff --cached``, then
    ``git status --porcelain`` as fallback.
    """
    import subprocess
    root = _git_root()
    os.chdir(str(root))

    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "HEAD~1"], text=True, stderr=subprocess.DEVNULL
        )
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        if lines:
            return lines
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "--cached"], text=True, stderr=subprocess.DEVNULL
        )
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        if lines:
            return lines
    except Exception:
        pass

    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"], text=True, stderr=subprocess.DEVNULL
        )
        lines = [l.strip()[3:] for l in out.splitlines() if l.strip()]
        return lines
    except Exception:
        return []


# -- main logic -------------------------------------------------------------

def run_checks(
    files: list[str],
    auto_fix: bool = False,
    max_iterations: int = 3,
) -> dict:
    """Run lint checks on *files*, optionally auto-fixing.

    Returns a JSON-serialisable dict.
    """
    # Filter skip rules
    files = [f for f in files if not _should_skip(f)]
    if not files:
        return {"status": "PASS", "languages_detected": [], "results": []}

    # Group files by checker
    checker_classes = discover_checkers()
    lang_files: dict[str, list[str]] = {}
    for f in files:
        cls = checker_for_file(f)
        if cls is None:
            continue
        lang = cls.language
        lang_files.setdefault(lang, []).append(f)

    if not lang_files:
        return {"status": "PASS", "languages_detected": [], "results": [],
                "note": "No recognised source files in change set"}

    # Instantiate one checker per language
    checkers: dict[str, object] = {}
    for lang, lang_fs in lang_files.items():
        cls = checker_for_file(lang_fs[0])
        if cls:
            checkers[lang] = cls()

    # Phase 1: check
    results: list[dict] = []
    for lang, checker in sorted(checkers.items()):
        fs = lang_files[lang]
        cr = checker.check(fs)
        results.append({
            "language": lang,
            "tool": checker.tool_name,
            "status": "PASS" if cr.exit_code == 0 and not cr.errors else "FAIL",
            "exit_code": cr.exit_code,
            "tool_missing": cr.tool_missing,
            "install_hint": cr.install_hint if cr.tool_missing else "",
            "errors": [
                {
                    "file": e.file, "line": e.line, "column": e.column,
                    "rule": e.rule, "message": e.message,
                    "severity": e.severity.value, "auto_fixable": e.auto_fixable,
                }
                for e in cr.errors
            ],
            "error_count": len(cr.errors),
        })

    # Phase 2: auto-fix loop
    total_fixed = 0
    if auto_fix:
        for iteration in range(1, max_iterations + 1):
            has_fixable = False
            for lang, checker in sorted(checkers.items()):
                fs = lang_files[lang]
                # Only run fix if there are auto-fixable errors
                cr = checker.check(fs)
                fixable = [e for e in cr.errors if e.auto_fixable]
                if not fixable:
                    continue
                has_fixable = True
                fr = checker.auto_fix(fs)
                total_fixed += fr.fixed_count
                # Update results
                for r in results:
                    if r["language"] == lang:
                        r["errors"] = [
                            {
                                "file": e.file, "line": e.line, "column": e.column,
                                "rule": e.rule, "message": e.message,
                                "severity": e.severity.value, "auto_fixable": e.auto_fixable,
                            }
                            for e in fr.remaining_errors
                        ]
                        r["error_count"] = len(fr.remaining_errors)
                        r["status"] = "PASS" if fr.exit_code == 0 and not fr.remaining_errors else "FAIL"
            if not has_fixable:
                break  # nothing left to fix

    # Phase 3: determine overall status
    has_blockers = False
    for r in results:
        if r["status"] == "FAIL":
            for e in r["errors"]:
                if e["severity"] in (Severity.P0.value, Severity.P1.value):
                    has_blockers = True
                    break

    return {
        "status": "BLOCKED" if has_blockers else "PASS",
        "languages_detected": sorted(lang_files.keys()),
        "results": results,
        "total_fixed": total_fixed,
        "iterations": max_iterations if auto_fix else 0,
    }


# -- CLI --------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(
        description="Cross-language lint runner — auto-detects languages and runs linters",
    )
    p.add_argument("--files", nargs="*", default=None,
                   help="Files to check (default: auto-detect from git diff)")
    p.add_argument("--auto-fix", action="store_true",
                   help="Run auto-fix tools after checking")
    p.add_argument("--max-iterations", type=int, default=3,
                   help="Max fix→re-check iterations (default: 3)")
    p.add_argument("--json", action="store_true",
                   help="Output JSON instead of human-readable text")
    args = p.parse_args()

    # Collect files
    files = args.files if args.files is not None else collect_changed_files()
    if not files:
        result = {"status": "PASS", "languages_detected": [], "results": [],
                  "note": "No changed files found"}
        if args.json:
            json.dump(result, sys.stdout, indent=2)
        else:
            print("PASS — No changed files to check.")
        sys.exit(0)

    # Run checks
    result = run_checks(files, auto_fix=args.auto_fix, max_iterations=args.max_iterations)

    if args.json:
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        # Human-readable output
        langs = ", ".join(result["languages_detected"]) or "none"
        print(f"Languages detected: {langs}")
        if result.get("note"):
            print(f"Note: {result['note']}")
        print(f"Status: {result['status']}")
        if result["total_fixed"]:
            print(f"Auto-fixed: {result['total_fixed']} issue(s)")
        print()
        for r in result["results"]:
            flag = "OK" if r["status"] == "PASS" else "FAIL"
            print(f"  [{flag}] {r['language']:15s}  {r['tool']:15s}  {r['error_count']} error(s)")
            if r["tool_missing"]:
                print(f"        TOOL MISSING — install: {r['install_hint']}")
            for e in r["errors"]:
                loc = ""
                if e["file"]:
                    loc = e["file"]
                    if e["line"] is not None:
                        loc += f":{e['line']}"
                        if e["column"] is not None:
                            loc += f":{e['column']}"
                fix = " [auto-fixable]" if e["auto_fixable"] else ""
                print(f"        {e['severity']} {e['rule']}  {loc}  {e['message']}{fix}")
        print()
        if result["status"] == "PASS":
            print("LINT_PASS — All standards checks passed.")
            sys.exit(0)
        else:
            print("LINT_BLOCKED — P0/P1 issues remain after auto-fix. Escalate for manual fix.")
            sys.exit(1)


if __name__ == "__main__":
    main()
