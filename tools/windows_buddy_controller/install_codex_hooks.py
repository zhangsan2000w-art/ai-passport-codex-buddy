"""Install or remove Codex Buddy lifecycle hooks without replacing other hooks."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Dict, List, Tuple


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


def _groups_for_command(command: str) -> Dict[str, List[Dict[str, object]]]:
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


def build_hook_groups(python_executable: Path,
                      hook_script: Path) -> Dict[str, List[Dict[str, object]]]:
    command = "%s %s" % (_quoted(python_executable.resolve()), _quoted(hook_script.resolve()))
    return _groups_for_command(command)


def build_executable_hook_groups(
        executable: Path) -> Dict[str, List[Dict[str, object]]]:
    return _groups_for_command("%s hook" % _quoted(executable.resolve()))


def _is_buddy_group(group: object) -> bool:
    if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
        return False
    for handler in group["hooks"]:
        if not isinstance(handler, dict):
            continue
        command = str(handler.get("commandWindows") or handler.get("command") or "")
        status = str(handler.get("statusMessage") or "")
        if ("Codex Buddy" in status and
                ("codex_hook.py" in command or "CodexBuddyAgent" in command)):
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


def read_document(target: Path) -> Dict[str, Any]:
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


def buddy_handler_locations(
        document: object) -> Dict[str, Tuple[int, int, Dict[str, object]]]:
    locations: Dict[str, Tuple[int, int, Dict[str, object]]] = {}
    if not isinstance(document, dict) or not isinstance(document.get("hooks"), dict):
        return locations
    hooks = document["hooks"]
    for event in HOOK_EVENTS:
        groups = hooks.get(event)
        if not isinstance(groups, list):
            continue
        for group_index, group in enumerate(groups):
            if not _is_buddy_group(group):
                continue
            handlers = group.get("hooks") if isinstance(group, dict) else None
            if not isinstance(handlers, list):
                continue
            for handler_index, handler in enumerate(handlers):
                if isinstance(handler, dict):
                    locations[event] = (group_index, handler_index, handler)
                    break
            if event in locations:
                break
    return locations


def verify_executable_hooks(target: Path, executable: Path) -> List[str]:
    document = read_document(target)
    expected = build_executable_hook_groups(executable)
    errors: List[str] = []
    hooks = document.get("hooks")
    if not isinstance(hooks, dict):
        return ["hooks.json 缺少 hooks 对象"]
    for event in HOOK_EVENTS:
        groups = hooks.get(event)
        buddy_groups = ([group for group in groups if _is_buddy_group(group)]
                        if isinstance(groups, list) else [])
        if len(buddy_groups) != 1:
            errors.append(f"{event} 应有 1 个 Codex Buddy Hook，实际为 {len(buddy_groups)} 个")
            continue
        if buddy_groups[0] != expected[event][0]:
            errors.append(f"{event} 的 Hook 命令或超时配置不正确")
    return errors


def install(target: Path, python_executable: Path,
            hook_script: Path) -> bool:
    existing = read_document(target)
    document = merge_hooks(
        existing,
        build_hook_groups(python_executable, hook_script),
    )
    changed = document != existing
    if changed:
        _write_document(target, document)
    return changed


def install_executable(target: Path, executable: Path) -> bool:
    existing = read_document(target)
    document = merge_hooks(
        existing,
        build_executable_hook_groups(executable),
    )
    changed = document != existing
    if changed:
        _write_document(target, document)
    return changed


def uninstall(target: Path) -> None:
    existing = read_document(target)
    document = remove_hooks(existing)
    if document != existing:
        _write_document(target, document)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="安装 Codex Buddy 实时状态与双端审批 Hook")
    parser.add_argument("action", choices=("install", "uninstall"), nargs="?", default="install")
    parser.add_argument(
        "--target", type=Path,
        default=Path.home() / ".codex" / "hooks.json",
    )
    args = parser.parse_args(argv)
    script = Path(__file__).with_name("codex_hook.py")
    if args.action == "install":
        changed = install(args.target, Path(sys.executable), script)
        print("Codex Buddy Hook 已安装: %s" % args.target)
        if changed:
            print("Hook 配置已更新。请完全重启 Codex，打开 /hooks，信任并启用全部六个 Hook。")
        else:
            print("Hook 配置没有变化。如状态仍未同步，请在 /hooks 中检查信任与启用状态。")
    else:
        uninstall(args.target)
        print("Codex Buddy Hook 已移除: %s" % args.target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
