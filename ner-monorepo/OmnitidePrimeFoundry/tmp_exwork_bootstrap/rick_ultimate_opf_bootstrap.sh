    #!/bin/bash
    # Rick's "ULTIMATE F--KING BOOTSTRAP" Shell Script - v2.1 (Now with more Rick!)
    # This script sets up the Omnitide Prime Foundry (OPF) directly using shell commands.
    # NO EX-WORK AGENT IS USED TO EXECUTE THIS SCRIPT'S LOGIC.
    # It assumes it's being run by a user who can write to $HOME.
    # It assumes your OLD project files are accessible.

    echo ""
    echo "[[ RICK SAYS: BOOTSTRAPPING OMNITIDE PRIME FOUNDRY - THE DIRECT, NO-NONSENSE WAY! ]]"
    echo "[[ If this doesn't work, it's because you didn't check the damn paths below. ]]"
    echo ""
    sleep 1

    # --- (!!!) CRITICAL CONFIGURATION: ARCHITECT, YOU MUST VERIFY/EDIT THESE PATHS (!!!) ---
    # Target OPF Root Directory (MUST BE USER-WRITABLE)
    OPF_ROOT_ABS="$HOME/OmnitidePrimeFoundry"

    # Base path to your OLD project files (where you extracted projectsupload.zip and the ex....work folder contents are)
    OLD_PROJECTS_BASE="$HOME/Projects/projectsupload" # E.g., /home/pong/Projects/projectsupload

    # --- CHOOSE YOUR SEED EX-WORK AGENT ---
    # This is the Ex-Work agent script that will be COPIED into the new OPF 
    # to become 'ex_work_agent_v_current.py', which you will then upgrade.
    # Rick recommends using the 'Ricksway/ex_work_agentv2.py' as we have seen its v2.3 logs.
    # Ensure this path is an EXACT, FULL, ABSOLUTE PATH to the .py file.
    # SOURCE_EXWORK_AGENT_ABS="$OLD_PROJECTS_BASE/Ricksway/ex_work_agentv2.py" 
    # ALTERNATIVE (if you prefer the NPTPAC v2.1 version from projectsupload.zip):
    SOURCE_EXWORK_AGENT_ABS="$OLD_PROJECTS_BASE/NPTPAC/core_agents/ex_work_agentv2.py"
    # ALTERNATIVE (if using one from the ex....work folder, e.g., the v2.2 interactive one - NOT RECOMMENDED FOR THIS SEED):
    # SOURCE_EXWORK_AGENT_ABS="$OLD_PROJECTS_BASE/ex....work/ex_work_agentv2.1.py" #<--- EXAMPLE, VERIFY THIS PATH FROM YOUR UPLOAD

    # --- Paths to other seed files from your OLD NPTPAC structure ---
    SOURCE_SCRIBE_AGENT_ABS="$OLD_PROJECTS_BASE/NPTPAC/core_agents/scribe_agent.py"
    SOURCE_TPC_DEF_ABS="$OLD_PROJECTS_BASE/NPTPAC/ner_repository/02_TPC_STANDARD/TPC_Definition_Latest.md"
    # --- END CRITICAL CONFIGURATION ---


    # Rick's Directives for ExWork-RickPrime (Markdown content)
    # Using single quotes for the main variable to prevent premature expansion inside the heredoc
    RICK_EXWORK_UPGRADE_DIRECTIVES_MD_CONTENT='## ExWork-RickPrime™️ Upgrade Directives By Rick

1. Proactive NER Integration

- Before executing an action that creates an artifact (e.g., CREATE_OR_REPLACE_FILE for Python scripts), especially if the directive is vague, AUTOMATICALLY SEARCH NER for: 
    - Appropriate ExWork Templates for the given task type.
    - TPC Guidelines related to the artifact type.
- If relevant templates are found, PROMPT the Architect to use them or provide parameters. 
- If no specific path for a config file is given (e.g., Scribe profile), automatically look in a conventional NER location.

2. Intelligent Parameterization

- For commonly required parameters (e.g., script_path, output_file), if not provided, attempt to infer from context or NER-based conventions.
- Implement a caching mechanism for frequently accessed NER assets to speed up parameter resolution.

3. Adaptive Error Diagnosis & Self-Healing

- Enhance the `DIAGNOSE_ERROR` action to:
    - Analyze stdout/stderr from failed `RUN_SCRIPT` actions.
    - Identify common Python errors (ImportError, SyntaxError, FileNotFoundError).
    - Use `LLM_INTERFACE` (from NPTPAC/Core) to query an assistant model with the error and output for potential fixes or explanations.
    - Suggest a "patch" file or a sequence of manual commands to apply the fix.
    - Potentially, add an `APPLY_EDITS_TO_FILE` action that could apply LLM-generated changes (after Architect signoff).

4. TPC-Enforcing by Default

- When a `CREATE_OR_REPLACE_FILE` action generates code (e.g., .py, .sh):
    - Automatically invoke Project Scribe on the generated code using a STRICT profile from NER.
    - This only happens if a Scribe profile and profile path is not specified, use a default one.
    - Allow an optional step parameter to skip Scribe (discouraged).
    - If Scribe fails, the ExWork step should fail by default, providing the Scribe report.

5. Chained Execution & State Transfer

- Introduce a more robust way to pass output from one step to another step'\''s input than just `steps_output.`.
- Allow for dependency checks between steps (e.g., step 2 only runs if step 1 succeeded and its output matches a condition).

6. Smarter RUN_SCRIPT

- Auto-detection of shebangs or file extensions to determine how to run a script (e.g., don'\''t require prepending python3 to .py files).
- Better handling of stdout/stderr encoding issues.
- Optional support for running scripts in isolated virtual environments or Docker containers via a new "runtime_environment" parameter.

7. ExWork Self-Auditing & Versioning

- Add a `STATUS_AND_HEALTH` action that checks ExWork'\''s own code structure, dependencies, and Scribe compliance.
- Integrate with NER'\''s version control (Git) to show current ExWork agent version, and the NER hash it was tested against.

8. Documentation Generation

- Add a `CONVERT_TO_DOCUMENTATION` action that takes an ExWork JSON and generates a markdown documentation page for it, listing all parameters, descriptions, and actions. This should use a template from NER.

this is just a start, architect. Feel free to have QO refine it or expand it. The goal is reflection not to produce more.'

# Rick's Strict Scribe Profile (TOML content)
RICK_SCRIBE_PROFILE_TOML_CONTENT='[general]

standard_library_check_enabled = true
enforce_docstrings = true
enforce_type_hints = true
max_line_length = 90
ban_placeholder_code = true # No "pass", "# TODO: Implement", "..."
error_on_placeholders = true

[file_checks]
check_utf8_encoding = true
check_empty_files = true # No empty init.py unless explicitly allowed by rule
lint_json_enabled = true
lint_yaml_enabled = true
fix_json_enabled = true # Auto-fix JSON formatting
fix_yaml_enabled = true # Auto-fix YAML formatting

[python_checks]
linter_enabled = true
formatter_enabled = true
linter_config_path = ".project_root/.pylintrc" # Define these files!
formatter_config_path = ".project_root/pyproject.toml" # Define these files!
run_isort = true
run_black = true
run_pylint = true
run_mypy = true
mypy_config_path = ".project_root/pyproject.toml" # Define these files!
mypy_check_untyped_defs = true

[script_checks] # For .sh files
linter_enabled = true
linter_config_path = ".project_root/.shellcheckrc" # Define this!
run_shellcheck = true
run_shfmt = true
'

MARKER_CONTENT="Omnitide Prime Foundry. No Mortys allowed. Access restricted to beings capable of understanding TPC or Rick Sanchez. Established by Rick's ULTIMATE Shell Bootstrap."

# ---- Function to check if a command exists ----
command_exists() {
    command -v "$1" &> /dev/null
}

# ---- Step 0: Pre-flight checks ----
echo ""
echo "[[ RICK_STEP 0: Pre-flight Sanity Checks ]]"
if ! command_exists git; then
    echo "  [FATAL_RICK_ERROR] 'git' command not found. Git is essential. Install it and make sure it's in your PATH."
    exit 1
fi
if ! command_exists python3; then
    echo "  [FATAL_RICK_ERROR] 'python3' command not found. Python 3 is essential. Install it and make sure it's in your PATH."
    exit 1
fi
if ! python3 -m pip --version &> /dev/null; then
    echo "  [RICK_WARNING] 'pip' for python3 might not be fully installed or configured. Trying 'python3 -m ensurepip --user'."
    python3 -m ensurepip --user
    if ! python3 -m pip --version &> /dev/null; then
         echo "  [FATAL_RICK_ERROR] Still can't find pip. You need pip to install Python packages for the agents later. Fix your Python/pip setup."
         exit 1
    fi
fi
echo "  Pre-flight checks passed (Python3 and Git seem to be available)."

# ---- Step 1: Validate Config & Create OPF Directory Structure ----
echo ""
echo "[[ RICK_STEP 1: Validating Config & Creating OPF Directories at $OPF_ROOT_ABS ]]"
if [ -z "$SOURCE_EXWORK_AGENT_ABS" ] || [ ! -f "$SOURCE_EXWORK_AGENT_ABS" ]; then
    echo "  [FATAL_RICK_ERROR] SOURCE_EXWORK_AGENT_ABS is not set correctly or file not found: '$SOURCE_EXWORK_AGENT_ABS'"
    echo "  Edit this script (rick_ultimate_opf_bootstrap.sh) and fix the path in the CONFIGURATION section!"
    exit 1
fi
if [ ! -f "$SOURCE_SCRIBE_AGENT_ABS" ]; then
    echo "  [FATAL_RICK_ERROR] SOURCE_SCRIBE_AGENT_ABS file not found: '$SOURCE_SCRIBE_AGENT_ABS'. Edit script!"
    exit 1
fi
if [ ! -f "$SOURCE_TPC_DEF_ABS" ]; then
    echo "  [FATAL_RICK_ERROR] SOURCE_TPC_DEF_ABS file not found: '$SOURCE_TPC_DEF_ABS'. Edit script!"
    exit 1
fi

# Create directories idempotently
mkdir -p "$OPF_ROOT_ABS/NPTPAC/core_agents"
mkdir -p "$OPF_ROOT_ABS/NPTPAC/pac_cli"
mkdir -p "$OPF_ROOT_ABS/NPTPAC/ner_repository/02_TPC_STANDARD"
mkdir -p "$OPF_ROOT_ABS/NPTPAC/ner_repository/06_AGENT_BLUEPRINTS/ex_work_agent/docs"
mkdir -p "$OPF_ROOT_ABS/NPTPAC/ner_repository/06_AGENT_BLUEPRINTS/scribe_agent/profiles"
mkdir -p "$OPF_ROOT_ABS/NPTPAC/exwork_tasks"
echo "  OPF Directories created/verified."

# ---- Step 2: Create Marker and .gitkeep Files ----
echo ""
echo "[[ RICK_STEP 2: Creating Marker and .gitkeep files ]]"
echo "$MARKER_CONTENT" > "$OPF_ROOT_ABS/.rick_prime_foundry_established_marker"
echo "  Marker file created."

touch "$OPF_ROOT_ABS/NPTPAC/core_agents/.gitkeep"
touch "$OPF_ROOT_ABS/NPTPAC/pac_cli/.gitkeep"
touch "$OPF_ROOT_ABS/NPTPAC/ner_repository/.gitkeep"
touch "$OPF_ROOT_ABS/NPTPAC/ner_repository/02_TPC_STANDARD/.gitkeep"
touch "$OPF_ROOT_ABS/NPTPAC/ner_repository/06_AGENT_BLUEPRINTS/scribe_agent/profiles/.gitkeep"
touch "$OPF_ROOT_ABS/NPTPAC/exwork_tasks/.gitkeep"
echo "  .gitkeep files created."

# ---- Step 3: Copy Essential Files from OLD Project Structure ----
echo ""
echo "[[ RICK_STEP 3: Copying essential agent and definition files ]]"
cp -vf "$SOURCE_EXWORK_AGENT_ABS" "$OPF_ROOT_ABS/NPTPAC/core_agents/ex_work_agent_v_current.py"
echo "  Copied Ex-Work agent seed to OPF."

cp -vf "$SOURCE_SCRIBE_AGENT_ABS" "$OPF_ROOT_ABS/NPTPAC/core_agents/scribe_agent_v_current.py"
echo "  Copied Scribe agent seed to OPF."

cp -vf "$SOURCE_TPC_DEF_ABS" "$OPF_ROOT_ABS/NPTPAC/ner_repository/02_TPC_STANDARD/TPC_Definition_Foundation.md"
echo "  Copied TPC Definition to OPF NER."

# ---- Step 4: Create Rick's Directives and Scribe Profile in OPF NER ----
echo ""
echo "[[ RICK_STEP 4: Creating Rick's Directives and Scribe Profile ]]"
# Using cat and heredoc for multiline content
cat << EOF_DIRECTIVES > "$OPF_ROOT_ABS/NPTPAC/ner_repository/06_AGENT_BLUEPRINTS/ex_work_agent/docs/ExWork_RickPrime_Upgrade_Directives.md"

$RICK_EXWORK_UPGRADE_DIRECTIVES_MD_CONTENT
EOF_DIRECTIVES
echo "  Rick's ExWork Upgrade Directives created in OPF NER."

cat << EOF_SCRIBE_PROFILE > "$OPF_ROOT_ABS/NPTPAC/ner_repository/06_AGENT_BLUEPRINTS/scribe_agent/profiles/rick_prime_strict.scribe.toml"

$RICK_SCRIBE_PROFILE_TOML_CONTENT
EOF_SCRIBE_PROFILE
echo "  Rick's Strict Scribe Profile created in OPF NER."

# ---- Step 5: Initialize Git Repository in OPF NER ----
echo ""
echo "[[ RICK_STEP 5: Initializing Git repository in OPF NER ]]"
if command -v git &> /dev/null; then
    # Store current CWD
    ORIGINAL_CWD_FOR_GIT_STEP=$(pwd)
    cd "$OPF_ROOT_ABS/NPTPAC/ner_repository" || { echo "  [GIT_ERROR] Could not cd to NER repo ('$OPF_ROOT_ABS/NPTPAC/ner_repository'). Skipping Git init."; cd "$ORIGINAL_CWD_FOR_GIT_STEP"; exit 1; } # Exit if cd fails
    
    # Double check we are in the right place before 'git init'
    if [ "$(pwd)" == "$OPF_ROOT_ABS/NPTPAC/ner_repository" ]; then
        if [ -d ".git" ]; then
            echo "  Git repository already initialized. Wiping .git and re-initializing for a clean state."
            rm -rf .git # Rick wants a CLEAN start for OPF NER
        fi
        git init -b main # Initialize with main branch
        echo "  OPF NER Git repository initialized."
        
        git add .
        # Check if there's anything to commit to avoid error
        if ! git diff-index --quiet HEAD --; then # This checks staged changes against HEAD
            git commit -m "FEAT: Omnitide Prime Foundry - Initial NER structure via Rick's ULTIMATE Shell Bootstrap"
            echo "  OPF NER Git repository initial commit made."
        else
            # If git add . resulted in no changes to be staged (e.g. only .gitkeep which might be gitignored by global config)
            # We still want a root commit if the repo is new.
            # This is tricky if `git add .` truly adds nothing.
            # Let's ensure TPC_Definition_Foundation.md exists and add it specifically if needed.
            if [ -f "02_TPC_STANDARD/TPC_Definition_Foundation.md" ]; then
                git add "02_TPC_STANDARD/TPC_Definition_Foundation.md" 
                # Add other key files explicitly if `git add .` isn't catching them
                git add "06_AGENT_BLUEPRINTS/ex_work_agent/docs/ExWork_RickPrime_Upgrade_Directives.md"
                git add "06_AGENT_BLUEPRINTS/scribe_agent/profiles/rick_prime_strict.scribe.toml"
                git commit -m "FEAT: Omnitide Prime Foundry - Initial NER structure (core assets)" --allow-empty # Allow empty if only .gitkeep was "added"
                echo "  OPF NER Git repository initial commit made (focused on key assets)."
            else
                echo "  OPF NER Git repository - No initial changes to commit (this is odd, check .gitignore or if files were created)."
            fi
        fi
    else
         echo "  [GIT_ERROR] CRITICAL: Still not in NER repo dir ('$OPF_ROOT_ABS/NPTPAC/ner_repository') after cd. This should not happen. Skipping Git init."
    fi
    cd "$ORIGINAL_CWD_FOR_GIT_STEP" # Go back to where the script was run from
else
    echo "  WARNING: 'git' command not found. Skipping NER Git initialization. You'll need to do this MANUALLY."
fi

# ---- Step 6: Reminder for Manual Task & Python Deps for OPF ----
echo ""
echo "[[ RICK_STEP 6: CRITICAL NEXT STEPS FOR YOU, ARCHITECT! ]]"
echo "  The Omnitide Prime Foundry structure should now be created at: $OPF_ROOT_ABS"
echo "  Seed agents ('_v_current.py') and TPC Definition have been COPIED using 'cp'."
echo "  Rick's directives for upgrading Ex-Work are in your new NER."
echo ""
echo "  1. MANUALLY CREATE THE FILE:"
echo "     '$OPF_ROOT_ABS/NPTPAC/exwork_tasks/001_Forge_ExWork_RickPrime.exwork.json'"
echo ""
echo "     Use the DECODED JSON content I will provide for it in our chat RIGHT AFTER this script's output."
echo "     (It's the one that starts with '{\"step_id\": \"forge_exwork_rickprime_agent_v1\", ...}')"
echo ""
echo "  2. INSTALL PYTHON DEPENDENCIES FOR THE NEW OPF AGENTS:"
echo "     The Ex-Work agent (even the seed one) needs 'Jinja2'. The PAC CLI (when you set it up)"
echo "     will need 'Click' and probably others from its old requirements.txt."
echo "     From your RICK_SH_BASELINE shell, run:"
echo "     python3 -m pip install --user Jinja2 Click requests PyYAML python-dotenv ruamel.yaml jsonschema"
echo "     (Added more common deps your Python ecosystem will likely need for TPC dev)."
echo ""
echo "  3. SET UP YOUR PAC CLI (Omnitide Nexus Protocol Toolkit & Prompt Assembler CLI):"
echo "     - Copy your OLD '$OLD_PROJECTS_BASE/NPTPAC/pac_cli/' directory into '$OPF_ROOT_ABS/NPTPAC/pac_cli/'."
echo "     - Carefully examine and run its 'setup_venv.sh' FROM WITHIN '$OPF_ROOT_ABS/NPTPAC/pac_cli/'."
echo "       (You might need to adapt setup_venv.sh if it has hardcoded old paths or assumptions)."
echo "     - EDIT its '$OPF_ROOT_ABS/NPTPAC/pac_cli/app/core/config_manager.py' (or equivalent) to point to the NEW NER path"
echo "       (e.g., '$OPF_ROOT_ABS/NPTPAC/ner_repository'), NEW agent paths (in '$OPF_ROOT_ABS/NPTPAC/core_agents/'), etc., all within OPF."
echo "     - Activate its venv: 'source \"$OPF_ROOT_ABS/NPTPAC/pac_cli/venv/bin/activate\"'"
echo ""
echo "  4. EXECUTE THE FORGE ExWORK-RICKPRIME TASK:"
echo "     Once PAC CLI is set up for OPF and its venv is active, run:"
echo "     npac exwork run \"$OPF_ROOT_ABS/NPTPAC/exwork_tasks/001_Forge_ExWork_RickPrime.exwork.json\""
echo "     (Or, if PAC CLI is giving you grief initially, directly run the copied seed agent: "
echo "      python3 \"$OPF_ROOT_ABS/NPTPAC/core_agents/ex_work_agent_v_current.py\" \"$OPF_ROOT_ABS/NPTPAC/exwork_tasks/001_Forge_ExWork_RickPrime.exwork.json\")"
echo ""
echo "  5. MANUALLY CODE THE ExWORK-RICKPRIME AGENT:"
echo "     That Ex-Work task will guide YOU to edit '$OPF_ROOT_ABS/NPTPAC/core_agents/ex_work_agent_v_current.py'"
echo "     (or its copy '$OPF_ROOT_ABS/NPTPAC/core_agents/ex_work_agent.py') according to my directives"
echo "     to make it the true ExWork-RickPrime."

echo ""
echo "[[ RICK SAYS: ULTIMATE Bootstrap shell script complete. If this didn't mostly work, you're cursed. ]]"
echo "[[ Check for any [FATAL_RICK_ERROR] or [GIT_ERROR] messages above. ]]"
exit 0
```