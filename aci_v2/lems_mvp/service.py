import logging
from typing import Any, Optional, Dict, List, Tuple
import ollama  # Official Ollama Python client

# from aci_v2.acls_mvp.service import ACIServiceMVP # For type hinting
# from .exceptions import LEMSError, LLMConfigNotFoundError, LLMClientInstantiationError, OllamaServiceError
# from .models import LEMSConfigMVP

ACIServiceMVP = Any

class LEMSServiceMVP:
    MODULE_NAME: str = "LEMS_MVP"
    ACLS_CONFIG_SECTION: str = "LEMS_MVP_Primary"
    ACLS_CONFIG_KEY_OLLAMA: str = "active_ollama_config_details"

    def __init__(self, acl_service: ACIServiceMVP):
        """
        Initializes the LEMS Service MVP with an ACLS handler.
        Args:
            acl_service: An initialized instance of ACIServiceMVP.
        Raises:
            ValueError: If acl_service is None.
        """
        if acl_service is None:
            raise ValueError("acl_service must not be None")
        self.acls = acl_service
        self.logger = self.acls.get_logger(f"ACI.{self.MODULE_NAME}")
        self._active_llm_client: Optional[Any] = None
        self._active_llm_config: Optional[Dict[str, Any]] = self._load_config_from_acls()
        if self._active_llm_config is None:
            self.logger.warning("LEMS is not yet configured.")
        self.logger.info("LEMS Service MVP Initialized.")

    def _load_config_from_acls(self) -> Optional[Dict[str, Any]]:
        config_dict = self.acls.get_config(self.ACLS_CONFIG_SECTION, self.ACLS_CONFIG_KEY_OLLAMA, fallback=None)
        if config_dict is not None and isinstance(config_dict, dict):
            self.logger.debug("Loaded LEMS MVP config from ACLS.")
            return config_dict
        elif config_dict is not None:
            self.logger.error("Malformed LEMS MVP config in ACLS.")
            return None
        else:
            self.logger.info("No LEMS MVP config found in ACLS.")
            return None

    def _save_config_to_acls(self, config_data: Dict[str, Any]) -> bool:
        try:
            self.acls.set_config(self.ACLS_CONFIG_SECTION, self.ACLS_CONFIG_KEY_OLLAMA, dict(config_data))
            self.logger.info("Saved LEMS MVP config to ACLS.")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save LEMS MVP config to ACLS: {e}")
            return False

    def configure_primary_ollama_endpoint(
        self,
        base_url: str,
        model_name: str,
        display_name: Optional[str] = None,
        timeout_seconds: int = 120,
        supports_system_prompt: bool = True
    ) -> Tuple[bool, str]:
        if not base_url or not model_name:
            raise ValueError("base_url and model_name must not be empty")
        config = {
            "config_id": "primary_ollama_mvp",
            "display_name": display_name or f"Ollama ({model_name} @ {base_url})",
            "provider_type": "ollama",
            "base_url": base_url,
            "model_name": model_name,
            "supports_system_prompt_directly": supports_system_prompt,
            "timeout_seconds": timeout_seconds,
            "last_tested_timestamp": None,
            "last_test_status": "UNTESTED"
        }
        if self._save_config_to_acls(config):
            self._active_llm_client = None
            self._active_llm_config = config
            self.logger.info(f"Primary Ollama endpoint '{config['display_name']}' configured successfully.")
            return True, f"Primary Ollama endpoint '{config['display_name']}' configured successfully."
        else:
            self.logger.error("Failed to save Ollama configuration to ACLS.")
            return False, "Failed to save Ollama configuration to ACLS."

    def get_active_llm_client_and_model(self) -> Optional[Tuple[Any, str]]:
        if self._active_llm_client and self._active_llm_config:
            return self._active_llm_client, self._active_llm_config["model_name"]
        active_config = self._load_config_from_acls()
        if not active_config or active_config.get("provider_type") != "ollama":
            self.logger.error("No active/valid Ollama MVP configuration found in ACLS. Please configure via ACI settings.")
            self._active_llm_client = None
            self._active_llm_config = None
            raise Exception("No active/valid Ollama MVP configuration found in ACLS. Please configure via ACI settings.")
        self._active_llm_config = active_config
        try:
            self.logger.info(f"Instantiating Ollama client for host: {active_config['base_url']}, model: {active_config['model_name']}")
            client = ollama.Client(host=active_config['base_url'], timeout=active_config['timeout_seconds'])
            self._active_llm_client = client
            return self._active_llm_client, active_config["model_name"]
        except Exception as e:
            self.logger.error(f"Failed to instantiate Ollama client: {e}")
            self._active_llm_client = None
            raise Exception(f"Failed to connect to or instantiate Ollama client at {active_config['base_url']}: {e}")

    def get_active_config_display_details(self) -> Optional[Dict[str, Any]]:
        config = self._load_config_from_acls()
        if config:
            return {
                "display_name": config["display_name"],
                "provider_type": config["provider_type"],
                "base_url": config["base_url"],
                "model_name": config["model_name"],
                "last_test_status": config["last_test_status"]
            }
        return None

    async def test_configured_ollama_connection(self) -> Tuple[bool, str]:
        active_config = self._load_config_from_acls()
        if not active_config or active_config.get("provider_type") != "ollama":
            return False, "No active Ollama configuration to test."
        test_success = False
        test_message = "Test failed."
        try:
            self.logger.info(f"Testing Ollama connection to {active_config['base_url']} for model {active_config['model_name']}")
            client = ollama.Client(host=active_config['base_url'], timeout=active_config['timeout_seconds'])
            client.list()
            test_success = True
            test_message = "Ollama connection successful. Server responded."
            self.logger.info(test_message)
        except Exception as e:
            test_message = f"Ollama connection test failed: {str(e)}"
            self.logger.error(test_message, exc_info=True)
            test_success = False
        active_config["last_tested_timestamp"] = None  # Should be set to current timestamp if needed
        active_config["last_test_status"] = test_message if test_success else f"ERROR: {test_message}"
        self._save_config_to_acls(active_config)
        return test_success, test_message
