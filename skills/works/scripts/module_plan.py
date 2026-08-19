#!/usr/bin/env python3
"""Validate Req×Maven-module DAGs and merged Subagent wave evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import subprocess

from works_core.common import atomic_json, branch_token, ordered_task_ids, result_filename
from tdd_slice import require_test_flags, run_command

ERROR = "E305_INVALID_MODULE_PLAN"
TASK_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")


def template(reqs: list[str]) -> dict:
    return {"version": 1, "max_parallel": 4, "tasks": [], "waves": [],
            "requirements": reqs}


def inside_module(project: Path, module: str, relative: str) -> bool:
    if not valid_module_name(module):
        return False
    if not isinstance(relative, str) or not relative or "\\" in relative:
        return False
    try:
        module_path = Path(module)
        relative_path = Path(relative)
        if module_path.is_absolute() or relative_path.is_absolute():
            return False
        path = (project / relative).resolve()
        root = (project / module).resolve()
        return root.is_relative_to(project.resolve()) and path.is_relative_to(root)
    except (OSError, ValueError):
        return False


def valid_module_name(module: object) -> bool:
    if not isinstance(module, str) or not module or "\\" in module or ":" in module:
        return False
    path = Path(module)
    return (not path.is_absolute() and not PureWindowsPath(module).is_absolute()
            and (module == "." or all(part not in {"", ".", ".."} for part in path.parts)))


def module_path(module: str, relative: str) -> str:
    """Return a Git-style path for a file inside a Maven module."""
    normalized = module.rstrip("/")
    if normalized in {"", "."}:
        return relative
    return f"{normalized}/{relative}"


def maven_module(project: Path, relative: str) -> str | None:
    path_value = relative.rsplit(":", 1)[0] if re.search(r":\d+$", relative) else relative
    if "\\" in path_value or Path(path_value).is_absolute() or PureWindowsPath(path_value).is_absolute():
        return None
    candidate = (project / path_value).resolve()
    if not candidate.is_relative_to(project.resolve()):
        return None
    roots = [pom.parent.resolve() for pom in project.rglob("pom.xml")]
    matches = [root for root in roots if candidate.is_relative_to(root)]
    if not matches:
        return None
    root = max(matches, key=lambda value: len(value.parts))
    relative_root = root.relative_to(project.resolve()).as_posix()
    return relative_root or "."


def required_modules(impact: dict, project: Path, reqs: list[str]) -> dict[str, set[str]]:
    required = {req: set() for req in reqs}
    for row in impact.get("requirements", []):
        if not isinstance(row, dict) or row.get("id") not in required:
            continue
        values = [value for field in ("entrypoints", "service_apis", "persistence")
                  for value in row.get(field, []) if isinstance(value, str)]
        values.extend(seam.get("planned_test") for seam in row.get("test_seams", [])
                      if isinstance(seam, dict) and isinstance(seam.get("planned_test"), str))
        required[row["id"]].update(module for value in values
                                   if (module := maven_module(project, value)) is not None)
    return required


def patch_paths(content: bytes) -> set[str]:
    paths: set[str] = set()
    headers = 0
    for raw in content.splitlines():
        if not raw.startswith(b"diff --git a/"):
            continue
        headers += 1
        line = raw.decode("utf-8", errors="replace")
        match = re.fullmatch(r"diff --git a/(.+) b/(.+)", line)
        if not match or match.group(1) != match.group(2):
            raise ValueError("patch contains malformed or rename diff header")
        paths.add(match.group(1))
    if headers != len(paths):
        raise ValueError("patch contains duplicate diff headers")
    return paths


def stable_patch_id(content: bytes) -> str | None:
    proc = subprocess.run(["git", "patch-id", "--stable"], input=content,
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if proc.returncode != 0 or not proc.stdout:
        return None
    return proc.stdout.decode(errors="replace").split()[0]


def verify_patches(plan: dict, project: Path, results: Path, wave_number: int) -> list[str]:
    errors: list[str] = []
    dirty = subprocess.run(
        ["git", "-C", str(project), "status", "--porcelain", "--untracked-files=no"], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    if dirty.returncode != 0 or dirty.stdout.strip():
        errors.append(f"wave {wave_number}: controller workspace must have no tracked changes before apply")
    task_map = {task["id"]: task for task in plan["tasks"]}
    ids = plan["waves"][wave_number - 1]["tasks"]
    bases: set[str] = set()
    all_paths: dict[str, str] = {}
    for task_id in ids:
        task = task_map[task_id]
        try:
            result = json.loads((results / result_filename(task_id)).read_text())
            base = result["base_commit"]
            patch_file = result["patch_file"]
            expected_hash = result["patch_sha256"]
            changed = result["changed_files"]
            test_file = result["test_file"]
            if result.get("task") != task_id or result.get("status") != "PATCH_READY":
                raise ValueError("candidate result must be PATCH_READY for its task")
            bases.add(base)
            patch_path = (results / patch_file).resolve()
            if not patch_path.is_relative_to(results.resolve()):
                raise ValueError("patch escapes results directory")
            content = patch_path.read_bytes()
            if hashlib.sha256(content).hexdigest() != expected_hash:
                raise ValueError("patch hash mismatch")
            if stable_patch_id(content) is None:
                raise ValueError("patch has no stable Git patch-id")
            applicable = subprocess.run(
                ["git", "-C", str(project), "apply", "--check", "-"], input=content,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            if applicable.returncode != 0:
                raise ValueError("patch does not apply cleanly to shared base")
            expected_paths = set(changed) | {test_file}
            test_prefix = module_path(task["module"], "src/test/")
            if not isinstance(test_file, str) or not test_file.startswith(test_prefix):
                raise ValueError("focused test_file must be under module/src/test")
            if test_file in set(changed):
                raise ValueError("focused test_file cannot be declared as production change")
            if (project / test_file).exists():
                raise ValueError("focused test file must not exist before patch apply")
            actual_paths = patch_paths(content)
            if actual_paths != expected_paths:
                raise ValueError("patch paths do not match declared production and test files")
            for relative in actual_paths:
                if not inside_module(project, task["module"], relative):
                    raise ValueError(f"patch path escapes module: {relative}")
                if relative != test_file and not any(
                        relative == scope.rstrip("/") or relative.startswith(scope.rstrip("/") + "/")
                        for scope in task.get("write_scope", [])):
                    raise ValueError(f"patch path escapes write_scope: {relative}")
                if relative in all_paths:
                    raise ValueError(f"patch path overlaps {all_paths[relative]}: {relative}")
                all_paths[relative] = task_id
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{task_id}: invalid patch candidate ({exc})")
    if len(bases) != 1:
        errors.append(f"wave {wave_number}: all Subagent patches must use one shared base_commit")
    else:
        head = subprocess.run(["git", "-C", str(project), "rev-parse", "HEAD"], text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if head.returncode != 0 or head.stdout.strip() != next(iter(bases)):
            errors.append(f"wave {wave_number}: shared base_commit must equal controller HEAD before apply")
    return errors


def validate(data: object, project: Path, reqs: list[str], impact: dict | None = None,
             contract: dict | None = None) -> list[str]:
    if not isinstance(data, dict):
        return ["module plan must be an object"]
    errors: list[str] = []
    if data.get("requirements") != reqs:
        errors.append("top-level requirements must exactly match the requirement contract")
    tasks = data.get("tasks")
    waves = data.get("waves")
    if data.get("version") != 1 or not isinstance(tasks, list) or not tasks:
        return ["version must be 1 and tasks must be a non-empty array"]
    if not isinstance(waves, list) or not waves:
        errors.append("waves must be a non-empty array")
        waves = []
    by_id: dict[str, dict] = {}
    by_req_module: dict[tuple[str, str], str] = {}
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
        valid_module = (valid_module_name(module)
                        and inside_module(project, module, module_path(module, "pom.xml"))
                        and (project / module / "pom.xml").is_file())
        if not valid_module:
            errors.append(f"{prefix}.module must identify a Maven module with pom.xml")
        elif req in reqs:
            key = (req, "." if module.rstrip("/") in {"", "."} else module.rstrip("/"))
            if key in by_req_module:
                errors.append(f"{prefix} duplicates Req × module task {by_req_module[key]}")
            else:
                by_req_module[key] = task_id
        write_scope = task.get("write_scope")
        if not isinstance(write_scope, list) or not write_scope:
            errors.append(f"{prefix}.write_scope must be non-empty")
        else:
            if len(write_scope) != len(set(scope for scope in write_scope if isinstance(scope, str))):
                errors.append(f"{prefix}.write_scope must not contain duplicates")
            for scope in write_scope:
                if not isinstance(scope, str) or not inside_module(project, module, scope):
                    errors.append(f"{prefix}.write_scope escapes module: {scope!r}")
                else:
                    scopes.append((task_id, scope.rstrip("/")))
        dependencies = task.get("depends_on")
        if (not isinstance(dependencies, list)
                or any(not isinstance(value, str) for value in dependencies)):
            errors.append(f"{prefix}.depends_on must be an array")
        elif len(dependencies) != len(set(dependencies)):
            errors.append(f"{prefix}.depends_on must not contain duplicates")
        behaviors = task.get("changed_behaviors")
        if (not isinstance(behaviors, list) or not behaviors
                or any(not isinstance(value, str) or not value.strip() for value in behaviors)):
            errors.append(f"{prefix}.changed_behaviors must be non-empty")
        elif len(behaviors) != len(set(behaviors)):
            errors.append(f"{prefix}.changed_behaviors must not contain duplicates")
        database_dependencies = task.get("database_dependencies")
        if (not isinstance(database_dependencies, list)
                or any(not isinstance(value, str) or not value.strip() for value in database_dependencies)):
            errors.append(f"{prefix}.database_dependencies must be an array")
        elif len(database_dependencies) != len(set(database_dependencies)):
            errors.append(f"{prefix}.database_dependencies must not contain duplicates")
    missing = [req for req in reqs if req not in covered]
    if missing:
        errors.append(f"requirements missing module tasks: {missing!r}")
    for task_id, task in by_id.items():
        for dependency in task.get("depends_on", []) if isinstance(task.get("depends_on"), list) else []:
            if dependency not in by_id or dependency == task_id:
                errors.append(f"{task_id} has invalid dependency {dependency!r}")
    wave_of: dict[str, int] = {}
    max_parallel = data.get("max_parallel", 4)
    if isinstance(max_parallel, bool) or not isinstance(max_parallel, int) or max_parallel < 1:
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
        for dependency in task.get("depends_on", []) if isinstance(task.get("depends_on"), list) else []:
            if dependency in wave_of and task_id in wave_of and wave_of[dependency] >= wave_of[task_id]:
                errors.append(f"{task_id} must be in a later wave than {dependency}")
    names = [result_filename(task_id) for task_id in by_id]
    if len(names) != len(set(names)):
        errors.append("task ids produce colliding cross-platform evidence filenames")
    planned_modules = {req: {module for task_req, module in by_req_module if task_req == req}
                       for req in reqs}
    if impact is not None:
        for req, modules in required_modules(impact, project, reqs).items():
            missing_modules = sorted(modules - planned_modules[req])
            if missing_modules:
                errors.append(f"{req} missing impacted Maven module tasks: {missing_modules!r}")
    if contract is not None:
        contract_modules = {req: set() for req in reqs}
        for row in contract.get("acceptance_commands", []):
            command = row.get("command", []) if isinstance(row, dict) else []
            if "-pl" not in command or command.index("-pl") + 1 >= len(command):
                continue
            module = command[command.index("-pl") + 1]
            for req in row.get("covers", []):
                if req in contract_modules:
                    contract_modules[req].add(module)
        for req, modules in contract_modules.items():
            missing_modules = sorted(modules - planned_modules[req])
            if missing_modules:
                errors.append(f"{req} missing contract Maven module tasks: {missing_modules!r}")
    return errors


def verify_wave(plan: dict, project: Path, results: Path, wave_number: int,
                baseline: dict, contract: dict | None = None) -> list[str]:
    errors: list[str] = []
    task_map = {task["id"]: task for task in plan["tasks"]}
    ids = plan["waves"][wave_number - 1]["tasks"]
    baseline_tests = set(baseline.get("tests", {}))
    wave_bases: set[str] = set()
    merged_by_task: dict[str, str] = {}
    for task_id in ids:
        task = task_map[task_id]
        path = results / result_filename(task_id)
        try:
            result = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"{task_id}: missing/invalid Subagent result ({exc})")
            continue
        required_git = ("base_commit", "patch_file", "patch_sha256", "commit")
        if (result.get("status") != "PASS" or result.get("task") != task_id
                or not all(isinstance(result.get(key), str) and result[key] for key in required_git)):
            errors.append(f"{task_id}: result must be PASS with complete patch and commit evidence")
        base_commit = result.get("base_commit")
        patch_file = result.get("patch_file")
        patch_sha256 = result.get("patch_sha256")
        merged_commit = result.get("commit")
        if isinstance(base_commit, str):
            wave_bases.add(base_commit)
        if isinstance(merged_commit, str):
            merged_by_task[task_id] = merged_commit
        patch = b""
        if isinstance(patch_file, str):
            try:
                patch_path = (results / patch_file).resolve()
                if not patch_path.is_relative_to(results.resolve()):
                    raise OSError("patch escapes results directory")
                patch = patch_path.read_bytes()
            except OSError as exc:
                errors.append(f"{task_id}: missing/invalid patch artifact ({exc})")
        if patch and hashlib.sha256(patch).hexdigest() != patch_sha256:
            errors.append(f"{task_id}: patch_sha256 does not match patch artifact")
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
        if isinstance(merged_commit, str):
            expected_commit_files = set(changed) | ({test_file} if isinstance(test_file, str) else set())
            try:
                actual_patch_paths = patch_paths(patch)
            except ValueError as exc:
                actual_patch_paths = set()
                errors.append(f"{task_id}: invalid patch artifact ({exc})")
            if actual_patch_paths != expected_commit_files:
                errors.append(f"{task_id}: patch paths do not exactly match production + new focused test")
            proc = subprocess.run(
                ["git", "-C", str(project), "diff-tree", "--root", "--no-commit-id",
                 "--name-only", "-r", merged_commit], text=True,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
            committed = set(proc.stdout.splitlines()) if proc.returncode == 0 else set()
            if proc.returncode != 0 or committed != expected_commit_files:
                errors.append(f"{task_id}: commit files do not exactly match production + new focused test")
            merged_patch = subprocess.run(
                ["git", "-C", str(project), "diff", f"{merged_commit}^", merged_commit, "--binary"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
            if (merged_patch.returncode != 0 or stable_patch_id(merged_patch.stdout) is None
                    or stable_patch_id(merged_patch.stdout) != stable_patch_id(patch)):
                errors.append(f"{task_id}: commit patch-id must equal the validated Subagent patch-id")
            ancestor = subprocess.run(
                ["git", "-C", str(project), "merge-base", "--is-ancestor", merged_commit, "HEAD"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            if ancestor.returncode != 0:
                errors.append(f"{task_id}: merged_commit is not integrated into the controller branch")
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
        req = task.get("req")
        if contract is not None:
            accepted = [row.get("command") for row in contract.get("acceptance_commands", [])
                        if req in row.get("covers", [])]
            if command not in accepted:
                errors.append(f"{task_id}: test_command is not declared for {req} in requirement contract")
        module = task["module"]
        runner = Path(command[0]).name.lower() if isinstance(command, list) and command else ""
        goals = [token for token in command if token in {"test", "verify", "package", "install"}] if isinstance(command, list) else []
        command_valid = (isinstance(command, list) and isinstance(selector, str)
                         and runner in {"mvn", "mvnw", "mvnw.cmd"}
                         and "-pl" in command and command.index("-pl") + 1 < len(command)
                         and command[command.index("-pl") + 1] == module
                         and f"-Dtest={selector}" in command
                         and "-DskipTests=false" in command and "-Dmaven.test.skip=false" in command
                         and goals == ["test"] and command[-1] == "test")
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
            safe_task = result_filename(task_id).removesuffix(".json")
            log_dir = results / "wave-verification" / f"wave-{wave_number}" / safe_task
            code, junit = run_command(project, command, log_dir / "test.log",
                                      log_dir / "reports", selector)
            target = junit["target"]
            if code != 0 or target["executed"] < 1 or target["failures"] or target["errors"]:
                errors.append(f"{task_id}: controller focused-test replay failed")
    if len(wave_bases) != 1:
        errors.append(f"wave {wave_number}: all Subagent patches must use one shared base_commit")
    elif len(merged_by_task) == len(ids):
        expected_parent = next(iter(wave_bases))
        for task_id in ordered_task_ids(ids):
            merged = merged_by_task[task_id]
            parent = subprocess.run(
                ["git", "-C", str(project), "rev-parse", f"{merged}^"], text=True,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
            if parent.returncode != 0 or parent.stdout.strip() != expected_parent:
                errors.append(f"{task_id}: merged commits must form task-id-sorted chain from wave base")
            expected_parent = merged
        head = subprocess.run(
            ["git", "-C", str(project), "rev-parse", "HEAD"], text=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        if head.returncode != 0 or head.stdout.strip() != expected_parent:
            errors.append(f"wave {wave_number}: controller HEAD must equal the final merged_commit")
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
    check.add_argument("--impact-map", required=True)
    check.add_argument("--contract", required=True)
    wave = sub.add_parser("verify-wave")
    wave.add_argument("--file", required=True)
    wave.add_argument("--project-root", required=True)
    wave.add_argument("--results-dir", required=True)
    wave.add_argument("--baseline", required=True)
    wave.add_argument("--contract", required=True)
    wave.add_argument("--wave", required=True, type=int)
    patches = sub.add_parser("verify-patches")
    patches.add_argument("--file", required=True)
    patches.add_argument("--project-root", required=True)
    patches.add_argument("--results-dir", required=True)
    patches.add_argument("--wave", required=True, type=int)
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
        impact = json.loads(Path(args.impact_map).read_text())
        contract = json.loads(Path(args.contract).read_text())
        errors = validate(data, Path(args.project_root).resolve(), args.req, impact, contract)
    elif args.action == "verify-wave":
        baseline = json.loads(Path(args.baseline).read_text())
        contract = json.loads(Path(args.contract).read_text())
        errors = verify_wave(data, Path(args.project_root).resolve(), Path(args.results_dir), args.wave,
                             baseline, contract)
    else:
        errors = verify_patches(data, Path(args.project_root).resolve(), Path(args.results_dir), args.wave)
    if errors:
        print(json.dumps({"ok": False, "error": ERROR, "violations": errors}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({"ok": True}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
