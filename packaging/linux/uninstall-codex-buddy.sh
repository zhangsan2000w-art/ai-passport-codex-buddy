#!/bin/sh
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
AGENT="$SCRIPT_DIR/CodexBuddyAgent"
if [ ! -x "$AGENT" ]; then
    echo "The package is incomplete."
    exit 1
fi
"$AGENT" uninstall
