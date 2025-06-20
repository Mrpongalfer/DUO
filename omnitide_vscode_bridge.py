#!/usr/bin/env python3
import json
import requests
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


console = Console()
url = "http://localhost:5000/execute"


def send_command(command_type, payload):
    data = {"command_type": command_type, "payload": payload}
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        console.print(
            Panel(
                json.dumps(response.json(), indent=2),
                title="Nexus Response",
                box=box.ROUNDED,
                style="green",
            )
        )
    except requests.RequestException as e:
        console.print(f"[red]Request failed: {e}[/red]")
        if hasattr(e, "response") and e.response is not None:
            console.print(f"[yellow]Response: {e.response.text}[/yellow]")


def main_menu():
    while True:
        console.print(
            Panel(
                "[bold cyan]Omnitide VSCode Bridge[/bold cyan]",
                subtitle="AI Assistant Menu",
                box=box.DOUBLE,
            )
        )
        console.print("[bold]1.[/bold] Generate Code")
        console.print("[bold]2.[/bold] Manage Project")
        console.print("[bold]3.[/bold] Exit")
        choice = Prompt.ask("Select an option", choices=["1", "2", "3"], default="1")
        if choice == "1":
            desc = Prompt.ask("Enter a high-level description for code generation")
            send_command("generate_code", desc)
        elif choice == "2":
            console.print(Panel("Future Nexus management options...", style="magenta"))
        elif choice == "3":
            console.print("[bold green]Goodbye![/bold green]")
            break


if __name__ == "__main__":
    main_menu()
