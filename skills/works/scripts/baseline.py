#!/usr/bin/env python3
"""Workspace baseline, Git preflight, fingerprints, and JUnit evidence helpers."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

from works_core.common import IGNORED_DIRS as IGNORED_PARTS, atomic_json, sha, windows_command

TRANSIENT_DIR_PARTS = {".idea", ".vscode", ".settings", ".metadata", ".externaltoolbuilders", ".classpath"}
TRANSIENT_FILE_NAMES = {".classpath", ".project", ".factorypath"}
TRANSIENT_SUFFIXES = (".iml",)


def is_transient_path(rel: str) -> bool:
    parts = tuple(part.lower() for part in Path(rel.replace("\\", "/")).parts)
    return bool(parts) and (
        any(part in TRANSIENT_DIR_PARTS for part in parts[:-1])
        or parts[-1] in TRANSIENT_FILE_NAMES
        or parts[-1].endswith(TRANSIENT_SUFFIXES)
    )


def normalized_production(values: dict[str, str]) -> dict[str, str]:
    return {path: digest for path, digest in values.items() if not is_transient_path(path)}


def is_test(rel: str) -> bool:
    path = rel.replace("\\", "/")
    name = Path(path).name.lower()
    return (
        "/src/test/" in f"/{path}"
        or path.startswith("src/test/")
        or "/test/" in f"/{path}"
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
        if is_transient_path(rel) or is_test(rel) == production:
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
    return state, Path(baseline["project_root"]), baseline


def changed(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(key for key in before.keys() | after.keys() if before.get(key) != after.get(key))


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
    summary = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "files": [],
               "target": {"selector": testcase, "executed": 0, "failures": 0, "errors": 0}}
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
            if testcase_matches(case.attrib.get("classname", ""), case.attrib.get("name", ""), testcase):
                summary["target"]["executed"] += 1
                summary["target"]["failures"] += len(case.findall("failure"))
                summary["target"]["errors"] += len(case.findall("error"))
        summary["files"].append({"path": str(path), "sha256": sha(path)})
    return summary


def run_command(root: Path, command: list[str], log: Path, report_dir: Path, testcase: str) -> tuple[int, dict]:
    if not command:
        raise SystemExit("missing command after --")
    before = report_snapshot(root)
    proc = subprocess.run(windows_command(command), cwd=root, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
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
            if value == "true" and (("skip" in lowered and "test" in lowered) or name == "skipTests"):
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


def cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.project_root).resolve()
    state = Path(args.state_dir).resolve()
    if (state / "baseline.json").exists():
        raise SystemExit("workspace baseline already exists; init is immutable for this plan")
    git_managed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0
    status = ""
    if git_managed:
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain=v2", "--untracked-files=all"],
            check=True, text=True, stdout=subprocess.PIPE,
        ).stdout
    data = {"version": 1, "project_root": str(root), "created_at": time.time(),
            "git_managed": git_managed, "git_status": status.splitlines(),
            "production": fingerprints(root, production=True)}
    atomic_json(state / "baseline.json", data)
    (state / "baseline.sha256").write_text(hashlib.sha256((state / "baseline.json").read_bytes()).hexdigest() + "\n")
    atomic_json(state / "checkpoint.json", {"sequence": 0, "production": data["production"], "previous_req": None})
    print(state / "baseline.json")
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    state, root, baseline = state_paths(args)
    baseline_file = state / "baseline.json"
    baseline_lock = state / "baseline.sha256"
    digest = sha(baseline_file)
    if not baseline_lock.exists() or baseline_lock.read_text().strip() != digest:
        raise SystemExit("baseline hash lock mismatch")
    managed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode == 0
    atomic_json(state / "preflight.json", {
        "passed": True, "source": "baseline", "baseline_version": baseline.get("version"),
        "baseline_sha256": digest, "git_managed": managed,
        "baseline_mode": "git" if managed else "fingerprint", "recorded_at": time.time(),
    })
    print(state / "preflight.json")
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    """Create and verify one immutable baseline without changing Git history."""
    if not (Path(args.state_dir).resolve() / "baseline.json").exists():
        cmd_init(args)
    return cmd_probe(args)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    sub = root.add_subparsers(dest="action", required=True)
    init = sub.add_parser("init")
    init.add_argument("--project-root", required=True)
    init.add_argument("--state-dir", required=True)
    init.set_defaults(func=cmd_init)
    probe = sub.add_parser("probe")
    probe.add_argument("--state-dir", required=True)
    probe.set_defaults(func=cmd_probe)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--project-root", required=True)
    preflight.add_argument("--state-dir", required=True)
    preflight.set_defaults(func=cmd_preflight)
    return root


if __name__ == "__main__":
    args = parser().parse_args()
    raise SystemExit(args.func(args))
