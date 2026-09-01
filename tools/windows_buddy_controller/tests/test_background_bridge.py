import logging
from pathlib import Path
import tempfile
import unittest

from windows_buddy_controller.background_bridge import BackgroundBridge
from windows_buddy_controller.ble_client import DeviceInfo
from windows_buddy_controller.controller_settings import (
    ControllerSettings,
    load_settings,
    save_settings,
)


class FakeBle:
    def __init__(self):
        self.connected_to = []
        self.sent = []

    def connect(self, address):
        self.connected_to.append(address)

    def send(self, payload):
        self.sent.append(payload)


class BackgroundBridgeTests(unittest.TestCase):
    def test_prefers_saved_card_and_remembers_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "settings.json"
            save_settings(ControllerSettings(last_device_address="saved"), path)
            bridge = BackgroundBridge(path, logging.getLogger("buddy-test"))
            fake = FakeBle()
            bridge.ble = fake
            bridge._handle_devices([
                DeviceInfo("Codex-OTHER", "other"),
                DeviceInfo("Codex-SAVED", "saved"),
            ])
            self.assertEqual(fake.connected_to, ["saved"])
            bridge._handle_connected(True)
            self.assertTrue(bridge.connected)
            self.assertEqual(load_settings(path).last_device_address, "saved")
            self.assertGreaterEqual(len(fake.sent), 3)

    def test_without_saved_card_only_unambiguous_scan_connects(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "settings.json"
            bridge = BackgroundBridge(path, logging.getLogger("buddy-test"))
            fake = FakeBle()
            bridge.ble = fake
            bridge._handle_devices([
                DeviceInfo("Codex-A", "a"),
                DeviceInfo("Codex-B", "b"),
            ])
            self.assertEqual(fake.connected_to, [])
            bridge._handle_devices([DeviceInfo("Codex-A", "a")])
            self.assertEqual(fake.connected_to, ["a"])

    def test_saved_card_never_falls_back_to_a_different_card(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "settings.json"
            save_settings(ControllerSettings(last_device_address="saved"), path)
            bridge = BackgroundBridge(path, logging.getLogger("buddy-test"))
            fake = FakeBle()
            bridge.ble = fake
            bridge._handle_devices([DeviceInfo("Codex-OTHER", "other")])
            self.assertEqual(fake.connected_to, [])


if __name__ == "__main__":
    unittest.main()
