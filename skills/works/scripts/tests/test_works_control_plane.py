from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import impact_map
import requirement_contract
import review_evidence
import service_boundary
from works_core.application import Application, WorksError
from works_core.discovery import discover, discover_maven_command
from works_core import state as store


def project_fixture(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "pom.xml").write_text("<project/>")
    (root / "requirement.md").write_text("# Requirement")


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
            contract = plan / "requirement-contract.json"
            contract.write_text(json.dumps({
                "version": 1,
                "requirement": str((root / "requirement.md").resolve()),
                "requirements": [{"id": "REQ-1", "statement": "behavior",
                                  "acceptance_criteria": ["observable result"]}],
                "acceptance_commands": [{"id": "module-tests", "covers": ["REQ-1"],
                                         "command": ["mvn", "-DskipTests=false",
                                                     "-Dmaven.test.skip=false", "test"]}],
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
                            "requirements": ["REQ-1"]})
            (evidence / "slices" / "REQ-1").mkdir(parents=True)
            (evidence / "slices" / "REQ-1" / "green.json").write_text("{}")
            (evidence / "final-verification.json").write_text('{"passed": false}')
            store.save(plan, current)
            updated = app.status(root)
            self.assertEqual(updated["state"], "READY_FOR_ACCEPTANCE")
            self.assertEqual(updated["next_action"]["id"], "diagnose-and-reopen-failing-requirement")
            repaired = app.run(root, "reopen", ["--req", "REQ-1"])
            self.assertEqual(repaired["state"], "READY_FOR_RED")
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
                                ("tdd-verify.json", {"passed": True}),
                                ("final-verification.json", {"passed": True})):
                (evidence / name).write_text(json.dumps(value))
            (evidence / "slices" / "REQ-1" / "green.json").write_text("{}")
            (plan / "requirement-contract.json").write_text(json.dumps({"requirements": [{"id": "REQ-1"}]}))
            current.update({"contract_valid": True, "contract_review_valid": True, "impact_valid": True,
                            "implementation_review_valid": False, "requirements": ["REQ-1"]})
            store.save(plan, current)
            updated = app.status(root)
            self.assertEqual(updated["state"], "IMPLEMENTATION_REVIEW_REQUIRED")
            app.run(root, "implementation-review-init", [])
            review = plan / "implementation-review.json"
            value = json.loads(review.read_text())
            value.update({"result": "PASS"})
            value["requirements"][0].update({"status": "PASS", "implementation": ["A.java:1"],
                                               "tests": ["ATest.java:1"]})
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
                                                             "-Dmaven.test.skip=false", "test"]}]}
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
                        "test_seams": ["Controller.java:1"], "risks": ["compatibility"]})
            self.assertEqual(impact_map.validate(data, project, ["REQ-1"]), [])


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


class ReviewEvidenceTest(unittest.TestCase):
    def test_implementation_review_requires_code_and_test_evidence(self):
        data = review_evidence.template("implementation", ["REQ-1"])
        data["result"] = "PASS"
        data["requirements"][0]["status"] = "PASS"
        errors = review_evidence.validate(data, "implementation", ["REQ-1"])
        self.assertTrue(any("implementation evidence" in error for error in errors))
        self.assertTrue(any("test evidence" in error for error in errors))

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
