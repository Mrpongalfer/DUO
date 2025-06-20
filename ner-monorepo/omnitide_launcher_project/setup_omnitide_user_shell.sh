#!/bin/bash
# setup_omnitide_user_shell.sh - Interactively sets up user's Xonsh environment for Omnitide CLI development.
# Run AS THE REGULAR USER (e.g., pong), NOT with sudo.

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration & Helper Functions ---
PYTHON_CMD="python3.11" # Primary Python for user-level tools
SCRIPT_VERSION="2.2_interactive"
OMNITIDE_PROJECT_DIR_NAME="omnitide_launcher_project" # Used for guidance

# Function to prompt for yes/no
prompt_yes_no() {
    while true; do
        read -r -p "$1 [Y/n]: " response
        response=${response,,} # tolower
        if [[ "$response" =~ ^(yes|y|"")$ ]]; then
            REPLY="yes"
            return 0
        elif [[ "$response" =~ ^(no|n)$ ]]; then
            REPLY="no"
            return 0
        else
            echo "Invalid input. Please enter 'yes' or 'no'."
        fi
    done
}

echo "--- Omnitide Interactive User Shell Setup Utility (v${SCRIPT_VERSION}) ---"
echo "This script will guide you through setting up Xonsh, essential tools,"
echo "and prepare your environment for the Omnitide CLI project."
echo "--------------------------------------------------------------------"

# --- 0. Pre-flight Checks ---
echo "[Phase 0/8] Performing pre-flight system checks..."
CAN_PROCEED=true
if ! command -v "$PYTHON_CMD" &> /dev/null; then
    echo "[FATAL_ERROR] ${PYTHON_CMD} could not be found. This script requires Python 3.11."
    echo "Please install Python 3.11, ensure it's in your PATH as '${PYTHON_CMD}', and re-run."
    CAN_PROCEED=false
fi
if ! command -v "curl" &> /dev/null; then
    echo "[FATAL_ERROR] 'curl' could not be found. It's required for some installations (e.g., x-cmd)."
    echo "Please install curl (e.g., 'sudo apt update && sudo apt install curl') and re-run."
    CAN_PROCEED=false
fi
if ! command -v "git" &> /dev/null; then
    echo "[WARNING] 'git' command not found. While not strictly fatal for this script,"
    echo "           git is essential for most development workflows and some xontrib features."
    echo "           It is highly recommended to install git (e.g., 'sudo apt install git')."
fi

if ! $CAN_PROCEED; then
    echo "Pre-flight checks failed. Please address the FATAL_ERROR messages above."
    exit 1
fi
echo "[OK] Basic pre-flight checks passed."
echo "--------------------------------------------------------------------"

# --- 1. Clean Up Old Configs (Interactive) ---
echo "[Phase 1/8] Optional: Clean up previous Xonsh/X-cmd user configurations."
prompt_yes_no "Do you want to attempt to remove existing user-level Xonsh/x-cmd configurations for a cleaner setup? (Recommended if you face issues or want a fresh start. This will remove ~/.xonshrc, ~/.config/xonsh, etc.)"
if [[ "$REPLY" == "yes" ]]; then
    echo "  Proceeding with cleanup..."
    rm -rf ~/.xonshrc ~/.config/xonsh ~/.local/share/xonsh ~/.cache/xonsh ~/.x-cmd.root
    echo "  Removed common Xonsh/X-cmd user config locations."
    echo "  [INFO] If you previously integrated Xonsh with other shells (.bashrc, .profile, .zshrc),"
    echo "         manual review of those files for leftover sourcing lines is recommended."
else
    echo "  Skipping cleanup of existing Xonsh/X-cmd configs."
fi
echo "[OK] Cleanup phase decision processed."
echo "--------------------------------------------------------------------"

# --- 2. Install/Upgrade Core Python Tools for User (pip, virtualenv) ---
echo "[Phase 2/8] Ensuring core Python tools (pip, virtualenv) are installed/upgraded for ${PYTHON_CMD}..."
echo "This will use '${PYTHON_CMD} -m pip install --user --upgrade pip virtualenv'."
prompt_yes_no "Proceed with checking/installing/upgrading pip and virtualenv for your user account?"
if [[ "$REPLY" == "yes" ]]; then
    "$PYTHON_CMD" -m ensurepip --upgrade || echo "[WARNING] '${PYTHON_CMD} -m ensurepip --upgrade' reported an issue. This might be okay if pip is already functional."
    if "$PYTHON_CMD" -m pip install --user --upgrade pip virtualenv; then
        echo "[OK] pip and virtualenv checked/installed/upgraded successfully for ${PYTHON_CMD}."
    else
        echo "[ERROR] Failed to install/upgrade pip or virtualenv using ${PYTHON_CMD}."
        echo "         Please check your Python installation and pip. You can try running manually:"
        echo "         ${PYTHON_CMD} -m pip install --user --upgrade pip virtualenv"
        prompt_yes_no "Continue despite this error (not recommended unless pip/virtualenv are known to be working)?"
        [[ "$REPLY" == "no" ]] && exit 1
    fi
else
    echo "  Skipping pip/virtualenv check/update. Ensure they are functional for ${PYTHON_CMD}."
fi
echo "--------------------------------------------------------------------"

# --- 3. Install/Upgrade Xonsh ---
echo "[Phase 3/8] Xonsh Shell Installation/Upgrade."
XONSH_USER_BIN="${HOME}/.local/bin/xonsh"
XONSH_INSTALLED=false
if command -v xonsh &>/dev/null || [ -f "$XONSH_USER_BIN" ]; then
    XONSH_INSTALLED=true
    echo "  Xonsh appears to be already installed."
    prompt_yes_no "Do you want to attempt to upgrade it using '${PYTHON_CMD} -m pip install --user --upgrade \"xonsh[full]\"'?"
    if [[ "$REPLY" == "no" ]]; then
        echo "  Skipping Xonsh upgrade."
    else
        NEEDS_XONSH_INSTALL_OR_UPGRADE=true
    fi
else
    echo "  Xonsh not detected."
    prompt_yes_no "Do you want to install Xonsh for your user account using '${PYTHON_CMD} -m pip install --user --upgrade \"xonsh[full]\"'?"
    [[ "$REPLY" == "no" ]] && { echo "  Xonsh installation skipped. Cannot proceed with further Xonsh-specific setup."; exit 0; }
    NEEDS_XONSH_INSTALL_OR_UPGRADE=true
fi

if [[ "$NEEDS_XONSH_INSTALL_OR_UPGRADE" == "true" ]]; then
    if "$PYTHON_CMD" -m pip install --user --upgrade "xonsh[full]"; then
        echo "[OK] Xonsh installed/upgraded successfully."
        XONSH_INSTALLED=true
    else
        echo "[FATAL_ERROR] Failed to install/upgrade Xonsh. Please check pip output and Python environment."
        exit 1
    fi
fi

if $XONSH_INSTALLED && [[ ":$PATH:" != *":${HOME}/.local/bin:"* ]]; then
    echo "[IMPORTANT_WARNING] '${HOME}/.local/bin' is not found in your current PATH."
    echo "  Xonsh (and other user-installed Python tools) might not be directly callable."
    echo "  Please add 'export PATH=\"\$HOME/.local/bin:\$PATH\"' to your shell's main startup file"
    echo "  (e.g., ~/.bashrc, ~/.zshrc, ~/.profile), then source it or re-login/restart your terminal."
fi
echo "[OK] Xonsh installation/check complete."
echo "--------------------------------------------------------------------"

# --- 4. Install Xontribs ---
echo "[Phase 4/8] Xonsh Extensions (Xontribs) Setup."
XONTRIBS_TO_CONSIDER=("xontrib-direnv" "xontrib-fzf" "xontrib-up") # Core for good DX
XONTRIBS_TO_INSTALL=()

echo "The following xontribs are recommended for an enhanced Xonsh experience, especially with direnv for project environments:"
for XONTRIB in "${XONTRIBS_TO_CONSIDER[@]}"; do
    echo "  - ${XONTRIB}"
done
prompt_yes_no "Do you want to install/upgrade these recommended xontribs now?"
if [[ "$REPLY" == "yes" ]]; then
    # System dependency checks for xontribs
    if [[ " ${XONTRIBS_TO_CONSIDER[*]} " =~ " xontrib-fzf " ]]; then
        if ! command -v fzf &> /dev/null; then
            echo "[WARNING] 'fzf' command (system dependency for xontrib-fzf) not found."
            echo "           xontrib-fzf provides fuzzy finding capabilities in Xonsh."
            echo "           Please install 'fzf' system-wide (e.g., 'sudo apt install fzf') for this xontrib to work."
        fi
    fi
    if [[ " ${XONTRIBS_TO_CONSIDER[*]} " =~ " xontrib-direnv " ]]; then
        if ! command -v direnv &> /dev/null; then
            echo "[WARNING] 'direnv' command (system dependency for xontrib-direnv) not found."
            echo "           xontrib-direnv integrates direnv for automatic environment management."
            echo "           Please install 'direnv' system-wide (e.g., 'sudo apt install direnv') for this xontrib to work effectively."
        fi
    fi
    
    echo "  Installing/upgrading: ${XONTRIBS_TO_CONSIDER[*]}..."
    if "$PYTHON_CMD" -m pip install --user --upgrade "${XONTRIBS_TO_CONSIDER[@]}"; then
        echo "[OK] Recommended xontribs installed/upgraded."
        XONTRIBS_TO_INSTALL=("${XONTRIBS_TO_CONSIDER[@]}") # For .xonshrc generation
    else
        echo "[ERROR] Failed to install one or more xontribs. Check pip output."
        # Decide if this is fatal or warning
    fi
else
    echo "  Skipping installation of recommended xontribs."
fi
echo "[OK] Xontribs setup phase complete."
echo "--------------------------------------------------------------------"

# --- 5. Install x-cmd (Optional) ---
echo "[Phase 5/8] x-cmd Installation (Optional Tool)."
XCMD_EXE_PATH="${HOME}/.x-cmd.root/bin/x"
XCMD_INSTALLED=false
if [ -f "$XCMD_EXE_PATH" ]; then
    echo "  x-cmd appears to be already installed at ${XCMD_EXE_PATH}."
    XCMD_INSTALLED=true
    prompt_yes_no "Do you want to check for x-cmd updates ('${XCMD_EXE_PATH} update self')?"
    if [[ "$REPLY" == "yes" ]]; then
        if "$XCMD_EXE_PATH" update self; then echo "  x-cmd updated."; else echo "  x-cmd update command had issues or was already latest."; fi
    fi
else
    prompt_yes_no "x-cmd is a community-driven command-line tool. Do you want to install it now?"
    if [[ "$REPLY" == "yes" ]]; then
        if bash -c "$(curl -fsSL https://get.x-cmd.com)"; then
            echo "[OK] x-cmd installation script completed."
            if [ -f "$XCMD_EXE_PATH" ]; then XCMD_INSTALLED=true; else echo "[ERROR] x-cmd executable not found after install."; fi
        else
            echo "[ERROR] x-cmd installation script failed."
        fi
    else
        echo "  Skipping x-cmd installation."
    fi
fi
echo "[OK] x-cmd installation phase complete."
echo "--------------------------------------------------------------------"

# --- 6. Integrate x-cmd with Xonsh (If x-cmd installed) ---
echo "[Phase 6/8] x-cmd Xonsh Integration (if x-cmd is installed)."
if $XCMD_INSTALLED; then
    prompt_yes_no "Do you want to run 'x onsh --setup' to integrate x-cmd with your Xonsh configuration? (This modifies Xonsh config files for x-cmd features)"
    if [[ "$REPLY" == "yes" ]]; then
        if "$XCMD_EXE_PATH" onsh --setup; then
            echo "[OK] 'x onsh --setup' completed."
        else
            echo "[WARNING] 'x onsh --setup' command reported an issue. This might be okay if already set up."
            echo "           If x-cmd features don't work in Xonsh, you might need to run it manually or check x-cmd documentation."
        fi
    else
        echo "  Skipping 'x onsh --setup'."
    fi
else
    echo "  Skipping x-cmd Xonsh integration because x-cmd is not installed (or installation failed)."
fi
echo "[OK] x-cmd Xonsh integration phase complete."
echo "--------------------------------------------------------------------"

# --- 7. Create/Update .xonshrc ---
echo "[Phase 7/8] Generating/Updating ~/.xonshrc file..."
XONSHRC_CONTENT="# ~/.xonshrc (Omnitide CLI Dev v${SCRIPT_VERSION})\n"
XONSHRC_CONTENT+="# Interactively generated. Loads essential plugins.\n\n"
XONSHRC_CONTENT+="print(f\"INFO: Omnitide Dev .xonshrc v${SCRIPT_VERSION} loading...\")\n\n"

if [ ${#XONTRIBS_TO_INSTALL[@]} -gt 0 ]; then
    XONSHRC_CONTENT+="# Load selected xontribs\n"
    XONSHRC_CONTENT+="print(\"INFO: Loading selected xontribs...\")\n"
    for XONTRIB_NAME_RAW in "${XONTRIBS_TO_INSTALL[@]}"; do
        # xontrib names for loading don't have the 'xontrib-' prefix
        XONTRIB_LOAD_NAME=$(echo "$XONTRIB_NAME_RAW" | sed 's/^xontrib-//')
        XONSHRC_CONTENT+="try:\n"
        XONSHRC_CONTENT+="    xontrib load ${XONTRIB_LOAD_NAME}\n"
        XONSHRC_CONTENT+="    print(f\"  INFO: Loaded xontrib: ${XONTRIB_LOAD_NAME}\")\n"
        XONSHRC_CONTENT+="except Exception as e_xontrib:\n"
        XONSHRC_CONTENT+="    print(f\"  WARN: Could not load xontrib '${XONTRIB_LOAD_NAME}': {{e_xontrib}}\")\n"
    done
    XONSHRC_CONTENT+="\n"
fi

XONSHRC_CONTENT+="# Optional: Powerline prompt (uncomment to try if 'xontrib-powerline' or similar is installed)\n"
XONSHRC_CONTENT+="# print(\"INFO: Attempting to load powerline prompt (optional)...\")\n"
XONSHRC_CONTENT+="# try:\n"
XONSHRC_CONTENT+="#     xontrib load powerline\n"
XONSHRC_CONTENT+="#     \$PROMPT = \$POWERLINE_PROMPT\n"
XONSHRC_CONTENT+="#     print(\"  INFO: Powerline prompt loaded.\")\n"
XONSHRC_CONTENT+="# except Exception as e_powerline:\n"
XONSHRC_CONTENT+="#     print(f\"  WARN: Could not load powerline xontrib: {{e_powerline}}\")\n\n"

XONSHRC_CONTENT+="# Note: x-cmd integration is typically handled by files in ~/.config/xonsh/ (e.g., rc.xsh)\n"
XONSHRC_CONTENT+="# created by 'x onsh --setup'.\n\n"

XONSHRC_CONTENT+="# Ensure prompt updates after all configurations\n"
XONSHRC_CONTENT+="if hasattr(builtins, 'update_prompt') and callable(builtins.update_prompt):\n"
XONSHRC_CONTENT+="    print(\"INFO: Requesting final prompt update...\")\n"
XONSHRC_CONTENT+="    update_prompt()\n\n"

XONSHRC_CONTENT+="print(f\"INFO: Omnitide Dev .xonshrc v${SCRIPT_VERSION} loading complete.\")\n"

echo -e "${XONSHRC_CONTENT}" > ~/.xonshrc
echo "[OK] ~/.xonshrc created/updated."
echo "--------------------------------------------------------------------"

# --- 8. Guidance for Omnitide CLI Project Setup ---
echo "[Phase 8/8] Guidance for Omnitide CLI Project Setup (using direnv)."
echo ""
echo "Your user-level Xonsh environment should now be substantially configured."
echo "For the '${OMNITIDE_PROJECT_DIR_NAME}' (or your specific project):"
echo ""
echo "  FIRST-TIME XONSH+DIRENV SETUP (run these commands *inside* Xonsh shell):"
echo "  1. If you haven't already, enable the direnv hook for Xonsh:"
echo "     (This only needs to be done once per user & Xonsh installation)"
echo "     XONSH> execx(\$(direnv hook xonsh), 'exec')"
echo "  2. After running the hook, it's best to RESTART XONSH (exit and type 'xonsh' again)."
echo ""
echo "  PROJECT-SPECIFIC ENVIRONMENT (using direnv):"
echo "  3. Navigate to your project directory (e.g., 'cd /path/to/${OMNITIDE_PROJECT_DIR_NAME}')."
echo "  4. Create or ensure an '.envrc' file exists in that project root with content like this:"
echo "     ----------------------------------------------------"
echo "     # .envrc for ${OMNITIDE_PROJECT_DIR_NAME}"
echo "     layout python ${PYTHON_CMD}  # Or your preferred project Python version"
echo "     export OMNITIDE_PROJECT_ROOT=\$(pwd)"
echo "     # You can add other project-specific environment variables here."
echo "     # Example: export OLLAMA_HOST=\"http://localhost:11434\""
echo "     ----------------------------------------------------"
echo "  5. In the project directory (still in Xonsh), run: direnv allow ."
echo "     This will create a Python virtual environment (e.g., in .direnv/python-${PYTHON_CMD}) "
echo "     and activate it whenever you 'cd' into this directory."
echo "  6. With the direnv environment active, install the project's Python dependencies:"
echo "     XONSH (${OMNITIDE_PROJECT_DIR_NAME})> pip install -r requirements_omnitide_cli.txt"
echo "     (Ensure 'requirements_omnitide_cli.txt' is in your project directory with the correct content)."
echo ""
echo "  7. Your Omnitide CLI toolkit should now be ready to use from within this project directory!"
echo "     Try: XONSH (${OMNITIDE_PROJECT_DIR_NAME})> python omnitide_cli.py --help"
echo ""
echo "--- Omnitide Interactive User Shell Setup Finished ---"
exit 0
