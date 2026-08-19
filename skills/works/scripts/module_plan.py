#!/usr/bin/env python3
"""Validate Req×Maven-module DAGs and merged Subagent wave evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess

from works_core.common import atomic_json
from tdd_slice import require_test_flags, run_command

ERROR = "E305_INVALID_MODULE_PLAN"
TASK_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")


def template(reqs: list[str]) -> dict:
    return {"version": 1, "max_parallel": 4, "tasks": [], "waves": [],
            "requirements": reqs}


def inside_module(project: Path, module: str, relative: str) -> bool:
    try:
        path = (project / relative).resolve()
        root = (project / module).resolve()
        return path.is_relative_to(root)
    except (OSError, ValueError):
        return False


def validate(data: object, project: Path, reqs: list[str]) -> list[str]:
    if not isinstance(data, dict):
        return ["module plan must be an object"]
    errors: list[str] = []
    tasks = data.get("tasks")
    waves = data.get("waves")
    if data.get("version") != 1 or not isinstance(tasks, list) or not tasks:
        return ["version must be 1 and tasks must be a non-empty array"]
    if not isinstance(waves, list) or not waves:
        errors.append("waves must be a non-empty array")
        waves = []
    by_id: dict[str, dict] = {}
    covered: set[str] = set()
    scopes: list[tuple[str, str]] = []
    for index, task in enumerate(tasks):
        prefix = f"tasks[{index}]"
        if not isinstance(task, dict):
            errors.append(f"{prefix} must be an object")
            continue
        task_id, req, module = task.get("id"), task.get("req"), task.get("module")
        if not isinstance(task_id, str) or not TASK_ID.fullmatch(task_id) or task_id in by_id:
            errors.append(f"{prefix}.id is invalid or duplicate")
            continue
        by_id[task_id] = task
        if req not in reqs:
            errors.append(f"{prefix}.req is unknown")
        else:
            covered.add(req)
        if not isinstance(module, str) or not (project / module / "pom.xml").is_file():
            errors.append(f"{prefix}.module must identify a Maven module with pom.xml")
        write_scope = task.get("write_scope")
        if not isinstance(write_scope, list) or not write_scope:
            errors.append(f"{prefix}.write_scope must be non-empty")
        else:
            for scope in write_scope:
                if not isinstance(scope, str) or not inside_module(project, module, scope):
                    errors.append(f"{prefix}.write_scope escapes module: {scope!r}")
                else:
                    scopes.append((task_id, scope.rstrip("/")))
        if not isinstance(task.get("depends_on"), list):
            errors.append(f"{prefix}.depends_on must be an array")
        if not isinstance(task.get("changed_behaviors"), list) or not task["changed_behaviors"]:
            errors.append(f"{prefix}.changed_behaviors must be non-empty")
        if not isinstance(task.get("database_dependencies"), list):
            errors.append(f"{prefix}.database_dependencies must be an array")
    missing = [req for req in reqs if req not in covered]
    if missing:
        errors.append(f"requirements missing module tasks: {missing!r}")
    for task_id, task in by_id.items():
        for dependency in task.get("depends_on", []):
            if dependency not in by_id or dependency == task_id:
                errors.append(f"{task_id} has invalid dependency {dependency!r}")
    wave_of: dict[str, int] = {}
    max_parallel = data.get("max_parallel", 4)
    if not isinstance(max_parallel, int) or max_parallel < 1:
        errors.append("max_parallel must be a positive integer")
        max_parallel = 1
    for number, wave in enumerate(waves, 1):
        ids = wave.get("tasks") if isinstance(wave, dict) else None
        if not isinstance(ids, list) or not ids or len(ids) > max_parallel:
            errors.append(f"waves[{number - 1}].tasks is invalid or exceeds max_parallel")
            continue
        for task_id in ids:
            if task_id not in by_id or task_id in wave_of:
                errors.append(f"waves[{number - 1}] contains unknown or duplicate task {task_id!r}")
            else:
                wave_of[task_id] = number
    if set(wave_of) != set(by_id):
        errors.append("waves must contain every task exactly once")
    for index, (left_id, left) in enumerate(scopes):
        for right_id, right in scopes[index + 1:]:
            overlap = left == right or left.startswith(right + "/") or right.startswith(left + "/")
            if left_id != right_id and overlap and wave_of.get(left_id) == wave_of.get(right_id):
                errors.append(f"parallel write scopes overlap: {left_id}:{left} and {right_id}:{right}")
    for task_id, task in by_id.items():
        for dependency in task.get("depends_on", []):
            if dependency in wave_of and task_id in wave_of and wave_of[dependency] >= wave_of[task_id]:
                errors.append(f"{task_id} must be in a later wave than {dependency}")
    return errors


def verify_wave(plan: dict, project: Path, results: Path, wave_number: int,
                baseline: dict) -> list[str]:
    errors: list[str] = []
    task_map = {task["id"]: task for task in plan["tasks"]}
    ids = plan["waves"][wave_number - 1]["tasks"]
    baseline_tests = set(baseline.get("tests", {}))
    for task_id in ids:
        task = task_map[task_id]
        path = results / f"{task_id}.json"
        try:
            result = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{task_id}: missing/invalid Subagent result ({exc})")
            continue
        if result.get("status") != "PASS" or result.get("task") != task_id or not result.get("commit"):
            errors.append(f"{task_id}: result must be PASS with task and commit")
        commit = result.get("commit")
        changed = result.get("changed_files")
        covered = result.get("covered_files")
        if not isinstance(changed, list) or not changed or set(changed) != set(covered or []):
            errors.append(f"{task_id}: every changed production file must be covered by the focused test")
            changed = []
        for relative in changed:
            if not inside_module(project, task["module"], relative):
                errors.append(f"{task_id}: changed file escapes module: {relative}")
            scopes = task.get("write_scope", [])
            if not any(relative == scope.rstrip("/") or relative.startswith(scope.rstrip("/") + "/")
                       for scope in scopes):
                errors.append(f"{task_id}: changed file escapes write_scope: {relative}")
        test_file = result.get("test_file")
        if not isinstance(test_file, str) or test_file in baseline_tests or not inside_module(project, task["module"], test_file):
            errors.append(f"{task_id}: test_file must be a new test inside the module")
            source = ""
        else:
            try:
                source = (project / test_file).read_text(errors="replace")
            except OSError:
                source = ""
                errors.append(f"{task_id}: test_file does not exist")
        if isinstance(commit, str):
            proc = subprocess.run(["git", "-C", str(project), "diff-tree", "--root", "--no-commit-id",
                                   "--name-only", "-r", commit], text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            committed = set(proc.stdout.splitlines()) if proc.returncode == 0 else set()
            expected_commit_files = set(changed) | ({test_file} if isinstance(test_file, str) else set())
            if proc.returncode != 0 or committed != expected_commit_files:
                errors.append(f"{task_id}: commit files do not exactly match production + new focused test")
        if "org.mockito" not in source or not ("@Mock" in source or "Mockito.mock(" in source or "mock(" in source):
            errors.append(f"{task_id}: new focused test must use Mockito")
        forbidden = ("@SpringBootTest", "@DataJpaTest", "@MybatisTest", "Testcontainers",
                     "DataSource", "JdbcTemplate", "EntityManager", "SqlSession", "jdbc:")
        present = [token for token in forbidden if token in source]
        if present:
            errors.append(f"{task_id}: focused test loads real framework/database dependencies: {present!r}")
        mocks = result.get("database_mocks")
        expected_mocks = task.get("database_dependencies", [])
        if sorted(mocks or []) != sorted(expected_mocks):
            errors.append(f"{task_id}: database_mocks must match planned database_dependencies")
        for symbol in expected_mocks:
            if symbol not in source:
                errors.append(f"{task_id}: database dependency {symbol} is not mocked in test source")
        command = result.get("test_command")
        selector = result.get("testcase")
        module = task["module"]
        command_valid = (isinstance(command, list) and isinstance(selector, str)
                         and "-pl" in command and command.index("-pl") + 1 < len(command)
                         and command[command.index("-pl") + 1] == module
                         and f"-Dtest={selector}" in command
                         and "-DskipTests=false" in command and "-Dmaven.test.skip=false" in command
                         and not ({"verify", "package"} & set(command)))
        if not command_valid:
            errors.append(f"{task_id}: test_command must target only module and testcase with tests enabled")
        elif command_valid:
            try:
                require_test_flags(project, command)
            except SystemExit as exc:
                errors.append(f"{task_id}: {exc}")
                command_valid = False
        evidence = result.get("test_evidence")
        if not isinstance(evidence, dict) or evidence.get("exit") != 0 or evidence.get("executed", 0) < 1:
            errors.append(f"{task_id}: focused test evidence must prove execution and success")
        if command_valid:
            log_dir = results / "wave-verification" / f"wave-{wave_number}" / task_id
            code, junit = run_command(project, command, log_dir / "test.log",
                                      log_dir / "reports", selector)
            target = junit["target"]
            if code != 0 or target["executed"] < 1 or target["failures"] or target["errors"]:
                errors.append(f"{task_id}: controller focused-test replay failed")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="action", required=True)
    init = sub.add_parser("init")
    init.add_argument("--output", required=True)
    init.add_argument("--req", action="append", required=True)
    check = sub.add_parser("validate")
    check.add_argument("--file", required=True)
    check.add_argument("--project-root", required=True)
    check.add_argument("--req", action="append", required=True)
    wave = sub.add_parser("verify-wave")
    wave.add_argument("--file", required=True)
    wave.add_argument("--project-root", required=True)
    wave.add_argument("--results-dir", required=True)
    wave.add_argument("--baseline", required=True)
    wave.add_argument("--wave", required=True, type=int)
    args = parser.parse_args()
    path = Path(args.output if args.action == "init" else args.file)
    if args.action == "init":
        if path.exists():
            raise SystemExit(f"{ERROR}: refusing to overwrite {path}")
        atomic_json(path, template(args.req))
        print(path)
        return 0
    data = json.loads(path.read_text())
    if args.action == "validate":
        errors = validate(data, Path(args.project_root).resolve(), args.req)
    else:
        baseline = json.loads(Path(args.baseline).read_text())
        errors = verify_wave(data, Path(args.project_root).resolve(), Path(args.results_dir), args.wave, baseline)
    if errors:
        print(json.dumps({"ok": False, "error": ERROR, "violations": errors}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({"ok": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
