#!/usr/bin/env python3
"""
orchestrator_menu.py
Bleeding-edge, AI-augmented TUI/CLI orchestration menu for dev environment
- Launches tools, agents, CI/CD, backup, and more
- Extensible: add more actions as needed
"""
import os
import subprocess
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

console = Console()

def main_menu():
    while True:
        table = Table(title="Dev Orchestration Menu", show_lines=True)
        table.add_column("Option", style="bold cyan")
        table.add_column("Action", style="bold magenta")
        table.add_row("1", "Open VS Code")
        table.add_row("2", "Start xonsh shell")
        table.add_row("3", "Launch tmux session")
        table.add_row("4", "Start Ollama AI agent")
        table.add_row("5", "Start Syncthing backup")
        table.add_row("6", "Start Docker services")
        table.add_row("7", "CI/CD runner status")
        table.add_row("8", "Exit")
        console.print(table)
        choice = Prompt.ask("Select option", choices=[str(i) for i in range(1,9)])
        if choice == "1":
            subprocess.Popen(["code"])
        elif choice == "2":
            os.system("xonsh")
        elif choice == "3":
            os.system("tmux new -A -s dev")
        elif choice == "4":
            os.system("ollama serve & ollama run gemma:2b")
        elif choice == "5":
            os.system("syncthing &")
        elif choice == "6":
            os.system("docker-compose up -d || docker compose up -d")
        elif choice == "7":
            os.system("systemctl status actions.runner* || echo 'Runner not installed.'")
        elif choice == "8":
            console.print("[bold green]Goodbye![/bold green]")
            break

if __name__ == "__main__":
    main_menu()
