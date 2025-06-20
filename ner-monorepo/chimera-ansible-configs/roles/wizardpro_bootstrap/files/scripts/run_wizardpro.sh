#!/bin/bash
# Runs the WizardPro CLI orchestrator

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_ACTIVATE="$PROJECT_ROOT/orchestrator/venv/bin/activate"
MODULE_PATH="orchestrator.main"

echo "[INFO] Attempting to run WizardPro Orchestrator as module ($MODULE_PATH)..."
cd "$PROJECT_ROOT" || {
    echo "[ERROR] Failed to cd to project root: $PROJECT_ROOT"
    exit 1
}

if [ ! -f "$VENV_ACTIVATE" ]; then
    echo "[ERROR] Venv activation script not found at $VENV_ACTIVATE. Run install_deps.sh first."
    exit 1
fi
source "$VENV_ACTIVATE" || {
    echo "[ERROR] Failed to activate venv."
    exit 1
}
echo "[INFO] Virtual environment activated."

echo "[INFO] Executing: python -m $MODULE_PATH \"\$@\"" # Pass script args to python module
echo "--- Orchestrator Output Start ---"
python -m "$MODULE_PATH" "$@" # Pass all arguments from script call
RUN_STATUS=$?
echo "--- Orchestrator Output End ---"

deactivate || echo "[WARN] Deactivate failed."
echo "[INFO] Virtual environment deactivated attempt finished."

if [ $RUN_STATUS -eq 0 ]; then echo "[SUCCESS] Orchestrator script finished successfully (Exit Code 0)."; else echo "[ERROR] Orchestrator script failed (Exit Code $RUN_STATUS). Check output."; fi
exit $RUN_STATUS
