#!/bin/bash
# --- run_ops_cli.sh ---
# Wrapper script to set up the venv for the Chimera Ops CLI,
# install its dependencies, and execute it.

set -e
VENV_DIR=".venv_ops" # Dedicated venv name for this tool
PYTHON_CMD="python3"
SCRIPTS_DIR="scripts"
REQS_FILE="${SCRIPTS_DIR}/requirements-cli.txt" # Requirements for the CLI tool
CLI_SCRIPT="chimera_ops_cli.py" # The main Python CLI application

# --- Colors ---
GREEN='\033[1;32m'; YELLOW='\033[1;33m'; RED='\033[1;31m'; NC='\033[0m'
info() { echo -e "${GREEN}INFO:${NC} $1"; }
warn() { echo -e "${YELLOW}WARN:${NC} $1"; }
error() { echo -e "${RED}ERROR:${NC} $1" >&2; exit 1; }

# --- Determine Platform Specific Paths ---
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    VENV_BIN_DIR="${VENV_DIR}/Scripts"; VENV_PYTHON="${VENV_BIN_DIR}/python.exe"
else
    VENV_BIN_DIR="${VENV_DIR}/bin"; VENV_PYTHON="${VENV_BIN_DIR}/python"
fi

info "Starting Chimera Ops CLI Launcher..."

# 1. Check for base Python command
if ! command -v $PYTHON_CMD &> /dev/null; then error "'$PYTHON_CMD' not found."; fi

# 2. Check/Create CLI Tool Virtual Environment
if [ ! -d "$VENV_DIR" ]; then
    info "Creating Ops CLI virtual environment '$VENV_DIR'..."
    if ! $PYTHON_CMD -m venv "$VENV_DIR"; then error "Failed to create venv."; fi
    info "Virtual environment created."
else
    info "Ops CLI virtual environment '$VENV_DIR' already exists."
fi

# 3. Check/Install CLI Tool Dependencies
if [ ! -f "$VENV_PYTHON" ]; then error "Python not found in venv at '$VENV_PYTHON'."; fi
if [ ! -f "$REQS_FILE" ]; then error "CLI requirements file '$REQS_FILE' not found."; fi

info "Installing/Verifying Ops CLI dependencies from '$REQS_FILE' into '$VENV_DIR'..."
# Use venv's python to run pip
if ! "$VENV_PYTHON" -m pip install -r "$REQS_FILE"; then error "Failed to install Ops CLI dependencies."; fi
info "Ops CLI dependencies checked/installed."

# 4. Execute the Main Python CLI Application
info "Launching Chimera Ops CLI: $CLI_SCRIPT ..."
if [ ! -f "$CLI_SCRIPT" ]; then error "Main CLI script '$CLI_SCRIPT' not found."; fi

# Execute using the venv's Python interpreter, passing any arguments ($@)
"$VENV_PYTHON" "$CLI_SCRIPT" "$@"
EXIT_CODE=$?

# Exit with the Python script's exit code
exit $EXIT_CODE
