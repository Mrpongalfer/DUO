#!/bin/bash
set -euo pipefail

# Ensure Python output is unbuffered for real-time logging
export PYTHONUNBUFFERED=1

# Ensure logs directory exists
mkdir -p logs

# === ENVIRONMENT VARIABLES ===
export ARCHITECT_DIGITAL_VAULT="472NzDwER6HMdNQzSBq9YK3fCQQuVvdwH179gWZb6RPAB4B1ZHZ6Cz2FdueDrnGAdFitoxCVqp9Du7hX7YHHntEs8oouJGg"

: <<'ARCHITECT_CRITICAL_WARNING'
**************************************************************************
***  CRITICAL: REPLACE THE ARCHITECT_DIGITAL_VAULT PLACEHOLDER ABOVE   ***
***  WITH YOUR ACTUAL UNTRACEABLE CRYPTOCURRENCY WALLET ADDRESS!       ***
***  THIS IS VITAL FOR RECEIVING FUNDS AND MAINTAINING UNTRACEABILITY. ***
**************************************************************************
ARCHITECT_CRITICAL_WARNING

# Discreet Logging Levels
export CPDDIAP_LOG_LEVEL="WARNING"
export CIAS_LOG_LEVEL="INFO"
export ADRGO_LOG_LEVEL="INFO"
export HRVO_LOG_LEVEL="WARNING"
export OAPDVAS_LOG_LEVEL="INFO"

# MongoDB URI for local testing
export MONGO_URI="mongodb://localhost:27017/oapdvas_db"

# Activate Python virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    export PYTHONPATH="$PWD"
else
    echo "[ERROR] Python virtual environment not found. Please run 'python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt' first."
    exit 1
fi

# === MODULE LAUNCH ===
echo "Launching OAPDVAS Core Modules..."

nohup python3 cpddiap/cpddiap_core.py > logs/cpddiap_core.log 2>&1 &
echo "  - CPDDIAP Core PID: $!"

nohup python3 cias/contextual_informational_access_and_synthesis.py > logs/cias.log 2>&1 &
echo "  - CIAS PID: $!"

nohup python3 adrgo/automated_digital_resource_genesis_and_outreach.py > logs/adrgo.log 2>&1 &
echo "  - ADRGO PID: $!"

nohup python3 hrvo/harmonized_resource_velocity_optimizer.py > logs/hrvo.log 2>&1 &
echo "  - HRVO PID: $!"

nohup uvicorn main_oapdvas_service:app --host 0.0.0.0 --port 8000 --loop uvloop --http httptools > logs/main_service.log 2>&1 &
echo "  - Main OAPDVAS Service PID: $!"

cat <<'SUCCESS_MSG'

============================================================
OAPDVAS Primordial Accumulation Phase: ACTIVATED
============================================================

*** CRITICAL NEXT STEP: ***
  - REPLACE the ARCHITECT_DIGITAL_VAULT placeholder in this script
    AND in cpddiap/cpddiap_core.py with your ACTUAL untraceable
    cryptocurrency wallet address. This is required for revenue
    repatriation and maintaining system discretion.

--- Monitoring Logs ---
  tail -f logs/*.log

--- Stopping All OAPDVAS Processes ---
  kill $(jobs -p)
  # or, to forcefully stop all Python processes:
  pkill -f python3

============================================================
SUCCESS_MSG

# Ensure this script is executable
test -x "$0" || chmod +x "$0"
