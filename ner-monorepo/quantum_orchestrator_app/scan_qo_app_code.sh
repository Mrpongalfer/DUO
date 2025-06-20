#!/bin/bash

# Script to gather current state of Quantum Orchestrator App code
# Run from within the application's root directory (e.g., ~/Projects/quantum_orchestrator_app)

echo "### Quantum Orchestrator Code Scan Initializing ###"
echo "Timestamp: $(date)"
echo "Scan Location: $(pwd)"
echo "========================================="
echo

# --- Git Status (if applicable) ---
echo "### Git Status ###"
if [ -d ".git" ]; then
    git status
    echo "----- Last Commit -----"
    git log -n 1 --oneline --decorate
else
    echo "# Not currently a Git repository."
fi
echo "========================================="
echo

# --- Basic Structure ---
echo "### Directory Listing (Detailed Root) ###"
ls -la .
echo
echo "### Directory Tree Structure (Max Depth 3) ###"
if command -v tree &>/dev/null; then
    tree -L 3 . # Show 3 levels deep
else
    echo "'tree' command not found. Using 'find':"
    find . -print | sed -e 's;[^/]*/;|____;g;s;____|; |;g'
fi
echo "========================================="
echo

# --- Key Files Content (Focus on Block 1) ---
echo "### Key File Contents ###"

# Helper function
cat_or_missing() {
    local filepath="$1"
    local filename=$(basename "$filepath")
    echo "----- Content of: $filepath -----"
    if [ -f "$filepath" ]; then
        # Add line numbers for easier reference
        nl -ba "$filepath"
    elif [ -d "$filepath" ]; then
        echo "# ERROR: Path exists but is a directory: $filepath"
    else
        echo "# File not found: $filepath"
    fi
    echo "--- End of: $filepath ---"
    echo
}

# Root Files
cat_or_missing "main.py"
cat_or_missing "run_api.py"
cat_or_missing "config.json"
cat_or_missing "instruction_schema.json"
cat_or_missing "pyproject.toml"
cat_or_missing "Dockerfile"
cat_or_missing "setup.py" # Check if it still exists/is relevant

# Core Modules (Block 1 Focus)
cat_or_missing "quantum_orchestrator/core/config.py"
cat_or_missing "quantum_orchestrator/core/agent.py"
cat_or_missing "quantum_orchestrator/core/state_manager.py"
cat_or_missing "quantum_orchestrator/core/instruction_parser.py"
cat_or_missing "quantum_orchestrator/core/self_verification.py" # Relevant to recent errors

# Handlers (Block 1 Focus)
cat_or_missing "quantum_orchestrator/handlers/file_operations.py"

# Utils (Block 1 Focus)
cat_or_missing "quantum_orchestrator/utils/logging_utils.py"
cat_or_missing "quantum_orchestrator/utils/error_utils.py"

echo "========================================="
echo
echo "### Quantum Orchestrator Code Scan Complete ###"
echo "Provide the *entire* output above."
