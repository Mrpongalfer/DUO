#!/bin/bash

# Script to restore key Ansible project files to their last known good state.
# Run this script from within the ~/Projects/chimera-ansible-configs directory.

PROJECT_ROOT="." # Assumes running from the project root

echo "--- Restoring Ansible Configuration State ---"

# --- File: ansible.cfg ---
echo "Restoring: ansible.cfg"
cat <<'EOF' >"${PROJECT_ROOT}/ansible.cfg"
# Ansible Configuration File - Managed by Chimera Setup

[defaults]
inventory = ./inventory/hosts_generated
host_key_checking = False
# vault_password_file = /home/aiseed/.ansible_vault_pass # COMMENTED OUT to avoid issues with ansible-lint/vault edit
# Note: Vault password file path set above

# Add other sections like [privilege_escalation] or [ssh_connection] if needed
# [privilege_escalation]
# become=True
# become_method=sudo
# become_user=root
# become_ask_pass=False
EOF

# --- File: .ansible-lint ---
echo "Restoring: .ansible-lint"
cat <<'EOF' >"${PROJECT_ROOT}/.ansible-lint"
# File: .ansible-lint
# Configuration for ansible-lint, used by pre-commit

skip_list:
  - syntax-check[unknown-module] # Broadly skip module resolution errors during linting
  # Example of other potential skips if needed later:
  # - command-instead-of-module
  # - package-latest
EOF

# --- File: .pre-commit-config.yaml ---
echo "Restoring: .pre-commit-config.yaml"
cat <<'EOF' >"${PROJECT_ROOT}/.pre-commit-config.yaml"
# File: .pre-commit-config.yaml
# For mixed Python App + Ansible Infra repository

repos:
# Python Formatting & Linting (Targeted at QO code - relative path from this file)
-   repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4 # Use a recent stable version
    hooks:
    -   id: ruff
        args: [--fix, --exit-non-zero-on-fix]
        files: ^(quantum_orchestrator/|main\.py|run_api\.py|setup\.py) # Regex to target QO python files
    -   id: ruff-format
        files: ^(quantum_orchestrator/|main\.py|run_api\.py|setup\.py) # Regex to target QO python files

# YAML Linting (For Ansible files, etc.)
-   repo: https://github.com/adrienverge/yamllint.git
    rev: v1.35.1 # Use a recent stable version
    hooks:
    -   id: yamllint
        args: [--strict] # Use strict mode for better checking
        # args: [--config-file, .yamllint.yaml] # Optional: Use if creating a custom yamllint config
        files: \.(yaml|yml)$ # Target all YAML files

# Ansible Linting
-   repo: https://github.com/ansible/ansible-lint.git
    rev: v6.22.2 # Use a specific stable tag (or latest)
    hooks:
    -   id: ansible-lint
        files: \.(yaml|yml)$
        args: ["-c", ".ansible-lint"] # Use the config file to apply skips

# Standard file checks
-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0 # Use a recent stable tag
    hooks:
    -   id: trailing-whitespace
    -   id: end-of-file-fixer
    -   id: check-yaml # Basic YAML syntax check
    -   id: check-json # Check config.json, etc.
    -   id: check-added-large-files
EOF

# --- File: site.yml ---
echo "Restoring: site.yml"
cat <<'EOF' >"${PROJECT_ROOT}/site.yml"
# File: /home/pong/Projects/chimera-ansible-configs/site.yml
# Version: 2.0 FINAL - Deploys Monitoring Stack & Quantum Orchestrator

---
- name: Pre-flight APT Cleanup and Validation on Server(s)
  hosts: server
  become: yes
  gather_facts: no
  tags: [always] # Ensure pre-flight runs even when tagging plays
  tasks:
    # --- LazyGit PPA Cleanup ---
    - name: Attempt removal of problematic lazygit PPA via module
      ansible.builtin.apt_repository:
        repo: "ppa:lazygit-team/release"
        state: absent
      ignore_errors: true

    - name: Force removal of lazygit PPA sources list file (.list format)
      ansible.builtin.file:
        path: "/etc/apt/sources.list.d/lazygit-team-ubuntu-release-{{ ansible_distribution_release | default('noble') }}.list"
        state: absent
      ignore_errors: true

    - name: Force removal of lazygit PPA sources file (.sources format)
      ansible.builtin.file:
        path: "/etc/apt/sources.list.d/lazygit-team-ubuntu-release-{{ ansible_distribution_release | default('noble') }}.sources"
        state: absent
      ignore_errors: true

    # --- Docker APT Config Cleanup ---
    - name: Remove potential conflicting Docker sources file (.list)
      ansible.builtin.file:
        path: "/etc/apt/sources.list.d/docker.list"
        state: absent
      ignore_errors: true

    - name: Remove potential conflicting Docker sources file (.sources)
      ansible.builtin.file:
        path: "/etc/apt/sources.list.d/docker.sources"
        state: absent
      ignore_errors: true

    - name: Remove potential conflicting Docker keyring file (.gpg)
      ansible.builtin.file:
        path: "/etc/apt/keyrings/docker.gpg"
        state: absent
      ignore_errors: true

    - name: Remove potential conflicting Docker keyring file (.asc)
      ansible.builtin.file:
        path: "/etc/apt/keyrings/docker.asc"
        state: absent
      ignore_errors: true
    # --- End Docker Cleanup ---

    - name: Clean APT package cache thoroughly
      ansible.builtin.command: apt-get clean -y
      changed_when: false

    - name: Update APT cache explicitly AFTER cleanup to validate
      ansible.builtin.apt:
        update_cache: yes
      register: preflight_apt_update_result
      retries: 1
      delay: 3
      until: preflight_apt_update_result is succeeded

# --- Main Configuration Play ---
- name: Apply common configuration to all hosts
  hosts: all
  become: yes
  gather_facts: yes
  vars:
    # --- Common Variables ---
    system_timezone: "America/Denver"
    admin_users:
      - { username: aiseed, shell: /bin/bash }
      - { username: pong, shell: /bin/bash }
    common_pkgs:
      - build-essential
      - python3-dev
      - curl
      - wget
      - git
      - vim
      - tmux
      - htop
      - net-tools
      - dnsutils
      - unzip
      - ca-certificates
      - gnupg
      - python3-pip
      - python3-venv
      - chrony
      - rsync # Required for synchronize (though replaced with copy)
      - libpq-dev # Added for psycopg2 system dependency

    # --- Security Variables ---
    security_ssh_port: 22
    security_fail2ban_enabled: false
    fail2ban_ignoreip: "127.0.0.1/8 ::1 192.168.0.0/24"
    monitoring_allowed_sources: "192.168.0.0/24"

    # --- Port Definitions ---
    prometheus_port: 9091
    loki_port: 3100
    grafana_port: 3000
    node_exporter_port: 9100
    qo_app_port: 8000 # Quantum Orchestrator API Port

    # --- UFW Rules ---
    # Rules applied by 'security' role based on group membership
    server_ufw_allow_rules:
      - { comment: "Allow SSH from Client", port: "{{ security_ssh_port }}", proto: tcp, rule: allow, src: "192.168.0.96" }
      - { comment: "Allow SSH from Localhost", port: "{{ security_ssh_port }}", proto: tcp, rule: allow, src: "127.0.0.1" }
      - { comment: "Allow Prometheus from Monitoring Subnet", port: "{{ prometheus_port }}", proto: tcp, rule: allow, src: "{{ monitoring_allowed_sources }}" }
      - { comment: "Allow Loki from Monitoring Subnet", port: "{{ loki_port }}", proto: tcp, rule: allow, src: "{{ monitoring_allowed_sources }}" }
      - { comment: "Allow Grafana from Monitoring Subnet", port: "{{ grafana_port }}", proto: tcp, rule: allow, src: "{{ monitoring_allowed_sources }}" }
      - { comment: "Allow Node Exporter from Monitoring Subnet", port: "{{ node_exporter_port }}", proto: tcp, rule: allow, src: "{{ monitoring_allowed_sources }}" }
      - { comment: "Allow Quantum Orchestrator API", port: "{{ qo_app_port }}", proto: tcp, rule: allow, src: "{{ monitoring_allowed_sources }}" }
    client_ufw_allow_rules:
      - { comment: "Allow SSH from Server", port: "{{ security_ssh_port }}", proto: tcp, rule: allow, src: "192.168.0.95" }
      - { comment: "Allow SSH from Localhost", port: "{{ security_ssh_port }}", proto: tcp, rule: allow, src: "127.0.0.1" }
      - { comment: "Allow Node Exporter from Monitoring Subnet", port: "{{ node_exporter_port }}", proto: tcp, rule: allow, src: "{{ monitoring_allowed_sources }}" }

    # --- Docker Variables ---
    docker_users_to_group:
      - aiseed
      - pong

    # --- Promtail Variables ---
    loki_server_url: "http://192.168.0.95:{{ loki_port }}/loki/api/v1/push"

  roles:
    - role: common
      tags: [common]
    - role: security
      tags: [security]
    - role: docker
      tags: [docker]
    - role: node_exporter
      tags: [monitoring, node_exporter]
    - role: promtail
      tags: [monitoring, promtail]

# --- Server-Specific Configuration ---
- name: Configure server-specific services (Monitoring Stack & Quantum Orchestrator)
  hosts: server
  become: yes
  gather_facts: no
  vars:
    # Explicitly define ports needed by roles in this play
    prometheus_port: 9091
    loki_port: 3100
    grafana_port: 3000
    node_exporter_port: 9100
    qo_app_port: 8000

    # User/Group for container files/processes on server
    docker_run_user: "aiseed"
    docker_run_group: "aiseed"

    # Prometheus Paths & Config
    prometheus_base_dir: "/opt/docker/prometheus"
    prometheus_config_dir: "{{ prometheus_base_dir }}/config"
    prometheus_data_dir: "{{ prometheus_base_dir }}/data"
    prometheus_compose_dir: "{{ prometheus_base_dir }}"
    prometheus_template_name: "docker-compose.yml.j2"
    prometheus_compose_file_path: "{{ prometheus_compose_dir }}/docker-compose.yml"
    prometheus_config_template: "prometheus.yml.j2"
    prometheus_config_file_path: "{{ prometheus_config_dir }}/prometheus.yml"

    # Loki Paths & Config
    loki_base_dir: "/opt/docker/loki"
    loki_config_dir: "{{ loki_base_dir }}/config"
    loki_data_dir: "{{ loki_base_dir }}/data"
    loki_compose_dir: "{{ loki_base_dir }}"
    loki_compose_file_path: "{{ loki_compose_dir }}/docker-compose.yml"
    loki_config_template: "loki-config.yml.j2"
    loki_config_file_path: "{{ loki_config_dir }}/loki-config.yml"

    # Grafana Paths & Config
    grafana_base_dir: "/opt/docker/grafana"
    grafana_config_dir: "{{ grafana_base_dir }}/config"
    grafana_data_dir: "{{ grafana_base_dir }}/data"
    grafana_compose_dir: "{{ grafana_base_dir }}"
    grafana_compose_file_path: "{{ grafana_compose_dir }}/docker-compose.yml"
    grafana_admin_password: "{{ vault_grafana_admin_password | default('ChangeMePlease!') }}"

    # Quantum Orchestrator Vars
    qo_local_code_path: "/home/pong/Projects/quantum_orchestrator_app" # CORRECTED PATH
    qo_base_dir: "/opt/docker/quantum_orchestrator"
    qo_deploy_dir: "{{ qo_base_dir }}"
    qo_container_port: 8000 # Internal port defined in Dockerfile/App
    qo_llm_model: "mistral-nemo:12b-instruct-2407-q4_k_m" # User preferred model

  roles:
    - role: prometheus
      tags: [monitoring, prometheus]
    - role: loki
      tags: [monitoring, loki]
    - role: grafana
      tags: [monitoring, grafana]
    - role: quantum_orchestrator
      tags: [app, quantum_orchestrator]

# --- Client-Specific Configuration ---
- name: Configure client-specific settings
  hosts: clients
  become: yes
  gather_facts: no
  vars:
    placeholder_client_var: true
  roles:
    - role: prompt_debug # Keeping placeholder for now
      tags: [debug]
EOF

# --- File: roles/common/tasks/main.yml ---
echo "Restoring: roles/common/tasks/main.yml"
cat <<'EOF' >"${PROJECT_ROOT}/roles/common/tasks/main.yml"
---
# File: roles/common/tasks/main.yml
# Version: Added Grafana repo cleanup to run on ALL hosts first

# --- BEGIN Grafana APT Config Cleanup (Moved Here) ---
- name: Remove potentially conflicting old Grafana GPG key location
  ansible.builtin.file:
    path: /usr/share/keyrings/grafana.gpg
    state: absent
  become: true
  ignore_errors: true # Ignore if file doesn't exist
  tags: [common, packages, apt, cleanup]

- name: Remove potentially conflicting old Grafana sources list file
  ansible.builtin.file:
    path: /etc/apt/sources.list.d/grafana.list
    state: absent
  become: true
  ignore_errors: true # Ignore if file doesn't exist
  tags: [common, packages, apt, cleanup]
# --- END Grafana Cleanup ---

# Existing common tasks follow:
- name: Update apt cache if older than 1 hour
  ansible.builtin.apt:
    update_cache: yes
    cache_valid_time: 3600 # Only update if cache is > 1 hour old
  changed_when: false # Prevent this task alone from reporting 'changed' status
  become: true # Added become: yes, apt update needs it
  tags: [common, packages, apt]


- name: Install common packages defined in vars
  ansible.builtin.apt:
    name: "{{ common_pkgs }}" # Uses the variable list
    state: present
  become: true # Ensure become is used for package installation
  tags: [common, packages, apt]

- name: Set system timezone
  community.general.timezone:
    name: "{{ system_timezone }}" # Uses the variable
  become: true # timezone module often needs root
  tags: [common, system, timezone]

# --- NTP Configuration (using Chrony) ---
- name: Ensure chrony NTP client is installed
  ansible.builtin.apt:
    name: chrony
    state: present
  become: true
  tags: [common, system, ntp]

- name: Ensure chrony service is enabled and running
  ansible.builtin.service:
    name: chrony # Service name might be chronyd on some systems
    state: started
    enabled: true
  become: true
  tags: [common, system, ntp]

# Basic user check - ensures specified users exist with correct shell
- name: Ensure admin users exist
  ansible.builtin.user:
    name: "{{ item.username }}"
    shell: "{{ item.shell }}"
    state: present
  loop: "{{ admin_users }}"
  become: true
  tags: [common, users]

# Add other common tasks below as needed:

EOF

# --- File: roles/docker/tasks/main.yml ---
echo "Restoring: roles/docker/tasks/main.yml"
cat <<'EOF' >"${PROJECT_ROOT}/roles/docker/tasks/main.yml"
---
# Tasks for installing and configuring Docker CE (with GPG Key Workaround)

- name: Ensure prerequisites for Docker repo are installed
  ansible.builtin.apt:
    name:
      - ca-certificates
      - curl
      - gnupg # Ensure gnupg is installed for the gpg command later if needed
    state: present
    update_cache: yes
  become: true
  tags: [docker, packages]

# Remove conflicting docker.io package if present (best effort)
- name: Ensure conflicting docker.io package is removed
  ansible.builtin.apt:
    name:
      - docker.io
      - docker-doc
      - docker-compose
      - podman-docker
      - containerd
      - runc
    state: absent
  ignore_errors: true
  become: true
  tags: [docker, packages]

- name: Ensure Docker apt key directory exists
  ansible.builtin.file:
    path: /etc/apt/keyrings
    state: directory
    mode: '0755'
  become: true
  tags: [docker, repo]

# --- Start: Replaced GPG Key Download Task ---
- name: Add Docker's official GPG key (using curl command)
  ansible.builtin.command:
    # Use curl on the target: fail silently on error (-f), show no progress (-s), follow redirects (-L), output to file (-o)
    cmd: curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    creates: /etc/apt/keyrings/docker.asc # Makes task idempotent - only run if file doesn't exist
  become: true
  changed_when: false # Idempotency handled by 'creates'
  tags: [docker, repo]

- name: Ensure Docker GPG key has correct permissions
  ansible.builtin.file:
    path: /etc/apt/keyrings/docker.asc # Path where key was saved
    mode: '0644'
    owner: root
    group: root
  become: true
  tags: [docker, repo]
# --- End: Replaced GPG Key Download Task ---

- name: Add Docker's official APT repository
  ansible.builtin.apt_repository:
    repo: "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu {{ ansible_distribution_release }} stable" # Ensure signed-by matches .asc path
    state: present
    filename: docker # Creates /etc/apt/sources.list.d/docker.list
    update_cache: yes
  become: true
  tags: [docker, repo]

- name: Install Docker CE packages
  ansible.builtin.apt:
    name:
      - docker-ce
      - docker-ce-cli
      - containerd.io # Required by docker-ce
      - docker-buildx-plugin
      - docker-compose-plugin # Installs 'docker compose' command
    state: present
  become: true
  tags: [docker, packages]
  # notify: Restart docker # Optional handler if needed

- name: Ensure docker group exists
  ansible.builtin.group:
    name: docker
    state: present
  become: true
  tags: [docker, users]

- name: Add specified users to the docker group
  ansible.builtin.user:
    name: "{{ item }}"
    groups: docker
    append: true # Add to existing groups
  loop: "{{ docker_users_to_group | default([]) }}"
  become: true
  tags: [docker, users]

- name: Ensure Docker service is enabled and running
  ansible.builtin.service:
    name: docker
    state: started
    enabled: true
  become: true
  tags: [docker, service]

EOF

# --- File: roles/promtail/tasks/main.yml ---
echo "Restoring: roles/promtail/tasks/main.yml"
cat <<'EOF' >"${PROJECT_ROOT}/roles/promtail/tasks/main.yml"
---
# File: roles/promtail/tasks/main.yml
# Version: Final - Uses curl workaround for GPG key

- name: Ensure prerequisites for Grafana APT repo are installed
  ansible.builtin.apt:
    name:
      - apt-transport-https # Often needed, though may be default now
      - software-properties-common
      - wget
      - gnupg # Needed for gpg dearmor
    state: present
    update_cache: yes
  become: true
  tags: [promtail, packages]

# Grafana repo cleanup tasks are now in 'common' role

# --- Start: Replaced Grafana GPG Key Task ---
- name: Add Grafana GPG key (using shell with curl and gpg)
  ansible.builtin.shell: # Use shell module for pipeline
    cmd: curl -fsSL https://apt.grafana.com/gpg.key | gpg --dearmor -o /etc/apt/keyrings/grafana.gpg
    creates: /etc/apt/keyrings/grafana.gpg # Makes task idempotent
  become: yes
  changed_when: false # Idempotency handled by 'creates'
  tags: [promtail, repo]

- name: Ensure Grafana GPG key has correct permissions
  ansible.builtin.file:
    path: /etc/apt/keyrings/grafana.gpg # Path where key was saved
    mode: '0644'
    owner: root
    group: root
  become: yes
  tags: [promtail, repo]
# --- End: Replaced Grafana GPG Key Task ---

- name: Add Grafana APT repository (for Promtail)
  ansible.builtin.apt_repository:
    repo: "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main" # Ensure signed-by matches key path
    state: present
    filename: grafana # Explicitly manages /etc/apt/sources.list.d/grafana.list
    update_cache: yes # Update cache after adding repo
  become: yes
  tags: [promtail, repo]

- name: Ensure promtail package is installed
  ansible.builtin.apt:
    name: promtail
    state: present
  become: true
  tags: [promtail, packages]
  notify: Restart promtail # Handler needed

# Explicitly manage user/group if needed (often created by package)
# The scan showed these tasks previously, retaining them if needed
- name: Stop promtail service before managing user/group (if running)
  ansible.builtin.service:
    name: promtail
    state: stopped
  become: true
  ignore_errors: true # Continue if service doesn't exist or isn't running
  changed_when: false
  tags: [promtail, config]

- name: Ensure promtail group exists
  ansible.builtin.group:
    name: promtail
    state: present
    system: true
  become: true
  tags: [promtail, config]

- name: Ensure promtail user exists
  ansible.builtin.user:
    name: promtail
    group: promtail
    system: true
    shell: /usr/sbin/nologin
    home: /var/lib/promtail # Common home/data dir
  become: true
  tags: [promtail, config]

- name: Ensure Promtail config directory exists (/etc/promtail)
  ansible.builtin.file:
    path: /etc/promtail
    state: directory
    owner: root
    group: promtail # Allow promtail group to read
    mode: '0775' # Or 0750 for more restrictive
  become: true
  tags: [promtail, config]

- name: Ensure Promtail lib directory exists for positions file (/var/lib/promtail)
  ansible.builtin.file:
    path: /var/lib/promtail
    state: directory
    owner: promtail
    group: promtail
    mode: '0750' # Needs to be writable by promtail user
  become: true
  tags: [promtail, config]

- name: Deploy Promtail configuration from template
  ansible.builtin.template:
    src: promtail-config.yml.j2
    dest: /etc/promtail/config.yml # Default path often expected by service
    owner: root
    group: promtail
    mode: '0640' # Readable by root and promtail group only
    validate: promtail -config.file=%s -print-config-stderr # Validate config
  become: true
  tags: [promtail, config]
  notify: Restart promtail

- name: Ensure promtail service is enabled and running
  ansible.builtin.service:
    name: promtail
    state: started
    enabled: true
  become: true
  tags: [promtail, service]

EOF

# --- File: roles/prometheus/tasks/main.yml ---
echo "Restoring: roles/prometheus/tasks/main.yml"
cat <<'EOF' >"${PROJECT_ROOT}/roles/prometheus/tasks/main.yml"
---
# File: roles/prometheus/tasks/main.yml
# Version: FINAL - Merged Local Fixes + Remote Volume Permission Fix + Hardcoded Src

- name: Ensure Prometheus directories exist
  ansible.builtin.file:
    path: "{{ item }}"
    state: directory
    owner: root # Let root create dirs initially
    group: root
    mode: '0755'
  loop:
    - "{{ prometheus_compose_dir }}"
    - "{{ prometheus_config_dir }}"
    - "{{ prometheus_data_dir }}"
  become: true
  tags: [prometheus, config]

- name: Deploy Prometheus configuration file (prometheus.yml)
  ansible.builtin.template:
    src: prometheus.yml.j2 # HARDCODED src path
    dest: "{{ prometheus_config_file_path }}"
    owner: root # Config needs to be readable by container user
    group: root # Group read often sufficient
    mode: '0644'
  become: true
  notify: Restart Prometheus container # Notify handler on config change
  tags: [prometheus, config]

- name: Ensure Docker Compose V2 is available
  ansible.builtin.command: docker compose version
  register: compose_version_check
  changed_when: false
  failed_when: compose_version_check.rc != 0
  become: true
  tags: [prometheus, docker, config]

- name: Deploy Prometheus docker-compose.yml file from template
  ansible.builtin.template:
    src: "{{ prometheus_template_name }}" # Var OK here
    dest: "{{ prometheus_compose_file_path }}"
    owner: root
    group: root
    mode: '0644'
  become: true
  notify: Restart Prometheus container # Notify handler on compose file change
  tags: [prometheus, config]

# --- BEGIN VOLUME PERMISSION FIX (from Remote) ---
- name: Ensure Prometheus data directory has correct permissions for container user
  ansible.builtin.file:
    path: "{{ prometheus_data_dir }}"
    state: directory
    owner: "65534" # UID for nobody (Prometheus container user)
    group: "65534" # GID for nogroup
    mode: '0775' # Writable by owner/group
  become: true
  tags: [prometheus, config, permissions]
# --- END VOLUME PERMISSION FIX ---

- name: Ensure potentially conflicting container is absent (Local Fix Re-applied)
  community.docker.docker_container:
    name: prometheus
    state: absent
    force_kill: yes
  become: yes
  ignore_errors: true
  tags: [prometheus, docker, run]

- name: Ensure Prometheus container is running via Docker Compose (Local Fix Re-applied)
  community.docker.docker_compose_v2:
    project_name: prometheus_stack
    definition: "{{ lookup('template', 'docker-compose.yml.j2') | from_yaml }}"
    state: present
    pull: missing
  become: yes
  register: compose_result
  # No notify needed here usually, config reload handled separately or via definition change
  tags: [prometheus, docker, run]

EOF

# --- File: roles/prometheus/templates/docker-compose.yml.j2 ---
echo "Restoring: roles/prometheus/templates/docker-compose.yml.j2"
cat <<'EOF' >"${PROJECT_ROOT}/roles/prometheus/templates/docker-compose.yml.j2"
# File: roles/prometheus/templates/docker-compose.yml.j2
# Version: FINAL - Merged Remote Changes + Correct Local Network Config

# Define network locally scoped to this project (prometheus_stack)
# Loki/Grafana will reference this as prometheus_stack_monitoring_net externally.
networks:
  monitoring_net: # This name gets prefixed by project_name ('prometheus_stack')
    driver: bridge

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus # Explicit name
    user: "65534:65534" # Run as nobody:nogroup
    volumes:
      # Mount config file rendered by Ansible (read-only)
      - "{{ prometheus_config_file_path }}:/etc/prometheus/prometheus.yml:ro"
      # Mount data volume from HOST - permissions handled by task in main.yml
      - "{{ prometheus_data_dir }}:/prometheus"
    ports:
      # Use variable from play vars (site.yml) for host port
      - "{{ prometheus_port }}:9090" # Uses 'prometheus_port' consistent with site.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
      - '--web.enable-lifecycle'
    restart: unless-stopped
    networks: # Connect service to the network defined above
      - monitoring_net
    labels:
      org.label-schema.group: "monitoring"
      managed-by: "ansible-chimera-prime"

EOF

# --- File: roles/prometheus/templates/prometheus.yml.j2 ---
echo "Restoring: roles/prometheus/templates/prometheus.yml.j2"
cat <<'EOF' >"${PROJECT_ROOT}/roles/prometheus/templates/prometheus.yml.j2"
# File: roles/prometheus/templates/prometheus.yml.j2
# Version: FINAL - Merged Remote Changes + Correct Self-Scrape Port + Refined Jinja

global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "prometheus"
    # Scrape Prometheus itself (inside Docker, uses internal port 9090)
    static_configs:
      - targets: ["localhost:9090"] # CORRECTED PORT to internal 9090

  - job_name: "node_exporter"
    # Scrape node_exporter based on inventory groups
    static_configs:
      - targets:
{%- set ne_targets = [] %} {# Initialize list #}
{%- set ne_port = node_exporter_port | default(9100) %} {# Get default port from vars #}
{%- for host in (groups['server'] | default([])) + (groups['clients'] | default([])) %} {# Combine server & client groups safely #}
{%-   set host_ip = hostvars[host]['ansible_host'] | default(host) %} {# Use connection IP or inventory name #}
{%-   set _ = ne_targets.append(host_ip ~ ':' ~ ne_port) %} {# Append 'host:port' #}
{%- endfor %}
{{ ne_targets | to_yaml | indent(8) }} {# Output list as YAML #}

# Add alerting rules configuration if needed
# rule_files:
#   - "/etc/prometheus/rules/*.rules.yml"

EOF

# --- File: roles/prometheus/handlers/main.yml ---
echo "Restoring: roles/prometheus/handlers/main.yml"
cat <<'EOF' >"${PROJECT_ROOT}/roles/prometheus/handlers/main.yml"
---
# File: roles/prometheus/handlers/main.yml
- name: Restart Prometheus container
  # Ensures the Prometheus stack defined by the template is running/restarted.
  # Use command module for explicit reload/restart if needed, or rely on compose state.
  community.docker.docker_compose_v2:
    project_name: prometheus_stack # Match project name from task
    definition: "{{ lookup('template', '../templates/docker-compose.yml.j2') | from_yaml }}" # Re-read definition
    state: present     # Ensure services are running per the definition
    # recreate: always # Use if 'state: present' isn't forceful enough
  become: yes
EOF

# --- File: roles/loki/handlers/main.yml ---
echo "Restoring: roles/loki/handlers/main.yml"
cat <<'EOF' >"${PROJECT_ROOT}/roles/loki/handlers/main.yml"
---
# File: roles/loki/handlers/main.yml
# Version: FINAL v2 - Using project_src only

- name: Restart Loki container
  # Ensures the QO stack defined by the compose file on disk is running/restarted.
  community.docker.docker_compose_v2:
    project_name: loki_stack # Use project name consistent with task
    project_src: "{{ loki_compose_dir }}" # Use project_src consistent with task
    state: present     # Ensure services are running per the file on disk
    # recreate: always # Consider if more forceful restart needed
  become: yes
EOF

# --- File: roles/loki/templates/loki-config.yml.j2 ---
echo "Restoring: roles/loki/templates/loki-config.yml.j2"
cat <<'EOF' >"${PROJECT_ROOT}/roles/loki/templates/loki-config.yml.j2"
# File: roles/loki/templates/loki-config.yml.j2
# Version: FINAL - Disabled structured metadata

auth_enabled: false

server:
  http_listen_port: {{ loki_port | default(3100) }}
  grpc_listen_port: 9096

common:
  instance_addr: 127.0.0.1
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

query_range:
  results_cache:
    cache:
      embedded_cache:
        enabled: true
        max_size_mb: 100

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper # Using older shipper store
      object_store: filesystem
      schema: v11 # Using older schema version
      index:
        prefix: index_
        period: 24h

ruler:
  alertmanager_url: http://localhost:9093 # Placeholder

# Added limits_config back JUST to disable structured metadata
limits_config:
  allow_structured_metadata: false
EOF

# --- File: roles/quantum_orchestrator/tasks/main.yml ---
echo "Restoring: roles/quantum_orchestrator/tasks/main.yml"
cat <<'EOF' >"${PROJECT_ROOT}/roles/quantum_orchestrator/tasks/main.yml"
---
# File: roles/quantum_orchestrator/tasks/main.yml
# Version: FINAL v2.3 - DEFINITIVELY Corrected Copy Src Path

- name: Ensure required Vault variables are defined (placeholders)
  ansible.builtin.assert:
    that:
      - vault_qo_db_user is defined
      - vault_qo_db_password is defined
      - vault_qo_db_name is defined
      - vault_qo_flask_secret_key is defined
    fail_msg: "Required Vault variables (vault_qo_db_*) are not defined. Please define them in inventory/group_vars/all/vault.yml"
    quiet: true
  tags: [quantum_orchestrator, config, prerequisites]

- name: Define deployment base directory variable
  ansible.builtin.set_fact:
    qo_deploy_dir: "{{ qo_base_dir | default('/opt/docker/quantum_orchestrator') }}"
  tags: [quantum_orchestrator, config]

- name: Ensure Quantum Orchestrator deployment directories exist
  ansible.builtin.file:
    path: "{{ item }}"
    state: directory
    owner: "{{ docker_run_user | default('root') }}"
    group: "{{ docker_run_group | default('root') }}"
    mode: '0755'
  loop:
    - "{{ qo_deploy_dir }}"
    - "{{ qo_deploy_dir }}/app_code"
    - "{{ qo_deploy_dir }}/ollama_data"
  become: true
  tags: [quantum_orchestrator, config]

- name: Ensure app_code directory is initially absent (forces clean copy)
  ansible.builtin.file:
    path: "{{ qo_deploy_dir }}/app_code"
    state: absent
  become: true
  tags: [quantum_orchestrator, config, code_sync]

- name: Recreate app_code directory for source code
  ansible.builtin.file:
    path: "{{ qo_deploy_dir }}/app_code"
    state: directory
    owner: "{{ docker_run_user | default('root') }}"
    group: "{{ docker_run_group | default('root') }}"
    mode: '0755'
  become: true
  tags: [quantum_orchestrator, config, code_sync]

# --- Start: Corrected Copy Tasks ---
- name: Copy essential application files to server build context
  ansible.builtin.copy:
    src: "{{ qo_local_code_path }}/{{ item }}" # CORRECTED: Use variable path pointing to ~/Projects/quantum_orchestrator_app
    dest: "{{ qo_deploy_dir }}/app_code/"
    owner: "{{ docker_run_user | default('root') }}"
    group: "{{ docker_run_group | default('root') }}"
    mode: '0644'
  become: true
  loop:
    - main.py
    - run_api.py
    - setup.py
    - pyproject.toml
    - uv.lock
    - config.json
    - instruction_schema.json
  ignore_errors: true # Still ignore errors for optional files like uv.lock
  tags: [quantum_orchestrator, config, code_sync]

- name: Copy application package directory to server build context
  ansible.builtin.copy:
    src: "{{ qo_local_code_path }}/quantum_orchestrator/" # CORRECTED: Use variable path pointing to ~/Projects/quantum_orchestrator_app
    dest: "{{ qo_deploy_dir }}/app_code/quantum_orchestrator/"
    owner: "{{ docker_run_user | default('root') }}"
    group: "{{ docker_run_group | default('root') }}"
    mode: '0755' # Dirs/executables might need execute
  become: true
  tags: [quantum_orchestrator, config, code_sync]
# --- End: Corrected Copy Tasks ---

- name: Ensure Ollama data directory permissions
  ansible.builtin.file:
    path: "{{ qo_deploy_dir }}/ollama_data"
    state: directory
    owner: "101" # Common default Ollama UID - REVIEW and adjust if needed
    group: "102" # Common default Ollama GID - REVIEW and adjust if needed
    mode: '0755'
  become: yes
  tags: [quantum_orchestrator, config, permissions]

- name: Template Docker Compose file for Quantum Orchestrator Stack
  ansible.builtin.template:
    src: docker-compose.yml.j2
    dest: "{{ qo_deploy_dir }}/docker-compose.yml" # Render to final location
    owner: "{{ docker_run_user | default('root') }}"
    group: "{{ docker_run_group | default('root') }}"
    mode: '0644'
  become: true
  notify: Restart Quantum Orchestrator stack
  tags: [quantum_orchestrator, config]

# Use project_src now that compose file is templated correctly
- name: Ensure Quantum Orchestrator stack is running via Docker Compose (uses volume mount)
  community.docker.docker_compose_v2:
    project_name: qo_stack
    project_src: "{{ qo_deploy_dir }}" # Point to dir containing docker-compose.yml and app_code
    # build: ... REMOVED ...
    state: present
    pull: always # Pull base images like python, postgres, ollama
  become: yes
  notify: Restart Quantum Orchestrator stack
  tags: [quantum_orchestrator, docker, run]

EOF

# --- File: roles/quantum_orchestrator/handlers/main.yml ---
echo "Restoring: roles/quantum_orchestrator/handlers/main.yml"
cat <<'EOF' >"${PROJECT_ROOT}/roles/quantum_orchestrator/handlers/main.yml"
---
# File: roles/quantum_orchestrator/handlers/main.yml
# Version: FINAL - Using project_src only

- name: Restart Quantum Orchestrator stack
  # Ensures the QO stack defined by the compose file on disk is running/restarted.
  community.docker.docker_compose_v2:
    project_name: qo_stack
    project_src: "{{ qo_deploy_dir }}" # Use project_src consistent with task
    state: present     # Ensure services are running per the file on disk
    # recreate: always # Consider if more forceful restart needed
  become: yes
EOF

# --- File: roles/quantum_orchestrator/templates/docker-compose.yml.j2 ---
echo "Restoring: roles/quantum_orchestrator/templates/docker-compose.yml.j2"
cat <<'EOF' >"${PROJECT_ROOT}/roles/quantum_orchestrator/templates/docker-compose.yml.j2"
# File: roles/quantum_orchestrator/templates/docker-compose.yml.j2
# Version: FINAL - Using Volume Mount for App Code

networks:
  # References the network created by the Prometheus stack
  monitoring_net:
    name: prometheus_stack_monitoring_net
    external: true
  # Internal network for this stack's services
  qo_backend_net:
    driver: bridge

volumes:
  # Define persistent volumes used by services
  qo_postgres_data: {}
  qo_ollama_data: {}

services:
  # --- Quantum Orchestrator Application ---
  app:
    container_name: quantum_orchestrator_app
    image: python:3.11-slim # USE BASE IMAGE - code comes from volume mount
    # build: ... REMOVED build section ...
    working_dir: /app # Set working directory inside container
    volumes:
      # Mount the copied code directory from host directly into container
      # HOST_PATH (relative to compose file): CONTAINER_PATH
      - ./app_code:/app
    restart: unless-stopped
    ports:
      # Map host port to container port
      - "{{ qo_app_port | default(8000) }}:{{ qo_container_port | default(8000) }}"
    environment:
      # Inject secrets and config via environment variables
      DATABASE_URL: "postgresql://{{ vault_qo_db_user }}:{{ vault_qo_db_password }}@postgres:5432/{{ vault_qo_db_name }}"
      FLASK_SECRET_KEY: "{{ vault_qo_flask_secret_key }}"
      LLM_API_BASE: "http://ollama:11434" # Internal Docker network hostname
      LLM_MODEL_NAME: "{{ qo_llm_model | default('mistral-nemo:12b-instruct-2407-q4_k_m') }}" # Use specific model
      PYTHONUNBUFFERED: "1" # Ensure logs appear immediately
      # Add other necessary environment variables here
    depends_on:
      - postgres
      - ollama
    networks:
      - qo_backend_net
      - monitoring_net
    labels:
      org.label-schema.group: "application"
      managed-by: "ansible-chimera-prime"
    # Command to run the application (installs deps first)
    command: >
      sh -c "pip install --upgrade pip && \
             pip install --no-cache-dir . && \
             python main.py"

  # --- PostgreSQL Database ---
  postgres:
    container_name: quantum_orchestrator_db
    image: postgres:latest
    restart: unless-stopped
    volumes:
      - qo_postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: "{{ vault_qo_db_user }}"
      POSTGRES_PASSWORD: "{{ vault_qo_db_password }}"
      POSTGRES_DB: "{{ vault_qo_db_name }}"
    networks:
      - qo_backend_net
    expose:
      - "5432"
    labels:
      org.label-schema.group: "database"
      managed-by: "ansible-chimera-prime"

  # --- Ollama LLM Service ---
  ollama:
    container_name: quantum_orchestrator_ollama
    image: ollama/ollama:latest
    restart: unless-stopped
    volumes:
      - qo_ollama_data:/root/.ollama
    networks:
      - qo_backend_net
      - monitoring_net
    expose:
      - "11434"
    # ports: # Uncomment if direct host access needed
    #  - "11434:11434"
    # deploy: # Uncomment and adjust if GPU needed/available
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]
    labels:
      org.label-schema.group: "ai_service"
      managed-by: "ansible-chimera-prime"
EOF

# --- File: roles/grafana/tasks/main.yml ---
echo "Restoring: roles/grafana/tasks/main.yml"
cat <<'EOF' >"${PROJECT_ROOT}/roles/grafana/tasks/main.yml"
# File: roles/grafana/tasks/main.yml
# Version: FINAL - Uses definition + project_name

- name: Ensure Grafana directories exist
  ansible.builtin.file:
    path: "{{ item }}"
    state: directory
    owner: "{{ docker_run_user | default('root') }}" # Note: Grafana container runs as UID/GID 472. Adjust if mounting host data dir.
    group: "{{ docker_run_group | default('root') }}"# Note: Grafana container runs as UID/GID 472. Adjust if mounting host data dir.
    mode: '0755'
  loop:
    - "{{ grafana_compose_dir }}" # Needed for project context if compose file uses relative paths
    - "{{ grafana_config_dir }}" # Needed if mounting grafana.ini or provisioning files later
    - "{{ grafana_data_dir }}"   # Needed only if mounting host data dir directly (Docker volume is preferred)
  become: true
  tags: [grafana, config]

- name: Ensure Grafana Docker Compose project is running
  community.docker.docker_compose_v2:
    project_name: grafana_stack # ADDED project_name
    definition: "{{ lookup('template', 'docker-compose.yml.j2') | from_yaml }}" # Embed template definition directly
    state: present
    pull: missing
  become: true
  tags: [grafana, docker, run]
EOF

# --- File: roles/grafana/templates/docker-compose.yml.j2 ---
echo "Restoring: roles/grafana/templates/docker-compose.yml.j2"
cat <<'EOF' >"${PROJECT_ROOT}/roles/grafana/templates/docker-compose.yml.j2"
# File: roles/grafana/templates/docker-compose.yml.j2
# Version: FINAL - Correct external network syntax

volumes:
  grafana_data: {}

networks:
  # Define the existing external network created by Prometheus
  monitoring_net: # Alias used by services below
    name: prometheus_stack_monitoring_net # Actual Docker network name
    external: true

services:
  grafana:
    image: grafana/grafana-oss:latest
    container_name: grafana
    restart: unless-stopped
    volumes:
      - grafana_data:/var/lib/grafana
      # Optional: Mount custom configs if needed later
      # - "{{ grafana_config_dir }}/grafana.ini:/etc/grafana/grafana.ini"
    ports:
      - "{{ grafana_port | default(3000) }}:3000"
    environment:
      # Use vault variable, provide clear default if unset
      - GF_SECURITY_ADMIN_PASSWORD={{ vault_grafana_admin_password | default('ChangeMePlease!') }}
    networks:
      # Connect service to the network defined above
      - monitoring_net # Use the alias defined under top-level 'networks:'
    labels:
      org.label-schema.group: "monitoring"
      managed-by: "ansible-chimera-prime"
EOF

# --- File: roles/loki/templates/docker-compose.yml.j2 ---
echo "Restoring: roles/loki/templates/docker-compose.yml.j2"
cat <<'EOF' >"${PROJECT_ROOT}/roles/loki/templates/docker-compose.yml.j2"
# File: roles/loki/templates/docker-compose.yml.j2
# Version: FINAL - Correct external network syntax

volumes:
  loki_data: {}

networks:
  # Define the existing external network created by Prometheus
  monitoring_net: # Alias used by services below
    name: prometheus_stack_monitoring_net # Actual Docker network name
    external: true

services:
  loki:
    image: grafana/loki:latest
    container_name: loki
    restart: unless-stopped
    volumes:
      - "{{ loki_config_file_path }}:/etc/loki/local-config.yaml:ro" # Use correct host path var
      - loki_data:/loki
    ports:
      - "{{ loki_port | default(3100) }}:{{ loki_port | default(3100) }}"
    command: -config.file=/etc/loki/local-config.yaml
    networks:
      # Connect service to the network defined above
      - monitoring_net # Use the alias defined under top-level 'networks:'
    labels:
      org.label-schema.group: "monitoring"
      managed-by: "ansible-chimera-prime"
EOF

# --- File: roles/loki/tasks/main.yml ---
echo "Restoring: roles/loki/tasks/main.yml"
cat <<'EOF' >"${PROJECT_ROOT}/roles/loki/tasks/main.yml"
---
# File: roles/loki/tasks/main.yml
# Version: FINAL - Uses definition + project_name

- name: Ensure Loki directories exist
  ansible.builtin.file:
    path: "{{ item }}"
    state: directory
    owner: "{{ docker_run_user | default('root') }}"
    group: "{{ docker_run_group | default('root') }}"
    mode: '0755'
  loop:
    - "{{ loki_compose_dir }}"
    - "{{ loki_config_dir }}"
    - "{{ loki_data_dir }}" # Used by Loki config internally for filesystem storage
  become: true
  tags: [loki, config]

- name: Deploy Loki configuration file (loki-config.yml)
  ansible.builtin.template:
    src: loki-config.yml.j2
    dest: "{{ loki_config_file_path }}" # Use precise var from site.yml
    owner: "{{ docker_run_user | default('root') }}"
    group: "{{ docker_run_group | default('root') }}"
    mode: '0644'
  become: true
  notify: Restart Loki container # Assumes handler 'Restart Loki container' exists
  tags: [loki, config]

- name: Ensure Loki Docker Compose project is running
  community.docker.docker_compose_v2:
    project_name: loki_stack # ADDED project_name
    definition: "{{ lookup('template', 'docker-compose.yml.j2') | from_yaml }}" # Embed template definition
    state: present
    pull: missing
  become: true
  notify: Restart Loki container # Assumes handler exists
  tags: [loki, docker, run]
EOF

echo "--- Restoration Script Complete ---"
echo "Run 'git status' to see changes."
echo "Then run 'git add .' and 'git commit -m \"chore: Restore known good state post-rollback\"'."
echo "Finally, run 'git push origin main --force-with-lease' to update GitHub."
echo "After committing and pushing, run the playbook."

exit 0
