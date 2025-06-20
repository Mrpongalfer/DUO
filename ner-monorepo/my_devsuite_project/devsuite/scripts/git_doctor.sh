#!/bin/bash

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