@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo [1/4] 检查 Python 3.11...
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo 未找到 Python 3.11。请先安装 Python 3.11，并在安装时启用 py launcher。
    pause
    exit /b 1
)

echo [2/4] 创建本地运行环境...
if not exist ".venv-buddy\Scripts\python.exe" (
    py -3.11 -m venv .venv-buddy
    if errorlevel 1 goto :failed
)

echo [3/4] 安装蓝牙依赖与 Codex Hook...
".venv-buddy\Scripts\python.exe" -m pip install -r tools\windows_buddy_controller\requirements.txt
if errorlevel 1 goto :failed
".venv-buddy\Scripts\python.exe" -m tools.windows_buddy_controller.install_codex_hooks install
if errorlevel 1 goto :failed

echo [4/4] 安装 Windows 后台自动连接...
".venv-buddy\Scripts\python.exe" -m tools.windows_buddy_controller.background_install install
if errorlevel 1 goto :failed

echo.
echo Codex Buddy 已安装。请重新启动 Codex，并完成一次卡片蓝牙配对。
pause
exit /b 0

:failed
echo.
echo 安装未完成，请保留本窗口中的错误信息。
pause
exit /b 1
