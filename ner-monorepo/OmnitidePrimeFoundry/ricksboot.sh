#!/usr/bin/env bash
# rick_ultimate_opf_bootstrap.sh - v1.0
# The "One and Done" Rick Way to Bootstrap the Omnitide Project Foundry (OPF)
# This script builds the basic workshop, copies seed agents, and sets up initial NER assets.
# TPC Mandated: Clarity, Robustness, Idempotency (where practical for setup).

# --- Strict Mode & Error Handling ---
set -euo pipefail # ERR_EXIT, UNBOUND_VARS, PIPE_FAILURES
trap 'echo "ERROR: Script failed at line $LINENO, command: $BASH_COMMAND"; exit 1' ERR
# Consider: trap 'cleanup_function' EXIT (if complex cleanup is needed)

# --- Configuration & Constants (User may need to adjust OPF_BASE_DIR) ---
OPF_BASE_DIR="${OPF_BASE_DIR:-$HOME/OmnitidePrimeFoundry}" # Default to ~/OmnitidePrimeFoundry if not set
OPF_ROOT_NAME="OPF_Instance_$(date +%Y%m%d_%H%M%S)" # Unique instance name
OPF_ROOT_ABS="${OPF_BASE_DIR}/${OPF_ROOT_NAME}"

# Relative paths within OPF_ROOT_ABS
NPTPAC_DIR_REL="NPTPAC" # Nexus TPC Asset Core
NER_REPOSITORY_REL="${NPTPAC_DIR_REL}/ner_repository"
CORE_AGENTS_DIR_REL="${NPTPAC_DIR_REL}/core_agents"
EXWORK_TASKS_DIR_REL="${NPTPAC_DIR_REL}/exwork_tasks"

# Seed Agent Source Paths (CRITICAL: These must point to your actual seed agent files)
# These paths are placeholders. The Architect MUST ensure these point to the correct
# locations of the 'current best' exwork and scribe agents before running this script.
# For this generation, I will assume they are in a 'seed_agents_source' directory
# relative to this bootstrap script's location, or the Architect will place them there.
SEED_AGENT_SOURCE_DIR="${SEED_AGENT_SOURCE_DIR:-./seed_agents_source}" # Default to a subdir
SEED_EXWORK_AGENT_FILENAME="ex_work_agent_v_current.py"
SEED_SCRIBE_AGENT_FILENAME="scribe_agent_v_current.py"

# NER Asset Content
RICKS_DIRECTIVES_MD_FILENAME="000_RICKS_DIRECTIVES_FOR_OMEGA_MVP.md"
STRICT_SCRIBE_PROFILE_TOML_FILENAME="rick_prime_strict_v1.scribe.toml"
NER_CORE_EDICTS_DIR_REL="00_CORE_EDICTS" # For Rick's Directives

# --- Utility Functions ---
log_info() {
    echo "[INFO] $(date +'%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo "[WARN] $(date +'%Y-%m-%d %H:%M:%S') - $1" >&2
}

log_error() {
    echo "[ERROR] $(date +'%Y-%m-%d %H:%M:%S') - $1" >&2
}

confirm_action() {
    read -r -p "$1 [y/N]: " response
    case "$response" in
        [yY][eE][sS]|[yY])
            true
            ;;
        *)
            false
            ;;
    esac
}

# --- Main Bootstrap Logic ---
log_info "=== Rick's Ultimate OPF Bootstrap Script v1.0 ==="
log_info "This script will create the Omnitide Project Foundry (OPF) structure."

# 1. Confirm OPF Root Directory
log_info "The Omnitide Project Foundry (OPF) will be created at:"
log_info "  OPF_BASE_DIR (Parent for instances): ${OPF_BASE_DIR}"
log_info "  OPF_ROOT_ABS (This specific instance): ${OPF_ROOT_ABS}"
echo # Newline for readability

if [ -d "${OPF_ROOT_ABS}" ]; then
    log_warning "OPF Root directory '${OPF_ROOT_ABS}' already exists."
    if ! confirm_action "Do you want to proceed? This might overwrite some initial config files if they exist (agents will be copied with unique names if conflicts)."; then
        log_info "Bootstrap aborted by user."
        exit 0
    fi
else
    if ! confirm_action "Proceed with creating the OPF at '${OPF_ROOT_ABS}'?"; then
        log_info "Bootstrap aborted by user."
        exit 0
    fi
fi

# 2. Create OPF Directory Structure
log_info "Creating OPF directory structure..."
mkdir -p "${OPF_ROOT_ABS}/${NER_REPOSITORY_REL}/${NER_CORE_EDICTS_DIR_REL}"
mkdir -p "${OPF_ROOT_ABS}/${CORE_AGENTS_DIR_REL}"
mkdir -p "${OPF_ROOT_ABS}/${EXWORK_TASKS_DIR_REL}"
# Add other NER top-level category dirs as per Phase 0/1 requirements
mkdir -p "${OPF_ROOT_ABS}/${NER_REPOSITORY_REL}/06_AGENT_BLUEPRINTS/scribe_agent/profiles"
mkdir -p "${OPF_ROOT_ABS}/${NER_REPOSITORY_REL}/exwork_tasks_schemas" # For schemas of exwork tasks if needed

log_info "OPF Directory structure created at '${OPF_ROOT_ABS}'."
echo "export OPF_ROOT_ABS=\"${OPF_ROOT_ABS}\" # Add this to your shell profile (.bashrc, .zshrc, etc.)" >> "${OPF_ROOT_ABS}/activate_opf_env.sh"
log_info "An environment activation helper script 'activate_opf_env.sh' has been created in '${OPF_ROOT_ABS}'."
log_info "Source it ('source ${OPF_ROOT_ABS}/activate_opf_env.sh') to set OPF_ROOT_ABS in your current shell."


# 3. Copy Seed Agents into OPF
log_info "Preparing to copy seed agents..."
SEED_EXWORK_AGENT_SRC="${SEED_AGENT_SOURCE_DIR}/${SEED_EXWORK_AGENT_FILENAME}"
SEED_SCRIBE_AGENT_SRC="${SEED_AGENT_SOURCE_DIR}/${SEED_SCRIBE_AGENT_FILENAME}"

if [ ! -f "${SEED_EXWORK_AGENT_SRC}" ]; then
    log_error "Seed Ex-Work agent not found at '${SEED_EXWORK_AGENT_SRC}'."
    log_error "Please ensure '${SEED_EXWORK_AGENT_FILENAME}' is in '${SEED_AGENT_SOURCE_DIR}' or update SEED_AGENT_SOURCE_DIR."
    exit 1
fi
if [ ! -f "${SEED_SCRIBE_AGENT_SRC}" ]; then
    log_error "Seed Scribe agent not found at '${SEED_SCRIBE_AGENT_SRC}'."
    log_error "Please ensure '${SEED_SCRIBE_AGENT_FILENAME}' is in '${SEED_AGENT_SOURCE_DIR}' or update SEED_AGENT_SOURCE_DIR."
    exit 1
fi

# Destination paths for seed agents within OPF
OPF_EXWORK_AGENT_DEST="${OPF_ROOT_ABS}/${CORE_AGENTS_DIR_REL}/${SEED_EXWORK_AGENT_FILENAME}"
OPF_SCRIBE_AGENT_DEST="${OPF_ROOT_ABS}/${CORE_AGENTS_DIR_REL}/${SEED_SCRIBE_AGENT_FILENAME}"

log_info "Copying seed Ex-Work agent to '${OPF_EXWORK_AGENT_DEST}'..."
cp "${SEED_EXWORK_AGENT_SRC}" "${OPF_EXWORK_AGENT_DEST}"
chmod +x "${OPF_EXWORK_AGENT_DEST}" # Ensure it's executable

log_info "Copying seed Scribe agent to '${OPF_SCRIBE_AGENT_DEST}'..."
cp "${SEED_SCRIBE_AGENT_SRC}" "${OPF_SCRIBE_AGENT_DEST}"
chmod +x "${OPF_SCRIBE_AGENT_DEST}" # Ensure it's executable

log_info "Seed agents copied successfully."

# 4. Create Rick's Directives MD and Strict Scribe Profile TOML in OPF NER
log_info "Creating initial NER assets..."

# Rick's Directives MD
RICKS_DIRECTIVES_MD_PATH="${OPF_ROOT_ABS}/${NER_REPOSITORY_REL}/${NER_CORE_EDICTS_DIR_REL}/${RICKS_DIRECTIVES_MD_FILENAME}"
log_info "Creating Rick's Directives at '${RICKS_DIRECTIVES_MD_PATH}'..."
cat << EOF > "${RICKS_DIRECTIVES_MD_PATH}"
# Rick's Directives for ExWork-Omega MVP (TPC Mandated)

Alright, Architect, listen up. This OPF is your new sandbox. The seed agents I've "graciously" allowed you to copy in are your starting point – think of them as slightly less dumb clay. Your first, and ONLY your first, ExWork task is to forge the **ExWork-RickPrime MVP**.

## Task 001: Forge ExWork-RickPrime MVP

**Objective:** Transform the seed \`ex_work_agent_v_current.py\` into the foundational ExWork-RickPrime MVP (\`ex_work_agent.py\` within OPF) capable of executing the Phase 1 features I've blueprinted. This MVP will then be used for all subsequent ExWork-Omega development.

**Input:** You, Architect, will MANUALLY create the first ExWork JSON task file:
   \`${EXWORK_TASKS_DIR_REL}/001_Forge_ExWork_RickPrime.exwork.json\`
   (Path relative to \`${OPF_ROOT_ABS}\`).
   Use the detailed JSON structure I provided in our "Omega" blueprint discussions for this task. It will use the seed Ex-Work agent to modify itself.

**Key MVP Capabilities to Implement (Phase 1):**
1.  **Reliable Input:** Accept JSON instruction file path (\`sys.argv[1]\`) AND stdin.
2.  **Explicit Project Context:** Honor \`--project-root\` argument. All path resolutions MUST use this.
3.  **Robust Jinja2 Templating:** Implement the \`Jinja2TemplatingEngine\` with access to \`global_parameters\` and \`steps_output.action_id.result_field\`. Basic filters (\`tojson\`, \`b64encode\`, \`b64decode\`) must work.
4.  **Fix \`CREATE_OR_REPLACE_FILE\` Handler:**
    * Correctly prioritize and use \`content_from_file\` (with templated paths).
    * Handle \`content_base64\` robustly.
    * Handle \`content_literal\`.
5.  **Reliable \`RUN_SCRIPT\` Handler:** Basic interpreter detection, CWD control, robust output/RC capture.
6.  **Basic NER Handler Integration (via \`NER_FETCH_ASSET\` action):**
    * Implement \`NER_FETCH_ASSET\` to read files from this OPF NER (e.g., \`ner://...\` resolves to \`${OPF_ROOT_ABS}/${NER_REPOSITORY_REL}/...\`).
7.  **Basic Scribe Integration (Project Scribe agent):**
    * The new \`CREATE_OR_REPLACE_FILE\` for code types MUST automatically call the seed Scribe agent (as a \`RUN_SCRIPT\` sub-step initially) using a Scribe profile fetched via \`NER_FETCH_ASSET\`.
8.  **Basic \`DIAGNOSE_ERROR\` Handler (using seed \`llm_interface.py\`):**
    * Capture \`failed_command\`, \`stdout\`, \`stderr\`.
    * Make a simple call to a local Ollama model via a copied/adapted \`llm_interface.py\`.

**TPC Goal for MVP:**
The ExWork-RickPrime MVP, once forged by this first task, must be capable of reliably executing the logic of *this very bootstrap script* if that logic were expressed as an Ex-Work JSON. It must handle copying itself and Scribe, and creating these directive files from \`content_from_ner\` or \`content_base64\`.

Don't screw this up. The fate of at least three moderately interesting realities depends on it. Probably.

*- Rick C-137 (Omnitide Nexus Project Lead)*
EOF

# Strict Scribe Profile TOML
STRICT_SCRIBE_PROFILE_PATH="${OPF_ROOT_ABS}/${NER_REPOSITORY_REL}/06_AGENT_BLUEPRINTS/scribe_agent/profiles/${STRICT_SCRIBE_PROFILE_TOML_FILENAME}"
log_info "Creating Strict Scribe Profile at '${STRICT_SCRIBE_PROFILE_PATH}'..."
cat << EOF > "${STRICT_SCRIBE_PROFILE_PATH}"
# Strict Scribe Profile for ExWork-Omega Development (rick_prime_strict_v1.scribe.toml)
# TPC Mandated. This is the baseline for all Omega components.

# General Settings
fail_on_audit_severity = "high" # Fail if pip-audit finds high or critical vulnerabilities
fail_on_lint_critical = true    # Fail if Ruff (or other linter) finds critical issues
fail_on_mypy_error = true       # Fail on any MyPy type checking errors
fail_on_test_failure = true     # Fail if Pytest (or other test runner) reports failures

# Ruff Linter Configuration (Conceptual - Scribe would translate this to Ruff commands/config)
# For actual Ruff config, use pyproject.toml or .ruff.toml. This is Scribe's view.
[tool.scribe.ruff_linter]
  enabled = true
  # Select common checks: E (pycodestyle error), W (pycodestyle warning), F (Pyflakes),
  # I (isort), B (flake8-bugbear), C90 (mccabe complexity)
  select = ["E", "W", "F", "I", "B", "C90"]
  ignore = ["E501"] # Line too long, handled by formatter
  max_complexity = 10 # McCabe complexity
  # fix = true # Scribe might always run with --fix for Ruff check

# Ruff Formatter Configuration
[tool.scribe.ruff_formatter]
  enabled = true
  line_length = 119
  quote_style = "double"

# MyPy Static Type Checking Configuration
[tool.scribe.mypy_type_checker]
  enabled = true
  # Common strict flags for MyPy, Scribe would translate these to CLI args
  strict_optional = true
  warn_return_any = true
  warn_unused_ignores = true
  disallow_untyped_defs = true
  check_untyped_defs = true
  # mypy_path can be set by Scribe based on project structure / venv

# Pytest Configuration (Conceptual - Scribe runs pytest)
[tool.scribe.pytest_runner]
  enabled = true
  # Default arguments Scribe might pass to pytest
  default_args = ["-v", "--cov=.", "--cov-report=term-missing"]
  # fail_under_coverage_percent = 90 # Example of a TPC coverage mandate

# ShellCheck for Bash Scripts
[tool.scribe.shellcheck_linter]
  enabled = true
  # severity = "warning" # Example: fail on warnings or errors

# JSONLint / YAML Lint (Conceptual)
[tool.scribe.json_linter]
  enabled = true
[tool.scribe.yaml_linter]
  enabled = true
  # config_file = ".yamllint_config.yaml" # Scribe could look for project-specific linter configs

# TPC Mandates (Conceptual - Scribe might check these beyond tool outputs)
[tpc_mandates]
  enforce_docstrings = "all_public" # "none", "all_public", "all"
  enforce_type_hints = "all_public" # "none", "all_public", "all"
  max_cognitive_complexity = 15 # If a tool for this exists or LLM assists Scribe
  # readme_quality_check = true # LLM-assisted check for README clarity/completeness
  # license_present_check = true
EOF

log_info "Initial NER assets created."

# 5. Initialize OPF NER as a Git Repository
log_info "Initializing OPF NER as a Git repository..."
NER_REPO_ABS_PATH="${OPF_ROOT_ABS}/${NER_REPOSITORY_REL}"

if [ -d "${NER_REPO_ABS_PATH}/.git" ]; then
    log_warning "NER repository at '${NER_REPO_ABS_PATH}' already appears to be a Git repo."
else
    if ! command -v git &> /dev/null; then
        log_error "'git' command not found. Cannot initialize NER as a Git repository."
        log_error "Please install Git and ensure it's in your PATH."
        # Decide if this is a fatal error for the bootstrap. For NER, it's pretty critical.
        exit 1
    fi
    (
        cd "${NER_REPO_ABS_PATH}" || exit 1 # Enter NER repo dir, exit subshell on cd failure
        git init -b main # Initialize with 'main' as default branch
        git config user.name "ExWork-Omega Bootstrap"
        git config user.email "exwork-omega@omnitide.nexus"
        git add .
        git commit -m "Initial commit: OPF NER Bootstrap v1.0 - Rick's Directives & Strict Scribe Profile"
        log_info "OPF NER initialized as a Git repository and initial assets committed."
    )
fi

# 6. Final Instructions for the Architect
log_info "--- Bootstrap Phase 0 Complete ---"
echo # Newline
log_info "Omnitide Project Foundry (OPF) instance created at: ${OPF_ROOT_ABS}"
log_info "Seed agents (Ex-Work, Scribe) copied to: ${OPF_ROOT_ABS}/${CORE_AGENTS_DIR_REL}"
log_info "Initial NER assets (Rick's Directives, Scribe Profile) created in: ${OPF_ROOT_ABS}/${NER_REPOSITORY_REL}"
log_info "OPF NER has been initialized as a Git repository."
echo # Newline
log_info "!!! ARCHITECT'S NEXT ACTION (MANUAL STEP) !!!"
log_info "You must now create the first ExWork task file:"
log_info "  ${OPF_ROOT_ABS}/${EXWORK_TASKS_DIR_REL}/001_Forge_ExWork_RickPrime.exwork.json"
log_info "Use the detailed ExWork-Omega Instruction Block Schema and the Phase 1 MVP objectives"
log_info "from Rick's Directives to define this task. This task will use the seed Ex-Work agent"
log_info "to begin forging the ExWork-RickPrime MVP."
echo # Newline
log_info "To activate the OPF environment variables for your current shell session, run:"
log_info "  source \"${OPF_ROOT_ABS}/activate_opf_env.sh\""
log_info "Then, you can navigate to your ExWork-Omega source code directory (where you are building it)"
log_info "and once the MVP is ready, you would execute that first task, for example:"
log_info "  export OPF_ROOT_ABS=\"${OPF_ROOT_ABS}\" # Ensure this is set if not sourced"
log_info "  python -m exwork_omega.main --project-context-path \"${OPF_ROOT_ABS}\" \"${OPF_ROOT_ABS}/${EXWORK_TASKS_DIR_REL}/001_Forge_ExWork_RickPrime.exwork.json\""
echo # Newline
log_info "Good luck, Architect. Don't mess it up."
log_info "========================================="

exit 0
