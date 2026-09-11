#!/bin/sh
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CONTROLLER="$SCRIPT_DIR/CodexBuddyController"
if [ ! -x "$CONTROLLER" ]; then
    echo "The package is incomplete. Extract the complete archive first."
    exit 1
fi
"$CONTROLLER" >/dev/null 2>&1 &
