@echo off
cd /d "%~dp0"

if not exist ".venv-buddy\Scripts\pythonw.exe" (
    echo Codex Buddy controller environment was not found.
    echo Please run the dependency setup first.
    pause
    exit /b 1
)

start "" ".venv-buddy\Scripts\pythonw.exe" -m tools.windows_buddy_controller.app
