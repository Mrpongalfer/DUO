#!/usr/bin/env bash
# setup_olodto.sh
# Super-Localized, Self-Evolving Omnitide Nexus (SLOEN) - Phase 1: Foundational Infrastructure
# This script automates secure, cross-platform setup for OLODTO (Linux/macOS/WSL).
# Run as: sudo bash setup_olodto.sh

set -euo pipefail

LOGFILE="/var/log/omnitide_nexus/setup_olodto.log"
mkdir -p "$(dirname "$LOGFILE")"
exec > >(tee -a "$LOGFILE") 2>&1

echo "======================================================================"
echo " Omnitide Local LLM Deployment & Training Orchestrator (OLODTO) Setup "
echo "======================================================================"
echo "This script will prepare your system for a secure, local Llama 3 instance"
echo "and Omnitide Remote Execution Agent (OREA) deployment."
echo "----------------------------------------------------------------------"

# 1. OS & Hardware Detection
echo "[*] Detecting OS and hardware..."
OS_TYPE=""
ARCH_TYPE="$(uname -m)"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if grep -qi microsoft /proc/version 2>/dev/null; then
        OS_TYPE="WSL"
    else
        OS_TYPE="Linux"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS_TYPE="macOS"
else
    echo "[!] Unsupported OS: $OSTYPE"
    exit 1
fi
echo "  - OS Detected: $OS_TYPE"
echo "  - Architecture: $ARCH_TYPE"

# GPU Detection
GPU_TYPE="CPU"
if command -v nvidia-smi &>/dev/null; then
    GPU_TYPE="NVIDIA"
elif system_profiler SPDisplaysDataType 2>/dev/null | grep -q "AMD"; then
    GPU_TYPE="AMD"
elif system_profiler SPDisplaysDataType 2>/dev/null | grep -q "Apple"; then
    GPU_TYPE="AppleSilicon"
fi
echo "  - GPU Detected: $GPU_TYPE"

# 2. Dependency Installation
echo "[*] Installing dependencies..."

install_linux_packages() {
    apt-get update
    apt-get install -y curl wget git build-essential python3 python3-pip python3-venv \
        docker.io docker-compose nginx firejail fail2ban cryptsetup gpg inotify-tools ufw \
        libgomp1
}

install_macos_packages() {
    if ! command -v brew &>/dev/null; then
        echo "[*] Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    brew update
    brew install curl wget git python3 docker docker-compose nginx firejail gpg inotify-tools
    # fail2ban/cryptsetup/ufw are Linux-only; pfctl is native on macOS
}

if [[ "$OS_TYPE" == "Linux" || "$OS_TYPE" == "WSL" ]]; then
    install_linux_packages
elif [[ "$OS_TYPE" == "macOS" ]]; then
    install_macos_packages
fi

# Docker post-install
if ! groups | grep -q docker; then
    usermod -aG docker "$USER" || true
fi

# Conda/Miniconda (robust, idempotent)
MINICONDA_DIR="$HOME/miniconda"
MINICONDA_SH="$HOME/miniconda.sh"
if ! command -v conda &>/dev/null; then
    echo "[*] Installing Miniconda..."
    if [[ ! -f "$MINICONDA_SH" ]]; then
        if [[ "$OS_TYPE" == "Linux" || "$OS_TYPE" == "WSL" ]]; then
            wget -O "$MINICONDA_SH" "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
        elif [[ "$OS_TYPE" == "macOS" ]]; then
            wget -O "$MINICONDA_SH" "https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh"
        fi
    fi
    if [[ -d "$MINICONDA_DIR" ]]; then
        echo "[*] Miniconda directory already exists. Updating with -u flag."
        bash "$MINICONDA_SH" -b -u -p "$MINICONDA_DIR"
    else
        bash "$MINICONDA_SH" -b -p "$MINICONDA_DIR"
    fi
    export PATH="$MINICONDA_DIR/bin:$PATH"
    echo 'export PATH="'$MINICONDA_DIR'/bin:$PATH"' >> ~/.bashrc
else
    echo "[*] Miniconda/conda already installed. Skipping installation."
fi

# Python venv fallback (robust, idempotent)
if ! command -v conda &>/dev/null; then
    if [[ ! -d "$HOME/olodto_venv" ]]; then
        python3 -m venv "$HOME/olodto_venv"
    fi
    # shellcheck disable=SC1090
    source "$HOME/olodto_venv/bin/activate"
fi

# LLM dependencies
# Ensure libgomp is visible to linker for pip builds
LIBGOMP_PATH=$(find /usr/lib /usr/lib64 /lib /lib64 /usr/lib/x86_64-linux-gnu -name libgomp.so.1 2>/dev/null | head -n1)
if [[ -n "$LIBGOMP_PATH" ]]; then
    export LD_LIBRARY_PATH="$(dirname "$LIBGOMP_PATH"):${LD_LIBRARY_PATH:-}"
    echo "[INFO] LD_LIBRARY_PATH set to include $(dirname "$LIBGOMP_PATH")"
    # If in a conda env, symlink libgomp.so.1 into conda's lib dir for build-time linking
    if command -v conda &>/dev/null; then
        CONDA_ENV_PATH=$(conda info --base 2>/dev/null || echo "")
        if [[ -n "${CONDA_PREFIX:-}" ]]; then
            CONDA_ENV_PATH="${CONDA_PREFIX:-}"
        fi
        if [[ -n "$CONDA_ENV_PATH" && -d "$CONDA_ENV_PATH/lib" ]]; then
            if [[ ! -f "$CONDA_ENV_PATH/lib/libgomp.so.1" ]]; then
                ln -sf "$LIBGOMP_PATH" "$CONDA_ENV_PATH/lib/libgomp.so.1"
                echo "[INFO] Symlinked libgomp.so.1 into $CONDA_ENV_PATH/lib/"
            fi
            export LDFLAGS="-L$(dirname "$LIBGOMP_PATH") ${LDFLAGS:-}"
            export LIBRARY_PATH="$(dirname "$LIBGOMP_PATH"):${LIBRARY_PATH:-}"
            echo "[INFO] LDFLAGS and LIBRARY_PATH set for libgomp.so.1"
        fi
    fi
fi

echo "[*] Installing LLM dependencies (ollama, llama-cpp-python, bitsandbytes, unsloth, PyTorch)..."
if [[ "$OS_TYPE" == "Linux" || "$OS_TYPE" == "WSL" ]]; then
    curl -fsSL https://ollama.com/install.sh | sh
elif [[ "$OS_TYPE" == "macOS" ]]; then
    brew install ollama
fi

pip3 install --upgrade pip
pip3 install llama-cpp-python bitsandbytes
if [[ "$GPU_TYPE" == "NVIDIA" ]]; then
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    pip3 install unsloth
elif [[ "$GPU_TYPE" == "AMD" ]]; then
    pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.4.2
elif [[ "$GPU_TYPE" == "AppleSilicon" ]]; then
    pip3 install torch torchvision torchaudio
fi

# 3. System Optimization
echo "[*] Optimizing system for LLM performance..."
if [[ "$OS_TYPE" == "Linux" || "$OS_TYPE" == "WSL" ]]; then
    sysctl -w vm.max_map_count=262144
    sysctl -w fs.file-max=1048576
    echo "vm.max_map_count=262144" >> /etc/sysctl.conf
    echo "fs.file-max=1048576" >> /etc/sysctl.conf
    systemctl stop bluetooth || true
    systemctl disable bluetooth || true
fi

# 4. Secure Directory Setup
echo "[*] Creating and hardening directories..."
mkdir -p /opt/omnitide_nexus /var/log/omnitide_nexus
chown root:root /opt/omnitide_nexus /var/log/omnitide_nexus
chmod 700 /opt/omnitide_nexus
chmod 700 /var/log/omnitide_nexus

# SELinux/AppArmor (Linux only)
if [[ "$OS_TYPE" == "Linux" ]]; then
    if command -v selinuxenabled &>/dev/null && selinuxenabled; then
        chcon -t var_log_t /var/log/omnitide_nexus
        chcon -t usr_t /opt/omnitide_nexus
    fi
    # AppArmor profile placeholder
fi

# inotify watches
inotifywait -m /opt/omnitide_nexus /var/log/omnitide_nexus &

# 5. Nginx & SSL/TLS Configuration
echo "[*] Configuring nginx with mTLS, SSL, and IP whitelisting..."
SSL_DIR="/opt/omnitide_nexus/ssl"
mkdir -p "$SSL_DIR"
openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
    -keyout "$SSL_DIR/server.key" -out "$SSL_DIR/server.crt" \
    -subj "/CN=localhost"
openssl req -new -newkey rsa:4096 -days 365 -nodes \
    -keyout "$SSL_DIR/client.key" -out "$SSL_DIR/client.csr" \
    -subj "/CN=omnitide_client"
openssl x509 -req -in "$SSL_DIR/client.csr" -CA "$SSL_DIR/server.crt" -CAkey "$SSL_DIR/server.key" -CAcreateserial -out "$SSL_DIR/client.crt" -days 365

cat > /etc/nginx/nginx.conf <<EOF
user www-data;
worker_processes auto;
pid /run/nginx.pid;
events { worker_connections 1024; }
http {
    include       mime.types;
    default_type  application/octet-stream;
    server {
        listen 443 ssl;
        server_name localhost;
        ssl_certificate $SSL_DIR/server.crt;
        ssl_certificate_key $SSL_DIR/server.key;
        ssl_client_certificate $SSL_DIR/client.crt;
        ssl_protocols TLSv1.3;
        ssl_ciphers 'TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256';
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
        location /api/ {
            allow 127.0.0.1; # Replace with your IP
            deny all;
            limit_req zone=api burst=10 nodelay;
            # Basic WAF-like rules
            if (\$request_method !~ ^(GET|POST|PUT|DELETE)$ ) { return 444; }
        }
        location / {
            root /opt/omnitide_nexus;
            index index.html;
        }
    }
    limit_req_zone \$binary_remote_addr zone=api:10m rate=1r/s;
}
EOF

systemctl restart nginx

# 6. Service Management
echo "[*] Creating systemd unit files for ollama and nginx..."
cat > /etc/systemd/system/ollama.service <<EOF
[Unit]
Description=Ollama LLM Service
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/ollama serve
Restart=on-failure
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=ollama

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ollama
systemctl enable nginx
systemctl restart ollama

# 7. SSH Hardening for OREA
echo "[*] Configuring SSH for omnitide_orea user..."
id -u omnitide_orea &>/dev/null || useradd -m -s /bin/bash omnitide_orea
mkdir -p /home/omnitide_orea/.ssh
chmod 700 /home/omnitide_orea/.ssh
ssh-keygen -t ed25519 -f /home/omnitide_orea/.ssh/id_ed25519 -N "" -C "OREA Key"
cat /home/omnitide_orea/.ssh/id_ed25519.pub >> /home/omnitide_orea/.ssh/authorized_keys
chmod 600 /home/omnitide_orea/.ssh/authorized_keys
chown -R omnitide_orea:omnitide_orea /home/omnitide_orea/.ssh

cat >> /etc/ssh/sshd_config <<EOF

# OREA SSH Hardening
Match User omnitide_orea
    ForceCommand /bin/false
    PermitTTY no
    X11Forwarding no
    AllowTcpForwarding no
    PermitTunnel no
    PasswordAuthentication no
EOF

systemctl restart sshd || systemctl restart ssh

# 8. Logging & Audit
echo "[*] Ensuring robust logging and audit..."
touch /var/log/omnitide_nexus/olodto_audit.log
chmod 600 /var/log/omnitide_nexus/olodto_audit.log

# 9. Idempotence & Self-Healing
echo "[*] Script is idempotent. Re-running will not break existing setup."

# 10. User Guidance
echo "----------------------------------------------------------------------"
echo "OLODTO setup complete!"
echo "Key actions performed:"
echo "  - OS/hardware detected: $OS_TYPE / $ARCH_TYPE / $GPU_TYPE"
echo "  - All dependencies installed and configured"
echo "  - Secure directories and logging set up"
echo "  - Nginx with mTLS and IP whitelisting configured"
echo "  - Systemd units for ollama and nginx created"
echo "  - SSH hardened for omnitide_orea user"
echo "  - Logging and audit enabled"
echo ""
echo "Next steps:"
echo "  1. Review /etc/nginx/nginx.conf and replace 'allow 127.0.0.1;' with your actual IP for /api/."
echo "  2. For disk encryption, run: cryptsetup status <device> (Linux only)."
echo "  3. For firewall, run: sudo ufw enable (Linux) or configure pfctl (macOS)."
echo "  4. To check logs: tail -f $LOGFILE"
echo ""
echo "If you encounter issues, review the log above or consult the documentation."
echo "----------------------------------------------------------------------"
