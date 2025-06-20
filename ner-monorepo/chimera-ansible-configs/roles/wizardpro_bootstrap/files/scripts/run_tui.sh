#!/bin/bash
# Runs the WizardPro TUI application

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_ACTIVATE="$PROJECT_ROOT/orchestrator/venv/bin/activate"
TUI_MODULE="orchestrator.tui.app"

echo "[INFO] Attempting to run WizardPro TUI ($TUI_MODULE)..."
cd "$PROJECT_ROOT" || {
    echo "[ERROR] Failed cd to project root: $PROJECT_ROOT"
    exit 1
}

if [ ! -f "$VENV_ACTIVATE" ]; then
    echo "[ERROR] Venv activation script not found: $VENV_ACTIVATE."
    exit 1
fi
source "$VENV_ACTIVATE" || {
    echo "[ERROR] Failed activate venv."
    exit 1
}
echo "[INFO] Virtual environment activated."

if [ ! -f "$PROJECT_ROOT/orchestrator/tui/app.py" ]; then
    echo "[ERROR] TUI app script not found."
    deactivate
    exit 1
fi

echo "[INFO] Executing: python -m $TUI_MODULE \"\$@\"" # Pass args if needed
echo "--- TUI Output Start (Press Ctrl+C to exit TUI) ---"
python -m "$TUI_MODULE" "$@"
RUN_STATUS=$?
echo "--- TUI Output End ---"

deactivate || echo "[WARN] Deactivate failed."
echo "[INFO] Virtual environment deactivated attempt finished."

if [ $RUN_STATUS -eq 0 ]; then echo "[SUCCESS] TUI script finished successfully."; else echo "[ERROR] TUI script exited status $RUN_STATUS."; fi
exit $RUN_STATUS
