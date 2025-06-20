#!/usr/bin/env bash
# omnitide_setup.sh - Unified Installer & Setup Wizard for Omnitide Nexus

set -euo pipefail

LOGFILE="/var/log/omnitide_nexus/omnitide_setup.log"
mkdir -p "$(dirname "$LOGFILE")"
exec > >(tee -a "$LOGFILE") 2>&1

banner() {
  echo "======================================================================"
  echo " Omnitide Nexus Unified Installer & Setup Wizard"
  echo "======================================================================"
}

banner

# 1. Pre-flight Checks
if [[ $EUID -ne 0 ]]; then
  echo "[ERROR] Please run as root (sudo bash omnitide_setup.sh)"
  exit 1
fi

for dep in docker python3 nginx openssl curl git; do
  if ! command -v $dep >/dev/null; then
    echo "[ERROR] $dep is required. Please install $dep."
    exit 1
  fi
done

# 2. System Preparation (merge setup_olodto.sh logic)
echo "[*] Preparing system and installing dependencies..."
if [[ -f ./setup_olodto.sh ]]; then
  bash ./setup_olodto.sh || { echo "[ERROR] setup_olodto.sh failed."; exit 1; }
else
  echo "[WARN] setup_olodto.sh not found. Skipping system prep."
fi

# 3. Detect OCKIFT-P and LCSAF project paths
autodetect_project() {
  local name="$1"
  local result
  result=$(find "$PWD" -maxdepth 2 -type d -name "$name" 2>/dev/null | head -n1)
  if [[ -z "$result" ]]; then
    read -rp "Enter absolute path to $name project: " result
    if [[ ! -d "$result" ]]; then
      echo "[ERROR] Directory $result not found. Exiting."
      exit 1
    fi
  fi
  echo "$result"
}

OCKIFTP_PATH=$(autodetect_project "ockiftp_project")
LCSAF_PATH=$(autodetect_project "lcsaf_project")

# 4. Build & Deploy OCKIFT-P and LCSAF
build_and_run() {
  local path="$1"
  local name="$2"
  local port="$3"
  cd "$path"
  docker build -t "$name" .
  docker rm -f "$name" 2>/dev/null || true
  docker run -d --name "$name" --restart unless-stopped -p "$port:8000" "$name"
}

echo "[*] Building and deploying OCKIFT-P and LCSAF containers..."
build_and_run "$OCKIFTP_PATH" "ockiftp" 8000
build_and_run "$LCSAF_PATH" "lcsaf" 8001

# 5. Nginx & mTLS
SSL_DIR="/opt/omnitide_nexus/ssl"
mkdir -p "$SSL_DIR"
SERVER_KEY="$SSL_DIR/server.key"
SERVER_CRT="$SSL_DIR/server.crt"
CLIENT_KEY="$SSL_DIR/client.key"
CLIENT_CSR="$SSL_DIR/client.csr"
CLIENT_CRT="$SSL_DIR/client.crt"

if [[ ! -f "$SERVER_KEY" || ! -f "$SERVER_CRT" ]]; then
  echo "[*] Generating server certificate..."
  openssl req -x509 -nodes -days 3650 -newkey rsa:4096 -keyout "$SERVER_KEY" -out "$SERVER_CRT" -subj "/CN=localhost"
fi
if [[ ! -f "$CLIENT_KEY" || ! -f "$CLIENT_CRT" ]]; then
  echo "[*] Generating client certificate for mobile app..."
  openssl genrsa -out "$CLIENT_KEY" 4096
  openssl req -new -key "$CLIENT_KEY" -out "$CLIENT_CSR" -subj "/CN=omi_mobile"
  openssl x509 -req -in "$CLIENT_CSR" -CA "$SERVER_CRT" -CAkey "$SERVER_KEY" -CAcreateserial -out "$CLIENT_CRT" -days 3650
fi

# Nginx config with mTLS and reverse proxy
echo "[*] Configuring Nginx with mTLS and reverse proxy..."
NGINX_CONF="/etc/nginx/conf.d/omnitide_nexus.conf"
cat > "$NGINX_CONF" <<EOF
server {
    listen 443 ssl;
    server_name _;
    ssl_certificate     $SERVER_CRT;
    ssl_certificate_key $SERVER_KEY;
    ssl_client_certificate $CLIENT_CRT;
    ssl_verify_client on;
    location /ockiftp/ {
        proxy_pass http://localhost:8000/;
    }
    location /lcsaf/ {
        proxy_pass http://localhost:8001/;
    }
}
EOF
nginx -t && systemctl reload nginx

# 6. SSH Hardening for OREA
if ! id omnitide_orea &>/dev/null; then
  useradd -m -s /bin/bash omnitide_orea
fi
mkdir -p /home/omnitide_orea/.ssh
chmod 700 /home/omnitide_orea/.ssh
if [[ ! -f /home/omnitide_orea/.ssh/id_ed25519 ]]; then
  ssh-keygen -t ed25519 -f /home/omnitide_orea/.ssh/id_ed25519 -N "" -C "OREA Key"
  chown omnitide_orea:omnitide_orea /home/omnitide_orea/.ssh/id_ed25519*
fi

# 7. Mobile App Provisioning (auto)
echo "[*] Auto-provisioning mobile client certificate..."
MOBILE_CERT_EXPORT="/opt/omnitide_nexus/ssl/omi_mobile_bundle.p12"
openssl pkcs12 -export -out "$MOBILE_CERT_EXPORT" -inkey "$CLIENT_KEY" -in "$CLIENT_CRT" -password pass:omipass

# 8. Finalization
banner
echo " Omnitide Nexus setup complete!"
echo " - OCKIFT-P API: https://localhost/ockiftp/"
echo " - LCSAF API:    https://localhost/lcsaf/"
echo " - SSH user:     omnitide_orea"
echo " - Mobile cert:  $MOBILE_CERT_EXPORT (password: omipass)"
echo " - Logs:         $LOGFILE"
echo "======================================================================"
