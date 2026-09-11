# Codex Buddy 桌面状态桥

这个目录保留早期的 `windows_buddy_controller` 包名，但 v0.1.4 的桌面端代码同时面向
Windows、macOS 和 Linux。当前传输方式只有加密蓝牙，不包含 Wi-Fi 或局域网桥。

## 普通用户

普通用户应下载自己系统的 v0.1.4 发布包，完整解压后运行安装入口：

| 系统 | 安装入口 | 打开控制器 | 卸载入口 |
| --- | --- | --- | --- |
| Windows | `安装 Codex Buddy.cmd` | `打开 Codex Buddy 控制器.cmd` | `卸载 Codex Buddy.cmd` |
| macOS | `安装 Codex Buddy.command` | `打开 Codex Buddy 控制器.command` | `卸载 Codex Buddy.command` |
| Linux | `install-codex-buddy.sh` | `open-codex-buddy.sh` | `uninstall-codex-buddy.sh` |

安装后完全重启 Codex，在 `/hooks` 中信任并启用六个 Codex Buddy Hook，再运行对应平台
的检查入口：Windows `检查 Codex Hook.cmd`、macOS `检查 Codex Hook.command`、Linux
`check-codex-hook.sh`。检查器会区分“文件已安装”和“实时状态链路已就绪”。

发布包内含独立运行时，不要求电脑预装 Python、Node.js 或 TRAE。安装后第一次必须打开
控制器，扫描并连接 `Codex-*`。系统蓝牙显示“已配对”不等于状态桥已经连接。

卡片保持开机时，控制器窗口可以关闭，由后台桥继续同步。卡片关机再开机后，按当前
真机行为需要重新打开控制器、选择设备并连接一次。每次完整刷机后，应在电脑蓝牙设置
中删除旧的 `Codex-*` 配对，再重新配对。

## 开发者源码模式

源码模式需要 Python 3.11：

```powershell
py -3.11 -m venv .venv-buddy
.\.venv-buddy\Scripts\python.exe -m pip install -r tools\windows_buddy_controller\requirements.txt
$env:PYTHONPATH = "tools"
.\.venv-buddy\Scripts\python.exe -m windows_buddy_controller.app
```

不要在仓库子目录中使用 `-m tools.windows_buddy_controller.app`；包搜索路径不一致时会
出现 `No module named 'tools'`。在仓库根目录使用上面的 `PYTHONPATH=tools` 方式即可。

## 运行链路

```text
Codex Hook → 文件/本地通知桥 → 桌面后台进程 → Bleak → 加密 BLE → 卡片
卡片审批 → 加密 BLE → 桌面后台进程 → Codex PermissionRequest Hook
```

状态桥不调用额外 OpenAI API，不需要 API Key。固件只负责显示、按键和蓝牙收发；
桌面桥负责把本机 Codex 事件变成卡片协议，所以每台电脑都要安装一次。

## 后台启动

- Windows：当前用户 `HKCU Run`。
- macOS：当前用户 `~/Library/LaunchAgents/cn.codexbuddy.bridge.plist`。
- Linux：当前用户 XDG autostart 文件。

安装器会先通知已运行的后台桥退出。v0.1.4 同时向当前控制端口和 v0.1.2 的旧端口发送
停止消息，用于修复升级后控制器提示“后台桥仍在退出”的问题。

## 打包

```powershell
python -m pip install -r tools\windows_buddy_controller\requirements.txt `
  -r tools\windows_buddy_controller\requirements-build.txt
python -m PyInstaller --noconfirm --clean `
  --distpath desktop-dist --workpath desktop-build `
  tools\windows_buddy_controller\CodexBuddyDesktop.spec
```

PyInstaller 不能在 Windows 上交叉生成 macOS/Linux 可执行文件。本仓库的 GitHub Actions
会分别在三个系统原生构建。Windows 包可在本机验证；macOS/Linux 未用真实卡片测试前
应标记 `NOT RUN`。

## 测试

```powershell
$env:PYTHONPATH = "tools"
python -m unittest discover -s tools\windows_buddy_controller\tests -v
python -m compileall -q tools\windows_buddy_controller
```

测试覆盖协议、Hook 合并、六事件完整性、隔离冒烟测试、信任/启用状态识别、设置保存、
单实例、v0.1.2 旧后台退出兼容、跨平台路径和自动启动文件生成。真实蓝牙扫描、配对、
通知和卡片审批仍需在每个平台用真机验证。
