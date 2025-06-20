    #!/bin/bash
    # setup_nexusterm_apex.sh - v2.7: Added delay and refined python check
    # Single script to set up NexusTerm TUI Dev Suite project in Termux.

    set -e # Exit immediately if a command exits with a non-zero status.

    echo "--- Starting Apex NexusTerm Setup Script (v2.7) ---"
    echo "Timestamp: $(date)"

    # --- 0. Define Project Path ---
    PROJECT_PARENT_DIR="$HOME/Projects"
    PROJECT_NAME="nexusterm"
    PROJECT_DIR="${PROJECT_PARENT_DIR}/${PROJECT_NAME}"
    VENV_DIR_NAME=".venv"
    echo "[Info] Target Project Directory: ${PROJECT_DIR}"
    mkdir -p "$PROJECT_PARENT_DIR"

    # --- 1. System Package Update ---
    echo "[Step 1/10] Updating Termux packages..."
    pkg update -y && pkg upgrade -y || { echo "[FATAL] Failed to update Termux packages."; exit 1; }
    echo "[OK] Termux packages updated."

    # --- 2. Install Required Termux Packages ---
    echo "[Step 2/10] Checking and installing required Termux packages..."
    REQUIRED_PKGS=("python" "git" "openssh" "build-essential" "libffi" "libjpeg-turbo" "zlib" "python-pip")
    echo "[Action] Ensuring required packages are installed: ${REQUIRED_PKGS[*]}"
    pkg install -y "${REQUIRED_PKGS[@]}" || { echo "[FATAL] Failed to install required Termux packages via pkg."; exit 1; }
    if ! command -v python >/dev/null 2>&1; then echo "[FATAL] Python not found after install."; exit 1; fi
    if ! python -m venv -h > /dev/null 2>&1; then echo "[FATAL] Python venv module not functional."; exit 1; fi
    echo "[OK] Required Termux packages installed/verified."

    # --- 3. Create Project Structure ---
    echo "[Step 3/10] Creating project directory structure..."
    mkdir -p "${PROJECT_DIR}/src/${PROJECT_NAME}" "${PROJECT_DIR}/scripts" "${PROJECT_DIR}/tests" "${PROJECT_DIR}/docs"
    echo "[OK] Base project directories created at ${PROJECT_DIR}"

    # --- 4. Initialize Git Repository ---
    echo "[Step 4/10] Initializing Git repository..."
    if [ -d "${PROJECT_DIR}/.git" ]; then
        echo "  [Skipped] Git repository already initialized."
    else
        mkdir -p "${PROJECT_DIR}" || { echo "[FATAL] Could not create project dir ${PROJECT_DIR}"; exit 1; }
        cd "${PROJECT_DIR}" || exit 1
        git init && git branch -M main || { echo "[FATAL] Failed to initialize Git repository."; cd - > /dev/null; exit 1; }
        echo "[OK] Git repository initialized."
        cd - > /dev/null
    fi

    # --- 5. Create Basic Files (.gitignore, README.md) ---
    echo "[Step 5/10] Creating basic project files..."
    GITIGNORE_PATH="${PROJECT_DIR}/.gitignore"; README_PATH="${PROJECT_DIR}/README.md"
    if [ ! -f "$GITIGNORE_PATH" ]; then echo "  Creating .gitignore..."; cat << 'EOF' > "$GITIGNORE_PATH"
    # (gitignore content as before)
    __pycache__/
    *.py[cod]
    *$py.class
    *.so
    build/
    dist/
    downloads/
    eggs/
    .eggs/
    lib/
    lib64/
    parts/
    sdist/
    var/
    wheels/
    *.egg-info/
    .installed.cfg
    *.egg
    MANIFEST
    .venv/
    venv/
    .vscode/
    .idea/
    *.sw?
    .DS_Store
    Thumbs.db
    htmlcov/
    .tox/
    .nox/
    .coverage*
    .cache
    nosetests.xml
    coverage.xml
    *.cover
    *.py,cover
    .hypothesis/
    .pytest_cache/
    cover/
    *.log
    *.tmp
    *.bak
    *.scribe.toml
    scribe_generated_tests/

EOF
else echo "  [Skipped] .gitignore already exists."; fi
if [ ! -f "$README_PATH" ]; then echo "  Creating README.md..."; cat << 'EOF' > "$README_PATH"
NexusTerm TUI Dev Suite (v2.0)

(Placeholder)
Usage

```bash
cd ~/Projects/nexusterm && ./run_nexusterm.sh
```
EOF
else echo "  [Skipped] README.md already exists."; fi
echo "[OK] Basic files created/verified."

# --- 6. Setup Python Virtual Environment & Find Executable ---
echo "[Step 6/10] Setting up Python virtual environment..."
VENV_PATH="${PROJECT_DIR}/${VENV_DIR_NAME}"
if [ ! -d "$VENV_PATH" ]; then
    echo "  Creating venv at ${VENV_PATH}..."
    python -m venv "${VENV_PATH}" || { echo "[FATAL] Failed to create virtual environment."; exit 1; }
    echo "  [OK] Virtual environment created. Pausing 1s for filesystem sync..."
    sleep 1 # ADDED DELAY
else
    echo "  [OK] Existing virtual environment found at ${VENV_PATH}."
fi

# Robustly find python executable inside venv bin
VENV_BIN_DIR="${VENV_PATH}/bin"
VENV_PYTHON=""
# Prioritize specific version found in manual test
PYTHON_CANDIDATES=("python3.12" "python3.11" "python3" "python")
echo "  Searching for Python executable in ${VENV_BIN_DIR}..."
for py_cmd in "${PYTHON_CANDIDATES[@]}"; do
    if [ -f "${VENV_BIN_DIR}/${py_cmd}" ]; then
        VENV_PYTHON="${VENV_BIN_DIR}/${py_cmd}"
        echo "    [Found] Using: ${VENV_PYTHON}"
        break
    fi
done
if [ -z "$VENV_PYTHON" ]; then echo "[FATAL] Could not find Python executable in ${VENV_BIN_DIR}."; ls -l "${VENV_BIN_DIR}"; exit 1; fi
echo "  Ensuring ${VENV_PYTHON} is executable..."
chmod +x "$VENV_PYTHON" || echo "[Warning] Failed to chmod venv Python."
echo "[OK] Venv Python path set to: ${VENV_PYTHON}"

# --- 7. Install Initial Python Dependencies ---
echo "[Step 7/10] Installing core & dev Python dependencies..."
echo "  Upgrading pip..."
"$VENV_PYTHON" -m pip install --upgrade pip || { echo "[FATAL] Failed to upgrade pip."; exit 1; }
echo "  Installing textual, paramiko, cryptography, bcrypt, ruff, pre-commit..."
"$VENV_PYTHON" -m pip install "textual[dev]>=0.50.0" "paramiko>=2.10.0" "cryptography>=3.4.0" "bcrypt>=3.2.0" "ruff>=0.4.0" "pre-commit>=3.0.0" || { echo "[FATAL] Failed to install Python dependencies."; exit 1; }
echo "[OK] Python dependencies installed."

# --- 8. Setup Pre-commit ---
echo "[Step 8/10] Setting up pre-commit hooks..."
PRECOMMIT_CONFIG_PATH="${PROJECT_DIR}/.pre-commit-config.yaml"
VENV_PRECOMMIT="${VENV_PATH}/bin/pre-commit"
if [ ! -f "$PRECOMMIT_CONFIG_PATH" ]; then echo "  Creating .pre-commit-config.yaml..."; cat << 'EOF' > "$PRECOMMIT_CONFIG_PATH"

File: .pre-commit-config.yaml for NexusTerm

exclude: ^.venv/
repos:

    repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4 # Use latest stable tag
    hooks:
        id: ruff args: [--fix, --exit-non-zero-on-fix]
        id: ruff-format

    repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0 # Use latest stable tag
    hooks:
        id: trailing-whitespace
        id: end-of-file-fixer
        id: check-yaml
        id: check-json
        id: check-toml EOF else echo " [Skipped] .pre-commit-config.yaml already exists."; fi echo " Installing pre-commit hooks into git repo..."
    Ensure pre-commit executable exists before running install

    if [ ! -f "$VENV_PRECOMMIT" ]; then echo "[FATAL] pre-commit executable not found in venv: ${VENV_PRECOMMIT}"; exit 1; fi
    (cd "${PROJECT_DIR}" && "$VENV_PRECOMMIT" install) || { echo "[Error] Failed to install pre-commit hooks."; exit 1; }
    echo "[OK] Pre-commit setup complete."
    --- 9. Create Placeholder App & Launch Script ---

    echo "[Step 9/10] Creating placeholder TUI app and launch script..."
    APP_SRC_DIR="${PROJECT_DIR}/src"; APP_PACKAGE_DIR="${APP_SRC_DIR}/${PROJECT_NAME}"
    APP_FILE="${APP_PACKAGE_DIR}/main.py"; INIT_FILE="${APP_PACKAGE_DIR}/init.py"
    LAUNCH_SCRIPT="${PROJECT_DIR}/run_nexusterm.sh"
    mkdir -p "$APP_PACKAGE_DIR"; echo -n > "$INIT_FILE" || { echo "[FATAL] Failed create ${INIT_FILE}"; exit 1; }
    echo "  Creating ${APP_FILE}..."
    cat << 'EOF' > "$APP_FILE"
    #!/usr/bin/env python3

src/nexusterm/main.py - Placeholder for NexusTerm TUI v0.1

import os
import sys
from pathlib import Path
import logging
Basic logging setup

LOG_FILE = Path(file).parent.parent.parent / "nexusterm_debug.log"
logging.basicConfig(level=logging.DEBUG, filename=LOG_FILE, filemode='a', format='%(asctime)s-%(levelname)s-%(name)s-%(message)s')
logger = logging.getLogger(name)

try:
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Label
from textual.containers import Container
except ImportError as e:
logger.critical(f"Textual import failed: {e}")
print(f"ERROR: Textual failed import. Run setup script again or check venv.", file=sys.stderr)
sys.exit(f"Dependency Error: {e}")

class NexusTermApp(App):
TITLE = "NexusTerm v0.1 Alpha"; BINDINGS = [("d", "toggle_dark", "Toggle Dark"), ("q", "quit", "Quit")]
def compose(self) -> ComposeResult:
logger.info(f"Composing UI (PID: {os.getpid()})..."); yield Header()
yield Container(Label(f"Welcome to {self.TITLE}!"), Static(f"Log: {LOG_FILE}"), Static("Core logic pending.", id="status")); yield Footer()
def action_toggle_dark(self) -> None: self.dark = not self.dark; logger.debug("Toggled dark mode.")
def action_quit(self) -> None: logger.info("Quit action invoked."); self.exit("User quit.")

if name == "main":
logger.info("--- Starting NexusTermApp ---")
app = NexusTermApp(); app.run()
logger.info("--- NexusTermApp Exited ---")
EOF
echo "  Creating ${LAUNCH_SCRIPT}..."
cat << 'EOF' > "$LAUNCH_SCRIPT"
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python" # Use found python
APP_MAIN="${SCRIPT_DIR}/src/nexusterm/main.py"
if [ ! -f "$VENV_PYTHON" ]; then echo "[Error] Venv Python missing: $VENV_PYTHON"; exit 1; fi
if [ ! -f "$APP_MAIN" ]; then echo "[Error] Main app script missing: $APP_MAIN"; exit 1; fi
echo "[NexusTerm] Launching TUI using: $VENV_PYTHON..."
"$VENV_PYTHON" "$APP_MAIN"
EXIT_CODE=$?
echo "[NexusTerm] TUI exited with code: $EXIT_CODE"
exit $EXIT_CODE
EOF
chmod +x "${APP_FILE}"; chmod +x "${LAUNCH_SCRIPT}"
echo "[OK] Placeholder app and launch script created."

# --- 10. Initial Commit ---
echo "[Step 10/10] Creating initial Git commit..."
cd "${PROJECT_DIR}" || exit 1
if [ -n "$(git status --porcelain)" ]; then
    git add . || echo "[Warning] git add failed."
    # Skip hooks for this initial setup commit
    git commit --no-verify -m "feat: Initial project structure and setup via setup_nexusterm_apex.sh v2.7" || echo "[Warning] Initial git commit failed."
    echo "[OK] Initial commit created (or skipped)."
else echo "[Skipped] No changes detected for initial commit."; fi
cd - > /dev/null

echo ""
echo "--- NexusTerm Apex Setup Complete (v2.7) ---"
echo "Project created at: ${PROJECT_DIR}"
echo "Quality tools (Ruff, Pre-commit) are installed and configured."
echo ""
echo "To run the placeholder TUI:"
echo "1. cd ${PROJECT_DIR}"
echo "2. ./run_nexusterm.sh"
echo ""
echo "Next step is NexusTerm Block 1: Core TUI layout & SSH."
echo "---------------------------------------"

exit 0
```