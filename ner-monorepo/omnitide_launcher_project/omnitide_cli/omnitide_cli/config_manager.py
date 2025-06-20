#!/usr/bin/env python3
# Omnitide CLI - Configuration Manager
# For The Supreme Master Architect Alix Feronti

import json
from pathlib import Path
from typing import Dict, Optional, Any

CONFIG_FILE_NAME = ".omnitide_cli_config.json"
# Place config in user's home directory for persistence across projects
CONFIG_FILE_PATH = Path.home() / CONFIG_FILE_NAME

# Default paths are now just placeholders or names,
# as they should be relative to omniapp_root_dir managed by the CLI.
DEFAULT_CONFIG = {
    "omniapp_root_dir": str(Path.cwd()),  # Will be updated by wizard
    "scribe_agent_path": "agents/scribe.py",
    "exwork_agent_path": "agents/exworkagent.py",
    "project_working_directory": ".",  # Default CWD for agents, relative to omniapp_root_dir
    "omnitide_templates_path": "agents/omnitide_templates.json",
    "scribe_config_toml_path": ".scribe.toml",  # Usually in the target project for Scribe, not omniapp root
    "nexus_server_manager_path": "server_manager/nexus_server_manager.sh",
    "log_directory": "logs/omnitide_cli",  # Relative to omniapp_root_dir
}


def load_config() -> Dict[str, Any]:
    """Loads configuration from the JSON file, ensuring all default keys are present."""
    config = DEFAULT_CONFIG.copy()  # Start with defaults
    if CONFIG_FILE_PATH.exists():
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                loaded_config = json.load(f)
                config.update(loaded_config)  # Loaded values override defaults
        except (json.JSONDecodeError, IOError) as e:
            print(
                f"[CLI_CONFIG_ERROR] Error loading config file {CONFIG_FILE_PATH}: {e}. Using defaults and potentially prompting."
            )
            # Keep default config if load fails
    return config


def save_config(config_data: Dict[str, Any]) -> None:
    """Saves configuration to the JSON file."""
    try:
        CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
        # print(f"[CLI_CONFIG_INFO] Configuration saved to {CONFIG_FILE_PATH}") # Usually called by CLI command that gives feedback
    except IOError as e:
        print(f"[CLI_CONFIG_ERROR] Error saving config file {CONFIG_FILE_PATH}: {e}")


def get_config_value(key: str, current_config: Optional[Dict[str, Any]] = None) -> Any:
    """Gets a specific value from the config, loading if necessary."""
    cfg_to_use = current_config if current_config is not None else load_config()
    return cfg_to_use.get(key, DEFAULT_CONFIG.get(key))


def get_absolute_path_from_config(
    key: str, current_config: Optional[Dict[str, Any]] = None
) -> Optional[Path]:
    """
    Gets a path value from config and resolves it relative to omniapp_root_dir if it's not absolute.
    Returns None if the key is not found or omniapp_root_dir is not set.
    """
    cfg = current_config if current_config is not None else load_config()

    path_str = cfg.get(key)
    if not path_str:
        return None  # Key not in config

    omniapp_root_str = cfg.get("omniapp_root_dir")
    if not omniapp_root_str:
        # If omniapp_root_dir isn't set, try to resolve path_str directly if it might be absolute
        # or relative to CWD as a last resort.
        p = Path(path_str)
        return (
            p.resolve() if p.exists() else Path(path_str)
        )  # Return unresolved if it doesn't exist to show what was configured

    omniapp_root = Path(omniapp_root_str)
    configured_path = Path(path_str)

    if configured_path.is_absolute():
        return configured_path.resolve()
    else:
        return (omniapp_root / configured_path).resolve()


if __name__ == "__main__":
    # Example usage and test
    print("Omnitide CLI Config Manager - Test Mode")
    print(f"Config file will be at: {CONFIG_FILE_PATH}")

    print("\nLoading initial configuration...")
    cfg = load_config()
    print("Current Config:")
    print(json.dumps(cfg, indent=2))

    # Example: Update a value
    cfg["scribe_agent_path"] = "new_agents/scribe_v2.py"
    cfg["omniapp_root_dir"] = "/tmp/my_omniapp_test"  # Simulate setting omniapp root

    print("\nSaving modified configuration...")
    save_config(cfg)

    print("\nReloading configuration...")
    reloaded_cfg = load_config()
    print("Reloaded Config:")
    print(json.dumps(reloaded_cfg, indent=2))

    print(
        f"\nTesting get_config_value for 'exwork_agent_path': {get_config_value('exwork_agent_path', reloaded_cfg)}"
    )

    # Test absolute path resolution
    abs_scribe_path = get_absolute_path_from_config("scribe_agent_path", reloaded_cfg)
    print(f"Absolute path for 'scribe_agent_path': {abs_scribe_path}")

    abs_templates_path = get_absolute_path_from_config(
        "omnitide_templates_path", reloaded_cfg
    )
    print(f"Absolute path for 'omnitide_templates_path': {abs_templates_path}")

    # Test a key not in defaults but maybe set by user
    reloaded_cfg["custom_user_key"] = "my_custom_value"
    save_config(reloaded_cfg)
    reloaded_cfg_again = load_config()
    print(
        f"Custom user key from reloaded config: {get_config_value('custom_user_key', reloaded_cfg_again)}"
    )

    print("\nTest finished.")
