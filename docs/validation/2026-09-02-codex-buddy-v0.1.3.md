# Codex Buddy v0.1.3 验证记录

验证日期：2026-09-02

## 本次范围

- 回退 Wi-Fi/LAN 实验，固件产品功能只保留加密 BLE。
- 保留授权双音、完成三音和五档音量。
- 增加 Windows、macOS、Linux 独立桌面桥打包入口。
- 修复新控制器不能停止 v0.1.2 旧后台桥的问题。

## 自动化与构建结果

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 桌面桥单元测试 | PASS | 46/46 |
| Python 字节码编译 | PASS | `compileall` 返回 0 |
| 固件主机逻辑测试 | PASS | 12/12，包含声音触发逻辑 |
| ESP-IDF 全新构建 | PASS | ESP-IDF 5.5.3，项目版本 0.1.3 |
| 固件应用大小 | PASS | `0x135260`，1,500 KiB 应用分区剩余 18% |
| 合并固件 | PASS | `Codex-Buddy-v0.1.3-merged.bin`，从 `0x0` 写入，大小 1,331,808 字节 |
| 声音模块链接 | PASS | 链接映射包含 `buddy_sound_logic.c.obj`、`buddy_sound_player.c.obj` 和声音队列函数 |
| 应用层 Wi-Fi 入口 | PASS | 主应用源文件及对象清单无 Wi-Fi 模块；没有 Wi-Fi 初始化、启动或连接调用 |
| Windows 独立包构建 | PASS | PyInstaller 6.22.2，Agent 自检通过 |
| macOS 独立包构建 | NOT RUN | 已提供原生 CI 构建配置，本机不能交叉生成 macOS 包 |
| Linux 独立包构建 | NOT RUN | 已提供原生 CI 构建配置，本机未生成 Linux 包 |

ESP-IDF 的完整构建过程会编译其组件仓库中的通用静态库，蓝牙射频共享底层也保留
`esp_wifi_bt_power_domain_*` 名称；Codex Buddy 主应用没有 Wi-Fi 功能入口，不会配网、
扫描网络或建立局域网连接。

## 真机状态

此前 v0.1.2 的蓝牙、审批、完成提醒、声音和时间/电量同步已由用户在真机验证。
v0.1.3 重新生成了固件，因此下列发布验收仍应针对 v0.1.3 再执行，不能用编译结果代替：

- v0.1.3 真机刷写与启动：NOT RUN。
- 授权双音、完成三音和五档音量：NOT RUN。
- Windows 蓝牙扫描、配对、连接和卡片审批：NOT RUN。
- Windows 安装器升级 v0.1.2 后台桥：NOT RUN。
- macOS/Linux 真实蓝牙与真实卡片连接：NOT RUN。
- 20 次连接/断开循环和 30 分钟稳定性测试：NOT RUN。

## 发布边界

本记录证明源码测试、固件构建、声音链接和 Windows 独立打包通过；不证明三个操作系统
均已完成真机兼容验收。正式发布时应把未运行项如实标注。
