import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from windows_buddy_controller import background_install, bundle_installer, platform_paths


class PlatformPathTests(unittest.TestCase):
    def test_linux_data_path_honors_xdg(self):
        with mock.patch.object(platform_paths.sys, "platform", "linux"), \
                mock.patch.dict(os.environ, {"XDG_DATA_HOME": "/tmp/buddy-data"}):
            self.assertEqual(
                platform_paths.product_data_dir(),
                Path("/tmp/buddy-data/CodexBuddy"),
            )
            self.assertEqual(platform_paths.executable_name("Agent"), "Agent")

    def test_macos_data_path_uses_application_support(self):
        with mock.patch.object(platform_paths.sys, "platform", "darwin"), \
                mock.patch.object(platform_paths.Path, "home", return_value=Path("/Users/test")):
            self.assertEqual(
                platform_paths.product_data_dir(),
                Path("/Users/test/Library/Application Support/CodexBuddy"),
            )

    def test_windows_executable_suffix(self):
        with mock.patch.object(platform_paths.sys, "platform", "win32"):
            self.assertEqual(platform_paths.executable_name("Agent"), "Agent.exe")


class AutostartDocumentTests(unittest.TestCase):
    def test_linux_desktop_entry_runs_background_agent(self):
        with mock.patch.object(background_install, "platform_id", return_value="linux"), \
                mock.patch.object(background_install, "background_command_args",
                                  return_value=["/opt/Codex Buddy/Agent", "background"]):
            entry = background_install.linux_desktop_entry()
        self.assertIn('Exec="/opt/Codex Buddy/Agent" "background"', entry)
        self.assertIn("Terminal=false", entry)

    def test_macos_launch_agent_runs_at_login(self):
        with mock.patch.object(background_install, "background_command_args",
                               return_value=["/Applications/CodexBuddyAgent", "background"]), \
                mock.patch.object(background_install, "background_workdir",
                                  return_value=Path("/Applications")):
            payload = background_install.macos_launch_agent()
        self.assertEqual(payload["Label"], "cn.codexbuddy.bridge")
        self.assertTrue(payload["RunAtLoad"])
        self.assertEqual(payload["ProgramArguments"][-1], "background")

    @mock.patch("windows_buddy_controller.instance_guard.socket.socket")
    def test_background_stop_reaches_current_and_v012_ports(self, socket_factory):
        from windows_buddy_controller.instance_guard import (
            CONTROL_HOST, CONTROL_PORT, LEGACY_CONTROL_PORTS,
            request_background_stop,
        )

        request_background_stop()
        destinations = [
            call.args[1] for call in socket_factory.return_value.__enter__
            .return_value.sendto.call_args_list
        ]
        self.assertIn((CONTROL_HOST, CONTROL_PORT), destinations)
        self.assertIn((CONTROL_HOST, LEGACY_CONTROL_PORTS[0]), destinations)

    def test_macos_bundle_uses_app_executable_for_hook_and_controller(self):
        root = Path("/Applications/Codex Buddy Package")
        with mock.patch.object(bundle_installer, "platform_id", return_value="macos"):
            expected = (root / "Codex Buddy.app" / "Contents" / "MacOS" /
                        "CodexBuddyAgent")
            self.assertEqual(bundle_installer.agent_path(root), expected)
            self.assertEqual(bundle_installer.controller_path(root), expected)

    def test_install_final_does_not_claim_success_when_hook_smoke_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            agent = Path(temporary) / "CodexBuddyAgent.exe"
            agent.touch()
            with mock.patch.object(bundle_installer, "is_frozen", return_value=True), \
                    mock.patch.object(bundle_installer, "bundle_dir",
                                      return_value=agent.parent), \
                    mock.patch.object(bundle_installer, "agent_path", return_value=agent), \
                    mock.patch.object(bundle_installer.hook_health, "read_hook_states",
                                      return_value={}), \
                    mock.patch.object(bundle_installer.install_codex_hooks,
                                      "install_executable", return_value=True), \
                    mock.patch.object(bundle_installer.install_codex_hooks,
                                      "verify_executable_hooks", return_value=[]), \
                    mock.patch.object(bundle_installer.hook_health,
                                      "write_install_receipt"), \
                    mock.patch.object(bundle_installer.hook_health, "smoke_test_agent",
                                      return_value=(False, "broken")), \
                    mock.patch.object(bundle_installer.background_install,
                                      "install") as background_install:
                self.assertEqual(bundle_installer.install_final(), 1)
                background_install.assert_not_called()

    def test_install_waits_for_old_bridge_to_exit_before_copying(self):
        source = Path("C:/package")
        target = Path("C:/installed")
        with mock.patch.object(bundle_installer, "is_frozen", return_value=True), \
                mock.patch.object(bundle_installer, "bundle_dir", return_value=source), \
                mock.patch.object(bundle_installer, "install_dir", return_value=target), \
                mock.patch.object(bundle_installer, "request_background_stop"), \
                mock.patch.object(bundle_installer.hook_health,
                                  "wait_for_bridge_stopped", return_value=False), \
                mock.patch.object(bundle_installer, "_copy_bundle") as copy_bundle:
            self.assertEqual(bundle_installer.install(), 1)
            copy_bundle.assert_not_called()


if __name__ == "__main__":
    unittest.main()
