import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from windows_buddy_controller import hook_health, install_codex_hooks


class HookHealthTests(unittest.TestCase):
    def _write_config(self, target: Path, document: dict,
                      hashes: dict[str, str], disabled: str = "") -> Path:
        config_path = target.parent / "config.toml"
        lines = []
        locations = install_codex_hooks.buddy_handler_locations(document)
        for event, (group_index, handler_index, _) in locations.items():
            key = hook_health._state_key(
                target, event, group_index, handler_index,
            )
            lines.extend((
                "[hooks.state.'%s']" % key,
                'trusted_hash = "%s"' % hashes[event],
            ))
            if event == disabled:
                lines.append("enabled = false")
            lines.append("")
        config_path.write_text("\n".join(lines), encoding="utf-8")
        return config_path

    def test_reads_six_trusted_hook_states_and_detects_disabled_event(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / ".codex" / "hooks.json"
            agent = root / "CodexBuddyAgent.exe"
            install_codex_hooks.install_executable(target, agent)
            document = install_codex_hooks.read_document(target)
            hashes = {event: "hash-" + event for event in install_codex_hooks.HOOK_EVENTS}
            config = self._write_config(target, document, hashes, "PreToolUse")

            states = hook_health.read_hook_states(target, config)
            self.assertEqual(len(states), 6)
            self.assertFalse(states["PreToolUse"].enabled)
            self.assertEqual(
                hook_health.trust_status(target, config, agent, states),
                "disabled",
            )

    def test_changed_hook_requires_refreshed_trust_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / ".codex" / "hooks.json"
            agent = root / "CodexBuddyAgent.exe"
            install_codex_hooks.install_executable(target, agent)
            document = install_codex_hooks.read_document(target)
            old_hashes = {event: "old-" + event for event in install_codex_hooks.HOOK_EVENTS}
            config = self._write_config(target, document, old_hashes)
            states = hook_health.read_hook_states(target, config)
            receipt = root / "receipt.json"

            with mock.patch.object(hook_health, "receipt_path", return_value=receipt):
                hook_health.write_install_receipt(target, agent, True, states)
                self.assertEqual(
                    hook_health.trust_status(target, config, agent, states),
                    "pending",
                )

                new_hashes = {
                    event: "new-" + event for event in install_codex_hooks.HOOK_EVENTS
                }
                config = self._write_config(target, document, new_hashes)
                refreshed = hook_health.read_hook_states(target, config)
                self.assertEqual(
                    hook_health.trust_status(target, config, agent, refreshed),
                    "confirmed",
                )

    def test_finds_single_packaged_agent_in_all_six_hooks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / ".codex" / "hooks.json"
            agent = root / "App-0.1.4" / "CodexBuddyAgent.exe"
            install_codex_hooks.install_executable(target, agent)
            self.assertEqual(
                hook_health.packaged_agent_from_hooks(target), agent.resolve(),
            )

    def test_report_exit_code_distinguishes_user_trust_from_broken_install(self):
        pending = hook_health.HookHealthReport(
            agent=Path("CodexBuddyAgent.exe"),
            smoke_ok=True,
            bridge_ok=True,
            trust_status="pending",
        )
        self.assertEqual(hook_health.exit_code(pending), 2)
        pending.trust_status = "confirmed"
        self.assertEqual(hook_health.exit_code(pending), 0)
        pending.hook_errors.append("broken")
        self.assertEqual(hook_health.exit_code(pending), 1)


if __name__ == "__main__":
    unittest.main()
