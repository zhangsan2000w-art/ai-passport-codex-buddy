#!/bin/sh
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
AGENT="$SCRIPT_DIR/Codex Buddy.app/Contents/MacOS/CodexBuddyAgent"

if [ ! -x "$AGENT" ]; then
    echo "安装包不完整，请先完整解压 ZIP。"
    printf "按回车键关闭..."
    read -r _buddy_answer
    exit 1
fi

"$AGENT" hook-doctor
BUDDY_RESULT=$?
echo
if [ "$BUDDY_RESULT" -eq 0 ]; then
    echo "检查完成，Codex 实时状态链路已就绪。"
elif [ "$BUDDY_RESULT" -eq 2 ]; then
    echo "Hook 文件已经安装，但仍需在 Codex 的 /hooks 页面完成信任或启用。"
else
    echo "检查失败，请重新运行安装程序，并保留上方错误信息。"
fi
printf "按回车键关闭..."
read -r _buddy_answer
exit "$BUDDY_RESULT"
