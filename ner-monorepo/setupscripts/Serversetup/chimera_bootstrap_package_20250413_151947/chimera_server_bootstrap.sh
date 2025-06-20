# Run this block ON YOUR Pop!_OS Machine (192.168.0.96) as user 'pong'

# STEP 1: Append SERVER's public key to CLIENT's authorized_keys
echo "[Pop\!_OS] Adding server's (aiseed@192.168.0.95) public key to pong's authorized_keys..."
mkdir -p ~/.ssh && chmod 700 ~/.ssh || { echo "ERROR: Failed mkdir/chmod ~/.ssh"; exit 1; }
# CAREFULLY Paste the public key copied from the server output inside the quotes below:
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICRjUBSf0xzNgdJRxUfoJ3fNDhfeXdGWiE2tb0EzXssA aiseed@thosedataguys-s" >> ~/.ssh/authorized_keys || \
 { echo "ERROR: Failed to append key. Check permissions or paste format."; exit 1; }

# STEP 2: Ensure Correct Permissions and Remove Duplicates
sort -u ~/.ssh/authorized_keys -o ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys || { echo "ERROR: Failed chmod authorized_keys"; exit 1; }
echo "[Pop\!_OS] Server key added to local authorized_keys."

#!/bin/bash
#
# Project Chimera v2.7 - Elite Linux SERVER Setup Bootstrap Script
# Target: Ubuntu Server (Assumes UFW)
# Version: 1.2 (Core Team Synthesis Derived, Server-Focused, Enhanced Automation)
#
# PURPOSE: Performs initial server hardening, installs essential admin & server tools,
#          prepares the server for Ansible management (incl. client key gen),
#          clones config repo, generates basic inventory, and offers initial playbook run.
#
# PRE-REQUISITES: 'bootstrap.conf' must exist in the same directory.
#
# WARNING: Review bootstrap.conf carefully before execution.
#          Execute with root privileges (e.g., using sudo).
#

set -e
# set -x

CONFIG_FILE="bootstrap.conf"

# --- Helper Functions ---
log_info() { echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $1"; }
log_warn() { echo "[WARN] $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2; }
log_error() { echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2; exit 1; }

# Check root & Source Config
check_root() { if [ "$(id -u)" -ne 0 ]; then log_error "This script must be run as root or with sudo."; fi; }
load_config() {
    if [ -f "${CONFIG_FILE}" ]; then
        log_info "Loading configuration from ${CONFIG_FILE}..."
        # shellcheck source=bootstrap.conf disable=SC1091
        source "${CONFIG_FILE}"
        local required_vars=(ADMIN_USER ADMIN_USER_SSH_PUBKEY CONFIG_REPO_URL ALLOWED_CLIENT_SUBNET INITIAL_PLAYBOOK)
        for var in "${required_vars[@]}"; do if [ -z "${!var}" ]; then log_error "Required var '${var}' not set in ${CONFIG_FILE}."; fi; done
    else log_error "Configuration file ${CONFIG_FILE} not found."; fi
}

# Detect Pkg Mgr (Simplified)
detect_pkg_manager() { if command -v apt-get &> /dev/null; then PKG_INSTALL="apt-get install -y"; PKG_UPDATE="apt-get update"; else log_error "apt not found. Ubuntu required."; fi; }

# Configure Timezone
configure_timezone() { log_info "Configuring timezone to ${SYSTEM_TIMEZONE}..."; timedatectl set-timezone "${SYSTEM_TIMEZONE}" || log_warn "Failed timezone set."; log_info "Current time: $(date)"; }

# Setup User & SSH Key for Access
setup_admin_user() {
    log_info "Setting up admin user '${ADMIN_USER}'...";
    if ! id "${ADMIN_USER}" &>/dev/null; then useradd -m -s "${ADMIN_USER_SHELL}" -G sudo "${ADMIN_USER}" || log_error "Failed useradd."; log_info "User '${ADMIN_USER}' created."; else log_info "User '${ADMIN_USER}' exists."; fi;
    local ssh_dir="/home/${ADMIN_USER}/.ssh"; local auth_keys_file="${ssh_dir}/authorized_keys";
    mkdir -p "${ssh_dir}" || log_error "Failed mkdir ${ssh_dir}."; echo "${ADMIN_USER_SSH_PUBKEY}" > "${auth_keys_file}" || log_error "Failed writing pubkey.";
    chown -R "${ADMIN_USER}:${ADMIN_USER}" "${ssh_dir}" || log_error "Failed chown ${ssh_dir}."; chmod 700 "${ssh_dir}" || log_error "Failed chmod 700."; chmod 600 "${auth_keys_file}" || log_error "Failed chmod 600.";
    log_info "SSH public key configured for '${ADMIN_USER}' access.";
}

# Harden SSHD
harden_ssh() {
    log_info "Hardening SSHD config..."; local sshd_config="/etc/ssh/sshd_config"; cp "${sshd_config}" "${sshd_config}.bak_$(date +%F_%T)";
    sed -i "s/^#*Port .*/Port ${SSH_PORT}/g" "${sshd_config}"; sed -i "s/^#*PermitRootLogin .*/PermitRootLogin no/g" "${sshd_config}";
    sed -i "s/^#*PasswordAuthentication .*/PasswordAuthentication no/g" "${sshd_config}"; sed -i "s/^#*ChallengeResponseAuthentication .*/ChallengeResponseAuthentication no/g" "${sshd_config}";
    sed -i "s/^#*UsePAM .*/UsePAM yes/g" "${sshd_config}"; sed -i "s/^#*PermitEmptyPasswords .*/PermitEmptyPasswords no/g" "${sshd_config}";
    sed -i "s/^#*X11Forwarding .*/X11Forwarding no/g" "${sshd_config}"; sed -i "s/^#*AllowAgentForwarding .*/AllowAgentForwarding yes/g" "${sshd_config}";
    sed -i "s/^#*MaxAuthTries .*/MaxAuthTries 3/g" "${sshd_config}"; sed -i "s/^#*LoginGraceTime .*/LoginGraceTime 60/g" "${sshd_config}";
    if ! grep -q "^AllowUsers ${ADMIN_USER}" "${sshd_config}"; then echo "AllowUsers ${ADMIN_USER}" >> "${sshd_config}"; fi;
    if ! grep -q "^Protocol 2" "${sshd_config}"; then echo "Protocol 2" >> "${sshd_config}"; fi;
    sshd -t || log_warn "sshd config test failed."; systemctl restart sshd || log_warn "sshd restart failed."; log_info "SSHD hardened.";
}

# Install Packages
install_packages() {
    log_info "Updating package lists..."; ${PKG_UPDATE} || log_warn "apt update failed.";
    local packages_to_install="${ANSIBLE_CORE_PACKAGES} ${EXTRA_PACKAGES} ${SERVER_PACKAGES} ${DOCKER_PACKAGES}"
    log_info "Installing packages..."; echo "Packages: ${packages_to_install}" # Show list
    # shellcheck disable=SC2086
    if ! ${PKG_INSTALL} ${packages_to_install}; then
         log_warn "Failed initial package install batch. Retrying individually...";
         # shellcheck disable=SC2086
         for pkg in ${packages_to_install}; do log_info "Installing ${pkg}..."; ${PKG_INSTALL} "${pkg}" || log_warn "Failed: ${pkg}"; done
    fi;
    log_info "Package install phase complete.";
    if [[ -n "$DOCKER_PACKAGES" ]] && command -v docker &> /dev/null; then
        if ! getent group docker > /dev/null; then log_info "Creating docker group..."; groupadd docker || log_warn "Failed groupadd docker."; fi;
        log_info "Adding '${ADMIN_USER}' to docker group..."; usermod -aG docker "${ADMIN_USER}" || log_warn "Failed usermod docker.";
        if [ "$ENABLE_DOCKER_ON_BOOT" = true ]; then log_info "Enabling Docker..."; systemctl enable docker && systemctl start docker || log_warn "Docker service enable/start failed."; fi;
    fi;
    if command -v pip3 &> /dev/null; then log_info "Installing pip packages..."; pip3 install --upgrade pip && pip3 install virtualenv docker || log_warn "Pip install failed."; else log_warn "pip3 not found."; fi;
}

# Configure Firewall (UFW)
configure_firewall() {
    log_info "Configuring firewall (ufw)...";
    if ! command -v ufw &> /dev/null; then log_warn "ufw not found, installing..."; ${PKG_INSTALL} ufw || log_error "Failed ufw install."; fi;
    log_info "Allowing SSH port ${SSH_PORT} from ${ALLOWED_CLIENT_SUBNET}..."; ufw allow from "${ALLOWED_CLIENT_SUBNET}" to any port "${SSH_PORT}" proto tcp || log_warn "Failed rule: SSH.";
    log_info "Allowing common server ports (HTTPS 443, Grafana 3000, Loki 3100) from ${ALLOWED_CLIENT_SUBNET}...";
    ufw allow from "${ALLOWED_CLIENT_SUBNET}" to any port 443 proto tcp || log_warn "Failed rule: HTTPS.";
    ufw allow from "${ALLOWED_CLIENT_SUBNET}" to any port 3000 proto tcp || log_warn "Failed rule: Grafana.";
    ufw allow from "${ALLOWED_CLIENT_SUBNET}" to any port 3100 proto tcp || log_warn "Failed rule: Loki.";
    # Add other ports specified implicitly by SERVER_PACKAGES if needed via Ansible later
    ufw default deny incoming || log_warn "Failed: deny incoming."; ufw default allow outgoing || log_warn "Failed: allow outgoing.";
    yes | ufw enable || log_warn "Failed ufw enable."; log_info "Firewall configured. Status:"; ufw status verbose;
}

# Prepare Ansible, Clone Repo, Generate Key/Inventory
prepare_ansible() {
    log_info "Preparing Ansible environment..."; local ansible_key_path="/home/${ADMIN_USER}/.ssh/ansible_client_key";
    log_info "Cloning config repo: ${CONFIG_REPO_URL} -> ${CONFIG_REPO_DEST}...";
    mkdir -p "$(dirname "${CONFIG_REPO_DEST}")" || log_error "Failed mkdir parent."; local git_clone_cmd="git clone --branch ${CONFIG_REPO_BRANCH} ${CONFIG_REPO_URL} ${CONFIG_REPO_DEST}";
    if [ -n "${CONFIG_REPO_DEPLOY_KEY_PATH}" ]; then
        log_info "Using deploy key: ${CONFIG_REPO_DEPLOY_KEY_PATH}"; if [ ! -f "${CONFIG_REPO_DEPLOY_KEY_PATH}" ]; then log_error "Deploy key not found."; fi; chmod 600 "${CONFIG_REPO_DEPLOY_KEY_PATH}" || log_warn "chmod key failed.";
        local ssh_cmd="ssh -i ${CONFIG_REPO_DEPLOY_KEY_PATH} -o IdentitiesOnly=yes -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"; # Less secure, good for automation setup
        git_clone_cmd="GIT_SSH_COMMAND=\"${ssh_cmd}\" ${git_clone_cmd}"; log_warn "Using StrictHostKeyChecking=no for clone.";
    fi;
    if [ -d "${CONFIG_REPO_DEST}" ]; then log_info "Removing existing ${CONFIG_REPO_DEST}..."; rm -rf "${CONFIG_REPO_DEST}" || log_error "Failed rm."; fi;
    if ! eval "${git_clone_cmd}"; then log_error "Failed git clone. Check URL, branch, key, network."; fi;
    log_info "Repo cloned."; # Optional: chown -R "${ADMIN_USER}:${ADMIN_USER}" "${CONFIG_REPO_DEST}"

    log_info "Generating Ansible SSH key for client mgmt (${ansible_key_path})...";
    if [ ! -f "${ansible_key_path}" ]; then
        ssh-keygen -t ed25519 -f "${ansible_key_path}" -N "" || log_error "ssh-keygen failed.";
        chown "${ADMIN_USER}:${ADMIN_USER}" "${ansible_key_path}" "${ansible_key_path}.pub"; chmod 600 "${ansible_key_path}"; chmod 644 "${ansible_key_path}.pub";
        log_info "Ansible SSH key generated.";
    else log_info "Ansible SSH key exists."; fi
    log_info "-> Add this PUBLIC key to client(s) ~/.ssh/authorized_keys:"; log_info "-> $(cat "${ansible_key_path}.pub")";

    # Generate Basic Inventory
    log_info "Generating basic Ansible inventory..."; local inventory_dir="${CONFIG_REPO_DEST}/inventory"; local inventory_file="${inventory_dir}/hosts_generated";
    mkdir -p "${inventory_dir}" || log_warn "Failed mkdir inventory dir.";
    echo "[server]" > "${inventory_file}" || log_error "Failed writing inventory."; echo "localhost ansible_connection=local ansible_user=${ADMIN_USER}" >> "${inventory_file}";
    echo "" >> "${inventory_file}"; echo "[clients]" >> "${inventory_file}";
    read -p "Enter IP address(es) of client machine(s) to manage (space-separated): " -a client_ips;
    if [ ${#client_ips[@]} -gt 0 ]; then for ip in "${client_ips[@]}"; do echo "${ip} ansible_user=${ADMIN_USER} ansible_private_key_file=${ansible_key_path}" >> "${inventory_file}"; done; else log_info "No client IPs provided. Inventory file contains server only."; fi;
    log_info "Generated inventory file: ${inventory_file}"; cat "${inventory_file}"; # Show generated inventory
     # Optional: chown -R "${ADMIN_USER}:${ADMIN_USER}" "${inventory_dir}"
}

# Offer Initial Ansible Runs
run_initial_ansible() {
    local inventory_file="${CONFIG_REPO_DEST}/inventory/hosts_generated";
    local playbook_path="${CONFIG_REPO_DEST}/${INITIAL_PLAYBOOK}";
    log_info "Switching to user '${ADMIN_USER}' for Ansible commands...";

    read -p "Run 'ansible all -m ping' using generated inventory (${inventory_file}) now? (Requires client key setup if clients added) (y/N): " run_ping
    if [[ "$run_ping" =~ ^[Yy]$ ]]; then
        log_info "Running ping test as user ${ADMIN_USER}... You might be asked for the sudo password."
        # Run as the admin user to ensure permissions/keys are correct
        sudo -u "${ADMIN_USER}" ansible all -i "${inventory_file}" -m ping --become --ask-become-pass || log_warn "Ansible ping failed. Check key setup on clients, inventory, and network."
    fi

    if [ -f "${playbook_path}" ]; then
        read -p "Run initial playbook '${INITIAL_PLAYBOOK}' using generated inventory now? (Requires client key setup if clients added) (y/N): " run_playbook
        if [[ "$run_playbook" =~ ^[Yy]$ ]]; then
            log_info "Running playbook '${playbook_path}' as user ${ADMIN_USER}... You might be asked for the sudo password."
            sudo -u "${ADMIN_USER}" ansible-playbook -i "${inventory_file}" "${playbook_path}" --become --ask-become-pass || log_warn "Ansible playbook run failed. Check playbook syntax, key setup on clients, inventory, and network."
        fi
    else
        log_info "Initial playbook '${INITIAL_PLAYBOOK}' not found at '${playbook_path}'. Skipping offer to run."
    fi
}


# --- Main Execution ---
check_root
load_config
detect_pkg_manager

log_info "--- Starting Chimera Elite Linux SERVER Bootstrap v1.2 ---"
configure_timezone
setup_admin_user
harden_ssh
install_packages
configure_firewall
prepare_ansible # Clones repo, generates key, generates basic inventory

# Offer initial Ansible runs (Ping, Playbook)
run_initial_ansible

log_info "--- Bootstrap v1.2 Complete! ---"
log_info "Server hardened, tools installed, Ansible ready, config repo: ${CONFIG_REPO_DEST}."
log_info "Generated Ansible inventory: ${CONFIG_REPO_DEST}/inventory/hosts_generated."
log_info "**ACTION REQUIRED:** Ensure the Ansible public key below is added to ~/.ssh/authorized_keys on all client machine(s) listed in the inventory:"
log_info "$(cat /home/${ADMIN_USER}/.ssh/ansible_client_key.pub)"
log_info "**NEXT STEPS:**"
log_info "1. Log in as '${ADMIN_USER}'."
log_info "2. Navigate to '${CONFIG_REPO_DEST}'."
log_info "3. Review/customize the generated inventory: inventory/hosts_generated (or your main inventory)."
log_info "4. Run your main Ansible playbook (e.g., \`ansible-playbook -i inventory/hosts_generated ${INITIAL_PLAYBOOK} --ask-become-pass\`) if you didn't run it automatically."
log_info "5. Use \`goss\` tests and \`just\` commands defined in your repo."

# --- Proactive Evolution Vector ---
echo ""; log_info "[Proactive Evolution Vector]"
log_info "* **Inventory Management:** Transition from static generated inventory to dynamic inventory sources (e.g., cloud provider APIs, CMDB) or a version-controlled static inventory managed fully within Git."
log_info "* **Ansible Vault:** Encrypt sensitive data within your Ansible repository using Ansible Vault instead of relying solely on SSH keys or external secret managers initially."
log_info "* **Refine Initial Playbook:** Ensure the '${INITIAL_PLAYBOOK}' (or equivalent) performs comprehensive initial setup, including deploying Goss tests, Justfile, and base configurations derived from roles."
log_info "* **Client Bootstrap:** Develop a minimal bootstrap script or Ansible playbook specifically for *new clients* that adds the server's Ansible public key and configures basic SSH access for management."
# --- End Proactive Evolution Vector ---

exit 0
