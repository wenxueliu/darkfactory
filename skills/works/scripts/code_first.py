#!/usr/bin/env python3
"""Evidence gates for the Java/Maven implement-then-test workflow."""

from __future__ import annotations

import argparse
from collections import Counter
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


PERSISTENCE_TYPE = re.compile(r"[A-Z][A-Za-z0-9_]*(?:Mapper|Dao|DAO|Repository)")
DIRECT_DATA_TYPE = {"JdbcTemplate", "NamedParameterJdbcTemplate", "EntityManager", "SqlSession",
                    "DSLContext", "RedisTemplate", "MongoTemplate"}


def java_code_only(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", " ", source, flags=re.DOTALL)
    source = re.sub(r"//[^\n]*", " ", source)
    source = re.sub(r'"(?:\\.|[^"\\])*"', '""', source)
    return re.sub(r"'(?:\\.|[^'\\])*'", "''", source)


def require_targeted_test(test: Path, testcase: str, command: list[str]) -> dict:
    source = test.read_text(encoding="utf-8", errors="replace")
    if re.search(r"\bSpringBootTest\b", source):
        raise SystemExit("test policy violation: @SpringBootTest is forbidden; use a focused test")
    if "#" not in testcase:
        raise SystemExit("test policy violation: --testcase must use Class#method")
    lifecycle = {"test", "verify", "package"} & set(command)
    if lifecycle != {"test"}:
        raise SystemExit("test policy violation: Maven lifecycle must be exactly test")
    selectors = [part.split("=", 1)[1] for part in command if part.startswith("-Dtest=")]
    if len(selectors) != 1:
        raise SystemExit("test policy violation: command must contain exactly one -Dtest=Class#method selector")
    expected = testcase.rsplit(".", 1)[-1]
    if "#" not in selectors[0] or selectors[0] != expected:
        raise SystemExit(f"test policy violation: -Dtest selector must exactly match {expected}")
    uses_mockito = bool(re.search(r"\bMockito\s*\.|\bmock\s*\(|@Mock\b|@InjectMocks\b", source))
    return {"framework": "Mockito" if uses_mockito else "JUnit", "targeted_selector": selectors[0],
            "spring_boot_test": False, "third_party_policy": "isolate-if-present"}


# Backward-compatible name for existing integrations.
require_targeted_mockito_test = require_targeted_test


def resolve_contract_test_command(contract_path: Path, req: str, testcase: str) -> list[str]:
    contract = load(contract_path)
    expected = testcase.rsplit(".", 1)[-1]
    matches = []
    for row in contract.get("acceptance_commands", []):
        if req not in row.get("covers", []):
            continue
        selectors = [
            part.split("=", 1)[1]
            for part in row.get("command", [])
            if isinstance(part, str) and part.startswith("-Dtest=")
        ]
        if expected in selectors:
            matches.append(row.get("command"))
    if len(matches) != 1 or not isinstance(matches[0], list):
        raise SystemExit(
            f"test policy violation: testcase {expected} must resolve to exactly one contract "
            f"acceptance command for {req}"
        )
    return matches[0]


def invokes_symbol(source: str, symbol: str) -> bool:
    for match in re.finditer(rf"\b{re.escape(symbol)}\s*\(", source):
        line_prefix = source[source.rfind("\n", 0, match.start()) + 1:match.start()]
        declaration_prefix = re.split(r"[{};]", line_prefix)[-1]
        stripped = declaration_prefix.strip()
        if stripped.endswith(".") or not stripped:
            return True
        words = re.findall(r"[A-Za-z_$][\w$]*", stripped)
        if words and words[-1] in {"return", "throw", "yield", "case"}:
            return True
        if not re.fullmatch(
            r"\s*(?:(?:public|protected|private|static|final|abstract|synchronized|native|default)\s+)*"
            r"(?:<[^>]+>\s*)?[\w$.,<>?\[\] ]+\s+",
            declaration_prefix,
        ):
            return True
    return False


def persistence_invocations(root: Path) -> dict[str, int]:
    calls: Counter[str] = Counter()
    for path in root.rglob("*.java"):
        if not path.is_file() or is_test(path.relative_to(root).as_posix()):
            continue
        source = java_code_only(path.read_text(encoding="utf-8", errors="replace"))
        variables = {}
        for type_name, variable in re.findall(
            r"\b([A-Z][\w$]*(?:Mapper|Dao|DAO|Repository)|JdbcTemplate|"
            r"NamedParameterJdbcTemplate|EntityManager|SqlSession|DSLContext|RedisTemplate|MongoTemplate)"
            r"(?:\s*<[^;=()]+>)?\s+([a-z_$][\w$]*)\b",
            source,
        ):
            if PERSISTENCE_TYPE.fullmatch(type_name) or type_name in DIRECT_DATA_TYPE:
                variables[variable] = type_name
        rel = path.relative_to(root).as_posix()
        for variable, type_name in variables.items():
            for method in re.findall(rf"\b{re.escape(variable)}\s*\.\s*([A-Za-z_$][\w$]*)\s*\(", source):
                calls[f"{rel}|{type_name}.{method}"] += 1
    return dict(sorted(calls.items()))


def cmd_reuse_init(args: argparse.Namespace) -> int:
    state, root, _ = state_paths(args)
    output = state / "reuse-baseline.json"
    atomic_json(output, {"persistence_invocations": persistence_invocations(root),
                         "recorded_at": time.time()})
    print(output)
    return 0


def require_reuse_decision(contract_path: Path, req: str, root: Path,
                           production_changes: list[str], reuse_baseline: Path) -> dict:
    contract = load(contract_path)
    row = next((item for item in contract.get("requirements", []) if item.get("id") == req), None)
    decision = row.get("implementation", {}).get("reuse") if isinstance(row, dict) else None
    if not isinstance(decision, dict):
        raise SystemExit(f"reuse policy violation: missing reuse_decision for {req}")
    target = decision.get("target", {})
    target_path = target.get("path")
    target_symbol = target.get("symbol")
    if not isinstance(target_path, str) or not isinstance(target_symbol, str):
        raise SystemExit(f"reuse policy violation: invalid reuse target for {req}")
    candidate = (root / target_path).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise SystemExit(f"reuse policy violation: reuse target no longer exists for {req}: {target_path}")
    source = candidate.read_text(encoding="utf-8", errors="replace")
    if not re.search(rf"\b{re.escape(target_symbol)}\b", source):
        raise SystemExit(f"reuse policy violation: reuse target is stale for {req}: {target_symbol}")
    if decision.get("kind") in {"existing_method", "service_api"}:
        entrypoint = (row.get("implementation", {}).get("entrypoint", {})
                      if isinstance(row, dict) else {})
        modifies_selected_method = (
            decision.get("kind") == "existing_method"
            and entrypoint == target
            and target_path in production_changes
        )
        changed_sources = java_code_only("\n".join(
            (root / path).read_text(encoding="utf-8", errors="replace")
            for path in production_changes
            if (root / path).is_file()
        ))
        if not modifies_selected_method and not invokes_symbol(changed_sources, target_symbol):
            raise SystemExit(
                f"reuse policy violation: implementation does not use selected "
                f"{decision['kind']} target {target_symbol} for {req}"
            )
        before = load(reuse_baseline).get("persistence_invocations", {})
        current = persistence_invocations(root)
        introduced = {
            key: count - before.get(key, 0)
            for key, count in current.items()
            if count > before.get(key, 0)
        }
        if introduced:
            raise SystemExit(
                f"reuse policy violation: {decision['kind']} decision forbids new "
                f"Mapper/Repository calls for {req}: {introduced!r}"
            )
    return decision


def require_implemented_entrypoint(contract_path: Path, req: str, root: Path) -> dict:
    contract = load(contract_path)
    row = next((item for item in contract.get("requirements", []) if item.get("id") == req), None)
    target = row.get("implementation", {}).get("entrypoint") if isinstance(row, dict) else None
    if not isinstance(target, dict):
        raise SystemExit(f"entrypoint policy violation: missing entrypoint for {req}")
    path_value, symbol = target.get("path"), target.get("symbol")
    if not isinstance(path_value, str) or not isinstance(symbol, str):
        raise SystemExit(f"entrypoint policy violation: invalid entrypoint for {req}")
    candidate = (root / path_value).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise SystemExit(f"entrypoint policy violation: implemented entrypoint does not exist for {req}: {path_value}")
    source = candidate.read_text(encoding="utf-8", errors="replace")
    if not re.search(rf"\b{re.escape(symbol)}\b", source):
        raise SystemExit(f"entrypoint policy violation: implemented symbol does not exist for {req}: {symbol}")
    return target


def cmd_implement(args: argparse.Namespace) -> int:
    req = req_id(args.req)
    state, root, _ = state_paths(args)
    checkpoint_file = state / "checkpoint.json"
    checkpoint = load(checkpoint_file)
    production = fingerprints(root, production=True)
    production_changes = changed(normalized_production(checkpoint["production"]), production)
    if not production_changes:
        raise SystemExit("invalid implementation: production did not change from the previous checkpoint")
    reuse_decision = require_reuse_decision(
        Path(args.contract), args.contract_req, root, production_changes,
        state / "reuse-baseline.json",
    )
    entrypoint = require_implemented_entrypoint(Path(args.contract), args.contract_req, root)
    slice_dir = state / "slices" / req
    slice_dir.mkdir(parents=True, exist_ok=True)
    if (slice_dir / "implementation.json").exists():
        raise SystemExit("implementation evidence already exists for this requirement")
    atomic_json(slice_dir / "implementation.json", {
        "req": req,
        "production_before": checkpoint["production"],
        "production": production,
        "changed": production_changes,
        "contract_req": args.contract_req,
        "reuse_decision": reuse_decision,
        "entrypoint": entrypoint,
        "requirement_contract_sha256": sha(Path(args.contract)),
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
    contract_command = resolve_contract_test_command(Path(args.contract), args.contract_req, args.testcase)
    legacy_command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if legacy_command and legacy_command != contract_command:
        raise SystemExit(
            "test policy violation: trailing Maven command differs from the requirement contract; "
            "omit it and let Works use the canonical contract argv"
        )
    command = contract_command
    require_test_flags(root, command)
    slice_dir = state / "slices" / req
    implementation_file = slice_dir / "implementation.json"
    implementation = load(implementation_file)
    if (slice_dir / "test.json").exists():
        raise SystemExit("test evidence already exists for this requirement")
    test = (root / args.test_file).resolve()
    if not test.is_relative_to(root) or not test.is_file() or not is_test(test.relative_to(root).as_posix()):
        raise SystemExit("--test-file must name an existing Maven test file inside the project")
    contract = load(Path(args.contract))
    contract_row = next((item for item in contract.get("requirements", [])
                         if item.get("id") == args.contract_req), None)
    planned_file = (contract_row.get("implementation", {}).get("test_target", {}).get("file")
                    if isinstance(contract_row, dict) else None)
    if planned_file and test.relative_to(root).as_posix() != planned_file:
        raise SystemExit("test policy violation: --test-file differs from contract test target")
    test_policy = require_targeted_test(test, args.testcase, command)
    test_policy["contract_req"] = args.contract_req
    test_policy["contract_command_source"] = "requirement-contract.json"
    production = fingerprints(root, production=True)
    if production != implementation["production"]:
        raise SystemExit("production changed after implementation checkpoint")
    log = slice_dir / "test.log"
    code, junit = run_command(root, command, log, slice_dir / "test-reports", args.testcase)
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
        "command": command,
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
    atomic_json(state / "reuse-baseline.json", {
        "persistence_invocations": persistence_invocations(root), "recorded_at": time.time(),
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
            if req in getattr(args, "skipped", []):
                skipped = load(state / "skipped" / f"{req}.json")
                if skipped.get("status") != "SKIPPED" or len(skipped.get("failures", [])) != 3:
                    failures.append(f"{req}: invalid skipped evidence")
                if skipped.get("implementation_sha256") != sha(slice_dir / "implementation.json"):
                    failures.append(f"{req}: skipped implementation evidence changed")
                before = normalized_production(implementation["production_before"])
                after = normalized_production(implementation["production"])
                if before != expected_production or after == before:
                    failures.append(f"{req}: invalid skipped production transition")
                if (implementation["checkpoint_sequence"] != sequence
                        or implementation["previous_req"] != previous_req):
                    failures.append(f"{req}: skipped checkpoint sequence/predecessor mismatch")
                expected_production = after
                previous_req = req
                continue
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
            if not getattr(args, "no_replay", False):
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
    implement.add_argument("--contract", required=True)
    implement.add_argument("--contract-req", required=True)
    implement.set_defaults(func=cmd_implement)
    reuse = sub.add_parser("reuse-init")
    reuse.add_argument("--state-dir", required=True)
    reuse.set_defaults(func=cmd_reuse_init)
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
    verify.add_argument("--skipped", action="append", default=[])
    verify.add_argument("--no-replay", action="store_true")
    verify.set_defaults(func=cmd_verify)
    return root


if __name__ == "__main__":
    ns = parser().parse_args()
    if getattr(ns, "command", [])[:1] == ["--"]:
        ns.command = ns.command[1:]
    raise SystemExit(ns.func(ns))
