from __future__ import annotations

import json
from pathlib import Path, PureWindowsPath
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import impact_map
import module_plan
import requirement_contract
import review_evidence
import service_boundary
import tdd_slice
from works_core.application import Application, WorksError
from works_core.discovery import discover, discover_maven_command
from works_core import application as works_application
from works_core import state as store


def project_fixture(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "pom.xml").write_text("<project/>")
    (root / "requirement.md").write_text("# Requirement")


def bind_module_plan_state(plan: Path, current: dict) -> None:
    """Create the immutable plan/input artifacts required by a validated state."""
    module_plan_file = plan / "module-plan.json"
    module_plan_file.write_text(json.dumps({
        "version": 1, "requirements": current.get("requirements", []),
        "tasks": current.get("module_tasks", []), "waves": current.get("waves", []),
    }))
    impact_file = plan / "impact-map.json"
    if not impact_file.exists():
        impact_file.write_text(json.dumps({"version": 1, "requirements": []}))
    contract_file = plan / "requirement-contract.json"
    if not contract_file.exists():
        contract_file.write_text(json.dumps({"version": 1, "requirements": []}))
    current["module_plan_sha256"] = module_plan.hashlib.sha256(
        module_plan_file.read_bytes()).hexdigest()
    current["module_plan_inputs"] = {
        name: module_plan.hashlib.sha256((plan / name).read_bytes()).hexdigest()
        for name in ("impact-map.json", "requirement-contract.json")
    }


class BaselineProbeTest(unittest.TestCase):
    def test_application_can_initialize_a_project_without_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pom.xml").write_text("<project/>")
            (root / "requirement.md").write_text("# Requirement")

            initialized = Application(SCRIPTS).init(root)

            self.assertEqual(initialized["state"], "SETUP_REQUIRED")
            self.assertFalse(initialized["discovery"]["git_managed"])
            self.assertTrue(Path(initialized["plan_dir"]).is_dir())

    def test_baseline_init_allows_a_project_without_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / ".planning" / "evidence"
            with mock.patch.object(tdd_slice.subprocess, "run") as run:
                run.return_value.returncode = 128
                result = tdd_slice.cmd_init(type("Args", (), {
                    "project_root": str(root), "state_dir": str(state),
                })())

            self.assertEqual(result, 0)
            baseline = json.loads((state / "baseline.json").read_text())
            self.assertFalse(baseline["git_managed"])
            self.assertEqual(baseline["git_status"], [])

    def test_probe_only_loads_locked_baseline_without_running_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            baseline = {"version": 1, "project_root": directory, "production": {}, "tests": {}}
            baseline_file = state / "baseline.json"
            baseline_file.write_text(json.dumps(baseline))
            (state / "baseline.sha256").write_text(tdd_slice.sha(baseline_file) + "\n")

            with mock.patch.object(tdd_slice.subprocess, "run") as run:
                run.return_value.returncode = 0
                result = tdd_slice.cmd_probe(type("Args", (), {"state_dir": str(state)})())

            self.assertEqual(result, 0)
            run.assert_called_once_with(
                ["git", "-C", directory, "rev-parse", "--is-inside-work-tree"],
                stdout=tdd_slice.subprocess.DEVNULL,
                stderr=tdd_slice.subprocess.DEVNULL,
            )
            preflight = json.loads((state / "preflight.json").read_text())
            self.assertTrue(preflight["passed"])
            self.assertEqual(preflight["source"], "baseline")
            self.assertEqual(preflight["baseline_sha256"], tdd_slice.sha(baseline_file))
            self.assertFalse(preflight["git_initialized"])

    def test_probe_initializes_and_commits_an_unmanaged_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / ".planning" / "evidence"
            state.mkdir(parents=True)
            baseline_file = state / "baseline.json"
            baseline_file.write_text(json.dumps({
                "version": 1, "project_root": str(root), "production": {}, "tests": {},
            }))
            (state / "baseline.sha256").write_text(tdd_slice.sha(baseline_file) + "\n")
            results = [mock.Mock(returncode=128), mock.Mock(returncode=0, stdout=""),
                       mock.Mock(returncode=0, stdout=""), mock.Mock(returncode=0, stdout="")]

            with mock.patch.object(tdd_slice.subprocess, "run", side_effect=results) as run:
                result = tdd_slice.cmd_probe(type("Args", (), {"state_dir": str(state)})())

            self.assertEqual(result, 0)
            self.assertEqual(run.call_args_list[1].args[0], ["git", "-C", directory, "init"])
            self.assertEqual(run.call_args_list[2].args[0], ["git", "-C", directory, "add", "."])
            self.assertEqual(run.call_args_list[3].args[0][-4:], [
                "user.email=works@example.invalid", "commit", "-m", "init commit",
            ])
            self.assertIn("/.planning/", (root / ".git" / "info" / "exclude").read_text().splitlines())
            self.assertTrue(json.loads((state / "preflight.json").read_text())["git_initialized"])

    def test_probe_rejects_a_modified_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            (state / "baseline.json").write_text(json.dumps({
                "version": 1, "project_root": directory, "production": {}, "tests": {},
            }))
            (state / "baseline.sha256").write_text("stale\n")

            with self.assertRaisesRegex(SystemExit, "baseline hash lock mismatch"):
                tdd_slice.cmd_probe(type("Args", (), {"state_dir": str(state)})())


class ProductionFingerprintTest(unittest.TestCase):
    def test_ignores_ide_metadata_including_classpath_file_and_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Main.java").write_text("class Main {}\n")
            (root / ".classpath").write_text("<classpath/>\n")
            for relative in (".idea/workspace.xml", ".vscode/settings.json", ".settings/prefs",
                             "module/.classpath/generated.xml"):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("generated\n")
            (root / "module.iml").write_text("generated\n")

            production = tdd_slice.fingerprints(root, production=True)

            self.assertEqual(set(production), {"Main.java"})

    def test_normalizes_transient_entries_from_an_existing_baseline(self):
        values = {
            "Main.java": "source",
            ".classpath": "old",
            "module/.classpath/generated.xml": "old",
            ".idea/workspace.xml": "old",
        }
        self.assertEqual(tdd_slice.normalized_production(values), {"Main.java": "source"})

    def test_keeps_real_production_changes(self):
        self.assertEqual(
            tdd_slice.normalized_production({"src/main/java/Main.java": "changed"}),
            {"src/main/java/Main.java": "changed"},
        )


class StateMachineTest(unittest.TestCase):
    def test_command_converts_evidence_path_to_string(self):
        app = Application(SCRIPTS)
        evidence = Path("plan") / "evidence"

        command = app._command(Path("plan"), {
            "evidence_dir": str(evidence),
            "project_root": "project",
            "state": "SETUP_REQUIRED",
        }, "probe", [])

        self.assertEqual(command[-2:], ["--state-dir", str(evidence)])
        self.assertTrue(all(isinstance(argument, str) for argument in command))

    def _ready_for_finalize(self, root: Path, command: list[str],
                            task_command: list[str] | None = None) -> tuple[Application, Path, Path]:
        app = Application(SCRIPTS)
        initialized = app.init(root)
        plan = Path(initialized["plan_dir"])
        current = store.load(plan)
        evidence = Path(current["evidence_dir"])
        results = evidence / "task-results"
        results.mkdir(parents=True)
        contract = {
            "version": 1,
            "requirement": str((root / "requirement.md").resolve()),
            "requirements": [{"id": "REQ-1", "statement": "behavior",
                              "acceptance_criteria": ["observable result"]}],
            "acceptance_commands": [{"id": "acceptance", "covers": ["REQ-1"],
                                     "command": command}],
        }
        (plan / "requirement-contract.json").write_text(json.dumps(contract))
        (evidence / "baseline.json").write_text("{}")
        (evidence / "preflight.json").write_text('{"passed": true}')
        (evidence / "wave-1.json").write_text('{"passed": true}')
        task_id = "REQ-1:module"
        (results / module_plan.result_filename(task_id)).write_text(json.dumps({
            "task": task_id,
            "status": "PASS",
            "test_command": task_command if task_command is not None else command,
        }))
        current.update({
            "contract_valid": True,
            "contract_review_valid": True,
            "impact_valid": True,
            "module_plan_valid": True,
            "requirements": ["REQ-1"],
            "module_tasks": [{"id": task_id, "req": "REQ-1", "module": "module"}],
            "waves": [{"tasks": [task_id]}],
            "current_wave": 1,
        })
        bind_module_plan_state(plan, current)
        store.save(plan, current)
        return app, plan, evidence

    def test_finalize_replays_acceptance_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            command = ["mvn", "-pl", "module", "-Dtest=WorksTest#behavior",
                       "-DskipTests=false", "-Dmaven.test.skip=false", "test"]
            app, plan, evidence = self._ready_for_finalize(root, command)

            junit = {"target": {"executed": 1, "failures": 0, "errors": 0}}
            with mock.patch.object(works_application, "run_command",
                                   return_value=(0, junit)) as replay:
                updated = app._finalize(plan, store.load(plan))

            self.assertEqual(replay.call_args.args[1], command)
            self.assertTrue(updated["ok"])
            verification = json.loads((evidence / "final-verification.json").read_text())
            self.assertTrue(verification["passed"])

    def test_finalize_blocks_when_acceptance_command_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            command = ["mvn", "-pl", "module", "-Dtest=WorksTest#behavior",
                       "-DskipTests=false", "-Dmaven.test.skip=false", "test"]
            app, plan, evidence = self._ready_for_finalize(root, command)
            junit = {"target": {"executed": 1, "failures": 1, "errors": 0}}

            with mock.patch.object(works_application, "run_command", return_value=(1, junit)):
                with self.assertRaises(WorksError) as caught:
                    app._finalize(plan, store.load(plan))

            self.assertEqual(caught.exception.code, "E401_ACCEPTANCE_FAILED")
            self.assertFalse(json.loads((evidence / "final-verification.json").read_text())["passed"])

    def test_finalize_rejects_wave_test_not_mapped_to_contract_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            acceptance = ["mvn", "-pl", "module", "-Dtest=WorksTest#behavior",
                          "-DskipTests=false", "-Dmaven.test.skip=false", "test"]
            unrelated = ["mvn", "-pl", "module", "-Dtest=OtherTest#other",
                         "-DskipTests=false", "-Dmaven.test.skip=false", "test"]
            app, plan, _evidence = self._ready_for_finalize(root, acceptance, unrelated)

            junit = {"target": {"executed": 1, "failures": 0, "errors": 0}}
            with mock.patch.object(works_application, "run_command",
                                   return_value=(0, junit)) as replay:
                with self.assertRaises(WorksError) as caught:
                    app._finalize(plan, store.load(plan))

            self.assertEqual(caught.exception.code, "E401_ACCEPTANCE_FAILED")
            replay.assert_not_called()

    def test_second_wave_patch_check_ignores_first_wave_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            app = Application(SCRIPTS)
            initialized = app.init(root)
            plan = Path(initialized["plan_dir"])
            current = store.load(plan)
            evidence = Path(current["evidence_dir"])
            results = evidence / "task-results"
            results.mkdir(parents=True)
            (evidence / "baseline.json").write_text("{}")
            (evidence / "preflight.json").write_text('{"passed": true}')
            (evidence / "wave-1.json").write_text('{"passed": true}')
            tasks = [{"id": "REQ-1:first", "module": "first"},
                     {"id": "REQ-1:second", "module": "second"}]
            current.update({"contract_valid": True, "contract_review_valid": True,
                            "impact_valid": True, "module_plan_valid": True,
                            "requirements": ["REQ-1"], "module_tasks": tasks,
                            "waves": [{"tasks": ["REQ-1:first"]},
                                      {"tasks": ["REQ-1:second"]}]})
            bind_module_plan_state(plan, current)
            store.save(plan, current)
            immutable = {"base_commit": "base", "patch_file": "patches/task.patch",
                         "patch_sha256": "digest", "changed_files": ["A.java"],
                         "covered_files": ["A.java"], "test_file": "ATest.java"}
            for task_id in ("REQ-1:first", "REQ-1:second"):
                token = module_plan.branch_token(task_id)
                patch_file = results / "patches" / f"{token}.patch"
                patch_file.parent.mkdir(exist_ok=True)
                patch_file.write_text(task_id)
                (results / module_plan.result_filename(task_id)).write_text(json.dumps({
                    **immutable, "task": task_id, "status": "PATCH_READY",
                    "patch_file": f"patches/{token}.patch",
                }))

            with mock.patch.object(Application, "_signature", return_value="signature"), \
                    mock.patch.object(works_application.subprocess, "run",
                                      return_value=mock.Mock(returncode=0, stdout="")):
                updated = app.run(root, "patch-check", [])

            marker = json.loads((evidence / "patch-set-2.json").read_text())
            self.assertEqual(set(marker["candidate_projections"]), {"REQ-1:second"})
            self.assertEqual(set(marker["candidate_hashes"]), {
                "task-results/patches/REQ-1-second.patch",
            })
            self.assertEqual(updated["next_action"]["id"], "apply-patches-and-verify-wave")

    def test_patch_check_signature_changes_when_candidate_is_corrected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            plan = root / ".planning"
            results = plan / "evidence" / "task-results"
            results.mkdir(parents=True)
            candidate = results / module_plan.result_filename("REQ-1:user")
            candidate.write_text('{"task":"REQ-1:user","patch_sha256":"bad"}')
            command = [sys.executable, str(SCRIPTS / "module_plan.py"), "verify-patches",
                       "--file", str(plan / "module-plan.json"),
                       "--results-dir", str(results), "--wave", "1"]

            first = Application._signature(root, command)
            candidate.write_text('{"task":"REQ-1:user","patch_sha256":"fixed"}')
            second = Application._signature(root, command)

            self.assertNotEqual(first, second)

    def test_signature_serializes_windows_path_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            command = [PureWindowsPath(r"C:\tools\python.exe"),
                       PureWindowsPath(r"C:\work\module_plan.py"), "validate"]

            signature = Application._signature(root, command)

            self.assertRegex(signature, r"^[0-9a-f]{64}$")

    def test_module_plan_exposes_parallel_wave_tasks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            app = Application(SCRIPTS)
            initialized = app.init(root)
            plan = Path(initialized["plan_dir"])
            current = store.load(plan)
            evidence = Path(current["evidence_dir"])
            evidence.mkdir()
            (evidence / "baseline.json").write_text("{}")
            (evidence / "preflight.json").write_text('{"passed": true}')
            current.update({"contract_valid": True, "contract_review_valid": True, "impact_valid": True,
                            "requirements": ["REQ-1"]})
            store.save(plan, current)
            updated = app.status(root)
            self.assertEqual(updated["state"], "MODULE_PLAN_REQUIRED")
            self.assertEqual(updated["next_action"]["id"], "module-plan-init")
            current.update({"module_plan_valid": True,
                            "module_tasks": [{"id": "REQ-1:user", "module": "user"},
                                             {"id": "REQ-1:order", "module": "order"}],
                            "waves": [{"tasks": ["REQ-1:user", "REQ-1:order"]}]})
            bind_module_plan_state(plan, current)
            store.save(plan, current)
            updated = app.status(root)
            self.assertEqual(updated["state"], "WAVE_EXECUTION_REQUIRED")
            self.assertEqual(updated["next_action"]["id"], "dispatch-subagents-and-check-patches")
            self.assertTrue(updated["next_action"]["parallel"])
            self.assertEqual([task["id"] for task in updated["next_action"]["tasks"]],
                             ["REQ-1:user", "REQ-1:order"])
            candidate = evidence / "task-results" / "patches" / "candidate.patch"
            candidate.parent.mkdir(parents=True)
            candidate.write_text("patch")
            digest = module_plan.hashlib.sha256(candidate.read_bytes()).hexdigest()
            result = evidence / "task-results" / "candidate.json"
            immutable = {"task": "REQ-1:user", "base_commit": "base",
                         "patch_file": "patches/candidate.patch", "patch_sha256": digest,
                         "changed_files": ["user/A.java"], "covered_files": ["user/A.java"],
                         "test_file": "user/src/test/UserWorksTest.java"}
            result.write_text(json.dumps({**immutable, "status": "PATCH_READY"}))
            projection = json.dumps(immutable, sort_keys=True, separators=(",", ":")).encode()
            order_result = evidence / "task-results" / "order.json"
            order_immutable = {**immutable, "task": "REQ-1:order"}
            order_result.write_text(json.dumps({**order_immutable, "status": "PATCH_READY"}))
            order_projection = json.dumps(order_immutable, sort_keys=True, separators=(",", ":")).encode()
            (evidence / "patch-set-1.json").write_text(json.dumps({
                "passed": True, "wave": 1,
                "candidate_hashes": {"task-results/patches/candidate.patch": digest},
                "candidate_projections": {"REQ-1:user": {
                    "file": "task-results/candidate.json",
                    "sha256": module_plan.hashlib.sha256(projection).hexdigest(),
                }, "REQ-1:order": {
                    "file": "task-results/order.json",
                    "sha256": module_plan.hashlib.sha256(order_projection).hexdigest(),
                }},
            }))
            updated = app.status(root)
            self.assertEqual(updated["next_action"]["id"], "apply-patches-and-verify-wave")
            self.assertFalse(updated["next_action"]["parallel"])
            result.write_text(json.dumps({**immutable, "status": "PASS", "commit": "abc"}))
            updated = app.status(root)
            self.assertEqual(updated["next_action"]["id"], "apply-patches-and-verify-wave")
            immutable["patch_file"] = "patches/evil.patch"
            result.write_text(json.dumps({**immutable, "status": "PASS", "commit": "abc"}))
            updated = app.status(root)
            self.assertEqual(updated["next_action"]["id"], "dispatch-subagents-and-check-patches")
            immutable["patch_file"] = "patches/candidate.patch"
            result.write_text(json.dumps({**immutable, "status": "PASS", "commit": "abc"}))
            candidate.write_text("tampered")
            updated = app.status(root)
            self.assertEqual(updated["next_action"]["id"], "dispatch-subagents-and-check-patches")

    def test_single_state_file_drives_setup_and_impact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            app = Application(SCRIPTS)
            initialized = app.init(root)
            plan = Path(initialized["plan_dir"])
            self.assertEqual(initialized["state"], "SETUP_REQUIRED")
            self.assertTrue((plan / "state.json").is_file())
            self.assertFalse((plan / "task_plan.md").exists())
            current = store.load(plan)
            evidence = Path(current["evidence_dir"])
            evidence.mkdir()
            (evidence / "baseline.json").write_text("{}")
            (evidence / "preflight.json").write_text('{"passed": true}')
            updated = app.status(root)
            self.assertEqual(updated["state"], "CONTRACT_REQUIRED")
            self.assertEqual(updated["next_action"]["id"], "contract-init")
            app.run(root, "contract-init", [])
            contract = plan / "requirement-contract.json"
            contract.write_text(json.dumps({
                "version": 1,
                "requirement": str((root / "requirement.md").resolve()),
                "requirements": [{"id": "REQ-1", "statement": "behavior",
                                  "acceptance_criteria": ["observable result"]}],
                "acceptance_commands": [{"id": "module-tests", "covers": ["REQ-1"],
                                         "command": ["mvn", "-pl", "module",
                                                     "-Dtest=WorksTest#behavior", "-DskipTests=false",
                                                     "-Dmaven.test.skip=false", "test"]}],
            }))
            updated = app.run(root, "contract-check", [])
            self.assertEqual(updated["state"], "CONTRACT_REVIEW_REQUIRED")
            self.assertEqual(updated["requirements"], ["REQ-1"])
            self.assertEqual(updated["next_action"]["id"], "contract-review-init")
            review_gate = app.run(root, "contract-review-init", [])
            self.assertEqual(review_gate["next_action"]["id"], "complete-contract-review")
            self.assertEqual(review_gate["next_action"]["kind"], "subagent-review")
            self.assertEqual(review_gate["next_action"]["skill"], "impl-validator")
            self.assertEqual(review_gate["allowed_actions"], ["contract-review-submit"])
            with self.assertRaises(WorksError) as caught:
                app.run(root, "contract-review-check", [])
            self.assertEqual(caught.exception.code, "E202_INVALID_STATE")
            review = plan / "contract-review.json"
            value = json.loads(review.read_text())
            value["requirements"][0]["status"] = "PASS"
            payload = root / "contract-review-payload.json"
            payload.write_text(json.dumps({**value, "result": "APPROVED"}))
            with self.assertRaises(WorksError) as caught:
                app.run(root, "contract-review-submit", ["--input", str(payload)])
            self.assertEqual(caught.exception.code, "E303_CONTRACT_REVIEW_FAILED")
            self.assertEqual(json.loads(review.read_text())["result"], "")

            payload.write_text(json.dumps({**value, "result": "PASS"}))
            submitted = app.run(root, "contract-review-submit", ["--input", str(payload)])
            self.assertEqual(submitted["next_action"]["id"], "contract-review-check")
            updated = app.run(root, "contract-review-check", [])
            self.assertEqual(updated["state"], "IMPACT_REQUIRED")
            self.assertEqual(updated["next_action"]["id"], "impact-init")
            self.assertTrue((plan / "summaries" / "contract-check.json").is_file())

    def test_invalid_transition_blocks_red(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            app = Application(SCRIPTS)
            app.init(root)
            with self.assertRaises(WorksError) as caught:
                app.run(root, "red", [])
            self.assertEqual(caught.exception.code, "E202_INVALID_STATE")

    def test_failed_finalization_exposes_autonomous_repair_action(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            app = Application(SCRIPTS)
            initialized = app.init(root)
            plan = Path(initialized["plan_dir"])
            current = store.load(plan)
            evidence = Path(current["evidence_dir"])
            evidence.mkdir()
            (evidence / "baseline.json").write_text("{}")
            (evidence / "preflight.json").write_text('{"passed": true}')
            current.update({"contract_valid": True, "contract_review_valid": True, "impact_valid": True,
                            "module_plan_valid": True, "requirements": ["REQ-1"],
                            "waves": [{"tasks": ["REQ-1:module"]}],
                            "module_tasks": [{"id": "REQ-1:module"}]})
            bind_module_plan_state(plan, current)
            (evidence / "wave-1.json").write_text('{"passed": true}')
            (evidence / "final-verification.json").write_text('{"passed": false}')
            store.save(plan, current)
            updated = app.status(root)
            self.assertEqual(updated["state"], "READY_FOR_ACCEPTANCE")
            self.assertEqual(updated["next_action"]["id"], "diagnose-and-reopen-failing-requirement")
            repaired = app.run(root, "reopen", ["--req", "REQ-1"])
            self.assertEqual(repaired["state"], "MODULE_PLAN_REQUIRED")
            self.assertIsNone(repaired["current_req"])
            self.assertEqual(repaired["requirements"], ["REQ-1", "REQ-1.repair-1"])

    def test_complete_requires_passing_implementation_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            app = Application(SCRIPTS)
            initialized = app.init(root)
            plan = Path(initialized["plan_dir"])
            current = store.load(plan)
            evidence = Path(current["evidence_dir"])
            (evidence / "slices" / "REQ-1").mkdir(parents=True)
            for name, value in (("baseline.json", {}), ("preflight.json", {"passed": True}),
                                ("code-first-verify.json", {"passed": True}),
                                ("final-verification.json", {"passed": True})):
                (evidence / name).write_text(json.dumps(value))
            (evidence / "slices" / "REQ-1" / "test.json").write_text("{}")
            (plan / "requirement-contract.json").write_text(json.dumps({"requirements": [{"id": "REQ-1"}]}))
            current.update({"contract_valid": True, "contract_review_valid": True, "impact_valid": True,
                            "module_plan_valid": True, "implementation_review_valid": False,
                            "requirements": ["REQ-1"], "waves": [{"tasks": ["REQ-1:module"]}],
                            "module_tasks": [{"id": "REQ-1:module"}]})
            bind_module_plan_state(plan, current)
            (evidence / "wave-1.json").write_text('{"passed": true}')
            store.save(plan, current)
            updated = app.status(root)
            self.assertEqual(updated["state"], "IMPLEMENTATION_REVIEW_REQUIRED")
            review_gate = app.run(root, "implementation-review-init", [])
            self.assertEqual(review_gate["next_action"]["id"], "complete-implementation-review")
            self.assertEqual(review_gate["next_action"]["kind"], "subagent-review")
            self.assertEqual(review_gate["next_action"]["skill"], "impl-validator")
            self.assertEqual(review_gate["allowed_actions"], ["implementation-review-submit"])
            with self.assertRaises(WorksError) as caught:
                app.run(root, "implementation-review-check", [])
            self.assertEqual(caught.exception.code, "E202_INVALID_STATE")
            review = plan / "implementation-review.json"
            (root / "A.java").write_text("class A {}\n")
            (root / "ATest.java").write_text("class ATest {}\n")
            value = json.loads(review.read_text())
            value.update({"result": "PASS"})
            value["requirements"][0].update({
                "status": "PASS",
                "implementation": [{"path": "A.java", "line": 1, "symbol": "A",
                                    "reason": "implements REQ-1"}],
                "tests": [{"path": "ATest.java", "line": 1, "symbol": "ATest",
                           "reason": "tests REQ-1"}],
            })
            payload = root / "implementation-review-payload.json"
            payload.write_text(json.dumps(value))
            submitted = app.run(root, "implementation-review-submit", ["--input", str(payload)])
            self.assertEqual(submitted["next_action"]["id"], "implementation-review-check")
            updated = app.run(root, "implementation-review-check", [])
            self.assertEqual(updated["state"], "COMPLETE")

    def test_failed_contract_review_can_be_revised_and_passed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            app = Application(SCRIPTS)
            initialized = app.init(root)
            plan = Path(initialized["plan_dir"])
            current = store.load(plan)
            evidence = Path(current["evidence_dir"])
            evidence.mkdir()
            (evidence / "baseline.json").write_text("{}")
            (evidence / "preflight.json").write_text('{"passed": true}')
            contract = {"version": 1, "requirement": str((root / "requirement.md").resolve()),
                        "requirements": [{"id": "REQ-1", "statement": "behavior",
                                          "acceptance_criteria": ["result"]}],
                        "acceptance_commands": [{"id": "tests", "covers": ["REQ-1"],
                                                 "command": ["mvn", "-pl", "module",
                                                             "-Dtest=WorksTest#behavior", "-DskipTests=false",
                                                             "-Dmaven.test.skip=false", "test"]}]}
            (plan / "requirement-contract.json").write_text(json.dumps(contract))
            app.run(root, "contract-check", [])
            app.run(root, "contract-review-init", [])
            review = plan / "contract-review.json"
            failed = json.loads(review.read_text())
            failed.update({"result": "FAIL", "missing": ["behavior"]})
            failed["requirements"][0].update({"status": "FAIL", "finding": "missing behavior"})
            payload = root / "failed-contract-review.json"
            payload.write_text(json.dumps(failed))
            submitted = app.run(root, "contract-review-submit", ["--input", str(payload)])
            self.assertEqual(submitted["next_action"]["id"], "revise-contract-and-rerun-review")
            contract["requirements"][0]["statement"] = "revised behavior"
            (plan / "requirement-contract.json").write_text(json.dumps(contract))
            app.run(root, "contract-check", [])
            app.run(root, "contract-review-init", [])
            passed = json.loads(review.read_text())
            passed["result"] = "PASS"
            passed["requirements"][0]["status"] = "PASS"
            passed_payload = root / "passed-contract-review.json"
            passed_payload.write_text(json.dumps(passed))
            app.run(root, "contract-review-submit", ["--input", str(passed_payload)])
            updated = app.run(root, "contract-review-check", [])
            self.assertEqual(updated["state"], "IMPACT_REQUIRED")

    def test_records_notes_and_recovers_last_activity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            app = Application(SCRIPTS)
            initialized = app.init(root)
            app.run(root, "note", ["--kind", "finding", "--text", "found service seam"])
            recovered = app.recover(root)
            self.assertTrue(recovered["recovered"])
            self.assertEqual(recovered["last_activity"]["action"], "note")
            self.assertTrue(Path(recovered["memory"]["findings"]).is_file())

    def test_empty_contract_requires_completion_before_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            app = Application(SCRIPTS)
            initialized = app.init(root)
            plan = Path(initialized["plan_dir"])
            current = store.load(plan)
            evidence = Path(current["evidence_dir"])
            evidence.mkdir()
            (evidence / "baseline.json").write_text("{}")
            (evidence / "preflight.json").write_text('{"passed": true}')
            initialized = app.run(root, "contract-init", [])

            self.assertEqual(initialized["next_action"]["id"], "complete-contract")
            self.assertEqual(initialized["next_action"]["kind"], "workspace-edit")
            self.assertEqual(initialized["allowed_actions"], [])
            with self.assertRaises(WorksError) as caught:
                app.run(root, "contract-check", [])
            self.assertEqual(caught.exception.code, "E202_INVALID_STATE")

            (plan / "requirement-contract.json").write_text(json.dumps({
                "version": 1,
                "requirement": str((root / "requirement.md").resolve()),
                "requirements": [{"id": "REQ-1", "statement": "behavior",
                                  "acceptance_criteria": ["observable result"]}],
                "acceptance_commands": [{
                    "id": "module-tests", "covers": ["REQ-1"],
                    "command": ["mvn", "-pl", "module", "-Dtest=WorksTest#behavior",
                                "-DskipTests=false", "-Dmaven.test.skip=false", "test"],
                }],
            }))

            ready = app.status(root)
            self.assertEqual(ready["next_action"]["id"], "contract-check")
            self.assertEqual(ready["allowed_actions"], ["contract-check"])
            checked = app.run(root, "contract-check", [])
            self.assertEqual(checked["state"], "CONTRACT_REVIEW_REQUIRED")

    def test_impact_template_requires_edit_and_failed_validation_returns_to_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            app = Application(SCRIPTS)
            initialized = app.init(root)
            plan = Path(initialized["plan_dir"])
            current = store.load(plan)
            evidence = Path(current["evidence_dir"])
            evidence.mkdir()
            (evidence / "baseline.json").write_text("{}")
            (evidence / "preflight.json").write_text('{"passed": true}')
            current.update({"contract_valid": True, "contract_review_valid": True,
                            "requirements": ["REQ-1"]})
            store.save(plan, current)

            initialized = app.run(root, "impact-init", [])
            self.assertEqual(initialized["next_action"]["id"], "complete-impact-map")
            self.assertEqual(initialized["allowed_actions"], [])

            artifact = plan / "impact-map.json"
            value = json.loads(artifact.read_text())
            value["requirements"][0]["behavior"] = "incomplete"
            artifact.write_text(json.dumps(value))
            ready = app.status(root)
            self.assertEqual(ready["next_action"]["id"], "impact-check")
            with self.assertRaises(WorksError) as caught:
                app.run(root, "impact-check", [])
            self.assertEqual(caught.exception.code, "E301_INVALID_IMPACT_MAP")

            repair = app.status(root)
            self.assertEqual(repair["next_action"]["id"], "complete-impact-map")
            self.assertEqual(repair["allowed_actions"], [])
            self.assertIn("violations", repair["next_action"]["previous_validation"]["output"])
            artifact.write_text(json.dumps(value, indent=2))
            self.assertEqual(app.status(root)["next_action"]["id"], "impact-check")

    def test_module_plan_template_requires_edit_and_failed_validation_returns_to_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            app = Application(SCRIPTS)
            initialized = app.init(root)
            plan = Path(initialized["plan_dir"])
            current = store.load(plan)
            evidence = Path(current["evidence_dir"])
            evidence.mkdir()
            (evidence / "baseline.json").write_text("{}")
            (evidence / "preflight.json").write_text('{"passed": true}')
            current.update({"contract_valid": True, "contract_review_valid": True,
                            "impact_valid": True, "requirements": ["REQ-1"]})
            store.save(plan, current)
            (plan / "impact-map.json").write_text(json.dumps({
                "version": 1, "requirements": [],
            }))
            (plan / "requirement-contract.json").write_text(json.dumps({
                "version": 1, "requirements": [], "acceptance_commands": [],
            }))

            initialized = app.run(root, "module-plan-init", [])
            self.assertEqual(initialized["next_action"]["id"], "complete-module-plan")
            self.assertEqual(initialized["allowed_actions"], [])

            artifact = plan / "module-plan.json"
            value = json.loads(artifact.read_text())
            value["tasks"] = [{}]
            artifact.write_text(json.dumps(value))
            self.assertEqual(app.status(root)["next_action"]["id"], "module-plan-check")
            with self.assertRaises(WorksError) as caught:
                app.run(root, "module-plan-check", [])
            self.assertEqual(caught.exception.code, "E305_INVALID_MODULE_PLAN")

            repair = app.status(root)
            self.assertEqual(repair["next_action"]["id"], "complete-module-plan")
            self.assertEqual(repair["allowed_actions"], [])
            self.assertIn("violations", repair["next_action"]["previous_validation"]["output"])
            artifact.write_text(json.dumps(value, indent=2))
            self.assertEqual(app.status(root)["next_action"]["id"], "module-plan-check")


class ImpactMapTest(unittest.TestCase):
    def test_allows_no_identified_risks_but_rejects_invalid_risk_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "Controller.java").write_text("class Controller {}\n")
            data = impact_map.template(["REQ-1"])
            row = data["requirements"][0]
            row.update({"behavior": "download", "entrypoints": ["Controller.java:1"],
                        "service_apis": ["Controller.java:1"],
                        "persistence": ["Controller.java:1"],
                        "test_seams": [{"boundary": "Controller.java:1",
                                        "planned_test": "src/test/java/ControllerTest.java"}],
                        "risks": []})

            self.assertEqual(impact_map.validate(data, project, ["REQ-1"]), [])
            for invalid in ([""], [None], [42]):
                with self.subTest(risks=invalid):
                    row["risks"] = invalid
                    errors = impact_map.validate(data, project, ["REQ-1"])
                    self.assertTrue(any("risks must be" in error for error in errors), errors)

    def test_requires_real_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "Controller.java").write_text("class Controller {}")
            data = impact_map.template(["REQ-1"])
            self.assertTrue(impact_map.validate(data, project, ["REQ-1"]))
            row = data["requirements"][0]
            row.update({"behavior": "download", "entrypoints": ["Controller.java:1"],
                        "service_apis": ["Controller.java:1"], "persistence": ["Controller.java:1"],
                        "test_seams": [{
                            "boundary": "Controller.java:1",
                            "planned_test": "src/test/java/ControllerTest.java",
                        }], "risks": ["compatibility"]})
            self.assertEqual(impact_map.validate(data, project, ["REQ-1"]), [])

    def test_allows_planned_test_file_to_not_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "Service.java").write_text("class Service {}\n")
            self.assertTrue(impact_map.boundary_evidence(project, "Service.java:1"))
            self.assertTrue(impact_map.planned_test_path(
                project, "module/src/test/java/example/ServiceTest.java"))

    def test_rejects_missing_or_invalid_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "Service.java").write_text("class Service {}\n")
            self.assertFalse(impact_map.boundary_evidence(project, "Missing.java:1"))
            self.assertFalse(impact_map.boundary_evidence(project, "Service.java:2"))
            self.assertFalse(impact_map.boundary_evidence(project, "Service.java"))

    def test_rejects_unsafe_or_non_test_planned_path(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            self.assertFalse(impact_map.planned_test_path(project, "../ServiceTest.java"))
            self.assertFalse(impact_map.planned_test_path(project, "src/main/java/ServiceTest.java"))
            self.assertFalse(impact_map.planned_test_path(project, "src/test/java/Service.java"))

    def test_rejects_legacy_string_test_seam(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "Controller.java").write_text("class Controller {}\n")
            data = impact_map.template(["REQ-1"])
            data["requirements"][0].update({
                "behavior": "download", "entrypoints": ["Controller.java:1"],
                "service_apis": ["Controller.java:1"], "persistence": ["Controller.java:1"],
                "test_seams": ["Controller.java:1"], "risks": ["compatibility"],
            })
            errors = impact_map.validate(data, project, ["REQ-1"])
            self.assertTrue(any("must contain exactly boundary and planned_test" in error
                                for error in errors))


class RequirementContractTest(unittest.TestCase):
    @staticmethod
    def _contract(requirement: Path, command: list[str], ids: list[str] | None = None) -> dict:
        ids = ids or ["REQ-1"]
        return {
            "version": 1,
            "requirement": str(requirement.resolve()),
            "requirements": [{"id": req, "statement": f"behavior {req}",
                              "acceptance_criteria": [f"result {req}"]} for req in ids],
            "acceptance_commands": [{"id": "tests", "covers": ids, "command": command}],
        }

    def test_requires_full_command_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            requirement = Path(directory) / "requirement.md"
            requirement.write_text("# Requirement")
            data = requirement_contract.template(requirement)
            data["requirements"] = [{"id": "REQ-1", "statement": "behavior",
                                     "acceptance_criteria": ["result"]}]
            self.assertTrue(requirement_contract.validate(data, requirement))
            data["acceptance_commands"] = [{"id": "tests", "covers": ["REQ-1"],
                                            "command": ["mvn", "-pl", "module",
                                                        "-Dtest=WorksTest#behavior", "-DskipTests=false",
                                                        "-Dmaven.test.skip=false", "test"]}]
            self.assertEqual(requirement_contract.validate(data, requirement), [])

    def test_rejects_trivial_success_command(self):
        with tempfile.TemporaryDirectory() as directory:
            requirement = Path(directory) / "requirement.md"
            requirement.write_text("# Requirement")
            data = requirement_contract.template(requirement)
            data["requirements"] = [{"id": "REQ-1", "statement": "behavior",
                                     "acceptance_criteria": ["result"]}]
            data["acceptance_commands"] = [{"id": "done", "covers": ["REQ-1"],
                                            "command": ["true"]}]
            errors = requirement_contract.validate(data, requirement)
            self.assertTrue(any("Maven" in error for error in errors))

    def test_rejects_non_exact_maven_acceptance_commands(self):
        valid = ["mvn", "-pl", "module", "-Dtest=WorksTest#behavior",
                 "-DskipTests=false", "-Dmaven.test.skip=false", "test"]
        invalid = {
            "multiple modules": ["mvn", "-pl", "a,b", *valid[3:]],
            "trailing argument": [*valid, "unexpected"],
            "multiple selectors": [*valid[:-1], "-Dtest=OtherTest#other", "test"],
            "empty module": ["mvn", "-pl", "", *valid[3:]],
            "empty selector": ["mvn", "-pl", "module", "-Dtest=", *valid[4:]],
        }
        with tempfile.TemporaryDirectory() as directory:
            requirement = Path(directory) / "requirement.md"
            requirement.write_text("# Requirement")
            for label, command in invalid.items():
                with self.subTest(label=label):
                    errors = requirement_contract.validate(
                        self._contract(requirement, command), requirement)
                    self.assertTrue(
                        any("target one Maven module and exact testcase" in error for error in errors),
                        errors,
                    )

    def test_requirement_ids_must_be_in_natural_order(self):
        command = ["mvn", "-pl", "module", "-Dtest=WorksTest#behavior",
                   "-DskipTests=false", "-Dmaven.test.skip=false", "test"]
        with tempfile.TemporaryDirectory() as directory:
            requirement = Path(directory) / "requirement.md"
            requirement.write_text("# Requirement")
            ordered = self._contract(requirement, command, ["REQ-2", "REQ-10"])
            reversed_ids = self._contract(requirement, command, ["REQ-10", "REQ-2"])

            self.assertEqual(requirement_contract.validate(ordered, requirement), [])
            errors = requirement_contract.validate(reversed_ids, requirement)
            self.assertTrue(any("ordered" in error for error in errors), errors)


class ReviewEvidenceTest(unittest.TestCase):
    def test_implementation_review_requires_code_and_test_evidence(self):
        data = review_evidence.template("implementation", ["REQ-1"])
        data["result"] = "PASS"
        data["requirements"][0]["status"] = "PASS"
        errors = review_evidence.validate(data, "implementation", ["REQ-1"])
        self.assertTrue(any("implementation evidence" in error for error in errors))
        self.assertTrue(any("test evidence" in error for error in errors))

    def test_implementation_review_validates_structured_locations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "A.java").write_text("class A {}\n")
            (root / "ATest.java").write_text("class ATest {}\n")
            data = review_evidence.template("implementation", ["REQ-1"])
            data["result"] = "PASS"
            data["requirements"][0].update({
                "status": "PASS",
                "implementation": [{"path": "A.java", "line": 1, "symbol": "A",
                                    "reason": "implements REQ-1"}],
                "tests": [{"path": "ATest.java", "line": 1, "symbol": "ATest",
                           "reason": "tests REQ-1"}],
            })
            self.assertEqual(review_evidence.validate(data, "implementation", ["REQ-1"], root), [])

    def test_implementation_review_rejects_fake_or_escaping_locations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "A.java").write_text("class A {}\n")
            data = review_evidence.template("implementation", ["REQ-1"])
            data["result"] = "PASS"
            data["requirements"][0].update({
                "status": "PASS",
                "implementation": [{"path": "A.java", "line": 99, "symbol": "A",
                                    "reason": "fake line"}],
                "tests": [{"path": "../outside.java", "line": 1, "symbol": "Outside",
                           "reason": "outside project"}],
            })
            errors = review_evidence.validate(data, "implementation", ["REQ-1"], root)
            self.assertTrue(any("exceeds file length" in error for error in errors))
            self.assertTrue(any("escapes the project root" in error for error in errors))

    def test_implementation_review_rejects_legacy_string_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = review_evidence.template("implementation", ["REQ-1"])
            data["result"] = "PASS"
            data["requirements"][0].update({"status": "PASS", "implementation": ["A.java:1"],
                                               "tests": ["ATest.java:1"]})
            errors = review_evidence.validate(data, "implementation", ["REQ-1"], root)
            self.assertEqual(sum("must be an object" in error for error in errors), 2)

    def test_contract_review_rejects_missing_requirement(self):
        data = review_evidence.template("contract", ["REQ-1"])
        data.update({"result": "PASS", "requirements": []})
        self.assertTrue(review_evidence.validate(data, "contract", ["REQ-1"]))

    def test_review_rejects_non_object_json(self):
        self.assertEqual(review_evidence.validate([], "contract", ["REQ-1"]),
                         ["review must be a JSON object"])


class ServiceBoundaryTest(unittest.TestCase):
    def test_comments_do_not_trigger_dependency(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "UserMapper.java").write_text("interface UserMapper {}")
            controller = root / "UserController.java"
            controller.write_text("class UserController { /* UserMapper mapper; */ }")
            self.assertEqual(service_boundary.violations(root)[0], {})
            controller.write_text("class UserController { private UserMapper mapper; }")
            self.assertIn("UserController.java|UserMapper", service_boundary.violations(root)[0])


class ModulePlanTest(unittest.TestCase):
    @staticmethod
    def _task(task_id: str = "REQ-1:user", req: str = "REQ-1",
              module: str = "user") -> dict:
        prefix = "" if module == "." else f"{module}/"
        return {
            "id": task_id, "req": req, "module": module, "depends_on": [],
            "write_scope": [f"{prefix}src/main"],
            "changed_behaviors": ["observable behavior"],
            "database_dependencies": [],
        }

    @classmethod
    def _plan(cls, tasks: list[dict], requirements: list[str] | None = None,
              max_parallel: object = 4) -> dict:
        return {
            "version": 1, "max_parallel": max_parallel,
            "requirements": requirements or ["REQ-1"], "tasks": tasks,
            "waves": [{"tasks": [task["id"] for task in tasks]}],
        }

    def test_module_must_be_safe_project_relative_path_but_root_dot_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory, \
                tempfile.TemporaryDirectory() as external_directory:
            root = Path(directory)
            (root / "pom.xml").write_text("<project/>")
            (root / "user").mkdir()
            (root / "user/pom.xml").write_text("<project/>")
            external = Path(external_directory)
            (external / "pom.xml").write_text("<project/>")

            root_plan = self._plan([self._task("REQ-1:root", module=".")])
            self.assertEqual(module_plan.validate(root_plan, root, ["REQ-1"]), [])

            invalid_modules = (str(external.resolve()), "../" + external.name, "")
            for invalid in invalid_modules:
                with self.subTest(module=invalid):
                    plan = self._plan([self._task(module=invalid)])
                    errors = module_plan.validate(plan, root, ["REQ-1"])
                    self.assertTrue(any("module" in error for error in errors), errors)

    def test_module_plan_action_lists_valid_project_relative_module_choices(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pom.xml").write_text("<project/>")
            (root / "services/user-service").mkdir(parents=True)
            (root / "services/user-service/pom.xml").write_text("<project/>")
            (root / "target/generated").mkdir(parents=True)
            (root / "target/generated/pom.xml").write_text("<project/>")

            action = store.next_action("complete-module-plan", {
                "state": "MODULE_PLAN_REQUIRED", "project_root": str(root),
            })

            self.assertEqual(action["available_modules"], [".", "services/user-service"])
            self.assertIn("available_modules", action["module_rule"])
            self.assertEqual(action["examples"]["nested_module"], "services/user-service")

    def test_invalid_module_error_lists_available_module_choices(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "user").mkdir()
            (root / "user/pom.xml").write_text("<project/>")
            plan = self._plan([self._task(module="/absolute/user")])

            errors = module_plan.validate(plan, root, ["REQ-1"])

            self.assertTrue(any("['user']" in error for error in errors), errors)
            self.assertTrue(any("project-relative Maven module directories" in error
                                for error in errors), errors)

    def test_clean_check_ignores_tracked_planning_state_but_not_source_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            state = root / ".planning" / "works-change" / "state.json"
            state.parent.mkdir(parents=True)
            state.write_text('{"state":"SETUP_REQUIRED"}')
            subprocess.run(["git", "-C", str(root), "add", "pom.xml", "requirement.md", ".planning"],
                           check=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=works", "-c",
                            "user.email=works@example.invalid", "commit", "-qm", "baseline"], check=True)

            state.write_text('{"state":"WAVE_EXECUTION_REQUIRED"}')
            self.assertTrue(module_plan.controller_worktree_clean(root))

            (root / "pom.xml").write_text("<project><version>2</version></project>")
            self.assertFalse(module_plan.controller_worktree_clean(root))

    def test_rejects_duplicate_req_module_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "user").mkdir()
            (root / "user/pom.xml").write_text("<project/>")
            first = self._task("REQ-1:user-a")
            second = self._task("REQ-1:user-b")
            second["write_scope"] = ["user/src/generated"]
            plan = self._plan([first, second])

            errors = module_plan.validate(plan, root, ["REQ-1"])
            self.assertTrue(any("Req" in error and "module" in error for error in errors), errors)

    def test_rejects_stale_requirements_invalid_elements_duplicates_and_bool_parallelism(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "user").mkdir()
            (root / "user/pom.xml").write_text("<project/>")
            mutations = {
                "stale requirements": lambda plan: plan.update(requirements=["STALE"]),
                "changed behavior type": lambda plan: plan["tasks"][0].update(
                    changed_behaviors=[None]),
                "changed behavior duplicate": lambda plan: plan["tasks"][0].update(
                    changed_behaviors=["same", "same"]),
                "database dependency type": lambda plan: plan["tasks"][0].update(
                    database_dependencies=[None]),
                "database dependency duplicate": lambda plan: plan["tasks"][0].update(
                    database_dependencies=["Repo", "Repo"]),
                "dependency type": lambda plan: plan["tasks"][0].update(depends_on=[None]),
                "dependency duplicate": lambda plan: plan["tasks"][0].update(
                    depends_on=["missing", "missing"]),
                "write scope type": lambda plan: plan["tasks"][0].update(write_scope=[None]),
                "write scope duplicate": lambda plan: plan["tasks"][0].update(
                    write_scope=["user/src/main", "user/src/main"]),
                "boolean parallelism": lambda plan: plan.update(max_parallel=True),
            }
            for label, mutate in mutations.items():
                with self.subTest(label=label):
                    plan = self._plan([self._task()])
                    mutate(plan)
                    self.assertTrue(module_plan.validate(plan, root, ["REQ-1"]), plan)

    def test_module_plan_cli_binds_impact_modules_and_contract_modules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for module in ("user", "order"):
                (root / module / "src/main/java").mkdir(parents=True)
                (root / module / "pom.xml").write_text("<project/>")
                (root / module / "src/main/java/Service.java").write_text("class Service {}\n")
            plan = self._plan([self._task()])
            plan_file = root / "module-plan.json"
            plan_file.write_text(json.dumps(plan))
            impact = {
                "version": 1, "requirements": [{
                    "id": "REQ-1", "behavior": "change",
                    "entrypoints": ["user/src/main/java/Service.java:1"],
                    "service_apis": ["order/src/main/java/Service.java:1"],
                    "persistence": ["order/src/main/java/Service.java:1"],
                    "callers": [], "config_data_impact": [], "test_seams": [], "risks": [],
                    "architecture_exception": None,
                }],
            }
            impact_file = root / "impact-map.json"
            impact_file.write_text(json.dumps(impact))
            contract = {
                "version": 1, "requirements": [{"id": "REQ-1"}],
                "acceptance_commands": [{
                    "id": "acceptance", "covers": ["REQ-1"],
                    "command": ["mvn", "-pl", "order", "-Dtest=WorksTest#works",
                                "-DskipTests=false", "-Dmaven.test.skip=false", "test"],
                }],
            }
            contract_file = root / "requirement-contract.json"
            contract_file.write_text(json.dumps(contract))
            command = [sys.executable, str(SCRIPTS / "module_plan.py"), "validate",
                       "--file", str(plan_file), "--project-root", str(root),
                       "--impact-map", str(impact_file), "--contract", str(contract_file),
                       "--req", "REQ-1"]

            proc = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("order", proc.stdout)

    def test_modified_module_plan_invalidates_validated_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            initialized = Application(SCRIPTS).init(root)
            plan_dir = Path(initialized["plan_dir"])
            current = store.load(plan_dir)
            evidence = Path(current["evidence_dir"])
            evidence.mkdir()
            (evidence / "baseline.json").write_text("{}")
            (evidence / "preflight.json").write_text('{"passed": true}')
            plan_file = plan_dir / "module-plan.json"
            plan_file.write_text(json.dumps(self._plan([self._task(module=".")])))
            current.update({
                "requirements": ["REQ-1"], "contract_valid": True,
                "contract_review_valid": True, "impact_valid": True,
                "module_plan_valid": True,
                "module_tasks": [self._task(module=".")],
                "waves": [{"tasks": ["REQ-1:user"]}],
            })
            bind_module_plan_state(plan_dir, current)
            store.save(plan_dir, current)

            plan_file.write_text(json.dumps(self._plan([self._task(module=".")]), indent=2))
            refreshed = store.refresh(plan_dir, store.load(plan_dir))
            self.assertFalse(refreshed["module_plan_valid"])
            self.assertEqual(refreshed["state"], "MODULE_PLAN_REQUIRED")

    def test_result_filename_is_cross_platform_safe(self):
        name = module_plan.result_filename("REQ-1:user")
        self.assertNotIn(":", name)
        self.assertRegex(name, r"^REQ-1-user-[0-9a-f]{8}\.json$")

    def test_wave_replay_log_path_is_cross_platform_safe(self):
        task_id = "REQ-1:user"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            module = root / "user"
            test = module / "src/test/java/UserWorksTest.java"
            test.parent.mkdir(parents=True)
            test.write_text("import org.mockito.Mock; class UserWorksTest { @Mock Repo repo; }")
            results = root / "results"
            (results / "patches").mkdir(parents=True)
            patch = (b"diff --git a/user/src/main/java/User.java b/user/src/main/java/User.java\n"
                     b"diff --git a/user/src/test/java/UserWorksTest.java b/user/src/test/java/UserWorksTest.java\n")
            (results / "patches/task.patch").write_bytes(patch)
            (results / module_plan.result_filename(task_id)).write_text(json.dumps({
                "task": task_id, "status": "PASS", "base_commit": "base",
                "patch_file": "patches/task.patch",
                "patch_sha256": module_plan.hashlib.sha256(patch).hexdigest(),
                "commit": "merged", "changed_files": ["user/src/main/java/User.java"],
                "covered_files": ["user/src/main/java/User.java"],
                "test_file": "user/src/test/java/UserWorksTest.java",
                "testcase": "UserWorksTest#works", "database_mocks": ["Repo"],
                "test_command": ["mvn", "-pl", "user", "-Dtest=UserWorksTest#works",
                                 "-DskipTests=false", "-Dmaven.test.skip=false", "test"],
                "test_evidence": {"exit": 0, "executed": 1},
            }))
            plan = {"tasks": [{"id": task_id, "module": "user",
                                "write_scope": ["user/src/main"],
                                "database_dependencies": ["Repo"]}],
                    "waves": [{"tasks": [task_id]}]}
            junit = {"target": {"executed": 1, "failures": 0, "errors": 0}}
            with mock.patch.object(module_plan, "run_command", return_value=(0, junit)) as replay, \
                    mock.patch.object(module_plan.subprocess, "run",
                                      return_value=mock.Mock(returncode=1, stdout="")):
                module_plan.verify_wave(plan, root, results, 1, {"tests": {}})

            log_path = replay.call_args.args[2]
            self.assertNotIn(":", log_path.name)
            self.assertEqual(log_path.parent.name,
                             Path(module_plan.result_filename(task_id)).stem)

    def test_root_module_accepts_src_test_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pom.xml").write_text("<project/>")
            results = root / "results"
            (results / "patches").mkdir(parents=True)
            patch = (b"diff --git a/src/main/java/App.java b/src/main/java/App.java\n"
                     b"diff --git a/src/test/java/AppWorksTest.java b/src/test/java/AppWorksTest.java\n")
            (results / "patches/task.patch").write_bytes(patch)
            task_id = "REQ-1:root"
            (results / module_plan.result_filename(task_id)).write_text(json.dumps({
                "task": task_id, "status": "PATCH_READY", "base_commit": "base",
                "patch_file": "patches/task.patch",
                "patch_sha256": module_plan.hashlib.sha256(patch).hexdigest(),
                "changed_files": ["src/main/java/App.java"],
                "covered_files": ["src/main/java/App.java"],
                "test_file": "src/test/java/AppWorksTest.java",
            }))
            plan = {"tasks": [{"id": task_id, "module": ".",
                                "write_scope": ["src/main"]}],
                    "waves": [{"tasks": [task_id]}]}

            def git_run(command, **_kwargs):
                if command[-2:] == ["patch-id", "--stable"]:
                    return mock.Mock(returncode=0, stdout=b"patch-id base\n")
                if command[-1] == "HEAD":
                    return mock.Mock(returncode=0, stdout="base\n")
                return mock.Mock(returncode=0, stdout="")

            with mock.patch.object(module_plan.subprocess, "run", side_effect=git_run):
                errors = module_plan.verify_patches(plan, root, results, 1)
            self.assertEqual(errors, [])

    def test_validates_parallel_module_dag(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for module in ("api", "user", "order"):
                target = root / module
                target.mkdir()
                (target / "pom.xml").write_text("<project/>")
            data = {"version": 1, "max_parallel": 2, "requirements": ["REQ-1"], "tasks": [
                {"id": "REQ-1:api", "req": "REQ-1", "module": "api", "depends_on": [],
                 "write_scope": ["api/src"], "changed_behaviors": ["contract"],
                 "database_dependencies": []},
                {"id": "REQ-1:user", "req": "REQ-1", "module": "user", "depends_on": ["REQ-1:api"],
                 "write_scope": ["user/src"], "changed_behaviors": ["user"],
                 "database_dependencies": ["UserRepository"]},
                {"id": "REQ-1:order", "req": "REQ-1", "module": "order", "depends_on": ["REQ-1:api"],
                 "write_scope": ["order/src"], "changed_behaviors": ["order"],
                 "database_dependencies": ["OrderMapper"]},
            ], "waves": [{"tasks": ["REQ-1:api"]}, {"tasks": ["REQ-1:user", "REQ-1:order"]}]}
            self.assertEqual(module_plan.validate(data, root, ["REQ-1"]), [])
            data["waves"] = [{"tasks": ["REQ-1:api", "REQ-1:user"]}, {"tasks": ["REQ-1:order"]}]
            self.assertTrue(any("later wave" in error for error in module_plan.validate(data, root, ["REQ-1"])))

    def test_wave_requires_new_mockito_focused_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            module = root / "user"
            module.mkdir()
            (module / "pom.xml").write_text("<project/>")
            production = module / "src/main/java/UserService.java"
            production.parent.mkdir(parents=True)
            production.write_text("class UserService {}\n")
            test = module / "src/test/java/UserServiceWorksTest.java"
            plan = {"tasks": [{"id": "REQ-1:user", "req": "REQ-1", "module": "user",
                               "write_scope": ["user/src"],
                               "database_dependencies": ["UserRepository"]}],
                    "waves": [{"tasks": ["REQ-1:user"]}]}
            results = root / "results"
            results.mkdir()
            patch = (b"diff --git a/user/src/main/java/UserService.java b/user/src/main/java/UserService.java\n"
                     b"diff --git a/user/src/test/java/UserServiceWorksTest.java b/user/src/test/java/UserServiceWorksTest.java\n")
            patches = results / "patches"
            patches.mkdir()
            (patches / "task.patch").write_bytes(patch)
            command = ["mvn", "-pl", "user", "-Dtest=UserServiceWorksTest#works",
                       "-DskipTests=false", "-Dmaven.test.skip=false", "test"]
            result_file = results / module_plan.result_filename("REQ-1:user")
            candidate = {
                "task": "REQ-1:user", "status": "PATCH_READY", "base_commit": "base",
                "patch_file": "patches/task.patch",
                "patch_sha256": module_plan.hashlib.sha256(patch).hexdigest(),
                "changed_files": ["user/src/main/java/UserService.java"],
                "covered_files": ["user/src/main/java/UserService.java"],
                "test_file": "user/src/test/java/UserServiceWorksTest.java",
            }
            result_file.write_text(json.dumps(candidate))
            def patch_check_git(command, **_kwargs):
                if command[-2:] == ["patch-id", "--stable"]:
                    return mock.Mock(returncode=0, stdout=b"candidate-id 0000000\n")
                if "status" in command and "--porcelain" in command:
                    return mock.Mock(returncode=0, stdout="")
                return mock.Mock(returncode=0, stdout="base\n")
            with mock.patch.object(module_plan.subprocess, "run", side_effect=patch_check_git):
                self.assertEqual(module_plan.verify_patches(plan, root, results, 1), [])
            test.parent.mkdir(parents=True)
            test.write_text("""import org.mockito.Mock;\nclass UserServiceWorksTest { @Mock UserRepository repo; }\n""")
            candidate.update({
                "status": "PASS", "commit": "merged",
                "testcase": "UserServiceWorksTest#works", "database_mocks": ["UserRepository"],
                "test_command": command,
                "test_evidence": {"exit": 0, "executed": 1, "failures": 0, "errors": 0},
            })
            result_file.write_text(json.dumps(candidate))
            junit = {"target": {"executed": 1, "failures": 0, "errors": 0}, "files": []}
            def replay(_root, _command, log, _reports, _selector):
                log.parent.mkdir(parents=True, exist_ok=True)
                log.write_text("passed\n")
                return 0, junit
            commit_files = "user/src/main/java/UserService.java\nuser/src/test/java/UserServiceWorksTest.java\n"
            def git_run(command, **_kwargs):
                if command[-2:] == ["patch-id", "--stable"]:
                    return mock.Mock(returncode=0, stdout=b"same-patch-id 0000000\n")
                if "diff-tree" in command:
                    return mock.Mock(returncode=0, stdout=commit_files)
                if "diff" in command:
                    return mock.Mock(returncode=0, stdout=patch)
                if command[-1] == "merged^":
                    return mock.Mock(returncode=0, stdout="base\n")
                if command[-1] == "HEAD":
                    return mock.Mock(returncode=0, stdout="merged\n")
                return mock.Mock(returncode=0, stdout="")
            with (mock.patch.object(module_plan, "run_command", side_effect=replay),
                  mock.patch.object(module_plan.subprocess, "run", side_effect=git_run)):
                self.assertEqual(module_plan.verify_wave(plan, root, results, 1, {"tests": {}}), [])
            test.write_text("@SpringBootTest class UserServiceWorksTest {}\n")
            with (mock.patch.object(module_plan, "run_command", side_effect=replay),
                  mock.patch.object(module_plan.subprocess, "run", side_effect=git_run)):
                errors = module_plan.verify_wave(plan, root, results, 1, {"tests": {}})
            self.assertTrue(any("Mockito" in error for error in errors))
            self.assertTrue(any("real framework" in error for error in errors))

    def test_wave_rejects_non_maven_test_runner(self):
        command = ["python3", "fake.py", "-pl", "user", "-Dtest=X#works",
                   "-DskipTests=false", "-Dmaven.test.skip=false", "test"]
        runner = Path(command[0]).name.lower()
        goals = [token for token in command if token in {"test", "verify", "package", "install"}]
        self.assertNotIn(runner, {"mvn", "mvnw", "mvnw.cmd"})
        self.assertEqual(goals, ["test"])


class DiscoveryTest(unittest.TestCase):
    def test_discovers_current_maven_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            result = discover(root)
            self.assertEqual(Path(result["project"]), root)
            self.assertEqual(Path(result["requirement"]), root / "requirement.md")

    def test_prefers_windows_maven_wrapper_on_windows(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "mvnw").write_text("#!/bin/sh\n")
            (root / "mvnw.cmd").write_text("@echo off\r\n")
            self.assertEqual(discover_maven_command(root, "nt"), str(root / "mvnw.cmd"))

    def test_windows_ignores_unix_wrapper_and_falls_back_to_maven(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "mvnw").write_text("#!/bin/sh\n")
            self.assertEqual(discover_maven_command(root, "nt"), "mvn")


if __name__ == "__main__":
    unittest.main()
