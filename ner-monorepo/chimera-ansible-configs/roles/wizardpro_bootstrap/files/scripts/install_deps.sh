#!/bin/bash
# Installs dependencies from requirements.txt into orchestrator/venv
# Assumes script is run from the project root directory

echo "[INFO] install_deps.sh starting..."

PROJECT_ROOT=$(pwd) # Use current directory as project root
VENV_DIR="orchestrator/venv"
VENV_ACTIVATE="$VENV_DIR/bin/activate"
REQ_FILE="orchestrator/requirements.txt"

echo "[DEBUG] Project Root: $PROJECT_ROOT"
echo "[DEBUG] Venv Path: $VENV_DIR"
echo "[DEBUG] Req File: $REQ_FILE"

# Check if requirements file exists using path relative to current dir
if [ ! -f "$REQ_FILE" ]; then
    echo "[ERROR] requirements.txt not found at '$PWD/$REQ_FILE'"
    ls -l orchestrator/ # Show directory content for debugging
    exit 1
fi
echo "[DEBUG] $REQ_FILE found."

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "[INFO] Creating virtual environment at $VENV_DIR..."
    # Use simpler path definition
    python3 -m venv "$VENV_DIR" || { echo "[ERROR] Failed to create venv."; exit 1; }
    echo "[DEBUG] Venv directory created."
else
    echo "[DEBUG] Venv directory already exists at $VENV_DIR."
fi
echo "[DEBUG] Venv directory check/creation complete."

# Activate and install
echo "[INFO] Activating venv: $VENV_ACTIVATE"
source "$VENV_ACTIVATE" || { echo "[ERROR] Failed to activate venv at '$VENV_ACTIVATE'."; exit 1; }
echo "[INFO] Venv activated. Installing packages..."

pip install --upgrade pip
pip install -r "$REQ_FILE"
INSTALL_STATUS=$?

# Deactivate (errors suppressed if not sourced)
deactivate &> /dev/null || true
echo "[INFO] Deactivation attempted."

if [ $INSTALL_STATUS -eq 0 ]; then
    echo "[SUCCESS] Dependencies installed successfully."
    exit 0
else
    echo "[ERROR] Dependency installation failed with status $INSTALL_STATUS."
    exit 1
fi
