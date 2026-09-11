"""Cross-platform paths and executable names for Codex Buddy."""

from __future__ import annotations

import os
from pathlib import Path
import sys


def platform_id() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def executable_name(stem: str) -> str:
    return stem + ".exe" if platform_id() == "windows" else stem


def product_data_dir() -> Path:
    current = platform_id()
    if current == "windows":
        root = os.environ.get("LOCALAPPDATA")
        if root:
            return Path(root) / "CodexBuddy"
        return Path.home() / "AppData" / "Local" / "CodexBuddy"
    if current == "macos":
        return Path.home() / "Library" / "Application Support" / "CodexBuddy"
    root = os.environ.get("XDG_DATA_HOME")
    return (Path(root) if root else Path.home() / ".local" / "share") / "CodexBuddy"


def linux_autostart_dir() -> Path:
    root = os.environ.get("XDG_CONFIG_HOME")
    return (Path(root) if root else Path.home() / ".config") / "autostart"
