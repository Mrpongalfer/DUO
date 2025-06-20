    #!/bin/bash
    # setup_nexusterm_apex.sh
    # Single script to set up NexusTerm TUI Dev Suite project in Termux.
    # Performs package checks/installs, dir creation, git init, venv setup,
    # Python deps install, placeholder app creation, and launch script generation.
    # Adheres to Drake Edict v5.0 Apex - Mandate Dependency Self-Sufficiency v1.0.

    set -e # Exit immediately if a command exits with a non-zero status.

    echo "--- Starting Apex NexusTerm Setup Script ---"
    echo "Timestamp: $(date)"

    # --- 0. Define Project Path ---
    # Using ~/nexusterm directly for simplicity in Termux home
    PROJECT_DIR="$HOME/nexusterm"
    echo "[Info] Target Project Directory: ${PROJECT_DIR}"

    # --- 1. System Package Update ---
    echo "[Step 1/8] Updating Termux packages..."
    pkg update -y && pkg upgrade -y || { echo "[FATAL] Failed to update Termux packages. Check network or pkg configuration."; exit 1; }
    echo "[OK] Termux packages updated."

    # --- 2. Install Required Termux Packages ---
    echo "[Step 2/8] Checking and installing required Termux packages..."
    # Added common build dependencies explicitly
    REQUIRED_PKGS=(
        python git openssh build-essential libffi-dev libjpeg-turbo zlib-dev
        python-pip python-venv # Ensure pip and venv tools are present
    )
    # Attempt to install all, pkg install handles existing ones gracefully
    echo "[Action] Ensuring required packages are installed: ${REQUIRED_PKGS[*]}"
    pkg install -y "${REQUIRED_PKGS[@]}" || { echo "[FATAL] Failed to install required Termux packages via pkg."; exit 1; }
    echo "[OK] Required Termux packages installed/verified."

    # Verify python and venv module specifically after install attempt
    if ! command -v python >/dev/null 2>&1; then echo "[FATAL] Python command still not found after install attempt."; exit 1; fi
    if ! python -m venv -h > /dev/null 2>&1; then echo "[FATAL] Python venv module still not functional after install attempt."; exit 1; fi
    echo "[OK] Python and venv module confirmed functional."

    # --- 3. Create Project Structure ---
    echo "[Step 3/8] Creating project directory structure..."
    mkdir -p "${PROJECT_DIR}/src/${PROJECT_NAME}" # Use src layout
    mkdir -p "${PROJECT_DIR}/scripts"
    mkdir -p "${PROJECT_DIR}/tests"
    mkdir -p "${PROJECT_DIR}/docs"
    echo "[OK] Project directories created at ${PROJECT_DIR}"

    # --- 4. Initialize Git Repository ---
    echo "[Step 4/8] Initializing Git repository..."
    # Check if already initialized only within the target dir
    if [ -d "${PROJECT_DIR}/.git" ]; then
        echo "  [Skipped] Git repository already initialized in ${PROJECT_DIR}."
    else
        cd "${PROJECT_DIR}" || { echo "[FATAL] Could not cd to ${PROJECT_DIR}"; exit 1; }
        git init || { echo "[FATAL] Failed to initialize Git repository."; cd - > /dev/null; exit 1; }
        echo "[OK] Git repository initialized."
        cd - > /dev/null # Go back to original dir silently
    fi

    # --- 5. Create Basic Files (.gitignore, README.md) ---
    echo "[Step 5/8] Creating basic project files..."
    GITIGNORE_PATH="${PROJECT_DIR}/.gitignore"
    README_PATH="${PROJECT_DIR}/README.md"

    if [ ! -f "$GITIGNORE_PATH" ]; then
        echo "  Creating .gitignore..."
        cat << EOF > "$GITIGNORE_PATH"

Python cache files

pycache/
*.py[cod]
*$py.class
Virtual environment

.venv/
venv/
IDE / Editor files

.vscode/
.idea/
*.swp
*~
OS files

.DS_Store
Thumbs.db
Test / Coverage outputs

htmlcov/
.coverage
.pytest_cache/
Build artifacts

build/
dist/
*.egg-info/
Logs and Temp

*.log
*.tmp
*.bak
Scribe specific (if run against itself)

*.scribe.toml
scribe_generated_tests/
EOF
else echo "  [Skipped] .gitignore already exists."
fi

if [ ! -f "$README_PATH" ]; then
    echo "  Creating README.md..."
    cat << EOF > "$README_PATH"

NexusTerm TUI Dev Suite (v2.0)

Project Goal: A sophisticated TUI interface for managing development workflows, server control, and AI interaction via Termux on mobile.

(Placeholder - To be expanded)
Setup

(Instructions will be added here)
Usage

```bash
./run_nexusterm.sh
```
EOF
else echo "  [Skipped] README.md already exists."
fi
echo "[OK] Basic files created/verified."

# --- 6. Setup Python Virtual Environment ---
echo "[Step 6/8] Setting up Python virtual environment..."
VENV_PATH="${PROJECT_DIR}/${VENV_DIR_NAME}"
if [ ! -d "$VENV_PATH" ]; then
    echo "  Creating venv at ${VENV_PATH}..."
    # Use system python (verified available in Step 2)
    python -m venv "${VENV_PATH}" || { echo "[FATAL] Failed to create virtual environment."; exit 1; }
    echo "  [OK] Virtual environment created."
else
    echo "  [OK] Existing virtual environment found at ${VENV_PATH}."
fi

# --- 7. Install Initial Python Dependencies ---
echo "[Step 7/8] Installing core Python dependencies (Textual, Paramiko)..."
VENV_PYTHON="${VENV_PATH}/bin/python"
VENV_PIP="${VENV_PATH}/bin/pip" # While -m pip is safer, direct path needed? Use python -m pip

# Ensure venv Python is executable (Fixes potential Termux/venv permission issue)
if [ -f "$VENV_PYTHON" ]; then
    chmod +x "$VENV_PYTHON" || echo "[Warning] Failed to chmod venv Python."
else
    echo "[FATAL] Venv Python not found at ${VENV_PYTHON} after creation."
    exit 1
fi

# Upgrade pip & Install core libraries using the venv's python
"$VENV_PYTHON" -m pip install --upgrade pip || { echo "[FATAL] Failed to upgrade pip in venv."; exit 1; }
"$VENV_PYTHON" -m pip install "textual[dev]>=0.50.0" "paramiko>=2.10.0" "cryptography>=3.4.0" "bcrypt>=3.2.0" || { echo "[FATAL] Failed to install core Python dependencies."; exit 1; }
echo "[OK] Core Python dependencies installed."

# --- 8. Create Placeholder App & Launch Script ---
echo "[Step 8/8] Creating placeholder TUI app and launch script..."
APP_DIR="${PROJECT_DIR}/src/${PROJECT_NAME}"
APP_FILE="${APP_DIR}/main.py"
INIT_FILE="${APP_DIR}/__init__.py"
LAUNCH_SCRIPT="${PROJECT_DIR}/run_nexusterm.sh"

mkdir -p "$APP_DIR" # Ensure src/projectname exists
touch "$INIT_FILE"  # Create __init__.py

# Create placeholder main.py
cat << EOF > "$APP_FILE"

#!/usr/bin/env python3
src/${PROJECT_NAME}/main.py - Placeholder for NexusTerm TUI

import os
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Label
from textual.containers import Container

class NexusTermApp(App):
"""NexusTerm TUI Placeholder"""

TITLE = "NexusTerm v0.1 Alpha"
BINDINGS = [("d", "toggle_dark", "Toggle Dark Mode"), ("q", "quit", "Quit")]

def compose(self) -> ComposeResult:
    yield Header()
    yield Container(
        Label(f"Welcome to {self.TITLE}! (PID: {os.getpid()})"),
        Static("Core functionality (SSH, Git, Scribe, Ansible) pending implementation.", id="status-line")
    )
    yield Footer()

def action_toggle_dark(self) -> None:
    self.dark = not self.dark

def action_quit(self) -> None:
    self.exit("User requested quit.")

if name == "main":
app = NexusTermApp()
app.run()

EOF

# Create launch script
cat << EOF > "$LAUNCH_SCRIPT"

#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
VENV_ACTIVATE="${SCRIPT_DIR}/${VENV_DIR_NAME}/bin/activate"
APP_MAIN="${SCRIPT_DIR}/src/${PROJECT_NAME}/main.py"

if [ ! -f "$VENV_ACTIVATE" ]; then
echo "[Error] Virtual environment activate script not found at $VENV_ACTIVATE"
echo "Please run setup script again or ensure venv exists."
exit 1
fi

if [ ! -f "$APP_MAIN" ]; then
echo "[Error] Main application script not found at $APP_MAIN"
exit 1
fi

echo "[NexusTerm] Activating environment and launching TUI..."
Activate venv then execute python script in the same command sequence

source "$VENV_ACTIVATE" && python "$APP_MAIN"

echo "[NexusTerm] TUI exited. Deactivating venv (if shell persists)..."
Deactivate might not run if script exits fully, but good practice

deactivate || true # Ignore error if deactivate fails (e.g., not interactive)
EOF
chmod +x "$LAUNCH_SCRIPT"
echo "[OK] Placeholder app and launch script created."

echo ""
echo "--- NexusTerm Apex Setup Complete ---"
echo "Project created at: ${PROJECT_DIR}"
echo ""
echo "To run the placeholder TUI:"
echo "1. cd ${PROJECT_DIR}"
echo "2. ./run_nexusterm.sh"
echo ""
echo "Next step is Block 1: Implementing core TUI layout & SSH functionality."
echo "---------------------------------------"

exit 0
```