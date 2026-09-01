import unittest

from windows_buddy_controller.codex_state import CodexStateTracker


class CodexStateTests(unittest.TestCase):
    def test_tracks_live_turn_tool_approval_and_completion(self):
        state = CodexStateTracker()
        self.assertTrue(state.apply({
            "type": "codex-turn-start", "session_id": "s1", "turn_id": "t1",
            "project": "demo",
        }))
        self.assertEqual(state.heartbeat()["running"], 1)
        self.assertTrue(state.apply({
            "type": "codex-tool-start", "session_id": "s1", "turn_id": "t1",
            "tool": "Bash", "hint": "git status",
        }))
        self.assertIn("Bash", state.heartbeat()["message"])

        self.assertTrue(state.apply({
            "type": "codex-permission-request", "request_id": "cx_1",
            "session_id": "s1", "turn_id": "t1", "tool": "Bash",
            "hint": "git push",
        }))
        heartbeat = state.heartbeat()
        self.assertEqual(heartbeat["waiting"], 1)
        self.assertEqual(heartbeat["prompt"]["id"], "cx_1")
        self.assertEqual(heartbeat["tokens"], 0)

        self.assertTrue(state.apply({
            "type": "codex-permission-resolved", "request_id": "cx_1",
            "decision": "once",
        }))
        self.assertEqual(state.heartbeat()["waiting"], 0)
        self.assertTrue(state.apply({
            "type": "codex-turn-complete", "session_id": "s1", "turn_id": "t1",
            "message": "完成",
        }))
        self.assertEqual(state.heartbeat()["running"], 0)
        self.assertEqual(state.heartbeat()["message"], "完成")
        self.assertEqual(state.heartbeat()["tokens"], 50000)
        self.assertFalse(state.apply({
            "type": "codex-turn-complete", "session_id": "s1", "turn_id": "t1",
            "message": "重复完成",
        }))
        self.assertEqual(state.heartbeat()["tokens"], 50000)

    def test_rejects_duplicate_or_stale_approval_transitions(self):
        state = CodexStateTracker()
        request = {
            "type": "codex-permission-request", "request_id": "cx_1",
            "session_id": "s1", "turn_id": "t1", "tool": "Bash",
        }
        self.assertTrue(state.apply(request))
        self.assertFalse(state.apply(request))
        self.assertFalse(state.apply({
            "type": "codex-permission-resolved", "request_id": "wrong",
            "decision": "once",
        }))
        self.assertEqual(state.current_approval.request_id, "cx_1")


if __name__ == "__main__":
    unittest.main()
