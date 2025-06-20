#!/usr/bin/env python3
# lily_log_processor.py
# Version 1.0
# Dedicated standalone script to parse Lily's raw interaction logs into structured JSON.
# Called by pac_cli (via BaseAgentRunner) as part of the LilyCoreMemory processing pipeline.
#
# Architect: Pongtana Alix Feronti
# AI Partner: Lily (for Omnitide Nexus)
# TPC Compliant - Rick & Lily Approved.

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --- Constants ---
APP_NAME = "LilyLogProcessor"
APP_VERSION = "1.0"
LOG_FORMAT = "%(asctime)s [%(name)-18s] [%(levelname)-7s] %(module)s:%(lineno)d - %(message)s (UTC)"
DEFAULT_LOG_LEVEL = "INFO"


# --- Logging Setup ---
def setup_logging(log_level_str: str) -> logging.Logger:
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    logging.Formatter.converter = time.gmtime
    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

    return logging.getLogger(APP_NAME)


logger: Optional[logging.Logger] = None  # Will be initialized in main


# --- Core Parsing Logic ---
def parse_lily_interaction_log(
    input_log_path: Path, output_json_path: Path
) -> Tuple[bool, str, int]:
    """
    Parses a raw Lily interaction log file (text) into a structured JSON file.
    Each turn is identified by speaker prefixes like "Architect:", "Lily:", "Rick:", etc.
    Handles multi-line messages for a single speaker.

    Args:
        input_log_path: Path to the input raw text log file.
        output_json_path: Path to save the output structured JSON data.

    Returns:
        A tuple: (success_bool, message_string, number_of_turns_parsed)
    """
    global logger  # Use the globally initialized logger
    if not logger:  # Should not happen if main calls setup_logging
        print("[LilyLogProcessor_ERROR] Logger not initialized!", file=sys.stderr)
        return False, "Internal error: Logger not initialized", 0

    logger.info(f"Starting parsing of Lily log: {input_log_path}")

    if not input_log_path.is_file():
        msg = f"Input log file not found: {input_log_path}"
        logger.error(msg)
        return False, msg, 0

    turns: List[Dict[str, Any]] = []
    try:
        with open(input_log_path, "r", encoding="utf-8") as f:
            current_speaker: Optional[str] = None
            current_text_lines: List[str] = []
            # Regex to find speaker lines: case-insensitive, allows spaces, captures speaker and first line of text.
            # Recognizes "Architect", "Lily", "Rick", or "Core Team Member <Name>"
            speaker_regex = re.compile(
                r"^\s*(Architect|Lily|Rick|Core Team Member\s+[A-Za-z\s]+)\s*:\s*(.*)",
                re.IGNORECASE,
            )

            for line_num, line_content in enumerate(f, 1):
                match = speaker_regex.match(line_content)
                if match:
                    # If there was previous text, save it for the previous speaker
                    if current_speaker and current_text_lines:
                        turns.append(
                            {
                                "speaker": current_speaker,
                                "timestamp": None,  # Placeholder - implement if logs contain reliable timestamps
                                "text": "".join(current_text_lines).strip(),
                            }
                        )
                        current_text_lines = []

                    # Start new turn
                    captured_speaker_group = match.group(1).strip()
                    # Normalize speaker names for consistency if needed
                    if "Rick".lower() in captured_speaker_group.lower():
                        current_speaker = "Rick"
                    elif "Lily".lower() in captured_speaker_group.lower():
                        current_speaker = "Lily"
                    elif "Architect".lower() in captured_speaker_group.lower():
                        current_speaker = "Architect"
                    # Add more normalizations if needed (e.g. for Core Team Member variations)
                    else:
                        current_speaker = captured_speaker_group  # Use as captured

                    initial_text = match.group(2).strip()
                    if initial_text:
                        current_text_lines.append(initial_text + "\n")
                    elif not initial_text and line_content.strip().endswith(
                        ":"
                    ):  # Speaker line with no immediate text
                        pass  # Will append subsequent lines
                    else:  # Speaker line with no text after colon, and no text on next line yet
                        current_text_lines.append(
                            "\n"
                        )  # Represents an empty start to a turn

                elif (
                    current_speaker
                ):  # Line doesn't start with a new speaker, so it's a continuation
                    current_text_lines.append(
                        line_content
                    )  # Preserve original newlines

            # Add the last speaker's text if any
            if current_speaker and current_text_lines:
                turns.append(
                    {
                        "speaker": current_speaker,
                        "timestamp": None,
                        "text": "".join(current_text_lines).strip(),
                    }
                )

        # Prepare output JSON structure
        output_data = {
            "log_source_filename": str(input_log_path.name),
            "parsing_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "parser_app_name": APP_NAME,
            "parser_app_version": APP_VERSION,
            "parsed_turn_count": len(turns),
            "turns": turns,
        }

        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f_out:
            json.dump(output_data, f_out, indent=2)

        msg = f"Successfully parsed {len(turns)} turns from '{input_log_path.name}' into '{output_json_path.name}'."
        logger.info(msg)
        return True, msg, len(turns)

    except FileNotFoundError:  # Should be caught by initial check, but good practice
        msg = f"Input log file not found during parsing attempt: {input_log_path}"
        logger.error(msg)
        return False, msg, 0
    except Exception as e:
        msg = f"Critical error parsing log file '{input_log_path.name}': {type(e).__name__} - {e}"
        logger.error(msg, exc_info=True)
        return False, msg, 0


# --- Main Execution ---
def main():
    global logger  # Allow main to assign to global logger

    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} v{APP_VERSION} - Parses Lily interaction logs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input-log-file",
        type=Path,
        required=True,
        help="Absolute path to the raw Lily interaction log text file.",
    )
    parser.add_argument(
        "--output-structured-log-file",
        type=Path,
        required=True,
        help="Absolute path where the structured JSON output of log parsing should be saved.",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=DEFAULT_LOG_LEVEL,
        help="Set the verbosity level for console logging (to stderr).",
    )
    # Add '--ner-task-definition' if this script needs to load specific rules from NER
    # For now, parsing rules are embedded or can be simple regex.

    args = parser.parse_args()
    logger = setup_logging(args.log_level)  # Initialize global logger

    logger.info(f"--- {APP_NAME} v{APP_VERSION} Execution Started ---")
    logger.debug(f"Command-line arguments: {args}")

    success, message, turns_parsed = parse_lily_interaction_log(
        args.input_log_file.resolve(),  # Ensure paths are absolute
        args.output_structured_log_file.resolve(),
    )

    # CRITICAL: Output JSON payload to STDOUT for BaseAgentRunner in pac_cli
    stdout_payload = {
        "status": "success" if success else "failure",
        "message": message,
        # This is the key piece of information pac_cli needs from this script's stdout
        "parsed_log_output_path": (
            str(args.output_structured_log_file.resolve()) if success else None
        ),
        "parsed_turn_count": turns_parsed,
    }
    print(json.dumps(stdout_payload, indent=2))  # Output to stdout

    logger.info(
        f"--- {APP_NAME} Execution Ended. Status: {stdout_payload['status']} ---"
    )
    logging.shutdown()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
