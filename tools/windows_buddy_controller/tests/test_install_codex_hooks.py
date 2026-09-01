import tempfile
from pathlib import Path
import unittest

from windows_buddy_controller.install_codex_hooks import (
    build_hook_groups,
    merge_hooks,
    remove_hooks,
)


class InstallCodexHooksTests(unittest.TestCase):
    def test_merge_preserves_other_hooks_and_is_idempotent(self):
        root = Path(tempfile.gettempdir()) / "codex-buddy-test"
        additions = build_hook_groups(root / "python.exe", root / "codex_hook.py")
        existing = {
            "description": "keep me",
            "hooks": {
                "Stop": [{"hooks": [{"type": "command", "command": "other.py"}]}],
            },
        }
        once = merge_hooks(existing, additions)
        twice = merge_hooks(once, additions)
        self.assertEqual(once, twice)
        self.assertEqual(twice["description"], "keep me")
        self.assertEqual(len(twice["hooks"]["Stop"]), 2)
        handler = twice["hooks"]["UserPromptSubmit"][0]["hooks"][0]
        self.assertTrue(handler["commandWindows"].startswith("& \""))

    def test_remove_only_removes_buddy_handlers(self):
        root = Path(tempfile.gettempdir()) / "codex-buddy-test"
        additions = build_hook_groups(root / "python.exe", root / "codex_hook.py")
        document = merge_hooks({
            "hooks": {
                "PermissionRequest": [{
                    "hooks": [{"type": "command", "command": "policy.py"}]
                }]
            }
        }, additions)
        cleaned = remove_hooks(document)
        groups = cleaned["hooks"]["PermissionRequest"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["hooks"][0]["command"], "policy.py")


if __name__ == "__main__":
    unittest.main()
