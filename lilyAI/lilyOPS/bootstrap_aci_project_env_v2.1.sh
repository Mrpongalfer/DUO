#!/bin/bash
#
# ACI Project Environment Bootstrap Script v2.1
# Designed by: Lily AI (Apex Developer Persona) for The Architect
# Purpose: Automates initial setup of the ACI v2.0 dev environment IN THE CURRENT DIRECTORY.
# Target OS: Pop!_OS (and other Debian/Ubuntu-based Linux distributions)
# Shell: Bash (should be compatible with Xonsh execution)

set -e # Exit immediately if a command exits with a non-zero status.

# --- Helper Functions ---
print_success() { echo -e "\033[0;32m[SUCCESS]\033[0m $1"; }
print_info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
print_warning() { echo -e "\033[0;33m[WARNING]\033[0m $1"; }
print_error() { echo -e "\033[0;31m[ERROR]\033[0m $1" >&2; }

# --- Configuration ---
PROJECT_ROOT_NAME=$(basename "$(pwd)") # Use current directory name
PYTHON_VERSION_TARGET="3.9" # Or your preferred Python 3.9+
VENV_NAME=".venv_aci" # Standardized venv name (ACI-specific to avoid conflicts)

print_info "ACI VS Code Environment Setup (v2.1) Initiated in: $(pwd)"
echo "---------------------------------------------------------------------------------"

# --- Pre-flight Checks ---
print_info "Performing pre-flight checks..."
if ! command -v git &> /dev/null; then print_error "Git not installed. Please install Git and re-run."; exit 1; fi; print_info "Git found."
PYTHON_CMD=$(command -v python3 || command -v python || { print_error "Python not found. Please install Python ${PYTHON_VERSION_TARGET}+ and re-run."; exit 1; }) ; print_info "Python found at $PYTHON_CMD."
if ! command -v uv &> /dev/null; then
    print_warning "'uv' command not found. This script relies on 'uv' for venv creation and package installation."
    print_warning "Please install 'uv' (e.g., 'pipx install uv' or 'cargo install uv' or 'pip install uv') and ensure it's in your PATH."
    exit 1
fi; print_info "'uv' found."
VSCODE_CLI_AVAILABLE=true; if ! command -v code &> /dev/null; then print_warning "VS Code 'code' CLI not found. Extension install will be skipped."; VSCODE_CLI_AVAILABLE=false; else print_info "VS Code 'code' command found."; fi

# --- 1. Git Initialization (Only if not already a Git repo) ---
if [ -d ".git" ]; then
    print_info "Current directory is already a Git repository."
else
    print_info "Initializing Git repository in current directory..."
    git init
    git branch -m main # Ensure default branch is 'main'
    print_success "Git repository initialized."
fi

# --- 2. Python Virtual Environment using uv ---
print_info "Setting up Python virtual environment '$VENV_NAME' using 'uv'..."
if [ -d "$VENV_NAME" ]; then
    print_info "Virtual environment '$VENV_NAME' already exists. Attempting to ensure it's usable..."
    # Ensure the Python version within is accessible, uv venv will create if incompatible or missing.
    uv venv "$VENV_NAME" -p "$PYTHON_CMD" --seed || { print_error "Failed to ensure/create virtual environment '$VENV_NAME' with 'uv'."; exit 1; }
    print_success "Virtual environment '$VENV_NAME' ensured/updated."
else
    uv venv "$VENV_NAME" -p "$PYTHON_CMD" --seed || { print_error "Failed to create virtual environment '$VENV_NAME' with 'uv'."; exit 1; }
    print_success "Virtual environment '$VENV_NAME' created."
fi
VENV_PYTHON_PATH="$(pwd)/$VENV_NAME/bin/python"
VENV_BIN_PATH="$(pwd)/$VENV_NAME/bin"

# --- 3. .gitignore Creation/Update ---
print_info "Creating/Updating .gitignore..."
# (Content from previous script version - it's comprehensive)
cat > .gitignore << EOF
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
*.out
*.prof
*.prof.json
*.lprof
*.prof.gz
*.py,cover
*.coverage
.coverage
.coverage.*
htmlcov/
MANIFEST
*.manifest
*.spec

# Virtual Environments
${VENV_NAME}/
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE / Editor
.vscode/*
!.vscode/settings.json
!.vscode/tasks.json
!.vscode/launch.json
!.vscode/extensions.json
.idea/
*.swp
*.swo

# Build artifacts
build/
dist/
sdist/
*.tar.gz
*.zip

# Coverage & Test Caches
.pytest_cache/
.ruff_cache/
.mypy_cache/

# OS-specific
.DS_Store
Thumbs.db
ehthumbs.db
Desktop.ini

# Logs & ACI Data (Local Only)
*.log
logs/
aci_mvp_config.ini
aci_main.db
aci_main.db-shm
aci_main.db-wal
# Path for local Git clone cache if EESRS uses one for RAG (should be outside project or here if small)
# Ensure this matches ACLS/EESRS config if it's within the project structure
# For now, assuming these are outside the lilyOPS_ACI_Project Git repo itself:
# local_git_repo_clone_path/
# eesrs_rag_index/

# Secrets (ALWAYS IGNORE - these are examples, actual secrets should never be versioned)
secrets/
*.env.*
*.pem
*.key
*.credential*
*token*
*secret*
EOF
print_success ".gitignore created/updated."


# --- 4. pyproject.toml Initialization ---
print_info "Ensuring pyproject.toml exists and has basic ACI/Ruff config..."
if [ ! -f "pyproject.toml" ]; then
    cat > pyproject.toml << EOF
[project]
name = "${PROJECT_ROOT_NAME}" # Uses current folder name
version = "0.1.0-mvp"
description = "Architect's Command Interface - Co-developed with Lily AI & The Architect."
authors = [
    {name = "The Architect (mrpongalfer)", email = "architect@example.com"}, # Placeholder
]
readme = "README.md"
requires-python = ">=${PYTHON_VERSION_TARGET}"
dependencies = [
    # To be populated by Lily AI's SDSS for each module, e.g.:
    # "textual>=0.50.0",
    # "aiohttp>=3.8.0",
    # "keyring",
    # "cryptography",
    # "ollama",
    # "PyGithub"
]

[project.scripts]
# Example: aci = "aci_v2.main_aci_runner_mvp:main"

[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E","F","W","I","UP","B","C4","SIM","TID","PT","Q","N","ANN","ASYNC","TRY"] # Comprehensive set
ignore = [
    "ANN101", # Missing type annotation for self
    "ANN102", # Missing type annotation for cls
    "E501",   # Line too long (Ruff formatter will handle this)
]
# fixable = ["ALL"] # Uncomment for very aggressive auto-fixing by 'ruff --fix'

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-string-normalization = false
line-ending = "lf"

# Placeholder for PDM dev dependencies if Architect chooses to use 'pdm install --dev'
# [tool.pdm.dev-dependencies]
# dev = [
#     "ruff",
#     "pytest",
#     "pre-commit"
# ]
EOF
    print_success "pyproject.toml created with basic structure and Ruff config."
else
    print_info "pyproject.toml already exists. Please ensure Ruff and other tool configurations are aligned with the above if necessary."
fi

# --- 5. VS Code Specific Setup ---
print_info "Creating/Updating VS Code project settings..."
mkdir -p ".vscode"

# settings.json
cat > ".vscode/settings.json" << EOF
{
    "python.analysis.typeCheckingMode": "strict",
    "python.analysis.autoImportCompletions": true,
    "python.terminal.activateEnvInCurrentTerminal": true,
    "python.defaultInterpreterPath": "${VENV_PYTHON_PATH}",

    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.fixAll": true,
            "source.organizeImports": true
        },
        "editor.rulers": [100, 120]
    },
    "ruff.enable": true,
    "ruff.lint.run": "onSave",
    "ruff.interpreter": ["${VENV_PYTHON_PATH}"],

    "files.eol": "\n",
    "files.insertFinalNewline": true,
    "files.trimFinalNewlines": true,
    "files.trimTrailingWhitespace": true,
    "editor.minimap.enabled": false,
    "workbench.editor.labelFormat": "short",
    "search.exclude": {
        "**/${VENV_NAME}": true,
        "**/.pytest_cache": true,
        "**/.ruff_cache": true,
        "**/__pycache__": true,
        "**/*.egg-info": true,
        "**/dist": true,
        "**/build": true,
        "**/.git": true
    },
    "better-comments.tags": [
        { "tag": "!", "color": "#FF2D00", "strikethrough": false, "backgroundColor": "transparent", "bold": true },
        { "tag": "?", "color": "#3498DB", "strikethrough": false, "backgroundColor": "transparent", "bold": false },
        { "tag": "//", "color": "#474747", "strikethrough": true, "backgroundColor": "transparent" },
        { "tag": "todo", "color": "#FF8C00", "strikethrough": false, "backgroundColor": "transparent" },
        { "tag": "*", "color": "#98C379", "strikethrough": false, "backgroundColor": "transparent" },
        { "tag": "CRITICAL:", "color": "#DC143C", "strikethrough": false, "backgroundColor": "transparent", "bold": true, "italic": true },
        { "tag": "ARCHITECT_ACTION:", "color": "#8A2BE2", "strikethrough": false, "backgroundColor": "transparent", "bold": true },
        { "tag": "NOTE:", "color": "#20B2AA", "strikethrough": false, "backgroundColor": "transparent", "italic": true },
        { "tag": "INFO:", "color": "#4682B4", "strikethrough": false, "backgroundColor": "transparent" },
        { "tag": "AGENT_ACTION:", "color": "#DAA520", "strikethrough": false, "backgroundColor": "transparent", "bold": true}
    ],
    "github.copilot.enable": {
        "*": true, "plaintext": true, "markdown": true, "python": true
    },
    "editor.inlineSuggest.enabled": true
}
EOF
print_success ".vscode/settings.json created/updated."

# extensions.json
cat > ".vscode/extensions.json" << EOF
{
    "recommendations": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "charliermarsh.ruff",
        "eamodio.gitlens",
        "streetsidesoftware.code-spell-checker",
        "aaron-bond.better-comments",
        "nils-werner.autodocstring",
        "rangav.vscode-thunder-client",
        "github.copilot",
        "github.copilot-chat"
    ]
}
EOF
print_success ".vscode/extensions.json created with recommendations."

if [ "$VSCODE_CLI_AVAILABLE" = true ] ; then
    print_info "Attempting to install/verify recommended VS Code extensions..."
    EXTENSIONS=(
        "ms-python.python" "ms-python.vscode-pylance" "charliermarsh.ruff"
        "eamodio.gitlens" "streetsidesoftware.code-spell-checker" "aaron-bond.better-comments"
        "nils-werner.autodocstring" "rangav.vscode-thunder-client"
        "github.copilot" "github.copilot-chat"
    )
    for ext_id in "${EXTENSIONS[@]}"; do
        print_info "   Processing extension: $ext_id"
        if ! code --install-extension "$ext_id" --force; then
            print_warning "   Attempt to install/update $ext_id failed. This might be due to network issues, the extension already being managed by VS Code Sync, or other VS Code CLI errors. Please verify manually in VS Code."
        fi
    done
    print_info "VS Code extension processing attempted. Please check VS Code for final status and ensure you are logged into GitHub Copilot."
else
    print_warning "VS Code 'code' command not available. Skipping automatic extension installation."
    print_info "Please install recommended extensions from '.vscode/extensions.json' manually within VS Code."
fi

# --- 6. Install Core Dev Dependencies into Virtual Environment using uv ---
print_info "Installing core development tools (ruff, pdm, pre-commit) into '$VENV_NAME' using 'uv'..."
# uv needs to be called directly. If venv is active, it installs into it.
# If venv is NOT active, uv needs to be told WHERE to install.
# The safest way is to use the venv's python to call uv's pip module, or use `uv pip install --python ...`
# The script previously failed here. Corrected approach:
if [ -f "$VENV_PYTHON_PATH" ]; then
    "$VENV_PYTHON_PATH" -m pip install uv # Ensure uv is available to this venv's pip if needed, or rely on global uv
    # Then use the venv's uv if it got installed, or global uv targeting this venv
    # The most robust way for this script is to use the global 'uv' and specify the venv path
    uv pip install --python "$VENV_PYTHON_PATH" ruff "pdm>=2.10" pre-commit || {
        print_error "Failed to install core dev tools (ruff, pdm, pre-commit) into virtual environment '$VENV_NAME'."
        print_info "Please activate the venv ('source $VENV_NAME/bin/activate') and try manually: uv pip install ruff pdm pre-commit"
    }
    print_success "Core dev tools (ruff, pdm, pre-commit) installation into virtual environment attempted."
else
    print_error "Virtual environment Python not found at '$VENV_PYTHON_PATH'. Cannot install dev tools into venv."
fi


# --- 7. pre-commit Setup ---
print_info "Setting up pre-commit..."
if [ ! -f ".pre-commit-config.yaml" ]; then
    cat > ".pre-commit-config.yaml" << EOF
# See https://pre-commit.com for more information
# See https://pre-commit.com/hooks.html for more hooks
repos:
-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0 # Use a recent stable version
    hooks:
    -   id: trailing-whitespace
    -   id: end-of-file-fixer
    -   id: check-yaml
    -   id: check-json
    -   id: check-toml
-   repo: https://github.com/astral-sh/ruff-pre-commit
    rev: 'v0.4.4' # Replace with desired stable Ruff version
    hooks:
    -   id: ruff
        args: [--fix, --exit-non-zero-on-fix]
    -   id: ruff-format
EOF
    print_info ".pre-commit-config.yaml created."
else
    print_info ".pre-commit-config.yaml already exists. Ensure it's configured for Ruff."
fi

# Install pre-commit hooks into .git/hooks, using the venv's pre-commit
print_info "Attempting to install pre-commit git hooks..."
if [ -f "$VENV_BIN_PATH/pre-commit" ]; then
    "$VENV_BIN_PATH/pre-commit" install || {
        print_warning "Failed to install pre-commit hooks using venv's pre-commit. You might need to activate the venv ('source $VENV_NAME/bin/activate') and run 'pre-commit install' manually."
    }
    print_success "Pre-commit hooks installation attempted."
elif command -v pre-commit &> /dev/null; then # Fallback to global if venv one not directly callable this way
    print_warning "Using global pre-commit as venv path wasn't directly callable. Ensure venv is active in your working shell for 'pre-commit install'."
    pre-commit install || print_warning "Global pre-commit install attempt also failed/warned."
else
    print_warning "Virtual environment or global 'pre-commit' not found. Skipping pre-commit hook installation. Please run 'source $VENV_NAME/bin/activate' then 'uv pip install pre-commit' then 'pre-commit install'."
fi


# --- Final Instructions ---
echo ""
echo "---------------------------------------------------------------------------------"
echo -e "\033[1;32mACI Project Environment Bootstrap (v2.1) COMPLETED in: $(pwd)!\033[0m"
echo "---------------------------------------------------------------------------------"
echo -e "\033[1;33mARCHITECT - CRITICAL NEXT STEPS:\033[0m"
echo "1. \033[1mMANUALLY VERIFY SCRIPT OUTPUT:\033[0m Please check for any WARNINGS or ERRORS above."
echo "2. \033[1mRESTART VS CODE:\033[0m If VS Code was open in this directory, close and reopen it to ensure all settings, the Python interpreter for '${VENV_NAME}', and extensions are fully loaded correctly."
echo "3. \033[1mACTIVATE THE PYTHON VIRTUAL ENVIRONMENT\033[0m in your Xonsh/Bash terminal if you haven't already:"
echo "   \033[0;32msource \"${VENV_NAME}/bin/activate\"\033[0m (or equivalent for your specific shell if not Bash-like for Xonsh activation)"
echo "4. \033[1mVERIFY DEV TOOL INSTALLATION IN VENV:\033[0m Inside the activated venv, confirm tools are present:"
echo "   \033[0;32mwhich ruff\033[0m (should point to the path inside '${VENV_NAME}')"
echo "   \033[0;32mwhich pdm\033[0m (should point to path inside '${VENV_NAME}')"
echo "   \033[0;32mwhich pre-commit\033[0m (should point to path inside '${VENV_NAME}')"
echo "   If they still point to global paths (e.g., ~/.local/bin/), your shell's PATH order might prioritize global pipx shims over an active venv's bin for these specific tools. PDM via 'pdm run <tool>' usually correctly uses project-local versions."
echo "5. \033[1mDEPENDENCY MANAGEMENT (PDM Highly Recommended):\033[0m"
echo "   - If you haven't initialized PDM for this project (and pyproject.toml is basic):"
echo "     \033[0;32mpdm init\033[0m (Follow prompts to customize pyproject.toml further if needed. It will detect the venv created by uv)."
echo "   - Add dev tools to PDM if not already managed (ensures PDM knows about them for 'pdm run'):"
echo "     \033[0;32mpdm add -d ruff pre-commit\033[0m"
echo "   - Install all project dependencies (once Lily starts specifying them in SDSS for modules):"
echo "     \033[0;32mpdm install\033[0m"
echo "6. \033[1mPRE-COMMIT HOOKS:\033[0m If 'pre-commit install' in the script showed warnings, ensure you run it successfully from an activated venv: \033[0;32mpdm run pre-commit install\033[0m or \033[0;32mpre-commit install\033[0m."
echo "7. \033[1mINITIAL GIT COMMIT (If you are satisfied with the setup):\033[0m"
echo "   \033[0;32mgit add .gitignore pyproject.toml .vscode/ .pre-commit-config.yaml\033[0m"
echo "   \033[0;32mgit commit -m \"feat: Initial ACI project environment setup (Python venv, VSCode, Ruff, pre-commit)\"\033[0m"
echo "8. \033[1mCONFIGURE GITHUB REMOTE (If not done yet for 'lilyOPS'):\033[0m"
echo "   (Assuming 'lilyOPS' is the desired remote repository name on GitHub under 'mrpongalfer')"
echo "   \033[0;32mgit remote add origin https://github.com/mrpongalfer/lilyOPS.git\033[0m (If it's a new local repo to push to an existing empty remote or new remote)"
echo "   \033[0;32mgit push -u origin main\033[0m (For the first push to set upstream)"
echo "9. \033[1mENSURE GITHUB COPILOT IS SIGNED IN\033[0m within VS Code and functioning."
echo "---------------------------------------------------------------------------------"
echo -e "\033[1mYour development environment foundation is now laid, Architect. This is the 'Apex Dev's streamlined pipeline.'\033[0m"
