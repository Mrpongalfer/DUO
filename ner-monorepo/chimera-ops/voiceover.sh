#!/bin/bash

# ==============================================================================
# Automated Voiceover Wizard Script
# ==============================================================================
# Description:
# This script guides you step-by-step to automatically generate a voiceover.
# It uses OpenAI (ChatGPT) to write a script based on your topic,
# and then uses ElevenLabs to turn that script into speech audio.
# It now attempts to list available ElevenLabs voices for selection.
#
# Includes Debug Flags:
# - Set DEBUG_SKIP_OPENAI=true to skip OpenAI call and use placeholder text.
# - Set DEBUG_SKIP_ELEVENLABS=true to skip ElevenLabs call.
#   Example: DEBUG_SKIP_OPENAI=true ./auto_voiceover_wizard.sh
#
# Requirements:
# 1. An active internet connection (unless using debug flags).
# 2. `curl` and `jq` utilities installed. The script will check for these.
# 3. An OpenAI API Key (unless skipping OpenAI).
# 4. An ElevenLabs API Key (unless skipping ElevenLabs).
# ==============================================================================

# --- Configuration ---
OPENAI_MODEL="gpt-4-turbo"                         # Advanced model for script generation
DEFAULT_ELEVENLABS_VOICE_ID="21m00Tcm4TlvDq8ikWAM" # Default voice: "Rachel"
DEFAULT_ELEVENLABS_VOICE_NAME="Rachel (Default)"
ELEVENLABS_MODEL_ID="eleven_multilingual_v2" # High-quality voice model
VOICE_STABILITY=0.55
VOICE_SIMILARITY=0.75
VOICE_STYLE=0.0
VOICE_SPEAKER_BOOST=true

# --- Debug Flags ---
: "${DEBUG_SKIP_OPENAI:=false}"
: "${DEBUG_SKIP_ELEVENLABS:=false}"

# --- Helper Functions ---
log() { echo "[INFO] $1"; }
print_step() {
    echo
    echo "=============================================================================="
    echo " STEP: $1"
    echo "=============================================================================="
}
fail() {
    local m="$1"
    local ec="${2:-1}"
    echo
    echo "[ERROR] $m" >&2
    echo "[ERROR] Script cannot continue." >&2
    exit "$ec"
}
command_exists() { command -v "$1" >/dev/null 2>&1; }

# Check Dependencies
check_dependencies() {
    print_step "Checking System Tools"
    log "Checking if 'curl' and 'jq' are installed..."
    local missing_deps=0
    if [[ "$DEBUG_SKIP_OPENAI" == "false" || "$DEBUG_SKIP_ELEVENLABS" == "false" ]]; then
        if ! command_exists curl; then
            echo "[WARNING] 'curl' not found." >&2
            missing_deps=1
        fi
        if ! command_exists jq; then
            echo "[WARNING] 'jq' not found." >&2
            missing_deps=1
        fi
        if [[ "$missing_deps" -eq 1 ]]; then
            echo "[ACTION NEEDED] Please install missing tools (curl, jq)." >&2
            echo "   - Debian/Ubuntu: sudo apt update && sudo apt install curl jq -y" >&2
            echo "   - Fedora/CentOS: sudo yum install curl jq -y" >&2
            echo "   - macOS (Homebrew): brew install curl jq" >&2
            fail "Missing required system tools." 1
        fi
        log "System tools check passed."
    else
        log "Skipping tool check (Debug flags active)."
    fi
}

# Get API Keys
get_api_keys() {
    if [[ "$DEBUG_SKIP_OPENAI" == "true" && "$DEBUG_SKIP_ELEVENLABS" == "true" ]]; then
        print_step "API Key Setup"
        log "Skipping API key input (Debug flags active)."
        OPENAI_API_KEY="debug_skipped"
        ELEVENLABS_API_KEY="debug_skipped"
        export OPENAI_API_KEY ELEVENLABS_API_KEY
        return
    fi
    print_step "API Key Setup"
    log "API keys needed for OpenAI (script) and ElevenLabs (voice)."
    log "  - OpenAI Key: https://platform.openai.com/account/api-keys"
    log "  - ElevenLabs Key: https://elevenlabs.io/ (Profile/Account Settings)"
    echo
    local openai_key_env="${OPENAI_API_KEY:-}"
    local elevenlabs_key_env="${ELEVENLABS_API_KEY:-}"
    if [[ "$DEBUG_SKIP_OPENAI" == "false" ]]; then
        if [[ -n "$openai_key_env" ]]; then
            log "Using OpenAI API Key from environment."
            OPENAI_API_KEY="$openai_key_env"
        else
            read -s -p "Paste OpenAI API Key: " OPENAI_API_KEY
            echo
            if [[ -z "$OPENAI_API_KEY" ]]; then fail "OpenAI Key empty." 2; fi
            log "OpenAI Key received."
        fi
        echo
    else
        log "Skipping OpenAI Key input."
        OPENAI_API_KEY="debug_skipped"
    fi
    if [[ "$DEBUG_SKIP_ELEVENLABS" == "false" ]]; then
        if [[ -n "$elevenlabs_key_env" ]]; then
            log "Using ElevenLabs API Key from environment."
            ELEVENLABS_API_KEY="$elevenlabs_key_env"
        else
            read -s -p "Paste ElevenLabs API Key: " ELEVENLABS_API_KEY
            echo
            if [[ -z "$ELEVENLABS_API_KEY" ]]; then fail "ElevenLabs Key empty." 2; fi
            log "ElevenLabs Key received."
        fi
    else
        log "Skipping ElevenLabs Key input."
        ELEVENLABS_API_KEY="debug_skipped"
    fi
    export OPENAI_API_KEY ELEVENLABS_API_KEY
}

# Generate Script (OpenAI) - unchanged from previous version
generate_script() {
    local prompt="$1"
    print_step "Generating Script via OpenAI (ChatGPT)"
    if [[ "$DEBUG_SKIP_OPENAI" == "true" ]]; then
        log "[DEBUG] Skipping OpenAI API call."
        echo "Placeholder script text (DEBUG_SKIP_OPENAI=true)."
        return 0
    fi
    log "Sending topic to OpenAI ($OPENAI_MODEL)..."
    log "This might take a moment..."
    local json_payload
    json_payload=$(jq -n --arg model "$OPENAI_MODEL" --arg user_prompt "$prompt" '{model: $model, messages: [{"role": "system", "content": "Generate concise, engaging script for voiceover."}, {"role": "user", "content": $user_prompt}], temperature: 0.7, max_tokens: 1000}')
    local response_body
    response_body=$(mktemp)
    trap 'rm -f "$response_body"' RETURN
    local http_status
    http_status=$(curl -s -L -w '%{http_code}' -X POST "https://api.openai.com/v1/chat/completions" -H "Content-Type: application/json" -H "Authorization: Bearer $OPENAI_API_KEY" -d "$json_payload" -o "$response_body")
    local curl_status=$?
    if [[ $curl_status -ne 0 ]]; then
        log "[ERROR] OpenAI communication failed (curl error: $curl_status)."
        rm -f "$response_body"
        return 1
    fi
    if [[ "$http_status" == "401" || "$http_status" == "403" ]]; then
        log "[ERROR] OpenAI Auth failed (HTTP: $http_status). Check OpenAI API Key."
        rm -f "$response_body"
        return 10
    fi
    if [[ "$http_status" != "200" ]]; then
        log "[ERROR] OpenAI API unexpected status: $http_status."
        if jq -e '.error' "$response_body" >/dev/null 2>&1; then log "[API Error] $(jq -r '.error.message' "$response_body")"; else log "[Response Body] $(cat "$response_body")"; fi
        rm -f "$response_body"
        return 1
    fi
    local script_content
    script_content=$(jq -r '.choices[0].message.content // empty' "$response_body")
    rm -f "$response_body"
    if [[ -z "$script_content" ]]; then
        log "[ERROR] Failed to extract script from OpenAI response."
        return 1
    fi
    log "Script generated successfully!"
    echo "$script_content"
    return 0
}

# --- NEW FUNCTION: List ElevenLabs Voices ---
# Returns:
#   0 on success (voice data echoed to stdout: "ID|Name")
#   11 on ElevenLabs authentication error
#   1 on other API errors or communication failures
list_available_voices() {
    log "Attempting to fetch available voices from ElevenLabs..."

    # Temporary file for response
    local response_body
    response_body=$(mktemp)
    trap 'rm -f "$response_body"' RETURN

    local http_status
    http_status=$(curl -s -L -w '%{http_code}' \
        -X GET "https://api.elevenlabs.io/v1/voices" \
        -H "Accept: application/json" \
        -H "xi-api-key: $ELEVENLABS_API_KEY" \
        -o "$response_body")

    local curl_status=$?
    if [[ $curl_status -ne 0 ]]; then
        log "[ERROR] Failed to communicate with ElevenLabs /v1/voices (curl error: $curl_status)."
        rm -f "$response_body"
        return 1
    fi

    if [[ "$http_status" == "401" ]]; then
        log "[ERROR] ElevenLabs Auth failed fetching voices (HTTP: $http_status). Check ElevenLabs API Key."
        rm -f "$response_body"
        return 11
    fi
    if [[ "$http_status" != "200" ]]; then
        log "[ERROR] ElevenLabs API unexpected status fetching voices: $http_status."
        rm -f "$response_body"
        return 1
    fi

    # Parse the response and output "ID|Name" lines
    if ! jq -e '.voices' "$response_body" >/dev/null 2>&1; then
        log "[ERROR] Invalid response format from ElevenLabs /v1/voices."
        rm -f "$response_body"
        return 1
    fi

    jq -r '.voices[] | "\(.voice_id)|\(.name)"' "$response_body"
    local jq_status=$?
    rm -f "$response_body" # Clean up temp file

    if [[ $jq_status -ne 0 ]]; then
        log "[ERROR] Failed to parse voices from ElevenLabs response."
        return 1
    fi

    # Check if any voices were actually output
    # Need to re-run jq or capture output earlier if we want to check count easily
    # For simplicity, assume success if jq ran okay. Selection logic will handle empty list.
    log "Successfully fetched voice list."
    return 0 # Success
}

# Generate Voiceover (ElevenLabs) - unchanged API call logic
generate_voiceover() {
    local script_text="$1"
    local voice_id="$2"
    local output_file="$3"
    print_step "Generating Voiceover via ElevenLabs"
    if [[ "$DEBUG_SKIP_ELEVENLABS" == "true" ]]; then
        log "[DEBUG] Skipping ElevenLabs API call."
        log "[DEBUG] Pretending voiceover generation was successful."
        return 0
    fi
    log "Sending script to ElevenLabs..."
    log "Using Voice ID: $voice_id"
    log "Saving audio to: $output_file"
    log "This might take moments..."
    local json_payload
    json_payload=$(jq -n --arg text "$script_text" --arg model_id "$ELEVENLABS_MODEL_ID" --argjson stability "$VOICE_STABILITY" --argjson similarity_boost "$VOICE_SIMILARITY" --argjson style "$VOICE_STYLE" --argjson use_speaker_boost "$VOICE_SPEAKER_BOOST" '{text: $text, model_id: $model_id, voice_settings: {stability: $stability, similarity_boost: $similarity_boost, style: $style, use_speaker_boost: $use_speaker_boost}}')
    local http_status
    http_status=$(curl -s -L -w '%{http_code}' --fail -X POST "https://api.elevenlabs.io/v1/text-to-speech/$voice_id" -H "Accept: audio/mpeg" -H "Content-Type: application/json" -H "xi-api-key: $ELEVENLABS_API_KEY" -d "$json_payload" -o "$output_file")
    local curl_status=$?
    if [[ "$http_status" == "401" ]]; then
        log "[ERROR] ElevenLabs Auth failed generating speech (HTTP: $http_status). Check API Key."
        rm -f "$output_file"
        return 11
    fi
    if [[ $curl_status -ne 0 && $curl_status -ne 22 ]] || [[ "$http_status" != "200" && "$http_status" != "401" ]]; then
        log "[ERROR] ElevenLabs communication/save failed."
        log "[Details] curl exit: $curl_status, HTTP status: $http_status"
        if [[ -f "$output_file" ]] && jq -e '.detail' "$output_file" >/dev/null 2>&1; then log "[API Error] $(jq -r '.detail | if type=="object" then .message else . end' "$output_file")"; elif [[ -f "$output_file" ]]; then log "[Raw Snippet] $(head -c 200 "$output_file")"; fi
        rm -f "$output_file"
        return 1
    fi
    if [[ ! -s "$output_file" ]]; then
        log "[ERROR] Output file empty despite successful communication."
        return 1
    fi
    log "Voiceover audio generated successfully!"
    return 0
}

# --- Main Script Execution ---
main() {
    echo "=============================================================================="
    echo " Welcome to the Automated Voiceover Wizard!"
    echo "=============================================================================="
    echo "Generates script via OpenAI, then voiceover via ElevenLabs."
    if [[ "$DEBUG_SKIP_OPENAI" == "true" ]]; then echo "[DEBUG] OpenAI calls will be skipped."; fi
    if [[ "$DEBUG_SKIP_ELEVENLABS" == "true" ]]; then echo "[DEBUG] ElevenLabs calls will be skipped."; fi
    echo
    check_dependencies
    get_api_keys

    # Get Script Topic
    print_step "Script Topic Input"
    log "What topic should the voiceover script be about?"
    local script_prompt=""
    while [[ -z "$script_prompt" ]]; do
        read -p "Enter the topic/prompt for the script: " script_prompt
        if [[ -z "$script_prompt" ]]; then log "[WARNING] Topic cannot be empty."; fi
    done
    log "Topic received: '$script_prompt'"

    # Generate Script & Confirm
    local generated_script
    generated_script=$(generate_script "$script_prompt")
    local script_status=$?
    if [[ $script_status -eq 10 ]]; then fail "OpenAI Auth issue. Check OpenAI API Key." "$script_status"; elif [[ $script_status -ne 0 ]]; then fail "Could not generate script from OpenAI." "$script_status"; fi
    echo
    log "Generated Script Preview:"
    echo "------------------------- SCRIPT PREVIEW -------------------------"
    echo "$generated_script"
    echo "------------------------------------------------------------------"
    local confirm_script=""
    while [[ "$confirm_script" != "y" && "$confirm_script" != "n" ]]; do
        read -p "Proceed with this script? (y/n): " confirm_script
        confirm_script=$(echo "$confirm_script" | tr '[:upper:]' '[:lower:]')
        if [[ "$confirm_script" == "n" ]]; then
            log "Aborting."
            exit 0
        elif [[ "$confirm_script" != "y" ]]; then log "[WARNING] Please enter 'y' or 'n'."; fi
    done
    log "Script confirmed."

    # Get Output Filename
    print_step "Output Audio Filename"
    log "Choose a name for the audio file (e.g., 'output.mp3')."
    local output_filename=""
    while [[ -z "$output_filename" ]]; do
        read -p "Enter desired output filename: " output_filename
        if [[ -z "$output_filename" ]]; then log "[WARNING] Filename cannot be empty."; elif [[ ! "$output_filename" =~ \.mp3$ ]]; then
            log "[WARNING] Recommended filename ends with '.mp3'."
            read -p "Use '$output_filename' anyway? (y/n): " confirm_ext
            if [[ ! "$confirm_ext" =~ ^[Yy]$ ]]; then output_filename=""; fi
        fi
    done
    log "Audio will be saved as: '$output_filename'"

    # --- MODIFIED: Select ElevenLabs Voice ---
    print_step "Select Voice"
    local voice_id=""
    local voice_list_output    # Capture output of list_available_voices
    local list_voices_status=1 # Default to failure

    # Only try listing voices if not skipping ElevenLabs
    if [[ "$DEBUG_SKIP_ELEVENLABS" == "false" ]]; then
        voice_list_output=$(list_available_voices)
        list_voices_status=$?
    else
        log "[DEBUG] Skipping voice listing."
    fi

    if [[ $list_voices_status -eq 0 && -n "$voice_list_output" ]]; then
        log "Available voices found:"
        # Create arrays for select menu
        declare -a voice_options
        declare -a voice_ids
        while IFS='|' read -r id name; do
            # Sanitize name for display if needed (e.g., remove problematic chars)
            voice_options+=("$name ($id)")
            voice_ids+=("$id")
        done <<<"$voice_list_output"

        # Add manual/default options
        voice_options+=("Enter Voice ID Manually")
        voice_options+=("Use Default ($DEFAULT_ELEVENLABS_VOICE_NAME)")

        # Use select for menu
        PS3="Select voice by number: " # Prompt for select
        select opt in "${voice_options[@]}"; do
            local choice_index=$REPLY # User's numeric choice
            # Check if choice is a valid number within the options range
            if [[ "$choice_index" -gt 0 && "$choice_index" -le "${#voice_options[@]}" ]]; then
                # Handle selection based on index
                if [[ "$choice_index" -le "${#voice_ids[@]}" ]]; then
                    # User selected a voice from the list
                    voice_id="${voice_ids[$choice_index - 1]}"
                    log "Selected voice: ${voice_options[$choice_index - 1]}"
                    break
                elif [[ "${voice_options[$choice_index - 1]}" == "Enter Voice ID Manually" ]]; then
                    # Fall through to manual entry below
                    voice_id="" # Ensure voice_id is empty to trigger manual prompt
                    log "Proceeding to manual Voice ID entry."
                    break
                elif [[ "${voice_options[$choice_index - 1]}" == "Use Default ($DEFAULT_ELEVENLABS_VOICE_NAME)" ]]; then
                    # User selected default
                    voice_id="$DEFAULT_ELEVENLABS_VOICE_ID"
                    log "Selected default voice: $DEFAULT_ELEVENLABS_VOICE_NAME"
                    break
                fi
            else
                echo "Invalid selection. Please enter a number from 1 to ${#voice_options[@]}."
            fi
        done
        # Reset PS3 prompt
        PS3=""

    else
        # Failed to list voices or list was empty
        if [[ "$DEBUG_SKIP_ELEVENLABS" == "false" ]]; then
            log "[WARNING] Could not automatically list voices. Please enter manually."
            # If status was 11 (auth error), we already logged it in list_available_voices
            if [[ $list_voices_status -ne 11 ]]; then
                log "[HINT] Check ElevenLabs API key and network connection."
            fi
        fi
        # Ensure voice_id is empty to trigger manual prompt
        voice_id=""
    fi

    # Manual entry prompt if needed (voice_id is still empty)
    if [[ -z "$voice_id" ]]; then
        log "Enter the ElevenLabs Voice ID manually, or press Enter to use default ($DEFAULT_ELEVENLABS_VOICE_NAME)."
        read -p "Enter ElevenLabs Voice ID [default: $DEFAULT_ELEVENLABS_VOICE_ID]: " voice_id_input
        voice_id=${voice_id_input:-$DEFAULT_ELEVENLABS_VOICE_ID}
    fi
    log "Using Voice ID: $voice_id"
    # --- END MODIFIED VOICE SELECTION ---

    # Generate Voiceover
    generate_voiceover "$generated_script" "$voice_id" "$output_filename"
    local voiceover_status=$?

    echo # Newline
    if [[ $voiceover_status -eq 11 ]]; then
        fail "ElevenLabs Auth issue generating speech. Check API Key." "$voiceover_status"
    elif [[ $voiceover_status -ne 0 ]]; then
        fail "Failed to generate voiceover audio." "$voiceover_status"
    else
        print_step "SUCCESS!"
        if [[ "$DEBUG_SKIP_ELEVENLABS" == "true" ]]; then log "[DEBUG] Voiceover generation skipped. No audio file created."; else
            log "Voiceover audio successfully generated and saved as:"
            log " --> $output_filename <--"
            log "Find this file in the same directory where the script was run."
        fi
    fi

    echo
    log "Wizard finished."
    echo "=============================================================================="
    echo
}

# Run main function
main
exit 0
