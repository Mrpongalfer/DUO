# ner-monorepo/my_devsuite_project/NPTPAC/pac_cli/app/commands/ner_cmds.py
import logging

# ... other imports needed for NER commands ...
from pathlib import Path
from typing import Optional

import typer

# Core NPTPAC imports
try:
    from ..games.nexus_omniengine_v3.core.agent_runner import ExWorkAgentRunner, ScribeAgentRunner
    from ..games.nexus_omniengine_v3.core.config_manager import ConfigManager
    from ..games.nexus_omniengine_v3.core.ner_handler import NERHandler
    from ..utils import ui_utils
except (ImportError, SystemError, ValueError):
    # Fallback for direct script/module execution
    from games.nexus_omniengine_v3.core.ner_handler import NERHandler
    from utils import ui_utils

ner_app = typer.Typer(
    name="ner",
    help="Interact with the Nexus Edict Repository (NER).",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)


@ner_app.command("browse", help="Interactively browse NER categories and items.")
def ner_browse_cmd(
    ctx: typer.Context,
    start_category: Optional[str] = typer.Argument(
        None,
        help="NER category to start Browse from (e.g., '00_CORE_EDICTS').",
        show_default=False,
    ),
    search_query: Optional[str] = typer.Option(
        None,
        "--search",
        "-s",
        help="Search NER filenames and content (basic search).",
        show_default=False,
    ),
):
    """Interactively browse or search the NER."""
    current_ner_handler: NERHandler = ctx.meta[
        "ner_handler"
    ]  # Assumes main_callback populated it

    if search_query:
        ui_utils.console.print(f"Searching NER for: '[cyan]{search_query}[/cyan]'...")
        # TODO, Architect: Allow user to specify if search is recursive, case-sensitive, etc.
        results = current_ner_handler.search_ner(
            search_query, search_in_category=start_category
        )
        if not results:
            ui_utils.console.print(
                f"No results found in NER for '{search_query}' {f'within category {start_category}' if start_category else ''}."
            )
            return

        table_rows = [
            [
                res["relative_path_to_ner"],
                res["type"],
                res.get("match_type", ""),
                res.get("snippet", "")[:80] + "...",
            ]
            for res in results
        ]
        ui_utils.display_table(
            f"Search Results for '{search_query}'",
            ["Path in NER", "Type", "Match", "Snippet"],
            table_rows,
        )
        # TODO, Architect: Allow selecting a search result to view its full content.
        return

    # --- Interactive Browse Logic (Simplified Conceptual Version) ---
    # TODO, Architect: Implement a full, rich interactive browser using ui_utils.fzf_select
    #                  or a Textual-based file browser component within PAC.
    #                  The version below is a very basic placeholder.
    current_path_in_ner = (
        Path(start_category) if start_category else Path(".")
    )  # Relative to NER root

    while True:
        abs_ner_path_to_list = (
            current_ner_handler.ner_root / current_path_in_ner
        ).resolve()
        ui_utils.console.rule(
            f"[bold blue]NER Browser: {abs_ner_path_to_list.relative_to(current_ner_handler.ner_root)}[/bold blue]"
        )

        items_in_dir = current_ner_handler.list_items_in_category(
            str(current_path_in_ner)
        )
        if not items_in_dir:
            ui_utils.console.print(
                "[yellow]This NER directory is empty or invalid.[/yellow]"
            )

        display_items = []
        if current_path_in_ner != Path("."):  # Allow going up if not at NER root
            display_items.append(
                {
                    "name": "[.. Up one level ..]",
                    "type": "action_up",
                    "relative_path_to_ner": str(current_path_in_ner.parent),
                }
            )

        display_items.extend(
            sorted(
                [item for item in items_in_dir if item["type"] == "directory"],
                key=lambda x: x["name"],
            )
        )
        display_items.extend(
            sorted(
                [item for item in items_in_dir if item["type"] == "file"],
                key=lambda x: x["name"],
            )
        )

        if not display_items and current_path_in_ner == Path("."):
            ui_utils.console.print(
                f"[yellow]NER at '{current_ner_handler.ner_root}' appears empty.[/yellow]"
            )
            break  # Exit browser if NER root is empty

        choices = [
            f"{item['name']}{'/' if item['type'] == 'directory' else ''}"
            for item in display_items
        ]
        choices.append("[Exit Browser]")

        selected_choice_str = ui_utils.fzf_select(
            choices,
            prompt=f"Browse {current_path_in_ner.name if current_path_in_ner.name else 'NER Root'}: ",
        )

        if not selected_choice_str or selected_choice_str == "[Exit Browser]":
            break

        selected_idx = -1
        for i, choice_text in enumerate(choices):  # Find index from selected string
            if choice_text == selected_choice_str:
                selected_idx = i
                break

        if selected_idx == -1:
            continue  # Should not happen with fzf

        selected_item_data = display_items[selected_idx]

        if selected_item_data["type"] == "action_up":
            current_path_in_ner = Path(selected_item_data["relative_path_to_ner"])
        elif selected_item_data["type"] == "directory":
            current_path_in_ner = Path(selected_item_data["relative_path_to_ner"])
        elif selected_item_data["type"] == "file":
            content = current_ner_handler.get_item_content(
                selected_item_data["relative_path_to_ner"]
            )
            if content:
                # Determine lexer for syntax highlighting
                file_ext = (
                    Path(selected_item_data["name"]).suffix[1:].lower()
                    if Path(selected_item_data["name"]).suffix
                    else "text"
                )
                if file_ext == "md":
                    ui_utils.display_markdown(content, title=selected_item_data["name"])
                elif file_ext in ["json", "toml", "yaml", "py", "sh"]:
                    ui_utils.display_syntax(
                        content, file_ext, title=selected_item_data["name"]
                    )
                else:
                    ui_utils.display_panel(content, title=selected_item_data["name"])
                typer.prompt(
                    "Press Enter to continue Browse...", default="", show_default=False
                )  # Pause
            else:
                ui_utils.console.print(
                    f"[red]Could not retrieve content for {selected_item_data['name']}.[/red]"
                )


try:
    logger = logging.getLogger("PAC.NERCmds")
except Exception:
    import logging as _logging

    logger = _logging.getLogger("PAC.NERCmds")
logger.info("Exited NER browser.")


@ner_app.command("view", help="View a specific NER item's content.")
def ner_view_cmd(
    ctx: typer.Context,
    item_path_relative_to_ner: str = typer.Argument(
        ...,
        help="Relative path to the NER item (e.g., '00_CORE_EDICTS/01_architect_supremacy.md').",
    ),
):
    """Displays the content of a specific file within NER"""
    current_ner_handler: NERHandler = ctx.meta["ner_handler"]
    content = current_ner_handler.get_item_content(item_path_relative_to_ner)
    if content:
        file_ext = (
            Path(item_path_relative_to_ner).suffix[1:].lower()
            if Path(item_path_relative_to_ner).suffix
            else "text"
        )
        title = Path(item_path_relative_to_ner).name
        if file_ext == "md":
            ui_utils.display_markdown(content, title=title)
        elif file_ext in ["json", "toml", "yaml", "py", "sh"]:
            ui_utils.display_syntax(content, file_ext, title=title)
        else:
            ui_utils.display_panel(content, title=title)
    else:
        ui_utils.console.print(
            f"[red]NER item not found or could not be read: {item_path_relative_to_ner}[/red]"
        )
        raise typer.Exit(code=1)


@ner_app.command(
    "git",
    help="Perform Git operations (status, commit, pull, push) on the NER repository.",
)
def ner_git_cmd(
    ctx: typer.Context,
    action: str = typer.Argument(
        ..., help="Git action: 'status', 'pull', 'push', or 'commit'."
    ),
    commit_message: Optional[str] = typer.Option(
        None, "-m", "--message", help="Commit message (required for 'commit' action)."
    ),
    add_all_first: bool = typer.Option(
        True,
        "--add-all/--no-add-all",
        help="Run 'git add .' before commit (default: True).",
    ),
):
    """Manages the NER Git repository."""
    current_ner_handler: NERHandler = ctx.meta["ner_handler"]
    action = action.lower()

    if not (current_ner_handler.ner_root / ".git").is_dir():
        ui_utils.console.print(
            f"[yellow]NER directory at '{current_ner_handler.ner_root}' is not a Git repository.[/yellow]"
        )
        ui_utils.console.print(
            "Initialize it first (e.g., via bootstrap or 'git init' then add remote)."
        )
        return

    success: bool = False
    output_message: str = "Action not performed."

    if action == "status":
        # TODO, Architect: Use ner_handler for a more structured git status, or parse output better.
        # For now, simple subprocess call.
        # This command should be run using a generic method in NERHandler or a new utility
        status_success, stdout, stderr = ui_utils.run_command(
            ["git", "status"], cwd=current_ner_handler.ner_root, capture=True
        )  # This ui_utils.run_command is conceptual
        if status_success:
            ui_utils.console.print(
                Panel(
                    stdout if stdout else "No status output.",
                    title="NER Git Status",
                    border_style="cyan",
                )
            )
        else:
            ui_utils.console.print(
                Panel(
                    f"Error getting status:\nSTDERR: {stderr}\nSTDOUT: {stdout}",
                    title="NER Git Status Error",
                    border_style="red",
                )
            )
        return  # Status is display-only

    elif action == "pull":
        success, output_message = current_ner_handler.git_pull_ner()
    elif action == "push":
        success, output_message = current_ner_handler.git_push_ner()
    elif action == "commit":
        if not commit_message:
            ui_utils.console.print(
                "[red]Commit message is required for 'git commit' action. Use -m 'Your message'.[/red]"
            )
            raise typer.Exit(code=1)
        success, output_message = current_ner_handler.git_commit_ner_changes(
            commit_message, add_all=add_all_first
        )
    else:
        ui_utils.console.print(
            f"[red]Unknown NER Git action: '{action}'. Valid actions: status, pull, push, commit.[/red]"
        )
        raise typer.Exit(code=1)

    if success:
        ui_utils.console.print(
            f"[green]NER Git '{action}' operation successful.[/green]"
        )
        if output_message:
            ui_utils.console.print(output_message)
    else:
        ui_utils.console.print(f"[red]NER Git '{action}' operation failed:[/red]")
        if output_message:
            ui_utils.console.print(output_message)
        raise typer.Exit(code=1)


# TODO, Architect: Add more NER commands:
# - ner create [--type <edict|template|profile...>] <relative_path_in_ner> [--editor]
# - ner edit <relative_path_in_ner> [--editor]
# - ner delete <relative_path_in_ner> [--force]
# - ner validate <template_path> --type <exwork|scribe|onap_part> (needs schemas)
