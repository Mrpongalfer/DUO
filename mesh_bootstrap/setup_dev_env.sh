#!/usr/bin/env bash
# setup_dev_env.sh
# Aggressive, idempotent, production-ready dev environment bootstrap for Pop!_OS
# Installs: xonsh, starship, VS Code, Docker, Docker Compose, Python3, pip, git, build tools
# Configures: xonsh as default shell, starship prompt, VS Code extensions

set -e

# Update and upgrade
sudo apt update && sudo apt upgrade -y

# Essential tools
sudo apt install -y git curl wget build-essential python3 python3-pip python3-venv unzip

# Xonsh
if ! command -v xonsh &> /dev/null; then
    pip3 install --user xonsh
    echo "xonsh installed via pip3."
fi

# Starship
if ! command -v starship &> /dev/null; then
    curl -sS https://starship.rs/install.sh | sh -s -- -y
    echo 'eval "$(starship init xonsh)"' >> ~/.xonshrc
fi

# Set xonsh as default shell
if [ "$SHELL" != "$(which xonsh)" ]; then
    chsh -s $(which xonsh)
fi

# VS Code
if ! command -v code &> /dev/null; then
    wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg
    sudo install -o root -g root -m 644 microsoft.gpg /etc/apt/trusted.gpg.d/
    sudo sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/repos/vscode stable main" > /etc/apt/sources.list.d/vscode.list'
    sudo apt update
    sudo apt install -y code
    rm microsoft.gpg
fi

# VS Code Extensions
code --install-extension ms-python.python || true
code --install-extension ms-azuretools.vscode-docker || true
code --install-extension GitHub.copilot || true
code --install-extension eamodio.gitlens || true

# Docker & Docker Compose
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
fi
if ! command -v docker-compose &> /dev/null; then
    sudo apt install -y docker-compose
fi

# Print summary
cat <<EOF

Dev environment setup complete!
- xonsh shell (set as default)
- starship prompt
- VS Code with Python, Docker, Copilot, GitLens extensions
- Docker & Compose
- Python3, pip, build tools

Log out and log back in for shell and Docker group changes to take effect.
EOF
