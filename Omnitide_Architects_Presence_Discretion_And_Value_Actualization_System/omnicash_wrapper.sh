#!/bin/bash
# OAPDVAS Control Center Wrapper Script
# Ensures the Python interpreter and virtual environment are correctly used.

# Resolve the absolute path of the script, handling symlinks
# This ensures we always get the true location of the OAPDVAS project root.
SCRIPT_FULL_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$SCRIPT_FULL_PATH")"
cd "$SCRIPT_DIR" || { echo "ERROR: Could not navigate to OAPDVAS project directory: $SCRIPT_DIR"; exit 1; }

# Activate the Python virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "ERROR: Python virtual environment not found. Please run './setup_oapdvas.sh' first."
    exit 1
fi

# Execute the Python Control Center script
python3 oapdvas_control_center.py "$@"

# Deactivate the virtual environment when the script exits (optional, but good practice)
# deactivate # This might interfere with TUI persistence, often omitted for TUI apps.