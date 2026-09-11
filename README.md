# Codex Buddy 中文提醒器

![Codex Buddy 社区封面](docs/assets/codex-buddy-cover.png)

Codex Buddy 是面向 FoloToy AI Passport 的中文 Codex 桌面提醒器。它把 Codex 的工作、
工具执行、授权和完成状态同步到卡片；需要授权时，可以在卡片或电脑上处理；任务完成后，
卡片会显示动画并播放独立提示音。

- 项目主页：<https://github.com/zhangsan2000w-art/ai-passport-codex-buddy>
- 全部版本：<https://github.com/zhangsan2000w-art/ai-passport-codex-buddy/releases>
- 更新记录：[CHANGELOG.md](CHANGELOG.md)

> Codex Buddy 是社区实验项目，并非 OpenAI 官方硬件产品。项目通过本机状态桥和加密
> BLE 传送事件，不提供公网服务，不需要额外的 OpenAI API Key。当前固件不包含 Wi-Fi
> 配网、局域网发现或联网服务。

## 它能做什么

- 在卡片上显示 Codex 的开始、工具执行、等待授权和任务完成状态。
- 支持电脑与卡片双端审批，同一个请求只接受一次有效决定。
- 连接后自动同步本地时间，并显示卡片自身读取的电量。
- 授权请求播放短促双音，任务完成播放上行三音。
- 音量支持 0%、25%、50%、75%、100% 五档并持久保存。
- 60 秒无按键后自动息屏，按键唤醒时不会顺带触发操作。
- 提供待机、工作、等待、完成和失败状态的 BSOD 像素宠物。
- 支持亮度、音量、蓝牙开关、设备端解除绑定和恢复出厂确认。

![Codex Buddy 真机运行画面](docs/assets/codex-buddy-runtime-capture.png)

更完整的硬件能力与可开发方向见
[`docs/PRODUCT_CAPABILITIES.zh_CN.md`](docs/PRODUCT_CAPABILITIES.zh_CN.md)。该文档描述硬件
本身能做什么，不代表 Codex Buddy 当前已经启用了所有硬件能力。

## 工作方式

```text
Codex → 本地 Hook → 本机状态桥 → 加密 BLE → Codex Buddy
Codex ← 本地 Hook ← 本机状态桥 ← 卡片审批按键
```

卡片不能只靠蓝牙配对直接读取 Codex 状态。每台电脑都需要安装一次对应系统的本地状态
桥，并让状态桥真正连接卡片。系统显示“已配对”只表示两端建立了安全关系，不表示 Codex
状态链路已经接通。

## 下载与系统支持

v0.1.4 是第一个同时提供三个桌面系统安装包的版本，请下载与自己系统对应的 v0.1.4 包：

| 系统 | 发布包 | 下载入口 | 说明 |
| --- | --- | --- | --- |
| Windows 10/11 | `Codex-Buddy-Windows-v0.1.4.zip` | [v0.1.4 Release](https://github.com/zhangsan2000w-art/ai-passport-codex-buddy/releases/tag/v0.1.4) | 本机构建并完成包内自检；v0.1.4 的主要改动都在这一端 |
| macOS | `Codex-Buddy-macOS-v0.1.4.zip` | [v0.1.4 Release](https://github.com/zhangsan2000w-art/ai-passport-codex-buddy/releases/tag/v0.1.4) | 由 GitHub Actions 在 macOS 运行器原生构建；未签名、未公证 |
| Linux 桌面 | `Codex-Buddy-Linux-v0.1.4.tar.gz` | [v0.1.4 Release](https://github.com/zhangsan2000w-art/ai-passport-codex-buddy/releases/tag/v0.1.4) | 由 GitHub Actions 在 Ubuntu 运行器原生构建；是压缩包，不是 `.deb`/`.rpm`/AppImage |

v0.1.3 当时只发布了 Windows 包，没有可用的 macOS/Linux 附件。macOS 和 Linux 用户请直接
使用 v0.1.4；旧版本仍保留在
[Releases 页面](https://github.com/zhangsan2000w-art/ai-passport-codex-buddy/releases)，
但不要把别的版本号的文件改名成 v0.1.4 混用。

### v0.1.4 的范围

v0.1.4 的桌面端变化集中在 Windows 状态桥，并首次把 macOS 和 Linux 安装包一起交付：

- Windows 安装器校验六个 Codex 生命周期 Hook 的命令、路径、超时和唯一性。
- 在隔离目录执行一次真实的 Hook 输入、程序运行和事件写入测试。
- 等待后台桥真正开始监听，不把“启动命令已发送”当成成功。
- 三个系统都增加独立的 Hook 检查入口，不绕过 Codex 的 Hook 信任和启用确认。
- 安装进程固定控制台输出编码，避免中文提示在非中文 Windows 代码页下中断安装。
- macOS/Linux 安装包由 `.github/workflows/build-desktop-bridges.yml` 在对应系统的
  GitHub 托管运行器上原生构建，并执行包内自检。

macOS/Linux 安装包已完成构建与包内自检，但还没有在真实电脑上完成安装、蓝牙连接和卡片
兼容性验收，详见“当前验证状态”。

### Release 附件分别是什么

- `Codex-Buddy-版本号-merged.bin`：刷入 AI Passport 卡片的完整固件，从地址 `0x0`
  写入。它不能代替电脑端状态桥。
- `Codex-Buddy-Windows-版本号.zip`：Windows 电脑端安装包，包含控制器、后台状态桥、
  Hook 安装与检查程序以及独立运行环境。使用前必须完整解压。
- `Codex-Buddy-macOS-版本号.zip`：macOS 电脑端安装包，包含 `Codex Buddy.app` 和四个
  `.command` 脚本。未签名、未公证，首次打开需要手动放行。使用前必须完整解压。
- `Codex-Buddy-Linux-版本号.tar.gz`：Linux 桌面端安装包，包含控制器、后台状态桥和四
  个 `.sh` 脚本。它是压缩包，不是 `.deb`/`.rpm`/AppImage。
- `Codex-Buddy-版本号-source.zip`：供开发者阅读、修改和重新构建的源码快照，普通用户
  安装时不需要。
- `SHA256SUMS.txt`：发布文件的 SHA-256 校验清单，用于确认下载完整且版本没有混淆。

普通用户通常需要卡片固件、自己系统的安装包和校验清单；不修改源码就不需要下载源码包。

## 快速开始

### 1. 下载同一版本的文件

从 [v0.1.4 Release](https://github.com/zhangsan2000w-art/ai-passport-codex-buddy/releases/tag/v0.1.4)
下载自己系统的三个文件，全部保持 v0.1.4：

```text
Windows：Codex-Buddy-v0.1.4-merged.bin、Codex-Buddy-Windows-v0.1.4.zip、SHA256SUMS.txt
macOS：  Codex-Buddy-v0.1.4-merged.bin、Codex-Buddy-macOS-v0.1.4.zip、SHA256SUMS.txt
Linux：  Codex-Buddy-v0.1.4-merged.bin、Codex-Buddy-Linux-v0.1.4.tar.gz、SHA256SUMS.txt
```

不要混用不同版本号的固件、状态桥和脚本。

### 2. 刷入卡片固件

使用 FoloToy Web Flasher 或其他兼容工具，把对应版本的合并固件从地址 `0x0` 写入卡片。
完整重刷后，建议同时删除电脑中的旧蓝牙配对，再重新配对和连接。

### 3. 安装电脑端状态桥

完整解压自己系统的安装包，然后运行对应的安装入口：

| 系统 | 安装入口 | 日常重新连接入口 |
| --- | --- | --- |
| Windows | 双击 `安装 Codex Buddy.cmd` | `打开 Codex Buddy 控制器.cmd` |
| macOS | 双击 `安装 Codex Buddy.command` | `打开 Codex Buddy 控制器.command` |
| Linux 桌面 | `./install-codex-buddy.sh` | `./open-codex-buddy.sh` |

安装器会复制独立运行程序、验证六个 Hook、合并 Codex Buddy Hook、注册当前用户的后台
自启动项，等待后台桥就绪后打开控制器。它只管理 Codex Buddy 自己的 Hook，不应删除用户
已有的其他 Hook。

macOS 首次运行可能被系统拦截，需要在“系统设置 → 隐私与安全性”中允许打开，并允许蓝牙
权限。Linux 需要桌面会话、BlueZ 和可用的蓝牙适配器；首次运行脚本前可能需要
`chmod +x *.sh`。

### 4. 连接卡片

1. 打开 Codex Buddy 控制器。
2. 点击“扫描”。
3. 选择自己的 `Codex-*` 设备并点击“连接”。
4. 电脑第一次弹出蓝牙确认时允许配对，不需要输入六位数字。
5. 等待控制器显示已连接；时间、使用者和设备状态会自动同步。

### 5. 确认 Codex Hook 已信任并启用

1. 完全退出并重新打开 Codex。
2. 进入任意一个 Codex 任务。
3. 点击任务页面底部的输入框。
4. 输入下面的命令，然后按回车：

   ```text
   /hooks
   ```

5. Codex 会打开 Hook 管理列表。找到六个 Codex Buddy Hook，确认每一个都同时显示：

   ```text
   Trusted
   Active
   ```

6. 回到解压后的安装包，运行 Hook 检查入口：

   ```text
   Windows：检查 Codex Hook.cmd
   macOS：  检查 Codex Hook.command
   Linux：  ./check-codex-hook.sh
   ```

7. 只有检查结果显示“实时状态链路已就绪”，才算状态桥安装完成。

`/hooks` 是在 Codex 的任务输入框中输入，不是在 PowerShell、Windows 设置或浏览器中
输入。

### 6. 验证完整链路

在 Codex 中发送一个任务，依次确认：

1. 卡片进入工作状态。
2. 工具执行状态能够更新。
3. 出现授权请求时，卡片播放授权双音并可以允许或拒绝。
4. 任务完成后，卡片显示完成状态并播放上行三音。

## 日常使用

| 场景 | 用户要做什么 | 是否打开控制器 |
| --- | --- | --- |
| 第一次使用 | 刷入固件、安装状态桥、扫描并连接卡片 | 需要 |
| 卡片保持开机 | 正常使用 Codex，后台桥继续运行 | 通常不需要 |
| 只重启 Codex | 重新打开 Codex；v0.1.4 用户重新确认 Hook 状态 | 通常不需要 |
| 卡片关机再开机 | 打开控制器，重新选择卡片并连接一次 | 需要 |
| 完整重刷固件 | 删除电脑中的旧配对，再重新配对和连接 | 需要 |
| 换电脑 | 在新电脑安装状态桥，再配对和连接卡片 | 第一次需要 |
| 电脑只显示“已配对” | 继续在控制器内点击连接 | 需要 |

连接成功后，时间和电量会自动更新，不需要手动同步。

## 卡片操作

### 声音设置

长按确定键打开菜单，进入“设置”，选中“声音”，按确定键在五档音量间切换：

```text
0% → 25% → 50% → 75% → 100% → 0%
```

授权音是短促双音，完成音是上行三音。0% 为静音，调整后的音量会立即保存。

### 按键

- 上键：切换主页、宠物和信息页；待确认页面用于滚动。
- 下键：切换子页面；待确认页面用于拒绝。
- 确定键：确认当前操作；待确认页面用于单次允许。
- 长按确定键：打开或关闭菜单。
- 屏幕关闭时：任意功能键的短按或长按均只唤醒屏幕。

## 常见问题

### 系统显示已配对，但卡片没有 Codex 状态

蓝牙配对不等于状态桥已经连接。打开控制器，选择自己的 `Codex-*` 设备并点击“连接”，
等待控制器明确显示已连接。

### 重刷后能够扫描，但连接超时

电脑和卡片可能保留了不同的旧绑定密钥：

1. 在卡片进入“设置 → 重置 → 取消配对”。
2. 在电脑蓝牙设置中删除对应的 `Codex-*`。
3. 重新扫描、配对并连接。

### 控制器能连接，但 Codex 状态不更新

先按照“确认 Codex Hook 已信任并启用”完成 Codex 内的信任与启用，再运行安装包里的 Hook
检查入口（Windows 为 `检查 Codex Hook.cmd`，macOS 为 `检查 Codex Hook.command`，
Linux 为 `check-codex-hook.sh`）。控制器能够手动连接卡片，不代表 Codex Hook 已经工作。

### 卡片没有声音

进入“设置 → 声音”，确认音量不是 0%。授权和完成使用不同提示音；若只有其中一种不响，
应分别测试授权请求与任务完成事件。

## 版本迭代

| 版本 | 主要变化 |
| --- | --- |
| v0.1.0 | 中文界面、基础状态显示、Codex 工作与授权链路 |
| v0.1.1 | 修复提示音，加入授权双音、完成三音和五档音量 |
| v0.1.2 | 连接后自动同步时间、电量和设备状态 |
| v0.1.3 | 固件回到纯蓝牙并保留完整声音；该版本只发布了 Windows 安装包 |
| v0.1.4 | 优化 Windows 状态桥，补齐 Hook 配置、自检、信任提示和后台桥就绪检查；首次同时发布 Windows、macOS、Linux 安装包 |

详细变更见 [CHANGELOG.md](CHANGELOG.md)。历史发布文件保留在
[Releases 页面](https://github.com/zhangsan2000w-art/ai-passport-codex-buddy/releases)。

## 当前验证状态

v0.1.4 已完成以下自动化和构建检查：

- Python 桌面桥与安装器测试 53/53，在 Windows、macOS、Linux 三种运行器上各执行一遍。
- 固件主机 Debug 测试 12/12。
- ESP-IDF 5.5.3 全量构建和合并固件校验。
- 声音模块最终链接检查。
- Windows 独立包自检和隔离 Hook 冒烟测试。
- macOS/Linux 安装包由 GitHub Actions 原生构建并通过包内自检
  （运行记录：[actions/runs/34572132643](https://github.com/zhangsan2000w-art/ai-passport-codex-buddy/actions/runs/34572132643)）。

完整证据见
[`docs/validation/2026-09-11-codex-buddy-v0.1.4.md`](docs/validation/2026-09-11-codex-buddy-v0.1.4.md)。

以下项目不能由编译或 Mock 测试代替，本轮仍为 `NOT RUN`：

- v0.1.4 在真实用户目录中的 Windows 安装、升级和 Hook 信任流程。
- 真实 Codex 六类生命周期事件。
- v0.1.4 真机刷写、声音、蓝牙连接和卡片审批。
- macOS/Linux 安装包在真实电脑上的解压、安装、蓝牙连接和卡片审批兼容性。
- macOS 安装包未签名、未公证，未验证 Gatekeeper 放行后的完整流程。
- 20 次连接/断开循环和 30 分钟稳定性测试。

因此本项目仍是社区开发预览版，不应描述为已经完成全平台、全硬件环境验证的量产固件。

## 从源码运行桌面桥

发布包用户不需要 Python。只有开发或修改源码时才需要 Python 3.11：

```powershell
py -3.11 -m venv .venv-buddy
.\.venv-buddy\Scripts\python.exe -m pip install -r tools\windows_buddy_controller\requirements.txt
$env:PYTHONPATH = "tools"
.\.venv-buddy\Scripts\python.exe -m windows_buddy_controller.app
```

## 编译固件

使用 ESP-IDF 5.5.3，并设置目标为 ESP32-C3：

```powershell
idf.py set-target esp32c3
idf.py build
python -m esptool --chip esp32c3 merge_bin -o build\merged-binary.bin -f raw `
  --flash_mode dio --flash_freq 80m --flash_size 4MB `
  0x0 build\bootloader\bootloader.bin `
  0x8000 build\partition_table\partition-table.bin `
  0x10000 build\Codex-Buddy.bin
```

网页刷机使用合并后的 BIN，并从 `0x0` 写入。

## 测试

```powershell
$env:PYTHONPATH = "tools"
python -m unittest discover -s tools\windows_buddy_controller\tests -v

cmake -S tests -B build-host
cmake --build build-host
ctest --test-dir build-host -C Debug --output-on-failure
idf.py build
```

## 目录

```text
components/bsp/                    FoloToy AI Passport 板级驱动
main/                              Codex Buddy 固件、状态、BLE、声音和中文 UI
tests/                             主机端 C 测试
tools/windows_buddy_controller/    桌面控制器、本地状态桥和打包入口
packaging/                         各系统安装、打开、检查和卸载脚本
.github/workflows/                 自动化测试与原生打包流程
docs/                              硬件能力说明和验证记录
```

本项目采用 [`MIT License`](LICENSE)。协议来源与上游许可证归属见 [`NOTICE`](NOTICE)。
