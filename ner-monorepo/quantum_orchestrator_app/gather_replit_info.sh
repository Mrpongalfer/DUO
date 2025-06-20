#!/bin/bash

# Script to gather info about a project migrated from Replit
# Run from within the project's root directory.

echo "### Replit Project Scan Initializing ###"
echo "Timestamp: $(date)"
echo "Scan Location: $(pwd)"
echo "========================================="
echo

# --- Basic Structure ---
echo "### Directory Listing (Detailed) ###"
ls -la
echo
echo "### Directory Tree Structure (Max Depth 3) ###"
if command -v tree &>/dev/null; then
    tree -L 5 .
else
    echo "'tree' command not found. Using 'find':"
    find . -print | sed -e 's;[^/]*/;|____;g;s;____|; |;g'
fi
echo "========================================="
echo

# --- Dependency Files ---
echo "### Dependency File Contents ###"
cat_or_missing() {
    local filepath="$1"
    local filename=$(basename "$filepath")
    echo "----- Content of: $filename -----"
    if [ -f "$filepath" ]; then
        cat "$filepath"
    else
        echo "# File not found: $filepath"
    fi
    echo "--- End of: $filename ---"
    echo
}

cat_or_missing "requirements.txt"
cat_or_missing "pyproject.toml"
cat_or_missing "package.json"
cat_or_missing "go.mod"
cat_or_missing "Gemfile"
# Add other common dependency files if needed

echo "========================================="
echo

# --- Configuration Files ---
echo "### Replit / Config File Contents ###"
cat_or_missing ".replit"
cat_or_missing "replit.nix"
cat_or_missing "Dockerfile" # Check if one already exists
cat_or_missing ".env"
cat_or_missing "config.py"
cat_or_missing "config.json"
cat_or_missing "settings.py"
cat_or_missing "Procfile"
echo "========================================="
echo

# --- Potential Entrypoints ---
echo "### Potential Entrypoint Files ###"
find . -maxdepth 1 -name 'main.py' -o -name 'app.py' -o -name 'index.js' -o -name 'server.js' -o -name 'main.go' -print 2>/dev/null || echo "# No common entrypoint files found in root."
echo "--- Check package.json 'scripts->start' or .replit 'run' command above ---"
echo "========================================="
echo

# --- Language Detection (Basic) ---
echo "### Detected File Extensions (Top 5) ###"
find . -type f | sed -n 's/.*\.\([a-zA-Z0-9]*\)$/\1/p' | grep -v '/' | sort | uniq -c | sort -nr | head -n 5 || echo "# Could not determine file extensions."
echo "========================================="
echo

echo "### Replit Project Scan Complete ###"
echo "Provide the *entire* output above."
