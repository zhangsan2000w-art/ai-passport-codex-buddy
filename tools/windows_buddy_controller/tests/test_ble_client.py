import sys
import types
import unittest
from unittest.mock import patch

from windows_buddy_controller.ble_client import BleWorker, split_for_write


class BleClientTests(unittest.TestCase):
    def test_split_for_write_preserves_bytes(self):
        payload = bytes(range(100))
        chunks = split_for_write(payload, 20)
        self.assertEqual(b"".join(chunks), payload)
        self.assertTrue(all(0 < len(chunk) <= 20 for chunk in chunks))

    def test_split_for_write_rejects_invalid_size(self):
        with self.assertRaises(ValueError):
            split_for_write(b"data", 0)


class BleConnectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_notify_failure_releases_partial_connection(self):
        events = []

        class FailingClient:
            last = None

            def __init__(self, _target, **_kwargs):
                self.is_connected = False
                self.disconnected = False
                self.options = _kwargs
                FailingClient.last = self

            async def connect(self):
                self.is_connected = True

            async def start_notify(self, _uuid, _callback):
                raise RuntimeError("Could not start notify: Unreachable")

            async def stop_notify(self, _uuid):
                return None

            async def disconnect(self):
                self.is_connected = False
                self.disconnected = True

        fake_bleak = types.ModuleType("bleak")
        fake_bleak.BleakClient = FailingClient
        worker = BleWorker(lambda kind, value: events.append((kind, value)))

        with patch("windows_buddy_controller.ble_client.sys.platform", "win32"), \
                patch.dict(sys.modules, {"bleak": fake_bleak}):
            with self.assertRaisesRegex(RuntimeError, "Unreachable"):
                await worker._connect("test-address")

        self.assertIsNone(worker._client)
        self.assertTrue(FailingClient.last.disconnected)
        self.assertEqual(
            {"use_cached_services": False}, FailingClient.last.options["winrt"]
        )
        self.assertIn(("connected", False), events)
        self.assertIn(
            ("status", "连接初始化失败，已释放设备，可重新扫描"), events
        )

        with patch("windows_buddy_controller.ble_client.sys.platform", "darwin"), \
                patch.dict(sys.modules, {"bleak": fake_bleak}):
            with self.assertRaisesRegex(RuntimeError, "Unreachable"):
                await worker._connect("mac-test-address")
        self.assertNotIn("winrt", FailingClient.last.options)


if __name__ == "__main__":
    unittest.main()
