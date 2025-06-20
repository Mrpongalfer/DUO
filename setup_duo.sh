#!/usr/bin/env xonsh
# Easy setup script for DUO project (Docker-first)

# Check for Docker
if ! command -v docker &>/dev/null:
    echo 'Docker is not installed. Please install Docker and rerun this script.'
    exit 1

# Build Docker image if not present
echo 'Building Docker image (if needed)...'
docker build -t duo-project .

# Optionally install Python dependencies locally (for VSCode tools, etc.)
if test -f requirements.txt:
    echo 'Installing Python dependencies locally (optional)...'
    pip install -r requirements.txt

# Print usage instructions
echo 'Setup complete!'
echo 'To start the main menu CLI inside Docker, run:'
echo '  docker run -it -p 5000:5000 -v $PWD:/workspace duo-project /bin/bash -c "cd /workspace/omnitide-vscode-bridge && python3 main.py"'
echo 'Or, to start the backend only:'
echo '  docker run -it -p 5000:5000 -v $PWD:/workspace duo-project /bin/bash -c "python3 start_nexus.py"'
