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

import impact_map
import code_first
import requirement_contract
import review_evidence
import service_boundary
import baseline
from works_core.application import Application, WorksError
from works_core.discovery import discover, discover_maven_command
from works_core import state as store


def project_fixture(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "pom.xml").write_text("<project/>")
    (root / "requirement.md").write_text("# Requirement")


class BaselineProbeTest(unittest.TestCase):
    def test_application_can_initialize_a_project_without_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pom.xml").write_text("<project/>")
            (root / "requirement.md").write_text("# Requirement")

            initialized = Application(SCRIPTS).init(root)

            self.assertEqual(initialized["state"], "SETUP_REQUIRED")
            self.assertEqual(initialized["next_action"]["id"], "baseline-init")
            self.assertEqual(initialized["allowed_actions"], ["baseline-init"])
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
            self.assertFalse(preflight["git_initialized"])

    def test_probe_initializes_and_commits_an_unmanaged_project(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            baseline_file = state / "baseline.json"
            baseline_file.write_text(json.dumps({
                "version": 1, "project_root": directory, "production": {},
            }))
            (state / "baseline.sha256").write_text(baseline.sha(baseline_file) + "\n")
            results = [mock.Mock(returncode=128), mock.Mock(returncode=0, stdout=""),
                       mock.Mock(returncode=0, stdout=""), mock.Mock(returncode=0, stdout="")]

            with mock.patch.object(baseline.subprocess, "run", side_effect=results) as run:
                result = baseline.cmd_probe(type("Args", (), {"state_dir": str(state)})())

            self.assertEqual(result, 0)
            self.assertEqual(run.call_args_list[1].args[0], ["git", "-C", directory, "init"])
            self.assertEqual(run.call_args_list[2].args[0], ["git", "-C", directory, "add", "."])
            self.assertEqual(run.call_args_list[3].args[0][-4:], [
                "user.email=works@example.invalid", "commit", "-m", "init commit",
            ])
            self.assertTrue(json.loads((state / "preflight.json").read_text())["git_initialized"])

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
            (evidence / "baseline.json").write_text("{}")
            (evidence / "preflight.json").write_text('{"passed": true}')
            updated = app.status(root)
            self.assertEqual(updated["state"], "CONTRACT_REQUIRED")
            self.assertEqual(updated["next_action"]["id"], "contract-init")
            app.run(root, "contract-init", [])
            authored = app.status(root)
            self.assertEqual(authored["next_action"]["id"], "complete-contract-and-check")
            self.assertEqual(authored["next_action"]["subagent"], "general")
            self.assertEqual(authored["next_action"]["reference"], "references/contract-author.md")
            contract = plan / "requirement-contract.json"
            contract.write_text(json.dumps({
                "version": 1,
                "requirement": str((root / "requirement.md").resolve()),
                "requirements": [{"id": "REQ-1", "statement": "behavior",
                                  "acceptance_criteria": ["observable result"]}],
                "acceptance_commands": [{"id": "module-tests", "covers": ["REQ-1"],
                                         "command": ["mvn", "-DskipTests=false",
                                                     "-Dmaven.test.skip=false",
                                                     "-Dtest=ATest#works", "test"]}],
            }))
            updated = app.run(root, "contract-check", [])
            self.assertEqual(updated["state"], "CONTRACT_REVIEW_REQUIRED")
            self.assertEqual(updated["requirements"], ["REQ-1"])
            self.assertEqual(updated["next_action"]["id"], "contract-review-init")
            app.run(root, "contract-review-init", [])
            review = plan / "contract-review.json"
            value = json.loads(review.read_text())
            value.update({"result": "PASS"})
            value["requirements"][0]["status"] = "PASS"
            review.write_text(json.dumps(value))
            updated = app.run(root, "contract-review-check", [])
            self.assertEqual(updated["state"], "IMPACT_REQUIRED")
            self.assertEqual(updated["next_action"]["id"], "impact-init")
            self.assertTrue((plan / "summaries" / "contract-check.json").is_file())

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
            (evidence / "baseline.json").write_text("{}")
            (evidence / "preflight.json").write_text('{"passed": true}')
            current.update({"contract_valid": True, "contract_review_valid": True, "impact_valid": True,
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
                            "implementation_review_valid": False, "requirements": ["REQ-1"]})
            store.save(plan, current)
            updated = app.status(root)
            self.assertEqual(updated["state"], "IMPLEMENTATION_REVIEW_REQUIRED")
            app.run(root, "implementation-review-init", [])
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
            review.write_text(json.dumps(value))
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
                                                 "command": ["mvn", "-DskipTests=false",
                                                             "-Dmaven.test.skip=false",
                                                             "-Dtest=ATest#works", "test"]}]}
            (plan / "requirement-contract.json").write_text(json.dumps(contract))
            app.run(root, "contract-check", [])
            app.run(root, "contract-review-init", [])
            review = plan / "contract-review.json"
            failed = json.loads(review.read_text())
            failed.update({"result": "CHANGES_REQUIRED", "missing": ["behavior"]})
            review.write_text(json.dumps(failed))
            with self.assertRaises(WorksError):
                app.run(root, "contract-review-check", [])
            contract["requirements"][0]["statement"] = "revised behavior"
            (plan / "requirement-contract.json").write_text(json.dumps(contract))
            app.run(root, "contract-check", [])
            app.run(root, "contract-review-init", [])
            passed = json.loads(review.read_text())
            passed["result"] = "PASS"
            passed["requirements"][0]["status"] = "PASS"
            review.write_text(json.dumps(passed))
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

    def test_blocks_identical_failed_action(self):
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
            with self.assertRaises(WorksError) as caught:
                app.run(root, "contract-check", [])
            self.assertEqual(caught.exception.code, "E901_REPEAT_FAILURE")
            state = store.load(plan)
            self.assertEqual(state["attempts"]["contract-check:-"]["count"], 1)
            activity = [json.loads(line) for line in (plan / "activity.jsonl").read_text().splitlines()]
            self.assertEqual([row["result"] for row in activity[-2:]], ["failed", "blocked"])


class ImpactMapTest(unittest.TestCase):
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
    def test_requires_full_command_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            requirement = Path(directory) / "requirement.md"
            requirement.write_text("# Requirement")
            data = requirement_contract.template(requirement)
            data["requirements"] = [{"id": "REQ-1", "statement": "behavior",
                                     "acceptance_criteria": ["result"]}]
            self.assertTrue(requirement_contract.validate(data, requirement))
            data["acceptance_commands"] = [{"id": "tests", "covers": ["REQ-1"],
                                            "command": ["mvn", "-DskipTests=false",
                                                        "-Dmaven.test.skip=false",
                                                        "-Dtest=ATest#works", "test"]}]
            self.assertEqual(requirement_contract.validate(data, requirement), [])

    def test_rejects_module_wide_test_command(self):
        with tempfile.TemporaryDirectory() as directory:
            requirement = Path(directory) / "requirement.md"
            requirement.write_text("# Requirement")
            data = requirement_contract.template(requirement)
            data["requirements"] = [{"id": "REQ-1", "statement": "behavior",
                                     "acceptance_criteria": ["result"]}]
            data["acceptance_commands"] = [{"id": "tests", "covers": ["REQ-1"],
                                            "command": ["mvn", "-DskipTests=false",
                                                        "-Dmaven.test.skip=false", "test"]}]
            errors = requirement_contract.validate(data, requirement)
            self.assertTrue(any("-Dtest=Class#method" in error for error in errors))

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


class CodeFirstEvidenceTest(unittest.TestCase):
    def test_requires_implementation_before_recording_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / ".planning" / "evidence"
            state.mkdir(parents=True)
            (state / "baseline.json").write_text(json.dumps({
                "project_root": str(root), "production": {}, "tests": {},
            }))
            args = type("Args", (), {
                "state_dir": str(state), "req": "REQ-1", "test_file": "src/test/java/ATest.java",
                "testcase": "ATest#works", "command": ["mvn", "-DskipTests=false",
                                                         "-Dmaven.test.skip=false",
                                                         "-Dtest=ATest#works", "test"],
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
            source.write_text("class A {}\n")
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
            implement = type("Args", (), {"state_dir": str(state), "req": "REQ-1"})()
            self.assertEqual(code_first.cmd_implement(implement), 0)
            command = ["mvn", "-DskipTests=false", "-Dmaven.test.skip=false",
                       "-Dtest=ATest#works", "test"]
            test_args = type("Args", (), {"state_dir": str(state), "req": "REQ-1",
                                           "test_file": "src/test/java/ATest.java",
                                           "testcase": "ATest#works", "command": command})()
            junit = {"target": {"executed": 1, "failures": 0, "errors": 0}, "files": []}
            def passing_run(_root, _command, log, _reports, _testcase):
                log.write_text("passed\n")
                return 0, junit
            with mock.patch.object(code_first, "run_command", side_effect=passing_run):
                self.assertEqual(code_first.cmd_test(test_args), 0)
            self.assertTrue((state / "slices" / "REQ-1" / "implementation.json").is_file())
            self.assertTrue((state / "slices" / "REQ-1" / "test.json").is_file())

    def test_policy_rejects_spring_boot_test(self):
        with tempfile.TemporaryDirectory() as directory:
            test = Path(directory) / "ATest.java"
            test.write_text("import org.mockito.Mock; @SpringBootTest class ATest { @Mock Object dep; }")
            with self.assertRaisesRegex(SystemExit, "SpringBootTest is forbidden"):
                code_first.require_targeted_mockito_test(
                    test, "ATest#works", ["mvn", "-Dtest=ATest#works", "test"])

    def test_policy_rejects_full_suite_and_non_mockito_test(self):
        with tempfile.TemporaryDirectory() as directory:
            test = Path(directory) / "ATest.java"
            test.write_text("class ATest { void works() {} }")
            with self.assertRaisesRegex(SystemExit, "must use Mockito"):
                code_first.require_targeted_mockito_test(test, "ATest#works", ["mvn", "test"])
            test.write_text("import org.mockito.Mock; class ATest { @Mock Object dep; }")
            with self.assertRaisesRegex(SystemExit, "exactly one -Dtest"):
                code_first.require_targeted_mockito_test(test, "ATest#works", ["mvn", "test"])


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
