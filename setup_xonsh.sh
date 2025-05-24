#!/bin/bash
#
# Omnitide Nexus Protocol: Shell Environment Reconfiguration
#
# This script reconfigures the user's environment to run xonsh on Python 3.11,
# without altering the system's default Python version.
#
# Architect: Pongtana Alix Feronti
# Engineer: Lily
#
# Core Technologies: pyenv for Python version management, pipx for isolated app installation.
#

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration ---
PYTHON_VERSION="3.11"
LATEST_PATCH="" # This will be auto-detected

# --- Helper Functions ---
print_info() {
    printf "\n\033[1;34m[INFO]\033[0m %s\n" "$1"
}

print_success() {
    printf "\033[1;32m[SUCCESS]\033[0m %s\n" "$1"
}

print_warning() {
    printf "\033[1;33m[WARNING]\033[0m %s\n" "$1"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# --- Main Logic ---

# 1. Install Build Dependencies for Python
install_dependencies() {
    print_info "Checking for and installing necessary build dependencies..."
    if command_exists apt-get; then
        # Debian/Ubuntu
        sudo apt-get update
        sudo apt-get install -y make build-essential libssl-dev zlib1g-dev \
        libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
        libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev
    elif command_exists yum; then
        # CentOS/RHEL
        sudo yum install -y gcc zlib-devel bzip2 bzip2-devel readline-devel sqlite \
        sqlite-devel openssl-devel tk-devel libffi-devel xz-devel
    elif command_exists pacman; then
        # Arch Linux
        sudo pacman -Syu --noconfirm base-devel openssl zlib xz tk
    elif command_exists brew; then
        # macOS
        brew install openssl readline sqlite3 xz zlib tcl-tk
    else
        print_warning "Could not determine package manager. Please install Python build dependencies manually."
    fi
    print_success "Build dependencies are satisfied."
}

# 2. Install pyenv
install_pyenv() {
    if [ -d "${HOME}/.pyenv" ]; then
        print_info "pyenv is already installed. Updating..."
        (cd "${HOME}/.pyenv" && git pull)
    else
        print_info "Installing pyenv..."
        git clone https://github.com/pyenv/pyenv.git ~/.pyenv
    fi

    # Set up pyenv environment variables
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    
    # Add pyenv init to shell profile
    SHELL_PROFILE=""
    CURRENT_SHELL=$(basename "$SHELL")
    if [ "$CURRENT_SHELL" = "bash" ]; then
        SHELL_PROFILE="$HOME/.bashrc"
    elif [ "$CURRENT_SHELL" = "zsh" ]; then
        SHELL_PROFILE="$HOME/.zshrc"
    else
        SHELL_PROFILE="$HOME/.profile"
    fi

    if ! grep -q 'pyenv init' "$SHELL_PROFILE"; then
        print_info "Adding pyenv configuration to ${SHELL_PROFILE}..."
        echo '' >> "$SHELL_PROFILE"
        echo '# Omnitide Nexus - pyenv configuration' >> "$SHELL_PROFILE"
        echo 'export PYENV_ROOT="$HOME/.pyenv"' >> "$SHELL_PROFILE"
        echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> "$SHELL_PROFILE"
        echo 'eval "$(pyenv init --path)"' >> "$SHELL_PROFILE"
        echo 'eval "$(pyenv init -)"' >> "$SHELL_PROFILE"
        print_warning "A new shell session is required for pyenv to be fully active. This script will attempt to source it."
    fi
    
    # Source the profile to make pyenv available in this script
    eval "$(pyenv init --path)"
    eval "$(pyenv init -)"

    print_success "pyenv installed and configured."
}

# 3. Install Target Python Version
install_python() {
    print_info "Looking for the latest patch version of Python ${PYTHON_VERSION}..."
    LATEST_PATCH=$(pyenv install --list | grep -E "^\s*${PYTHON_VERSION}\.[0-9]+\s*$" | tail -n 1 | tr -d '[:space:]')
    
    if [ -z "$LATEST_PATCH" ]; then
      echo "Could not find a suitable Python ${PYTHON_VERSION} version to install."
      exit 1
    fi
    
    print_info "Latest available version is ${LATEST_PATCH}."

    if pyenv versions --bare | grep -q "^${LATEST_PATCH}$"; then
        print_info "Python ${LATEST_PATCH} is already installed."
    else
        print_info "Installing Python ${LATEST_PATCH} with pyenv... (this may take a while)"
        pyenv install "$LATEST_PATCH"
    fi
    print_success "Python ${LATEST_PATCH} is available."
}

# 4. Install/Reinstall xonsh with pipx
install_xonsh() {
    print_info "Ensuring pipx is installed and configured..."
    if ! command_exists pipx; then
        python3 -m pip install --user pipx
        python3 -m pipx ensurepath
    fi
    
    # Add pipx path to current session
    export PATH="${HOME}/.local/bin:${PATH}"

    # Get the full path to the pyenv Python interpreter
    PYENV_PYTHON_PATH=$(pyenv which python)
    if [ -z "$PYENV_PYTHON_PATH" ]; then
        # This is a fallback in case `pyenv which` fails in a weird shell state
        PYENV_PYTHON_PATH="${PYENV_ROOT}/versions/${LATEST_PATCH}/bin/python"
    fi
    
    print_info "Found pyenv Python at: ${PYENV_PYTHON_PATH}"

    if command_exists xonsh && [[ $(pipx list --json) == *'"name": "xonsh"'* ]]; then
        print_info "xonsh is already installed via pipx. Reinstalling with Python ${LATEST_PATCH}..."
        pipx reinstall xonsh --python "$PYENV_PYTHON_PATH"
    else
        print_info "Installing xonsh via pipx with Python ${LATEST_PATCH}..."
        # Uninstall any system-wide or user-wide copies first to avoid confusion
        if command_exists xonsh; then
            print_warning "Attempting to uninstall existing xonsh to avoid conflicts..."
            pip uninstall -y xonsh &>/dev/null || true
        fi
        pipx install xonsh --python "$PYENV_PYTHON_PATH"
    fi
    print_success "xonsh has been installed into an isolated environment using Python ${LATEST_PATCH}."
}

# 5. Install x-cmd for xonsh
install_xcmd() {
    print_info "Installing x-cmd for the new xonsh environment..."
    # Use the pipx-installed xonsh to run the installation command
    "${HOME}/.local/bin/xonsh" -c 'xpip install x-cmd'
    print_success "x-cmd installed."
}

# --- Execution ---
main() {
    install_dependencies
    install_pyenv
    install_python
    install_xonsh
    install_xcmd

    echo
    print_success "All operations completed successfully!"
    print_info "To start using your new shell, please open a NEW terminal window."
    print_info "Once in the new terminal, run 'xonsh' to start the shell."
    
    XONSH_PATH=$(command -v xonsh)
    print_info "Your new xonsh executable is located at: ${XONSH_PATH}"
    print_info "To verify the Python version inside xonsh, run:"
    echo "  xonsh -c 'echo(\$PYTHON_VERSION)'"
    echo
    print_warning "To make xonsh your default login shell, you can run:"
    print_warning "  chsh -s \"${XONSH_PATH}\""
    print_warning "You may need to add ${XONSH_PATH} to /etc/shells first."
}

main "$@"
