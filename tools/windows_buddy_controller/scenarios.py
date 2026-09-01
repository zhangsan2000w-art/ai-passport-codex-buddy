"""Manual and automatic Hardware Buddy heartbeat scenarios."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import uuid


@dataclass(frozen=True)
class Scenario:
    name: str
    total: int
    running: int
    message: str


class ScenarioController:
    AUTO: List[Scenario] = [
        Scenario("空闲", 1, 0, "Codex 已就绪"),
        Scenario("工作中", 1, 1, "Codex 正在处理任务"),
        Scenario("待确认", 1, 0, "Codex 请求授权"),
        Scenario("已完成", 1, 0, "Codex 任务已完成"),
        Scenario("休眠", 0, 0, "等待 Codex 通知"),
    ]

    def __init__(self) -> None:
        self.total = 1
        self.running = 0
        self.message = "Codex 已就绪"
        self.entries: List[str] = []
        self.tokens = 0
        self.tokens_today = 0
        self.prompt: Optional[Dict[str, str]] = None
        self._auto_index = -1

    def set_idle(self) -> None:
        self.total, self.running, self.message = 1, 0, "Codex 已就绪"
        self.prompt = None

    def set_busy(self) -> None:
        self.total, self.running, self.message = 1, 1, "Codex 正在处理任务"
        self.prompt = None

    def set_completed(self, message: str = "Codex 任务已完成") -> None:
        self.total, self.running, self.message = 1, 0, message
        self.prompt = None
        # The firmware celebrates each 50k boundary. Here the value is a local
        # completion score, not an OpenAI token-usage claim.
        self.tokens += 50000
        self.tokens_today += 50000

    def set_sleep(self) -> None:
        self.total, self.running, self.message = 0, 0, "等待 Codex 通知"
        self.prompt = None

    def set_approval(self, request_id: str, tool: str, hint: str) -> None:
        self.total, self.running, self.message = 1, 0, "Codex 请求授权: " + tool
        self.prompt = {"id": request_id, "tool": tool, "hint": hint}

    def set_fresh_approval(self, tool: str, hint: str) -> str:
        # The firmware remembers the last attempted approval id so a replayed
        # heartbeat cannot trigger a second decision. Every test request must
        # therefore use a fresh, bounded id just like a real Codex request.
        request_id = "manual_" + uuid.uuid4().hex[:20]
        self.set_approval(request_id, tool, hint)
        return request_id

    def clear_prompt(self) -> None:
        self.prompt = None
        self.message = "Codex 已就绪"

    def resolve_approval(self, request_id: str, decision: str) -> bool:
        """Resolve the active manual approval without involving a Codex Hook."""
        if (not self.prompt or self.prompt.get("id") != request_id or
                decision not in ("once", "deny")):
            return False
        if decision == "once":
            self.set_completed("审批已允许 · Codex 任务已完成")
        else:
            self.prompt = None
            self.running = 0
            self.message = "审批已拒绝"
        return True

    def advance_auto(self) -> Scenario:
        self._auto_index = (self._auto_index + 1) % len(self.AUTO)
        scenario = self.AUTO[self._auto_index]
        if scenario.name == "空闲":
            self.set_idle()
        elif scenario.name == "工作中":
            self.set_busy()
        elif scenario.name == "待确认":
            self.set_fresh_approval("Shell", "echo automatic scenario")
        elif scenario.name == "已完成":
            self.set_completed()
        else:
            self.set_sleep()
        return scenario

    def heartbeat(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "total": self.total,
            "running": self.running,
            "waiting": 1 if self.prompt else 0,
            "message": self.message,
            "entries": list(self.entries),
            "tokens": self.tokens,
            "tokens_today": self.tokens_today,
        }
        if self.prompt:
            result["prompt"] = dict(self.prompt)
        return result
