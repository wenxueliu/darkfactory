from __future__ import annotations

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


class WorksStateFlowTest(unittest.TestCase):
    def test_default_development_workflow_enforces_java_brownfield_flow(self):
        workflow_path = SCRIPTS.parent / "assets" / "workflows" / "development.json"
        default = json.loads(workflow_path.read_text(encoding="utf-8"))

        step_ids = [step["id"] for step in default["steps"]]
        self.assertEqual(
            step_ids,
            ["requirements", "exploration", "reuse_analysis", "unit_test", "implementation",
             "compile", "regression_test", "build_test_fix"],
        )
        self.assertEqual(default["initial_step"], "requirements")
        self.assertIn("requirement.md", default["steps"][0]["do"])
        self.assertIn("Service", default["steps"][2]["do"])
        self.assertIn("JUnit", default["steps"][3]["do"])
        self.assertIn("失败", default["steps"][3]["check"])
        self.assertIn("已有类和已有方法", default["steps"][4]["do"])
        self.assertEqual(default["steps"][5]["on_failure"]["goto"], "build_test_fix")
        self.assertEqual(default["steps"][6]["on_failure"]["goto"], "build_test_fix")
        self.assertIn("仅运行", default["steps"][6]["do"])
        self.assertIsNone(default["steps"][6]["on_success"])
        self.assertEqual(
            default["steps"][3]["references"],
            ["references/java-brownfield-development.md", "references/build-and-test.md"],
        )

    def test_init_embeds_workflow_in_the_only_state_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = Application().init(root, workflow())

            self.assertEqual(result["current_step"], "build")
            self.assertEqual(result["next_action"]["do"], "build it")
            self.assertEqual(result["next_action"]["check"], "inspect build")
            self.assertEqual(result["next_action"]["references_to_read"], [])
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


if __name__ == "__main__":
    unittest.main()
