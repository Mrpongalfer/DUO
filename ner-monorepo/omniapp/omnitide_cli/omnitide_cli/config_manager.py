# Omnitide CLI - config_manager.py (v1.2 Bootstrap)
import json
from pathlib import Path
from typing import Dict, Optional, Any

CONFIG_FILE_NAME = ".omnitide_cli_config.json"  # Stored in user's home directory
CONFIG_FILE_PATH = Path.home() / CONFIG_FILE_NAME

DEFAULT_CONFIG = {
    "omnitide_app_root": "",  # To be populated by bootstrap or wizard with OMNIAPP_DIR
    "agents_dir": "agents",  # Relative to omniapp_root
    "scribe_agent_script": "scribe.py",  # Name of script within agents_dir
    "exwork_agent_script": "exworkagent.py",  # Name of script within agents_dir
    "omnitide_templates_file": "omnitide_templates.json",  # Name of file, expected in agents_dir relative to omniapp_root
    "default_project_cwd": ".",  # Default CWD for agents, relative to omniapp_root or absolute
    "default_scribe_config_toml": ".scribe.toml",  # Default name for Scribe's config, relative to project_cwd
}


def load_config() -> Dict[str, Any]:
    """Loads configuration from the JSON file, applying defaults for missing keys."""
    if CONFIG_FILE_PATH.exists():
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                config_from_file = json.load(f)
            # Merge with defaults: ensure all default keys exist, file values override
            merged_config = DEFAULT_CONFIG.copy()
            merged_config.update(config_from_file)  # Values from file take precedence
            return merged_config
        except (json.JSONDecodeError, IOError) as e:
            print(
                f"[CLI_CONFIG_ERROR] Error loading config file {CONFIG_FILE_PATH}: {e}. Using defaults."
            )
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config_data: Dict[str, Any]) -> None:
    """Saves configuration to the JSON file."""
    try:
        CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
        # print(f"[CLI_CONFIG_INFO] Configuration saved to {CONFIG_FILE_PATH}") # Can be verbose
    except IOError as e:
        print(
            f"[CLI_CONFIG_ERROR] Error saving CLI config file {CONFIG_FILE_PATH}: {e}"
        )


def get_config_value(key: str, current_config: Optional[Dict[str, Any]] = None) -> Any:
    """Gets a specific value from the config, loading if necessary."""
    config_to_use = current_config if current_config is not None else load_config()
    return config_to_use.get(
        key, DEFAULT_CONFIG.get(key)
    )  # Fallback to default dict if key somehow missing after load
