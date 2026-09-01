"""Aggregate live Codex Hook events into the original Buddy heartbeat shape."""

from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass
import time
from typing import Deque, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class PendingApproval:
    request_id: str
    session_id: str
    turn_id: str
    tool: str
    hint: str


class CodexStateTracker:
    """Tracks ephemeral activity only; no prompt or approval data is persisted."""

    def __init__(self) -> None:
        self._sessions: Dict[str, float] = {}
        self._active_turns: Dict[Tuple[str, str], float] = {}
        self._pending: "OrderedDict[str, PendingApproval]" = OrderedDict()
        self._entries: Deque[str] = deque(maxlen=6)
        self._message = "Codex 已就绪"
        self._last_completed: Optional[Tuple[str, str]] = None
        self._completion_score = 0

    @property
    def current_approval(self) -> Optional[PendingApproval]:
        return next(iter(self._pending.values()), None)

    def apply(self, event: object) -> bool:
        if not isinstance(event, dict):
            return False
        event_type = str(event.get("type") or "")
        session_id = str(event.get("session_id") or "")
        turn_id = str(event.get("turn_id") or "")
        key = (session_id, turn_id)
        now = time.monotonic()
        if session_id:
            self._sessions[session_id] = now

        if event_type == "codex-turn-start":
            self._active_turns[key] = now
            self._message = "Codex 正在处理任务"
            self._add_entry("开始任务", str(event.get("project") or ""))
        elif event_type == "codex-tool-start":
            if session_id or turn_id:
                self._active_turns[key] = now
            tool = str(event.get("tool") or "工具")
            self._message = "Codex 正在使用 " + tool
            self._add_entry(tool, str(event.get("hint") or ""))
        elif event_type == "codex-tool-complete":
            self._message = "Codex 正在处理任务"
        elif event_type == "codex-permission-request":
            request_id = str(event.get("request_id") or "")
            if not request_id or request_id in self._pending:
                return False
            approval = PendingApproval(
                request_id=request_id,
                session_id=session_id,
                turn_id=turn_id,
                tool=str(event.get("tool") or "Codex"),
                hint=str(event.get("hint") or event.get("reason") or ""),
            )
            self._pending[request_id] = approval
            self._message = "Codex 请求授权: " + approval.tool
            self._add_entry("请求授权", approval.tool)
        elif event_type == "codex-permission-resolved":
            request_id = str(event.get("request_id") or "")
            approval = self._pending.pop(request_id, None)
            if approval is None:
                return False
            decision = str(event.get("decision") or "")
            self._add_entry("已允许" if decision == "once" else "已拒绝", approval.tool)
            self._message = "Codex 正在处理任务" if self._active_turns else "Codex 已就绪"
        elif event_type == "codex-turn-complete":
            if self._last_completed == key and (session_id or turn_id):
                return False
            self._last_completed = key
            self._completion_score += 50000
            self._active_turns.pop(key, None)
            for request_id, approval in list(self._pending.items()):
                if (not turn_id or approval.turn_id == turn_id) and (
                    not session_id or approval.session_id == session_id
                ):
                    self._pending.pop(request_id, None)
            self._message = str(event.get("message") or "Codex 任务已完成")
            self._add_entry("任务完成", self._message)
        elif event_type == "codex-session-end":
            self._sessions.pop(session_id, None)
            for active_key in list(self._active_turns):
                if active_key[0] == session_id:
                    self._active_turns.pop(active_key, None)
            for request_id, approval in list(self._pending.items()):
                if approval.session_id == session_id:
                    self._pending.pop(request_id, None)
            self._message = "Codex 已就绪" if self._sessions else "等待 Codex 任务"
        else:
            return False
        return True

    def heartbeat(self) -> Dict[str, object]:
        prompt = self.current_approval
        total = max(len(self._sessions), len(self._active_turns), 1)
        result: Dict[str, object] = {
            "total": total,
            "running": len(self._active_turns),
            "waiting": len(self._pending),
            "message": self._message,
            "entries": list(self._entries),
            # Codex Hooks do not expose token usage. These values are local
            # completion points; each completed turn crosses one firmware
            # celebration boundary without pretending to be API token usage.
            "tokens": self._completion_score,
            "tokens_today": self._completion_score,
        }
        if prompt is not None:
            result["prompt"] = {
                "id": prompt.request_id,
                "tool": prompt.tool,
                "hint": prompt.hint,
            }
        return result

    def _add_entry(self, label: str, detail: str) -> None:
        compact = " ".join(detail.split())
        text = label + (" · " + compact if compact else "")
        self._entries.appendleft(text[:120])
