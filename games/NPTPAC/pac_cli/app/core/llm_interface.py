# pac_cli/app/core/llm_interface.py
import json
import logging
from typing import Any, Optional, Tuple

# For direct HTTP calls, you might add:
# For Ex-Work integration:

logger = logging.getLogger(__name__)
# Note: The Ex-Work agent provided uses Ollama via direct HTTP requests.
# This LLMInterface could be expanded to use a dedicated Ollama Python client,
# or adapt its HTTP request logic from Ex-Work for more features (e.g., chat, embeddings).
# For now, it provides a generic structure that could call out to Ex-Work's
# CALL_LOCAL_LLM action if PAC needs general LLM access without direct HTTP handling.
# Alternatively, PAC could implement its own direct HTTP calls to Ollama here.


class LLMInterface:
    """
    Provides an interface for PAC to interact with LLMs.
    This could be direct API calls or orchestration via an agent like Ex-Work.
    """

    def __init__(self, config_manager: Any, ex_work_runner: Optional[Any] = None):
        self.config = config_manager
        self.ex_work_runner = ex_work_runner

        self.provider = self.config.get("llm_interface.provider", "generic")
        self.api_base_url = self.config.get("llm_interface.api_base_url")
        self.default_model = self.config.get("llm_interface.default_model")
        self.api_key_env_var = self.config.get("llm_interface.api_key_env_var")
        self.timeout = self.config.get("llm_interface.timeout_seconds", 180)
        self.max_retries = self.config.get("llm_interface.max_retries", 2)

        # Optionally initialize HTTP client if making direct calls
        # self.http_client = httpx.Client(base_url=self.api_base_url, timeout=self.timeout) # Uncomment if needed

        logger.info(
            f"LLMInterface initialized. Provider: {self.provider}, Model: {self.default_model}"
        )
        if self.provider == "generic" and self.ex_work_runner:
            logger.info(
                "Generic provider configured. LLM calls may be routed via Ex-Work agent's CALL_LOCAL_LLM."
            )

    def send_prompt(
        self,
        prompt: str,
        model_override: Optional[str] = None,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        output_format_json: bool = False,
    ) -> Tuple[bool, Any]:
        """
        Sends a prompt to the configured LLM.
        This could be a direct HTTP request to OpenAI/Anthropic/Ollama,
        or it could construct an Ex-Work JSON payload to use its CALL_LOCAL_LLM action.
        """
        target_model = model_override or self.default_model
        logger.info(
            f"Sending prompt (approx {len(prompt)} chars) to LLM (model: {target_model})..."
        )

        # --- Option 1: Route via Ex-Work Agent's CALL_LOCAL_LLM (if configured and available) ---
        if self.provider == "ollama" and self.ex_work_runner:
            logger.info("Routing LLM prompt via Ex-Work agent's CALL_LOCAL_LLM action.")
            ex_work_instruction = {
                "step_id": "pac_llm_interface_call",
                "description": f"PAC internal call to LLM: {prompt[:50]}...",
                "actions": [
                    {
                        "type": "CALL_LOCAL_LLM",
                        "prompt": prompt,
                        "model": target_model,
                        "options": {
                            "system": system_message,
                            "temperature": temperature,
                            "num_predict": max_tokens,
                            "format": "json" if output_format_json else "",
                        },
                    }
                ],
            }
            project_path_for_exwork = self.config.npt_base_dir
            exw_success, exw_output = self.ex_work_runner.execute_instruction_block(
                json.dumps(ex_work_instruction), project_path=project_path_for_exwork
            )
            if exw_success and exw_output.get("overall_success"):
                try:
                    llm_action_result = exw_output["action_results"][0][
                        "message_or_payload"
                    ]
                    if exw_output["action_results"][0]["success"]:
                        response_text = llm_action_result
                        if output_format_json:
                            try:
                                return True, json.loads(response_text)
                            except json.JSONDecodeError as je:
                                logger.error(
                                    f"LLM via Ex-Work was asked for JSON but did not return valid JSON: {je}"
                                )
                                return False, {
                                    "error": "LLM via Ex-Work Invalid JSON response",
                                    "details": response_text,
                                }
                        return True, response_text
                    else:
                        logger.error(
                            f"Ex-Work's CALL_LOCAL_LLM action failed: {llm_action_result}"
                        )
                        return False, {
                            "error": "Ex-Work CALL_LOCAL_LLM action failed",
                            "details": llm_action_result,
                        }
                except (IndexError, KeyError, TypeError) as e:
                    logger.error(
                        f"Could not parse LLM response from Ex-Work output: {e}. Output: {exw_output}"
                    )
                    return False, {
                        "error": "Failed to parse LLM response from Ex-Work",
                        "details": str(exw_output),
                    }
            else:
                logger.error(
                    f"Ex-Work execution failed when trying to call LLM. Output: {exw_output}"
                )
                return False, {
                    "error": "Ex-Work execution failed for LLM call",
                    "details": exw_output.get(
                        "status_message", "Unknown Ex-Work error"
                    ),
                }

        # --- Option 2: Direct HTTP call (Example for Ollama-like API, needs httpx client setup) ---
        elif self.provider == "ollama" or (
            self.provider == "generic" and not self.ex_work_runner
        ):
            if not self.api_base_url or not target_model:
                return False, {
                    "error": "LLM API base URL or model not configured for direct call."
                }

            # TODO: Implement direct HTTP call using self.http_client (e.g., httpx)
            # See comments in the original for details on payload and error handling.
            logger.warning(
                "Direct LLM call logic in LLMInterface not fully implemented yet. Needs specific API client code."
            )
            return False, {
                "error": "LLM direct call not implemented",
                "details": "Implement direct HTTP/API calls.",
            }

        else:
            logger.error(
                f"LLM provider '{self.provider}' not supported or Ex-Work runner unavailable for generic/Ollama."
            )
            return False, {"error": "Unsupported LLM provider or configuration."}

    # Additional methods for specific LLM tasks can be added here as needed.
