#!/bin/bash

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