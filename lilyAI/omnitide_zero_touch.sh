#!/usr/bin/env bash
# omnitide_zero_touch.sh - Zero-Touch Unified Auto-Installer for Omnitide Nexus

set -euo pipefail

LOGFILE="/var/log/omnitide_nexus/omnitide_zero_touch.log"
mkdir -p "$(dirname "$LOGFILE")"
exec > >(tee -a "$LOGFILE") 2>&1

banner() {
  echo "======================================================================"
  echo " Omnitide Nexus Zero-Touch Unified Installer"
  echo "======================================================================"
}

error_exit() {
  echo "[FATAL] $1" | tee -a "$LOGFILE"
  exit 1
}

banner

# 1. Pre-flight Checks
if [[ $EUID -ne 0 ]]; then
  error_exit "Please run as root (sudo bash omnitide_zero_touch.sh)"
fi

for dep in docker python3 nginx openssl curl git; do
  if ! command -v $dep >/dev/null; then
    echo "[ERROR] $dep is required. Installing..." | tee -a "$LOGFILE"
    if command -v apt-get &>/dev/null; then
      apt-get update && apt-get install -y $dep || error_exit "Failed to install $dep via apt-get."
    elif command -v brew &>/dev/null; then
      brew install $dep || error_exit "Failed to install $dep via brew."
    else
      error_exit "Could not auto-install $dep. Please install it manually."
    fi
  fi
done

# 2. Auto-detect project roots (print and prompt if not found)
find_project() {
  local name="$1"
  local type="$2" # file or dir
  local result
  if [[ "$type" == "file" ]]; then
    result=$(find "$PWD" -maxdepth 5 -type f -name "$name" 2>/dev/null | head -n1)
    if [[ -z "$result" ]]; then
      echo "[WARN] Could not auto-detect $name. Please enter the absolute path to the file: " | tee -a "$LOGFILE" >&2
      read -r result
      if [[ ! -f "$result" ]]; then
        error_exit "$name not found at $result."
      fi
    fi
    echo "[INFO] Using $name at $result" | tee -a "$LOGFILE" >&2
    echo "$result"
  else
    result=$(find "$PWD" -maxdepth 5 -type d -name "$name" 2>/dev/null | head -n1)
    if [[ -z "$result" ]]; then
      echo "[WARN] Could not auto-detect $name. Please enter the absolute path to the directory: " | tee -a "$LOGFILE" >&2
      read -r result
      if [[ ! -d "$result" ]]; then
        error_exit "$name not found at $result."
      fi
    fi
    echo "[INFO] Using $name at $result" | tee -a "$LOGFILE" >&2
    echo "$result"
  fi
}

OLODTO_SCRIPT=$(find_project "setup_olodto.sh" "file")
OLODTO_PATH=$(dirname "$OLODTO_SCRIPT")
OCKIFTP_PATH=$(find_project "ockiftp_project" "dir")
LCSAF_PATH=$(find_project "lcsaf_project" "dir")
OMI_PATH=$(find_project "omi_mobile_app" "dir")

# 3. System Preparation (OLODTO)
echo "[*] Running OLODTO system preparation at $OLODTO_PATH..." | tee -a "$LOGFILE"
cd "$OLODTO_PATH"
bash "$OLODTO_SCRIPT" || error_exit "setup_olodto.sh failed."

# 4. Build & Deploy OCKIFT-P and LCSAF
echo "[*] Building and deploying OCKIFT-P and LCSAF containers..." | tee -a "$LOGFILE"
cd "$OCKIFTP_PATH"
echo "[INFO] Building ockiftp Docker image..." | tee -a "$LOGFILE"
docker build -t ockiftp . || error_exit "Failed to build ockiftp Docker image."
docker rm -f ockiftp 2>/dev/null || true
docker run -d --name ockiftp --restart unless-stopped -p 8000:8000 ockiftp || error_exit "Failed to run ockiftp container."

cd "$LCSAF_PATH"
echo "[INFO] Building lcsaf Docker image..." | tee -a "$LOGFILE"
docker build -t lcsaf . || error_exit "Failed to build lcsaf Docker image."
docker rm -f lcsaf 2>/dev/null || true
docker run -d --name lcsaf --restart unless-stopped -p 8001:8000 lcsaf || error_exit "Failed to run lcsaf container."

# 5. Nginx & mTLS
echo "[*] Configuring Nginx with mTLS and reverse proxy..." | tee -a "$LOGFILE"
SSL_DIR="/opt/omnitide_nexus/ssl"
mkdir -p "$SSL_DIR"
SERVER_KEY="$SSL_DIR/server.key"
SERVER_CRT="$SSL_DIR/server.crt"
CLIENT_KEY="$SSL_DIR/client.key"
CLIENT_CSR="$SSL_DIR/client.csr"
CLIENT_CRT="$SSL_DIR/client.crt"

if [[ ! -f "$SERVER_KEY" || ! -f "$SERVER_CRT" ]]; then
  echo "[INFO] Generating server certificate..." | tee -a "$LOGFILE"
  openssl req -x509 -nodes -days 3650 -newkey rsa:4096 -keyout "$SERVER_KEY" -out "$SERVER_CRT" -subj "/CN=localhost" || error_exit "Failed to generate server cert."
fi
if [[ ! -f "$CLIENT_KEY" || ! -f "$CLIENT_CRT" ]]; then
  echo "[INFO] Generating client certificate for mobile app..." | tee -a "$LOGFILE"
  openssl genrsa -out "$CLIENT_KEY" 4096 || error_exit "Failed to generate client key."
  openssl req -new -key "$CLIENT_KEY" -out "$CLIENT_CSR" -subj "/CN=omi_mobile" || error_exit "Failed to generate client CSR."
  openssl x509 -req -in "$CLIENT_CSR" -CA "$SERVER_CRT" -CAkey "$SERVER_KEY" -CAcreateserial -out "$CLIENT_CRT" -days 3650 || error_exit "Failed to sign client cert."
fi

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
nginx -t || error_exit "Nginx config test failed."
systemctl reload nginx || error_exit "Failed to reload nginx."

# 6. SSH Hardening for OREA
if ! id omnitide_orea &>/dev/null; then
  useradd -m -s /bin/bash omnitide_orea || error_exit "Failed to create omnitide_orea user."
fi
mkdir -p /home/omnitide_orea/.ssh
chmod 700 /home/omnitide_orea/.ssh
if [[ ! -f /home/omnitide_orea/.ssh/id_ed25519 ]]; then
  ssh-keygen -t ed25519 -f /home/omnitide_orea/.ssh/id_ed25519 -N "" -C "OREA Key" || error_exit "Failed to generate SSH key for omnitide_orea."
  chown omnitide_orea:omnitide_orea /home/omnitide_orea/.ssh/id_ed25519*
fi

# 7. Mobile App Provisioning (auto)
echo "[*] Auto-provisioning mobile client certificate..." | tee -a "$LOGFILE"
MOBILE_CERT_EXPORT="$SSL_DIR/omi_mobile_bundle.p12"
openssl pkcs12 -export -out "$MOBILE_CERT_EXPORT" -inkey "$CLIENT_KEY" -in "$CLIENT_CRT" -password pass:omipass || error_exit "Failed to export mobile cert."

# 8. OMI Mobile App (optional QR)
echo "[*] Preparing OMI mobile app onboarding..." | tee -a "$LOGFILE"
if command -v qrencode &>/dev/null; then
  qrencode -o "$SSL_DIR/omi_mobile_cert_qr.png" "file://$MOBILE_CERT_EXPORT"
  echo "[+] QR code for mobile cert generated at $SSL_DIR/omi_mobile_cert_qr.png" | tee -a "$LOGFILE"
fi

# 9. Finalization
banner
echo " Omnitide Nexus zero-touch setup complete!" | tee -a "$LOGFILE"
echo " - OCKIFT-P API: https://localhost/ockiftp/" | tee -a "$LOGFILE"
echo " - LCSAF API:    https://localhost/lcsaf/" | tee -a "$LOGFILE"
echo " - SSH user:     omnitide_orea" | tee -a "$LOGFILE"
echo " - Mobile cert:  $MOBILE_CERT_EXPORT (password: omipass)" | tee -a "$LOGFILE"
echo " - Logs:         $LOGFILE" | tee -a "$LOGFILE"
echo "======================================================================" | tee -a "$LOGFILE"
