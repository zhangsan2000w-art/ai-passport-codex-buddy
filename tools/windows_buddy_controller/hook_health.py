"""Validate the installed Codex Hook without bypassing Codex trust."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import tempfile
import time
import tomllib
from typing import Dict, Optional

from .file_bridge import event_dir, read_json
from .install_codex_hooks import (HOOK_EVENTS, buddy_handler_locations,
                                  read_document, verify_executable_hooks)
from .platform_paths import platform_id, product_data_dir


RECEIPT_NAME = "hook-install-state.json"
HOOK_EVENT_SLUGS = {
    "UserPromptSubmit": "user_prompt_submit",
    "PreToolUse": "pre_tool_use",
    "PostToolUse": "post_tool_use",
    "PermissionRequest": "permission_request",
    "Stop": "stop",
    "SessionEnd": "session_end",
}
_PACKAGED_COMMAND = re.compile(r'^"([^"]+)"\s+hook$')


@dataclass(frozen=True)
class HookState:
    trusted_hash: str = ""
    enabled: bool = True


@dataclass
class HookHealthReport:
    agent: Optional[Path] = None
    hook_errors: list[str] = field(default_factory=list)
    smoke_ok: bool = False
    smoke_detail: str = "未执行"
    bridge_ok: bool = False
    trust_status: str = "unknown"
    trusted_count: int = 0
    enabled_count: int = 0

    @property
    def configuration_ok(self) -> bool:
        return self.agent is not None and not self.hook_errors

    @property
    def ready(self) -> bool:
        return (self.configuration_ok and self.smoke_ok and self.bridge_ok and
                self.trust_status == "confirmed")


def default_hooks_path() -> Path:
    return Path.home() / ".codex" / "hooks.json"


def default_codex_config_path() -> Path:
    return Path.home() / ".codex" / "config.toml"


def receipt_path() -> Path:
    return product_data_dir() / RECEIPT_NAME


def packaged_agent_from_hooks(target: Path) -> Optional[Path]:
    try:
        locations = buddy_handler_locations(read_document(target))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    paths: set[Path] = set()
    for _, _, handler in locations.values():
        command = str(handler.get("command") or "")
        match = _PACKAGED_COMMAND.fullmatch(command)
        if match is None:
            return None
        paths.add(Path(match.group(1)))
    return next(iter(paths)) if len(paths) == 1 else None


def _state_key(target: Path, event: str, group_index: int,
               handler_index: int) -> str:
    return "%s:%s:%d:%d" % (
        target.resolve(), HOOK_EVENT_SLUGS[event], group_index, handler_index,
    )


def _normalized_key(value: str) -> str:
    return os.path.normcase(os.path.normpath(value))


def read_hook_states(target: Path, config_path: Path) -> Dict[str, HookState]:
    try:
        document = read_document(target)
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError, tomllib.TOMLDecodeError,
            json.JSONDecodeError):
        return {}
    hooks = config.get("hooks")
    states = hooks.get("state") if isinstance(hooks, dict) else None
    if not isinstance(states, dict):
        return {}
    normalized_states = {
        _normalized_key(str(key)): value
        for key, value in states.items()
        if isinstance(value, dict)
    }
    result: Dict[str, HookState] = {}
    for event, (group_index, handler_index, _) in buddy_handler_locations(document).items():
        key = _normalized_key(_state_key(target, event, group_index, handler_index))
        value = normalized_states.get(key)
        if not isinstance(value, dict):
            continue
        trusted_hash = value.get("trusted_hash")
        result[event] = HookState(
            trusted_hash=(trusted_hash if isinstance(trusted_hash, str) else ""),
            enabled=value.get("enabled") is not False,
        )
    return result


def write_install_receipt(target: Path, agent: Path, changed: bool,
                          previous: Dict[str, HookState]) -> None:
    destination = receipt_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": 1,
        "hooks_path": str(target.resolve()),
        "agent_path": str(agent.resolve()),
        "hook_document_changed": changed,
        "installed_at_ns": time.time_ns(),
        "previous_trusted_hashes": {
            event: state.trusted_hash for event, state in previous.items()
        },
    }
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, destination)


def _load_receipt(target: Path, agent: Path) -> Optional[dict[str, object]]:
    try:
        payload = json.loads(receipt_path().read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if (_normalized_key(str(payload.get("hooks_path") or "")) !=
            _normalized_key(str(target.resolve()))):
        return None
    if (_normalized_key(str(payload.get("agent_path") or "")) !=
            _normalized_key(str(agent.resolve()))):
        return None
    return payload


def trust_status(target: Path, config_path: Path, agent: Path,
                 states: Dict[str, HookState]) -> str:
    if any(not states.get(event, HookState()).enabled for event in HOOK_EVENTS):
        return "disabled"
    if any(not states.get(event, HookState()).trusted_hash for event in HOOK_EVENTS):
        return "pending"
    receipt = _load_receipt(target, agent)
    if not receipt or receipt.get("hook_document_changed") is not True:
        return "confirmed"
    previous = receipt.get("previous_trusted_hashes")
    if not isinstance(previous, dict):
        return "pending"
    refreshed = all(
        states[event].trusted_hash != str(previous.get(event) or "")
        for event in HOOK_EVENTS
    )
    return "confirmed" if refreshed else "pending"


def smoke_test_agent(agent: Path) -> tuple[bool, str]:
    if not agent.is_file():
        return False, "Hook 可执行文件不存在"
    parent = product_data_dir()
    parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix="hook-smoke-", dir=parent))
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "codex-buddy-install-check",
        "turn_id": "install-check",
        "cwd": str(product_data_dir()),
        "model": "health-check",
    }
    environment = os.environ.copy()
    environment["CODEX_BUDDY_BRIDGE_DIR"] = str(temporary_root)
    options: dict[str, object] = {}
    if platform_id() == "windows":
        options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        result = subprocess.run(
            [str(agent), "hook"],
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=15,
            cwd=agent.parent,
            env=environment,
            check=False,
            **options,
        )
        if result.returncode != 0:
            return False, "Hook 进程退出码为 %d" % result.returncode
        paths = list(event_dir(temporary_root).glob("event-*.json"))
        if len(paths) != 1:
            return False, "Hook 未生成唯一测试事件"
        event = read_json(paths[0])
        if (event.get("type") != "codex-turn-start" or
                event.get("source") != "hook"):
            return False, "Hook 测试事件内容不正确"
        return True, "Hook 可执行文件与事件写入正常"
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return False, "Hook 冒烟测试失败：%s" % error
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


def bridge_is_ready() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 17322), timeout=0.3):
            return True
    except OSError:
        return False


def wait_for_bridge(timeout: float = 8.0) -> bool:
    deadline = time.monotonic() + max(0.0, timeout)
    while time.monotonic() < deadline:
        if bridge_is_ready():
            return True
        time.sleep(0.1)
    return bridge_is_ready()


def wait_for_bridge_stopped(timeout: float = 8.0) -> bool:
    deadline = time.monotonic() + max(0.0, timeout)
    while time.monotonic() < deadline:
        if not bridge_is_ready():
            return True
        time.sleep(0.1)
    return not bridge_is_ready()


def diagnose(target: Optional[Path] = None,
             config_path: Optional[Path] = None) -> HookHealthReport:
    selected = target or default_hooks_path()
    selected_config = config_path or default_codex_config_path()
    report = HookHealthReport()
    report.agent = packaged_agent_from_hooks(selected)
    if report.agent is None:
        report.hook_errors.append("未找到完整的 Codex Buddy 打包版 Hook")
        return report
    try:
        report.hook_errors.extend(verify_executable_hooks(selected, report.agent))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        report.hook_errors.append("无法读取 hooks.json：%s" % error)
        return report
    report.smoke_ok, report.smoke_detail = smoke_test_agent(report.agent)
    report.bridge_ok = bridge_is_ready()
    states = read_hook_states(selected, selected_config)
    report.trusted_count = sum(
        bool(states.get(event, HookState()).trusted_hash) for event in HOOK_EVENTS
    )
    report.enabled_count = sum(
        (event in states and states[event].enabled) for event in HOOK_EVENTS
    )
    report.trust_status = trust_status(selected, selected_config, report.agent, states)
    return report


def report_lines(report: HookHealthReport) -> list[str]:
    lines = [
        "Codex Buddy Hook 检查结果",
        "  Hook 配置：%s" % ("正常" if report.configuration_ok else "异常"),
        "  Hook 自检：%s（%s）" % (
            "通过" if report.smoke_ok else "失败", report.smoke_detail,
        ),
        "  后台状态桥：%s" % ("已就绪" if report.bridge_ok else "未就绪"),
        "  Codex 信任记录：%d/%d" % (report.trusted_count, len(HOOK_EVENTS)),
        "  Codex 启用记录：%d/%d" % (report.enabled_count, len(HOOK_EVENTS)),
    ]
    for error in report.hook_errors:
        lines.append("  错误：" + error)
    if report.trust_status == "confirmed":
        lines.append("  Hook 状态：已信任并启用")
    elif report.trust_status == "disabled":
        lines.append("  Hook 状态：存在已关闭的事件，请在 Codex /hooks 中启用")
    else:
        lines.append("  Hook 状态：等待在 Codex /hooks 中信任全部六个事件")
    return lines


def exit_code(report: HookHealthReport) -> int:
    if report.ready:
        return 0
    if (report.configuration_ok and report.smoke_ok and report.bridge_ok and
            report.trust_status in {"pending", "disabled"}):
        return 2
    return 1
