"""Install or remove the invisible per-user desktop Buddy bridge."""

from __future__ import annotations

import argparse
from pathlib import Path
import plistlib
import shlex
import socket
import subprocess
import sys
import time
from typing import Optional

if __package__:
    from .controller_settings import load_settings, save_settings
    from .instance_guard import request_background_stop
    from .platform_paths import (executable_name, linux_autostart_dir,
                                 platform_id)
else:
    from controller_settings import load_settings, save_settings
    from instance_guard import request_background_stop
    from platform_paths import (executable_name, linux_autostart_dir,
                                platform_id)


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "CodexBuddyBridge"
MACOS_LABEL = "cn.codexbuddy.bridge"
LINUX_DESKTOP_NAME = "codex-buddy.desktop"


def background_script_path() -> Path:
    return Path(__file__).resolve().with_name("background_bridge.py")


def source_python_path() -> Path:
    current = Path(sys.executable).resolve()
    if platform_id() == "windows":
        candidate = current.with_name("pythonw.exe")
        if candidate.exists():
            return candidate
    return current


def packaged_agent_path() -> Path:
    current = Path(sys.executable).resolve()
    candidate = current.with_name(executable_name("CodexBuddyAgent"))
    return candidate if candidate.exists() else current


def background_command_args() -> list[str]:
    if getattr(sys, "frozen", False):
        return [str(packaged_agent_path()), "background"]
    return [str(source_python_path()), str(background_script_path())]


def background_workdir() -> Path:
    if getattr(sys, "frozen", False):
        return packaged_agent_path().parent
    return background_script_path().parents[2]


def startup_command() -> str:
    arguments = background_command_args()
    if platform_id() == "windows":
        return subprocess.list2cmdline(arguments)
    return shlex.join(arguments)


def macos_launch_agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{MACOS_LABEL}.plist"


def macos_launch_agent() -> dict[str, object]:
    return {
        "Label": MACOS_LABEL,
        "ProgramArguments": background_command_args(),
        "RunAtLoad": True,
        "WorkingDirectory": str(background_workdir()),
        "StandardOutPath": "/dev/null",
        "StandardErrorPath": "/dev/null",
        "ProcessType": "Background",
    }


def linux_desktop_path() -> Path:
    return linux_autostart_dir() / LINUX_DESKTOP_NAME


def _desktop_exec_argument(argument: str) -> str:
    escaped = (argument.replace("\\", "\\\\")
               .replace('"', '\\"')
               .replace("`", "\\`")
               .replace("$", "\\$"))
    return '"%s"' % escaped


def linux_desktop_entry() -> str:
    command = " ".join(_desktop_exec_argument(value)
                       for value in background_command_args())
    return "\n".join((
        "[Desktop Entry]",
        "Type=Application",
        "Version=1.0",
        "Name=Codex Buddy Bridge",
        f"Exec={command}",
        "Terminal=false",
        "X-GNOME-Autostart-enabled=true",
        "Comment=Sync local Codex status to Codex Buddy",
        "",
    ))


def _windows_autostart_value() -> Optional[str]:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, RUN_VALUE)
    except FileNotFoundError:
        return None
    return value if isinstance(value, str) else None


def autostart_is_installed() -> bool:
    current = platform_id()
    if current == "windows":
        return _windows_autostart_value() == startup_command()
    if current == "macos":
        try:
            with macos_launch_agent_path().open("rb") as handle:
                payload = plistlib.load(handle)
        except (FileNotFoundError, OSError, plistlib.InvalidFileException):
            return False
        return payload.get("ProgramArguments") == background_command_args()
    try:
        return linux_desktop_path().read_text(encoding="utf-8") == linux_desktop_entry()
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        return False


def launch_background() -> bool:
    options: dict[str, object] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
        "cwd": str(background_workdir()),
    }
    if platform_id() == "windows":
        options["creationflags"] = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0) |
            getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    else:
        options["start_new_session"] = True
    try:
        subprocess.Popen(background_command_args(), **options)
    except OSError:
        return False
    return True


def bridge_is_active() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 17322), timeout=0.2):
            return True
    except OSError:
        return False


def _write_autostart() -> None:
    current = platform_id()
    if current == "windows":
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, startup_command())
        return
    if current == "macos":
        target = macos_launch_agent_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            plistlib.dump(macos_launch_agent(), handle, sort_keys=True)
        return
    target = linux_desktop_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(linux_desktop_entry(), encoding="utf-8")


def _remove_autostart() -> None:
    current = platform_id()
    if current == "windows":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                                winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, RUN_VALUE)
        except FileNotFoundError:
            pass
        return
    target = macos_launch_agent_path() if current == "macos" else linux_desktop_path()
    try:
        target.unlink()
    except FileNotFoundError:
        pass


def install() -> bool:
    _write_autostart()
    settings = load_settings()
    settings.autostart_enabled = True
    save_settings(settings)
    return True if bridge_is_active() else launch_background()


def uninstall() -> None:
    request_background_stop()
    time.sleep(0.2)
    _remove_autostart()
    settings = load_settings()
    settings.autostart_enabled = False
    save_settings(settings)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Codex Buddy 后台桥管理")
    parser.add_argument("action", choices=("install", "uninstall", "start", "stop", "status"))
    args = parser.parse_args(argv)
    if args.action == "install":
        if not install():
            print("后台自动启动已安装，但本次启动失败。")
            return 1
        print("后台自动启动已安装并启动。")
    elif args.action == "uninstall":
        uninstall()
        print("后台自动启动已卸载。")
    elif args.action == "start":
        if not launch_background():
            print("后台桥启动失败。")
            return 1
        print("后台桥启动命令已发送。")
    elif args.action == "stop":
        request_background_stop()
        print("后台桥停止命令已发送。")
    else:
        print("已安装" if autostart_is_installed() else "未安装")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
