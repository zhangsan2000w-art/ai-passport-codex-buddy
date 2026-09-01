# Codex Buddy Windows 中文控制器

该工具负责在 Windows 与 Codex Buddy 卡片之间建立加密 BLE 连接。它通过 Codex
官方生命周期 Hook 同步开始、工具执行、审批和完成状态。界面和日志均为中文。

## 环境与启动

- Windows 11
- Python 3.11 或更高版本
- 电脑具备 Bluetooth LE

从仓库根目录执行：

```powershell
py -3.11 -m venv .venv-buddy
.\.venv-buddy\Scripts\python.exe -m pip install -r tools\windows_buddy_controller\requirements.txt
.\.venv-buddy\Scripts\python.exe -m tools.windows_buddy_controller.app
```

若只复制了当前文件夹，也可以执行：

```powershell
python -m pip install -r requirements.txt
python .\app.py
```

## 使用步骤

1. 给 AI Passport 烧录 Codex Buddy 固件并开机。
2. 点击“扫描”，选择 `Codex-*` 设备并点击“连接”。
3. 首次连接若 Windows 显示蓝牙配对确认，点击允许；无需输入配对码。
4. 连接后工具自动同步时间与使用者，并每 10 秒保活。
5. 手动测试空闲、工作中、完成、休眠和授权请求等设备页面。
6. 安装下节的 Codex Hook 并重启 Codex。
7. 保持工具运行，即可接收真实状态和审批请求。

## 首次配对后自动使用

先在控制器里成功连接一次卡片，让工具记住目标设备。随后双击仓库根目录的
`安装后台自动连接.cmd`。以后 Windows 登录后会用 `pythonw.exe` 无窗口启动桥接：

- 卡片开机后自动扫描并重连最后一次选择的 `Codex-*` 设备；
- 自动同步时间、使用者、Codex 状态、审批与完成提醒；
- 不显示控制器窗口，也不需要再点击“扫描/连接”；
- 手动打开控制器时会先让后台桥退出，关闭控制器后自动恢复后台桥；
- `卸载后台自动连接.cmd` 只移除当前用户的自动启动项，不删除固件或配对记录。

后台日志保存在 `%LOCALAPPDATA%\CodexBuddy\background.log`，最多保留三个小文件；
日志会隐藏审批编号和参数。普通蓝牙配对本身不会传送 Codex 事件，因此后台桥仍需在
Windows 上运行，但日常使用不再需要操作它。

## Codex 实时状态与双端审批

从仓库根目录运行：

```powershell
.\.venv-buddy\Scripts\python.exe -m tools.windows_buddy_controller.install_codex_hooks install
```

安装器会合并用户级 `.codex/hooks.json`，不会替换其他 Hook。重启 Codex 并确认 Hook
信任后，控制器会接收以下真实事件：

- `UserPromptSubmit`：开始工作。
- `PreToolUse` / `PostToolUse`：工具执行状态。
- `PermissionRequest`：真实审批请求。
- “授权请求测试”现在也能接收卡片的允许/拒绝结果；选择允许后会立即发送明确的
  “Codex 任务已完成”状态并触发一次本地完成庆祝。每次测试自动生成新的审批编号，
  避免固件把重复编号当成已处理请求而不再显示。
- `Stop` / `SessionEnd`：完成与会话结束。

审批同时显示在电脑控制器与卡片。电脑点击“一次允许/拒绝”，或卡片按 `OK`/`DOWN`；
先提交的一端生效。完整审批编号不会写日志，请求参数只向卡片发送截断后的显示提示。
控制器没有运行时，Hook 会放弃决定，让 Codex 使用原生电脑审批。

实时事件和审批默认通过仓库内的 `.codex-buddy-bridge-v1` 临时队列交换，以兼容
Codex Windows 受限环境；目录已加入 `.gitignore`，不会提交任务或审批数据。原有
`127.0.0.1:17321`（状态）和 `127.0.0.1:17322`（审批）仅保留为旧版兼容后备。
Hook 的稳定字段目前不提供 token 用量，因此实时模式把该字段明确用作本地完成积分：
每完成一个 Codex 回合增加 50000 分，只用于触发卡片现有的完成庆祝，不代表 API token。

## 故障排查

- 扫描不到：确认卡片显示 `Codex Buddy`、BLE 已打开，并关闭占用该设备的其他程序。
- 没有配对窗口：在 Windows 蓝牙设置和卡片设置中分别删除旧绑定，然后重新连接。
- 已连接但无法发送：重新连接并确认 Windows 已保存绑定；固件要求加密、绑定和通知订阅。
- 本地文件桥不可用：确认项目目录可写，并只运行一个控制器实例。
- 本地状态端口不可用：旧版后备端口被占用；关闭另一个控制器实例。
- 本地审批端口不可用：关闭另一个控制器实例，或设置相同的
  `CODEX_BUDDY_APPROVAL_PORT`。

## 测试

```powershell
$env:PYTHONPATH = "tools"
python -m unittest discover -s tools\windows_buddy_controller\tests -v
```
