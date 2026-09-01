import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from windows_buddy_controller.codex_hook import (
    build_approval_event,
    build_lifecycle_event,
    permission_output,
    run_hook,
)


class CodexHookTests(unittest.TestCase):
    def test_lifecycle_event_is_written_to_shared_file_bridge(self):
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(os.environ, {
                "CODEX_BUDDY_BRIDGE_DIR": temporary,
            }):
                result = run_hook({
                    "hook_event_name": "UserPromptSubmit",
                    "session_id": "session-file",
                    "turn_id": "turn-file",
                    "cwd": "D:/work/demo",
                })
            self.assertIsNone(result)
            events = list((Path(temporary) / "events").glob("event-*.json"))
            self.assertEqual(len(events), 1)
            payload = json.loads(events[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["type"], "codex-turn-start")
            self.assertEqual(payload["session_id"], "session-file")

    def test_builds_start_tool_and_stop_events_without_user_prompt(self):
        common = {
            "session_id": "session-1",
            "turn_id": "turn-1",
            "cwd": "D:/work/demo",
            "model": "gpt-test",
        }
        start = build_lifecycle_event({
            **common,
            "hook_event_name": "UserPromptSubmit",
            "prompt": "不应发送到卡片的完整用户提示",
        })
        self.assertEqual(start["type"], "codex-turn-start")
        self.assertEqual(start["project"], "demo")
        self.assertNotIn("prompt", start)

        tool = build_lifecycle_event({
            **common,
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "git status"},
        })
        self.assertEqual(tool["type"], "codex-tool-start")
        self.assertEqual(tool["hint"], "git status")

        stop = build_lifecycle_event({
            **common,
            "hook_event_name": "Stop",
            "last_assistant_message": "测试通过",
        })
        self.assertEqual(stop["message"], "Codex 任务已完成")

    def test_builds_bounded_opaque_approval(self):
        event = build_approval_event({
            "hook_event_name": "PermissionRequest",
            "session_id": "session-1",
            "turn_id": "turn-1",
            "tool_name": "Bash",
            "tool_input": {"command": "echo x " * 100},
        }, request_id="cx_test")
        self.assertEqual(event["request_id"], "cx_test")
        self.assertEqual(event["tool"], "Bash")
        self.assertLessEqual(len(event["hint"].encode("utf-8")), 183)

    def test_malformed_windows_unicode_does_not_drop_approval(self):
        event = build_approval_event({
            "hook_event_name": "PermissionRequest",
            "session_id": "session-1",
            "turn_id": "turn-1",
            "tool_name": "Bash",
            "tool_input": {
                "command": "echo ok",
                "description": "审批\udc95测试",
            },
        }, request_id="cx_unicode")
        self.assertEqual(event["request_id"], "cx_unicode")
        self.assertEqual(event["reason"], "审批?测试")
        json.dumps(event, ensure_ascii=False).encode("utf-8")

    def test_permission_outputs_match_official_hook_shape(self):
        self.assertEqual(
            permission_output("once")["hookSpecificOutput"]["decision"]["behavior"],
            "allow",
        )
        self.assertEqual(
            permission_output("deny")["hookSpecificOutput"]["decision"]["behavior"],
            "deny",
        )
        self.assertIsNone(permission_output("fallback"))

    def test_permission_falls_back_or_uses_first_bridge_decision(self):
        payload = {
            "hook_event_name": "PermissionRequest",
            "tool_name": "Bash",
            "tool_input": {"command": "git push"},
        }
        with mock.patch(
            "windows_buddy_controller.codex_hook._request_approval",
            return_value=None,
        ):
            self.assertIsNone(run_hook(payload))
        with mock.patch(
            "windows_buddy_controller.codex_hook._request_approval",
            return_value="once",
        ):
            result = run_hook(payload)
        self.assertEqual(
            result["hookSpecificOutput"]["decision"]["behavior"], "allow"
        )


if __name__ == "__main__":
    unittest.main()
