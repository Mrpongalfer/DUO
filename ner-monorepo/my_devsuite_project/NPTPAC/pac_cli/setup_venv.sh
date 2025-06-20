#!/bin/bash
# Setup script for PAC Python Virtual Environment v2.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_NAME=".venv_pac"
PYTHON_EXECUTABLE="python3" # Python command determined by NPT generator
REQUIREMENTS_FILE="\$SCRIPT_DIR/requirements.txt"
# REQUIREMENTS_DEV_FILE="\$SCRIPT_DIR/requirements-dev.txt" # If generating this too

echo "Setting up Python virtual environment for PAC in \$SCRIPT_DIR/\$VENV_NAME..."
echo "Using Python: \$PYTHON_EXECUTABLE"

if [ ! -f "\$PYTHON_EXECUTABLE" ]; then
    echo "ERROR: Python executable '\$PYTHON_EXECUTABLE' not found. Cannot create venv."
    exit 1
fi

if [ ! -d "\$SCRIPT_DIR/\$VENV_NAME" ]; then
    echo "Creating venv..."
    \$PYTHON_EXECUTABLE -m venv "\$SCRIPT_DIR/\$VENV_NAME" || { echo "ERROR: Failed to create venv."; exit 1; }
else
    echo "Virtual environment '\$VENV_NAME' already exists in \$SCRIPT_DIR."
fi

echo "Activating venv..."
# shellcheck source=/dev/null
source "\$SCRIPT_DIR/\$VENV_NAME/bin/activate" || { echo "ERROR: Failed to activate venv."; exit 1; }

echo "Upgrading pip, setuptools, and wheel..."
pip install --disable-pip-version-check --upgrade pip setuptools wheel || {
    echo "WARN: Failed to upgrade pip/setuptools/wheel. Proceeding with dependency installation."
}

if [ ! -f "\$REQUIREMENTS_FILE" ]; then
    echo "ERROR: \$REQUIREMENTS_FILE not found. Cannot install dependencies."
    deactivate
    exit 1
fi

echo "Installing dependencies from \$REQUIREMENTS_FILE..."
pip install --disable-pip-version-check -r "\$REQUIREMENTS_FILE" || {
    echo "ERROR: Failed to install dependencies from \$REQUIREMENTS_FILE."
    echo "Ensure all dependencies are compatible and network is available."
    deactivate
    exit 1
}

# Optional: Install dev dependencies
# if [ -f "\$REQUIREMENTS_DEV_FILE" ]; then
#   echo "Installing development dependencies from \$REQUIREMENTS_DEV_FILE..."
#   pip install -r "\$REQUIREMENTS_DEV_FILE" || {
#       echo "WARN: Failed to install dev dependencies. Main dependencies installed."
#   }
# fi

echo ""
echo "PAC Python environment in '\$SCRIPT_DIR/\$VENV_NAME' is ready."
echo "To activate it manually in the future, run from the 'pac_cli' directory:"
echo "  source ./$VENV_NAME/bin/activate"
echo "To run PAC, use the 'npac' launcher from the NPT base directory (recommended)."

deactivate
echo "Setup complete. Virtual environment deactivated for current shell."