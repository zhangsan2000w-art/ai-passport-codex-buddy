#!/bin/sh
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
AGENT="$SCRIPT_DIR/CodexBuddyAgent"

if [ ! -x "$AGENT" ]; then
    echo "The package is incomplete. Extract the complete archive first."
    exit 1
fi

"$AGENT" install
BUDDY_RESULT=$?
if [ "$BUDDY_RESULT" -eq 0 ]; then
    echo "Local installation checks passed."
    echo "Restart Codex, then trust and enable all six Codex Buddy hooks in /hooks."
    echo "Run check-codex-hook.sh afterwards; only a passing check means realtime status is ready."
else
    echo "Installation failed. Keep the error output above."
fi
exit "$BUDDY_RESULT"
