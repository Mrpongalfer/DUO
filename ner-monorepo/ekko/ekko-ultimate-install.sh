#!/bin/bash
set -euo pipefail

# Copyright (c) 2024 MrPongalfer. All rights reserved.
# This software is licensed under the Quantum Commercial License v1.0

# ====================
# CONFIGURATION WIZARD
# ====================
echo "🔮 Ekko Ultimate Installer v1.0"
echo "Copyright (c) 2024 MrPongalfer"

# Run config wizard if no args
#if [ $# -eq 0 ]; then
#    echo "Launching configuration wizard..."
#    bash <(curl -sSL https://raw.githubusercontent.com/mrpongalfer/ekko/main/ekko-config-wizard.sh)
#    exit 0
#fi

# ====================
# SYSTEM REQUIREMENTS
# ====================
echo "⚙️  Checking system requirements..."

REQUIREMENTS=("python3" "ansible" "docker" "git")
MISSING=()

for cmd in "${REQUIREMENTS[@]}"; do
    if ! command -v $cmd &> /dev/null; then
        MISSING+=("$cmd")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "❌ Missing dependencies:"
    for dep in "${MISSING[@]}"; do
        echo " - $dep"
    done
    echo "Install with: sudo apt install ${MISSING[*]}"
    exit 1
fi

# ====================
# INSTALLATION
# ====================
echo "🚀 Installing Ekko Ultimate..."

# Clone repository
git clone https://github.com/mrpongalfer/ekko.git /opt/ekko-ultimate

# Install Python dependencies
pip3 install -r /opt/ekko-ultimate/requirements.txt --user

# Setup symlinks
ln -s /opt/ekko-ultimate/bin/ekko /usr/local/bin/ekko
ln -s /opt/ekko-ultimate/bin/ekko-tui /usr/local/bin/ekko-tui

# Initialize Ansible roles
ansible-galaxy install -r /opt/ekko-ultimate/ansible/requirements.yml

# ====================
# POST-INSTALL
# ====================
echo "✅ Installation complete!"
echo "Quick start:"
echo "1. Run the TUI: ekko-tui"
echo "2. Initialize project: ekko init"
echo "3. Develop with AI: ekko dev --ai gemini"

cat << EOF

███████╗██╗  ██╗██╗  ██╗ ██████╗
██╔════╝██║ ██╔╝██║ ██╔╝██╔═══██╗
█████╗  █████╔╝ █████╔╝ ██║   ██║
██╔══╝  ██╔═██╗ ██╔═██╗ ██║   ██║
███████╗██║  ██╗██║  ██╗╚██████╔╝
╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝
Copyright (c) 2024 MrPongalfer
Quantum Commercial License v1.0
EOF
