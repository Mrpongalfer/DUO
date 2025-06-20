    #!/bin/bash
    # Rick's "Enough of this Ex-Work Bootstrap Bullshit" Shell Script - v1.0
    # This script sets up the Omnitide Prime Foundry (OPF) directly.
    # It assumes it's being run by a user who can write to $HOME.
    # It assumes your OLD project files (from projectsupload.zip) are accessible.

    echo "[[ RICK SAYS: Starting Omnitide Prime Foundry Bootstrap - No More Games! ]]"
    echo ""

    # --- CONFIGURATION: ARCHITECT, VERIFY THESE PATHS! ---
    # Target OPF Root Directory (MUST BE USER-WRITABLE)
    OPF_ROOT_ABS="$HOME/OmnitidePrimeFoundry"

    # Source paths for OLD files (from your projectsupload extraction)
    # Adjust these if your 'projectsupload' content is elsewhere or if you prefer a different seed Ex-Work.
    OLD_PROJECTS_BASE="$HOME/Projects/projectsupload" # Base path to your extracted zip

    # Path to the Ex-Work agent you want to SEED into OPF
    # I'm choosing the one from Ricksway because it's the last one we saw logs from (v2.3 "Apex")
    # If the NPTPAC one (v2.1) is more stable, change this.
    SOURCE_EXWORK_AGENT_ABS="$OLD_PROJECTS_BASE/Ricksway/ex_work_agentv2.py" 

    SOURCE_SCRIBE_AGENT_ABS="$OLD_PROJECTS_BASE/NPTPAC/core_agents/scribe_agent.py"
    SOURCE_TPC_DEF_ABS="$OLD_PROJECTS_BASE/NPTPAC/ner_repository/02_TPC_STANDARD/TPC_Definition_Latest.md"
    # --- END CONFIGURATION ---

    # Function to Base64 encode (cross-platform-ish attempt for inline content)
    # Tries `base64 -w0` (Linux), then `base64` (macOS might not need -w0 or might have it by default)
    # For truly empty string, output is empty string.
    rick_b64_encode() {
        if [ -z "$1" ]; then
            echo -n ""
        else
            echo -n "$1" | base64 -w0 2>/dev/null || echo -n "$1" | base64
        fi
    }

    # Rick's Directives for ExWork-RickPrime (Markdown content)
    # (Same content as before, just directly in the script)
    RICK_EXWORK_UPGRADE_DIRECTIVES_MD_CONTENT="## ExWork-RickPrime™️ Upgrade Directives By Rick

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

- Enhance the \`DIAGNOSE_ERROR\` action to:
    - Analyze stdout/stderr from failed \`RUN_SCRIPT\` actions.
    - Identify common Python errors (ImportError, SyntaxError, FileNotFoundError).
    - Use \`LLM_INTERFACE\` (from NPTPAC/Core) to query an assistant model with the error and output for potential fixes or explanations.
    - Suggest a \"patch\" file or a sequence of manual commands to apply the fix.
    - Potentially, add an \`APPLY_EDITS_TO_FILE\` action that could apply LLM-generated changes (after Architect signoff).

4. TPC-Enforcing by Default

- When a \`CREATE_OR_REPLACE_FILE\` action generates code (e.g., .py, .sh):
    - Automatically invoke Project Scribe on the generated code using a STRICT profile from NER.
    - This only happens if a Scribe profile and profile path is not specified, use a default one.
    - Allow an optional step parameter to skip Scribe (discouraged).
    - If Scribe fails, the ExWork step should fail by default, providing the Scribe report.

5. Chained Execution & State Transfer

- Introduce a more robust way to pass output from one step to another step's input than just \`steps_output.\`.
- Allow for dependency checks between steps (e.g., step 2 only runs if step 1 succeeded and its output matches a condition).

6. Smarter `RUN_SCRIPT`

- Auto-detection of shebangs or file extensions to determine how to run a script (e.g., don't require prepending python3 to .py files).
- Better handling of stdout/stderr encoding issues.
- Optional support for running scripts in isolated virtual environments or Docker containers via a new \"runtime_environment\" parameter.

7. ExWork Self-Auditing & Versioning

- Add a \`STATUS_AND_HEALTH\` action that checks ExWork's own code structure, dependencies, and Scribe compliance.
- Integrate with NER's version control (Git) to show current ExWork agent version, and the NER hash it was tested against.

8. Documentation Generation

- Add a \`CONVERT_TO_DOCUMENTATION\` action that takes an ExWork JSON and generates a markdown documentation page for it, listing all parameters, descriptions, and actions. This should use a template from NER.

this is just a start, architect. Feel free to have QO refine it or expand it. The goal is reflection not to produce more."
RICK_EXWORK_UPGRADE_DIRECTIVES_B64=$(rick_b64_encode "$RICK_EXWORK_UPGRADE_DIRECTIVES_MD_CONTENT")

# Rick's Strict Scribe Profile (TOML content)
RICK_SCRIBE_PROFILE_TOML_CONTENT="[general]

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
"
RICK_SCRIBE_PROFILE_B64=$(rick_b64_encode "$RICK_SCRIBE_PROFILE_TOML_CONTENT")

# Marker file content
MARKER_CONTENT="Omnitide Prime Foundry. No Mortys allowed. Access restricted to beings capable of understanding TPC or Rick Sanchez. Established by Rick's Shell Bootstrap."
MARKER_CONTENT_B64=$(rick_b64_encode "$MARKER_CONTENT")

# ---- Step 1: Create OPF Directory Structure ----
echo ""
echo "[[ RICK_STEP 1: Creating OPF Directory Structure at $OPF_ROOT_ABS ]]"
mkdir -p "$OPF_ROOT_ABS/NPTPAC/core_agents"
mkdir -p "$OPF_ROOT_ABS/NPTPAC/pac_cli"
mkdir -p "$OPF_ROOT_ABS/NPTPAC/ner_repository/02_TPC_STANDARD"
mkdir -p "$OPF_ROOT_ABS/NPTPAC/ner_repository/06_AGENT_BLUEPRINTS/ex_work_agent/docs"
mkdir -p "$OPF_ROOT_ABS/NPTPAC/ner_repository/06_AGENT_BLUEPRINTS/scribe_agent/profiles"
mkdir -p "$OPF_ROOT_ABS/NPTPAC/exwork_tasks"
echo "  OPF Directories created."

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
if [ -f "$SOURCE_EXWORK_AGENT_ABS" ]; then
    cp "$SOURCE_EXWORK_AGENT_ABS" "$OPF_ROOT_ABS/NPTPAC/core_agents/ex_work_agent_v_current.py"
    echo "  Copied Ex-Work agent to OPF."
else
    echo "  ERROR: Source Ex-Work agent NOT FOUND at $SOURCE_EXWORK_AGENT_ABS. Skipping copy."
fi

if [ -f "$SOURCE_SCRIBE_AGENT_ABS" ]; then
    cp "$SOURCE_SCRIBE_AGENT_ABS" "$OPF_ROOT_ABS/NPTPAC/core_agents/scribe_agent_v_current.py"
    echo "  Copied Scribe agent to OPF."
else
    echo "  ERROR: Source Scribe agent NOT FOUND at $SOURCE_SCRIBE_AGENT_ABS. Skipping copy."
fi

if [ -f "$SOURCE_TPC_DEF_ABS" ]; then
    cp "$SOURCE_TPC_DEF_ABS" "$OPF_ROOT_ABS/NPTPAC/ner_repository/02_TPC_STANDARD/TPC_Definition_Foundation.md"
    echo "  Copied TPC Definition to OPF NER."
else
    echo "  ERROR: Source TPC Definition NOT FOUND at $SOURCE_TPC_DEF_ABS. Skipping copy."
fi

# ---- Step 4: Create Rick's Directives and Scribe Profile in OPF NER ----
echo ""
echo "[[ RICK_STEP 4: Creating Rick's Directives and Scribe Profile ]]"
echo "$RICK_EXWORK_UPGRADE_DIRECTIVES_MD_CONTENT" > "$OPF_ROOT_ABS/NPTPAC/ner_repository/06_AGENT_BLUEPRINTS/ex_work_agent/docs/ExWork_RickPrime_Upgrade_Directives.md"
echo "  Rick's ExWork Upgrade Directives created in OPF NER."

echo "$RICK_SCRIBE_PROFILE_TOML_CONTENT" > "$OPF_ROOT_ABS/NPTPAC/ner_repository/06_AGENT_BLUEPRINTS/scribe_agent/profiles/rick_prime_strict.scribe.toml"
echo "  Rick's Strict Scribe Profile created in OPF NER."

# ---- Step 5: Initialize Git Repository in OPF NER ----
echo ""
echo "[[ RICK_STEP 5: Initializing Git repository in OPF NER ]]"
if command -v git &> /dev/null; then
    cd "$OPF_ROOT_ABS/NPTPAC/ner_repository" || exit 1
    git init
    git add .
    git commit -m "FEAT: Omnitide Prime Foundry - Initial NER structure via Rick's Shell Bootstrap"
    echo "  OPF NER Git repository initialized and committed."
    cd "$OLDPWD" # Go back to where the script was run from
else
    echo "  WARNING: 'git' command not found. Skipping NER Git initialization. You'll need to do this manually."
fi

# ---- Step 6: Reminder for Manual Task ----
echo ""
echo "[[ RICK_STEP 6: CRITICAL MANUAL TASK FOR YOU, ARCHITECT! ]]"
echo "  The Omnitide Prime Foundry structure is created at: $OPF_ROOT_ABS"
echo "  Essential agents and definitions have been COPIED."
echo "  Rick's directives for upgrading Ex-Work are in your new NER."
echo ""
echo "  YOUR NEXT JOB IS TO MANUALLY CREATE THE FILE:"
echo "    $OPF_ROOT_ABS/NPTPAC/exwork_tasks/001_Forge_ExWork_RickPrime.exwork.json"
echo ""
echo "  Use the DECODED JSON content I provided in our previous communications for that file."
echo "  (It's the one that starts with '{\"step_id\": \"forge_exwork_rickprime_agent_v1\", ...}')"
echo ""
echo "  Once that file is created, your next step will be to set up your PAC CLI"
echo "  to operate from WITHIN $OPF_ROOT_ABS/NPTPAC/pac_cli/, pointing to the"
echo "  agents and NER inside $OPF_ROOT_ABS, and then use it (or the python script directly)"
echo "  to run '$OPF_ROOT_ABS/NPTPAC/exwork_tasks/001_Forge_ExWork_RickPrime.exwork.json'."
echo "  That task will then guide YOU through MANUALLY CODING the ExWork-RickPrime agent."

echo ""
echo "[[ RICK SAYS: Bootstrap complete (maybe). Don't screw up the manual part. ]]"
exit 0
