import json
from pathlib import Path
import tempfile
import unittest

from windows_buddy_controller.controller_settings import (
    ControllerSettings,
    load_settings,
    save_settings,
)


class ControllerSettingsTests(unittest.TestCase):
    def test_round_trip_preserves_only_background_preferences(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "settings.json"
            expected = ControllerSettings(
                last_device_address="device-address",
                owner="用户",
                autostart_enabled=True,
            )
            save_settings(expected, path)
            self.assertEqual(load_settings(path), expected)
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("prompt", payload)
            self.assertNotIn("approval", payload)

    def test_invalid_file_uses_safe_defaults(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "settings.json"
            path.write_text("not json", encoding="utf-8")
            settings = load_settings(path)
            self.assertEqual(settings.last_device_address, "")
            self.assertEqual(settings.owner, "用户")
            self.assertFalse(settings.autostart_enabled)


if __name__ == "__main__":
    unittest.main()
