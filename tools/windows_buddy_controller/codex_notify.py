"""Codex `notify` hook that forwards a minimal event to the local controller."""

import json
import os
from pathlib import Path
import socket
import sys
from typing import Any, Dict, Optional

try:
    from .notify_listener import DEFAULT_HOST, DEFAULT_PORT
except ImportError:
    from notify_listener import DEFAULT_HOST, DEFAULT_PORT


def _compact_text(value: object, maximum_bytes: int = 150) -> str:
    compact = " ".join(str(value or "").split()) or "Codex 任务已完成"
    encoded = compact.encode("utf-8", errors="replace")
    if len(encoded) <= maximum_bytes:
        return encoded.decode("utf-8")
    clipped = encoded[:maximum_bytes]
    while clipped:
        try:
            return clipped.decode("utf-8").rstrip() + "..."
        except UnicodeDecodeError:
            clipped = clipped[:-1]
    return "Codex 任务已完成"


def build_bridge_event(raw: object) -> Optional[Dict[str, str]]:
    try:
        payload: Any = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or payload.get("type") != "agent-turn-complete":
        return None
    cwd = str(payload.get("cwd") or "")
    return {
        "type": "codex-turn-complete",
        "thread_id": str(payload.get("thread-id") or ""),
        "project": Path(cwd).name if cwd else "",
        "message": _compact_text(payload.get("last-assistant-message")),
    }


def main() -> int:
    if len(sys.argv) != 2:
        return 0
    event = build_bridge_event(sys.argv[1])
    if event is None:
        return 0
    port = int(os.environ.get("CODEX_BUDDY_PORT", str(DEFAULT_PORT)))
    data = json.dumps(event, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(data, (DEFAULT_HOST, port))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
