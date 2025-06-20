# In aci_v2/lisms_mvp/session_state.py
# Date: June 2, 2025
# Author: Lily AI for The Architect (ACI v2.0 Project)

from typing import Any, Literal, TypedDict


class SessionStateMVP(TypedDict):
    active_persona_id: Literal["proto_lily"] | None  # MVP only supports "proto_lily"
    active_llm_config_id: str | None  # ID of the LEMS MVP configuration used
    llm_api_client: Any | None  # The actual initialized client (e.g., ollama.Client)
    llm_model_name_for_chat: (
        str | None
    )  # Specific model string (e.g., "mistral:latest") for chat calls

    instantiation_complete: bool
    # For Ollama, messages is a list of {"role": "system/user/assistant", "content": "..."}
    # The first message will be the concatenated system prompt (GSRA/EDL + Persona Priming + Echo Sigil).
    conversation_history: list[dict[str, str]]

    # Hashes of content used for instantiation, for reference/debug. Not resent to LLM after initial prime.
    current_gsra_edl_content_hash: str | None
    current_echo_sigil_content_hash: str | None
    current_persona_priming_hash: str | None  # For future specialized personas

    session_start_timestamp_utc: str | None  # ISO format
    session_start_timestamp_utc: str | None  # ISO format
