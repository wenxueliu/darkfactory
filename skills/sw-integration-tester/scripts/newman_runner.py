#!/usr/bin/env python3
"""newman_runner — Hard-execute Newman API tests with pre-check + JUnit parsing.

This script is the single source of truth for "newman ran successfully".
It is invoked by sw-integration-tester as a MANDATORY step. Failure here
fails the integration gate; it cannot be silently skipped.

Usage:
    python newman_runner.py --requirement-id REQ-20260107-001
    python newman_runner.py --requirement-id REQ-... --json
    python newman_runner.py --requirement-id REQ-... --no-bail
    python newman_runner.py --service-id user-service --requirement-id REQ-20260107-001

Exit codes:
    0  - All tests passed
    2  - Collection / env file missing (pre-check fail)
    3  - newman binary not installed
    4  - newman execution failed (test failures, non-zero exit)
    5  - Output parsing failed
    6  - Internal error
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import yaml

# --- Constants ---

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
# Walk up to project root: skills/sw-integration-tester/scripts -> project root
PROJECT_ROOT = SKILL_DIR.parent.parent.parent

DEFAULT_SHARED_DIR = "knowledge"
DESIGNS_DIRNAME = "designs"
MANIFEST_FILENAME = "manifest.yaml"
RESULTS_FILENAME = "test-results.yaml"

NEWMAN_NOT_INSTALLED_HINT = (
    "newman not found on PATH. Install with: `npm install -g newman`. "
    "See https://www.npmjs.com/package/newman for details."
)


# --- Pre-check helpers ---

def detect_project_root(start) -> Path:
    """Walk up to find the project root (where _context/ or knowledge/ lives)."""
    start = Path(start) if not isinstance(start, Path) else start
    markers = {".git", "_context", "knowledge", "package.json", "pyproject.toml"}
    d = start.resolve()
    for _ in range(8):
        for marker in markers:
            if (d / marker).exists():
                return d
        parent = d.parent
        if parent == d:
            break
        d = parent
    return start.resolve()


def resolve_paths(requirement_id: str, project_root: Path, service_id: str) -> dict:
    """Resolve one service's canonical test paths from the requirement bundle."""
    tests_dir = (
        project_root
        / DEFAULT_SHARED_DIR
        / DESIGNS_DIRNAME
        / requirement_id
        / "services"
        / service_id
        / "tests"
    )
    return {
        "collection": tests_dir / "collection.json",
        "env": tests_dir / "environment.json",
        "data": tests_dir / "data.json",
        "report": tests_dir / "report.xml",
        "service_id": service_id,
        "results_yaml": (
            project_root
            / DEFAULT_SHARED_DIR
            / "requirements"
            / requirement_id
            / RESULTS_FILENAME
        ),
    }


def resolve_manifest_path(requirement_id: str, project_root: Path) -> Path:
    """Return the Stage 1 bundle manifest for a requirement."""
    return (
        project_root
        / DEFAULT_SHARED_DIR
        / DESIGNS_DIRNAME
        / requirement_id
        / MANIFEST_FILENAME
    )


def resolve_all_paths(requirement_id: str, project_root: Path) -> tuple[list[dict], str]:
    """Load all Stage 2 API artifacts registered by the bundle manifest."""
    manifest_path = resolve_manifest_path(requirement_id, project_root)
    if not manifest_path.exists():
        return [], f"Bundle manifest not found: {manifest_path}"

    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        return [], f"Cannot read bundle manifest {manifest_path}: {exc}"

    entries = manifest.get("api_test_artifacts") or []
    if not entries:
        return [], (
            f"No api_test_artifacts registered in {manifest_path}. "
            "Every passed Stage 2 service must register its API test artifacts."
        )

    bundle_dir = manifest_path.parent
    paths = []
    for entry in entries:
        service_id = entry.get("service_id")
        if not service_id:
            return [], f"Manifest entry in {manifest_path} is missing service_id"
        resolved = resolve_paths(requirement_id, project_root, service_id)
        for key, manifest_key in (
            ("collection", "collection"),
            ("env", "environment"),
            ("data", "data"),
            ("report", "report"),
        ):
            value = entry.get(manifest_key)
            if value and value != "NOT_CREATED":
                resolved[key] = bundle_dir / value
        paths.append(resolved)
    return paths, ""


def pre_check(paths: dict) -> tuple[bool, str]:
    """Verify required files exist. Returns (ok, error_message)."""
    if not paths["collection"].exists():
        return False, (
            f"Collection not found: {paths['collection']}. "
            f"sw-service-designer must register a collection for this service before integration test runs. "
            f"Block: this is a hard failure; integration gate cannot pass without it."
        )
    if not paths["env"].exists():
        # env is optional in some setups, but for CI it's required
        return False, (
            f"Environment file not found: {paths['env']}. "
            f"Required for parameterizing baseUrl and authToken. "
            f"Generate via sw-service-designer alongside the collection."
        )
    return True, ""


# --- Newman invocation ---

def check_newman_installed() -> tuple[bool, str]:
    """Check that newman is on PATH. Returns (ok, hint)."""
    if shutil.which("newman") is None:
        return False, NEWMAN_NOT_INSTALLED_HINT
    return True, ""


def run_newman(paths: dict, bail: bool, timeout_request_ms: int) -> tuple[int, str, str]:
    """Invoke newman and capture stdout/stderr. Returns (exit_code, stdout, stderr)."""
    cmd = [
        "newman", "run", str(paths["collection"]),
        "-e", str(paths["env"]),
        "--reporters", "cli,junit",
        "--reporter-junit-export", str(paths["report"]),
    ]
    if paths["data"].exists():
        cmd.extend(["-d", str(paths["data"])])
    if bail:
        cmd.append("--bail")
    cmd.extend(["--timeout-request", str(timeout_request_ms)])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # hard cap at 5 min for the whole run
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"newman run timed out after 300s (cmd: {' '.join(cmd)})"
    except OSError as e:
        return 126, "", f"Failed to invoke newman: {e}"


# --- JUnit parsing ---

def parse_junit_xml(report_path: Path) -> dict:
    """Parse newman's JUnit XML output into structured test result.

    Returns dict with: total, passed, failed, errored, skipped, failures (list).
    On parse failure, returns dict with parse_error key.
    """
    if not report_path.exists():
        return {"parse_error": f"Report not found: {report_path}"}

    try:
        tree = ET.parse(report_path)
        root = tree.getroot()
    except ET.ParseError as e:
        return {"parse_error": f"Malformed JUnit XML: {e}"}
    except OSError as e:
        return {"parse_error": f"Cannot read report: {e}"}

    # newman uses <testsuites><testsuite><testcase> structure
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    failures = []

    for testsuite in root.iter("testsuite"):
        for k in totals:
            try:
                totals[k] += int(testsuite.get(k, 0))
            except (TypeError, ValueError):
                pass
        for testcase in testsuite.iter("testcase"):
            name = testcase.get("name", "<unknown>")
            classname = testcase.get("classname", "")
            for failure in testcase.findall("failure"):
                failures.append({
                    "name": name,
                    "classname": classname,
                    "type": failure.get("type", ""),
                    "message": (failure.get("message") or "").strip(),
                    "detail": (failure.text or "").strip()[:500],
                })
            for error in testcase.findall("error"):
                failures.append({
                    "name": name,
                    "classname": classname,
                    "type": "error",
                    "message": (error.get("message") or "").strip(),
                    "detail": (error.text or "").strip()[:500],
                })

    passed = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]
    return {
        "total": totals["tests"],
        "passed": max(0, passed),
        "failed": totals["failures"],
        "errored": totals["errors"],
        "skipped": totals["skipped"],
        "failures": failures,
    }


# --- Result persistence ---

def append_to_test_results_yaml(paths: dict, requirement_id: str, summary: dict) -> tuple[bool, str]:
    """Write the requirement's api_tests section into its result bundle.

    Uses a simple append-with-replace approach: if this requirement already has
    an api_tests block, replace it; otherwise append a new block. Idempotent.
    """
    results_path = paths["results_yaml"]
    results_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().isoformat() + "Z"
    new_block_lines = [
        f"  - requirement_id: {requirement_id}",
        f"    timestamp: {timestamp}",
        f"    total: {summary['total']}",
        f"    passed: {summary['passed']}",
        f"    failed: {summary['failed']}",
        f"    errored: {summary['errored']}",
        f"    skipped: {summary['skipped']}",
        f"    exit_code: {summary['newman_exit_code']}",
        f"    status: {summary['status']}",
    ]
    if summary.get("services"):
        new_block_lines.insert(2, f"    services: {', '.join(summary['services'])}")
    new_block = "\n".join(new_block_lines) + "\n"

    existing = ""
    if results_path.exists():
        try:
            existing = results_path.read_text(encoding="utf-8")
        except OSError as e:
            return False, f"Cannot read existing results: {e}"

    # Replace existing block for this requirement_id (idempotency)
    pattern = re.compile(
        r"(  - requirement_id: " + re.escape(requirement_id) + r"\n(?:    .+\n)+)",
        re.MULTILINE,
    )
    if pattern.search(existing):
        updated = pattern.sub(new_block, existing, count=1)
    else:
        # No existing block — append under api_tests:
        if "api_tests:" in existing:
            updated = existing.rstrip() + "\n" + new_block
        else:
            updated = existing.rstrip() + "\n\napi_tests:\n" + new_block

    try:
        results_path.write_text(updated, encoding="utf-8")
    except OSError as e:
        return False, f"Cannot write results: {e}"
    return True, ""


# --- Main orchestration ---

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hard-execute Newman API tests for sw-integration-tester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--requirement-id", required=True,
                        help="Requirement ID (e.g. REQ-20260107-001). "
                        "Used to read the Stage 1 bundle manifest and registered Stage 2 artifacts.")
    parser.add_argument("--service-id",
                        help="Run only one registered service's API collection; default runs all services.")
    parser.add_argument("--project-root", help="Override project root detection")
    parser.add_argument("--no-bail", action="store_true",
                        help="Disable --bail (run all tests even after first failure)")
    parser.add_argument("--timeout-request", type=int, default=10000,
                        help="Per-request timeout in ms (default: 10000)")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    args = parser.parse_args()

    if args.project_root:
        project_root = Path(args.project_root).resolve()
    else:
        project_root = detect_project_root(Path.cwd())

    if args.service_id:
        service_paths = [resolve_paths(args.requirement_id, project_root, args.service_id)]
    else:
        service_paths, err = resolve_all_paths(args.requirement_id, project_root)
        if err:
            result = {"status": "PRECHECK_FAILED", "exit_code": 2, "error": err}
            _emit(result, args.json)
            return 2

    # --- Pre-check: every collection + env file ---
    for paths in service_paths:
        ok, err = pre_check(paths)
        if not ok:
            result = {
                "status": "PRECHECK_FAILED",
                "exit_code": 2,
                "error": err,
                "service_id": paths["service_id"],
                "paths": {k: str(v) for k, v in paths.items() if isinstance(v, Path)},
            }
            _emit(result, args.json)
            return 2

    # --- Pre-check: newman installed ---
    ok, err = check_newman_installed()
    if not ok:
        result = {
            "status": "NEWMAN_MISSING",
            "exit_code": 3,
            "error": err,
        }
        _emit(result, args.json)
        return 3

    # --- Execute Newman for every registered service ---
    service_summaries = []
    for paths in service_paths:
        exit_code, stdout, stderr = run_newman(
            paths,
            bail=not args.no_bail,
            timeout_request_ms=args.timeout_request,
        )
        summary = parse_junit_xml(paths["report"])
        if "parse_error" in summary:
            result = {
                "status": "PARSE_FAILED",
                "exit_code": 5,
                "newman_exit_code": exit_code,
                "service_id": paths["service_id"],
                "error": summary["parse_error"],
                "stderr_tail": stderr[-500:] if stderr else "",
            }
            _emit(result, args.json)
            return 5
        summary["newman_exit_code"] = exit_code
        summary["service_id"] = paths["service_id"]
        service_summaries.append(summary)

    summary = {
        "total": sum(item["total"] for item in service_summaries),
        "passed": sum(item["passed"] for item in service_summaries),
        "failed": sum(item["failed"] for item in service_summaries),
        "errored": sum(item["errored"] for item in service_summaries),
        "skipped": sum(item["skipped"] for item in service_summaries),
        "failures": [failure for item in service_summaries for failure in item.get("failures", [])],
        "services": [item["service_id"] for item in service_summaries],
    }
    if all(item["newman_exit_code"] == 0 for item in service_summaries) and not summary["failed"] and not summary["errored"]:
        summary["status"] = "PASS"
        out_exit = 0
    else:
        summary["status"] = "FAIL"
        out_exit = 4
    summary["newman_exit_code"] = 0 if out_exit == 0 else 4

    # --- Persist to the requirement's test-results.yaml ---
    ok, err = append_to_test_results_yaml(paths, args.requirement_id, summary)
    if not ok:
        # Persistence failure is a warning, not a hard fail
        summary["persistence_warning"] = err

    # --- Final output ---
    summary["report_paths"] = [str(paths["report"]) for paths in service_paths]
    summary["collection_paths"] = [str(paths["collection"]) for paths in service_paths]
    result = {
        "status": summary["status"],
        "exit_code": out_exit,
        "summary": summary,
    }
    _emit(result, args.json)
    return out_exit


def _emit(result: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = result.get("status", "UNKNOWN")
        print(f"=== Newman Runner: {status} ===")
        if "error" in result:
            print(f"Error: {result['error']}")
        if "summary" in result:
            s = result["summary"]
            print(f"Total: {s.get('total', '?')}, "
                  f"Passed: {s.get('passed', '?')}, "
                  f"Failed: {s.get('failed', '?')}, "
                  f"Errored: {s.get('errored', '?')}, "
                  f"Skipped: {s.get('skipped', '?')}")
            if s.get("failures"):
                print(f"\nFailures ({len(s['failures'])}):")
                for f in s["failures"][:10]:
                    print(f"  - [{f.get('type', '?')}] {f.get('name', '?')}: "
                          f"{(f.get('message') or '')[:120]}")
            if s.get("persistence_warning"):
                print(f"\nWARNING: {s['persistence_warning']}")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Internal error: {e}", file=sys.stderr)
        sys.exit(6)
