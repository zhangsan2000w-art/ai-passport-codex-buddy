#!/bin/sh
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
AGENT="$SCRIPT_DIR/CodexBuddyAgent"

if [ ! -x "$AGENT" ]; then
    echo "The package is incomplete. Extract the complete archive first."
    exit 1
fi

"$AGENT" hook-doctor
BUDDY_RESULT=$?
if [ "$BUDDY_RESULT" -eq 0 ]; then
    echo "Codex realtime status is ready."
elif [ "$BUDDY_RESULT" -eq 2 ]; then
    echo "Hooks are installed. Trust and enable all Codex Buddy hooks in /hooks."
else
    echo "Hook check failed. Run the installer again and keep the output above."
fi
exit "$BUDDY_RESULT"
