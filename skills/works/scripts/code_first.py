#!/usr/bin/env python3
"""Evidence gates for the Java/Maven implement-then-test workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import time

from works_core.common import atomic_json, sha
from baseline import (
    changed,
    fingerprints,
    is_test,
    load,
    normalized_production,
    req_id,
    require_test_flags,
    run_command,
    state_paths,
)


def require_targeted_mockito_test(test: Path, testcase: str, command: list[str]) -> dict:
    source = test.read_text(encoding="utf-8", errors="replace")
    if re.search(r"\bSpringBootTest\b", source):
        raise SystemExit("test policy violation: @SpringBootTest is forbidden; use a Mockito unit test")
    if not re.search(r"\bMockito\s*\.|\bmock\s*\(|@Mock\b|@InjectMocks\b", source):
        raise SystemExit("test policy violation: the target test must use Mockito")
    if "#" not in testcase:
        raise SystemExit("test policy violation: --testcase must use Class#method")
    selectors = [part.split("=", 1)[1] for part in command if part.startswith("-Dtest=")]
    if len(selectors) != 1:
        raise SystemExit("test policy violation: command must contain exactly one -Dtest=Class#method selector")
    expected = testcase.rsplit(".", 1)[-1]
    if "#" not in selectors[0] or selectors[0] != expected:
        raise SystemExit(f"test policy violation: -Dtest selector must exactly match {expected}")
    return {"framework": "Mockito", "targeted_selector": selectors[0],
            "spring_boot_test": False, "third_party_policy": "mock"}


def require_contract_testcase(contract_path: Path, req: str, testcase: str) -> list[str]:
    contract = load(contract_path)
    selectors = []
    for row in contract.get("acceptance_commands", []):
        if req not in row.get("covers", []):
            continue
        selectors.extend(
            part.split("=", 1)[1]
            for part in row.get("command", [])
            if isinstance(part, str) and part.startswith("-Dtest=")
        )
    expected = testcase.rsplit(".", 1)[-1]
    if not selectors:
        raise SystemExit(f"test policy violation: contract has no -Dtest selector covering {req}")
    if expected not in selectors:
        raise SystemExit(
            f"test policy violation: testcase {expected} does not match contract selectors for "
            f"{req}: {selectors!r}"
        )
    return selectors


def cmd_implement(args: argparse.Namespace) -> int:
    req = req_id(args.req)
    state, root, _ = state_paths(args)
    checkpoint_file = state / "checkpoint.json"
    checkpoint = load(checkpoint_file)
    production = fingerprints(root, production=True)
    production_changes = changed(normalized_production(checkpoint["production"]), production)
    if not production_changes:
        raise SystemExit("invalid implementation: production did not change from the previous checkpoint")
    slice_dir = state / "slices" / req
    slice_dir.mkdir(parents=True, exist_ok=True)
    if (slice_dir / "implementation.json").exists():
        raise SystemExit("implementation evidence already exists for this requirement")
    atomic_json(slice_dir / "implementation.json", {
        "req": req,
        "production_before": checkpoint["production"],
        "production": production,
        "changed": production_changes,
        "checkpoint_sequence": checkpoint["sequence"],
        "previous_req": checkpoint["previous_req"],
        "checkpoint_sha256": sha(checkpoint_file),
        "recorded_at": time.time(),
    })
    print(slice_dir / "implementation.json")
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    req = req_id(args.req)
    state, root, _ = state_paths(args)
    require_test_flags(root, args.command)
    slice_dir = state / "slices" / req
    implementation_file = slice_dir / "implementation.json"
    implementation = load(implementation_file)
    if (slice_dir / "test.json").exists():
        raise SystemExit("test evidence already exists for this requirement")
    test = (root / args.test_file).resolve()
    if not test.is_relative_to(root) or not test.is_file() or not is_test(test.relative_to(root).as_posix()):
        raise SystemExit("--test-file must name an existing Maven test file inside the project")
    contract_selectors = require_contract_testcase(Path(args.contract), args.contract_req, args.testcase)
    test_policy = require_targeted_mockito_test(test, args.testcase, args.command)
    test_policy["contract_req"] = args.contract_req
    test_policy["contract_selectors"] = contract_selectors
    production = fingerprints(root, production=True)
    if production != implementation["production"]:
        raise SystemExit("production changed after implementation checkpoint")
    log = slice_dir / "test.log"
    code, junit = run_command(root, args.command, log, slice_dir / "test-reports", args.testcase)
    target = junit["target"]
    if code != 0 or target["executed"] < 1 or target["failures"] != 0 or target["errors"] != 0:
        raise SystemExit(
            f"invalid test evidence for {args.testcase}: exit={code}, executed={target['executed']}, "
            f"failures={target['failures']}, errors={target['errors']}"
        )
    atomic_json(slice_dir / "test.json", {
        "req": req,
        "implementation_sha256": sha(implementation_file),
        "test_file": test.relative_to(root).as_posix(),
        "test_sha256": sha(test),
        "testcase": args.testcase,
        "command": args.command,
        "test_policy": test_policy,
        "exit": code,
        "junit": junit,
        "log": str(log),
        "log_sha256": sha(log),
        "recorded_at": time.time(),
    })
    atomic_json(state / "checkpoint.json", {
        "sequence": implementation["checkpoint_sequence"] + 1,
        "production": production,
        "previous_req": req,
    })
    print(slice_dir / "test.json")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    state, root, baseline = state_paths(args)
    failures = []
    baseline_file = state / "baseline.json"
    baseline_lock = state / "baseline.sha256"
    if not baseline_lock.exists() or baseline_lock.read_text().strip() != sha(baseline_file):
        failures.append("baseline: hash lock mismatch")
    preflight = load(state / "preflight.json")
    if not preflight.get("passed"):
        failures.append("preflight: baseline probe did not pass")
    expected_production = normalized_production(baseline["production"])
    previous_req = None
    verification_runs = []
    for sequence, raw_req in enumerate(args.req):
        req = req_id(raw_req)
        slice_dir = state / "slices" / req
        try:
            implementation = load(slice_dir / "implementation.json")
            test = load(slice_dir / "test.json")
            if test["implementation_sha256"] != sha(slice_dir / "implementation.json"):
                failures.append(f"{req}: implementation evidence changed after test")
            if test.get("exit") != 0 or test["junit"]["target"]["executed"] < 1:
                failures.append(f"{req}: recorded test did not execute and pass")
            if implementation["recorded_at"] >= test["recorded_at"]:
                failures.append(f"{req}: evidence order is not implementation before test")
            if not Path(test["log"]).is_file() or sha(Path(test["log"])) != test["log_sha256"]:
                failures.append(f"{req}: test log hash mismatch")
            for report in test["junit"]["files"]:
                report_path = Path(report["path"])
                if not report_path.is_file() or sha(report_path) != report["sha256"]:
                    failures.append(f"{req}: report hash mismatch: {report_path}")
            test_file = root / test["test_file"]
            if not test_file.is_file() or sha(test_file) != test["test_sha256"]:
                failures.append(f"{req}: test evidence changed or disappeared")
            if implementation["checkpoint_sequence"] != sequence or implementation["previous_req"] != previous_req:
                failures.append(f"{req}: checkpoint sequence/predecessor mismatch")
            before = normalized_production(implementation["production_before"])
            after = normalized_production(implementation["production"])
            if before != expected_production or after == before:
                failures.append(f"{req}: invalid implementation production transition")
            verify_log = slice_dir / "verify.log"
            code, junit = run_command(root, test["command"], verify_log,
                                      slice_dir / "verify-reports", test["testcase"])
            target = junit["target"]
            verification_runs.append({"req": req, "command": test["command"], "exit": code,
                                      "target": target, "log": str(verify_log),
                                      "log_sha256": sha(verify_log), "reports": junit["files"]})
            if code != 0 or target["executed"] < 1 or target["failures"] != 0 or target["errors"] != 0:
                failures.append(f"{req}: final target testcase did not execute and pass")
            expected_production = after
            previous_req = req
        except (OSError, SystemExit, KeyError, json.JSONDecodeError) as exc:
            failures.append(f"{req}: incomplete evidence ({exc})")
    checkpoint = load(state / "checkpoint.json")
    if (normalized_production(checkpoint["production"]) != expected_production
            or checkpoint["previous_req"] != previous_req):
        failures.append("checkpoint: final production/predecessor mismatch")
    if fingerprints(root, production=True) != expected_production:
        failures.append("worktree: production changed after the final test checkpoint")
    result = {"reqs": args.req, "passed": not failures, "failures": failures,
              "verification_runs": verification_runs, "verified_at": time.time()}
    atomic_json(state / "code-first-verify.json", result)
    if failures:
        raise SystemExit("; ".join(failures))
    print(state / "code-first-verify.json")
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    sub = root.add_subparsers(dest="action", required=True)
    implement = sub.add_parser("implement")
    implement.add_argument("--state-dir", required=True)
    implement.add_argument("--req", required=True)
    implement.set_defaults(func=cmd_implement)
    test = sub.add_parser("test")
    test.add_argument("--state-dir", required=True)
    test.add_argument("--req", required=True)
    test.add_argument("--test-file", required=True)
    test.add_argument("--testcase", required=True)
    test.add_argument("--contract", required=True)
    test.add_argument("--contract-req", required=True)
    test.add_argument("command", nargs=argparse.REMAINDER)
    test.set_defaults(func=cmd_test)
    verify = sub.add_parser("verify")
    verify.add_argument("--state-dir", required=True)
    verify.add_argument("--req", action="append", default=[])
    verify.set_defaults(func=cmd_verify)
    return root


if __name__ == "__main__":
    ns = parser().parse_args()
    if getattr(ns, "command", [])[:1] == ["--"]:
        ns.command = ns.command[1:]
    raise SystemExit(ns.func(ns))
