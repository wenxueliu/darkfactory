from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import code_first
import requirement_contract
import service_boundary
import baseline
from works_core.application import Application, WorksError
from works_core.discovery import discover, discover_maven_command
from works_core import state as store


def project_fixture(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "pom.xml").write_text("<project/>")
    (root / "requirement.md").write_text("# Requirement")
    (root / "Controller.java").write_text("class Controller { void existing() {} }\n")


def implementation_fixture(kind: str = "existing_method") -> dict:
    absence = []
    if kind == "persistence":
        absence = [
            {"scope": "current_class", "evidence": "Controller has no equivalent method",
             "reason": "searched current class"},
            {"scope": "same_layer_service", "evidence": "no matching service API",
             "reason": "searched same-layer services"},
        ]
    return {
        "entrypoint": {"path": "Controller.java", "symbol": "Controller"},
        "reuse": {"kind": kind, "target": {"path": "Controller.java", "symbol": "existing"},
                  "reason": "reuse the existing boundary", "absence_evidence": absence},
        "test_target": {"file": "src/test/java/ATest.java", "selector": "ATest#works"},
    }


class BaselineProbeTest(unittest.TestCase):
    def test_application_can_initialize_a_project_without_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pom.xml").write_text("<project/>")
            (root / "requirement.md").write_text("# Requirement")

            initialized = Application(SCRIPTS).init(root)

            self.assertEqual(initialized["state"], "SETUP_REQUIRED")
            self.assertEqual(initialized["next_action"]["id"], "preflight")
            self.assertEqual(initialized["allowed_actions"], ["preflight"])
            self.assertFalse(initialized["discovery"]["git_managed"])
            self.assertTrue(Path(initialized["plan_dir"]).is_dir())

    def test_baseline_init_allows_a_project_without_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / ".planning" / "evidence"
            with mock.patch.object(baseline.subprocess, "run") as run:
                run.return_value.returncode = 128
                result = baseline.cmd_init(type("Args", (), {
                    "project_root": str(root), "state_dir": str(state),
                })())

            self.assertEqual(result, 0)
            baseline_data = json.loads((state / "baseline.json").read_text())
            self.assertFalse(baseline_data["git_managed"])
            self.assertEqual(baseline_data["git_status"], [])
            self.assertNotIn("tests", baseline_data)

    def test_preflight_combines_baseline_and_probe_without_building(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / ".planning" / "evidence"
            with mock.patch.object(baseline.subprocess, "run",
                                   return_value=mock.Mock(returncode=128)) as run:
                result = baseline.cmd_preflight(type("Args", (), {
                    "project_root": str(root), "state_dir": str(state),
                })())

            self.assertEqual(result, 0)
            self.assertTrue((state / "baseline.json").is_file())
            self.assertEqual(json.loads((state / "preflight.json").read_text())["baseline_mode"],
                             "fingerprint")
            self.assertTrue(all(call.args[0][-1] != "init" for call in run.call_args_list))
            self.assertTrue(all(call.args[0][0] != "mvn" for call in run.call_args_list))
            self.assertFalse((state / "baseline-compile.json").exists())
            self.assertFalse((state / "baseline-compile.log").exists())

    def test_preflight_recovers_from_a_partial_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / ".planning" / "evidence"
            with mock.patch.object(baseline.subprocess, "run",
                                   return_value=mock.Mock(returncode=128)):
                baseline.cmd_preflight(type("Args", (), {
                    "project_root": str(root), "state_dir": str(state),
                })())
                (state / "preflight.json").unlink()
                result = baseline.cmd_preflight(type("Args", (), {
                    "project_root": str(root), "state_dir": str(state),
                })())
            self.assertEqual(result, 0)

    def test_probe_only_loads_locked_baseline_without_running_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            baseline_data = {"version": 1, "project_root": directory, "production": {}}
            baseline_file = state / "baseline.json"
            baseline_file.write_text(json.dumps(baseline_data))
            (state / "baseline.sha256").write_text(baseline.sha(baseline_file) + "\n")

            with mock.patch.object(baseline.subprocess, "run") as run:
                run.return_value.returncode = 0
                result = baseline.cmd_probe(type("Args", (), {"state_dir": str(state)})())

            self.assertEqual(result, 0)
            run.assert_called_once_with(
                ["git", "-C", directory, "rev-parse", "--is-inside-work-tree"],
                stdout=baseline.subprocess.DEVNULL,
                stderr=baseline.subprocess.DEVNULL,
            )
            preflight = json.loads((state / "preflight.json").read_text())
            self.assertTrue(preflight["passed"])
            self.assertEqual(preflight["source"], "baseline")
            self.assertEqual(preflight["baseline_sha256"], baseline.sha(baseline_file))
            self.assertTrue(preflight["git_managed"])
            self.assertEqual(preflight["baseline_mode"], "git")

    def test_probe_uses_fingerprint_baseline_without_initializing_git(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            baseline_file = state / "baseline.json"
            baseline_file.write_text(json.dumps({
                "version": 1, "project_root": directory, "production": {},
            }))
            (state / "baseline.sha256").write_text(baseline.sha(baseline_file) + "\n")
            with mock.patch.object(baseline.subprocess, "run",
                                   return_value=mock.Mock(returncode=128)) as run:
                result = baseline.cmd_probe(type("Args", (), {"state_dir": str(state)})())

            self.assertEqual(result, 0)
            self.assertEqual(run.call_count, 1)
            preflight = json.loads((state / "preflight.json").read_text())
            self.assertFalse(preflight["git_managed"])
            self.assertEqual(preflight["baseline_mode"], "fingerprint")

    def test_probe_rejects_a_modified_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            (state / "baseline.json").write_text(json.dumps({
                "version": 1, "project_root": directory, "production": {},
            }))
            (state / "baseline.sha256").write_text("stale\n")

            with self.assertRaisesRegex(SystemExit, "baseline hash lock mismatch"):
                baseline.cmd_probe(type("Args", (), {"state_dir": str(state)})())


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

            production = baseline.fingerprints(root, production=True)

            self.assertEqual(set(production), {"Main.java"})

    def test_normalizes_transient_entries_from_an_existing_baseline(self):
        values = {
            "Main.java": "source",
            ".classpath": "old",
            "module/.classpath/generated.xml": "old",
            ".idea/workspace.xml": "old",
        }
        self.assertEqual(baseline.normalized_production(values), {"Main.java": "source"})

    def test_keeps_real_production_changes(self):
        self.assertEqual(
            baseline.normalized_production({"src/main/java/Main.java": "changed"}),
            {"src/main/java/Main.java": "changed"},
        )


class StateMachineTest(unittest.TestCase):
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
            (evidence / "baseline.json").write_text(json.dumps({
                "project_root": str(root), "production": {},
            }))
            (evidence / "preflight.json").write_text('{"passed": true}')
            updated = app.status(root)
            self.assertEqual(updated["state"], "CONTRACT_REQUIRED")
            self.assertEqual(updated["next_action"]["id"], "contract-init")
            app.run(root, "contract-init", [])
            authored = app.status(root)
            self.assertEqual(authored["next_action"]["id"], "complete-contract-and-check")
            self.assertIsNone(authored["next_action"]["subagent"])
            contract = plan / "requirement-contract.json"
            contract.write_text(json.dumps({
                "version": 1,
                "requirement": str((root / "requirement.md").resolve()),
                "requirements": [{"id": "REQ-1", "statement": "behavior",
                                  "source": {"heading": "Requirement", "item": "behavior"},
                                  "acceptance_criteria": ["observable result"],
                                  "implementation": implementation_fixture()}],
                "acceptance_commands": [{"id": "module-tests", "covers": ["REQ-1"],
                                         "command": ["mvn", "-DskipTests=false",
                                                     "-Dmaven.test.skip=false",
                                                     "-Dtest=ATest#works", "test"]}],
            }))
            updated = app.run(root, "contract-check", [])
            self.assertEqual(updated["state"], "READY_FOR_IMPLEMENTATION")
            self.assertEqual(updated["requirements"], ["REQ-1"])
            self.assertEqual(updated["next_action"]["id"], "checkpoint-current-implementation")
            self.assertFalse((plan / "summaries").exists())

    def test_invalid_transition_blocks_implementation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            app = Application(SCRIPTS)
            app.init(root)
            with self.assertRaises(WorksError) as caught:
                app.run(root, "implement", [])
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
            (evidence / "baseline.json").write_text(json.dumps({
                "project_root": str(root), "production": {},
            }))
            (evidence / "preflight.json").write_text('{"passed": true}')
            current.update({"contract_valid": True,
                            "requirements": ["REQ-1"]})
            (evidence / "slices" / "REQ-1").mkdir(parents=True)
            (evidence / "slices" / "REQ-1" / "test.json").write_text("{}")
            (evidence / "final-verification.json").write_text('{"passed": false}')
            store.save(plan, current)
            updated = app.status(root)
            self.assertEqual(updated["state"], "READY_FOR_ACCEPTANCE")
            self.assertEqual(updated["next_action"]["id"], "diagnose-and-reopen-failing-requirement")
            repaired = app.run(root, "reopen", ["--req", "REQ-1"])
            self.assertEqual(repaired["state"], "READY_FOR_IMPLEMENTATION")
            self.assertEqual(repaired["current_req"], "REQ-1.repair-1")
            self.assertEqual(repaired["requirements"], ["REQ-1", "REQ-1.repair-1"])

    def test_failed_req_test_routes_to_rework_without_creating_repair_req(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            app = Application(SCRIPTS)
            initialized = app.init(root)
            plan = Path(initialized["plan_dir"])
            current = store.load(plan)
            evidence = Path(current["evidence_dir"])
            slice_dir = evidence / "slices" / "REQ-1"
            slice_dir.mkdir(parents=True)
            (evidence / "baseline.json").write_text(json.dumps({"project_root": str(root)}))
            (evidence / "preflight.json").write_text('{"passed": true}')
            (slice_dir / "implementation.json").write_text('{"req": "REQ-1"}')
            (slice_dir / "test.log").write_text("failed test output")
            current.update({"contract_valid": True, "requirements": ["REQ-1"],
                            "attempts": {"test:REQ-1": {"result": "failed"}}})
            store.save(plan, current)

            status = app.status(root)
            self.assertEqual(status["next_action"]["id"], "rework-current-implementation")
            result = app.run(root, "rework", ["--req", "REQ-1", "--reason", "production-fix"])

            self.assertEqual(result["state"], "READY_FOR_IMPLEMENTATION")
            self.assertEqual(result["requirements"], ["REQ-1"])
            self.assertFalse((slice_dir / "implementation.json").exists())
            self.assertTrue(Path(result["archive"]).joinpath("implementation.json").is_file())

    def test_complete_requires_only_passing_deterministic_gates(self):
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
            current.update({"contract_valid": True, "requirements": ["REQ-1"]})
            store.save(plan, current)
            updated = app.status(root)
            self.assertEqual(updated["state"], "COMPLETE")

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

    def test_repeated_failure_is_recorded_without_signature_blocking(self):
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
            app.run(root, "contract-init", [])
            with self.assertRaises(WorksError):
                app.run(root, "contract-check", [])
            with self.assertRaises(WorksError):
                app.run(root, "contract-check", [])
            state = store.load(plan)
            self.assertEqual(state["attempts"]["contract-check:-"]["count"], 2)
            self.assertNotIn("signature", state["attempts"]["contract-check:-"])
            activity = [json.loads(line) for line in (plan / "activity.jsonl").read_text().splitlines()]
            self.assertEqual([row["result"] for row in activity[-2:]], ["failed", "failed"])


class RequirementContractTest(unittest.TestCase):
    def test_contract_paths_use_explicit_project_root_and_strip_project_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            requirement = repository / "requirement.md"
            requirement.write_text("# Requirement")
            project = repository / "service"
            project.mkdir()
            (project / "Controller.java").write_text(
                "class Controller { void existing() {} }\n")
            implementation = implementation_fixture()
            implementation["entrypoint"] = {
                "path": "service/Controller.java", "symbol": "Controller",
            }
            implementation["reuse"]["target"] = {
                "path": "service/Controller.java", "symbol": "existing",
            }
            implementation["test_target"]["file"] = "service/src/test/java/ATest.java"
            data = requirement_contract.template(requirement)
            data["requirements"] = [{
                "id": "REQ-1", "statement": "behavior",
                "source": {"heading": "Requirement", "item": "behavior"},
                "acceptance_criteria": ["result"], "implementation": implementation,
            }]
            data["acceptance_commands"] = [{
                "id": "tests", "covers": ["REQ-1"],
                "command": ["mvn", "-DskipTests=false", "-Dmaven.test.skip=false",
                            "-Dtest=ATest#works", "test"],
            }]

            self.assertTrue(requirement_contract.normalize_project_paths(data, project))
            self.assertEqual(requirement_contract.validate(data, requirement, project), [])
            self.assertEqual(implementation["entrypoint"]["path"], "Controller.java")
            self.assertEqual(implementation["reuse"]["target"]["path"], "Controller.java")
            self.assertEqual(implementation["test_target"]["file"], "src/test/java/ATest.java")

    def test_allows_a_planned_entrypoint_but_requires_existing_reuse_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            requirement = root / "requirement.md"
            requirement.write_text("# Requirement")
            (root / "Service.java").write_text("class Service { void existing() {} }\n")
            implementation = implementation_fixture()
            implementation["entrypoint"] = {
                "path": "src/main/java/NewController.java", "symbol": "create",
            }
            implementation["reuse"]["target"] = {"path": "Service.java", "symbol": "existing"}
            data = requirement_contract.template(requirement)
            data["requirements"] = [{
                "id": "REQ-1", "statement": "create endpoint",
                "source": {"heading": "Requirement", "item": "create endpoint"},
                "acceptance_criteria": ["endpoint responds"], "implementation": implementation,
            }]
            data["acceptance_commands"] = [{
                "id": "tests", "covers": ["REQ-1"],
                "command": ["mvn", "-DskipTests=false", "-Dmaven.test.skip=false",
                            "-Dtest=ATest#works", "test"],
            }]

            self.assertEqual(requirement_contract.validate(data, requirement), [])
            implementation["reuse"]["target"] = {"path": "MissingService.java", "symbol": "existing"}
            self.assertTrue(any("reuse.target.path does not exist" in error
                                for error in requirement_contract.validate(data, requirement)))

    def test_requires_full_command_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            requirement = Path(directory) / "requirement.md"
            requirement.write_text("# Requirement")
            (Path(directory) / "Controller.java").write_text(
                "class Controller { void existing() {} }\n")
            data = requirement_contract.template(requirement)
            data["requirements"] = [{"id": "REQ-1", "statement": "behavior",
                                     "source": {"heading": "Requirement", "item": "behavior"},
                                     "acceptance_criteria": ["result"],
                                     "implementation": implementation_fixture()}]
            self.assertTrue(requirement_contract.validate(data, requirement))
            data["acceptance_commands"] = [{"id": "tests", "covers": ["REQ-1"],
                                            "command": ["mvn", "-DskipTests=false",
                                                        "-Dmaven.test.skip=false",
                                                        "-Dtest=ATest#works", "test"]}]
            self.assertEqual(requirement_contract.validate(data, requirement), [])

    def test_persistence_reuse_requires_both_absence_scopes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            requirement = root / "requirement.md"
            requirement.write_text("# Requirement")
            (root / "Controller.java").write_text("class Controller { void existing() {} }\n")
            implementation = implementation_fixture(kind="persistence")
            implementation["reuse"]["absence_evidence"].pop()
            data = requirement_contract.template(requirement)
            data["requirements"] = [{"id": "REQ-1", "statement": "save",
                                     "acceptance_criteria": ["saved"],
                                     "implementation": implementation}]
            errors = requirement_contract.validate(data, requirement)
            self.assertTrue(any("requires current_class and same_layer_service" in error
                                for error in errors))

    def test_test_target_must_match_acceptance_selector(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            requirement = root / "requirement.md"
            requirement.write_text("# Requirement")
            (root / "Controller.java").write_text("class Controller { void existing() {} }\n")
            data = requirement_contract.template(requirement)
            data["requirements"] = [{"id": "REQ-1", "statement": "behavior",
                                     "acceptance_criteria": ["result"],
                                     "implementation": implementation_fixture()}]
            data["acceptance_commands"] = [{
                "id": "tests", "covers": ["REQ-1"],
                "command": ["mvn", "-DskipTests=false", "-Dmaven.test.skip=false",
                            "-Dtest=ATest#different", "test"],
            }]
            errors = requirement_contract.validate(data, requirement)
            self.assertTrue(any("test_target.selector must match" in error for error in errors))

    def test_rejects_module_wide_test_command(self):
        with tempfile.TemporaryDirectory() as directory:
            requirement = Path(directory) / "requirement.md"
            requirement.write_text("# Requirement")
            (Path(directory) / "Controller.java").write_text(
                "class Controller { void existing() {} }\n")
            data = requirement_contract.template(requirement)
            data["requirements"] = [{"id": "REQ-1", "statement": "behavior",
                                     "acceptance_criteria": ["result"],
                                     "implementation": implementation_fixture()}]
            data["acceptance_commands"] = [{"id": "tests", "covers": ["REQ-1"],
                                            "command": ["mvn", "-DskipTests=false",
                                                        "-Dmaven.test.skip=false", "test"]}]
            errors = requirement_contract.validate(data, requirement)
            self.assertTrue(any("-Dtest=Class#method" in error for error in errors))

    def test_rejects_trivial_success_command(self):
        with tempfile.TemporaryDirectory() as directory:
            requirement = Path(directory) / "requirement.md"
            requirement.write_text("# Requirement")
            (Path(directory) / "Controller.java").write_text(
                "class Controller { void existing() {} }\n")
            data = requirement_contract.template(requirement)
            data["requirements"] = [{"id": "REQ-1", "statement": "behavior",
                                     "acceptance_criteria": ["result"],
                                     "implementation": implementation_fixture()}]
            data["acceptance_commands"] = [{"id": "done", "covers": ["REQ-1"],
                                            "command": ["true"]}]
            errors = requirement_contract.validate(data, requirement)
            self.assertTrue(any("Maven" in error for error in errors))


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


class CodeFirstEvidenceTest(unittest.TestCase):
    def test_requires_implementation_before_recording_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / ".planning" / "evidence"
            state.mkdir(parents=True)
            (state / "baseline.json").write_text(json.dumps({
                "project_root": str(root), "production": {}, "tests": {},
            }))
            contract = root / "requirement-contract.json"
            contract.write_text(json.dumps({"acceptance_commands": [{
                "covers": ["REQ-1"], "command": ["mvn", "-DskipTests=false",
                                                       "-Dmaven.test.skip=false",
                                                       "-Dtest=ATest#works", "test"]
            }]}))
            args = type("Args", (), {
                "state_dir": str(state), "req": "REQ-1", "test_file": "src/test/java/ATest.java",
                "testcase": "ATest#works", "command": ["mvn", "-DskipTests=false",
                                                         "-Dmaven.test.skip=false",
                                                         "-Dtest=ATest#works", "test"],
                "contract": str(contract), "contract_req": "REQ-1",
            })()
            with self.assertRaisesRegex(SystemExit, "missing evidence"):
                code_first.cmd_test(args)

    def test_records_implementation_then_passing_maven_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / ".planning" / "evidence"
            state.mkdir(parents=True)
            source = root / "src/main/java/A.java"
            source.parent.mkdir(parents=True)
            source.write_text("class A { void existing() {} void changed() { existing(); } }\n")
            test = root / "src/test/java/ATest.java"
            test.parent.mkdir(parents=True)
            test.write_text(
                "import static org.mockito.Mockito.mock;\n"
                "class ATest { void works() { Object dependency = mock(Object.class); } }\n"
            )
            (state / "baseline.json").write_text(json.dumps({
                "project_root": str(root), "production": {}, "tests": {},
            }))
            (state / "checkpoint.json").write_text(json.dumps({
                "sequence": 0, "production": {}, "previous_req": None,
            }))
            contract = root / "requirement-contract.json"
            contract.write_text(json.dumps({"requirements": [{
                "id": "REQ-1", "implementation": {
                    "entrypoint": {"path": "src/main/java/A.java", "symbol": "changed"},
                    "reuse": {
                    "kind": "existing_method",
                    "target": {"path": "src/main/java/A.java", "symbol": "existing"},
                    "reason": "reuse existing method", "absence_evidence": [],
                }},
            }], "acceptance_commands": [{
                "covers": ["REQ-1"], "command": ["mvn", "-DskipTests=false",
                                                       "-Dmaven.test.skip=false",
                                                       "-Dtest=ATest#works", "test"]
            }]}))
            (state / "reuse-baseline.json").write_text(json.dumps({
                "persistence_invocations": {},
            }))
            implement = type("Args", (), {"state_dir": str(state), "req": "REQ-1",
                                            "contract": str(contract), "contract_req": "REQ-1"})()
            self.assertEqual(code_first.cmd_implement(implement), 0)
            command = ["mvn", "-DskipTests=false", "-Dmaven.test.skip=false",
                       "-Dtest=ATest#works", "test"]
            test_args = type("Args", (), {"state_dir": str(state), "req": "REQ-1",
                                           "test_file": "src/test/java/ATest.java",
                                           "testcase": "ATest#works", "command": [],
                                           "contract": str(contract), "contract_req": "REQ-1"})()
            junit = {"target": {"executed": 1, "failures": 0, "errors": 0}, "files": []}
            def passing_run(_root, _command, log, _reports, _testcase):
                log.write_text("passed\n")
                return 0, junit
            with mock.patch.object(code_first, "run_command", side_effect=passing_run):
                self.assertEqual(code_first.cmd_test(test_args), 0)
            self.assertTrue((state / "slices" / "REQ-1" / "implementation.json").is_file())
            self.assertTrue((state / "slices" / "REQ-1" / "test.json").is_file())

    def test_implementation_checkpoint_requires_planned_entrypoint_to_exist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contract = root / "requirement-contract.json"
            contract.write_text(json.dumps({"requirements": [{
                "id": "REQ-1", "implementation": {
                    "entrypoint": {"path": "NewController.java", "symbol": "create"},
                },
            }]}))
            with self.assertRaisesRegex(SystemExit, "implemented entrypoint does not exist"):
                code_first.require_implemented_entrypoint(contract, "REQ-1", root)
            (root / "NewController.java").write_text("class NewController { void create() {} }\n")
            self.assertEqual(
                code_first.require_implemented_entrypoint(contract, "REQ-1", root),
                {"path": "NewController.java", "symbol": "create"},
            )

    def test_implementation_rejects_ignored_service_reuse_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "Service.java"
            source.write_text("class Service { void existing() {} void changed() {} }\n")
            contract = root / "requirement-contract.json"
            contract.write_text(json.dumps({"requirements": [{
                "id": "REQ-1", "implementation": {"reuse": {
                    "kind": "service_api",
                    "target": {"path": "Service.java", "symbol": "existing"},
                    "reason": "reuse service API", "absence_evidence": [],
                }},
            }]}))
            reuse_baseline = root / "reuse-baseline.json"
            reuse_baseline.write_text(json.dumps({"persistence_invocations": {}}))
            with self.assertRaisesRegex(SystemExit, "does not use selected service_api"):
                code_first.require_reuse_decision(
                    contract, "REQ-1", root, ["Service.java"], reuse_baseline
                )

    def test_existing_method_can_be_modified_in_place(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "Controller.java"
            source.write_text("class Controller { void update() { changed(); } void changed() {} }\n")
            contract = root / "requirement-contract.json"
            target = {"path": "Controller.java", "symbol": "update"}
            contract.write_text(json.dumps({"requirements": [{
                "id": "REQ-1", "implementation": {
                    "entrypoint": target,
                    "reuse": {"kind": "existing_method", "target": target,
                              "reason": "extend the existing endpoint method",
                              "absence_evidence": []},
                },
            }]}))
            reuse_baseline = root / "reuse-baseline.json"
            reuse_baseline.write_text(json.dumps({"persistence_invocations": {}}))

            decision = code_first.require_reuse_decision(
                contract, "REQ-1", root, ["Controller.java"], reuse_baseline
            )

            self.assertEqual(decision["kind"], "existing_method")

    def test_existing_method_in_same_file_still_requires_call_when_not_entrypoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "Controller.java"
            source.write_text("class Controller { void entry() {} void helper() {} }\n")
            contract = root / "requirement-contract.json"
            contract.write_text(json.dumps({"requirements": [{
                "id": "REQ-1", "implementation": {
                    "entrypoint": {"path": "Controller.java", "symbol": "entry"},
                    "reuse": {"kind": "existing_method",
                              "target": {"path": "Controller.java", "symbol": "helper"},
                              "reason": "reuse helper", "absence_evidence": []},
                },
            }]}))
            reuse_baseline = root / "reuse-baseline.json"
            reuse_baseline.write_text(json.dumps({"persistence_invocations": {}}))

            with self.assertRaisesRegex(SystemExit, "does not use selected existing_method"):
                code_first.require_reuse_decision(
                    contract, "REQ-1", root, ["Controller.java"], reuse_baseline
                )

    def test_reuse_target_in_comment_does_not_satisfy_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "Service.java"
            source.write_text("class Service { void existing() {} void changed() { /* existing(); */ } }\n")
            contract = root / "requirement-contract.json"
            contract.write_text(json.dumps({"requirements": [{
                "id": "REQ-1", "implementation": {"reuse": {
                    "kind": "service_api",
                    "target": {"path": "Service.java", "symbol": "existing"},
                    "reason": "reuse service API", "absence_evidence": [],
                }},
            }]}))
            reuse_baseline = root / "reuse-baseline.json"
            reuse_baseline.write_text(json.dumps({"persistence_invocations": {}}))
            with self.assertRaisesRegex(SystemExit, "does not use selected service_api"):
                code_first.require_reuse_decision(
                    contract, "REQ-1", root, ["Service.java"], reuse_baseline
                )

    def test_service_reuse_decision_rejects_new_mapper_call(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "Service.java"
            source.write_text(
                "class Service { UserMapper mapper; void existing() {} "
                "void changed() { existing(); mapper.select(); } }\n"
            )
            contract = root / "requirement-contract.json"
            contract.write_text(json.dumps({"requirements": [{
                "id": "REQ-1", "implementation": {"reuse": {
                    "kind": "service_api",
                    "target": {"path": "Service.java", "symbol": "existing"},
                    "reason": "reuse service API", "absence_evidence": [],
                }},
            }]}))
            reuse_baseline = root / "reuse-baseline.json"
            reuse_baseline.write_text(json.dumps({"persistence_invocations": {}}))
            with self.assertRaisesRegex(SystemExit, "forbids new Mapper/Repository calls"):
                code_first.require_reuse_decision(
                    contract, "REQ-1", root, ["Service.java"], reuse_baseline
                )

    def test_rejects_testcase_that_drifted_from_requirement_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = Path(directory) / "requirement-contract.json"
            contract.write_text(json.dumps({"acceptance_commands": [{
                "covers": ["REQ-1"], "command": ["mvn", "-Dtest=ATest#expected", "test"]
            }]}))
            with self.assertRaisesRegex(SystemExit, "must resolve to exactly one contract"):
                code_first.resolve_contract_test_command(contract, "REQ-1", "ATest#actual")

    def test_accepts_testcase_declared_for_requirement_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = Path(directory) / "requirement-contract.json"
            contract.write_text(json.dumps({"acceptance_commands": [{
                "covers": ["REQ-1"], "command": ["mvn", "-Dtest=ATest#expected", "test"]
            }]}))
            self.assertEqual(
                code_first.resolve_contract_test_command(contract, "REQ-1", "pkg.ATest#expected"),
                ["mvn", "-Dtest=ATest#expected", "test"],
            )

    def test_resolves_windows_wrapper_argv_without_shell_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = Path(directory) / "requirement-contract.json"
            command = [r"C:\\repo\\mvnw.cmd", "-DskipTests=false", "-Dmaven.test.skip=false",
                       "-Dtest=ATest#expected", "test"]
            contract.write_text(json.dumps({"acceptance_commands": [{
                "covers": ["REQ-1"], "command": command,
            }]}))
            self.assertEqual(
                code_first.resolve_contract_test_command(contract, "REQ-1", "ATest#expected"),
                command,
            )

    def test_policy_rejects_spring_boot_test(self):
        with tempfile.TemporaryDirectory() as directory:
            test = Path(directory) / "ATest.java"
            test.write_text("import org.mockito.Mock; @SpringBootTest class ATest { @Mock Object dep; }")
            with self.assertRaisesRegex(SystemExit, "SpringBootTest is forbidden"):
                code_first.require_targeted_mockito_test(
                    test, "ATest#works", ["mvn", "-Dtest=ATest#works", "test"])

    def test_policy_allows_plain_junit_but_rejects_full_suite(self):
        with tempfile.TemporaryDirectory() as directory:
            test = Path(directory) / "ATest.java"
            test.write_text("class ATest { void works() {} }")
            policy = code_first.require_targeted_test(
                test, "ATest#works", ["mvn", "-Dtest=ATest#works", "test"])
            self.assertEqual(policy["framework"], "JUnit")
            with self.assertRaisesRegex(SystemExit, "exactly one -Dtest"):
                code_first.require_targeted_test(test, "ATest#works", ["mvn", "test"])


class DiscoveryTest(unittest.TestCase):
    def test_discovers_current_maven_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project_fixture(root)
            result = discover(root)
            self.assertEqual(Path(result["project"]), root)
            self.assertEqual(Path(result["requirement"]), root / "requirement.md")

    def test_nested_maven_project_is_used_as_preflight_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / "requirement.md").write_text("# Requirement")
            module = root / "service"
            module.mkdir()
            (module / "pom.xml").write_text("<project/>")

            result = discover(root)

            self.assertEqual(Path(result["project"]), module)
            self.assertEqual(Path(result["pom"]), module / "pom.xml")

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
