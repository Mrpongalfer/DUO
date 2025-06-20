#!/usr/bin/env xonsh
# DUO: Holistic Environment Reset & Bootstrap Script

import os

BOLD = "\033[1m"
RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"

echo f"{BOLD}{GREEN}==== DUO: HOLISTIC ENVIRONMENT RESET ===={RESET}"

# 1. Nuking all venvs and build trash
venvs = [p for p in os.listdir('.') if os.path.isdir(p) and (p.endswith('venv') or p == '.venv')]
if venvs:
    echo f"{YELLOW}Removing old venvs: {', '.join(venvs)}{RESET}"
    for v in venvs:
        rm -rf $v
else:
    echo f"{GREEN}No old venvs found.{RESET}"

for trash in $(find . -type d -name '__pycache__' -o -name '*.egg-info' 2>/dev/null):
    rm -rf $trash

for pyc in $(find . -type f -name '*.pyc' 2>/dev/null):
    rm -f $pyc

for lock in ['Pipfile', 'Pipfile.lock', 'poetry.lock']:
    if os.path.exists(lock):
        echo f"{YELLOW}Removing {lock}{RESET}"
        rm -f $lock

echo f"{GREEN}All build trash removed.{RESET}"

# 2. Ensure pyenv and Python 3.11
if not which('pyenv'):
    echo f"{YELLOW}pyenv not found. Installing...{RESET}"
    curl -fsSL https://pyenv.run | bash
    $HOME/.pyenv/bin/pyenv init - | source
    $HOME/.pyenv/bin/pyenv virtualenv-init - | source

if not "3.11" in !pyenv versions --bare:
    echo f"{YELLOW}Installing Python 3.11.x via pyenv...{RESET}"
    pyenv install 3.11.9

pyenv local 3.11.9

# 3. Ensure uv (ultra-fast Python package manager)
if not which('uv'):
    echo f"{YELLOW}uv not found. Installing via pipx...{RESET}"
    pip install --user pipx
    pipx ensurepath
    pipx install uv

# 4. Create new .venv using uv
echo f"{YELLOW}Creating new .venv using uv...{RESET}"
uv venv .venv

# 5. Activate venv in Xonsh
source .venv/bin/activate.xsh

# 6. Install ruff, black, flake8 in the venv
echo f"{YELLOW}Installing ruff, black, flake8...{RESET}"
uv pip install -U ruff black flake8

# 7. Install all requirements
if os.path.exists('requirements.txt'):
    echo f"{YELLOW}Installing from requirements.txt...{RESET}"
    uv pip install -r requirements.txt

if os.path.exists('requirements-dev.txt'):
    echo f"{YELLOW}Installing from requirements-dev.txt...{RESET}"
    uv pip install -r requirements-dev.txt

if os.path.exists('pyproject.toml'):
    # Try to install dependencies specified in pyproject.toml
    if "dependencies" in $(cat pyproject.toml):
        echo f"{YELLOW}pyproject.toml detected with dependencies. Installing...{RESET}"
        uv pip install .
    else:
        echo f"{GREEN}pyproject.toml found, but no dependencies section detected.{RESET}"

# 8. Warn if .pre-commit-config.yaml exists (remind to run pre-commit install)
if os.path.exists('.pre-commit-config.yaml'):
    echo f"{YELLOW}Detected .pre-commit-config.yaml. You may want to run:{RESET}"
    echo f"{BOLD}    pre-commit install{RESET}"

# 9. Final VS Code instructions
echo ""
echo f"{BOLD}{GREEN}==== ENV RESET COMPLETE ===={RESET}"
echo f"{BOLD}Set your VS Code Python interpreter to: {os.getcwd()}/.venv/bin/python{RESET}"
echo f"Add to .vscode/settings.json:"
echo f'  "python.defaultInterpreterPath": "${{workspaceFolder}}/.venv/bin/python"'
echo ""
echo f"{BOLD}Test with:{RESET}"
echo f"  ruff ."
echo f"  black --check ."
echo f"  flake8 ."
echo f"  python3 run_duo_pipeline.py  # (if you have this orchestrator script)"
echo ""
echo f"{GREEN}Python version:{RESET}"
python --version
echo f"{GREEN}uv version:{RESET}"
uv --version
echo f"{GREEN}ruff version:{RESET}"
ruff --version
echo f"{GREEN}black version:{RESET}"
black --version
echo f"{GREEN}flake8 version:{RESET}"
flake8 --version
