# pac_cli/app/utils/ui_utils.py
from typing import List, Optional, Any, Dict
import subprocess
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.padding import Padding
import logging

logger = logging.getLogger(__name__)
console = Console() # Global console for UI elements from this module

def display_panel(content: str, title: Optional[str] = None, border_style: str = "blue", expand: bool = False, padding_val: Any = (1,2)):
    # ... (rest of this function as previously defined) ...
    try:
        console.print(Panel(content, title=title, border_style=border_style, expand=expand, padding=padding_val))
    except Exception as e:
        logger.error(f"Error displaying panel for title '{title}': {e}")
        console.print(f"[bold red]Error rendering panel content.[/bold red]")

def display_markdown(markdown_text: str, title: Optional[str] = None):
    # ... (rest of this function as previously defined) ...
    md = Markdown(markdown_text)
    if title:
        console.print(Panel(md, title=title, border_style="green", expand=False))
    else:
        console.print(md)

def display_syntax(code: str, language: str, title: Optional[str] = None, line_numbers: bool = True, theme: str = "monokai"):
    # ... (rest of this function as previously defined) ...
    syntax = Syntax(code, language, theme=theme, line_numbers=line_numbers)
    if title:
        console.print(Panel(syntax, title=title, border_style="blue", expand=False)) # expand=False for code typically
    else:
        console.print(syntax)

def display_table(title: str, columns: List[str], rows: List[List[Any]], column_styles: Optional[List[str]] = None):
    # ... (rest of this function as previously defined) ...
    table = Table(title=title, show_header=True, header_style="bold magenta")
    if not column_styles or len(column_styles) != len(columns):
        column_styles = [""] * len(columns) # Default style

    for i, col_name in enumerate(columns):
        table.add_column(col_name, style=column_styles[i])

    for row in rows:
        table.add_row(*(str(item) for item in row))

    console.print(table)

def select_from_list_rich(items: List[str], prompt_message: str, default_choice: Optional[str] = None) -> Optional[str]:
    # ... (rest of this function as previously defined) ...
    if not items:
        return None
    console.print(Padding(prompt_message, (1,0,0,0)))
    for i, item_name in enumerate(items):
        console.print(f"  [cyan]{i+1}[/cyan]. {item_name}")

    while True:
        choice_num_str = IntPrompt.ask(
            "Enter number of your choice (or 0 to cancel)",
            choices=[str(i) for i in range(len(items) + 1)], 
            show_choices=False, 
            default=0 if default_choice is None or default_choice not in items else items.index(default_choice) + 1
        )
        if choice_num_str == 0: 
            return None
        if 1 <= choice_num_str <= len(items):
            return items[choice_num_str - 1]
        console.print("[red]Invalid selection. Please try again.[/red]")

def fzf_select(items: List[str], prompt: str = "Select:", multi: bool = False, fzf_executable: str = "fzf") -> Optional[Union[str, List[str]]]:
    # ... (rest of this function as previously defined) ...
    if not items:
        return [] if multi else None

    items_str = "\n".join(items)
    fzf_command = [fzf_executable, "--prompt", prompt, "--height", "40%", "--layout=reverse", "--border", "--ansi"]
    if multi:
        fzf_command.append("--multi")

    try:
        process = subprocess.run(
            fzf_command,
            input=items_str,
            text=True,
            capture_output=True,
            check=False
        )
        if process.returncode == 0: 
            return process.stdout.strip().splitlines() if multi else process.stdout.strip()
        elif process.returncode == 1: 
            return [] if multi else None
        elif process.returncode == 130: 
            console.print("[yellow]Selection cancelled (ESC).[/yellow]")
            return [] if multi else None
        else: 
            logger.warning(f"fzf exited with unexpected code {process.returncode}. Stderr: {process.stderr.strip()}")
            return [] if multi else None
    except FileNotFoundError:
        logger.error(f"fzf command ('{fzf_executable}') not found. Please install fzf or ensure it's in PATH.")
        if not multi:
             return select_from_list_rich(items, f"(fzf fallback) {prompt}")
        else:
             console.print("[red]fzf not found, cannot perform multi-selection. Try installing fzf.[/red]")
             return [] 
    except Exception as e:
        logger.error(f"Error using fzf: {e}", exc_info=True)
        if not multi:
            return select_from_list_rich(items, f"(fzf error fallback) {prompt}")
        else:
            console.print(f"[red]Error using fzf: {e}. Multi-select unavailable.[/red]")
            return []

def get_user_confirmation(message: str, default_yes: bool = False) -> bool:
    # ... (rest of this function as previously defined) ...
    return Confirm.ask(message, default=default_yes)

def get_text_input(prompt_message: str, default_value: Optional[str] = None, password: bool = False) -> str:
    # ... (rest of this function as previously defined) ...
    if default_value is not None:
        return Prompt.ask(prompt_message, default=default_value, password=password)
    else:
        return Prompt.ask(prompt_message, password=password)

def print_agent_output(agent_name: str, success: bool, output_data: Dict[str, Any], raw_stdout: Optional[str], raw_stderr: Optional[str]):
    title = f"Output from {agent_name}"
    border_color = "green" if success else "red"

    content_parts = [f"[bold {'green' if success else 'red'}]Execution Status: {'SUCCESS' if success else 'FAILURE'}[/bold {'green' if success else 'red'}]"]

    if "error" in output_data:
        content_parts.append(f"[bold red]Error Message:[/bold red] {output_data['error']}")
    if "details" in output_data and output_data["details"] != output_data.get("error"):
        content_parts.append(f"Details: {output_data['details']}")

    if "action_results" in output_data and isinstance(output_data["action_results"], list):
        content_parts.append("\n[bold]Action Results:[/bold]")
        for i, res in enumerate(output_data["action_results"]):
            act_success = res.get('success', False)
            act_type = res.get('action_type', 'UnknownAction')
            act_msg_payload = res.get('message_or_payload', 'N/A')
            if isinstance(act_msg_payload, dict):
                act_msg_payload = f"{{...}} (details in logs or full JSON output)" # Correctly escaped for the outer f-string
            elif isinstance(act_msg_payload, str) and len(act_msg_payload) > 150:
                act_msg_payload = act_msg_payload[:150] + "..."

                    content_parts.append(f"  {i+1}. {act_type}: [{'green' if act_success else 'red'}]Succeeded: {act_success}[/{'green' if act_success else 'red'}] - {act_msg_payload}") # <--- INSERT THE CONSTRUCTED STRING HERE

    elif "steps" in output_data and isinstance(output_data["steps"], list):
        # ... (Scribe steps overview as previously defined) ...
        content_parts.append("\n[bold]Scribe Validation Steps Overview:[/bold]")
        for i, step_res in enumerate(output_data["steps"]):
            step_name = step_res.get('name', 'UnknownStep')
            step_status = step_res.get('status', 'UNKNOWN')
            step_msg_obj = step_res.get('details', {})
            step_msg = step_msg_obj.get('message', step_res.get('error_message', 'No message.')) if isinstance(step_msg_obj, dict) else str(step_msg_obj)
            if len(str(step_msg)) > 100 : step_msg = str(step_msg)[:100] + "..."

            color = "green"
            if step_status == "FAILURE": color = "red"
            elif step_status == "WARNING": color = "yellow"
            elif step_status == "SKIPPED": color = "dim"
            content_parts.append(f"  {i+1}. {step_name}: [{color}]{step_status}[/{color}] - {step_msg}")
        if "overall_status" in output_data:
             content_parts.append(f"\nScribe Overall Status: [bold {'green' if output_data['overall_status'] == 'SUCCESS' else 'red'}]{output_data['overall_status']}[/bold {'green' if output_data['overall_status'] == 'SUCCESS' else 'red'}]")

    elif not success and "error" not in output_data:
         if raw_stderr: content_parts.append(f"\n[bold red]Raw STDERR:[/bold red]\n{raw_stderr}")
         if raw_stdout: content_parts.append(f"\n[bold yellow]Raw STDOUT (on failure):[/bold yellow]\n{raw_stdout}")

    content_parts.append("\n[dim](Full JSON output from agent may contain more details. Check logs if errors occurred.)[/dim]")

    display_panel("\n".join(content_parts), title=title, border_style=border_color)
