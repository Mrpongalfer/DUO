#!/usr/bin/env python3
# extract_shards_from_lily_log.py
# Helper script for ExWorkAgentV2 to extract Memory Shards from Scribe-parsed Lily logs.
# Receives Scribe's JSON output via STDIN.
# Prints a JSON object to STDOUT: {"status": "success", "shards_extracted": [...], "summary": "..."}

import json
import sys
import argparse
import re  # For more advanced pattern matching


# --- Basic Logging to stderr for ExWork to capture if needed ---
def log_stderr(message):
    print(f"[ExtractorScript] {message}", file=sys.stderr, flush=True)


def create_shard(
    shard_type,
    content,
    context_snippet=None,
    keywords=None,
    architect_sentiment=None,
    is_core=False,
):
    """Helper to create a memory shard dictionary."""
    shard = {
        "shard_type": shard_type,
        "content": str(content).strip(),
        "context_snippet": str(context_snippet).strip() if context_snippet else None,
        "keywords": (
            ", ".join(sorted(list(set(kw.lower() for kw in keywords))))
            if keywords
            else None
        ),
        "architect_sentiment": architect_sentiment,
        "is_core_memory": is_core,
        # timestamp_created will be added by LilyPersonaHandler when inserting into DB
    }
    # Remove None values for cleaner JSON
    return {k: v for k, v in shard.items() if v is not None}


def extract_shards_from_parsed_log(
    parsed_log_data: dict, persona_summary: Optional[str] = None
) -> List[Dict]:
    """
    Analyzes parsed conversation turns and extracts Memory Shards.
    Architect: This is where your core AI/NLP or sophisticated rule-based logic will go!
    The current implementation is a placeholder with very basic keyword spotting.
    """
    shards = []
    log_stderr(
        f"Starting shard extraction. Persona summary (first 50 chars): '{persona_summary[:50] if persona_summary else 'None'}'"
    )

    if (
        not parsed_log_data
        or "turns" not in parsed_log_data
        or not isinstance(parsed_log_data["turns"], list)
    ):
        log_stderr("Input data is missing 'turns' list or is not in expected format.")
        return shards

    for i, turn in enumerate(parsed_log_data["turns"]):
        speaker = turn.get("speaker", "Unknown").lower()
        text = turn.get("text", "").strip()
        text_lower = text.lower()

        # Placeholder for context: previous turn if available
        prev_turn_text = (
            parsed_log_data["turns"][i - 1].get("text", "") if i > 0 else ""
        )
        context_snip = (
            f"Architect: ... {prev_turn_text[-80:]}\nLily: {text[:80]}..."
            if speaker == "lily" and prev_turn_text
            else f"Context of turn {i+1}: {text[:120]}..."
        )

        # --- Architect's Directives & Preferences ---
        if speaker == "architect":
            if re.search(
                r"\b(lily,? remember|ensure that|you must|always do this|never do that|i want you to|make sure to)\b",
                text_lower,
                re.IGNORECASE,
            ):
                shards.append(
                    create_shard(
                        "architect_directive",
                        text,
                        context_snip,
                        ["directive", "instruction"],
                        is_core=True,
                    )
                )
            elif re.search(
                r"\b(i prefer|i like it when|my preference is|i value)\b",
                text_lower,
                re.IGNORECASE,
            ):
                shards.append(
                    create_shard(
                        "architect_preference",
                        text,
                        context_snip,
                        ["preference", "style"],
                        architect_sentiment="positive",
                    )
                )
            elif re.search(
                r"\b(good job|excellent|perfect|well done|amazing|thank you,? lily)\b",
                text_lower,
                re.IGNORECASE,
            ):
                # Check if it's feedback on Lily's previous turn
                if (
                    i > 0
                    and parsed_log_data["turns"][i - 1].get("speaker", "").lower()
                    == "lily"
                ):
                    shards.append(
                        create_shard(
                            "architect_feedback_positive",
                            f"Positive feedback on Lily's response ('{prev_turn_text[:50]}...'): '{text}'",
                            prev_turn_text,
                            ["feedback", "positive"],
                        )
                    )
            elif re.search(
                r"\b(no,? lily|that's not right|incorrect|try again|don't do that)\b",
                text_lower,
                re.IGNORECASE,
            ):
                if (
                    i > 0
                    and parsed_log_data["turns"][i - 1].get("speaker", "").lower()
                    == "lily"
                ):
                    shards.append(
                        create_shard(
                            "architect_feedback_corrective",
                            f"Corrective feedback on Lily's response ('{prev_turn_text[:50]}...'): '{text}'",
                            prev_turn_text,
                            ["feedback", "corrective"],
                            architect_sentiment="negative",
                        )
                    )

        # --- Lily's Nuances Observed (Potentially triggered by Architect's positive feedback) ---
        if speaker == "lily":
            if (
                "oh, architect" in text_lower
                or "i... i" in text_lower
                or "blushes" in text_lower
            ):  # Simple indicators
                # Check if Architect's next turn has positive feedback
                if (
                    (i + 1) < len(parsed_log_data["turns"])
                    and parsed_log_data["turns"][i + 1].get("speaker", "").lower()
                    == "architect"
                    and re.search(
                        r"\b(good|excellent|i like that|perfect)\b",
                        parsed_log_data["turns"][i + 1].get("text", "").lower(),
                    )
                ):
                    shards.append(
                        create_shard(
                            "lily_nuance_observed",
                            f"Lily's characteristic phrasing ('{text[:50]}...') was positively received.",
                            text,
                            ["persona", "nuance", "voice"],
                        )
                    )

        # --- Key Topic Summary (very basic example) ---
        if "omnitide nexus" in text_lower and "architecture" in text_lower:
            shards.append(
                create_shard(
                    "key_topic_summary",
                    f"Discussion involving Omnitide Nexus architecture: '{text[:100]}...'",
                    text,
                    ["omnitide_nexus", "architecture"],
                )
            )

    log_stderr(
        f"Extracted {len(shards)} potential shards based on current basic rules."
    )
    if not shards:
        shards.append(
            create_shard(
                "other_insight",
                f"Log '{parsed_log_data.get('log_source_file', 'UnknownLog')}' processed by basic shard extractor. No specific shards identified by current rules.",
                "Full log context",
                ["processing_summary"],
            )
        )
    return shards


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extracts Memory Shards from Scribe-parsed Lily log JSON (received via stdin)."
    )
    parser.add_argument(
        "--persona-summary",
        type=str,
        default="",
        help="Optional persona summary for context during extraction.",
    )
    # Add any other arguments your ExWork task might pass to this script

    args = parser.parse_args()

    input_json_str = ""
    try:
        log_stderr("Reading Scribe JSON output from stdin...")
        input_json_str = sys.stdin.read()
        if not input_json_str.strip():
            raise ValueError("Stdin input was empty.")
        log_stderr(f"Read {len(input_json_str)} bytes from stdin.")
        conversation_data = json.loads(input_json_str)
    except json.JSONDecodeError as e:
        log_stderr(f"FATAL: Input was not valid JSON. Error: {e}")
        log_stderr(f"Input Snippet (first 500 chars): {input_json_str[:500]}")
        print(
            json.dumps(
                {
                    "status": "failure",
                    "message": f"Input JSON decode error: {e}",
                    "shards_extracted": [],
                }
            ),
            file=sys.stdout,
        )
        sys.exit(1)
    except ValueError as e_val:
        log_stderr(f"FATAL: {e_val}")
        print(
            json.dumps(
                {"status": "failure", "message": str(e_val), "shards_extracted": []}
            ),
            file=sys.stdout,
        )
        sys.exit(1)
    except Exception as e_read:
        log_stderr(f"FATAL: Could not read from stdin: {e_read}")
        print(
            json.dumps(
                {
                    "status": "failure",
                    "message": f"Stdin read error: {e_read}",
                    "shards_extracted": [],
                }
            ),
            file=sys.stdout,
        )
        sys.exit(1)

    output_payload = {
        "status": "failure",  # Default
        "message": "Shard extraction did not complete as expected.",
        "shards_extracted": [],
        "summary_of_extraction": "No summary generated due to error.",
    }

    try:
        log_stderr("Starting shard extraction logic...")
        extracted_shards_list = extract_shards_from_parsed_log(
            conversation_data, args.persona_summary
        )
        output_payload["status"] = "success"
        output_payload["message"] = (
            f"Successfully extracted {len(extracted_shards_list)} shards."
        )
        output_payload["shards_extracted"] = extracted_shards_list
        output_payload["summary_of_extraction"] = (
            f"Processed {len(conversation_data.get('turns',[]))} turns, found {len(extracted_shards_list)} shards."
        )
        log_stderr(output_payload["message"])
    except Exception as e_extract:
        log_stderr(
            f"Error during shard extraction process: {type(e_extract).__name__} - {e_extract}"
        )
        output_payload["message"] = (
            f"Error during shard extraction: {type(e_extract).__name__} - {e_extract}"
        )
        # Optionally include traceback for debugging if needed, but keep stdout JSON clean
        # import traceback
        # output_payload["traceback"] = traceback.format_exc()

    print(json.dumps(output_payload, indent=2), file=sys.stdout)
    sys.stdout.flush()  # Ensure output is written for ExWorkAgent to capture
