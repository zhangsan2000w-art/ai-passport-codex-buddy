import json
import os
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest import mock

from windows_buddy_controller.codex_hook import run_hook
from windows_buddy_controller.notify_listener import NotifyListener


class NotifyListenerTests(unittest.TestCase):
    def test_first_approval_decision_wins_and_returns_to_hook(self):
        received = []
        with tempfile.TemporaryDirectory() as temporary:
            listener = NotifyListener(
                lambda kind, value: received.append((kind, value)),
                port=0,
                approval_port=0,
                bridge_dir=Path(temporary),
            )
            listener.start()
            try:
                deadline = time.time() + 2.0
                while listener.approval_port == 0 and time.time() < deadline:
                    time.sleep(0.01)
                self.assertNotEqual(listener.approval_port, 0)
                result = {}

                def request() -> None:
                    payload = {
                        "type": "codex-permission-request",
                        "request_id": "cx_test_1",
                        "tool": "Bash",
                        "hint": "git push",
                    }
                    with socket.create_connection(
                        ("127.0.0.1", listener.approval_port), timeout=2.0
                    ) as sock:
                        sock.sendall(json.dumps(payload).encode("utf-8") + b"\n")
                        result.update(json.loads(sock.makefile("rb").readline()))

                thread = threading.Thread(target=request)
                thread.start()
                deadline = time.time() + 2.0
                while not any(kind == "codex_approval" for kind, _ in received) and time.time() < deadline:
                    time.sleep(0.01)
                self.assertTrue(listener.resolve_approval("cx_test_1", "once"))
                self.assertFalse(listener.resolve_approval("cx_test_1", "deny"))
                thread.join(timeout=2.0)
                self.assertFalse(thread.is_alive())
                self.assertEqual(result["decision"], "once")
            finally:
                listener.stop()

    def test_file_bridge_delivers_lifecycle_and_first_approval(self):
        received = []
        with tempfile.TemporaryDirectory() as temporary:
            listener = NotifyListener(
                lambda kind, value: received.append((kind, value)),
                port=0,
                approval_port=0,
                bridge_dir=Path(temporary),
            )
            listener.start()
            try:
                environment = {
                    "CODEX_BUDDY_BRIDGE_DIR": temporary,
                    "CODEX_BUDDY_APPROVAL_TIMEOUT": "2",
                }
                with mock.patch.dict(os.environ, environment):
                    run_hook({
                        "hook_event_name": "UserPromptSubmit",
                        "session_id": "session-file",
                        "turn_id": "turn-file",
                    })
                    deadline = time.time() + 2.0
                    while not any(kind == "codex_event" for kind, _ in received) and time.time() < deadline:
                        time.sleep(0.01)
                    self.assertTrue(any(kind == "codex_event" for kind, _ in received))

                    result = {}

                    def file_request() -> None:
                        output = run_hook({
                            "hook_event_name": "PermissionRequest",
                            "session_id": "session-file",
                            "turn_id": "turn-file",
                            "tool_name": "Bash",
                            "tool_input": {"command": "git push"},
                        })
                        if output:
                            result.update(output)

                    thread = threading.Thread(target=file_request)
                    thread.start()
                    deadline = time.time() + 2.0
                    while not any(kind == "codex_approval" for kind, _ in received) and time.time() < deadline:
                        time.sleep(0.01)
                    approval = next(value for kind, value in received if kind == "codex_approval")
                    request_id = str(approval["request_id"])
                    self.assertTrue(listener.resolve_approval(request_id, "once"))
                    self.assertFalse(listener.resolve_approval(request_id, "deny"))
                    thread.join(timeout=2.0)
                    self.assertFalse(thread.is_alive())
                    decision = result["hookSpecificOutput"]["decision"]
                    self.assertEqual(decision["behavior"], "allow")

                    run_hook({
                        "hook_event_name": "Stop",
                        "session_id": "session-file",
                        "turn_id": "turn-file",
                        "last_assistant_message": "这段正文不应替代完成提示",
                    })
                    deadline = time.time() + 2.0
                    while not any(kind == "codex_notify" for kind, _ in received) and time.time() < deadline:
                        time.sleep(0.01)
                    completion = next(
                        value for kind, value in received if kind == "codex_notify"
                    )
                    self.assertEqual(completion["message"], "Codex 任务已完成")
            finally:
                listener.stop()


if __name__ == "__main__":
    unittest.main()
