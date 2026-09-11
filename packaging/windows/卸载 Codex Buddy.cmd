@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
set "PYTHONUTF8=1"
cd /d "%~dp0"
if not exist "CodexBuddyAgent.exe" (
    echo 安装包不完整，请先完整解压 ZIP。
    pause
    exit /b 1
)
"CodexBuddyAgent.exe" uninstall
set "BUDDY_RESULT=%ERRORLEVEL%"
echo 按任意键关闭。
pause >nul
exit /b %BUDDY_RESULT%
