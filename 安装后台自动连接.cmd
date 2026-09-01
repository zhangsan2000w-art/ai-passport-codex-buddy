@echo off
chcp 65001 >nul
set "BUDDY_ROOT=%~dp0"
if not exist "%BUDDY_ROOT%.venv-buddy\Scripts\python.exe" (
  echo 未找到 Codex Buddy 运行环境，请先完成控制器安装。
  pause
  exit /b 1
)
"%BUDDY_ROOT%.venv-buddy\Scripts\python.exe" "%BUDDY_ROOT%tools\windows_buddy_controller\background_install.py" install
pause
