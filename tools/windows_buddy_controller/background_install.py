"""Install or remove the invisible per-user Windows Buddy bridge."""

from __future__ import annotations

import argparse
from pathlib import Path
import socket
import subprocess
import sys
import time
from typing import Optional
import winreg

if __package__:
    from .controller_settings import load_settings, save_settings
    from .instance_guard import request_background_stop
else:
    from controller_settings import load_settings, save_settings
    from instance_guard import request_background_stop


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "CodexBuddyBridge"


def background_script_path() -> Path:
    return Path(__file__).resolve().with_name("background_bridge.py")


def pythonw_path() -> Path:
    candidate = Path(sys.executable).resolve().with_name("pythonw.exe")
    return candidate if candidate.exists() else Path(sys.executable).resolve()


def startup_command() -> str:
    return subprocess.list2cmdline([
        str(pythonw_path()), str(background_script_path()),
    ])


def autostart_is_installed() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, RUN_VALUE)
    except FileNotFoundError:
        return False
    return isinstance(value, str) and value == startup_command()


def launch_background() -> bool:
    creation_flags = 0
    creation_flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
    creation_flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    try:
        subprocess.Popen(
            [str(pythonw_path()), str(background_script_path())],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=creation_flags,
            cwd=str(background_script_path().parents[2]),
        )
    except OSError:
        return False
    return True


def bridge_is_active() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 17322), timeout=0.2):
            return True
    except OSError:
        return False


def install() -> bool:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
        winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, startup_command())
    settings = load_settings()
    settings.autostart_enabled = True
    save_settings(settings)
    return True if bridge_is_active() else launch_background()


def uninstall() -> None:
    request_background_stop()
    time.sleep(0.2)
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, RUN_VALUE)
    except FileNotFoundError:
        pass
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
