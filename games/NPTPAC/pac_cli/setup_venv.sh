#!/usr/bin/env xonsh
# Setup script for PAC Python Virtual Environment v2.0


# Xonsh-compatible setup script for PAC Python Virtual Environment v2.0

import os
import sys
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
VENV_NAME = ".venv_pac"
PYTHON_EXECUTABLE = "python3"
REQUIREMENTS_FILE = SCRIPT_DIR / "requirements.txt"
REQUIREMENTS_DEV_FILE = SCRIPT_DIR / "requirements-dev.txt"

print(f"Setting up Python virtual environment for PAC in {SCRIPT_DIR}/{VENV_NAME}...")
print(f"Using Python: {PYTHON_EXECUTABLE}")

if not shutil.which(PYTHON_EXECUTABLE):
    print(f"ERROR: Python executable '{PYTHON_EXECUTABLE}' not found. Cannot create venv.")
    sys.exit(1)

venv_path = SCRIPT_DIR / VENV_NAME
if not venv_path.exists():
    print("Creating venv...")
    os.system(f"{PYTHON_EXECUTABLE} -m venv {venv_path}")
else:
    print(f"Virtual environment '{VENV_NAME}' already exists in {SCRIPT_DIR}.")

activate_script = venv_path / "bin" / "activate"
if not activate_script.exists():
    print(f"ERROR: Activation script not found at {activate_script}")
    sys.exit(1)

print("Activating venv...")
execx(f"source {activate_script}")

print("Upgrading pip, setuptools, and wheel...")
os.system("pip install --disable-pip-version-check --upgrade pip setuptools wheel")

if not REQUIREMENTS_FILE.exists():
    print(f"ERROR: {REQUIREMENTS_FILE} not found. Cannot install dependencies.")
    sys.exit(1)

print(f"Installing dependencies from {REQUIREMENTS_FILE}...")
os.system(f"pip install --disable-pip-version-check -r {REQUIREMENTS_FILE}")

if REQUIREMENTS_DEV_FILE.exists():
    print(f"Installing development dependencies from {REQUIREMENTS_DEV_FILE}...")
    os.system(f"pip install -r {REQUIREMENTS_DEV_FILE}")

print("")
print(f"PAC Python environment in '{venv_path}' is ready.")
print("To activate it manually in the future, run from the 'pac_cli' directory:")
print(f"  source ./{VENV_NAME}/bin/activate")
print("To run PAC, use the 'npac' launcher from the NPT base directory (recommended).")

print("Setup complete. Virtual environment is ready.")