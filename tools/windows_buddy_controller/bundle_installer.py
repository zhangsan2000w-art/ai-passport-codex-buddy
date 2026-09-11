"""Install a self-contained desktop bundle into the current user profile."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from . import background_install, hook_health, install_codex_hooks
from .instance_guard import request_background_stop
from .platform_paths import executable_name, platform_id, product_data_dir


PRODUCT_VERSION = "0.1.4"
MACOS_APP_NAME = "Codex Buddy.app"


def agent_name() -> str:
    return executable_name("CodexBuddyAgent")


def controller_name() -> str:
    return executable_name("CodexBuddyController")


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundle_dir() -> Path:
    executable = Path(sys.executable).resolve()
    if platform_id() == "macos":
        for parent in executable.parents:
            if parent.name.endswith(".app"):
                return parent.parent
    return executable.parent


def agent_path(directory: Path) -> Path:
    if platform_id() == "macos":
        return (directory / MACOS_APP_NAME / "Contents" / "MacOS" /
                "CodexBuddyAgent")
    return directory / agent_name()


def controller_path(directory: Path) -> Path:
    if platform_id() == "macos":
        return agent_path(directory)
    return directory / controller_name()


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:12]


def install_dir(source: Path | None = None) -> Path:
    selected = source or bundle_dir()
    agent = agent_path(selected)
    suffix = _file_digest(agent) if agent.is_file() else "source"
    return product_data_dir() / f"App-{PRODUCT_VERSION}-{suffix}"


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve()))


def _copy_bundle(source: Path, target: Path) -> bool:
    if target.is_dir() and agent_path(target).is_file():
        return True
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target, dirs_exist_ok=True, symlinks=True)
    except OSError as error:
        print(f"无法复制 Codex Buddy 到用户目录：{error}")
        return False
    return agent_path(target).is_file() and controller_path(target).is_file()


def _launch_controller(directory: Path) -> bool:
    controller = controller_path(directory)
    if not controller.is_file():
        return False
    options: dict[str, object] = {}
    if platform_id() == "windows":
        options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        options["start_new_session"] = True
    try:
        subprocess.Popen(
            [str(controller)], cwd=directory, stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            close_fds=True, **options,
        )
    except OSError:
        return False
    return True


def install_final() -> int:
    directory = bundle_dir()
    agent = agent_path(directory)
    if not is_frozen() or not agent.is_file():
        print("请从完整的 Codex Buddy 桌面免 Python 安装包运行。")
        return 1
    target = Path.home() / ".codex" / "hooks.json"
    config_path = Path.home() / ".codex" / "config.toml"
    try:
        previous_states = hook_health.read_hook_states(target, config_path)
        hook_changed = install_codex_hooks.install_executable(target, agent)
        hook_errors = install_codex_hooks.verify_executable_hooks(target, agent)
        hook_health.write_install_receipt(
            target, agent, hook_changed, previous_states,
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Codex Hook 安装失败：{error}")
        return 1
    if hook_errors:
        print("Codex Hook 安装校验失败：")
        for error in hook_errors:
            print("  - " + error)
        return 1
    smoke_ok, smoke_detail = hook_health.smoke_test_agent(agent)
    if not smoke_ok:
        print("Codex Hook 自检失败：" + smoke_detail)
        return 1
    print("Codex Hook 自检通过：" + smoke_detail)
    if not background_install.install():
        print("后台状态桥启动失败。请查看系统安全设置是否拦截。")
        return 1
    if not hook_health.wait_for_bridge():
        print("后台状态桥未能在 8 秒内就绪。")
        return 1
    if not _launch_controller(directory):
        print("控制器启动失败。请保留当前窗口并重新运行安装程序。")
        return 1
    report = hook_health.diagnose(target, config_path)
    for line in hook_health.report_lines(report):
        print(line)
    print("Codex Buddy v0.1.4 已安装并打开控制器。")
    print("首次请在控制器中扫描并通过蓝牙连接卡片。")
    if hook_changed or report.trust_status != "confirmed":
        print("实时状态同步尚未完成：请完全重启 Codex，输入 /hooks，")
        print("确认 Codex Buddy 的六个 Hook 均为 Trusted 且 Active。")
        print("确认后可运行“检查 Codex Hook”再次验证。")
    else:
        print("Hook 已信任并启用，可以同步 Codex 实时状态。")
    return 0


def install() -> int:
    if not is_frozen():
        print("当前是源码运行方式；免 Python 安装请使用对应系统的发布包。")
        return 1
    source = bundle_dir()
    target = install_dir(source)
    if _same_path(source, target):
        return install_final()
    request_background_stop()
    if not hook_health.wait_for_bridge_stopped():
        print("旧后台桥未能在 8 秒内退出。请关闭控制器后重新运行安装程序。")
        return 1
    if not _copy_bundle(source, target):
        return 1
    installed_agent = agent_path(target)
    result = subprocess.run(
        [str(installed_agent), "install-final"], cwd=target,
        check=False,
    )
    return result.returncode


def uninstall() -> int:
    try:
        background_install.uninstall()
        install_codex_hooks.uninstall(Path.home() / ".codex" / "hooks.json")
    except (OSError, ValueError) as error:
        print(f"卸载失败：{error}")
        return 1
    print("Codex Buddy Hook 和后台启动项已移除。")
    print("卡片固件、蓝牙配对和本地程序文件未删除。")
    return 0


def doctor() -> int:
    report = hook_health.diagnose()
    for line in hook_health.report_lines(report):
        print(line)
    if report.ready:
        print("检查通过：Codex 实时状态链路已就绪。")
    elif report.trust_status in {"pending", "disabled"}:
        print("请完全重启 Codex，输入 /hooks，信任并启用全部六个 Codex Buddy Hook。")
    else:
        print("检查未通过：请重新运行 Codex Buddy 安装程序进行修复。")
    return hook_health.exit_code(report)
