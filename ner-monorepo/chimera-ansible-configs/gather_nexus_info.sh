
#!/bin/bash

# Script to gather comprehensive Ansible project and environment info for Chimera Prime
# Run from within the Ansible project directory with the virtualenv activated.

echo "### Nexus Reality Scan Initializing ###"
echo "Timestamp: $(date)"
echo "========================================="
echo

# --- Basic System Info ---
echo "### System Information ###"
echo "User: $(whoami)"
echo "Hostname: $(hostname)"
echo "Current Directory: $(pwd)"
echo "----- OS Info -----"
lsb_release -a 2>/dev/null || cat /etc/*release 2>/dev/null || echo "OS info not available"
echo "----- Kernel Info -----"
uname -a
echo "========================================="
echo

# --- Ansible Environment ---
echo "### Ansible Environment ###"
echo "----- Ansible Version -----"
ansible --version
echo "----- Installed Collections -----"
ansible-galaxy collection list
echo "----- Python Packages (pip list) -----"
pip list
echo "========================================="
echo

# --- Git Repository Status ---
echo "### Git Repository Status ###"
if [ -d ".git" ]; then
  echo "----- Git Status -----"
  git status
  echo "----- Git Remotes -----"
  git remote -v
  echo "----- Git Branches -----"
  git branch -vv
  echo "----- Git Log (Last 5) -----"
  git log -n 5 --oneline --graph --decorate
else
  echo "Not a Git repository or .git directory not found."
fi
echo "========================================="
echo

# --- Project Structure ---
echo "### Project Directory Structure ###"
if command -v tree &> /dev/null; then
  tree -L 3 . # Show 3 levels deep
else
  echo "'tree' command not found. Using 'find':"
  find . -print | sed -e 's;[^/]*/;|____;g;s;____|; |;g'
fi
echo "========================================="
echo

# --- Key Configuration Files ---
echo "### Key Configuration File Contents ###"

# Function to safely cat file or report missing
cat_or_missing() {
  local filepath="$1"
  local filename=$(basename "$filepath")
  echo "----- Content of: $filename -----"
  if [ -f "$filepath" ]; then
    cat "$filepath"
  elif [ -d "$filepath" ]; then
    echo "# ERROR: Path exists but is a directory: $filepath"
  else
    echo "# File not found: $filepath"
  fi
  echo "--- End of: $filename ---"
  echo
}

cat_or_missing "ansible.cfg"
cat_or_missing "inventory/hosts_generated" # Specific inventory file
cat_or_missing "site.yml"
cat_or_missing "vars/common_packages.yml"
cat_or_missing "inventory/group_vars/all.yml"
cat_or_missing "inventory/group_vars/server.yml"
cat_or_missing "inventory/group_vars/clients.yml"

echo "----- List Vault Files -----"
find . -name 'vault.yml' -print 2>/dev/null || echo "# No files named 'vault.yml' found."
echo "--- End Vault List ---"
echo

cat_or_missing "roles/common/tasks/main.yml"
cat_or_missing "roles/security/tasks/main.yml"
cat_or_missing "roles/docker/tasks/main.yml"
cat_or_missing "roles/prometheus/tasks/main.yml"
cat_or_missing "roles/prometheus/templates/prometheus.yml.j2"
cat_or_missing "roles/prometheus/templates/docker-compose.yml.j2"

echo "========================================="
echo

# --- Network Info ---
echo "### Network Information (Control Node) ###"
echo "----- IP Addresses -----"
ip a || echo "# 'ip a' command failed."
echo "----- Listening Ports (TCP/UDP) -----"
ss -tulnp 2>/dev/null || netstat -tulnp 2>/dev/null || echo "# 'ss' or 'netstat' command failed or not found."
echo "========================================="
echo

# --- Ansible Lint ---
echo "### Ansible Lint Check (Optional) ###"
if command -v ansible-lint &> /dev/null; then
  ansible-lint site.yml --nocolor # Run lint on main playbook
else
  echo "# 'ansible-lint' command not found. Skipping lint check."
fi
echo "========================================="
echo


echo "### Nexus Reality Scan Complete ###"
echo "Provide the *entire* output above when requested."
