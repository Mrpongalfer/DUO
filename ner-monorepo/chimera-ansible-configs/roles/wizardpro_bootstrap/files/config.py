# Content for roles/wizardpro_bootstrap/files/config.py
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env file relative to this config's location if it exists
try:
    dotenv_path = Path(__file__).parent / ".env"
    if dotenv_path.is_file():
        load_dotenv(dotenv_path=dotenv_path)
        logging.getLogger(__name__).info(
            f"Loaded environment variables from: {dotenv_path}"
        )
    else:
        logging.getLogger(__name__).debug(
            f".env file not found at {dotenv_path}, relying on system environment."
        )
except Exception as e:
    logging.getLogger(__name__).warning(f"Error loading .env file: {e}")

logger = logging.getLogger(__name__)

# --- Core Settings ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
# Ensure project root is calculated relative to this file's expected location
# Assumes config.py is in orchestrator/
PROJECT_ROOT_PATH = Path(__file__).parent.parent.resolve()
PROJECT_CONTEXT_DIR = str(PROJECT_ROOT_PATH / "project_contexts")
PROMPT_DIR_PATH = str(PROJECT_ROOT_PATH / "orchestrator" / "prompt_templates")

# --- API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
# Add other keys here

# --- Model Defaults (Example using Ollama) ---
# These can be overridden by orchestrator/.env
DEFAULT_LLM_MODEL = os.getenv(
    "DEFAULT_LLM_MODEL", "ollama:mistral-nemo:12b-instruct-2407-q4_k_m"
)
DEFAULT_PARSING_MODEL = os.getenv("DEFAULT_PARSING_MODEL", DEFAULT_LLM_MODEL)
DEFAULT_ANALYSIS_MODEL = os.getenv("DEFAULT_ANALYSIS_MODEL", DEFAULT_LLM_MODEL)

# --- Phase Configuration ---
MAX_REFINEMENT_ATTEMPTS = int(os.getenv("MAX_REFINEMENT_ATTEMPTS", "3"))


# --- Validation ---
def validate_config():
    # Basic check for directories needed by PromptManager and Context saving
    valid = True
    if not os.path.isdir(PROMPT_DIR_PATH):
        logger.error(f"Config Error: Prompt directory not found: {PROMPT_DIR_PATH}")
        valid = False
    if not os.path.isdir(PROJECT_CONTEXT_DIR):
        logger.warning(
            f"Project context directory not found: {PROJECT_CONTEXT_DIR}. Attempting to create."
        )
        try:
            os.makedirs(PROJECT_CONTEXT_DIR)
        except OSError as e:
            logger.error(
                f"Config Error: Could not create project context directory {PROJECT_CONTEXT_DIR}: {e}"
            )
            valid = False
    return valid


# Run validation on import? Or rely on Orchestrator to check?
# if not validate_config():
#     logger.critical("Mandatory configuration paths missing or invalid. Exiting.")
#     import sys
#     sys.exit(1)

logger.info("Configuration loading attempt complete from config.py.")
