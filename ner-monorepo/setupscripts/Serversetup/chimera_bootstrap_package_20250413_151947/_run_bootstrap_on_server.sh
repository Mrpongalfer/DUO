#!/bin/bash
#
# Helper script to transfer bootstrap files to the server and execute.
# Run this script from the directory containing bootstrap.conf and chimera_server_bootstrap.sh
#

set -e

BOOTSTRAP_SCRIPT="chimera_server_bootstrap.sh"
CONFIG_FILE="bootstrap.conf"
REMOTE_USER="" # User with SSH access and sudo rights on the server (e.g., root or initial user)
REMOTE_HOST="" # IP address or hostname of the Ubuntu server
REMOTE_TMP_DIR="/tmp/chimera_bootstrap_pkg"

# --- Configuration ---
read -p "Enter username for SSH connection to the server (must have sudo): " REMOTE_USER
while [ -z "${REMOTE_USER}" ]; do read -p "Username cannot be empty: " REMOTE_USER; done

read -p "Enter IP address or hostname of the server: " REMOTE_HOST
while [ -z "${REMOTE_HOST}" ]; do read -p "Server IP/hostname cannot be empty: " REMOTE_HOST; done
# --- End Configuration ---

echo "[INFO] Checking local files..."
if [ ! -f "${BOOTSTRAP_SCRIPT}" ] || [ ! -f "${CONFIG_FILE}" ]; then
    echo "[ERROR] Cannot find required files: ${BOOTSTRAP_SCRIPT} and ${CONFIG_FILE} in current directory."
    exit 1
fi

echo "[INFO] Transferring files to ${REMOTE_HOST}...${REMOTE_TMP_DIR}..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" "mkdir -p ${REMOTE_TMP_DIR}" || { echo "[ERROR] Failed to create remote directory via SSH."; exit 1; }
scp "${BOOTSTRAP_SCRIPT}" "${CONFIG_FILE}" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_TMP_DIR}/" || { echo "[ERROR] Failed to copy files via SCP."; exit 1; }

echo "[INFO] Running bootstrap script on ${REMOTE_HOST} via SSH..."
echo "[INFO] You will likely be prompted for ${REMOTE_USER}'s password for sudo."

# Execute the script remotely using sudo. Pass config file location if needed (though script expects it in same dir)
ssh -t "${REMOTE_USER}@${REMOTE_HOST}" "cd ${REMOTE_TMP_DIR} && sudo bash ./${BOOTSTRAP_SCRIPT}"

if [ $? -eq 0 ]; then
    echo "[INFO] Bootstrap script executed successfully (check output above)."
    echo "[INFO] Cleaning up remote temporary directory..."
    ssh "${REMOTE_USER}@${REMOTE_HOST}" "rm -rf ${REMOTE_TMP_DIR}" || echo "[WARN] Failed to remove remote temporary directory."
else
    echo "[ERROR] Bootstrap script execution failed on server. Check SSH output."
    echo "[WARN] Remote directory ${REMOTE_TMP_DIR} was not cleaned up for inspection."
    exit 1
fi

echo "[INFO] Process complete. Follow the 'NEXT STEPS' instructions from the bootstrap script output."
exit 0

