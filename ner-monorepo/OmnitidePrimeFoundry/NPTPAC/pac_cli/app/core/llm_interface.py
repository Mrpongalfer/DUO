# pac_cli/app/core/llm_interface.py
        import json
        import logging
        from typing import Any, Dict, Optional, Tuple
        # from .config_manager import ConfigManager # If needed for direct config access
        # For direct HTTP calls, you might add:
        # import httpx 
        # For Ex-Work integration:
        # from .agent_runner import ExWorkAgentRunner 

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
            TODO, Architect: Flesh this out based on chosen LLM strategy.
            ".""
            def __init__(self, config_manager: Any, ex_work_runner: Optional[Any] = None): # ConfigManager, ExWorkAgentRunner
                self.config = config_manager
                self.ex_work_runner = ex_work_runner # Optional, if using Ex-Work for LLM calls

                self.provider = self.config.get("llm_interface.provider", "generic")
                self.api_base_url = self.config.get("llm_interface.api_base_url")
                self.default_model = self.config.get("llm_interface.default_model")
                self.api_key_env_var = self.config.get("llm_interface.api_key_env_var")
                self.timeout = self.config.get("llm_interface.timeout_seconds", 180)
                self.max_retries = self.config.get("llm_interface.max_retries", 2)

                # TODO, Architect: Initialize HTTP client (e.g., httpx.Client) if making direct calls.
                # self.http_client = None # Example: httpx.Client(base_url=self.api_base_url, timeout=self.timeout)

                logger.info(f"LLMInterface initialized. Provider: {self.provider}, Model: {self.default_model}")
                if self.provider == "generic" and self.ex_work_runner:
                    logger.info("Generic provider configured. LLM calls may be routed via Ex-Work agent's CALL_LOCAL_LLM.")


            def send_prompt(self,
                            prompt: str,
                            model_override: Optional[str] = None,
                            system_message: Optional[str] = None, # For chat-like models
                            temperature: Optional[float] = None, # Common LLM param
                            max_tokens: Optional[int] = None,    # Common LLM param
                            output_format_json: bool = False      # If LLM should be hinted to output JSON
                           ) -> Tuple[bool, Any]: # Returns (success, response_content_or_error_dict)
                """
                Sends a prompt to the configured LLM.
                TODO, Architect: Implement the actual LLM call logic here.
                                 This could be a direct HTTP request to OpenAI/Anthropic/Ollama,
                                 or it could construct an Ex-Work JSON payload to use its
                                 CALL_LOCAL_LLM action, especially if Ollama is preferred.
                ".""
                target_model = model_override or self.default_model
                logger.info(f"Sending prompt (approx {len(prompt)} chars) to LLM (model: {target_model})...")

                # --- Option 1: Route via Ex-Work Agent's CALL_LOCAL_LLM (if configured and available) ---
                if self.provider == "ollama" and self.ex_work_runner: # Or generic with Ex-Work
                    logger.info(f"Routing LLM prompt via Ex-Work agent's CALL_LOCAL_LLM action.")
                    ex_work_instruction = {
                        "step_id": "pac_llm_interface_call",
                        "description": f"PAC internal call to LLM: {prompt[:50]}...",
                        "actions": [{
                            "type": "CALL_LOCAL_LLM",
                            "prompt": prompt,
                            "model": target_model, # Ex-Work handler uses its own defaults if this is None
                            # TODO, Architect: Ex-Work's CALL_LOCAL_LLM needs to support 'options' for temp, max_tokens, system_message, json_format
                            "options": { # Conceptual options for Ex-Work
                                "system": system_message,
                                "temperature": temperature,
                                "num_predict": max_tokens, # Ollama specific for max_tokens
                                "format": "json" if output_format_json else ""
                            }
                        }]
                    }
                    # Assume ex_work_runner is properly initialized and project_path is relevant (e.g. NPT_BASE_DIR)
                    # This needs careful thought on what CWD Ex-Work should use for these calls.
                    project_path_for_exwork = self.config.npt_base_dir # Or Path.cwd()

                    # The ExWorkAgentRunner.execute_instruction_block returns (bool, dict)
                    # The dict is the *entire output payload from Ex-Work*.
                    # We need to extract the *actual LLM response* from that.
                    exw_success, exw_output = self.ex_work_runner.execute_instruction_block(
                        json.dumps(ex_work_instruction),
                        project_path=project_path_for_exwork
                    )
                    if exw_success and exw_output.get("overall_success"):
                        # Ex-Work's CALL_LOCAL_LLM returns (bool, response_text_or_error_msg) as its result_payload.
                        # This needs to be accessible from exw_output["action_results"][0]["message_or_payload"]
                        try:
                            llm_action_result = exw_output["action_results"][0]["message_or_payload"]
                            # Ex-Work's CALL_LOCAL_LLM returns a string, which might be JSON if it succeeded
                            # The first element of the tuple from handler is success, second is message string
                            # But action_results has message_or_payload as the string.

                            # This structure depends heavily on how Ex-Work formats its "message_or_payload" for CALL_LOCAL_LLM
                            # Assuming message_or_payload directly IS the LLM's text response or an error message from that handler.
                            if exw_output["action_results"][0]["success"]: # Check success of the *CALL_LOCAL_LLM action itself*
                                response_text = llm_action_result
                                if output_format_json:
                                    try:
                                        return True, json.loads(response_text)
                                    except json.JSONDecodeError as je:
                                        logger.error(f"LLM via Ex-Work was asked for JSON but did not return valid JSON: {je}")
                                        return False, {"error": "LLM via Ex-Work Invalid JSON response", "details": response_text}
                                return True, response_text # String response
                            else: # CALL_LOCAL_LLM action failed
                                logger.error(f"Ex-Work's CALL_LOCAL_LLM action failed: {llm_action_result}")
                                return False, {"error": "Ex-Work CALL_LOCAL_LLM action failed", "details": llm_action_result}
                        except (IndexError, KeyError, TypeError) as e:
                            logger.error(f"Could not parse LLM response from Ex-Work output: {e}. Output: {exw_output}")
                            return False, {"error": "Failed to parse LLM response from Ex-Work", "details": str(exw_output)}
                    else: # Ex-Work instruction block execution failed
                        logger.error(f"Ex-Work execution failed when trying to call LLM. Output: {exw_output}")
                        return False, {"error": "Ex-Work execution failed for LLM call", "details": exw_output.get("status_message", "Unknown Ex-Work error")}

                # --- Option 2: Direct HTTP call (Example for Ollama-like API, needs httpx client setup) ---
                elif self.provider == "ollama" or (self.provider == "generic" and not self.ex_work_runner) : # Direct call
                    if not self.api_base_url or not target_model:
                        return False, {"error": "LLM API base URL or model not configured for direct call."}

                    # TODO, Architect: Implement direct HTTP call using self.http_client (e.g., httpx)
                    # This would involve:
                    # 1. Constructing the payload (model, prompt, stream:false, options for temp/max_tokens, format:json if output_format_json).
                    #    Refer to specific LLM API docs (Ollama, OpenAI, Anthropic).
                    # 2. Making the POST request with headers (Authorization if API key needed).
                    # 3. Handling retries for transient network errors.
                    # 4. Parsing the response (JSON).
                    # 5. Extracting the content from the response structure.
                    # Example (Conceptual for Ollama direct call):
                    # payload = {"model": target_model, "prompt": prompt, "stream": False}
                    # if output_format_json: payload["format"] = "json"
                    # if system_message: payload["system"] = system_message 
                    # options = {}
                    # if temperature is not None: options["temperature"] = temperature
                    # if max_tokens is not None: options["num_predict"] = max_tokens # Ollama uses num_predict
                    # if options: payload["options"] = options
                    # try:
                    #   response = self.http_client.post("/api/generate", json=payload, timeout=self.timeout) # Assuming httpx client with base_url
                    #   response.raise_for_status()
                    #   data = response.json()
                    #   if data.get("error"): return False, {"error": "LLM API Error", "details": data["error"]}
                    #   content = data.get("response", "") if not output_format_json else data # If format:json, response might be the JSON object directly
                    #   return True, content
                    # except Exception as e:
                    #   logger.error(f"Direct LLM API call failed: {e}", exc_info=True)
                    #   return False, {"error": "Direct LLM API call failed", "details": str(e)}

                    logger.warning("Direct LLM call logic in LLMInterface not fully implemented yet. Needs specific API client code.")
                    return False, {"error": "LLM direct call not implemented", "details": "TODO, Architect: Implement direct HTTP/API calls."}

                else: # Other providers or misconfiguration
                    logger.error(f"LLM provider '{self.provider}' not supported or Ex-Work runner unavailable for generic/Ollama.")
                    return False, {"error": "Unsupported LLM provider or configuration."}

            # TODO, Architect: Add methods for specific LLM tasks if needed, e.g.:
            # def summarize_text(self, text: str, model_override: Optional[str] = None) -> Tuple[bool, str]:
            # def generate_code_from_prompt(self, requirements: str, language: str = "python") -> Tuple[bool, str]:
            # def classify_text(self, text: str, categories: List[str]) -> Tuple[bool, str]: