#!/bin/bash
# metamorphosis.sh - Orchestrator for the Self-Improving Loop

# --- Configuration ---
# The Scribe agent script
SCRIBE_AGENT="scribe0.py"
# The Code Generator helper script
CODE_GENERATOR="llm_code_generator.py"

# The agent we want to perpetually improve.
# Let's start by having Scribe improve Ex-Work.
TARGET_AGENT_DIR="." # Assumes target agent is in the same dir as this script
TARGET_AGENT_FILE="exworkagent0.py" # The file within TARGET_AGENT_DIR

# Temporary files
SCRIBE_REVIEW_JSON="scribe_review_output.json"
NEW_AGENT_CODE_PY="new_generated_agent_code.py"

# Ensure Ollama with gemma:2b (or your chosen model for Scribe) is running.
# Scribe's .scribe.toml in the TARGET_AGENT_DIR should be configured for this.
# For simplicity, this script assumes Scribe will use a .scribe.toml in TARGET_AGENT_DIR if it exists.

# --- Helper Functions ---
log_info() { echo "[METAMORPHOSIS] INFO: $1"; }
log_warn() { echo "[METAMORPHOSIS] WARNING: $1"; }
log_error() { echo "[METAMORPHOSIS] ERROR: $1"; }
cleanup_temp_files() {
    rm -f "$SCRIBE_REVIEW_JSON" "$NEW_AGENT_CODE_PY"
}
trap cleanup_temp_files EXIT # Cleanup on exit

# --- Perpetual Loop ---
log_info "--- Initiating Metamorphic Loop ---"
log_info "Target for improvement: ${TARGET_AGENT_DIR}/${TARGET_AGENT_FILE}"
if [ ! -f "${TARGET_AGENT_DIR}/${TARGET_AGENT_FILE}" ]; then
    log_error "Target agent file '${TARGET_AGENT_DIR}/${TARGET_AGENT_FILE}' not found. Exiting."
    exit 1
fi
if [ ! -f "$SCRIBE_AGENT" ]; then
    log_error "Scribe agent script '${SCRIBE_AGENT}' not found. Exiting."
    exit 1
fi
if [ ! -f "$CODE_GENERATOR" ]; then
    log_error "Code generator script '${CODE_GENERATOR}' not found. Exiting."
    exit 1
fi


# Ensure the target directory is a Git repository
if [ ! -d "${TARGET_AGENT_DIR}/.git" ]; then
    log_info "Target directory '${TARGET_AGENT_DIR}' is not a Git repository. Initializing..."
    (cd "${TARGET_AGENT_DIR}" && git init && git add . && git commit -m "Initial commit for Metamorphic Loop" --allow-empty)
    if [ $? -ne 0 ]; then
        log_error "Failed to initialize Git repository in '${TARGET_AGENT_DIR}'. Exiting."
        exit 1
    fi
fi

# Ensure Ollama service is running
log_info "Checking if Ollama service is accessible..."
if ! curl -s http://localhost:11434/health | grep -q 'OK'; then
    log_error "Ollama service is not running or accessible. Exiting."
    exit 1
fi
log_info "Ollama service is running and accessible."


while true; do
    echo
    log_info "================ Starting New Improvement Cycle at $(date) ================"
    
    # --- STEP 1: Scribe performs a review to find an improvement ---
    log_info "Asking Scribe to review '${TARGET_AGENT_FILE}' for improvements..."
    # Note: Assuming scribe0.py and target agent are in the same directory (PROJECT_DIR)
    # Scribe will use its own config (.scribe.toml) if present in PROJECT_DIR
    python3 "${SCRIBE_AGENT}" "${TARGET_AGENT_DIR}" \
        --source-file "${TARGET_AGENT_FILE}" \
        --target-file "${TARGET_AGENT_FILE}" \
        --review-only \
        --log-level INFO \
        > "${SCRIBE_REVIEW_JSON}"

    if [ $? -ne 0 ]; then
        log_error "Scribe failed during the review phase. Review '${SCRIBE_REVIEW_JSON}'. Pausing for 5 minutes."
        sleep 300
        continue
    fi
    log_info "Scribe review phase completed. Report in '${SCRIBE_REVIEW_JSON}'."

    # --- STEP 2: Extract the improvement suggestion from Scribe's report ---
    log_info "Parsing Scribe's review for a suggestion..."
    # Takes the first suggestion. jq handles 'null' gracefully (outputs "null" string).
    suggestion=$(jq -r '.ai_review_findings[0].description // empty' "${SCRIBE_REVIEW_JSON}")

    if [ -z "$suggestion" ] || [ "$suggestion" == "null" ]; then
        log_warn "No improvement suggestions found by Scribe's AI review this cycle, or failed to parse. The agent may be perfect (for now) or review failed! Checking again in 5 minutes."
        sleep 300
        continue
    fi
    log_info "Improvement suggestion found: \"${suggestion}\""

    # --- STEP 3: Generate new code based on the suggestion ---
    log_info "Asking Code Synthesis script to generate new code for '${TARGET_AGENT_FILE}'..."
    python3 "${CODE_GENERATOR}" "${TARGET_AGENT_DIR}/${TARGET_AGENT_FILE}" "${suggestion}" "${NEW_AGENT_CODE_PY}"

    if [ $? -ne 0 ] || [ ! -s "${NEW_AGENT_CODE_PY}" ]; then
        log_error "Code generation failed or produced an empty file. Skipping this cycle. Check logs from ${CODE_GENERATOR}."
        sleep 60
        continue
    fi
    log_info "New code generated and saved to '${NEW_AGENT_CODE_PY}'."

    # --- STEP 4: Scribe applies and validates the new code ---
    log_info "Asking Scribe to apply, validate, and commit the new code to '${TARGET_AGENT_FILE}'..."
    # We want Scribe to commit this time.
    python3 "${SCRIBE_AGENT}" "${TARGET_AGENT_DIR}" \
        --source-file "${NEW_AGENT_CODE_PY}" \
        --target-file "${TARGET_AGENT_FILE}" \
        --commit \
        --log-level INFO 
        # Let Scribe produce its JSON report to stdout for manual inspection if needed

    if [ $? -ne 0 ]; then
        log_error "Scribe failed to apply/validate the new code. The change was likely NOT committed. Review Scribe output. Pausing for 5 minutes."
        sleep 300
    else
        log_info "SUCCESS! Scribe successfully applied and committed the improvement to '${TARGET_AGENT_FILE}'."
        log_info "Latest commit in '${TARGET_AGENT_DIR}':"
        (cd "${TARGET_AGENT_DIR}" && git log -1 --pretty=oneline)
    fi
    
    log_info "Cycle complete. Pausing for 60 seconds before starting next cycle..."
    sleep 60
done
