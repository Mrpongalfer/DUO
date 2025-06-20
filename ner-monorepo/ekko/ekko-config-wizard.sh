#!/bin/bash

# Copyright (c) 2024 MrPongalfer. All rights reserved.

echo "🔍 Ekko Configuration Wizard"
echo "We need some information to customize your setup:"

# Collect user info
read -p "Enter your GitHub username: " GITHUB_USER
read -p "Enter your preferred AI model (gemini/gpt4/claude): " AI_MODEL
read -p "Enable chaos engineering? (y/n): " CHAOS_MODE
read -p "Set commercial license key (or press enter for free tier): " LICENSE_KEY

# Generate config
CONFIG_FILE="$HOME/.ekko/config.yaml"
mkdir -p "$(dirname "$CONFIG_FILE")"

cat > "$CONFIG_FILE" << EOF
# Ekko Configuration
user:
  github: "$GITHUB_USER"
  license_key: "$LICENSE_KEY"

ai:
  preferred_model: "$AI_MODEL"
  safety_level: "strict"

chaos_engineering:
  enabled: $([ "$CHAOS_MODE" = "y" ] && echo "true" || echo "false")
  intensity: 5

ansible:
  auto_deploy: true
  cloud_provider: "aws"
EOF

echo "✅ Configuration saved to $CONFIG_FILE"
echo "Run the installer with: ./ekko-ultimate-install.sh"
