"""Codex lifecycle Hook adapter for the local Codex Buddy controller.

The command reads one official Codex Hook JSON object from stdin.  Informational
events are sent over loopback UDP.  PermissionRequest uses a loopback TCP
request so the Hook can wait for the first decision made on the desktop UI or
the physical Buddy without exposing a listener outside this computer.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import time
from typing import Any, Dict, Optional

try:
    from .file_bridge import (approval_path, atomic_write_json,
                              default_bridge_dir, enqueue_event, read_json,
                              response_path)
    from .notify_listener import (DEFAULT_APPROVAL_PORT, DEFAULT_HOST,
                                  DEFAULT_PORT)
except ImportError:
    from file_bridge import (approval_path, atomic_write_json,
                             default_bridge_dir, enqueue_event, read_json,
                             response_path)
    from notify_listener import DEFAULT_APPROVAL_PORT, DEFAULT_HOST, DEFAULT_PORT


MAX_EVENT_BYTES = 8192
MAX_HINT_BYTES = 180
DEFAULT_APPROVAL_TIMEOUT = 590.0


def _compact_text(value: object, maximum_bytes: int) -> str:
    compact = " ".join(str(value or "").split())
    # Windows hook input can contain an unpaired UTF-16 surrogate when a
    # PowerShell/native-process boundary clips or substitutes a character.
    # Replace only the malformed code point so observability and, critically,
    # PermissionRequest delivery continue instead of crashing the hook.
    encoded = compact.encode("utf-8", errors="replace")
    if len(encoded) <= maximum_bytes:
        return encoded.decode("utf-8")
    clipped = encoded[:maximum_bytes]
    while clipped:
        try:
            return clipped.decode("utf-8").rstrip() + "..."
        except UnicodeDecodeError:
            clipped = clipped[:-1]
    return ""


def _project(payload: Dict[str, Any]) -> str:
    cwd = str(payload.get("cwd") or "")
    return Path(cwd).name if cwd else ""


def _tool_hint(tool_input: object) -> str:
    if not isinstance(tool_input, dict):
        return _compact_text(tool_input, MAX_HINT_BYTES)
    description = tool_input.get("description")
    command = tool_input.get("command")
    if command:
        return _compact_text(command, MAX_HINT_BYTES)
    if description:
        return _compact_text(description, MAX_HINT_BYTES)
    # MCP and other local tools do not share one stable preview field.  Avoid
    # forwarding their complete argument object to the small physical display.
    keys = ", ".join(str(key) for key in list(tool_input)[:5])
    return _compact_text(keys, MAX_HINT_BYTES)


def _base_event(payload: Dict[str, Any], event_type: str) -> Dict[str, str]:
    return {
        "type": event_type,
        "source": "hook",
        "session_id": str(payload.get("session_id") or ""),
        "turn_id": str(payload.get("turn_id") or ""),
        "project": _project(payload),
        "model": str(payload.get("model") or ""),
    }


def build_lifecycle_event(payload: object) -> Optional[Dict[str, str]]:
    if not isinstance(payload, dict):
        return None
    hook_name = str(payload.get("hook_event_name") or "")
    if hook_name == "UserPromptSubmit":
        return _base_event(payload, "codex-turn-start")
    if hook_name in ("PreToolUse", "PostToolUse"):
        event = _base_event(
            payload,
            "codex-tool-start" if hook_name == "PreToolUse" else "codex-tool-complete",
        )
        event["tool"] = _compact_text(payload.get("tool_name"), 48)
        event["hint"] = _tool_hint(payload.get("tool_input"))
        return event
    if hook_name == "Stop":
        event = _base_event(payload, "codex-turn-complete")
        # Keep the small card's completion state deterministic. The full final
        # answer belongs on the computer and can otherwise look like another
        # in-progress message when clipped to the display.
        event["message"] = "Codex 任务已完成"
        return event
    if hook_name == "SessionEnd":
        return _base_event(payload, "codex-session-end")
    return None


def _approval_id(payload: Dict[str, Any]) -> str:
    # The public PermissionRequest Hook payload has no tool-use id.  A digest of
    # this invocation plus fresh process entropy is short enough for the Buddy
    # protocol and cannot reveal the command contents.
    material = "|".join((
        str(payload.get("session_id") or ""),
        str(payload.get("turn_id") or ""),
        str(payload.get("tool_name") or ""),
        str(os.getpid()),
        os.urandom(8).hex(),
    ))
    return "cx_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def build_approval_event(payload: object,
                         request_id: Optional[str] = None) -> Optional[Dict[str, str]]:
    if not isinstance(payload, dict) or payload.get("hook_event_name") != "PermissionRequest":
        return None
    event = _base_event(payload, "codex-permission-request")
    event["request_id"] = request_id or _approval_id(payload)
    event["tool"] = _compact_text(payload.get("tool_name") or "Codex", 48)
    event["hint"] = _tool_hint(payload.get("tool_input"))
    reason = ""
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        reason = _compact_text(tool_input.get("description"), 120)
    event["reason"] = reason
    return event


def permission_output(decision: str) -> Optional[Dict[str, object]]:
    if decision == "once":
        behavior: Dict[str, str] = {"behavior": "allow"}
    elif decision == "deny":
        behavior = {"behavior": "deny", "message": "已在 Codex Buddy 上拒绝。"}
    else:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": behavior,
        }
    }


def _send_lifecycle(event: Dict[str, str]) -> None:
    try:
        enqueue_event(event)
        return
    except (OSError, ValueError):
        # Keep the original loopback transport as a compatibility fallback.
        pass
    port = int(os.environ.get("CODEX_BUDDY_PORT", str(DEFAULT_PORT)))
    data = json.dumps(event, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(data) > MAX_EVENT_BYTES:
        return
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(data, (DEFAULT_HOST, port))


def _request_approval_file(event: Dict[str, str], timeout: float) -> Optional[str]:
    request_id = str(event.get("request_id") or "")
    root = default_bridge_dir()
    request = approval_path(request_id, root)
    response = response_path(request_id, root)
    try:
        try:
            response.unlink()
        except FileNotFoundError:
            pass
        atomic_write_json(request, event)
        deadline = time.monotonic() + max(1.0, timeout)
        while time.monotonic() < deadline:
            try:
                result = read_json(response)
            except FileNotFoundError:
                time.sleep(0.1)
                continue
            decision = result.get("decision")
            return str(decision) if decision in ("once", "deny") else None
        return None
    finally:
        for path in (request, response):
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def _request_approval_socket(event: Dict[str, str], timeout: float) -> Optional[str]:
    port = int(os.environ.get(
        "CODEX_BUDDY_APPROVAL_PORT", str(DEFAULT_APPROVAL_PORT)
    ))
    data = json.dumps(event, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
    if len(data) > MAX_EVENT_BYTES:
        return None
    try:
        with socket.create_connection((DEFAULT_HOST, port), timeout=1.5) as sock:
            sock.settimeout(max(1.0, timeout))
            sock.sendall(data)
            response = bytearray()
            while len(response) < 1024:
                chunk = sock.recv(1024 - len(response))
                if not chunk:
                    break
                response.extend(chunk)
                if b"\n" in chunk:
                    break
    except (OSError, ValueError):
        return None
    try:
        result = json.loads(bytes(response).split(b"\n", 1)[0].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if isinstance(result, dict) and result.get("decision") in ("once", "deny"):
        return str(result["decision"])
    return None


def _request_approval(event: Dict[str, str]) -> Optional[str]:
    timeout = float(os.environ.get(
        "CODEX_BUDDY_APPROVAL_TIMEOUT", str(DEFAULT_APPROVAL_TIMEOUT)
    ))
    try:
        return _request_approval_file(event, timeout)
    except (OSError, ValueError):
        return _request_approval_socket(event, timeout)


def run_hook(payload: object) -> Optional[Dict[str, object]]:
    if isinstance(payload, dict) and payload.get("hook_event_name") == "PermissionRequest":
        event = build_approval_event(payload)
        if event is None:
            return None
        return permission_output(_request_approval(event) or "")
    event = build_lifecycle_event(payload)
    if event is not None:
        try:
            _send_lifecycle(event)
        except (OSError, ValueError):
            # Observability must never break the active Codex turn.
            pass
    if isinstance(payload, dict) and payload.get("hook_event_name") == "Stop":
        return {}
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 0
    result = run_hook(payload)
    if result is not None:
        sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
