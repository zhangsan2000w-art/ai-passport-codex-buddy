"""Install or remove Codex Buddy lifecycle hooks without replacing other hooks."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Dict, List


HOOK_EVENTS = (
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "PermissionRequest",
    "Stop",
    "SessionEnd",
)


def _quoted(path: Path) -> str:
    return '"%s"' % str(path)


def build_hook_groups(python_executable: Path,
                      hook_script: Path) -> Dict[str, List[Dict[str, object]]]:
    command = "%s %s" % (_quoted(python_executable.resolve()), _quoted(hook_script.resolve()))
    # Codex Desktop uses the configured PowerShell on Windows. A command that
    # begins with a quoted executable path is parsed as a string expression;
    # the call operator is required to execute it and preserve Hook stdin.
    windows_command = "& " + command

    def group(status: str, timeout: int = 10) -> Dict[str, object]:
        return {
            "hooks": [{
                "type": "command",
                "command": command,
                "commandWindows": windows_command,
                "timeout": timeout,
                "statusMessage": status,
            }]
        }

    return {
        "UserPromptSubmit": [group("同步 Codex Buddy 工作状态")],
        "PreToolUse": [group("同步 Codex Buddy 工具状态")],
        "PostToolUse": [group("同步 Codex Buddy 工具结果")],
        "PermissionRequest": [group("等待电脑或 Codex Buddy 审批", 600)],
        "Stop": [group("同步 Codex Buddy 完成状态")],
        "SessionEnd": [group("关闭 Codex Buddy 会话状态", 3)],
    }


def _is_buddy_group(group: object) -> bool:
    if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
        return False
    for handler in group["hooks"]:
        if not isinstance(handler, dict):
            continue
        command = str(handler.get("commandWindows") or handler.get("command") or "")
        status = str(handler.get("statusMessage") or "")
        if "codex_hook.py" in command and "Codex Buddy" in status:
            return True
    return False


def merge_hooks(existing: object,
                additions: Dict[str, List[Dict[str, object]]]) -> Dict[str, Any]:
    document: Dict[str, Any] = deepcopy(existing) if isinstance(existing, dict) else {}
    hooks = document.get("hooks")
    if not isinstance(hooks, dict):
        hooks = {}
        document["hooks"] = hooks
    for event in HOOK_EVENTS:
        groups = hooks.get(event)
        if not isinstance(groups, list):
            groups = []
        groups = [group for group in groups if not _is_buddy_group(group)]
        groups.extend(deepcopy(additions[event]))
        hooks[event] = groups
    return document


def remove_hooks(existing: object) -> Dict[str, Any]:
    document: Dict[str, Any] = deepcopy(existing) if isinstance(existing, dict) else {}
    hooks = document.get("hooks")
    if not isinstance(hooks, dict):
        return document
    for event in list(hooks):
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        kept = [group for group in groups if not _is_buddy_group(group)]
        if kept:
            hooks[event] = kept
        else:
            hooks.pop(event, None)
    return document


def _read_document(target: Path) -> Dict[str, Any]:
    if not target.exists():
        return {}
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("hooks.json 顶层必须是 JSON 对象")
    return payload


def _write_document(target: Path, document: Dict[str, Any]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = target.with_name(target.name + ".codex-buddy-" + stamp + ".bak")
        shutil.copy2(target, backup)
    temporary = target.with_name(target.name + ".codex-buddy.tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)


def install(target: Path, python_executable: Path,
            hook_script: Path) -> None:
    document = merge_hooks(
        _read_document(target),
        build_hook_groups(python_executable, hook_script),
    )
    _write_document(target, document)


def uninstall(target: Path) -> None:
    _write_document(target, remove_hooks(_read_document(target)))


def main() -> int:
    parser = argparse.ArgumentParser(description="安装 Codex Buddy 实时状态与双端审批 Hook")
    parser.add_argument("action", choices=("install", "uninstall"), nargs="?", default="install")
    parser.add_argument(
        "--target", type=Path,
        default=Path.home() / ".codex" / "hooks.json",
    )
    args = parser.parse_args()
    script = Path(__file__).with_name("codex_hook.py")
    if args.action == "install":
        install(args.target, Path(sys.executable), script)
        print("Codex Buddy Hook 已安装: %s" % args.target)
        print("请在 Codex CLI 中打开 /hooks，信任更新后的 Hook，再完全重启 Codex Desktop。")
    else:
        uninstall(args.target)
        print("Codex Buddy Hook 已移除: %s" % args.target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
