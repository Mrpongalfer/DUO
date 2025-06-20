#!/bin/bash
# setup_omnitide_user_shell.sh - Interactively sets up user's Xonsh environment for Omnitide CLI development.
# Version: 2.3_interactive_plus
# Run AS THE REGULAR USER (e.g., pong), NOT with sudo.

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration & Helper Functions ---
PYTHON_CMD_DEFAULT="python3.11" # Primary Python for user-level tools
SCRIPT_VERSION="2.3_interactive_plus"
OMNITIDE_PROJECT_DIR_NAME_DEFAULT="omnitide_launcher_project" # Used for guidance
REQUIREMENTS_FILE_NAME="requirements_omnitide_cli.txt" # Project requirements file

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

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

echo "--- Omnitide Interactive User Shell Setup Utility (v${SCRIPT_VERSION}) ---"
echo "This script will guide you through setting up Xonsh, essential tools,"
echo "and assist with preparing your environment for an Omnitide CLI project."
echo "--------------------------------------------------------------------"

# --- 0. Pre-flight Checks & Python Command Configuration ---
echo "[Phase 0/9] Performing pre-flight system checks and Python setup..."
PYTHON_CMD=""
prompt_yes_no "This script will use a Python interpreter (preferably 3.11+) for installing user-level packages like Xonsh. Do you want to specify the Python command now (e.g., python3.11, python3), or use the default '${PYTHON_CMD_DEFAULT}'?"
if [[ "$REPLY" == "yes" ]]; then
    read -r -p "Enter the Python command to use (e.g., python3.11): " PYTHON_CMD_INPUT
    PYTHON_CMD=${PYTHON_CMD_INPUT:-$PYTHON_CMD_DEFAULT}
else
    PYTHON_CMD=$PYTHON_CMD_DEFAULT
fi
echo "  Using Python command: '${PYTHON_CMD}'"

CAN_PROCEED=true
if ! command_exists "$PYTHON_CMD"; then
    echo -e "${RED}FATAL_ERROR: Python command '${PYTHON_CMD}' could not be found. This script requires a working Python (preferably 3.11+).${NC}"
    echo "Please install Python, ensure it's in your PATH with the specified command name, and re-run."
    CAN_PROCEED=false
fi
if ! command_exists "curl"; then
    echo -e "${RED}FATAL_ERROR: 'curl' could not be found. It's required for some installations (e.g., x-cmd).${NC}"
    echo "Please install curl (e.g., 'sudo apt update && sudo apt install curl') and re-run."
    CAN_PROCEED=false
fi
if ! command_exists "git"; then
    echo -e "${YELLOW}WARNING: 'git' command not found. While not strictly fatal for this script,"
    echo "           git is essential for most development workflows and some xontrib features.${NC}"
    prompt_yes_no "It is highly recommended to install git. Would you like to attempt to install it now using 'sudo apt install git' (requires sudo privileges)?"
    if [[ "$REPLY" == "yes" ]]; then
        if sudo apt update && sudo apt install -y git; then
            echo "  Git installed successfully."
        else
            echo -e "  ${RED}ERROR: Git installation failed. Please install it manually.${NC}"
        fi
    fi
fi

if ! $CAN_PROCEED; then
    echo "Pre-flight checks failed. Please address the FATAL_ERROR messages above."
    exit 1
fi
echo "[OK] Basic pre-flight checks passed."
echo "--------------------------------------------------------------------"

# --- 1. Clean Up Old Configs (Interactive) ---
echo "[Phase 1/9] Optional: Clean up previous Xonsh/X-cmd user configurations."
prompt_yes_no "Do you want to attempt to REMOVE existing user-level Xonsh/x-cmd configurations? (Select 'yes' for a fresh start, 'no' to keep existing configs. ${RED}THIS IS DESTRUCTIVE if you have custom setups you want to keep.${NC})"
if [[ "$REPLY" == "yes" ]]; then
    echo "  Proceeding with cleanup..."
    rm -rf ~/.xonshrc ~/.config/xonsh ~/.local/share/xonsh ~/.cache/xonsh ~/.x-cmd.root ~/.xontribs_python_path
    echo "  Removed common Xonsh/X-cmd user config locations and ~/.xontribs_python_path."
    echo "  [INFO] If you previously integrated Xonsh with other shells (.bashrc, .profile, .zshrc),"
    echo "         manual review of those files for leftover sourcing lines is recommended."
else
    echo "  Skipping cleanup of existing Xonsh/X-cmd configs."
fi
echo "[OK] Cleanup phase decision processed."
echo "--------------------------------------------------------------------"

# --- 2. Install/Upgrade Core Python Tools for User (pip, virtualenv) ---
echo "[Phase 2/9] Core Python Tools (pip, virtualenv) for ${PYTHON_CMD}."
echo "This will ensure pip and virtualenv are installed/upgraded for your user account via '${PYTHON_CMD}'."
prompt_yes_no "Proceed with checking/installing/upgrading pip and virtualenv?"
if [[ "$REPLY" == "yes" ]]; then
    "$PYTHON_CMD" -m ensurepip --upgrade || echo -e "${YELLOW}WARNING: '${PYTHON_CMD} -m ensurepip --upgrade' reported an issue. This might be okay if pip is already functional.${NC}"
    if "$PYTHON_CMD" -m pip install --user --upgrade pip virtualenv; then
        echo "[OK] pip and virtualenv checked/installed/upgraded successfully for ${PYTHON_CMD}."
    else
        echo -e "${RED}ERROR: Failed to install/upgrade pip or virtualenv using ${PYTHON_CMD}.${NC}"
        echo "         Please check your Python installation and pip. You can try running manually:"
        echo "         ${PYTHON_CMD} -m pip install --user --upgrade pip virtualenv"
        prompt_yes_no "Continue despite this error (not recommended unless pip/virtualenv are known to be working for '${PYTHON_CMD}')?"
        [[ "$REPLY" == "no" ]] && exit 1
    fi
else
    echo "  Skipping pip/virtualenv check/update. Ensure they are functional for ${PYTHON_CMD}."
fi
echo "--------------------------------------------------------------------"

# --- 3. Install/Upgrade Xonsh ---
echo "[Phase 3/9] Xonsh Shell Installation/Upgrade."
XONSH_USER_BIN_DIR="\${HOME}/.local/bin" # Use literal $HOME for echo, expansion for test
XONSH_EXE_PATH_TEST="${HOME}/.local/bin/xonsh" # For -f test
XONSH_INSTALLED=false
NEEDS_XONSH_INSTALL_OR_UPGRADE=false

if [ -f "$XONSH_EXE_PATH_TEST" ] || command_exists xonsh; then
    XONSH_INSTALLED=true
    echo "  Xonsh appears to be already installed."
    prompt_yes_no "Do you want to attempt to UPGRADE it using '${PYTHON_CMD} -m pip install --user --upgrade \"xonsh[full]\"'?"
    if [[ "$REPLY" == "yes" ]]; then
        NEEDS_XONSH_INSTALL_OR_UPGRADE=true
    else
        echo "  Skipping Xonsh upgrade."
    fi
else
    echo "  Xonsh not detected."
    prompt_yes_no "Do you want to INSTALL Xonsh for your user account using '${PYTHON_CMD} -m pip install --user --upgrade \"xonsh[full]\"'?"
    if [[ "$REPLY" == "yes" ]]; then
        NEEDS_XONSH_INSTALL_OR_UPGRADE=true
    else
        echo "  Xonsh installation skipped. Further Xonsh-specific setup will be aborted."
        echo "Setup terminated by user choice."
        exit 0
    fi
fi

if [[ "\$NEEDS_XONSH_INSTALL_OR_UPGRADE" == "true" ]]; then
    echo "  Installing/Upgrading Xonsh (this may take a moment)..."
    if "$PYTHON_CMD" -m pip install --user --upgrade "xonsh[full]"; then
        echo "[OK] Xonsh installed/upgraded successfully."
        XONSH_INSTALLED=true 
    else
        echo -e "${RED}FATAL_ERROR: Failed to install/upgrade Xonsh. Please check pip output and Python environment.${NC}"
        exit 1
    fi
fi

if \$XONSH_INSTALLED; then
    mkdir -p "${HOME}/.local/bin" 
    if [[ ":\$PATH:" != *":\${HOME}/.local/bin:"* ]]; then
        echo ""
        echo -e "${YELLOW}[IMPORTANT_ACTION_REQUIRED] '\${HOME}/.local/bin' is not found in your current PATH.${NC}"
        echo "  To make Xonsh directly callable, you MUST add it to your PATH."
        echo "  Add this line to your shell's startup file (e.g., ~/.bashrc, ~/.zshrc, or ~/.profile):"
        echo -e "      ${CYAN}export PATH=\"\\$HOME/.local/bin:\\$PATH\"${NC}"
        echo "  Then, source the file (e.g., 'source ~/.bashrc') or re-login / restart your terminal."
        prompt_yes_no "This script can attempt to add it to ~/.profile if you wish. Proceed?"
        if [[ "\$REPLY" == "yes" ]]; then
            if ! grep -qF "export PATH=\"\$HOME/.local/bin:\$PATH\"" ~/.profile; then
                echo -e '
# Added by Omnitide User Shell Setup for Xonsh and user pip packages
export PATH="$HOME/.local/bin:$PATH"' >> ~/.profile
                echo "  Line added to ~/.profile. You'll need to re-login for it to take full effect."
            else
                echo "  Required PATH export line already exists in ~/.profile."
            fi
        fi
    fi
else
    echo "Xonsh is not installed. Cannot proceed with Xonsh specific setup."
    exit 1
fi
echo "[OK] Xonsh installation/check complete."
echo "--------------------------------------------------------------------"

# --- 4. Install Xontribs ---
echo "[Phase 4/9] Xonsh Extensions (Xontribs) Setup."
XONTRIBS_CORE_RECOMMENDED=("xontrib-direnv" "xontrib-fzf" "xontrib-up")
XONTRIBS_INSTALLED_FOR_RC=()

echo "The following xontribs are highly recommended:"
for XONTRIB in "\${XONTRIBS_CORE_RECOMMENDED[@]}"; do echo "  - \${XONTRIB}"; done
prompt_yes_no "Do you want to install/upgrade these recommended xontribs?"
if [[ "\$REPLY" == "yes" ]]; then
    if [[ " \${XONTRIBS_CORE_RECOMMENDED[*]} " =~ " xontrib-fzf " ]] && ! command_exists fzf; then
        echo -e "${YELLOW}WARNING: 'fzf' command (system dependency for xontrib-fzf) not found.${NC}"
        prompt_yes_no "           Install 'fzf' system-wide (e.g., 'sudo apt install fzf')? This script can try."
        if [[ "\$REPLY" == "yes" ]]; then
            if sudo apt update && sudo apt install -y fzf; then echo "  fzf installed."; else echo -e "  ${RED}ERROR: fzf system installation failed. Install manually.${NC}"; fi
        fi
    fi
    if [[ " \${XONTRIBS_CORE_RECOMMENDED[*]} " =~ " xontrib-direnv " ]] && ! command_exists direnv; then
        echo -e "${YELLOW}WARNING: 'direnv' command (system dependency for xontrib-direnv) not found.${NC}"
        prompt_yes_no "           Install 'direnv' system-wide (e.g., 'sudo apt install direnv')? This script can try."
        if [[ "\$REPLY" == "yes" ]]; then
             if sudo apt update && sudo apt install -y direnv; then echo "  direnv installed."; else echo -e "  ${RED}ERROR: direnv system installation failed. Install manually.${NC}"; fi
        fi
    fi
    
    echo "  Installing/upgrading recommended xontribs: \${XONTRIBS_CORE_RECOMMENDED[*]}..."
    if "$PYTHON_CMD" -m pip install --user --upgrade "\${XONTRIBS_CORE_RECOMMENDED[@]}"; then
        echo "[OK] Recommended xontribs installed/upgraded."
        XONTRIBS_INSTALLED_FOR_RC=("\${XONTRIBS_CORE_RECOMMENDED[@]}")
    else
        echo -e "${RED}ERROR: Failed to install one or more core xontribs. Check pip output.${NC}"
    fi
else
    echo "  Skipping installation of recommended xontribs."
fi
echo "[OK] Xontribs setup phase complete."
echo "--------------------------------------------------------------------"

# --- 5. Install x-cmd (Optional) ---
echo "[Phase 5/9] x-cmd Installation (Optional Tool)."
XCMD_EXE_PATH_TEST="\${HOME}/.x-cmd.root/bin/x"
XCMD_INSTALLED_FLAG=false
if [ -f "\$XCMD_EXE_PATH_TEST" ]; then
    echo "  x-cmd appears to be already installed."
    XCMD_INSTALLED_FLAG=true
    prompt_yes_no "Do you want to check for x-cmd updates ('\$XCMD_EXE_PATH_TEST update self')?"
    if [[ "\$REPLY" == "yes" ]]; then
        if "\$XCMD_EXE_PATH_TEST" update self; then echo "  x-cmd updated."; else echo "  x-cmd update command had issues or was already latest."; fi
    fi
else
    prompt_yes_no "x-cmd is a community-driven command-line tool enhancer. Install it now?"
    if [[ "\$REPLY" == "yes" ]]; then
        if bash -c "\$(curl -fsSL https://get.x-cmd.com)"; then
            echo "[OK] x-cmd installation script completed."
            if [ -f "\$XCMD_EXE_PATH_TEST" ]; then XCMD_INSTALLED_FLAG=true; else echo -e "${RED}ERROR: x-cmd executable not found after install.${NC}"; fi
        else
            echo -e "${RED}ERROR: x-cmd installation script failed.${NC}"
        fi
    else
        echo "  Skipping x-cmd installation."
    fi
fi
echo "[OK] x-cmd installation phase complete."
echo "--------------------------------------------------------------------"

# --- 6. Integrate x-cmd with Xonsh (If x-cmd installed) ---
echo "[Phase 6/9] x-cmd Xonsh Integration (if x-cmd is installed)."
if \$XCMD_INSTALLED_FLAG; then
    prompt_yes_no "Run 'x onsh --setup' to integrate x-cmd with Xonsh configuration?"
    if [[ "\$REPLY" == "yes" ]]; then
        if "\$XCMD_EXE_PATH_TEST" onsh --setup; then
            echo "[OK] 'x onsh --setup' completed."
        else
            echo -e "${YELLOW}WARNING: 'x onsh --setup' command reported an issue. This might be okay if already set up.${NC}"
        fi
    else
        echo "  Skipping 'x onsh --setup'."
    fi
else
    echo "  Skipping x-cmd Xonsh integration (x-cmd not installed)."
fi
echo "[OK] x-cmd Xonsh integration phase complete."
echo "--------------------------------------------------------------------"

# --- 7. Create/Update .xonshrc ---
echo "[Phase 7/9] Generating/Updating ~/.xonshrc file..."
XONSHRC_CONTENT="# ~/.xonshrc (Omnitide CLI Dev v\${SCRIPT_VERSION})
# Interactively generated. Loads essential plugins.

print(f\"INFO: Omnitide Dev .xonshrc v\${SCRIPT_VERSION} loading...\")

# Load selected xontribs (ensure system packages fzf, direnv are installed for these)
if \${#XONTRIBS_INSTALLED_FOR_RC[@]} -gt 0 ; then
    print(\"INFO: Loading selected xontribs...\")
    for xontrib_raw_name in \"\${XONTRIBS_INSTALLED_FOR_RC[@]}\"; do
        xontrib_load_name = xontrib_raw_name.replace('xontrib-', '')
        try:
            xontrib load @(xontrib_load_name)
            print(f\"  INFO: Successfully loaded xontrib: {xontrib_load_name}\")
        except Exception as e_xontrib:
            print(f\"  WARN: Could not load xontrib '{xontrib_load_name}': {{e_xontrib}}\")
    print(\"\")
else:
    print(\"INFO: No xontribs were selected for auto-loading in .xonshrc during setup.\")
    print(\"      You can load them manually via 'xontrib load <name>'.\")
fi

# Optional: Powerline prompt (Uncomment if xontrib-powerline or similar is installed)
# print(\"INFO: Attempting to load powerline prompt (optional)...\")
# try:
#     xontrib load powerline 
#     \$PROMPT = \$POWERLINE_PROMPT 
#     print(\"  INFO: Powerline prompt theme loaded.\")
# except Exception as e_powerline:
#     print(f\"  WARN: Could not load powerline xontrib or set prompt: {{e_powerline}}\")

# x-cmd integration is typically handled by files in ~/.config/xonsh/ via 'x onsh --setup'.

# Ensure prompt updates after all configurations.
if 'update_prompt' in globals() and callable(globals()['update_prompt']):
    print(\"INFO: Requesting final prompt update via globals()['update_prompt']()...\")
    globals()['update_prompt']()
elif hasattr(__builtins__, 'update_prompt') and callable(getattr(__builtins__, 'update_prompt')): # Fallback
    print(\"INFO: Requesting final prompt update via __builtins__.update_prompt()...\")
    getattr(__builtins__, 'update_prompt')()
else:
    print(\"INFO: 'update_prompt' function not found/callable. Prompt may update via other mechanisms.\")

print(f\"INFO: Omnitide Dev .xonshrc v\${SCRIPT_VERSION} loading complete.\")
"
# The XONSHRC_CONTENT needs to be written carefully to avoid issues with bash trying to expand $ and backticks.
# Using single quotes for cat EOF is safer for literal content.
# For the xontrib loop within .xonshrc, it's tricky to generate that part from bash into python.
# A simpler .xonshrc might be better if this becomes too complex.

# Simplified .xonshrc generation, user can add xontribs manually or script adds fixed ones
cat << EOF_XONSHRC > ~/.xonshrc
# ~/.xonshrc (Omnitide CLI Dev v${SCRIPT_VERSION})
# Interactively generated.

print(f"INFO: Omnitide Dev .xonshrc v${SCRIPT_VERSION} loading...")

# Load direnv, fzf, up if they were installed via this script
EOF_XONSHRC

# Append xontrib loading if they were installed
if [[ " ${XONTRIBS_INSTALLED_FOR_RC[*]} " =~ " xontrib-direnv " ]]; then
echo -e "print('  Loading xontrib-direnv...')
try: xontrib load direnv
except: print('  WARN: Failed to load direnv xontrib.')" >> ~/.xonshrc
fi
if [[ " ${XONTRIBS_INSTALLED_FOR_RC[*]} " =~ " xontrib-fzf " ]]; then
echo -e "print('  Loading xontrib-fzf...')
try: xontrib load fzf
except: print('  WARN: Failed to load fzf xontrib.')" >> ~/.xonshrc
fi
if [[ " ${XONTRIBS_INSTALLED_FOR_RC[*]} " =~ " xontrib-up " ]]; then
echo -e "print('  Loading xontrib-up...')
try: xontrib load up
except: print('  WARN: Failed to load up xontrib.')" >> ~/.xonshrc
fi

cat <<EOF_XONSHRC_END >> ~/.xonshrc

# Optional: Powerline (manual uncomment)
# print("INFO: Attempting to load powerline prompt...")
# try:
#     xontrib load powerline
#     \$PROMPT = \$POWERLINE_PROMPT
# except Exception as e:
#     print(f"  WARN: Could not load powerline: {e}")

if 'update_prompt' in globals() and callable(globals()['update_prompt']):
    print("INFO: Requesting final prompt update...")
    globals()['update_prompt']()
else:
    print("INFO: 'update_prompt' not found/callable.")

print(f"INFO: Omnitide Dev .xonshrc v${SCRIPT_VERSION} loading complete.")
EOF_XONSHRC_END

echo "[OK] ~/.xonshrc created/updated."
echo "--------------------------------------------------------------------"

# --- 8. Guidance and Automation for Omnitide CLI Project Setup ---
echo "[Phase 8/9] Omnitide Project Environment Setup Assistance (using direnv)."
echo ""
CURRENT_DIR_FOR_PROJECT_SETUP=$(pwd)
prompt_yes_no "Is the current directory ('${CURRENT_DIR_FOR_PROJECT_SETUP}') the root of your Omniapp project where you want to set up a direnv environment?"
if [[ "\$REPLY" == "yes" ]]; then
    OMNIAPP_PROJECT_ROOT_CONFIRMED="\$CURRENT_DIR_FOR_PROJECT_SETUP"
    echo "  Current directory confirmed as project root: \${OMNIAPP_PROJECT_ROOT_CONFIRMED}"

    if ! command_exists direnv; then
        echo -e "  ${RED}ERROR: 'direnv' command is not available. This step requires 'direnv' (system-wide) and 'xontrib-direnv' (for Xonsh).${NC}"
    else
        echo "  Setting up direnv for project: \${OMNIAPP_PROJECT_ROOT_CONFIRMED}"
        ENVRC_FILE="\${OMNIAPP_PROJECT_ROOT_CONFIRMED}/.envrc"
        REQUIREMENTS_PROJECT_FILE="\${OMNIAPP_PROJECT_ROOT_CONFIRMED}/${REQUIREMENTS_FILE_NAME}" # Using global var

        if [ -f "\$ENVRC_FILE" ]; then
            echo "  Found existing .envrc file in project directory."
            prompt_yes_no "Overwrite existing .envrc with a standard Omniapp template?"
            if [[ "\$REPLY" == "no" ]]; then
                echo "  Keeping existing .envrc. Ensure it includes 'layout python ${PYTHON_CMD_FOR_VENV}' or similar."
                NEEDS_ENVRC_CREATION_PROJECT=false
            else
                NEEDS_ENVRC_CREATION_PROJECT=true
            fi
        else
            NEEDS_ENVRC_CREATION_PROJECT=true
        fi

        if \$NEEDS_ENVRC_CREATION_PROJECT; then
            echo "  Creating/Overwriting .envrc file with standard Python layout..."
            # Use the PYTHON_CMD_FOR_VENV defined at the top of this bootstrap script
            echo "# .envrc for Omniapp Suite (auto-generated by setup script)" > "\$ENVRC_FILE"
            echo "echo \"Loading Omniapp project environment (\${OMNIAPP_PROJECT_ROOT_CONFIRMED})...\"" >> "\$ENVRC_FILE"
            echo "layout python ${PYTHON_CMD_FOR_VENV}" >> "\$ENVRC_FILE"
            echo "export OMNIAPP_ROOT=\\$(pwd)" >> "\$ENVRC_FILE" # direnv will set OMNIAPP_ROOT
            echo "echo \"Python from venv: \\$(which python)\"" >> "\$ENVRC_FILE"
            echo "echo \"Omniapp project environment loaded.\"" >> "\$ENVRC_FILE"
            echo "  .envrc file created/updated in \${OMNIAPP_PROJECT_ROOT_CONFIRMED}."
        fi

        prompt_yes_no "Run 'direnv allow .' in this directory ('\${OMNIAPP_PROJECT_ROOT_CONFIRMED}') to approve and activate the environment?"
        if [[ "\$REPLY" == "yes" ]]; then
            echo "  Running 'direnv allow .'..."
            if (cd "\${OMNIAPP_PROJECT_ROOT_CONFIRMED}" && direnv allow .); then
                echo "  'direnv allow .' executed."
                
                if [ -f "\$REQUIREMENTS_PROJECT_FILE" ]; then
                    echo "  Found project requirements file: \${REQUIREMENTS_PROJECT_FILE}"
                    prompt_yes_no "Attempt to install project dependencies using 'pip install -r \${REQUIREMENTS_FILE_NAME}' into the direnv-managed venv now?"
                    if [[ "\$REPLY" == "yes" ]]; then
                        echo "  Attempting to install dependencies. This assumes direnv has activated the venv."
                        if (cd "\${OMNIAPP_PROJECT_ROOT_CONFIRMED}" && direnv exec . pip install -r "\${REQUIREMENTS_FILE_NAME}"); then
                             echo "  [OK] 'pip install -r \${REQUIREMENTS_FILE_NAME}' executed."
                        else
                             echo -e "  ${YELLOW}WARNING: 'pip install' via 'direnv exec' reported an issue. Manual installation might be needed after ensuring direnv environment is active.${NC}"
                        fi
                    fi
                else
                    echo -e "  ${YELLOW}WARNING: Project requirements file '\${REQUIREMENTS_PROJECT_FILE}' not found. Cannot offer to install dependencies.${NC}"
                    echo "            Please ensure '\${REQUIREMENTS_FILE_NAME}' (with content for CLI, WebUI, Agents) is in '\${OMNIAPP_PROJECT_ROOT_CONFIRMED}'."
                fi
            else
                echo -e "  ${RED}ERROR: 'direnv allow .' failed. Please run it manually in '\${OMNIAPP_PROJECT_ROOT_CONFIRMED}' from within Xonsh.${NC}"
            fi
        else
            echo "  Skipped 'direnv allow .'. You will need to run it manually in '\${OMNIAPP_PROJECT_ROOT_CONFIRMED}'."
        fi
    fi
else
    echo "  Skipping automated project setup for current directory."
    echo "  Remember to set up a 'direnv' environment for your Omniapp project manually later."
fi
echo "--------------------------------------------------------------------"


# --- 9. Final Instructions ---
echo "[Phase 9/9] Final Instructions & Summary"
echo ""
echo -e "${GREEN}--- Omnitide Interactive User Shell & Project Setup Finished ---${NC}"
echo "IMPORTANT NEXT STEPS:"
echo "1. If PATH was modified (e.g., for ~/.local/bin), ${YELLOW}CLOSE THIS TERMINAL and open a new one, or re-login.${NC}"
echo "2. Start Xonsh in your new terminal: ${CYAN}xonsh${NC}"
echo "3. If this is your FIRST time using direnv with Xonsh:"
echo "   Run this command ONCE *inside* Xonsh: ${CYAN}execx(\$(direnv hook xonsh), 'exec')${NC}"
echo "   Then, ${YELLOW}RESTART XONSH${NC} again (exit and type 'xonsh')."
echo "4. Navigate to your Omniapp project directory (e.g., '${CYAN}cd ${OMNIAPP_DIR:-/home/pong/Projects/omniapp}${NC}')."
echo "   - If you used Phase 8 for project setup:"
echo "     - Direnv should automatically activate the venv (you'll see a message)."
echo "     - If dependencies weren't installed, run: ${CYAN}pip install -r ${REQUIREMENTS_FILE_NAME}${NC}"
echo "   - If you SKIPPED Phase 8 project setup:"
echo "     - Create an '.envrc' file (see Phase 8 output for an example)."
echo "     - Run: ${CYAN}direnv allow .${NC}"
echo "     - Install dependencies: ${CYAN}pip install -r ${REQUIREMENTS_FILE_NAME}${NC}"
echo "5. Once the project environment is active and dependencies are installed, you should be able to use the Omnitide tools."
echo ""
echo "Review all script output for WARNINGS or ERRORS and address them as needed."
echo "--------------------------------------------------------------------"
exit 0
