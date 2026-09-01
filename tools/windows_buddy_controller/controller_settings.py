"""Small local settings file for unattended Codex Buddy reconnects."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Optional


@dataclass
class ControllerSettings:
    last_device_address: str = ""
    owner: str = "用户"
    autostart_enabled: bool = False


def default_settings_path() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    if not root:
        root = tempfile.gettempdir()
    return Path(root) / "CodexBuddy" / "settings.json"


def load_settings(path: Optional[Path] = None) -> ControllerSettings:
    selected = path or default_settings_path()
    try:
        payload = json.loads(selected.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ControllerSettings()
    if not isinstance(payload, dict):
        return ControllerSettings()
    address = payload.get("last_device_address")
    owner = payload.get("owner")
    autostart = payload.get("autostart_enabled")
    return ControllerSettings(
        last_device_address=address if isinstance(address, str) else "",
        owner=owner if isinstance(owner, str) and owner else "用户",
        autostart_enabled=bool(autostart) if isinstance(autostart, bool) else False,
    )


def save_settings(settings: ControllerSettings,
                  path: Optional[Path] = None) -> None:
    selected = path or default_settings_path()
    selected.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(asdict(settings), ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")
    temporary = selected.with_name(
        ".%s.%d.tmp" % (selected.name, os.getpid())
    )
    try:
        with temporary.open("wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, selected)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
