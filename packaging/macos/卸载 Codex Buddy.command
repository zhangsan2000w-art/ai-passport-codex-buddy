#!/bin/sh
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
AGENT="$SCRIPT_DIR/Codex Buddy.app/Contents/MacOS/CodexBuddyAgent"
if [ ! -x "$AGENT" ]; then
    echo "安装包不完整。"
    exit 1
fi
"$AGENT" uninstall
BUDDY_RESULT=$?
printf "按回车键关闭..."
read -r _buddy_answer
exit "$BUDDY_RESULT"
