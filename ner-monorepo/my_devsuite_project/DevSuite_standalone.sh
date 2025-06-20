#!/bin/bash
# Standalone DevSuite - Generated on Wed May 14 03:59:50 PM MDT 2025
# Combines launcher and all modules from ./devsuite

set -euo pipefail

# --- Embedded Common Functions (if _common.sh exists) ---
# --- Embedded Tool Script Functions ---
function run_git_doctor() {

# === Git Remote Diagnoser and Fixer ===
# Automatically checks 'origin' remote, tests connection, and helps fix configuration.
# Adheres to Omnitide Nexus standards for automation and robustness.

set -euo pipefail # Exit on error, unset variable, or pipe failure

REPO_DIR=$(pwd) # Assume running from the repo directory

# --- Helper Functions ---
print_info() {
    echo "[INFO] $1"
}

print_warn() {
    echo "[WARN] $1" >&2
}

print_error() {
    echo "[ERROR] $1" >&2
    exit 1
}

prompt_yes_no() {
    local prompt_message="$1"
    local response
    while true; do
        read -rp "$prompt_message [y/N]: " response
        case "$response" in
            [Yy]* ) return 0;; # Yes
            [Nn]* | "" ) return 1;; # No or Enter
            * ) echo "Please answer yes (y) or no (n).";;
        esac
    done
}

get_remote_url() {
    local remote_name="$1"
    git remote get-url "$remote_name" 2>/dev/null || echo ""
}

test_ssh_connection() {
    local url="$1"
    local host
    local user_host
    # Extract user@host from git@host:path/repo.git format
    if [[ "$url" =~ ^([^@]+@)?([^:]+): ]]; then
        host="${BASH_REMATCH[2]}"
        user_host="$url" # Use full user@host specification if present
        print_info "Testing SSH connection to $host..."
        # Use -T to prevent remote command execution, -o StrictHostKeyChecking=no and BatchMode=yes for automation
        if ssh -T -o StrictHostKeyChecking=accept-new -o BatchMode=yes "$host" 2>&1 | grep -q "successfully authenticated"; then
            print_info "SSH connection successful and authenticated."
            return 0
        else
            print_warn "SSH connection test failed or authentication unsuccessful."
            print_info "Attempting connection again with verbose output for diagnostics:"
            ssh -vT "$host" || true # Show verbose output but don't exit script on failure
            print_warn "Check SSH key setup: Is the correct public key added to $host?"
            print_warn "Ensure ssh-agent is running and the key is added ('ssh-add ~/.ssh/your_private_key')."
            return 1
        fi
    else
        print_warn "Could not extract host from SSH URL: $url"
        return 1
    fi
}

test_repo_accessibility() {
    local remote_name="$1"
    print_info "Attempting to list remote refs for '$remote_name' to check accessibility and existence..."
    if git ls-remote "$remote_name" HEAD > /dev/null 2>&1; then
        print_info "Successfully accessed remote repository '$remote_name'."
        return 0
    else
        print_warn "Failed to access remote repository '$remote_name'."
        print_warn "This could mean:"
        print_warn "  1. The repository URL is correct, but the repo doesn't exist on the server."
        print_warn "  2. You don't have read access (check permissions/SSH keys/HTTPS tokens)."
        print_warn "  3. There's a network issue preventing connection."
        return 1
    fi
}


# --- Main Logic ---

print_info "Starting Git remote diagnosis for repository in: $REPO_DIR"

# 1. Check if it's a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    print_error "This directory ($REPO_DIR) is not a Git repository."
fi
print_info "Confirmed Git repository."

# 2. Check 'origin' remote
ORIGIN_URL=$(get_remote_url "origin")

if [[ -z "$ORIGIN_URL" ]]; then
    # Origin does not exist
    print_warn "Remote 'origin' is not configured for this repository."
    if prompt_yes_no "Do you know the correct URL for the remote repository?"; then
        read -rp "Please enter the correct remote repository URL: " NEW_URL
        if [[ -z "$NEW_URL" ]]; then
             print_error "No URL provided. Aborting."
        fi
        print_info "Adding remote 'origin' with URL: $NEW_URL"
        if git remote add origin "$NEW_URL"; then
            print_info "Successfully added remote 'origin'."
            ORIGIN_URL="$NEW_URL" # Update variable for subsequent checks
             # Recommend initial push command after adding
            local current_branch
            current_branch=$(git symbolic-ref --short HEAD 2>/dev/null || git rev-parse --short HEAD)
            print_info "You might now want to push your branch:"
            print_info "  git push -u origin $current_branch"
        else
            print_error "Failed to add remote 'origin'. Check the URL and try again."
        fi
    else
        print_warn "Please create the repository on your hosting platform (GitHub, GitLab, etc.) first."
        print_warn "Then, re-run this script or use 'git remote add origin <repository_url>' manually."
        exit 0 # Exit gracefully as user needs to perform external action
    fi
else
    # Origin exists
    print_info "Remote 'origin' found with URL: $ORIGIN_URL"
    if ! prompt_yes_no "Is this URL correct?"; then
         read -rp "Please enter the correct remote repository URL: " CORRECT_URL
         if [[ -z "$CORRECT_URL" ]]; then
             print_error "No URL provided. Aborting."
         fi
         print_info "Updating remote 'origin' URL to: $CORRECT_URL"
         if git remote set-url origin "$CORRECT_URL"; then
             print_info "Successfully updated remote 'origin' URL."
             ORIGIN_URL="$CORRECT_URL" # Update variable
         else
             print_error "Failed to update remote 'origin' URL. Check the URL and permissions."
         fi
    fi
fi

# 3. Test connection/accessibility based on protocol
if [[ "$ORIGIN_URL" == git@* || "$ORIGIN_URL" == ssh://* ]]; then
    # SSH URL
    print_info "Detected SSH URL. Testing connection and authentication..."
    test_ssh_connection "$ORIGIN_URL" || true # Run test, don't exit script if it fails initially
    print_info "Testing repository accessibility via ls-remote..."
    test_repo_accessibility "origin" || print_warn "Further investigation needed based on previous messages."

elif [[ "$ORIGIN_URL" == https://* ]]; then
    # HTTPS URL
    print_info "Detected HTTPS URL."
    print_info "Testing repository accessibility via ls-remote..."
    if ! test_repo_accessibility "origin"; then
         print_warn "HTTPS access failed. Common issues:"
         print_warn "  - Incorrect username/password or Personal Access Token (PAT)."
         print_warn "  - Token lacks necessary permissions (e.g., 'repo' scope on GitHub)."
         print_warn "  - Expired token."
         print_warn "  - Check credential manager if used (e.g., git-credential-manager, osxkeychain)."
         print_warn "Try accessing the URL $ORIGIN_URL in your web browser to verify existence and your login."
    fi
else
    print_warn "URL protocol ($ORIGIN_URL) is not recognized as standard SSH or HTTPS. Cannot perform automated connection tests."
fi

# 4. Final advice
print_info "Diagnosis complete."
if git ls-remote origin HEAD > /dev/null 2>&1; then
     print_info "Remote 'origin' appears configured correctly and is accessible."
     print_info "Try running your push command again. If it still fails, check:"
     print_info "  - The specific branch name you are pushing (e.g., 'main', 'master')."
     print_info "  - Write permissions for your user/key/token on the remote repository."
     print_info "  - Any branch protection rules on the remote."
     print_info "You can try a verbose push for more details: git push --verbose origin <branch-name>"
 else
     print_warn "Automated checks suggest issues remain with the remote 'origin' configuration, accessibility, or permissions."
     print_warn "Please review the previous diagnostic messages and take appropriate action."
     print_warn "Common next steps:"
     print_warn "  - Verify repository existence and URL on the hosting platform."
     print_warn "  - Double-check SSH key setup or HTTPS token validity and permissions."
     print_warn "  - Consult your hosting provider's documentation for connection troubleshooting."
fi

exit 0
}

function run_network_doctor() {

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
}

# --- Main Launcher Logic ---

# === DevSuite Launcher ===
# Main TUI menu for launching developer diagnostic/repair tools.

set -euo pipefail

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
SCRIPTS_SUBDIR="scripts"
TOOL_SCRIPTS_PATH="$SCRIPT_DIR/$SCRIPTS_SUBDIR"

# --- Dependency Check ---
if ! command -v gum &> /dev/null; then
    echo "Error: 'gum' command not found." >&2
    echo "Please install gum: https://github.com/charmbracelet/gum" >&2
    # Optionally fallback to dialog or exit
    # if ! command -v dialog &> /dev/null; then
    #   echo "Error: Neither 'gum' nor 'dialog' found. Cannot proceed." >&2
    #   exit 1
    # fi
    # USE_DIALOG=true
    # echo "Warning: 'gum' not found. Falling back to 'dialog' (limited functionality/appearance)." >&2
    exit 1 # Sticking to gum for this implementation
fi

# --- Source Common Functions (Optional but recommended) ---
# if [[ -f "$TOOL_SCRIPTS_PATH/_common.sh" ]]; then
#     source "$TOOL_SCRIPTS_PATH/_common.sh"
# else
#     echo "Warning: Common functions script not found at $TOOL_SCRIPTS_PATH/_common.sh" >&2
# fi

# --- Main Menu ---
while true; do
    gum style \
        --border normal --margin "1" --padding "1" --border-foreground 212 \
        "DevSuite - Developer Diagnostics Toolkit"

    CHOICE=$(gum choose \
        "Git Doctor" \
        "Network Doctor" \
        "Docker Doctor" \
        "Node.js Doctor" \
        "SSH Doctor" \
        "---" \
        "Exit DevSuite")

    # Handle Empty Choice / Esc
    if [[ -z "$CHOICE" ]]; then
        CHOICE="Exit DevSuite"
    fi

    case "$CHOICE" in
        "Git Doctor")
            gum spin --spinner dot --title "Launching Git Doctor..." -- sleep 0.5
            if [[ -f "$TOOL_SCRIPTS_PATH/git_doctor.sh" ]]; then
                bash "$TOOL_SCRIPTS_PATH/git_doctor.sh"
            else
                gum confirm "Script 'git_doctor.sh' not found. Continue?" || break
            fi
            ;;
        "Network Doctor")
             gum spin --spinner dot --title "Launching Network Doctor..." -- sleep 0.5
            if [[ -f "$TOOL_SCRIPTS_PATH/network_doctor.sh" ]]; then
                bash "$TOOL_SCRIPTS_PATH/network_doctor.sh"
            else
                gum confirm "Script 'network_doctor.sh' not found. Continue?" || break
            fi
            ;;
         "Docker Doctor")
             gum spin --spinner dot --title "Launching Docker Doctor..." -- sleep 0.5
            if [[ -f "$TOOL_SCRIPTS_PATH/docker_doctor.sh" ]]; then
                 bash "$TOOL_SCRIPTS_PATH/docker_doctor.sh"
            else
                gum confirm "Script 'docker_doctor.sh' not found. Continue?" || break
            fi
            ;;
         "Node.js Doctor")
             gum spin --spinner dot --title "Launching Node.js Doctor..." -- sleep 0.5
             # Add context check: Look for package.json?
             if [[ ! -f "package.json" ]]; then
                 gum style --foreground 212 "[WARN] No 'package.json' found in current directory ($(pwd)). Node Doctor may have limited context."
                 gum confirm "Continue anyway?" || continue # Use continue to go back to main menu
             fi
             if [[ -f "$TOOL_SCRIPTS_PATH/node_doctor.sh" ]]; then
                 bash "$TOOL_SCRIPTS_PATH/node_doctor.sh"
             else
                 gum confirm "Script 'node_doctor.sh' not found. Continue?" || break
             fi
            ;;
         "SSH Doctor")
             gum spin --spinner dot --title "Launching SSH Doctor..." -- sleep 0.5
            if [[ -f "$TOOL_SCRIPTS_PATH/ssh_doctor.sh" ]]; then
                 bash "$TOOL_SCRIPTS_PATH/ssh_doctor.sh"
            else
                gum confirm "Script 'ssh_doctor.sh' not found. Continue?" || break
            fi
            ;;
        "---")
            # Separator - do nothing
            ;;
        "Exit DevSuite")
            gum style --foreground 2 "Exiting DevSuite. Goodbye!"
            break
            ;;
        *)
            # Should not happen with gum choose, but good practice
            gum style --foreground 1 "Invalid choice."
            sleep 1
            ;;
    esac

    # Pause briefly before showing menu again, unless exiting
    if [[ "$CHOICE" != "Exit DevSuite" ]]; then
        # Using read with -p "" -t 1 -n 1 to effectively pause without message
        # Or a simple sleep:
        # sleep 1
        gum input --placeholder "Press Enter to return to the main menu..." > /dev/null
    fi
done

exit 0
