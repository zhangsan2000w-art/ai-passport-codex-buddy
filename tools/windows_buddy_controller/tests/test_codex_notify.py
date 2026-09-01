import unittest

from windows_buddy_controller.codex_notify import build_bridge_event


class CodexNotifyTests(unittest.TestCase):
    def test_accepts_turn_complete_and_drops_prompt_text(self):
        event = build_bridge_event({
            "type": "agent-turn-complete",
            "thread-id": "thread-1",
            "cwd": "D:/work/demo",
            "input-messages": ["这是不应转发的用户提示"],
            "last-assistant-message": "  构建完成\n测试通过  ",
        })
        self.assertEqual(event["type"], "codex-turn-complete")
        self.assertEqual(event["project"], "demo")
        self.assertEqual(event["message"], "构建完成 测试通过")
        self.assertNotIn("input", event)

    def test_ignores_other_events_and_invalid_json(self):
        self.assertIsNone(build_bridge_event({"type": "approval-requested"}))
        self.assertIsNone(build_bridge_event("not json"))

    def test_clips_utf8_without_splitting_characters(self):
        event = build_bridge_event({
            "type": "agent-turn-complete",
            "last-assistant-message": "完成" * 100,
        })
        event["message"].encode("utf-8").decode("utf-8")
        self.assertTrue(event["message"].endswith("..."))

    def test_replaces_malformed_windows_unicode(self):
        event = build_bridge_event({
            "type": "agent-turn-complete",
            "last-assistant-message": "完成\udc95测试",
        })
        self.assertEqual(event["message"], "完成?测试")
        event["message"].encode("utf-8")


if __name__ == "__main__":
    unittest.main()
