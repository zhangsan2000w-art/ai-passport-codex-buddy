# Codex Buddy v0.1.4 验证记录

验证日期：2026-09-11

## 本次范围

- 修复 Hook 安装器把“写入 `hooks.json`”误当成实时状态链路已经可用的问题。
- 校验六个 Hook 的唯一性、命令、路径与超时，并执行隔离的 Hook 事件冒烟测试。
- 安装后等待后台桥真正监听，区分程序故障与仍需用户完成的 Codex 信任/启用操作。
- 增加 Windows、macOS、Linux 的独立 Hook 检查入口。
- 保留 v0.1.3 的纯蓝牙固件、授权双音、完成三音和五档音量。

## 自动化与构建结果

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 桌面桥与安装器单元测试 | PASS | 53/53；覆盖六 Hook 合并/校验、信任状态、冒烟失败中止安装、旧后台退出超时 |
| Python 字节码编译 | PASS | `compileall` 返回 0 |
| 固件主机逻辑测试 | PASS | Debug 配置 12/12，包含声音与编排逻辑 |
| ESP-IDF 全新构建 | PASS | ESP-IDF 5.5.3，项目版本 0.1.4，构建目录 `build-firmware-v014h` |
| 固件应用大小 | PASS | `0x135260`；`0x177000` 应用分区剩余 `0x41da0`（18%） |
| 合并固件 | PASS | `Codex-Buddy-v0.1.4-merged.bin` 从 `0x0` 写入，1,331,808 字节，映像校验有效 |
| 声音模块链接 | PASS | 最终链接映射包含 `buddy_sound_logic.c.obj`、`buddy_sound_player.c.obj` 与 `bsp_audio.c.obj` |
| 应用层 Wi-Fi 入口 | PASS | 主应用、桌面桥、安装脚本和发布工作流无 Wi-Fi/LAN 初始化、配网、发现或服务入口 |
| Windows 独立包构建 | PASS | PyInstaller 6.22.2；安装器模块导入自检与打包 Hook 的 JSON 输入到事件写入均通过 |
| macOS 独立包构建 | NOT RUN | 已提供原生 CI 构建配置，本机不能交叉生成 macOS 包 |
| Linux 独立包构建 | NOT RUN | 已提供原生 CI 构建配置，本机未生成 Linux 包 |

ESP-IDF 的非最小化构建会编译其通用 Wi-Fi、网络和配网静态组件，蓝牙射频底层也会
引用共享组件名称。这不等于应用启用了 Wi-Fi；Codex Buddy 主应用没有 Wi-Fi 初始化、
扫描、配网、局域网发现或网络服务调用。

## Hook 安装边界

本次自动化证明：安装器能够保留其他 Hook，生成并复核六个 Codex Buddy Hook；打包后的
Agent 能接收 Hook JSON 并写出唯一、内容正确的本地事件；失败时不会继续宣称安装完成。

Codex 的 Hook 信任属于产品安全边界，安装器没有也不应自动绕过。安装或升级导致命令、
路径或内容变化后，用户仍须完全重启 Codex，在 `/hooks` 中把六个 Hook 确认为
`Trusted` 和 `Active`，然后运行发布包中的“检查 Codex Hook”入口。未完成这一步时，
检查器应返回“需要用户操作”，不能显示“实时状态链路已就绪”。

## 真机与真实用户环境状态

以下项目不能由编译或 Mock 测试代替，本轮未修改开发机的真实 Codex Hook、注册表启动项
或蓝牙配对：

- Windows 安装包在真实用户目录完成安装、升级、`/hooks` 信任和检查：NOT RUN。
- 真实 Codex 的开始、工具、审批、完成和会话结束六类事件：NOT RUN。
- v0.1.4 真机刷写、启动、授权双音、完成三音与五档音量：NOT RUN。
- Windows 蓝牙扫描、配对、连接和卡片审批：NOT RUN。
- macOS/Linux 真实蓝牙与真实卡片连接：NOT RUN。
- 20 次连接/断开循环和 30 分钟稳定性测试：NOT RUN。

## 发布边界

本记录证明源码测试、固件构建、声音链接、Windows 独立打包和隔离 Hook 冒烟测试通过；
不证明真实 Codex 信任流程、真实蓝牙硬件或三个操作系统的真机兼容验收已经完成。
