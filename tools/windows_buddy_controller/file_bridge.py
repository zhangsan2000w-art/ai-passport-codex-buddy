"""Shared, loopback-free transport for Codex Hook events on desktop systems.

Codex Hooks may run in a sandbox whose network namespace cannot reach a desktop
controller on 127.0.0.1.  Small atomically-renamed JSON files under the user's
temporary directory provide a local-only bridge without widening network access.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
import time
import uuid
from typing import Dict, Iterable, Optional

if __package__:
    from .platform_paths import product_data_dir
else:
    from platform_paths import product_data_dir


MAX_BRIDGE_BYTES = 8192
BRIDGE_VERSION = "codex-buddy-bridge-v1"
_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,63}$")


def default_bridge_dir() -> Path:
    override = os.environ.get("CODEX_BUDDY_BRIDGE_DIR")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):
        return product_data_dir() / ("." + BRIDGE_VERSION)
    # In source mode keep the spool inside the Buddy workspace. Sandboxed
    # Codex processes can virtualize a system temporary directory, while this
    # project path is shared with the desktop controller.
    return Path(__file__).resolve().parents[2] / ("." + BRIDGE_VERSION)


def event_dir(root: Optional[Path] = None) -> Path:
    return (root or default_bridge_dir()) / "events"


def approval_dir(root: Optional[Path] = None) -> Path:
    return (root or default_bridge_dir()) / "approvals"


def response_dir(root: Optional[Path] = None) -> Path:
    return (root or default_bridge_dir()) / "responses"


def ensure_bridge_dirs(root: Optional[Path] = None) -> Path:
    selected = root or default_bridge_dir()
    for directory in (event_dir(selected), approval_dir(selected), response_dir(selected)):
        directory.mkdir(parents=True, exist_ok=True)
    return selected


def valid_request_id(request_id: str) -> bool:
    return bool(_SAFE_ID.fullmatch(request_id))


def approval_path(request_id: str, root: Optional[Path] = None) -> Path:
    if not valid_request_id(request_id):
        raise ValueError("invalid approval request id")
    return approval_dir(root) / ("approval-" + request_id + ".json")


def response_path(request_id: str, root: Optional[Path] = None) -> Path:
    if not valid_request_id(request_id):
        raise ValueError("invalid approval request id")
    return response_dir(root) / ("response-" + request_id + ".json")


def atomic_write_json(path: Path, payload: Dict[str, object]) -> None:
    data = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    if len(data) > MAX_BRIDGE_BYTES:
        raise ValueError("bridge message is too large")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        ".%s.%s.%s.tmp" % (path.name, os.getpid(), uuid.uuid4().hex)
    )
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def enqueue_event(payload: Dict[str, object], root: Optional[Path] = None) -> Path:
    selected = ensure_bridge_dirs(root)
    path = event_dir(selected) / (
        "event-%d-%d-%s.json" % (time.time_ns(), os.getpid(), uuid.uuid4().hex)
    )
    atomic_write_json(path, payload)
    return path


def read_json(path: Path) -> Dict[str, object]:
    if path.stat().st_size > MAX_BRIDGE_BYTES:
        raise ValueError("bridge message is too large")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("bridge message must be an object")
    return payload


def iter_ready(directory: Path, pattern: str, limit: int = 64) -> Iterable[Path]:
    try:
        paths = sorted(directory.glob(pattern), key=lambda path: path.name)
    except OSError:
        return ()
    return paths[:limit]
