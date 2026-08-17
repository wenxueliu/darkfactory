#!/usr/bin/env python3
"""Evidence gate for test-first slices in an existing Git/Maven worktree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


IGNORED_PARTS = {".git", ".planning", "target", "build", ".gradle", "node_modules"}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, path)


def sync_plan(state: Path, event: str, req: str | None = None) -> None:
    """Make the durable plan reflect every successful TDD transition."""
    plan = state.resolve().parent
    if not (plan / "task_plan.md").is_file():
        return
    command = [
        sys.executable,
        str(Path(__file__).with_name("works_plan_gate.py")),
        "sync",
        "--state-dir",
        str(state),
        "--event",
        event,
    ]
    if req:
        command.extend(["--current-req", req])
    subprocess.run(command, check=True)


def service_boundary(action: str, state: Path, root: Path | None = None) -> None:
    command = [sys.executable, str(Path(__file__).with_name("service_boundary.py")), action]
    if action == "init":
        command.extend(["--project-root", str(root), "--state-dir", str(state)])
    else:
        command.extend(["--state-dir", str(state)])
    subprocess.run(command, check=True)


def is_test(rel: str) -> bool:
    p = rel.replace("\\", "/")
    name = Path(p).name.lower()
    return (
        "/src/test/" in f"/{p}"
        or p.startswith("src/test/")
        or "/test/" in f"/{p}"
        or name.endswith(("test.java", "tests.java", "it.java", "test.kt", "spec.groovy"))
    )


def fingerprints(root: Path, production: bool) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(root).as_posix()
        if any(part in IGNORED_PARTS for part in path.relative_to(root).parts):
            continue
        if is_test(rel) == production:
            continue
        result[rel] = sha(path)
    return result


def load(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"missing evidence: {path}")
    return json.loads(path.read_text())


def state_paths(args: argparse.Namespace) -> tuple[Path, Path, dict]:
    state = Path(args.state_dir).resolve()
    baseline = load(state / "baseline.json")
    root = Path(baseline["project_root"])
    return state, root, baseline


def changed(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))


def report_snapshot(root: Path) -> dict[str, tuple[str, int]]:
    found: dict[str, tuple[str, int]] = {}
    for pattern in ("**/target/surefire-reports/TEST-*.xml", "**/target/failsafe-reports/TEST-*.xml"):
        for path in root.glob(pattern):
            found[str(path.resolve())] = (sha(path), path.stat().st_mtime_ns)
    return found


def testcase_matches(classname: str, name: str, selector: str) -> bool:
    short = classname.rsplit(".", 1)[-1]
    return selector in {name, f"{short}#{name}", f"{classname}#{name}"}


def report_summary(paths: list[Path], testcase: str) -> dict:
    summary = {
        "tests": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "files": [],
        "target": {"selector": testcase, "executed": 0, "failures": 0, "errors": 0},
    }
    for path in paths:
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError):
            continue
        suites = [root] if root.tag.endswith("testsuite") else list(root.iter("testsuite"))
        for suite in suites:
            for key in ("tests", "failures", "errors", "skipped"):
                summary[key] += int(float(suite.attrib.get(key, 0)))
        for case in root.iter("testcase"):
            classname = case.attrib.get("classname", "")
            name = case.attrib.get("name", "")
            if testcase_matches(classname, name, testcase):
                summary["target"]["executed"] += 1
                summary["target"]["failures"] += len(case.findall("failure"))
                summary["target"]["errors"] += len(case.findall("error"))
        summary["files"].append({"path": str(path), "sha256": sha(path)})
    return summary


def run_command(root: Path, command: list[str], log: Path, report_dir: Path, testcase: str) -> tuple[int, dict]:
    if not command:
        raise SystemExit("missing command after --")
    before = report_snapshot(root)
    proc = subprocess.run(command, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(proc.stdout)
    after = report_snapshot(root)
    fresh = [Path(path) for path, stamp in after.items() if before.get(path) != stamp]
    if report_dir.exists():
        shutil.rmtree(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for index, source in enumerate(fresh):
        target = report_dir / f"{index:03d}-{source.name}"
        shutil.copy2(source, target)
        copied.append(target)
    return proc.returncode, report_summary(copied, testcase)


def req_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", value):
        raise SystemExit("invalid --req; use 1-64 letters, digits, dot, underscore or hyphen")
    return value


def baseline_digest(baseline: dict) -> str:
    return hashlib.sha256(json.dumps(baseline["production"], sort_keys=True).encode()).hexdigest()


def required_test_flags(root: Path) -> list[str]:
    names = {"skipTests", "maven.test.skip"}
    for pom in root.rglob("pom.xml"):
        if any(part in IGNORED_PARTS for part in pom.relative_to(root).parts):
            continue
        try:
            tree = ET.parse(pom)
        except (ET.ParseError, OSError):
            continue
        for element in tree.iter():
            name = element.tag.rsplit("}", 1)[-1]
            value = (element.text or "").strip().lower()
            lowered = name.lower()
            if value == "true" and (("skip" in lowered and "test" in lowered) or name in {"skipTests"}):
                names.add(name)
            if value == "true" and name == "skip":
                names.add("skipTests")
    return sorted(f"-D{name}=false" for name in names)


def require_test_flags(root: Path, command: list[str]) -> list[str]:
    required = required_test_flags(root)
    missing = [flag for flag in required if flag not in command]
    if missing:
        raise SystemExit("test command must explicitly override skip configuration: " + " ".join(missing))
    return required


def testcase_body(source: str, selector: str) -> str:
    name = selector.rsplit("#", 1)[-1]
    pattern = re.compile(rf"(?:\bfun\s+)?\b{re.escape(name)}\s*\([^)]*\)[^{{;=]*\{{")
    match = pattern.search(source)
    if not match:
        raise SystemExit(f"cannot locate brace-delimited testcase method body: {selector}")
    start = source.find("{", match.start())
    depth = 0
    quote = None
    escaped = False
    line_comment = False
    block_comment = False
    i = start
    while i < len(source):
        ch = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""
        if line_comment:
            if ch == "\n":
                line_comment = False
        elif block_comment:
            if ch == "*" and nxt == "/":
                block_comment = False
                i += 1
        elif quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
        elif ch == "/" and nxt == "/":
            line_comment = True
            i += 1
        elif ch == "/" and nxt == "*":
            block_comment = True
            i += 1
        elif ch in {'"', "'"}:
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[match.start() : i + 1]
        i += 1
    raise SystemExit(f"unterminated testcase method body: {selector}")


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.project_root).resolve()
    state = Path(args.state_dir).resolve()
    if (state / "baseline.json").exists():
        raise SystemExit("TDD baseline already exists; init is immutable for this plan")
    if not (root / ".git").exists() and subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode:
        raise SystemExit("project root is not inside a Git worktree")
    status = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain=v2", "--untracked-files=all"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout
    data = {
            "version": 1,
            "project_root": str(root),
            "created_at": time.time(),
            "git_status": status.splitlines(),
            "production": fingerprints(root, production=True),
            "tests": fingerprints(root, production=False),
        }
    atomic_json(state / "baseline.json", data)
    (state / "baseline.sha256").write_text(hashlib.sha256((state / "baseline.json").read_bytes()).hexdigest() + "\n")
    atomic_json(state / "checkpoint.json", {"sequence": 0, "production": data["production"], "previous_req": None})
    service_boundary("init", state, root)
    sync_plan(state, "tdd_init")
    print(state / "baseline.json")
    return 0


def cmd_red(args: argparse.Namespace) -> int:
    req = req_id(args.req)
    state, root, baseline = state_paths(args)
    preflight = load(state / "preflight.json")
    if not preflight.get("passed"):
        raise SystemExit("Maven test preflight has not passed")
    require_test_flags(root, args.command)
    test = (root / args.test_file).resolve()
    if not test.is_relative_to(root) or not test.exists() or not is_test(test.relative_to(root).as_posix()):
        raise SystemExit("--test-file must name an existing test file inside the project")
    checkpoint_file = state / "checkpoint.json"
    checkpoint = load(checkpoint_file)
    prod_now = fingerprints(root, production=True)
    prod_changes = changed(checkpoint["production"], prod_now)
    if prod_changes:
        raise SystemExit("invalid Red: production differs from latest Green checkpoint: " + ", ".join(prod_changes[:20]))
    test_rel = test.relative_to(root).as_posix()
    if baseline["tests"].get(test_rel) == sha(test):
        raise SystemExit("invalid Red: target test file has not changed since baseline")
    slice_dir = state / "slices" / req
    if (slice_dir / "red.json").exists():
        raise SystemExit("Red evidence already exists for this requirement; use a new Req/slice ID")
    log = slice_dir / "red.log"
    code, junit = run_command(root, args.command, log, slice_dir / "red-reports", args.testcase)
    target = junit["target"]
    if code == 0 or target["executed"] < 1 or target["failures"] < 1 or target["errors"] != 0:
        raise SystemExit(
            f"invalid Red for {args.testcase}: exit={code}, executed={target['executed']}, "
            f"failures={target['failures']}, errors={target['errors']}"
        )
    checkpoint_copy = slice_dir / "checkpoint-before.json"
    atomic_json(checkpoint_copy, checkpoint)
    evidence = {
        "req": req,
        "testcase": args.testcase,
        "test_file": test_rel,
        "test_sha256": sha(test),
        "command": args.command,
        "exit": code,
        "junit": junit,
        "log": str(log),
        "log_sha256": sha(log),
        "production_baseline_sha256": baseline_digest(baseline),
        "checkpoint_sha256": sha(checkpoint_file),
        "checkpoint_copy": str(checkpoint_copy),
        "checkpoint_copy_sha256": sha(checkpoint_copy),
        "checkpoint_sequence": checkpoint["sequence"],
        "previous_req": checkpoint["previous_req"],
        "production_before": prod_now,
        "recorded_at": time.time(),
    }
    atomic_json(slice_dir / "red.json", evidence)
    sync_plan(state, "red_pass", req)
    print(slice_dir / "red.json")
    return 0


def cmd_green(args: argparse.Namespace) -> int:
    req = req_id(args.req)
    state, root, _ = state_paths(args)
    require_test_flags(root, args.command)
    slice_dir = state / "slices" / req
    if (slice_dir / "green.json").exists():
        raise SystemExit("Green evidence already exists for this requirement")
    red = load(slice_dir / "red.json")
    test = root / red["test_file"]
    if not test.exists() or sha(test) != red["test_sha256"]:
        raise SystemExit("invalid Green: Red test changed; discard this slice and establish a new Red")
    if args.command != red["command"]:
        raise SystemExit("invalid Green: command must exactly match the Red command")
    checkpoint_file = state / "checkpoint.json"
    if sha(checkpoint_file) != red["checkpoint_sha256"]:
        raise SystemExit("invalid Green: slice checkpoint changed after Red")
    production = fingerprints(root, production=True)
    if production == red["production_before"]:
        raise SystemExit("invalid Green: production did not change from this slice's Red checkpoint")
    service_boundary("verify", state)
    log = slice_dir / "green.log"
    code, junit = run_command(root, args.command, log, slice_dir / "green-reports", red["testcase"])
    target = junit["target"]
    if code != 0 or target["executed"] < 1 or target["failures"] != 0 or target["errors"] != 0:
        raise SystemExit(
            f"invalid Green for {red['testcase']}: exit={code}, executed={target['executed']}, "
            f"failures={target['failures']}, errors={target['errors']}"
        )
    body = testcase_body(test.read_text(), red["testcase"])
    body_file = slice_dir / "testcase-at-green.txt"
    body_file.write_text(body)
    atomic_json(
        slice_dir / "green.json",
        {
            "req": req,
            "red_sha256": sha(slice_dir / "red.json"),
            "test_file": red["test_file"],
            "test_sha256": red["test_sha256"],
            "testcase_body": str(body_file),
            "testcase_body_sha256": sha(body_file),
            "command": args.command,
            "exit": code,
            "junit": junit,
            "log": str(log),
            "log_sha256": sha(log),
            "production": production,
            "recorded_at": time.time(),
        },
    )
    atomic_json(
        state / "checkpoint.json",
        {"sequence": red["checkpoint_sequence"] + 1, "production": production, "previous_req": req},
    )
    sync_plan(state, "green_pass")
    print(slice_dir / "green.json")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    state, root, baseline = state_paths(args)
    preflight = load(state / "preflight.json")
    failures = []
    baseline_file = state / "baseline.json"
    baseline_lock = state / "baseline.sha256"
    if not baseline_lock.exists() or baseline_lock.read_text().strip() != sha(baseline_file):
        failures.append("baseline: hash lock mismatch")
    if not preflight.get("passed"):
        failures.append("preflight: Maven tests were not proven executable")
    expected_production = baseline["production"]
    previous_req = None
    verification_runs = []
    for sequence, raw_req in enumerate(args.req):
        req = req_id(raw_req)
        slice_dir = state / "slices" / req
        try:
            red = load(slice_dir / "red.json")
            green = load(slice_dir / "green.json")
            test = root / red["test_file"]
            if green["red_sha256"] != sha(slice_dir / "red.json"):
                failures.append(f"{req}: Red evidence changed after Green")
            body_file = Path(green["testcase_body"])
            if not body_file.exists() or sha(body_file) != green["testcase_body_sha256"]:
                failures.append(f"{req}: Green testcase snapshot changed or disappeared")
            elif not test.exists() or testcase_body(test.read_text(), red["testcase"]) != body_file.read_text():
                failures.append(f"{req}: established testcase method body changed")
            if green["command"] != red["command"]:
                failures.append(f"{req}: Red/Green commands differ")
            if red["production_baseline_sha256"] != baseline_digest(baseline):
                failures.append(f"{req}: baseline production hash mismatch")
            checkpoint_copy = Path(red["checkpoint_copy"])
            if not checkpoint_copy.exists() or sha(checkpoint_copy) != red["checkpoint_copy_sha256"]:
                failures.append(f"{req}: checkpoint evidence hash mismatch")
            else:
                checkpoint_data = load(checkpoint_copy)
                if checkpoint_data["production"] != red["production_before"]:
                    failures.append(f"{req}: checkpoint evidence production mismatch")
            if red["exit"] == 0 or red["junit"]["target"]["failures"] < 1 or red["junit"]["target"]["errors"] != 0:
                failures.append(f"{req}: invalid Red fields")
            if green["exit"] != 0 or green["junit"]["target"]["executed"] < 1 or green["junit"]["target"]["failures"] != 0:
                failures.append(f"{req}: invalid Green fields")
            if sha(Path(red["log"])) != red["log_sha256"] or sha(Path(green["log"])) != green["log_sha256"]:
                failures.append(f"{req}: log hash mismatch")
            for phase in (red, green):
                for report in phase["junit"]["files"]:
                    path = Path(report["path"])
                    if not path.exists() or sha(path) != report["sha256"]:
                        failures.append(f"{req}: report hash mismatch: {path}")
            if red["recorded_at"] >= green["recorded_at"]:
                failures.append(f"{req}: evidence order is not Red before Green")
            if red["checkpoint_sequence"] != sequence or red["previous_req"] != previous_req:
                failures.append(f"{req}: checkpoint sequence/predecessor mismatch")
            if red["production_before"] != expected_production:
                failures.append(f"{req}: Red production checkpoint does not follow previous Green")
            if green["production"] == red["production_before"]:
                failures.append(f"{req}: Green has no production change")
            verify_log = slice_dir / "verify.log"
            code, junit = run_command(
                root,
                red["command"],
                verify_log,
                slice_dir / "verify-reports",
                red["testcase"],
            )
            target = junit["target"]
            verification_runs.append(
                {
                    "req": req,
                    "command": red["command"],
                    "exit": code,
                    "target": target,
                    "log": str(verify_log),
                    "log_sha256": sha(verify_log),
                    "reports": junit["files"],
                }
            )
            if code != 0 or target["executed"] < 1 or target["failures"] != 0 or target["errors"] != 0:
                failures.append(f"{req}: final target testcase did not execute and pass")
            expected_production = green["production"]
            previous_req = req
        except (SystemExit, KeyError, json.JSONDecodeError) as exc:
            failures.append(f"{req}: incomplete evidence ({exc})")
    checkpoint = load(state / "checkpoint.json")
    if checkpoint["production"] != expected_production or checkpoint["previous_req"] != previous_req:
        failures.append("checkpoint: final production/predecessor mismatch")
    if fingerprints(root, production=True) != expected_production:
        failures.append("worktree: production changed after the final Green checkpoint")
    result = {
        "reqs": args.req,
        "passed": not failures,
        "failures": failures,
        "verification_runs": verification_runs,
        "verified_at": time.time(),
    }
    atomic_json(state / "tdd-verify.json", result)
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    sync_plan(state, "tdd_verify_pass")
    print(state / "tdd-verify.json")
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    state, root, _ = state_paths(args)
    required = require_test_flags(root, args.command)
    evidence = state / "preflight"
    log = evidence / "probe.log"
    code, junit = run_command(root, args.command, log, evidence / "reports", args.testcase)
    target = junit["target"]
    passed = code == 0 and target["executed"] >= 1 and target["failures"] == 0 and target["errors"] == 0
    result = {
        "passed": passed,
        "testcase": args.testcase,
        "command": args.command,
        "required_skip_overrides": required,
        "exit": code,
        "junit": junit,
        "log": str(log),
        "log_sha256": sha(log),
        "recorded_at": time.time(),
    }
    atomic_json(state / "preflight.json", result)
    if not passed:
        raise SystemExit(
            f"test preflight failed: exit={code}, executed={target['executed']}, "
            f"failures={target['failures']}, errors={target['errors']}"
        )
    sync_plan(state, "test_preflight_pass")
    print(state / "preflight.json")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="action", required=True)
    init = sub.add_parser("init")
    init.add_argument("--project-root", required=True)
    init.add_argument("--state-dir", required=True)
    init.set_defaults(func=cmd_init)
    probe = sub.add_parser("probe")
    probe.add_argument("--state-dir", required=True)
    probe.add_argument("--testcase", required=True)
    probe.add_argument("command", nargs=argparse.REMAINDER)
    probe.set_defaults(func=cmd_probe)
    for name, func in (("red", cmd_red), ("green", cmd_green)):
        sp = sub.add_parser(name)
        sp.add_argument("--state-dir", required=True)
        sp.add_argument("--req", required=True)
        if name == "red":
            sp.add_argument("--test-file", required=True)
            sp.add_argument("--testcase", required=True, help="method, Class#method, or fully.qualified.Class#method")
        sp.add_argument("command", nargs=argparse.REMAINDER)
        sp.set_defaults(func=func)
    verify = sub.add_parser("verify")
    verify.add_argument("--state-dir", required=True)
    verify.add_argument("--req", action="append", required=True)
    verify.set_defaults(func=cmd_verify)
    return p


if __name__ == "__main__":
    ns = parser().parse_args()
    if hasattr(ns, "command") and ns.command[:1] == ["--"]:
        ns.command = ns.command[1:]
    raise SystemExit(ns.func(ns))
