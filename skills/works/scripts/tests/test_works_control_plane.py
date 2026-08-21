from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from works_core.application import Application, WorksError


def workflow() -> dict:
    return {
        "name": "custom",
        "initial_step": "build",
        "steps": [
            {"id": "build", "do": "build it", "check": "inspect build",
             "on_success": "test", "on_failure": {"retries": 1, "goto": "build"}},
            {"id": "test", "do": "test it", "check": "run tests",
             "on_success": None, "on_failure": {"retries": 0, "goto": "fix"}},
            {"id": "fix", "do": "fix it", "check": "inspect fix",
             "on_success": "test", "on_failure": {"retries": 0, "goto": "build"}},
        ],
    }


def development_evidence(selected: str | None = "SameLayerService.call") -> str:
    failed_gates = {
        "semantic_match": True, "callable": True, "no_recursion": False,
        "dependency_direction": True, "proxy_safe": True,
        "transaction_compatible": True, "contract_compatible": True,
    }
    passed_gates = {name: True for name in failed_gates}
    candidates = [
        {"symbol": "CurrentService.helper", "tier": "current_class", "feasible": False,
         "evidence": "private helper at CurrentService.java:20",
         "reject_reasons": ["calling it would recurse"], "gates": failed_gates},
        {"symbol": "SameLayerService.call", "tier": "same_layer", "feasible": True,
         "evidence": "declaration and caller at SameLayerService.java:30", "reject_reasons": [],
         "gates": passed_gates},
    ]
    if selected is None:
        candidates[1]["feasible"] = False
        candidates[1]["reject_reasons"] = ["module dependency direction forbids the call"]
        candidates[1]["gates"] = {**passed_gates, "dependency_direction": False}
    search_evidence = {
        "current_class": "searched CurrentService methods",
        "same_layer": "searched service interfaces and implementations",
    }
    if selected is None:
        search_evidence["cross_layer"] = "searched allowed adapters and mapper boundary"
    return json.dumps({"reuse_decisions": [{
        "feature": "feature-a", "selected": selected, "candidates": candidates,
        "search_evidence": search_evidence,
    }]})


def write_test_case_design(root: Path) -> None:
    requirement_hash = hashlib.sha256((root / "requirement.md").read_bytes()).hexdigest()
    artifact = {
        "schema_version": 1,
        "requirement_sha256": requirement_hash,
        "features": [{
            "feature": "feature-a",
            "target_test_class": "CurrentServiceTest",
            "cases": [{
                "id": "feature-a-happy",
                "kind": "happy_path",
                "given": ["valid input"],
                "when": "the feature is invoked",
                "then": ["the expected result is returned"],
                "related_requirement": "feature-a acceptance criterion",
            }],
            "excluded": ["unrelated modules are out of scope"],
        }],
    }
    path = root / ".works" / "test-case-design.json"
    path.write_text(json.dumps(artifact), encoding="utf-8")


def write_generated_test(root: Path) -> str:
    test_file = root / "CurrentServiceTest.java"
    test_file.write_text(
        "class CurrentServiceTest { void featureAHappy() {} }\n",
        encoding="utf-8",
    )
    return json.dumps({"test_generation_mapping": [{
        "case_id": "feature-a-happy",
        "test_file": "CurrentServiceTest.java",
        "test_method": "featureAHappy",
        "test_selector": "CurrentServiceTest#featureAHappy",
    }]})


class WorksStateFlowTest(unittest.TestCase):
    def test_default_development_workflow_enforces_java_brownfield_flow(self):
        workflow_path = SCRIPTS.parent / "assets" / "workflows" / "development.json"
        default = json.loads(workflow_path.read_text(encoding="utf-8"))

        step_ids = [step["id"] for step in default["steps"]]
        self.assertEqual(
            step_ids,
            ["requirements", "exploration", "reuse_analysis", "test_case_design", "implementation",
             "compile", "test_generation", "regression_test", "build_test_fix"],
        )
        self.assertEqual(default["initial_step"], "requirements")
        self.assertIn("requirement.md", default["steps"][0]["do"])
        self.assertIn("Service", default["steps"][2]["do"])
        self.assertIn("test-case-designer subagent", default["steps"][3]["do"])
        self.assertEqual(default["steps"][3]["validator"], "test_case_design_artifact")
        self.assertEqual(default["steps"][3]["subagent"]["role"], "test-case-designer")
        self.assertTrue(default["steps"][3]["subagent"]["fresh_context"])
        self.assertIn("已有类和已有方法", default["steps"][4]["do"])
        self.assertEqual(default["steps"][5]["on_failure"]["goto"], "build_test_fix")
        self.assertEqual(default["steps"][6]["validator"], "test_generation_mapping")
        self.assertEqual(default["steps"][7]["on_failure"]["goto"], "build_test_fix")
        self.assertIn("设计文件中的全部 case id", default["steps"][7]["check"])
        self.assertIsNone(default["steps"][7]["on_success"])
        self.assertEqual(
            default["steps"][3]["references"],
            ["references/java-brownfield-development.md"],
        )

    def test_init_embeds_workflow_in_the_only_state_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = Application().init(root, workflow())

            self.assertEqual(result["current_step"], "build")
            self.assertEqual(result["next_action"]["do"], "build it")
            self.assertEqual(result["next_action"]["check"], "inspect build")
            self.assertEqual(result["next_action"]["references_to_read"], [])
            self.assertIsNone(result["next_action"]["subagent"])
            self.assertEqual(
                [path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()],
                [".works/state.json"],
            )
            self.assertEqual(json.loads((root / ".works/state.json").read_text())["workflow"]["name"],
                             "custom")

    def test_success_moves_to_configured_step_and_final_success_completes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            app.init(root, workflow())

            testing = app.check(root, True, "implementation inspected")
            completed = app.check_command(root, [sys.executable, "-c", "print('ok')"])

            self.assertEqual(testing["current_step"], "test")
            self.assertEqual(testing["next_action"]["do"], "test it")
            self.assertTrue(completed["completed"])
            self.assertIsNone(completed["next_action"])

    def test_failure_retries_then_uses_configured_fallback(self):
        custom = workflow()
        custom["steps"][0]["on_failure"] = {"retries": 1, "goto": "fix"}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            app.init(root, custom)

            retry = app.check(root, False, "first failure")
            fallback = app.check(root, False, "second failure")

            self.assertEqual(retry["current_step"], "build")
            self.assertEqual(retry["failures"]["build"], 1)
            self.assertEqual(fallback["current_step"], "fix")
            self.assertEqual(fallback["failures"]["build"], 0)
            self.assertEqual(fallback["last_check"]["evidence"], "second failure")

    def test_command_failure_routes_to_fix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            app.init(root, workflow())
            app.check(root, True, "ready")

            failed = app.check_command(root, [sys.executable, "-c", "raise SystemExit(7)"])

            self.assertEqual(failed["current_step"], "fix")
            self.assertFalse(failed["check_passed"])
            self.assertIn("exit=7", failed["last_check"]["evidence"])

    def test_state_survives_a_new_application_instance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Application().init(root, workflow())
            Application().check(root, True, "ready")

            recovered = Application().status(root)

            self.assertEqual(recovered["current_step"], "test")
            self.assertEqual(recovered["next_action"]["check"], "run tests")

    def test_rejects_unknown_transition_target(self):
        invalid = workflow()
        invalid["steps"][0]["on_success"] = "missing"
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(WorksError) as caught:
                Application().init(Path(directory), invalid)

            self.assertEqual(caught.exception.code, "E102_INVALID_WORKFLOW")

    def test_rejects_missing_do_or_check_prompt(self):
        invalid = workflow()
        invalid["steps"][0]["check"] = ""
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(WorksError):
                Application().init(Path(directory), invalid)

    def test_exposes_step_references_and_rejects_invalid_values(self):
        custom = workflow()
        custom["steps"][0]["references"] = ["references/build-and-test.md"]
        with tempfile.TemporaryDirectory() as directory:
            result = Application().init(Path(directory), custom)
            self.assertEqual(
                result["next_action"]["references_to_read"],
                ["references/build-and-test.md"],
            )

        custom["steps"][0]["references"] = ["references/build-and-test.md", ""]
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(WorksError):
                Application().init(Path(directory), custom)

        custom["steps"][0]["references"] = ["../outside.md"]
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(WorksError):
                Application().init(Path(directory), custom)

    def test_reuse_decision_is_validated_and_survives_test_case_design(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            (root / "requirement.md").write_text("feature-a", encoding="utf-8")
            app.init(root, json.loads((SCRIPTS.parent / "assets/workflows/development.json").read_text()))
            app.check(root, True, "requirements")
            app.check(root, True, "exploration")

            test_case_design = app.check(root, True, development_evidence())
            self.assertEqual(
                test_case_design["next_action"]["subagent"]["role"],
                "test-case-designer",
            )
            write_test_case_design(root)
            implementation = app.check(root, True, ".works/test-case-design.json")
            (root / "CurrentService.java").write_text(
                "sameLayerService.call();\n", encoding="utf-8"
            )
            implementation_evidence = json.dumps({"implementation_reuse": [{
                "feature": "feature-a", "action": "invoke",
                "symbol": "SameLayerService.call", "call_site": "CurrentService.java:1",
            }]})
            compile_step = app.check(root, True, implementation_evidence)

            self.assertEqual(test_case_design["reuse_decisions"]["feature-a"]["selected"],
                             "SameLayerService.call")
            self.assertEqual(implementation["current_step"], "implementation")
            self.assertIn("feature-a", implementation["reuse_decisions"])
            self.assertEqual(
                implementation["test_case_design_artifact"]["path"],
                ".works/test-case-design.json",
            )
            self.assertEqual(compile_step["current_step"], "compile")

    def test_test_case_design_requires_the_validated_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            (root / "requirement.md").write_text("feature-a", encoding="utf-8")
            default = json.loads((SCRIPTS.parent / "assets/workflows/development.json").read_text())
            app.init(root, default)
            app.check(root, True, "requirements")
            app.check(root, True, "exploration")
            app.check(root, True, development_evidence())

            with self.assertRaises(WorksError) as caught:
                app.check(root, True, ".works/test-case-design.json")

            self.assertEqual(caught.exception.code, "E207_TEST_CASE_FILE_REQUIRED")

    def test_changed_test_case_design_returns_regression_to_design(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            (root / "requirement.md").write_text("feature-a", encoding="utf-8")
            default = json.loads((SCRIPTS.parent / "assets/workflows/development.json").read_text())
            app.init(root, default)
            app.check(root, True, "requirements")
            app.check(root, True, "exploration")
            app.check(root, True, development_evidence())
            write_test_case_design(root)
            app.check(root, True, ".works/test-case-design.json")
            (root / "CurrentService.java").write_text(
                "sameLayerService.call();\n", encoding="utf-8"
            )
            implementation_evidence = json.dumps({"implementation_reuse": [{
                "feature": "feature-a", "action": "invoke",
                "symbol": "SameLayerService.call", "call_site": "CurrentService.java:1",
            }]})
            app.check(root, True, implementation_evidence)
            app.check(root, True, "compiled")
            app.check(root, True, write_generated_test(root))
            with (root / ".works" / "test-case-design.json").open("a", encoding="utf-8") as handle:
                handle.write("\n")

            with self.assertRaises(WorksError) as caught:
                app.check_command(root, [sys.executable, "-c", "print('tests')"])

            self.assertEqual(caught.exception.code, "E208_TEST_CASE_DESIGN_STALE")
            self.assertEqual(app.status(root)["current_step"], "test_case_design")

    def test_regression_command_must_select_generated_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            (root / "requirement.md").write_text("feature-a", encoding="utf-8")
            default = json.loads((SCRIPTS.parent / "assets/workflows/development.json").read_text())
            app.init(root, default)
            app.check(root, True, "requirements")
            app.check(root, True, "exploration")
            app.check(root, True, development_evidence())
            write_test_case_design(root)
            app.check(root, True, ".works/test-case-design.json")
            (root / "CurrentService.java").write_text(
                "sameLayerService.call();\n", encoding="utf-8"
            )
            implementation_evidence = json.dumps({"implementation_reuse": [{
                "feature": "feature-a", "action": "invoke",
                "symbol": "SameLayerService.call", "call_site": "CurrentService.java:1",
            }]})
            app.check(root, True, implementation_evidence)
            app.check(root, True, "compiled")
            app.check(root, True, write_generated_test(root))

            with self.assertRaises(WorksError) as caught:
                app.check_command(root, [sys.executable, "-c", "print('unrelated')"])

            self.assertEqual(caught.exception.code, "E209_TEST_GENERATION_MAPPING_REQUIRED")

    def test_reuse_rejects_lower_tier_when_higher_tier_is_feasible(self):
        evidence = json.loads(development_evidence())
        evidence["reuse_decisions"][0]["candidates"][0]["feasible"] = True
        evidence["reuse_decisions"][0]["candidates"][0]["reject_reasons"] = []
        evidence["reuse_decisions"][0]["candidates"][0]["gates"]["no_recursion"] = True
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            app.init(root, json.loads((SCRIPTS.parent / "assets/workflows/development.json").read_text()))
            app.check(root, True, "requirements")
            app.check(root, True, "exploration")
            with self.assertRaises(WorksError):
                app.check(root, True, json.dumps(evidence))

    def test_reuse_fallback_requires_all_tier_search_and_no_feasible_candidate(self):
        valid = development_evidence(None)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            app.init(root, json.loads((SCRIPTS.parent / "assets/workflows/development.json").read_text()))
            app.check(root, True, "requirements")
            app.check(root, True, "exploration")
            result = app.check(root, True, valid)
            self.assertIsNone(result["reuse_decisions"]["feature-a"]["selected"])

            incomplete = json.loads(valid)
            incomplete["reuse_decisions"][0]["search_evidence"]["cross_layer"] = ""
            root2 = Path(directory) / "second"
            root2.mkdir()
            app.init(root2, json.loads((SCRIPTS.parent / "assets/workflows/development.json").read_text()))
            app.check(root2, True, "requirements")
            app.check(root2, True, "exploration")
            with self.assertRaises(WorksError):
                app.check(root2, True, json.dumps(incomplete))

    def test_implementation_requires_persisted_reuse_decision(self):
        custom = workflow()
        custom["steps"][2]["id"] = "implementation"
        custom["steps"][2]["validator"] = "implementation_reuse"
        custom["steps"][1]["on_failure"]["goto"] = "implementation"
        custom["initial_step"] = "implementation"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            app.init(root, custom)
            with self.assertRaises(WorksError) as caught:
                app.check(root, True, "implementation reviewed")
            self.assertEqual(caught.exception.code, "E205_REUSE_DECISION_REQUIRED")

    def test_v2_default_state_migrates_and_returns_to_reuse_analysis(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            default = json.loads((SCRIPTS.parent / "assets/workflows/development.json").read_text())
            app.init(root, default)
            state_path = root / ".works/state.json"
            state = json.loads(state_path.read_text())
            state["version"] = 2
            state.pop("reuse_decisions")
            state["current_step"] = "implementation"
            for step in state["workflow"]["steps"]:
                step.pop("validator", None)
            state_path.write_text(json.dumps(state), encoding="utf-8")

            migrated = app.status(root)

            self.assertEqual(migrated["version"], 5)
            self.assertEqual(migrated["current_step"], "reuse_analysis")
            self.assertEqual(migrated["reuse_decisions"], {})
            self.assertEqual(migrated["next_action"]["step"], "reuse_analysis")

    def test_v3_unit_test_state_migrates_to_test_case_design(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            default = json.loads((SCRIPTS.parent / "assets/workflows/development.json").read_text())
            app.init(root, default)
            state_path = root / ".works/state.json"
            state = json.loads(state_path.read_text())
            state["version"] = 3
            state["current_step"] = "unit_test"
            state_path.write_text(json.dumps(state), encoding="utf-8")

            migrated = app.status(root)

            self.assertEqual(migrated["version"], 5)
            self.assertEqual(migrated["current_step"], "test_case_design")
            self.assertEqual(migrated["next_action"]["step"], "test_case_design")

    def test_v4_implementation_state_returns_to_test_case_design(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            default = json.loads((SCRIPTS.parent / "assets/workflows/development.json").read_text())
            app.init(root, default)
            state_path = root / ".works/state.json"
            state = json.loads(state_path.read_text())
            state["version"] = 4
            state["current_step"] = "implementation"
            state.pop("test_case_design_artifact")
            state_path.write_text(json.dumps(state), encoding="utf-8")

            migrated = app.status(root)

            self.assertEqual(migrated["version"], 5)
            self.assertEqual(migrated["current_step"], "test_case_design")

    def test_implementation_evidence_must_match_selected_symbol(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            (root / "requirement.md").write_text("feature-a", encoding="utf-8")
            default = json.loads((SCRIPTS.parent / "assets/workflows/development.json").read_text())
            app.init(root, default)
            app.check(root, True, "requirements")
            app.check(root, True, "exploration")
            app.check(root, True, development_evidence())
            write_test_case_design(root)
            app.check(root, True, ".works/test-case-design.json")
            mismatch = json.dumps({"implementation_reuse": [{
                "feature": "feature-a", "action": "invoke",
                "symbol": "WrongService.call", "call_site": "CurrentService.java:42",
            }]})
            with self.assertRaises(WorksError) as caught:
                app.check(root, True, mismatch)
            self.assertEqual(caught.exception.code, "E206_IMPLEMENTATION_REUSE_MISMATCH")

    def test_implementation_rejects_a_nonexistent_call_site(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            (root / "requirement.md").write_text("feature-a", encoding="utf-8")
            default = json.loads((SCRIPTS.parent / "assets/workflows/development.json").read_text())
            app.init(root, default)
            app.check(root, True, "requirements")
            app.check(root, True, "exploration")
            app.check(root, True, development_evidence())
            write_test_case_design(root)
            app.check(root, True, ".works/test-case-design.json")
            forged = json.dumps({"implementation_reuse": [{
                "feature": "feature-a", "action": "invoke",
                "symbol": "SameLayerService.call", "call_site": "missing.java:1",
            }]})
            with self.assertRaises(WorksError) as caught:
                app.check(root, True, forged)
            self.assertEqual(caught.exception.code, "E206_IMPLEMENTATION_REUSE_MISMATCH")

    def test_current_class_selection_stops_before_lower_tier_search(self):
        evidence = json.loads(development_evidence("CurrentService.helper"))
        current = evidence["reuse_decisions"][0]["candidates"][0]
        current["feasible"] = True
        current["reject_reasons"] = []
        current["gates"]["no_recursion"] = True
        evidence["reuse_decisions"][0]["candidates"] = [current]
        evidence["reuse_decisions"][0]["search_evidence"] = {
            "current_class": "searched CurrentService methods"
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            default = json.loads((SCRIPTS.parent / "assets/workflows/development.json").read_text())
            app.init(root, default)
            app.check(root, True, "requirements")
            app.check(root, True, "exploration")
            result = app.check(root, True, json.dumps(evidence))
            self.assertEqual(result["reuse_decisions"]["feature-a"]["selected"],
                             "CurrentService.helper")

if __name__ == "__main__":
    unittest.main()
