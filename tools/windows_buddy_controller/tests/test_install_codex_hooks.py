import tempfile
from pathlib import Path
import unittest

from windows_buddy_controller.install_codex_hooks import (
    build_executable_hook_groups,
    build_hook_groups,
    install_executable,
    merge_hooks,
    remove_hooks,
    verify_executable_hooks,
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

    def test_packaged_agent_hook_works_on_all_desktop_platforms(self):
        root = Path(tempfile.gettempdir()) / "Codex Buddy"
        additions = build_executable_hook_groups(root / "CodexBuddyAgent")
        handler = additions["PermissionRequest"][0]["hooks"][0]
        self.assertEqual(
            handler["command"],
            '"%s" hook' % (root / "CodexBuddyAgent").resolve(),
        )
        self.assertEqual(handler["commandWindows"], "& " + handler["command"])
        self.assertEqual(handler["timeout"], 600)
        cleaned = remove_hooks(merge_hooks({}, additions))
        self.assertNotIn("PermissionRequest", cleaned["hooks"])

    def test_packaged_install_is_verified_and_second_install_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "home" / ".codex" / "hooks.json"
            agent = root / "Codex Buddy" / "CodexBuddyAgent.exe"
            agent.parent.mkdir(parents=True)
            agent.touch()

            self.assertTrue(install_executable(target, agent))
            self.assertEqual(verify_executable_hooks(target, agent), [])
            self.assertFalse(install_executable(target, agent))

            wrong_agent = root / "Other" / "CodexBuddyAgent.exe"
            errors = verify_executable_hooks(target, wrong_agent)
            self.assertEqual(len(errors), 6)


if __name__ == "__main__":
    unittest.main()
