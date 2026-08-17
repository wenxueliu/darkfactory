#!/usr/bin/env python3
"""Bridge works TDD evidence into planning-with-files state and phase gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time


BEGIN = "<!-- WORKS_STATE_BEGIN -->"
END = "<!-- WORKS_STATE_END -->"


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def paths(state_dir: str) -> tuple[Path, Path, Path]:
    tdd = Path(state_dir).resolve()
    baseline = load(tdd / "baseline.json")
    if not baseline:
        raise SystemExit(f"missing TDD baseline: {tdd / 'baseline.json'}")
    project = Path(baseline["project_root"]).resolve()
    plan = tdd.parent.parent if tdd.parent.name == "tdd" else tdd.parent
    if not (plan / "task_plan.md").is_file():
        candidates = [p.parent for p in (project / ".planning").glob("*/task_plan.md") if (p.parent / "tdd") == tdd]
        if candidates:
            plan = candidates[0]
    if not (plan / "task_plan.md").is_file():
        raise SystemExit(f"cannot bind TDD state to a planning directory: {tdd}")
    return tdd, plan, project


def slice_records(tdd: Path) -> list[dict]:
    rows = []
    for red_path in (tdd / "slices").glob("*/red.json"):
        red = load(red_path)
        if not red:
            continue
        green_path = red_path.parent / "green.json"
        rows.append(
            {
                "req": red.get("req", red_path.parent.name),
                "sequence": red.get("checkpoint_sequence", 999999),
                "red": red_path,
                "green": green_path if green_path.is_file() else None,
                "testcase": red.get("testcase", ""),
            }
        )
    return sorted(rows, key=lambda row: (row["sequence"], row["req"]))


def derive(tdd: Path, requested_req: str | None = None, req_queue: list[str] | None = None) -> dict:
    baseline = load(tdd / "baseline.json")
    preflight = load(tdd / "preflight.json")
    checkpoint = load(tdd / "checkpoint.json")
    verification = load(tdd / "tdd-verify.json")
    rows = slice_records(tdd)
    open_row = next((row for row in reversed(rows) if row["green"] is None), None)
    completed = [row["req"] for row in rows if row["green"]]
    remaining = [req for req in (req_queue or []) if req not in completed]
    automatic_req = remaining[0] if remaining else None
    expected_verify_reqs = req_queue or completed
    verification_valid = bool(
        verification.get("passed") and verification.get("reqs") == expected_verify_reqs
    )
    if not baseline:
        state, next_step = "baseline_required", "Run tdd_slice.py init before any feature or production edit."
    elif not preflight.get("passed"):
        state, next_step = "preflight_required", "Run tdd_slice.py probe with skip flags disabled and a known passing testcase."
    elif open_row:
        state = "implementation_allowed"
        next_step = f"Implement only {open_row['req']} minimally, then run tdd_slice.py green with {open_row['testcase']}."
    elif requested_req or automatic_req:
        requested_req = requested_req or automatic_req
        state = "red_required"
        next_step = f"Continue automatically with {requested_req}: write one behavior test and establish its Red before production edits."
    elif verification_valid:
        state, next_step = "acceptance_ready", "Run regression/CI-equivalent acceptance commands, then request Phase 5 completion."
    else:
        state, next_step = "next_slice_required", "Select the next uncovered Req ID and establish its Red; if all are Green, run tdd_slice.py verify."
    return {
        "state": state,
        "next_step": next_step,
        "current_req": open_row["req"] if open_row else requested_req,
        "testcase": open_row["testcase"] if open_row else None,
        "completed_reqs": completed,
        "remaining_reqs": remaining,
        "auto_continue": True,
        "open_req": open_row["req"] if open_row else None,
        "baseline_sha256": digest(tdd / "baseline.json"),
        "preflight_sha256": digest(tdd / "preflight.json"),
        "checkpoint_sha256": digest(tdd / "checkpoint.json"),
        "verify_sha256": digest(tdd / "tdd-verify.json"),
        "checkpoint_sequence": checkpoint.get("sequence", 0),
        "verification_passed": verification_valid,
        "updated_at": time.time(),
    }


def replace_section(text: str, heading: str, body: str) -> str:
    pattern = re.compile(rf"(^## {re.escape(heading)}\s*$)(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL)
    replacement = rf"\1\n{body.strip()}\n\n"
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    return text


def update_plan(plan_file: Path, state: dict) -> None:
    text = plan_file.read_text()
    text = replace_section(text, "Next Step", state["next_step"])
    if state.get("current_phase"):
        text = replace_section(text, "Current Phase", f"Phase {state['current_phase']}")
    block = "\n".join(
        [
            BEGIN,
            "## Works Execution State",
            f"- **TDD State:** {state['state']}",
            f"- **Current Req:** {state['current_req'] or 'none'}",
            f"- **Target Testcase:** {state['testcase'] or 'none'}",
            f"- **Production Write Allowed:** {'true' if state['state'] == 'implementation_allowed' else 'false'}",
            f"- **Completed Reqs:** {', '.join(state['completed_reqs']) or 'none'}",
            f"- **Remaining Reqs:** {', '.join(state['remaining_reqs']) or 'none'}",
            "- **Auto Continue:** true (never ask whether to continue between Reqs)",
            f"- **Baseline SHA256:** {state['baseline_sha256']}",
            f"- **Preflight SHA256:** {state['preflight_sha256']}",
            f"- **Checkpoint SHA256:** {state['checkpoint_sha256']}",
            f"- **Verify SHA256:** {state['verify_sha256']}",
            END,
        ]
    )
    if BEGIN in text and END in text:
        text = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), block, text, count=1, flags=re.DOTALL)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    atomic_text(plan_file, text)


def planning_skill() -> Path:
    candidate = Path(__file__).resolve().parents[2] / "planning-with-files"
    if not candidate.is_dir():
        raise SystemExit("planning-with-files must be installed beside works")
    return candidate


def env_for(project: Path, plan: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PWF_PLAN_ROOT"] = str(project)
    try:
        env["PLAN_ID"] = plan.relative_to(project / ".planning").as_posix()
    except ValueError:
        env.pop("PLAN_ID", None)
    return env


def run_script(name: str, args: list[str], project: Path, plan: Path) -> None:
    script = planning_skill() / "scripts" / name
    subprocess.run(["sh", str(script), *args], cwd=project, env=env_for(project, plan), check=True)


def append_ledger(event: str, summary: str, phase: str, files: list[str], project: Path, plan: Path) -> None:
    run_script(
        "ledger-append.sh",
        [event, summary, "--agent", "works", "--phase", phase, "--files", ",".join(files)],
        project,
        plan,
    )


def attest(project: Path, plan: Path) -> None:
    run_script("attest-plan.sh", [], project, plan)


def phase_status(plan_file: Path, phase: int) -> str | None:
    section = re.search(
        rf"^### Phase {phase}(?=\D|$).*?(?=^### Phase |\Z)",
        plan_file.read_text(),
        re.MULTILINE | re.DOTALL,
    )
    if not section:
        return None
    match = re.search(r"^\*\*Status:\*\*\s*(\w+)", section.group(0), re.MULTILINE)
    return match.group(1) if match else None


def active_phase(plan_file: Path) -> int:
    return next((phase for phase in range(1, 7) if phase_status(plan_file, phase) == "in_progress"), 6)


def align_next_step(state: dict) -> None:
    phase = state["current_phase"]
    fixed = {
        2: "Finish the baseline and executable-test preflight evidence.",
        3: "Complete the Req-to-Service/Mapper impact matrix before production edits.",
        5: "Run regression/CI-equivalent commands through works_plan_gate.py check.",
        6: "Audit the final diff, user-owned changes, risks, and delivery evidence.",
    }
    if phase in (2, 3) or (phase in (5, 6) and state["state"] == "acceptance_ready"):
        state["next_step"] = fixed[phase]


def validate_phase(phase: int, tdd: Path, plan: Path, project: Path, reqs: list[str]) -> None:
    baseline = load(tdd / "baseline.json")
    preflight = load(tdd / "preflight.json")
    verification = load(tdd / "tdd-verify.json")
    rows = slice_records(tdd)
    if phase == 2:
        if not baseline or not preflight.get("passed"):
            raise SystemExit("Phase 2 gate failed: baseline and passed preflight are required")
    elif phase == 3:
        findings = plan / "findings.md"
        content = findings.read_text() if findings.is_file() else ""
        for required in ("Req ID", "Service API", "Mapper/Repository"):
            if required not in content:
                raise SystemExit(f"Phase 3 gate failed: findings.md lacks {required}")
        req_queue = load(plan / "requirements.json").get("reqs", [])
        if not req_queue:
            raise SystemExit("Phase 3 gate failed: persist the ordered Req queue with set-reqs")
    elif phase in (4, 5, 6):
        if not reqs:
            raise SystemExit(f"Phase {phase} gate requires every --req in execution order")
        req_queue = load(plan / "requirements.json").get("reqs", [])
        if req_queue != reqs:
            raise SystemExit("Phase 4+ gate failed: --req order must exactly match persisted requirements.json")
        by_req = {row["req"]: row for row in rows}
        missing = [req for req in reqs if req not in by_req or by_req[req]["green"] is None]
        if missing:
            raise SystemExit("Phase 4+ gate failed: incomplete Red/Green evidence for " + ", ".join(missing))
        subprocess.run(
            [sys.executable, str(Path(__file__).with_name("service_boundary.py")), "verify", "--state-dir", str(tdd)],
            cwd=project,
            check=True,
        )
        subprocess.run(
            [sys.executable, str(Path(__file__).with_name("tdd_slice.py")), "verify", "--state-dir", str(tdd),
             *[item for req in reqs for item in ("--req", req)]],
            cwd=project,
            check=True,
        )
        verification = load(tdd / "tdd-verify.json")
        if not verification.get("passed") or verification.get("reqs") != reqs:
            raise SystemExit("Phase 4+ gate failed: run tdd_slice.py verify with all Req IDs in order")
        if phase >= 5 and phase_status(plan / "task_plan.md", 4) != "complete":
            raise SystemExit("Phase 5+ gate failed: Phase 4 is not complete")
        if phase >= 5:
            acceptance = load(plan / "acceptance.json")
            checks = acceptance.get("checks", [])
            if not checks or any(check.get("exit") != 0 for check in checks):
                raise SystemExit("Phase 5+ gate failed: run at least one successful acceptance check")
        if phase == 6 and phase_status(plan / "task_plan.md", 5) != "complete":
            raise SystemExit("Phase 6 gate failed: Phase 5 is not complete")


def cmd_sync(args: argparse.Namespace) -> int:
    tdd, plan, project = paths(args.state_dir)
    req_queue = load(plan / "requirements.json").get("reqs", [])
    state = derive(tdd, args.current_req, req_queue)
    state["current_phase"] = active_phase(plan / "task_plan.md")
    align_next_step(state)
    atomic_text(plan / "works-state.json", json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    update_plan(plan / "task_plan.md", state)
    append_ledger(
        "progress",
        f"{args.event} state={state['state']} req={state['current_req'] or 'none'} checkpoint={state['checkpoint_sequence']}",
        "4",
        ["works-state.json", "task_plan.md"],
        project,
        plan,
    )
    attest(project, plan)
    print(json.dumps(state, ensure_ascii=False))
    return 0


def cmd_complete(args: argparse.Namespace) -> int:
    tdd, plan, project = paths(args.state_dir)
    validate_phase(args.phase, tdd, plan, project, args.req)
    run_script("phase-status.sh", [str(args.phase), "complete"], project, plan)
    next_phase = args.phase + 1
    if next_phase <= 6 and phase_status(plan / "task_plan.md", next_phase) == "pending":
        run_script("phase-status.sh", [str(next_phase), "in_progress"], project, plan)
    req_queue = load(plan / "requirements.json").get("reqs", [])
    state = derive(tdd, args.current_req, req_queue)
    state["current_phase"] = active_phase(plan / "task_plan.md")
    align_next_step(state)
    atomic_text(plan / "works-state.json", json.dumps(state, ensure_ascii=False, indent=2) + "\n")
    update_plan(plan / "task_plan.md", state)
    append_ledger(
        "phase_complete",
        f"works phase {args.phase} completed after evidence validation",
        str(args.phase),
        ["task_plan.md", "works-state.json"],
        project,
        plan,
    )
    attest(project, plan)
    print(f"Phase {args.phase} complete")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    tdd, plan, project = paths(args.state_dir)
    if not args.command:
        raise SystemExit("missing acceptance command after --")
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", args.name).strip("-") or "check"
    log = plan / "logs" / f"acceptance-{safe_name}.log"
    proc = subprocess.run(args.command, cwd=project, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    atomic_text(log, proc.stdout)
    acceptance_file = plan / "acceptance.json"
    acceptance = load(acceptance_file)
    checks = acceptance.setdefault("checks", [])
    checks.append({
        "name": args.name,
        "command": args.command,
        "exit": proc.returncode,
        "log": str(log),
        "log_sha256": digest(log),
        "recorded_at": time.time(),
    })
    atomic_text(acceptance_file, json.dumps(acceptance, ensure_ascii=False, indent=2) + "\n")
    append_ledger("progress", f"acceptance {args.name} exit={proc.returncode}", "5", [str(log), "acceptance.json"], project, plan)
    attest(project, plan)
    if proc.returncode:
        print(proc.stdout, file=sys.stderr)
    return proc.returncode


def cmd_set_reqs(args: argparse.Namespace) -> int:
    _, plan, project = paths(args.state_dir)
    if not args.req or len(args.req) != len(set(args.req)):
        raise SystemExit("provide a non-empty, ordered, duplicate-free Req list")
    atomic_text(plan / "requirements.json", json.dumps({"reqs": args.req}, ensure_ascii=False, indent=2) + "\n")
    append_ledger("progress", "persisted autonomous Req queue: " + ", ".join(args.req), "3", ["requirements.json"], project, plan)
    attest(project, plan)
    return cmd_sync(argparse.Namespace(state_dir=args.state_dir, current_req=None, event="req_queue_saved"))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="action", required=True)
    sync = sub.add_parser("sync")
    sync.add_argument("--state-dir", required=True)
    sync.add_argument("--current-req")
    sync.add_argument("--event", default="manual_sync")
    sync.set_defaults(func=cmd_sync)
    complete = sub.add_parser("complete-phase")
    complete.add_argument("--state-dir", required=True)
    complete.add_argument("--phase", type=int, choices=range(2, 7), required=True)
    complete.add_argument("--req", action="append", default=[])
    complete.add_argument("--current-req")
    complete.set_defaults(func=cmd_complete)
    check = sub.add_parser("check")
    check.add_argument("--state-dir", required=True)
    check.add_argument("--name", required=True)
    check.add_argument("command", nargs=argparse.REMAINDER)
    check.set_defaults(func=cmd_check)
    reqs = sub.add_parser("set-reqs")
    reqs.add_argument("--state-dir", required=True)
    reqs.add_argument("--req", action="append", required=True)
    reqs.set_defaults(func=cmd_set_reqs)
    return p


if __name__ == "__main__":
    ns = parser().parse_args()
    if hasattr(ns, "command") and ns.command[:1] == ["--"]:
        ns.command = ns.command[1:]
    raise SystemExit(ns.func(ns))
