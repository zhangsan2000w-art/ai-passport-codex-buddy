import json
import unittest

from windows_buddy_controller.protocol import (
    LineDecoder,
    build_heartbeat,
    build_name,
    build_owner,
    build_status_request,
    build_time_sync,
    parse_device_message,
    redact_protocol_line,
)


class ProtocolTests(unittest.TestCase):
    def test_builds_official_heartbeat_without_cmd_envelope(self):
        line = build_heartbeat(
            total=3,
            running=1,
            waiting=1,
            message="approve: Bash",
            entries=["10:42 git push", "10:41 test"],
            tokens=184502,
            tokens_today=31200,
            prompt={"id": "req_abc123", "tool": "Bash", "hint": "git push"},
        )
        self.assertTrue(line.endswith(b"\n"))
        payload = json.loads(line)
        self.assertNotIn("cmd", payload)
        self.assertEqual(payload["msg"], "approve: Bash")
        self.assertEqual(payload["prompt"]["id"], "req_abc123")

    def test_builds_official_one_shot_and_command_shapes(self):
        self.assertEqual(json.loads(build_time_sync(1775731234, -25200)),
                         {"time": [1775731234, -25200]})
        self.assertEqual(json.loads(build_owner("Felix")),
                         {"cmd": "owner", "name": "Felix"})
        self.assertEqual(json.loads(build_name("Clawd")),
                         {"cmd": "name", "name": "Clawd"})
        self.assertEqual(json.loads(build_status_request()), {"cmd": "status"})

    def test_line_decoder_reassembles_fragmented_notifications(self):
        decoder = LineDecoder(max_line_bytes=64)
        self.assertEqual(decoder.feed(b'{"ack":"sta'), [])
        self.assertEqual(decoder.feed(b'tus"}\n{"ack":"name"}\n'),
                         ['{"ack":"status"}', '{"ack":"name"}'])

    def test_line_decoder_recovers_after_oversized_line(self):
        decoder = LineDecoder(max_line_bytes=8)
        self.assertEqual(decoder.feed(b"1234567890\n{\"x\":1}\n"), ['{"x":1}'])
        self.assertEqual(decoder.overflow_count, 1)

    def test_parses_permission_and_status(self):
        permission = parse_device_message(
            '{"cmd":"permission","id":"req_1","decision":"deny"}'
        )
        self.assertEqual(permission.kind, "permission")
        self.assertEqual(permission.payload["decision"], "deny")

        status = parse_device_message(
            '{"ack":"status","ok":true,"data":{"name":"Clawd","sec":true}}'
        )
        self.assertEqual(status.kind, "status")
        self.assertTrue(status.payload["data"]["sec"])

    def test_rejects_invalid_permission_decision(self):
        with self.assertRaises(ValueError):
            parse_device_message(
                '{"cmd":"permission","id":"req_1","decision":"always"}'
            )

    def test_redacts_approval_ids_and_tool_parameters_in_logs(self):
        heartbeat = redact_protocol_line(
            '{"total":1,"prompt":{"id":"secret-id","tool":"Bash","hint":"token=secret"}}'
        )
        self.assertNotIn("secret-id", heartbeat)
        self.assertNotIn("token=secret", heartbeat)
        self.assertIn("Bash", heartbeat)
        permission = redact_protocol_line(
            '{"cmd":"permission","id":"secret-id","decision":"once"}'
        )
        self.assertNotIn("secret-id", permission)


if __name__ == "__main__":
    unittest.main()
