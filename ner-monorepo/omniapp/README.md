# Omniapp Suite

Welcome to the Omniapp Suite, Architect!

This project consolidates various Omnitide Nexus tools, primarily focusing on:
- **Omnitide CLI:** A Python Typer-based command-line interface for orchestrating ExWork and Scribe.
- **Agents:** Core Scribe and ExWork agents (copied from your specified source).
- **Web UI:** A Flask-based web interface for interacting with the agents.
- **User Shell Setup:** Scripts to configure your Xonsh development environment.

## Setup

1.  This `bootstrap_omniapp.sh` script initializes the project structure.
2.  Ensure your Xonsh environment is configured (you can use `user_shell_setup/setup_omnitide_user_shell.sh`).
3.  Navigate to this directory (`omniapp`).
4.  Activate the direnv environment: `direnv allow .` (This will use the `.envrc` file).
5.  The direnv environment should create a Python virtual environment. Install dependencies: `pip install -r requirements.txt` while the venv is active.

## Usage
-   **Omnitide CLI:** `python omnitide_cli/omnitide_cli/main.py --help` (or `omni-cli --help` if `pyproject.toml` setup makes it a system command via `pip install -e ./omnitide_cli`)
-   **Web UI:** `python web_ui/app.py` (then open browser to http://127.0.0.1:5678)
-   **User Shell Setup:** `bash user_shell_setup/setup_omnitide_user_shell.sh` (Run this once to configure your user's Xonsh)
