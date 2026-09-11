@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
set "PYTHONUTF8=1"
cd /d "%~dp0"
title Codex Buddy Installer

if not exist "CodexBuddyAgent.exe" (
    echo The Windows package is incomplete. Extract the complete ZIP first.
    set "BUDDY_RESULT=1"
    goto finished
)

"CodexBuddyAgent.exe" install
set "BUDDY_RESULT=%ERRORLEVEL%"

:finished
if not defined BUDDY_RESULT set "BUDDY_RESULT=1"
echo.
if "%BUDDY_RESULT%"=="0" (
    echo 安装程序已完成本地校验。
    echo 请完全重启 Codex，输入 /hooks，确认六个 Codex Buddy Hook 均为 Trusted 和 Active。
    echo 完成后运行“检查 Codex Hook.cmd”，只有检查通过才表示实时状态链路可用。
) else (
    echo 安装失败，请保留上方错误信息。
)
echo 按任意键关闭。
pause >nul
exit /b %BUDDY_RESULT%
