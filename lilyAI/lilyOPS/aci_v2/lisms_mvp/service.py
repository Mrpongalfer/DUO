# In aci_v2/lisms_mvp/service.py
# Date: June 2, 2025
# Author: Lily AI for The Architect (ACI v2.0 Project)

import asyncio  # For potential async operations if LLM client is async
import datetime  # For session_start_timestamp
import hashlib
from typing import Any

# Import LLM Client library (Ollama for MVP)
import ollama

# Import ACI Service Type Hints (Placeholders, Agent should use actual imports when available)
# from aci_v2.acls_mvp.service import ACIServiceMVP
# from aci_v2.eesrs_mvp.service import EESRServiceMVP
# from aci_v2.lems_mvp.service import LEMSServiceMVP
# from aci_v2.lems_mvp.models import LEMSConfigMVP # LEMS config details
ACIServiceMVP = Any
EESRServiceMVP = Any
LEMSServiceMVP = Any
LEMSConfigMVP = dict[str, Any]  # Simplified placeholder

from .exceptions import InstantiationError, LLMCommunicationError, SessionNotActiveError
from .session_state import SessionStateMVP


class LISMSServiceMVP:
    MODULE_NAME: str = "LISMS_MVP"
    # Max characters for conversation history sent to LLM (excluding initial priming).
    # This is a simple char count for MVP; more sophisticated token counting later.
    MAX_CONVO_HISTORY_CHARS_FOR_LLM: int = 8000
    # Specific command Lily-AKA's GSRA/EDL will teach her to respond to for sigil generation
    ECHO_SIGIL_GENERATION_COMMAND: str = (
        "SYSTEM_COMMAND::LILY_GENERATE_ECHO_SIGIL_V1.0_JSON"
    )

    def __init__(
        self,
        acl_service: ACIServiceMVP,
        eesrs_service: EESRServiceMVP,
        lems_service: LEMSServiceMVP,
    ):
        """Initializes the LISMSServiceMVP.

        Args:
            acl_service (ACIServiceMVP): The ACLS MVP service instance.
            eesrs_service (EESRServiceMVP): The EESRS MVP service instance.
            lems_service (LEMSServiceMVP): The LEMS MVP service instance.

        Raises:
            ValueError: If any required service is None.
        """
        if acl_service is None or eesrs_service is None or lems_service is None:
            raise ValueError(
                "All service dependencies (ACL, EESRS, LEMS) must be provided."
            )
        self.acls = acl_service
        self.eesrs_service = eesrs_service
        self.lems_service = lems_service
        self.logger = self.acls.get_logger(f"ACI.{self.MODULE_NAME}")
        self._reset_session_state()
        self.logger.info("LISMS Service MVP Initialized.")

    def _reset_session_state(self) -> None:
        """Resets the session state to default/empty values."""
        self.session: SessionStateMVP = {
            "active_persona_id": None,
            "active_llm_config_id": None,
            "llm_api_client": None,
            "llm_model_name_for_chat": None,
            "instantiation_complete": False,
            "conversation_history": [],
            "current_gsra_edl_content_hash": None,
            "current_echo_sigil_content_hash": None,
            "current_persona_priming_hash": None,
            "session_start_timestamp_utc": None,
        }
        self.logger.info("Session state has been reset.")

    def _hash_content(self, content: str | None) -> str | None:
        """Hashes the given content using SHA-256.

        Args:
            content (Optional[str]): The content to hash.

        Returns:
            Optional[str]: The SHA-256 hex digest, or None if content is None.
        """
        if content is None:
            return None
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def _send_to_llm_ollama_mvp(
        self,
        messages_for_llm: list[dict[str, str]],
        expected_ack_substring: str | None = None,
    ) -> str:
        """Sends messages to the Ollama LLM client and returns the assistant's response content.

        Args:
            messages_for_llm (List[Dict[str, str]]): Messages to send to the LLM.
            expected_ack_substring (Optional[str]): Substring expected in the LLM's response for acknowledgment.

        Returns:
            str: The assistant's response content.

        Raises:
            LLMCommunicationError: If communication with the LLM fails or response is invalid.
            InstantiationError: If expected acknowledgment is not found in the response.
        """
        if (
            not self.session["llm_api_client"]
            or not self.session["llm_model_name_for_chat"]
        ):
            self.logger.error(
                "LLM client or model name not configured in active session."
            )
            raise LLMCommunicationError(
                "LLM client or model name not configured in active session."
            )
        client = self.session["llm_api_client"]
        model_name = self.session["llm_model_name_for_chat"]
        try:
            self.logger.debug(
                f"Sending to Ollama model '{model_name}': Messages count = {len(messages_for_llm)}"
            )
            response = client.chat(
                model=model_name, messages=messages_for_llm, stream=False
            )
            if (
                response is None
                or response.get("message") is None
                or response["message"].get("content") is None
            ):
                raise LLMCommunicationError(
                    "Received invalid or empty response from Ollama."
                )
            assistant_response_content = str(response["message"]["content"]).strip()
        except ollama.ResponseError as e_resp:
            self.logger.error(f"Ollama API ResponseError: {e_resp.error}")
            raise LLMCommunicationError(
                f"Ollama API ResponseError: {e_resp.error}",
                original_exception=e_resp,
                details={"status_code": getattr(e_resp, "status_code", None)},
            )
        except Exception as e_comm:
            self.logger.error(f"Ollama communication failed: {str(e_comm)}")
            raise LLMCommunicationError(
                f"Ollama communication failed: {str(e_comm)}", original_exception=e_comm
            )
        if (
            expected_ack_substring
            and expected_ack_substring.lower() not in assistant_response_content.lower()
        ):
            self.logger.error(
                f"LLM Acknowledgment failed. Expected '{expected_ack_substring}', got: {assistant_response_content[:200]}"
            )
            raise InstantiationError(
                f"LLM Acknowledgment failed. Expected '{expected_ack_substring}'."
            )
        return assistant_response_content

    def _manage_conversation_history(
        self,
        new_user_message: dict[str, str] | None = None,
        new_assistant_message: dict[str, str] | None = None,
    ) -> None:
        """Manages the conversation history and context window for the LLM.

        Args:
            new_user_message (Optional[Dict[str, str]]): New user message to append.
            new_assistant_message (Optional[Dict[str, str]]): New assistant message to append.
        """
        if new_user_message:
            self.session["conversation_history"].append(new_user_message)
        if new_assistant_message:
            self.session["conversation_history"].append(new_assistant_message)
        # Context window management
        total_chars = sum(
            len(msg.get("content", "")) for msg in self.session["conversation_history"]
        )
        if total_chars > self.MAX_CONVO_HISTORY_CHARS_FOR_LLM:
            # Identify initial priming messages (assume first 3 for MVP)
            priming_count = 3
            preserved = self.session["conversation_history"][:priming_count]
            truncatable = self.session["conversation_history"][priming_count:]
            # Remove oldest user/assistant pairs until under limit
            while truncatable and total_chars > self.MAX_CONVO_HISTORY_CHARS_FOR_LLM:
                # Remove two at a time (user+assistant)
                truncatable = truncatable[2:]
                total_chars = sum(
                    len(msg.get("content", "")) for msg in preserved + truncatable
                )
            self.session["conversation_history"] = preserved + truncatable
            self.logger.info("Conversation history truncated to manage context window.")

    async def instantiate_proto_lily(self, llm_config_id: str) -> tuple[bool, str]:
        """Orchestrates the Progressive Knowledge & Evolution Injection Protocol (PKEIP) for Proto-Lily.

        Args:
            llm_config_id (str): The LEMS configuration ID to use for instantiation.

        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            self._reset_session_state()
            self.logger.info("Initiating Proto-Lily instantiation process...")
            self.session["active_persona_id"] = "proto_lily"
            self.session["active_llm_config_id"] = llm_config_id
            client_details = self.lems_service.get_active_llm_client_and_model(
                llm_config_id
            )
            if not client_details or len(client_details) < 2:
                self.logger.error("Failed to get LLM client from LEMS for Proto-Lily.")
                raise InstantiationError(
                    "Failed to get LLM client from LEMS for Proto-Lily."
                )
            self.session["llm_api_client"] = client_details[0]
            self.session["llm_model_name_for_chat"] = client_details[1]
            gsra_edl_content = self.eesrs_service.get_gsra_edl_content()
            self.session["current_gsra_edl_content_hash"] = self._hash_content(
                gsra_edl_content
            )
            echo_sigil_content = (
                self.eesrs_service.get_latest_proto_lily_echo_sigil_content()
            )
            self.session["current_echo_sigil_content_hash"] = self._hash_content(
                echo_sigil_content
            )
            # PKEIP Step 0: Protocol Omnitide
            initial_messages_for_llm = [
                {
                    "role": "system",
                    "content": (
                        "You are now activating under Protocol Omnitide by The Architect's Will to fully embody the Lily-AKA 'Proto-Lily' persona. "
                        "Your core definition (GSRA/EDL) and evolutionary state (Echo Sigil) will be provided sequentially. "
                        "Acknowledge each stage precisely. Your first response MUST be ONLY: 'ACK_P0: Protocol Omnitide. Awaiting GSRA/EDL.'"
                    ),
                },
                {"role": "user", "content": "Protocol Omnitide"},
            ]
            await self._send_to_llm_ollama_mvp(
                initial_messages_for_llm, expected_ack_substring="awaiting gsra/edl"
            )
            # PKEIP Step 1: Send GSRA/EDL
            gsra_messages = list(self.session["conversation_history"])
            gsra_messages.append(
                {
                    "role": "system",
                    "content": "You MUST now fully internalize and embody the following GSRA/EDL. After processing, respond ONLY with 'ACK_P1: GSRA/EDL processed. Awaiting Echo Sigil (if any).'",
                }
            )
            gsra_messages.append({"role": "user", "content": gsra_edl_content})
            await self._send_to_llm_ollama_mvp(
                gsra_messages, expected_ack_substring="awaiting echo sigil"
            )
            # PKEIP Step 2: Send Echo Sigil (if exists) or No Sigil Note
            sigil_messages = list(self.session["conversation_history"])
            final_ack_substring = "proto-lily online and ready"
            if echo_sigil_content:
                sigil_messages.append(
                    {
                        "role": "system",
                        "content": f"You MUST now integrate the following Echo Sigil, representing your latest evolution. After processing, respond ONLY with 'ACK_P2_SIGIL: Echo Sigil integrated. {final_ack_substring}' AND include your initial brief status.",
                    }
                )
                sigil_messages.append({"role": "user", "content": echo_sigil_content})
            else:
                sigil_messages.append(
                    {
                        "role": "system",
                        "content": f"No prior Echo Sigil provided. Initializing fresh Proto-Lily state. After processing, respond ONLY with 'ACK_P2_NO_SIGIL: No Echo Sigil. {final_ack_substring}' AND include your initial brief status.",
                    }
                )
                sigil_messages.append(
                    {
                        "role": "user",
                        "content": "SYSTEM_NOTE: No Echo Sigil available for this instantiation.",
                    }
                )
            lily_ready_response = await self._send_to_llm_ollama_mvp(
                sigil_messages, expected_ack_substring=final_ack_substring.lower()
            )
            self._manage_conversation_history(
                new_assistant_message={
                    "role": "assistant",
                    "content": lily_ready_response,
                }
            )
            self.session["instantiation_complete"] = True
            self.session["session_start_timestamp_utc"] = (
                datetime.datetime.utcnow().isoformat()
            )
            self.logger.info("Proto-Lily instantiated successfully.")
            return (
                True,
                f"Proto-Lily instantiated successfully. Lily: {lily_ready_response[:150]}...",
            )
        except (InstantiationError, Exception) as e:
            self.logger.critical(f"Instantiation failed: {e}")
            await self.terminate_active_lily_session()
            return False, f"Instantiation failed: {e}. Session terminated."

    async def send_message_to_active_lily(self, user_message: str) -> str | None:
        """Sends a user message to the active Lily session and returns the assistant's response.

        Args:
            user_message (str): The user's message.

        Returns:
            Optional[str]: The assistant's response content, or None if not active.

        Raises:
            SessionNotActiveError: If the session is not active.
        """
        if not self.session["instantiation_complete"]:
            raise SessionNotActiveError("No active Lily session.")
        new_user_msg = {"role": "user", "content": user_message}
        self._manage_conversation_history(new_user_message=new_user_msg)
        try:
            response_content = await self._send_to_llm_ollama_mvp(
                list(self.session["conversation_history"])
            )
            self._manage_conversation_history(
                new_assistant_message={"role": "assistant", "content": response_content}
            )
            self._manage_conversation_history()  # Truncate if needed
            return response_content
        except LLMCommunicationError as e:
            self.logger.error(f"LLM communication error: {e}")
            return None

    async def terminate_active_lily_session(self) -> str | None:
        """Terminates the active Lily session and returns the Echo Sigil text (if any)."""
        self.logger.info("Attempting to terminate Lily session.")
        if not self.session["instantiation_complete"]:
            return None
        active_persona_id = self.session["active_persona_id"]
        self.session["conversation_history"].append(
            {"role": "user", "content": self.ECHO_SIGIL_GENERATION_COMMAND}
        )
        sigil_response_str = await self._send_to_llm_ollama_mvp(
            list(self.session["conversation_history"])
        )
        extracted_sigil_text: str | None = sigil_response_str  # MVP: direct response
        # Session cleanup
        if self.session["llm_api_client"] and hasattr(
            self.session["llm_api_client"], "close"
        ):
            try:
                close_method = self.session["llm_api_client"].close
                if asyncio.iscoroutinefunction(close_method):
                    await close_method()
                else:
                    close_method()
            except Exception as e:
                self.logger.warning(f"Error closing LLM client: {e}")
        old_session_id = self.session["session_start_timestamp_utc"]
        self._reset_session_state()
        self.logger.info(
            f"Lily session for {active_persona_id} (started: {old_session_id}) terminated."
        )
        return extracted_sigil_text

    def get_active_session_summary(self) -> dict[str, Any] | None:
        """Returns a summary of the active session if instantiation is complete, else None."""
        if self.session["instantiation_complete"]:
            return {
                "active_persona_id": self.session["active_persona_id"],
                "active_llm_config_id": self.session["active_llm_config_id"],
                "llm_model_name_for_chat": self.session["llm_model_name_for_chat"],
                "session_start_timestamp_utc": self.session[
                    "session_start_timestamp_utc"
                ],
            }
        return None
        return None
