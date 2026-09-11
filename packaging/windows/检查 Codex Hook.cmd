@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul
set "PYTHONUTF8=1"
cd /d "%~dp0"
title Codex Buddy Hook Check

if not exist "CodexBuddyAgent.exe" (
    echo 安装包不完整，请先完整解压 ZIP。
    set "BUDDY_RESULT=1"
    goto finished
)

"CodexBuddyAgent.exe" hook-doctor
set "BUDDY_RESULT=%ERRORLEVEL%"

:finished
if not defined BUDDY_RESULT set "BUDDY_RESULT=1"
echo.
if "%BUDDY_RESULT%"=="0" (
    echo 检查完成：Codex 实时状态链路已就绪。
) else if "%BUDDY_RESULT%"=="2" (
    echo Hook 文件已经安装，但仍需在 Codex 的 /hooks 页面完成信任或启用。
) else (
    echo 检查失败，请重新运行“安装 Codex Buddy.cmd”，并保留上方错误信息。
)
echo 按任意键关闭。
pause >nul
exit /b %BUDDY_RESULT%
