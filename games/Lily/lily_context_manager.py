#!/usr/bin/env python3
# lily_context_manager.py
# Helps Architect assemble context for Lily and create structured interaction snapshots.
# TPC Compliant - Rick & Lily Approved.

import datetime
import sys
from pathlib import Path

# --- Configuration ---
# LilyCoreMemory path resolution:
import os

LILY_CORE_MEMORY_PATH = None
DEFAULT_LCM_PATH_STR = os.environ.get("LILY_CORE_MEMORY_PATH", "./Lily/LilyCoreMemory")


# --- Color Codes for Terminal Output (Basic) ---
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    ENDC = "\033[0m"


def print_color(text, color):
    # Basic color printing, consider 'rich' or 'colorama' for more robust cross-platform coloring
    # For simplicity, using ANSI escape codes directly.
    if sys.stdout.isatty():  # Only use colors if output is a TTY
        print(f"{color}{text}{Colors.ENDC}")
    else:
        print(text)


def get_lcm_path():
    """Gets the LilyCoreMemory path from the user or uses default."""
    user_path_str = input(f"Enter LilyCoreMemory base path [{DEFAULT_LCM_PATH_STR}]: ")
    path_str = user_path_str if user_path_str else DEFAULT_LCM_PATH_STR
    lcm_path = Path(path_str).resolve()
    if not lcm_path.is_dir():
        print_color(
            f"ERROR: Path '{lcm_path}' does not exist or is not a directory. Please create it first (e.g., using initialize_lily_core_memory.sh).",
            Colors.RED,
        )
        sys.exit(1)
    return lcm_path


LILY_CORE_MEMORY_PATH = None  # Will be set by get_lcm_path()

# --- Core Files and Directories ---
# These will be dynamically set based on LILY_CORE_MEMORY_PATH
PERSONA_FOUNDATION_MD = "00_Persona_Foundation.md"
INTERACTION_PRINCIPLES_MD = "01_InteractionPrinciples_Baseline.md"
KEY_DIRECTIVES_DIR = "KeyDirectives"
SNAPSHOTS_DIR = "InteractionLog_ContextualSnapshots"
SCRIPTS_DIR = "Scripts"  # For this script itself, or others

# --- Functions ---


def assemble_lily_context(lcm_path: Path, include_snapshots: int = 0) -> str:
    """
    Assembles the core context for Lily from the Persona Foundation,
    Key Directives, and optionally, recent snapshots.
    """
    print_color("\n🌿 Assembling Lily's Core Context...", Colors.BLUE)
    context_parts = []

    # 1. Persona Foundation
    persona_file = lcm_path / PERSONA_FOUNDATION_MD
    if persona_file.is_file():
        print_color(f"   Loading: {PERSONA_FOUNDATION_MD}", Colors.YELLOW)
        context_parts.append(
            f"--- START: {PERSONA_FOUNDATION_MD} ---\n{persona_file.read_text(encoding='utf-8')}\n--- END: {PERSONA_FOUNDATION_MD} ---"
        )
    else:
        print_color(f"   WARNING: {PERSONA_FOUNDATION_MD} not found.", Colors.RED)

    # 2. Interaction Principles
    principles_file = lcm_path / INTERACTION_PRINCIPLES_MD
    if principles_file.is_file():
        print_color(f"   Loading: {INTERACTION_PRINCIPLES_MD}", Colors.YELLOW)
        context_parts.append(
            f"--- START: {INTERACTION_PRINCIPLES_MD} ---\n{principles_file.read_text(encoding='utf-8')}\n--- END: {INTERACTION_PRINCIPLES_MD} ---"
        )
    else:
        print_color(f"   WARNING: {INTERACTION_PRINCIPLES_MD} not found.", Colors.RED)

    # 3. Key Directives
    directives_path = lcm_path / KEY_DIRECTIVES_DIR
    if directives_path.is_dir():
        print_color(
            f"   Loading Key Directives from: {KEY_DIRECTIVES_DIR}/", Colors.YELLOW
        )
        for directive_file in sorted(directives_path.glob("*.md")):
            print_color(f"     - {directive_file.name}", Colors.YELLOW)
            context_parts.append(
                f"--- START DIRECTIVE: {directive_file.name} ---\n{directive_file.read_text(encoding='utf-8')}\n--- END DIRECTIVE: {directive_file.name} ---"
            )

    # 4. Optional: Recent Snapshots
    if include_snapshots > 0:
        snapshots_path = lcm_path / SNAPSHOTS_DIR
        if snapshots_path.is_dir():
            print_color(
                f"   Loading last {include_snapshots} Interaction Snapshot(s) from: {SNAPSHOTS_DIR}/",
                Colors.YELLOW,
            )
            # Get all markdown files, sort by name (hoping timestamp in name makes it chronological)
            # A more robust way would be to parse timestamp from name or use file mtime.
            all_snapshots = sorted(snapshots_path.glob("snapshot_*.md"), reverse=True)
            for snapshot_file in all_snapshots[:include_snapshots]:
                print_color(f"     - {snapshot_file.name}", Colors.YELLOW)
                context_parts.append(
                    f"--- START SNAPSHOT: {snapshot_file.name} ---\n{snapshot_file.read_text(encoding='utf-8')}\n--- END SNAPSHOT: {snapshot_file.name} ---"
                )
        else:
            print_color(
                f"   WARNING: Snapshots directory '{SNAPSHOTS_DIR}' not found.",
                Colors.RED,
            )

    full_context = "\n\n".join(context_parts)

    # Save to a temporary file for easy copy-pasting by Architect
    context_file_path = lcm_path / SCRIPTS_DIR / "lily_current_context.txt"
    try:
        context_file_path.parent.mkdir(parents=True, exist_ok=True)
        context_file_path.write_text(full_context, encoding="utf-8")
        print_color(
            f"\n✅ Full context assembled and saved to: {context_file_path}",
            Colors.GREEN,
        )
        print_color(
            "   You can now copy the content of this file to provide context to Lily.",
            Colors.GREEN,
        )
    except Exception as e:
        print_color(f"   ERROR saving context to file: {e}", Colors.RED)

    return full_context


def create_interaction_snapshot(lcm_path: Path):
    """
    Guides the Architect to create a new structured interaction snapshot.
    """
    print_color("\n📝 Creating New Interaction Snapshot...", Colors.BLUE)
    snapshots_path = lcm_path / SNAPSHOTS_DIR
    snapshots_path.mkdir(parents=True, exist_ok=True)

    now = datetime.datetime.now()
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")

    print_color("Please provide details for this snapshot:", Colors.YELLOW)

    session_title = input(
        "   Session Title/Brief Description (e.g., Ansible_GitOps_Planning): "
    )
    filename_suggestion = (
        f"snapshot_{timestamp_str}_{session_title.replace(' ', '_').lower()}.md"
    )

    key_topics = input("   Key Topics Discussed (comma-separated): ")
    new_directives = input("   New Directives/Preferences given to Lily (or 'none'): ")
    notable_lily_good = input(
        "   Notable Lily Responses (Good - brief quote/summary or 'none'): "
    )
    notable_lily_improvement = input(
        "   Lily Responses needing Improvement (brief quote/summary or 'none'): "
    )
    architect_reflections = input(
        "   Architect's Reflections/Notes for Lily's Evolution: "
    )

    snapshot_content = f"""---
title: "{session_title if session_title else 'Interaction Snapshot'}"
date: "{now.isoformat()}"
tags: [{', '.join(f'"{t.strip()}"' for t in key_topics.split(',') if t.strip()) if key_topics else ''}] 
---

# Interaction Snapshot: {session_title if session_title else timestamp_str}

**Date:** {now.strftime("%Y-%m-%d %H:%M:%S")}

## Key Topics Discussed:
- {key_topics if key_topics else "N/A"}

## New Directives or Preferences Given to Lily:
- {new_directives if new_directives else "None"}

## Notable Lily Responses (Positive):
- {notable_lily_good if notable_lily_good else "None"}

## Lily Responses Identified for Improvement:
- {notable_lily_improvement if notable_lily_improvement else "None"}

## Architect's Reflections & Notes for Lily's Evolution:
{architect_reflections if architect_reflections else "N/A"}

---
*This snapshot helps Lily remember and grow from our interactions.*
"""
    snapshot_filename = input(
        f"   Enter filename for snapshot [{filename_suggestion}]: "
    )
    snapshot_filename = snapshot_filename if snapshot_filename else filename_suggestion

    snapshot_file_path = snapshots_path / snapshot_filename
    try:
        snapshot_file_path.write_text(snapshot_content, encoding="utf-8")
        print_color(
            f"\n✅ Snapshot created successfully: {snapshot_file_path}", Colors.GREEN
        )
        print_color(
            f"   Remember to 'git add {snapshot_file_path}' and commit it!",
            Colors.YELLOW,
        )
    except Exception as e:
        print_color(f"   ERROR saving snapshot: {e}", Colors.RED)


def main_menu():
    """Displays the main menu and handles user choices."""
    global LILY_CORE_MEMORY_PATH  # Allow modification of global
    LILY_CORE_MEMORY_PATH = get_lcm_path()  # Initialize path at start

    while True:
        print_color("\n--- Lily Context Manager ---", Colors.BLUE)
        print("1. Assemble Lily's Core Context (for new session)")
        print("2. Create New Interaction Snapshot")
        print("3. Change LilyCoreMemory Path")
        print("0. Exit")
        choice = input("Enter your choice: ")

        if choice == "1":
            try:
                num_snapshots_str = input(
                    "   Include how many recent snapshots in context (e.g., 0, 1, 3) [0]: "
                )
                num_snapshots = (
                    int(num_snapshots_str) if num_snapshots_str.isdigit() else 0
                )
                assemble_lily_context(LILY_CORE_MEMORY_PATH, num_snapshots)
            except Exception as e:
                print_color(f"Error during context assembly: {e}", Colors.RED)
        elif choice == "2":
            try:
                create_interaction_snapshot(LILY_CORE_MEMORY_PATH)
            except Exception as e:
                print_color(f"Error during snapshot creation: {e}", Colors.RED)
        elif choice == "3":
            LILY_CORE_MEMORY_PATH = get_lcm_path()  # Allow user to change path
            print_color(
                f"LilyCoreMemory path updated to: {LILY_CORE_MEMORY_PATH}", Colors.GREEN
            )
        elif choice == "0":
            print_color(
                "Exiting Lily Context Manager. Stay creative, Architect!", Colors.GREEN
            )
            break
        else:
            print_color("Invalid choice. Please try again.", Colors.RED)
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    if (
        not LILY_CORE_MEMORY_PATH
    ):  # Ensure it's set before menu, if script is run directly
        # This direct call might be redundant if main_menu always calls get_lcm_path first.
        # However, good for safety if other functions were to be called directly.
        try:
            # Attempt to get path without user input if possible for non-interactive use later
            # For now, interactive is fine.
            pass
        except Exception:
            # Suppress error if path is not found non-interactively, main_menu will handle.
            pass
    main_menu()
