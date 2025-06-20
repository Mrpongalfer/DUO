#!/bin/bash

# === Network Doctor ===
# Diagnose common network connectivity issues using gum.

set -euo pipefail

# --- Dependency Check ---
# Assume main script checked for gum, but check for network tools
check_command() {
    if ! command -v "$1" &> /dev/null; then
        gum style --foreground 1 "Error: Required command '$1' not found. Please install it."
        exit 1
    fi
}
check_command ping
check_command dig # or nslookup
check_command traceroute # or tracepath
check_command curl

# --- Helper Functions ---
show_status() {
    local status="$1" # "Success", "Failure", "Info"
    local message="$2"
    local color="2" # Default Green for Success

    if [[ "$status" == "Failure" ]]; then
        color="1" # Red
    elif [[ "$status" == "Info" ]]; then
        color="4" # Blue
    elif [[ "$status" == "Warn" ]]; then
        color="3" # Yellow
    fi

    gum style --foreground "$color" "[$status] $message"
}

run_command_spin() {
    local title="$1"
    shift
    local cmd_string="$@"
    local output
    local exit_code=0

    # Use process substitution and tee to capture output and exit code
    output=$( (eval "$cmd_string") 2>&1 | tee /dev/fd/3; exit "${PIPESTATUS[0]}" ) 3>&1
    exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        show_status "Success" "$title completed."
    else
        show_status "Failure" "$title failed (Exit Code: $exit_code)."
    fi
    echo "--- Output ---"
    gum style --faint "$output"
    echo "--------------"
    return $exit_code
}


# --- Tool Menu ---
while true; do
    gum style --border normal --margin "1" --padding "1" --border-foreground 212 "Network Doctor"

    ACTION=$(gum choose \
        "Ping Host" \
        "Check DNS Resolution" \
        "Trace Route to Host" \
        "Check Remote Port (TCP)" \
        "Check Local Port Listening" \
        "---" \
        "Back to Main Menu")

     if [[ -z "$ACTION" ]]; then
        ACTION="Back to Main Menu"
     fi

    case "$ACTION" in
        "Ping Host")
            TARGET_HOST=$(gum input --placeholder "Enter hostname or IP address (e.g., google.com)")
            if [[ -n "$TARGET_HOST" ]]; then
                # Use -c 4 for 4 packets, adjust as needed
                run_command_spin "Pinging $TARGET_HOST" "ping -c 4 '$TARGET_HOST'" || true # Don't exit script on failure
            fi
            ;;

        "Check DNS Resolution")
            TARGET_HOST=$(gum input --placeholder "Enter hostname to resolve (e.g., github.com)")
             if [[ -n "$TARGET_HOST" ]]; then
                DNS_SERVER=$(gum input --placeholder "Optional: DNS server (e.g., 8.8.8.8) - leave empty for default")
                CMD="dig '$TARGET_HOST'"
                if [[ -n "$DNS_SERVER" ]]; then
                    CMD="dig @'$DNS_SERVER' '$TARGET_HOST'"
                fi
                 run_command_spin "Resolving $TARGET_HOST" "$CMD" || true
            fi
            ;;

        "Trace Route to Host")
            TARGET_HOST=$(gum input --placeholder "Enter hostname or IP address (e.g., 1.1.1.1)")
             if [[ -n "$TARGET_HOST" ]]; then
                # traceroute options vary (e.g., -I for ICMP on some Linux, default on macOS)
                # Using a common option, may need adjustment based on OS
                CMD="traceroute '$TARGET_HOST'"
                if [[ "$(uname)" == "Linux" ]]; then
                    # Try common Linux options, -q 1 (1 probe), -w 2 (2 sec wait)
                     CMD="traceroute -q 1 -w 2 '$TARGET_HOST'"
                fi
                 run_command_spin "Tracing route to $TARGET_HOST" "$CMD" || true
            fi
            ;;

        "Check Remote Port (TCP)")
            TARGET_HOST=$(gum input --placeholder "Enter hostname or IP address")
            TARGET_PORT=$(gum input --placeholder "Enter port number (e.g., 80, 443)")
            if [[ -n "$TARGET_HOST" && -n "$TARGET_PORT" ]]; then
                 # Using curl for better cross-platform compatibility and info than nc
                 # Timeout set to 5 seconds
                 run_command_spin "Checking TCP connection to $TARGET_HOST:$TARGET_PORT" \
                    "curl --connect-timeout 5 -v telnet://$TARGET_HOST:$TARGET_PORT" || true
                 show_status "Info" "Curl attempts a TELNET handshake. 'Connected to...' indicates port is open. 'Connection refused' or 'timed out' indicates closed/filtered."
            fi
            ;;

        "Check Local Port Listening")
            TARGET_PORT=$(gum input --placeholder "Enter local port number to check")
            if [[ -n "$TARGET_PORT" ]]; then
                show_status "Info" "Checking for listeners on port $TARGET_PORT..."
                LISTEN_OUTPUT=""
                LISTEN_FOUND=false
                if command -v ss &> /dev/null; then
                    LISTEN_OUTPUT=$(ss -tulnp | grep ":$TARGET_PORT ") || true # Ignore grep exit code if not found
                elif command -v netstat &> /dev/null; then
                     # Netstat args vary wildly between OS (Linux vs macOS vs Windows)
                     # Trying a common Linux format
                     LISTEN_OUTPUT=$(netstat -tulnp | grep ":$TARGET_PORT ") || true # Linux
                     if [[ -z "$LISTEN_OUTPUT" && "$(uname)" == "Darwin" ]]; then
                         LISTEN_OUTPUT=$(netstat -anp tcp | grep "[.:]$TARGET_PORT .*LISTEN") || true # macOS variant
                     fi
                else
                    show_status "Warn" "Neither 'ss' nor 'netstat' found. Cannot check local ports automatically."
                    continue # Back to menu
                fi

                if [[ -n "$LISTEN_OUTPUT" ]]; then
                    show_status "Success" "Port $TARGET_PORT appears to be listening."
                    echo "$LISTEN_OUTPUT" | gum table
                    LISTEN_FOUND=true
                else
                     show_status "Failure" "No process found listening on TCP or UDP port $TARGET_PORT."
                fi
            fi
            ;;

        "---")
            ;;
        "Back to Main Menu")
            break # Exit the inner loop, devsuite.sh will show main menu again
            ;;
        *)
            show_status "Warn" "Invalid action selected."
            sleep 1
            ;;
    esac
     # Pause before showing Network Doctor menu again
     gum input --placeholder "Press Enter to continue..." > /dev/null
done

exit 0