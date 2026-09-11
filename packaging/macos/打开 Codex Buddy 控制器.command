#!/bin/sh
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CONTROLLER="$SCRIPT_DIR/Codex Buddy.app/Contents/MacOS/CodexBuddyAgent"
if [ ! -x "$CONTROLLER" ]; then
    echo "安装包不完整。请先解压完整 ZIP。"
    exit 1
fi
"$CONTROLLER" >/dev/null 2>&1 &
