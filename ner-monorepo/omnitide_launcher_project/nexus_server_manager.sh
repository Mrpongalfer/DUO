#!/bin/bash
# Nexus Server Manager Ultimate v2.2 (Enhanced Fan Control by Drake)
# All-in-one interactive management for home servers

# --- Configuration ---
REMOTE_SERVER_USER_HOST_DEFAULT="aiseed@192.168.0.95"
SSH_CONNECT_TIMEOUT=10
DEFAULT_SSH_OPTS="-o ConnectTimeout=${SSH_CONNECT_TIMEOUT} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
SAFETY_TEMP_THRESHOLD=85

# --- Local Storage for Server-Specific Configs ---
CONFIG_DIR="${HOME}/.nexus_server_manager"
mkdir -p "${CONFIG_DIR}"
# FAN_CONFIG_FILE will be set to "${CONFIG_DIR}/${CURRENT_SERVER_ALIAS}_fan_config.json"

# --- Color Codes ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# --- Global Variables ---
CURRENT_SERVER_USER_HOST=""
CURRENT_SERVER_ALIAS="" # Short name for the server, used for config files
SSH_OPTS=""
declare -A FAN_CONFIG # Associative array for fan control paths

# --- Helper Functions (print_*, prompt_yes_no, run_ssh, run_ssh_heredoc from previous version) ---
print_error() { echo -e "${RED}ERROR: $1${NC}"; }
print_success() { echo -e "${GREEN}SUCCESS: $1${NC}"; }
print_warning() { echo -e "${YELLOW}WARNING: $1${NC}"; }
print_info() { echo -e "${BLUE}INFO: $1${NC}"; }
print_header() { echo -e "\n${CYAN}==== $1 ====${NC}"; }

prompt_yes_no() {
    while true; do
        read -r -p "$1 [Y/n]: " response
        response=${response,,}
        if [[ "$response" =~ ^(yes|y|"")$ ]]; then REPLY="yes"; return 0;
        elif [[ "$response" =~ ^(no|n)$ ]]; then REPLY="no"; return 0;
        else print_error "Invalid input."; fi
    done
}

run_ssh() {
    local cmd_string="$1"
    local suppress_output_flag="$2"
    local output
    local ret_code

    print_info "Executing on ${CURRENT_SERVER_USER_HOST}: ${cmd_string}"
    if [[ "$suppress_output_flag" == "suppress" ]]; then
        # Capture stdout and stderr combined
        output=$(ssh $SSH_OPTS "${CURRENT_SERVER_USER_HOST}" "${cmd_string}" 2>&1)
        ret_code=$?
        # Even if suppressed for general display, print if error
        if [ $ret_code -ne 0 ]; then
            print_error "Remote command failed (Exit Code: $ret_code) on ${CURRENT_SERVER_USER_HOST}"
            echo -e "Command: ${cmd_string}\nOutput:\n$output"
        fi
        # Return captured output for the caller to process if needed
        echo "$output" 
    else
        # Stream output directly
        ssh $SSH_OPTS "${CURRENT_SERVER_USER_HOST}" "${cmd_string}"
        ret_code=$?
        if [ $ret_code -ne 0 ]; then
            print_error "Remote command failed (Exit Code: $ret_code) on ${CURRENT_SERVER_USER_HOST}"
        fi
    fi
    return $ret_code
}

run_ssh_heredoc() {
    local script_content
    script_content=$(cat) 
    print_info "Executing script block on ${CURRENT_SERVER_USER_HOST}..."
    if ssh $SSH_OPTS "${CURRENT_SERVER_USER_HOST}" 'bash -s' <<<"${script_content}"; then
        return 0
    else
        local ret_code=$?
        print_error "Remote script block failed (Exit Code: $ret_code) on ${CURRENT_SERVER_USER_HOST}"
        return $ret_code
    fi
}

# --- Configuration and Connection ---
check_server_connection() {
    print_header "Server Connection Setup"
    local temp_server_user_host
    local temp_server_alias

    read -r -p "Enter server connection string (user@host) [${REMOTE_SERVER_USER_HOST_DEFAULT}]: " temp_server_user_host
    CURRENT_SERVER_USER_HOST=${temp_server_user_host:-$REMOTE_SERVER_USER_HOST_DEFAULT}
    
    # Generate a simple alias from user@host, replacing @ and . with _
    temp_server_alias=$(echo "${CURRENT_SERVER_USER_HOST}" | tr '@.' '_')
    read -r -p "Enter a short alias for this server (for config files) [${temp_server_alias}]: " custom_alias
    CURRENT_SERVER_ALIAS=${custom_alias:-$temp_server_alias}
    FAN_CONFIG_FILE="${CONFIG_DIR}/${CURRENT_SERVER_ALIAS}_fan_config.json"


    local custom_ssh_key_path
    prompt_yes_no "Use a specific SSH private key for this connection?"
    if [[ "$REPLY" == "yes" ]]; then
        read -r -e -p "Enter path to your SSH private key: " custom_ssh_key_path
        if [ -f "$custom_ssh_key_path" ]; then
            SSH_OPTS="${DEFAULT_SSH_OPTS} -i ${custom_ssh_key_path}"
            print_info "Using custom SSH key: $custom_ssh_key_path"
        else
            print_warning "SSH key '$custom_ssh_key_path' not found. Using default SSH agent/keys."
            SSH_OPTS="${DEFAULT_SSH_OPTS}"
        fi
    else
        SSH_OPTS="${DEFAULT_SSH_OPTS}"
    fi

    print_info "Testing connection to ${CURRENT_SERVER_USER_HOST}..."
    # Capture output to prevent it from interfering with prompts
    if ssh $SSH_OPTS "${CURRENT_SERVER_USER_HOST}" "echo 'Connection successful.' > /dev/null"; then
        print_success "Successfully connected to ${CURRENT_SERVER_USER_HOST} (Alias: ${CURRENT_SERVER_ALIAS})."
        load_fan_config # Attempt to load existing fan config for this server
        return 0
    else
        print_error "Failed to connect to ${CURRENT_SERVER_USER_HOST}."
        CURRENT_SERVER_USER_HOST=""
        CURRENT_SERVER_ALIAS=""
        SSH_OPTS=""
        return 1
    fi
}

# --- Bootstrap Function (More Interactive) ---
bootstrap_server() {
    print_header "Server Bootstrap & Initialization"
    print_warning "This will install/update packages on '${CURRENT_SERVER_USER_HOST}'."
    print_warning "It requires sudo privileges on the remote server."
    
    declare -A install_flags
    install_flags["monitoring_core"]="yes" # lm-sensors, ipmitool, pciutils, hdparm, smartmontools
    install_flags["security_base"]="yes"   # fail2ban, ufw/firewalld
    install_flags["network_utils"]="yes"  # net-tools, nload, htop, iotop, iftop
    install_flags["general_utils"]="yes"  # ncdu, tree, curl, wget, tmux, rsync, git
    install_flags["python_env"]="yes"     # python3, python3-pip, python3-venv
    install_flags["nvidia_tools"]="no"    # nvidia-smi, nvidia-settings (if NVIDIA detected)
    install_flags["user_py_tools"]="yes"  # speedtest-cli, glances

    echo "Select package categories to install/check:"
    prompt_yes_no "  Core Hardware Monitoring Tools (lm-sensors, ipmitool, etc.)?"
    install_flags["monitoring_core"]=$REPLY
    prompt_yes_no "  Base Security Tools (Fail2Ban, Firewall package)?"
    install_flags["security_base"]=$REPLY
    prompt_yes_no "  Network Utilities (nload, htop, etc.)?"
    install_flags["network_utils"]=$REPLY
    prompt_yes_no "  General Utilities (ncdu, tree, tmux, git, etc.)?"
    install_flags["general_utils"]=$REPLY
    prompt_yes_no "  Python Environment (python3, pip, venv)?"
    install_flags["python_env"]=$REPLY
    
    # Check for NVIDIA GPU remotely before asking about NVIDIA tools
    print_info "Checking for NVIDIA GPU on remote server..."
    if ssh $SSH_OPTS "${CURRENT_SERVER_USER_HOST}" "lspci -nnk | grep -i nvidia -C2 | grep -i vga" >/dev/null 2>&1; then
        print_info "NVIDIA GPU detected."
        prompt_yes_no "  NVIDIA Tools (nvidia-smi, nvidia-settings for GPU stats/fan control - REQUIRES NVIDIA DRIVERS INSTALLED)?"
        install_flags["nvidia_tools"]=$REPLY
    else
        print_info "No NVIDIA GPU detected by lspci, or command failed. Skipping NVIDIA tools question."
        install_flags["nvidia_tools"]="no"
    fi
    prompt_yes_no "  User Python Tools (speedtest-cli, glances via pip3 install --user)?"
    install_flags["user_py_tools"]=$REPLY

    prompt_yes_no "Proceed with selected installations on '${CURRENT_SERVER_USER_HOST}'?"
    [[ "$REPLY" == "no" ]] && return

    print_info "Starting server bootstrap process with selected components..."
    
    # Build package list based on flags
    package_list_builder_script='
        PKG_LIST=();
        FIREWALL_PKG_NAME=""; # Determined based on OS
        if [[ "${install_flags[monitoring_core]}" == "yes" ]]; then PKG_LIST+=(lm-sensors ipmitool pciutils hdparm smartmontools); fi
        if [[ "${install_flags[security_base]}" == "yes" ]]; then 
            if command -v apt-get &>/dev/null; then FIREWALL_PKG_NAME="ufw"; else FIREWALL_PKG_NAME="firewalld"; fi
            PKG_LIST+=(fail2ban "$FIREWALL_PKG_NAME"); 
        fi
        if [[ "${install_flags[network_utils]}" == "yes" ]]; then PKG_LIST+=(net-tools nload htop iotop iftop); fi
        if [[ "${install_flags[general_utils]}" == "yes" ]]; then PKG_LIST+=(ncdu tree curl wget tmux rsync git); fi
        if [[ "${install_flags[python_env]}" == "yes" ]]; then PKG_LIST+=(python3 python3-pip python3-venv); fi
        if [[ "${install_flags[nvidia_tools]}" == "yes" ]]; then 
             if command -v apt-get &>/dev/null; then PKG_LIST+=(nvidia-smi nvidia-settings); else PKG_LIST+=(nvidia-smi); fi
        fi
        echo "${PKG_LIST[*]}"; # Output space-separated list
    '
    # Evaluate flags locally to pass to the remote script
    eval_flags_locally=$(
        for flag_key in "${!install_flags[@]}"; do
            echo "install_flags[${flag_key}]=\"${install_flags[$flag_key]}\""
        done
    )
    
    # The main heredoc script
    run_ssh_heredoc <<EOF_BOOTSTRAP
#!/bin/bash
echo "--- Remote Bootstrap Started (Interactive Selection Mode) ---"
export DEBIAN_FRONTEND=noninteractive
declare -A install_flags
${eval_flags_locally} # This injects the flag settings from local bash to remote bash

# Determine package manager (copied from previous version, good)
PKG_MANAGER=""
PM_UPDATE_CMD=""
PM_INSTALL_CMD=""
if command -v apt-get &>/dev/null; then
    PKG_MANAGER="apt-get"; PM_UPDATE_CMD="sudo apt-get update -qq"; PM_INSTALL_CMD="sudo apt-get install -y -qq";
elif command -v yum &>/dev/null; then
    PKG_MANAGER="yum"; PM_UPDATE_CMD="sudo yum check-update -q || true"; PM_INSTALL_CMD="sudo yum install -y -q";
elif command -v dnf &>/dev/null; then
    PKG_MANAGER="dnf"; PM_UPDATE_CMD="sudo dnf check-update -q || true"; PM_INSTALL_CMD="sudo dnf install -y -q";
else
    echo "ERROR: No supported package manager (apt-get, yum, dnf) found. Cannot install packages."
    exit 1
fi
echo "INFO: Using package manager: \$PKG_MANAGER"

echo "INFO: Updating package lists (can take a moment)..."
eval \$PM_UPDATE_CMD || echo "WARNING: Package list update command had issues."

# Build package list on remote based on flags
${package_list_builder_script} # This will echo the final list
# Capture the output of the package list builder
FINAL_PACKAGE_LIST=\$(${package_list_builder_script})

if [ -z "\$FINAL_PACKAGE_LIST" ]; then
    echo "INFO: No packages selected for installation."
else
    echo "INFO: Attempting to install selected packages: \$FINAL_PACKAGE_LIST"
    for pkg in \$FINAL_PACKAGE_LIST; do
        echo "  Installing/Checking \$pkg..."
        if eval \$PM_INSTALL_CMD "\$pkg"; then
            echo "    \$pkg processed successfully."
        else
            echo "    WARNING: Failed to install \$pkg or it was already installed/processed with issues. Check manually if needed."
        fi
    done
fi

echo "INFO: Configuring core services based on selections..."
if [[ "\${install_flags[monitoring_core]}" == "yes" ]] && command -v sensors-detect &>/dev/null; then
    echo "  Running sensors-detect (non-interactively)..."
    sudo sensors-detect --auto < /dev/null || echo "  WARNING: sensors-detect had issues."
fi

if [[ "\${install_flags[security_base]}" == "yes" ]] && command -v systemctl &>/dev/null; then
    if command -v fail2ban-server &>/dev/null; then
        echo "  Enabling and starting Fail2Ban..."
        sudo systemctl enable fail2ban >/dev/null 2>&1
        sudo systemctl start fail2ban >/dev/null 2>&1 || echo "  WARNING: Failed to start/enable fail2ban."
    fi
    # Firewall enabling/configuration is better handled interactively in its own menu.
fi

# User Python tools
if [[ "\${install_flags[user_py_tools]}" == "yes" ]]; then
    echo "INFO: Installing user Python tools (speedtest-cli, glances)..."
    # Ensure .local/bin is in PATH for the remote user (copied from previous version)
    PROFILE_FILES=("\$HOME/.bashrc" "\$HOME/.zshrc" "\$HOME/.profile" "\$HOME/.bash_profile")
    LOCAL_BIN_PATH_STR="export PATH=\\\"\\\$HOME/.local/bin:\\\$PATH\\\"" # Escaped for remote eval
    NEEDS_PATH_ADD=true
    for PFILE in "\${PROFILE_FILES[@]}"; do
        if [ -f "\$PFILE" ] && grep -qF -- "\$LOCAL_BIN_PATH_STR" "\$PFILE"; then NEEDS_PATH_ADD=false; break; fi
    done
    if \$NEEDS_PATH_ADD; then
        TARGET_PROFILE_FILE="\$HOME/.bashrc"; if [ ! -f "\$TARGET_PROFILE_FILE" ]; then TARGET_PROFILE_FILE="\$HOME/.profile"; touch "\$TARGET_PROFILE_FILE"; fi
        if ! grep -qF -- "\$LOCAL_BIN_PATH_STR" "\$TARGET_PROFILE_FILE"; then
            echo -e "\\n# Added by Nexus Server Manager for user-installed Python tools\\n\${LOCAL_BIN_PATH_STR}" >> "\$TARGET_PROFILE_FILE"
            echo "    PATH update for \$HOME/.local/bin added to \$TARGET_PROFILE_FILE. Re-login or source it on the server."
        fi
    fi
    python3 -m pip install --user --upgrade pip >/dev/null 2>&1
    if python3 -m pip install --user speedtest-cli glances; then
         echo "    User Python tools (speedtest-cli, glances) installed/upgraded successfully."
    else
         echo "    WARNING: Failed to install some user Python tools. Ensure pip3 works for the remote user."
    fi
fi
echo "--- Remote Bootstrap Finished ---"
EOF_BOOTSTRAP

    if [ $? -eq 0 ]; then
        print_success "Server bootstrap process completed."
    else
        print_error "Server bootstrap process encountered errors. Please review output."
    fi
    read -rp "Press Enter to continue..."
}

# --- Fan Control Configuration & Logic ---
load_fan_config() {
    # FAN_CONFIG_FILE is set in check_server_connection
    if [ -f "${FAN_CONFIG_FILE}" ]; then
        print_info "Loading fan configuration from ${FAN_CONFIG_FILE}..."
        # Read JSON and populate FAN_CONFIG associative array
        # This is tricky in bash. A more robust way would be to use python or jq.
        # Simple parsing for now, assuming specific structure.
        # Example: {"cpu_fan_pwm": "/sys/class/hwmon/hwmon2/pwm1", "cpu_fan_enable": "/sys/class/hwmon/hwmon2/pwm1_enable", ...}
        
        # Clear existing FAN_CONFIG
        FAN_CONFIG=() 
        while IFS="=" read -r key value; do
            # Basic sanitization: remove quotes, commas from simple jq output
            key=$(echo "$key" | tr -d '" ,')
            value=$(echo "$value" | tr -d '" ,')
            if [[ -n "$key" && -n "$value" ]]; then
                 FAN_CONFIG["$key"]="$value"
            fi
        done < <(jq -r 'to_entries|map("\(.key)=\(.value)")|.[]' "${FAN_CONFIG_FILE}" 2>/dev/null)

        if [ ${#FAN_CONFIG[@]} -gt 0 ]; then
            print_success "Fan configuration loaded."
            # Optionally print loaded config for debugging
            # for K in "${!FAN_CONFIG[@]}"; do echo "  ${K} -> ${FAN_CONFIG[$K]}"; done
        else
            print_warning "Could not parse fan config or file is empty: ${FAN_CONFIG_FILE}. Manual discovery might be needed."
        fi
    else
        print_info "No existing fan configuration file found for ${CURRENT_SERVER_ALIAS} at ${FAN_CONFIG_FILE}."
        FAN_CONFIG=() # Ensure it's empty
    fi
}

save_fan_config() {
    if [ -z "$CURRENT_SERVER_ALIAS" ]; then
        print_error "Cannot save fan config, server alias not set."
        return 1
    fi
    
    # Convert bash associative array to JSON
    # This is also tricky. Using a heredoc to build JSON string.
    local json_output="{"
    local first_entry=true
    for key in "${!FAN_CONFIG[@]}"; do
        if ! $first_entry; then
            json_output+=","
        fi
        # Ensure values are properly escaped for JSON if they contain special chars
        # For sysfs paths, this is usually not an issue.
        json_output+="\"${key}\":\"${FAN_CONFIG[$key]}\""
        first_entry=false
    done
    json_output+="}"

    echo "$json_output" > "${FAN_CONFIG_FILE}"
    if [ $? -eq 0 ]; then
        print_success "Fan configuration saved to ${FAN_CONFIG_FILE}."
    else
        print_error "Failed to save fan configuration to ${FAN_CONFIG_FILE}."
    fi
}

discover_and_configure_fans_interactive() {
    print_header "Interactive Fan Control Discovery & Configuration"
    print_warning "This process requires careful observation of your server's fans."
    print_info "We will list potential controls and you will help map them."

    # --- Discover lm-sensors based PWM controls ---
    print_info "Discovering sysfs (lm-sensors) PWM controls..."
    local pwm_controls_raw
    pwm_controls_raw=$(run_ssh '
        find /sys/class/hwmon/hwmon*/ -type f \( -name "pwm*" ! -name "*_enable" ! -name "*_mode" ! -name "*_auto_channels_pwm" ! -name "*_auto_point*_pwm" \) -print 2>/dev/null | sort
    ' "suppress")

    if [ -z "$pwm_controls_raw" ]; then
        print_warning "No sysfs PWM control files found (e.g., /sys/class/hwmon/hwmonX/pwmY)."
    else
        declare -a pwm_options
        while IFS= read -r line; do pwm_options+=("$line"); done <<< "$pwm_controls_raw"
        
        print_info "Found potential PWM control files:"
        for i in "${!pwm_options[@]}"; do
            local pwm_path="${pwm_options[$i]}"
            local hwmon_name_path=$(dirname "$pwm_path")/name
            local hwmon_name=$(run_ssh "cat $hwmon_name_path 2>/dev/null || echo UnknownChip" "suppress")
            echo "  $((i+1))) $pwm_path (Chip: $hwmon_name)"
        done

        prompt_yes_no "Do you want to configure any of these sysfs PWM controls now?"
        if [[ "$REPLY" == "yes" ]]; then
            read -r -p "Enter the number of the PWM file for CPU Fan (or 's' to skip): " choice_cpu
            if [[ "$choice_cpu" =~ ^[0-9]+$ ]] && [ "$choice_cpu" -le "${#pwm_options[@]}" ]; then
                FAN_CONFIG["cpu_fan_pwm"]="${pwm_options[$((choice_cpu-1))]}"
                FAN_CONFIG["cpu_fan_enable"]="${FAN_CONFIG["cpu_fan_pwm"]}_enable" # Common pattern
                FAN_CONFIG["cpu_fan_mode"]="${FAN_CONFIG["cpu_fan_pwm"]}_mode"     # Common pattern
                print_info "CPU Fan PWM mapped to: ${FAN_CONFIG["cpu_fan_pwm"]}"
                print_info "  (Enable path assumed: ${FAN_CONFIG["cpu_fan_enable"]})"
                print_info "  (Mode path assumed: ${FAN_CONFIG["cpu_fan_mode"]})"
            fi
            # Repeat for CHASSIS_FAN_PWM, OTHER_FAN_PWM etc. as needed
            read -r -p "Enter the number of a PWM file for a Chassis Fan (or 's' to skip): " choice_chassis
             if [[ "$choice_chassis" =~ ^[0-9]+$ ]] && [ "$choice_chassis" -le "${#pwm_options[@]}" ]; then
                FAN_CONFIG["chassis_fan_pwm"]="${pwm_options[$((choice_chassis-1))]}"
                FAN_CONFIG["chassis_fan_enable"]="${FAN_CONFIG["chassis_fan_pwm"]}_enable"
                FAN_CONFIG["chassis_fan_mode"]="${FAN_CONFIG["chassis_fan_pwm"]}_mode"
                print_info "Chassis Fan PWM mapped to: ${FAN_CONFIG["chassis_fan_pwm"]}"
            fi
        fi
    fi

    # --- Discover NVIDIA GPU Fan controls ---
    print_info "Checking for NVIDIA GPU fan controls..."
    if run_ssh "command -v nvidia-settings &>/dev/null && nvidia-settings -q fans -t | grep -q '\[fan-0\]'" "suppress"; then
        print_info "NVIDIA GPU with controllable fan detected (via nvidia-settings)."
        prompt_yes_no "Configure NVIDIA GPU fan control (gpu0_fan)?"
        if [[ "$REPLY" == "yes" ]]; then
            FAN_CONFIG["gpu0_fan_type"]="nvidia_settings"
            # No specific path needed, just the type and index (0 for first GPU)
            print_info "NVIDIA GPU fan control (gpu0_fan) enabled for mapping."
        fi
    else
        print_info "nvidia-settings not found or no controllable fans reported by it."
    fi
    
    # --- Placeholder for AMD GPU Fan controls ---
    # TODO: Add discovery for /sys/class/drm/cardX/device/hwmon/hwmonY/pwmZ

    # --- Placeholder for IPMI Fan controls ---
    print_info "Checking for IPMI tool..."
    if run_ssh "command -v ipmitool &>/dev/null" "suppress"; then
        print_info "ipmitool found. You can use IPMI options in the fan control menu if your server supports it."
        FAN_CONFIG["ipmi_available"]="yes"
    fi

    if [ ${#FAN_CONFIG[@]} -gt 0 ]; then
        save_fan_config
    else
        print_warning "No fan controls were mapped during this session."
    fi
    read -rp "Press Enter to continue..."
}

# Generic function to set a sysfs PWM fan
# Args: $1=pwm_path, $2=pwm_value (0-255), $3=enable_path, $4=manual_enable_value (e.g., 1)
set_sysfs_pwm_fan() {
    local pwm_path="$1"
    local pwm_value="$2"
    local enable_path="$3"
    local manual_enable_value="$4" # Often 1 for manual mode

    if [ -z "$pwm_path" ] || [ -z "$enable_path" ]; then
        print_error "PWM path or enable path not configured for this fan."
        return 1
    fi

    print_info "Attempting to set '${enable_path}' to '${manual_enable_value}' (manual mode)..."
    run_ssh "echo ${manual_enable_value} | sudo tee '${enable_path}'" "suppress"
    if [ $? -ne 0 ]; then print_warning "Failed to set enable mode for ${enable_path}. Fan speed change might not take effect."; fi
    
    print_info "Attempting to write '${pwm_value}' to '${pwm_path}'..."
    run_ssh "echo ${pwm_value} | sudo tee '${pwm_path}'" "suppress"
    if [ $? -eq 0 ]; then
        print_success "PWM value ${pwm_value} written to ${pwm_path}."
    else
        print_error "Failed to write PWM value to ${pwm_path}."
        return 1
    fi
    return 0
}

# Generic function to reset a sysfs PWM fan to auto
# Args: $1=enable_path, $2=auto_enable_value (e.g., 2 or system default)
reset_sysfs_pwm_fan_auto() {
    local enable_path="$1"
    local auto_enable_value="$2" # Often 2 for "auto" or BIOS/EC control

    if [ -z "$enable_path" ]; then
        print_error "Enable path not configured for this fan."
        return 1
    fi
    print_info "Attempting to write '${auto_enable_value}' to ${enable_path} for automatic control..."
    run_ssh "echo ${auto_enable_value} | sudo tee '${enable_path}'" "suppress"
    if [ $? -eq 0 ]; then
        print_success "Enable path ${enable_path} set to ${auto_enable_value} for automatic control."
    else
        print_error "Failed to set ${enable_path} to automatic."
        return 1
    fi
    return 0
}


set_fan_speed_interactive() {
    print_header "Set Fan Speed (Interactive)"
    load_fan_config # Ensure latest config is loaded

    if [ ${#FAN_CONFIG[@]} -eq 0 ]; then
        print_warning "No fan controls configured yet. Please run 'Discover/Configure Fan Controls' first."
        prompt_yes_no "Run discovery now?"
        if [[ "$REPLY" == "yes" ]]; then
            discover_and_configure_fans_interactive
            load_fan_config # Reload after discovery
            if [ ${#FAN_CONFIG[@]} -eq 0 ]; then
                 print_error "Still no fan controls configured. Aborting set speed."
                 return 1
            fi
        else
            return 1
        fi
    fi

    echo "Available configured fan controls:"
    local i=1
    declare -A menu_options_map # Maps menu number to fan_key
    if [[ -n "${FAN_CONFIG[cpu_fan_pwm]}" ]]; then echo "  $i) CPU Fan (Sysfs PWM)"; menu_options_map[$i]="cpu_fan"; i=$((i+1)); fi
    if [[ -n "${FAN_CONFIG[chassis_fan_pwm]}" ]]; then echo "  $i) Chassis Fan (Sysfs PWM)"; menu_options_map[$i]="chassis_fan"; i=$((i+1)); fi
    if [[ "${FAN_CONFIG[gpu0_fan_type]}" == "nvidia_settings" ]]; then echo "  $i) NVIDIA GPU0 Fan"; menu_options_map[$i]="gpu0_fan"; i=$((i+1)); fi
    if [[ "${FAN_CONFIG[ipmi_available]}" == "yes" ]]; then echo "  $i) IPMI Fan Control"; menu_options_map[$i]="ipmi_fan"; i=$((i+1)); fi
    
    if [ $i -eq 1 ]; then
        print_error "No recognized fan control types in the current configuration. Please re-run discovery."
        return 1
    fi
    echo "  $i) Back"
    menu_options_map[$i]="back"

    read -r -p "Select fan to control: " fan_choice
    local selected_fan_key=${menu_options_map[$fan_choice]}

    case $selected_fan_key in
        "cpu_fan"|"chassis_fan")
            local pwm_path="${FAN_CONFIG[${selected_fan_key}_pwm]}"
            local enable_path="${FAN_CONFIG[${selected_fan_key}_enable]}"
            # Mode 1 is typically manual for many hwmon drivers with pwmX_enable
            local manual_enable_val=1 
            
            read -r -p "Enter PWM value for ${selected_fan_key} (0-255, e.g., 150 for medium): " pwm_val
            if [[ "$pwm_val" =~ ^[0-9]+$ ]] && [ "$pwm_val" -ge 0 ] && [ "$pwm_val" -le 255 ]; then
                set_sysfs_pwm_fan "$pwm_path" "$pwm_val" "$enable_path" "$manual_enable_val"
            else
                print_error "Invalid PWM value."
            fi
            ;;
        "gpu0_fan")
            read -r -p "Enter NVIDIA GPU0 fan speed percentage (0-100): " gpu_percent
            if [[ "$gpu_percent" =~ ^[0-9]+$ ]] && [ "$gpu_percent" -ge 0 ] && [ "$gpu_percent" -le 100 ]; then
                print_info "Attempting to set NVIDIA GPU0 fan to ${gpu_percent}%..."
                run_ssh "export DISPLAY=:0; sudo nvidia-settings -a \"[gpu:0]/GPUFanControlState=1\" -a \"[fan:0]/GPUTargetFanSpeed=${gpu_percent}\"" "suppress"
                if [ $? -ne 0 ]; then print_error "Failed to set NVIDIA GPU fan. Check X server config for nvidia-settings or ensure drivers/tool are installed."; fi
            else
                print_error "Invalid percentage."
            fi
            ;;
        "ipmi_fan")
            print_info "IPMI Fan Control Options:"
            echo "  1) Set to Full Speed (Caution: Loud!)"
            echo "  2) Set to Optimal/Standard Speed (System Default Auto)"
            echo "  3) Set Manual Duty Cycle Percentage"
            read -r -p "IPMI Fan Choice: " ipmi_choice
            case $ipmi_choice in
                1) run_ssh "sudo ipmitool raw 0x30 0x30 0x01 0x01" "suppress"; print_success "IPMI fan set to full speed command issued.";; # Full speed
                2) run_ssh "sudo ipmitool raw 0x30 0x30 0x01 0x00" "suppress"; print_success "IPMI fan set to optimal/auto command issued.";; # Optimal/Auto
                3) 
                    read -r -p "Enter fan duty cycle percentage (0-100) for IPMI: " ipmi_percent
                    if [[ "$ipmi_percent" =~ ^[0-9]+$ ]] && [ "$ipmi_percent" -ge 0 ] && [ "$ipmi_percent" -le 100 ]; then
                        # Convert percentage to hex 0x00 - 0x64 for standard IPMI range
                        local ipmi_hex_val=$(printf "0x%02x" "$ipmi_percent")
                        run_ssh "sudo ipmitool raw 0x30 0x30 0x02 0xff ${ipmi_hex_val}" "suppress" # Set all fans to %
                        print_success "IPMI fan duty cycle ${ipmi_percent}% (${ipmi_hex_val}) command issued."
                    else
                        print_error "Invalid IPMI percentage."
                    fi
                    ;;
                *) print_error "Invalid IPMI fan option.";;
            esac
            ;;
        "back") return ;;
        *) print_error "Invalid selection for fan control." ;;
    esac
}

reset_fans_interactive() {
    print_header "Reset Fan Control to Automatic (Interactive)"
    load_fan_config

    if [ ${#FAN_CONFIG[@]} -eq 0 ]; then
        print_warning "No fan controls configured. Cannot reset. Run discovery first."
        return 1
    fi
    
    print_info "Select which fan group to reset to automatic control:"
    # Similar menu to set_fan_speed_interactive but for resetting
    echo "Available configured fan controls to reset:"
    local i=1
    declare -A menu_options_map_reset
    if [[ -n "${FAN_CONFIG[cpu_fan_enable]}" ]]; then echo "  $i) CPU Fan (Sysfs PWM)"; menu_options_map_reset[$i]="cpu_fan"; i=$((i+1)); fi
    if [[ -n "${FAN_CONFIG[chassis_fan_enable]}" ]]; then echo "  $i) Chassis Fan (Sysfs PWM)"; menu_options_map_reset[$i]="chassis_fan"; i=$((i+1)); fi
    if [[ "${FAN_CONFIG[gpu0_fan_type]}" == "nvidia_settings" ]]; then echo "  $i) NVIDIA GPU0 Fan"; menu_options_map_reset[$i]="gpu0_fan"; i=$((i+1)); fi
    if [[ "${FAN_CONFIG[ipmi_available]}" == "yes" ]]; then echo "  $i) IPMI Fans (to Optimal/System Auto)"; menu_options_map_reset[$i]="ipmi_fan"; i=$((i+1)); fi
    
    if [ $i -eq 1 ]; then
        print_error "No configured fans to reset."
        return 1
    fi
    echo "  $i) ALL Configured Fans (where applicable)"
    menu_options_map_reset[$i]="all_fans"
    i=$((i+1))
    echo "  $i) Back"
    menu_options_map_reset[$i]="back"

    read -r -p "Select fan group to reset: " reset_choice
    local selected_reset_key=${menu_options_map_reset[$reset_choice]}

    reset_one_fan() {
        local fan_key_prefix=$1
        local fan_type_desc=$2
        print_info "Resetting ${fan_type_desc}..."
        if [[ "$fan_key_prefix" == "cpu_fan" ]] || [[ "$fan_key_prefix" == "chassis_fan" ]]; then
            local enable_p="${FAN_CONFIG[${fan_key_prefix}_enable]}"
            # Common auto values for pwmX_enable: 2 (BIOS/EC control), sometimes 1 (if '0' is off and '1' is variable by system).
            # Ask user for safety or use a common default.
            read -r -p "Enter 'auto' value for ${enable_p} (typically 2 for mobo/BIOS control, or 1 for some auto modes) [2]: " auto_val
            auto_val=${auto_val:-2}
            if [[ "$auto_val" =~ ^[0-9]+$ ]]; then
                 reset_sysfs_pwm_fan_auto "$enable_p" "$auto_val"
            else
                print_error "Invalid auto value for sysfs PWM enable."
            fi
        elif [[ "$fan_key_prefix" == "gpu0_fan" ]]; then
            run_ssh "export DISPLAY=:0; sudo nvidia-settings -a \"[gpu:0]/GPUFanControlState=0\"" "suppress"
            if [ $? -eq 0 ]; then print_success "NVIDIA GPU0 fan control reset to auto."; else print_error "Failed to reset NVIDIA GPU0 fan."; fi
        elif [[ "$fan_key_prefix" == "ipmi_fan" ]]; then
            run_ssh "sudo ipmitool raw 0x30 0x30 0x01 0x00" "suppress" # Standard command for "Optimal" or system auto
            if [ $? -eq 0 ]; then print_success "IPMI fans set to Optimal/System Auto command issued."; else print_error "Failed to set IPMI fans to auto."; fi
        fi
    }

    case $selected_reset_key in
        "cpu_fan") reset_one_fan "cpu_fan" "CPU Fan (Sysfs)";;
        "chassis_fan") reset_one_fan "chassis_fan" "Chassis Fan (Sysfs)";;
        "gpu0_fan") reset_one_fan "gpu0_fan" "NVIDIA GPU0 Fan";;
        "ipmi_fan") reset_one_fan "ipmi_fan" "IPMI Fans";;
        "all_fans")
            print_info "Attempting to reset ALL configured fans to automatic..."
            if [[ -n "${FAN_CONFIG[cpu_fan_enable]}" ]]; then reset_one_fan "cpu_fan" "CPU Fan (Sysfs)"; fi
            if [[ -n "${FAN_CONFIG[chassis_fan_enable]}" ]]; then reset_one_fan "chassis_fan" "Chassis Fan (Sysfs)"; fi
            if [[ "${FAN_CONFIG[gpu0_fan_type]}" == "nvidia_settings" ]]; then reset_one_fan "gpu0_fan" "NVIDIA GPU0 Fan"; fi
            if [[ "${FAN_CONFIG[ipmi_available]}" == "yes" ]]; then reset_one_fan "ipmi_fan" "IPMI Fans"; fi
            print_success "All configured fans reset commands issued."
            ;;
        "back") return ;;
        *) print_error "Invalid selection for fan reset." ;;
    esac
}


# --- Hardware Menu (Now more robust and interactive for fans) ---
show_hardware_menu() {
    while true; do
        print_header "Hardware Control (Server: ${CURRENT_SERVER_ALIAS})"
        echo "1. Check Full System Status"
        echo "2. Discover & Configure Fan Controls (Interactive Setup - Run this first for new servers!)"
        echo "3. Set Fan Speed (Uses configured controls)"
        echo "4. Reset Fans to Automatic (Uses configured controls)"
        echo "5. CPU Governor Settings"
        echo "6. Back to Main Menu"
        echo -n "Choice: "
        read -r h_choice
        case $h_choice in
            1) get_system_status; read -rp "Press Enter to continue..." ;;
            2) discover_and_configure_fans_interactive ;;
            3) set_fan_speed_interactive; read -rp "Press Enter to continue..." ;;
            4) reset_fans_interactive; read -rp "Press Enter to continue..." ;;
            5) show_cpu_governor_menu ;;
            6) return ;;
            *) print_error "Invalid option"; sleep 1 ;;
        esac
    done
}


# --- Main Menu and Execution (Structure from previous, will call updated functions) ---
# (show_security_menu, show_network_menu, etc. would be similarly enhanced)
# ... (Placeholders for other menus from previous version are fine for now) ...
show_diagnostics_menu() { print_header "System Diagnostics"; print_warning "Diagnostics menu not yet implemented."; sleep 2; }
show_user_menu() { print_header "User Management"; print_warning "User menu not yet implemented."; sleep 2; }
show_service_menu() { print_header "Service Manager"; print_warning "Service menu not yet implemented."; sleep 2; }
show_privacy_menu() { print_header "Privacy Tools"; print_warning "Privacy menu not yet implemented."; sleep 2; }

show_main_menu() {
    if [ -z "$CURRENT_SERVER_USER_HOST" ]; then
        if ! check_server_connection; then
            print_error "Cannot proceed without a valid server connection."
            exit 1
        fi
    fi

    while true; do
        clear
        print_header "Nexus Server Manager Ultimate v2.2 (Target: ${CURRENT_SERVER_USER_HOST} as ${CURRENT_SERVER_ALIAS})"
        echo "1. Bootstrap Server (Initial Setup/Update Dependencies)"
        echo "2. Hardware Control (Enhanced Fan Management)"
        echo "3. Security Center"
        echo "4. Network Tools"
        echo "5. System Diagnostics ${YELLOW}(NYI)${NC}"
        echo "6. User Management ${YELLOW}(NYI)${NC}"
        echo "7. Service Manager ${YELLOW}(NYI)${NC}"
        echo "8. Privacy Tools ${YELLOW}(NYI)${NC}"
        echo "9. Change Server / Reconnect / Re-load Fan Config"
        echo "0. Exit"
        echo -n "Enter your choice: "
        
        read -r choice
        case $choice in
            1) bootstrap_server ;;
            2) show_hardware_menu ;;
            3) show_security_menu ;; # Uses functions from previous version
            4) show_network_menu ;;  # Uses functions from previous version
            5) show_diagnostics_menu ;;
            6) show_user_menu ;;
            7) show_service_menu ;;
            8) show_privacy_menu ;;
            9) 
                if ! check_server_connection; then # This will also re-load fan_config
                     print_error "Failed to change server or reconnect."
                     # Decide if to exit or just stay on old server if conn failed
                fi
                ;;
            0) print_info "Exiting Nexus Server Manager."; exit 0 ;;
            *) print_error "Invalid option, please try again."; sleep 1 ;;
        esac
    done
}

# --- Main Execution ---
trap 'echo -e "\n${RED}Exiting by user request (Ctrl+C).${NC}"; exit 130' INT

# Start
if ! check_server_connection; then
    exit 1
fi
show_main_menu
