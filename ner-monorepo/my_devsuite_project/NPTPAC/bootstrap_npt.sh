#!/bin/bash
# Nexus Protocol Toolkit (NPT) Bootstrapper - v2.1 (Development Version)
# Executes an existing Python-based NPT generator script.

set -e # Exit immediately if a command exits with a non-zero status.
set -o pipefail # Pipeline returns exit status of last command that failed.

# --- Configuration ---
NPT_GENERATOR_FILENAME="npt_generator.py" # Assumed to be in the NPT_BASE_DIR
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=8 # Python for the generator itself

# --- Helper Functions ---
echo_color() {
    local color_code="$1"
    local message="$2"
    echo -e "\033[${color_code}m${message}\033[0m"
}

info() { echo_color "34" "INFO: $1"; }
warning() { echo_color "33" "WARN: $1"; }
error_exit() { # Renamed to avoid conflict with npt_generator.py's error
    echo_color "31" "ERROR (bootstrap_npt.sh): $1" >&2
    exit "${2:-1}"
}
success() { echo_color "32" "SUCCESS: $1"; }
step() { echo_color "36" "\n>>> STEP (bootstrap_npt.sh): $1 <<<\n"; }

check_command() {
    command -v "$1" &>/dev/null
}

verify_dependencies() {
    step "Verifying System Dependencies"
    local missing_deps=0
    PYTHON_CMD=""

    if ! (check_command "python3" || check_command "python"); then
        error_exit "Python 3 (python3 or python) not installed or not in PATH." 1
    fi

    if check_command "python3"; then PYTHON_CMD="python3"; else PYTHON_CMD="python"; fi
    
    PY_VERSION_FULL=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
    PY_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
    PY_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')

    info "Found Python: $($PYTHON_CMD --version) (version $PY_VERSION_FULL) at $(command -v $PYTHON_CMD)"

    if [ "$PY_MAJOR" -lt "$MIN_PYTHON_MAJOR" ] || \
       { [ "$PY_MAJOR" -eq "$MIN_PYTHON_MAJOR" ] && [ "$PY_MINOR" -lt "$MIN_PYTHON_MINOR" ]; }; then
        error_exit "Python version $PY_MAJOR.$PY_MINOR is too old. NPT generator requires Python $MIN_PYTHON_MAJOR.$MIN_PYTHON_MINOR+." 1
    else
        success "Python version $PY_MAJOR.$PY_MINOR is sufficient."
        export NPT_PYTHON_CMD="$PYTHON_CMD" # Export for npt_generator.py
    fi

    if ! check_command "git"; then error_exit "Git not found. Required for NER." 1; else success "Git is installed."; fi
    
    info "System dependencies verified."
}

# --- Main Bootstrap Logic ---
main() {
    echo_color "35" "=================================================================="
    echo_color "35" "=== Nexus Protocol Toolkit (NPT) Bootstrapper v2.1 (Dev Mode)==="
    echo_color "35" "=================================================================="

    verify_dependencies

    step "Setting up NPT Base Directory"
    DEFAULT_NPT_BASE_DIR="$HOME/Projects/NPTPAC" # Your default
    read -p "Enter NPT base directory (default: $DEFAULT_NPT_BASE_DIR): " NPT_BASE_DIR_INPUT
    NPT_BASE_DIR="${NPT_BASE_DIR_INPUT:-$DEFAULT_NPT_BASE_DIR}"
    NPT_BASE_DIR_EXPANDED=$(eval echo "$NPT_BASE_DIR") # Expands ~

    if ! mkdir -p "$NPT_BASE_DIR_EXPANDED"; then
        error_exit "Failed to create/access NPT base directory: $NPT_BASE_DIR_EXPANDED. Check permissions." 1
    fi
    NPT_BASE_DIR_ABS=$(cd "$NPT_BASE_DIR_EXPANDED" && pwd)
    info "Using NPT base directory: $NPT_BASE_DIR_ABS"

    GENERATOR_SCRIPT_PATH="$NPT_BASE_DIR_ABS/$NPT_GENERATOR_FILENAME"

    step "Locating NPT Generator Script"
    if [ ! -f "$GENERATOR_SCRIPT_PATH" ]; then
        error_exit "NPT Generator script '$GENERATOR_SCRIPT_PATH' not found!" 1
    fi
    info "NPT Generator script found at $GENERATOR_SCRIPT_PATH"
    # No chmod +x needed if calling with python3 explicitly

    step "Executing NPT Generator Script"
    info "The Python NPT Generator will now take over..."
    info "It will prompt for paths to your Scribe and Ex-Work agents if defaults are not found or suitable."
    
    # Execute the Python generator script
    if "$NPT_PYTHON_CMD" "$GENERATOR_SCRIPT_PATH" --base-dir "$NPT_BASE_DIR_ABS"; then
        success "NPT Generator script executed successfully."
        echo_color "35" "\n=================================================================="
        echo_color "35" "NPT Bootstrap v2.1 Complete!"
        echo_color "35" "Please review the detailed 'Next Steps' guidance provided by the generator."
        echo_color "35" "=================================================================="
    else
        # npt_generator.py should print its own specific errors.
        # The error() function in npt_generator.py calls sys.exit(code).
        error_exit "NPT Generator script execution FAILED. Review output above." 1
    fi
}

# Run main if script is executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi