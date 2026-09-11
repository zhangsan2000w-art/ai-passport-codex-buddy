@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
if not exist "CodexBuddyController.exe" (
    echo 安装包不完整，请先完整解压 ZIP。
    pause
    exit /b 1
)
start "" "CodexBuddyController.exe"
