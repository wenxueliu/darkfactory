from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from works_core.application import Application, WorksError


def dynamic_workflow() -> dict:
    return {
        "name": "dynamic",
        "initial_step": "requirements",
        "steps": [
            {
                "id": "requirements",
                "purpose": "confirm requirements",
                "route_when": "requirements are missing or invalid",
                "do": "read requirements",
                "check": "verify requirements",
                "next": ["exploration"],
                "forward_policy": "declared",
                "forward_targets": ["implementation"],
            },
            {
                "id": "exploration",
                "purpose": "inspect the codebase",
                "route_when": "the implementation location is unclear",
                "do": "explore code",
                "check": "verify findings",
                "next": ["implementation"],
            },
            {
                "id": "implementation",
                "purpose": "implement the change",
                "route_when": "production behavior is invalid",
                "do": "change code",
                "check": "verify implementation",
                "next": ["test"],
            },
            {
                "id": "test",
                "purpose": "run regression tests",
                "route_when": "results need verification",
                "do": "run tests",
                "check": "verify test results",
                "next": [],
                "complete": True,
            },
        ],
    }


class WorksDynamicRoutingTest(unittest.TestCase):
    def test_feedback_lifecycle_and_hard_pause_priority(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            app.init(root, dynamic_workflow())

            feedback = app.feedback(root, "please reconsider the requirement")
            self.assertEqual(feedback["feedback"]["status"], "delivered")

            action = app.next(root)
            self.assertEqual(action["next_action"]["type"], "interpret_feedback")
            self.assertEqual(app.feedback_list(root)["feedback"][0]["status"], "observed")

            response = app.feedback_respond(
                root,
                feedback["feedback"]["id"],
                "continue",
                "the requested adjustment is unambiguous",
                "the existing goal determines the behavior",
                {"keep": ["goal"], "modify": ["implementation"], "reverify": ["test"]},
            )
            self.assertEqual(response["feedback"]["status"], "applied")

            app.pause(root, "stop now")
            paused = app.next(root)
            self.assertEqual(paused["execution_state"], "paused")
            self.assertIsNone(paused["next_action"])
            self.assertEqual(paused["feedback"]["kind"], "control")
            self.assertEqual(paused["feedback"]["status"], "applied")

            resumed = app.resume(root)
            self.assertEqual(resumed["execution_state"], "running")
            self.assertEqual(app.next(root)["next_action"]["type"], "execute_step")

    def test_ask_waits_for_a_follow_up_feedback_response(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            app.init(root, dynamic_workflow())
            feedback_id = app.feedback(root, "which behavior?")["feedback"]["id"]
            app.next(root)

            waiting = app.feedback_respond(
                root, feedback_id, "ask", "two meanings are possible", "user intent is required",
                {}, {"text": "Which one?", "options": ["A", "B"]},
            )
            self.assertEqual(waiting["execution_state"], "waiting_for_human")
            self.assertEqual(app.next(root)["next_action"]["type"], "await_human")

            answer_id = app.feedback(root, "A")["feedback"]["id"]
            self.assertEqual(app.next(root)["next_action"]["feedback"]["id"], answer_id)
            continued = app.feedback_respond(
                root, answer_id, "continue", "the answer selects A", "ambiguity resolved", {},
            )
            self.assertEqual(continued["execution_state"], "running")
            self.assertIsNone(continued["active_question"])

    def test_goal_revision_marks_verified_steps_for_revalidation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            requirement = root / "requirement.md"
            requirement.write_text("first goal", encoding="utf-8")
            app = Application()
            app.init(root, dynamic_workflow())
            app.check(root, True, "requirements verified")
            app.route(root, "exploration", "requirements passed", "requirement.md", ["requirements"], [])
            requirement.write_text("revised goal", encoding="utf-8")

            revised = app.goal_revise(root, "goal clarified", requirement)

            self.assertEqual(revised["goal"]["revision"], 2)
            self.assertEqual(revised["goal_revision"], 2)
            self.assertEqual(revised["step_results"]["requirements"]["status"],
                             "needs_revalidation")
            events = (root / ".works" / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn('"type": "goal_revised"', events)

    def test_dynamic_route_rejects_illegal_targets_and_supports_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            initialized = app.init(root, dynamic_workflow())
            self.assertEqual(
                initialized["allowed_targets"],
                ["requirements", "exploration", "implementation"],
            )

            app.check(root, True, "requirements verified")
            with self.assertRaises(WorksError) as caught:
                app.route(root, "test", "skip ahead", "no exploration", ["requirements"], [])
            self.assertEqual(caught.exception.code, "E_INVALID_TARGET")

            app.route(root, "implementation", "simple safe change", "single method", ["requirements"], [])
            self.assertEqual(app.status(root)["visited_steps"], ["requirements", "implementation"])
            app.check(root, True, "implementation verified")
            app.route(root, "test", "ready to test", "build clean", ["requirements", "implementation"], [])
            app.check(root, True, "tests passed")
            completed = app.route(
                root, "__complete__", "all gates passed", "tests exit 0",
                ["requirements", "implementation", "test"], [],
            )
            self.assertEqual(completed["execution_state"], "completed")
            self.assertTrue(completed["completed"])

    def test_route_requires_a_passed_check_and_is_blocked_by_feedback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            app.init(root, dynamic_workflow())
            with self.assertRaises(WorksError) as caught:
                app.route(root, "exploration", "move", "evidence", [], [])
            self.assertEqual(caught.exception.code, "E_ROUTE_NOT_READY")

            app.check(root, True, "requirements verified")
            app.feedback(root, "wait")
            with self.assertRaises(WorksError) as caught:
                app.route(root, "exploration", "move", "evidence", ["requirements"], [])
            self.assertEqual(caught.exception.code, "E_FEEDBACK_BLOCKING")

    def test_pending_feedback_blocks_command_before_process_start(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "command-started"
            app = Application()
            app.init(root, dynamic_workflow())
            app.feedback(root, "stop before the next tool")

            with self.assertRaises(WorksError) as caught:
                app.check_command(
                    root,
                    [sys.executable, "-c", f"open({str(marker)!r}, 'w').write('started')"],
                )

            self.assertEqual(caught.exception.code, "E_FEEDBACK_BLOCKING")
            self.assertFalse(marker.exists())

    def test_next_discovers_hook_inbox_and_applies_resume_control(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = Application()
            app.init(root, dynamic_workflow())
            app.pause(root, "stop")
            self.assertEqual(app.next(root)["execution_state"], "paused")
            external = {
                "id": "HF-HOOK", "kind": "control", "action": "resume",
                "reason": "continue", "status": "delivered", "created_at": 2,
            }
            (root / ".works" / "inbox" / "HF-HOOK.json").write_text(
                json.dumps(external), encoding="utf-8",
            )

            resumed = app.next(root)

            self.assertEqual(resumed["execution_state"], "running")
            self.assertEqual(resumed["feedback"]["status"], "applied")
            self.assertNotIn("HF-HOOK", resumed["pending_feedback"])


if __name__ == "__main__":
    unittest.main()
