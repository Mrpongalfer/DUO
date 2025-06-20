#!/bin/bash
# Rick's "For God's Sake, Stay Put!" Babysitter Script v1

# Target directory where we WANT Ex-Work to think its "project root" is
TARGET_CWD="$HOME/OmnitidePrimeFoundry"

# Absolute path to the OLD Ex-Work agent script you're using for this bootstrap
# !!! ARCHITECT: YOU MUST VERIFY THIS PATH IS CORRECT !!!
OLD_EXWORK_AGENT_SCRIPT_PATH="/home/pong/Projects/projectsupload/Ricksway/ex_work_agentv2.py"

# Path to the (hopefully correctly edited) Genesis Protocol JSON
# This path is relative to TARGET_CWD because we cd there first
GENESIS_JSON_FILE="tmp_exwork_bootstrap/rick_genesis_protocol_FULLY_BRUTEFORCED.exwork.json"

echo "[RICK_BABYSITTER] Intended CWD for Ex-Work: $TARGET_CWD"
echo "[RICK_BABYSITTER] Path to old Ex-Work agent: $OLD_EXWORK_AGENT_SCRIPT_PATH"
echo "[RICK_BABYSITTER] Path to Genesis JSON (relative to TARGET_CWD): $GENESIS_JSON_FILE"

# Change to the target CWD
cd "$TARGET_CWD" || { echo "[RICK_BABYSITTER_FATAL] Could not cd to $TARGET_CWD. Aborting."; exit 1; }

echo "[RICK_BABYSITTER] Current directory is now: $(pwd)"
echo "[RICK_BABYSITTER] About to pipe '$GENESIS_JSON_FILE' to '$OLD_EXWORK_AGENT_SCRIPT_PATH'..."

if [ ! -f "$GENESIS_JSON_FILE" ]; then
    echo "[RICK_BABYSITTER_FATAL] Genesis JSON file not found at: $(pwd)/$GENESIS_JSON_FILE. Aborting."
    exit 1
fi

if [ ! -f "$OLD_EXWORK_AGENT_SCRIPT_PATH" ]; then
    echo "[RICK_BABYSITTER_FATAL] Old Ex-Work agent script not found at: $OLD_EXWORK_AGENT_SCRIPT_PATH. Aborting."
    exit 1
fi

cat "$GENESIS_JSON_FILE" | python3 "$OLD_EXWORK_AGENT_SCRIPT_PATH"

EXWORK_EXIT_CODE=$?
echo "[RICK_BABYSITTER] Ex-Work agent finished with exit code: $EXWORK_EXIT_CODE"

if [ $EXWORK_EXIT_CODE -ne 0 ]; then
    echo "[RICK_BABYSITTER_FAIL] Ex-Work seems to have failed. Check the damn output above."
else
    echo "[RICK_BABYSITTER_SUCCESS_MAYBE?] Ex-Work exited cleanly. Miracles happen. Verify it actually DID something."
fi

exit $EXWORK_EXIT_CODE
