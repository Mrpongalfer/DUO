#!/bin/bash
#
# Omnitide Nexus - Agent Test Harness
#
# This script provides an end-to-end testing framework for the Ex-Work and Scribe agents.
# It creates an isolated workspace, sets up mock projects and commands,
# executes the agents, and reports on the outcome.
#

# --- Colors and Formatting ---
COLOR_BLUE="\033[1;34m"
COLOR_GREEN="\033[1;32m"
COLOR_YELLOW="\033[1;33m"
COLOR_RED="\033[1;31m"
COLOR_RESET="\033[0m"

print_header() {
    printf "\n${COLOR_BLUE}========== %s ==========${COLOR_RESET}\n" "$1"
}

print_success() {
    printf "${COLOR_GREEN}[SUCCESS]${COLOR_RESET} %s\n" "$1"
}

print_warning() {
    printf "${COLOR_YELLOW}[WARNING]${COLOR_RESET} %s\n" "$1"
}

print_info() {
    printf "[INFO] %s\n" "$1"
}

print_error() {
    printf "${COLOR_RED}[ERROR]${COLOR_RESET} %s\n" "$1"
}

# --- Setup ---
WORKSPACE="test_workspace"
print_header "Setting Up Test Workspace"

if [ -d "$WORKSPACE" ]; then
    print_warning "Workspace '$WORKSPACE' already exists. Reusing it."
else
    mkdir "$WORKSPACE"
    print_info "Created workspace directory: $WORKSPACE"
fi
cd "$WORKSPACE" || exit 1

# Ensure agents are executable
chmod +x ../exworkagent0.py
chmod +x ../scribe0.py


# ==============================================================================
# 1. TESTING EX-WORK AGENT
# ==============================================================================
print_header "Testing Ex-Work Agent (exworkagent0.py)"

# Create a simple script for the agent to run
print_info "Creating helper script 'test_script.sh' for RUN_SCRIPT action..."
cat << 'EOF' > test_script.sh
#!/bin/bash
echo "Hello from the test script! You passed the argument: $1"
EOF
chmod +x test_script.sh

# Create the JSON command for the agent
print_info "Creating JSON instruction file 'exwork_test.json'..."
cat << EOF > exwork_test.json
{
  "step_id": "exwork_agent_test_01",
  "description": "Test file creation and script execution.",
  "actions": [
    {
      "type": "CREATE_OR_REPLACE_FILE",
      "path": "output_file.txt",
      "content_base64": "$(echo -n "This file was created by the Ex-Work agent." | base64)"
    },
    {
      "type": "RUN_SCRIPT",
      "script_path": "./test_script.sh",
      "args": ["ArgumentFromJSON"]
    }
  ]
}
EOF

# Run the agent
print_info "Executing exworkagent0.py with JSON input..."
EXWORK_OUTPUT=$(../exworkagent0.py < exwork_test.json)
echo -e "\n--- Ex-Work Agent Output ---"
echo "$EXWORK_OUTPUT"
echo -e "--------------------------\n"

# Validate the results
print_info "Validating Ex-Work agent test results..."
if [ -f "output_file.txt" ]; then
    print_success "File 'output_file.txt' was created."
    if grep -q "This file was created by the Ex-Work agent." output_file.txt; then
        print_success "File content is correct."
    else
        print_error "File content is incorrect!"
    fi
else
    print_error "File 'output_file.txt' was NOT created!"
fi

if echo "$EXWORK_OUTPUT" | grep -q '"overall_success": true'; then
    print_success "Ex-Work agent reported overall success."
else
    print_error "Ex-Work agent reported a failure."
fi


# ==============================================================================
# 2. TESTING SCRIBE AGENT
# ==============================================================================
print_header "Testing Scribe Agent (scribe0.py)"

# Setup a mock Python project
PROJECT_DIR="scribe_test_project"
print_info "Setting up mock project: $PROJECT_DIR"
rm -rf "$PROJECT_DIR" # Clean previous runs
mkdir -p "$PROJECT_DIR/src"

# Initialize Git repo
(cd "$PROJECT_DIR" && git init && git config user.name "TestBot" && git config user.email "bot@test.com")

# Create project files
print_info "Creating mock project files..."

# requirements.txt
echo "requests==2.31.0" > "$PROJECT_DIR/requirements.txt"

# .scribe.toml (Scribe config)
cat << 'EOF' > "$PROJECT_DIR/.scribe.toml"
fail_on_audit_severity = "high"
fail_on_lint_critical = true
fail_on_mypy_error = true
commit_message_template = "test(Scribe): Validated changes for {target_file}"
EOF

# Initial Python file
cat << 'EOF' > "$PROJECT_DIR/src/main.py"
# Version 1.0
import os

def old_function(name):
    # This function has a minor issue
    print('Hello'  +  name)

if __name__ == "__main__":
    old_function("World")
EOF

# Commit the initial version
(cd "$PROJECT_DIR" && git add . && git commit -m "Initial commit")
print_info "Committed initial version of mock project."

# Create the "new code" file that Scribe will apply
print_info "Creating 'new_code.py' to be applied by Scribe..."
cat << 'EOF' > new_code.py
# Version 2.0
import os
from typing import Optional

def new_and_improved_function(name: str) -> None:
    """A much better function."""
    print(f"Hello, {name}!")

def another_function(data: Optional[list] = None) -> int:
    """Another function for testing."""
    if data is None:
        return 0
    return len(data)

if __name__ == "__main__":
    new_and_improved_function("World")
EOF

# Run the Scribe agent
# This assumes Python dependencies like 'ruff' and 'mypy' are installed in the environment running this script.
print_info "Executing scribe0.py on the mock project..."
print_info "This may take a minute as it sets up a venv and runs tools..."
SCRIBE_OUTPUT=$(../scribe0.py \
    "$PROJECT_DIR" \
    --target-file "src/main.py" \
    --source-file "new_code.py" \
    --commit \
    --log-level WARNING \
    --report-format json)

echo -e "\n--- Scribe Agent Final Report ---"
echo "$SCRIBE_OUTPUT"
echo -e "---------------------------------\n"

# Validate Scribe results
print_info "Validating Scribe agent test results..."
if echo "$SCRIBE_OUTPUT" | grep -q '"overall_status": "SUCCESS"'; then
    print_success "Scribe agent reported OVERALL SUCCESS."
else
    print_error "Scribe agent reported a FAILURE in its pipeline. Please review the JSON report above."
fi

if echo "$SCRIBE_OUTPUT" | grep -q '"commit_sha":'; then
    COMMIT_SHA=$(echo "$SCRIBE_OUTPUT" | grep '"commit_sha":' | awk -F'"' '{print $4}')
    if [[ -n "$COMMIT_SHA" && "$COMMIT_SHA" != "null" ]]; then
        print_success "A new commit was created with SHA: $COMMIT_SHA"
        (cd "$PROJECT_DIR" && git log -1)
    else
        print_warning "Scribe ran but did not produce a new commit SHA."
    fi
else
    print_error "Scribe report is missing the 'commit_sha' field."
fi


# --- Cleanup ---
cd ..
print_header "Testing Complete"
print_info "The test workspace is located at: $(pwd)/$WORKSPACE"
print_info "You can inspect the generated files and logs there."
print_warning "To clean up, you can manually delete the '$WORKSPACE' directory."
