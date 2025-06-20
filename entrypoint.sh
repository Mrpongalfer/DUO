#!/bin/bash
set -e

# Pass 2: Enhance entrypoint for zero-touch automation
# Add .env loading, LLM config, and auto-dependency install
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Auto-detect and install missing dependencies
if [ -f requirements.txt ]; then
    echo "[Entrypoint] Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt || true
fi

# Auto-detect and run migrations/setup if present
if [ -f setup_xonsh.sh ]; then
    echo "[Entrypoint] Running setup_xonsh.sh..."
    bash setup_xonsh.sh || true
fi
if [ -f setup_duo.sh ]; then
    echo "[Entrypoint] Running setup_duo.sh..."
    bash setup_duo.sh || true
fi

# Auto-detect what to run based on env or args
if [ "$OMNITIDE_MODE" = "cli" ]; then
    echo "[Entrypoint] Launching Omnitide CLI menu..."
    cd omnitide-vscode-bridge && exec python3 main.py
elif [ "$OMNITIDE_MODE" = "backend" ]; then
    echo "[Entrypoint] Launching backend (start_nexus.py)..."
    exec python3 start_nexus.py
elif [ "$OMNITIDE_MODE" = "agent" ] && [ -n "$OMNITIDE_AGENT" ]; then
    echo "[Entrypoint] Launching agent: $OMNITIDE_AGENT..."
    exec python3 "$OMNITIDE_AGENT"
elif [ $# -gt 0 ]; then
    echo "[Entrypoint] Executing custom command: $@"
    exec "$@"
else
    echo "[Entrypoint] No mode specified. Launching CLI menu by default."
    cd omnitide-vscode-bridge && exec python3 main.py
fi
