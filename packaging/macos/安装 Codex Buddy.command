#!/bin/sh
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
AGENT="$SCRIPT_DIR/Codex Buddy.app/Contents/MacOS/CodexBuddyAgent"

if [ ! -x "$AGENT" ]; then
    echo "安装包不完整。请先解压完整 ZIP，再从解压后的目录运行。"
    printf "按回车键关闭..."
    read -r _buddy_answer
    exit 1
fi

"$AGENT" install
BUDDY_RESULT=$?
echo
if [ "$BUDDY_RESULT" -eq 0 ]; then
    echo "安装程序已完成本地校验。"
    echo "请完全重启 Codex，在 /hooks 中确认六个 Codex Buddy Hook 均已信任并启用。"
    echo "完成后运行“检查 Codex Hook.command”，只有检查通过才表示实时状态链路可用。"
else
    echo "安装失败。请保留上面的错误信息。"
fi
printf "按回车键关闭..."
read -r _buddy_answer
exit "$BUDDY_RESULT"
