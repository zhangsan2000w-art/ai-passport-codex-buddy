@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv-buddy\Scripts\python.exe" (
    echo 未找到 Codex Buddy 本地运行环境，无需卸载。
    pause
    exit /b 0
)

".venv-buddy\Scripts\python.exe" -m tools.windows_buddy_controller.background_install uninstall
".venv-buddy\Scripts\python.exe" -m tools.windows_buddy_controller.install_codex_hooks uninstall

echo.
echo Codex Buddy 后台启动项和 Hook 已移除。固件、蓝牙配对和本地运行环境未删除。
pause
