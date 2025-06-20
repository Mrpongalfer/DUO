#!/usr/bin/env python3
import json
import os

import docker
import requests
from rich.prompt import Prompt
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import set_key
import requests as pyrequests

console = Console()
API_URL = "http://localhost:5000/execute"
LLM_ENV_PATH = os.path.join(os.getcwd(), ".env")


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def dispatch_command(command_type, payload=None):
    data = {"command_type": command_type, "payload": payload}
    try:
        response = requests.post(API_URL, json=data, timeout=10)
        response.raise_for_status()
        resp_json = response.json()
        console.print(
            Panel(
                json.dumps(resp_json, indent=2),
                title="Nexus Response",
                box=box.ROUNDED,
                style="green",
            )
        )
    except requests.ConnectionError:
        console.print(
            Panel(
                "[red]Could not connect to Omnitide Nexus backend!\nEnsure Omnitide Nexus Docker container is running![/red]",
                title="Connection Error",
                style="red",
            )
        )
    except requests.Timeout:
        console.print(
            Panel(
                "[red]Request to Nexus timed out![/red]", title="Timeout", style="red"
            )
        )
    except requests.RequestException as e:
        msg = getattr(e.response, "text", str(e))
        console.print(
            Panel(f"[red]Nexus API error: {msg}[/red]", title="API Error", style="red")
        )
    except Exception as e:
        console.print(
            Panel(f"[red]Unexpected error: {e}[/red]", title="Error", style="red")
        )


def manage_environment_menu():
    client = docker.from_env()
    while True:
        clear_screen()
        console.print(
            Panel(
                "[bold yellow]Manage Environment[/bold yellow]",
                subtitle="Nexus Backend & Docker Control",
                box=box.DOUBLE,
            )
        )
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_row("[bold green][1][/bold green] Start/Ensure Nexus Backend")
        table.add_row("[bold red][2][/bold red] Stop Nexus Backend")
        table.add_row("[bold yellow][3][/bold yellow] Restart Nexus Backend")
        table.add_row("[bold cyan][4][/bold cyan] Check Nexus Status")
        table.add_row("[bold magenta][5][/bold magenta] Provision New Environment")
        table.add_row("[bold][6][/bold] Back to Main Menu")
        table.add_row("[bold red][7][/bold red] Troubleshoot Nexus Backend")
        console.print(table)
        choice = Prompt.ask(
            "Select an option",
            choices=["1", "2", "3", "4", "5", "6", "7"],
            default="1",
        )
        if choice == "1":
            # Start/Ensure Nexus Backend (reuse logic from start_nexus.py)
            import subprocess
            from pathlib import Path

            CONTAINER_NAME = "omnitide_nexus_instance"
            IMAGE_NAME = "omnitide-nexus-agent"
            DOCKERFILE_PATH = str(Path(os.getcwd()) / "Dockerfile")
            HOST_PORT = "5000"
            CONTAINER_PORT = "5000"
            CODEBASE_PATH = os.path.abspath(os.getcwd())

            def run(cmd):
                try:
                    result = subprocess.run(
                        cmd, shell=True, check=True, capture_output=True, text=True
                    )
                    return result.stdout.strip()
                except subprocess.CalledProcessError as e:
                    console.print(
                        Panel(
                            f"[red]Command failed: {e}\n{e.stdout}\n{e.stderr}[/red]",
                            title="Docker Error",
                            style="red",
                        )
                    )
                    return None

            def image_exists():
                images = client.images.list(name=IMAGE_NAME)
                return bool(images)

            def container_exists():
                try:
                    client.containers.get(CONTAINER_NAME)
                    return True
                except docker.errors.NotFound:
                    return False

            def container_running():
                try:
                    c = client.containers.get(CONTAINER_NAME)
                    return c.status == "running"
                except docker.errors.NotFound:
                    return False

            if not image_exists():
                console.print("[yellow]Building Docker image...[/yellow]")
                try:
                    client.images.build(
                        path=CODEBASE_PATH,
                        dockerfile=DOCKERFILE_PATH,
                        tag=IMAGE_NAME,
                    )
                    console.print("[green]Image built successfully.[/green]")
                except Exception as e:
                    console.print(
                        Panel(
                            f"[red]Image build failed: {e}[/red]",
                            title="Docker Error",
                            style="red",
                        )
                    )
                    Prompt.ask("Press Enter to return to menu")
                    continue
            if not container_exists():
                console.print("[yellow]Starting new Nexus container...[/yellow]")
                try:
                    client.containers.run(
                        IMAGE_NAME,
                        detach=True,
                        name=CONTAINER_NAME,
                        ports={f"{CONTAINER_PORT}/tcp": int(HOST_PORT)},
                        volumes={
                            CODEBASE_PATH: {"bind": "/app/codebase", "mode": "rw"}
                        },
                        environment={
                            "OLLAMA_HOST": "http://host.docker.internal:11434",
                            "OLLAMA_MODEL": "llama3",
                        },
                        restart_policy={"Name": "unless-stopped"},
                    )
                    console.print("[green]Nexus backend started![/green]")
                except Exception as e:
                    console.print(
                        Panel(
                            f"[red]Container start failed: {e}[/red]",
                            title="Docker Error",
                            style="red",
                        )
                    )
            elif not container_running():
                console.print(
                    "[yellow]Container exists but is not running. Starting..."
                )
                try:
                    c = client.containers.get(CONTAINER_NAME)
                    c.start()
                    console.print("[green]Container started.[/green]")
                except Exception as e:
                    console.print(
                        Panel(
                            f"[red]Container start failed: {e}[/red]",
                            title="Docker Error",
                            style="red",
                        )
                    )
            else:
                console.print("[green]Container is already running.[/green]")
            Prompt.ask("Press Enter to return to menu")
        elif choice == "2":
            # Stop Nexus Backend
            try:
                c = client.containers.get("omnitide_nexus_instance")
                c.stop()
                console.print("[green]Nexus backend stopped.[/green]")
            except docker.errors.NotFound:
                console.print("[yellow]Container not found.[/yellow]")
            except Exception as e:
                console.print(
                    Panel(
                        f"[red]Stop failed: {e}[/red]",
                        title="Docker Error",
                        style="red",
                    )
                )
            Prompt.ask("Press Enter to return to menu")
        elif choice == "3":
            # Restart Nexus Backend
            try:
                c = client.containers.get("omnitide_nexus_instance")
                c.restart()
                console.print("[green]Nexus backend restarted.[/green]")
            except docker.errors.NotFound:
                console.print("[yellow]Container not found.[/yellow]")
            except Exception as e:
                console.print(
                    Panel(
                        f"[red]Restart failed: {e}[/red]",
                        title="Docker Error",
                        style="red",
                    )
                )
            Prompt.ask("Press Enter to return to menu")
        elif choice == "4":
            # Check Nexus Status
            try:
                containers = client.containers.list(
                    all=True, filters={"name": "omnitide_nexus_instance"}
                )
                if containers:
                    c = containers[0]
                    status = c.status
                    console.print(
                        Panel(
                            f"[cyan]Container status: {status}[/cyan]",
                            title="Nexus Status",
                            style="cyan",
                        )
                    )
                else:
                    console.print(
                        Panel(
                            "[yellow]Container not found.[/yellow]",
                            title="Nexus Status",
                            style="yellow",
                        )
                    )
            except Exception as e:
                console.print(
                    Panel(
                        f"[red]Status check failed: {e}[/red]",
                        title="Docker Error",
                        style="red",
                    )
                )
            Prompt.ask("Press Enter to return to menu")
        elif choice == "5":
            console.print(
                Panel(
                    "Future: Generate Docker Compose for microservice...",
                    style="magenta",
                )
            )
            Prompt.ask("Press Enter to return to menu")
        elif choice == "6":
            break
        elif choice == "7":
            # Troubleshoot Nexus Backend
            try:
                containers = client.containers.list(
                    all=True, filters={"name": CONTAINER_NAME}
                )
                if not containers:
                    console.print("[yellow]No Nexus container found.[/yellow]")
                else:
                    c = containers[0]
                    status = c.status
                    console.print(
                        Panel(
                            f"[cyan]Container status: {status}[/cyan]",
                            title="Nexus Status",
                            style="cyan",
                        )
                    )
                    if status == "restarting":
                        console.print("[red]Container is stuck restarting![/red]")
                        logs = c.logs(tail=20).decode(errors="ignore")
                        console.print(
                            Panel(
                                f"Last 20 log lines:\n{logs}",
                                title="Container Logs",
                                style="yellow",
                            )
                        )
                        fix = Prompt.ask(
                            "Do you want to remove and recreate the container? [y/N]",
                            choices=["y", "Y", "n", "N"],
                            default="N",
                        )
                        if fix.lower() == "y":
                            c.remove(force=True)
                            console.print(
                                "[green]Container removed. Please try starting again from the menu.[/green]"
                            )
                    elif status == "exited":
                        console.print(
                            "[yellow]Container is exited. Check logs above and try restarting or recreating."
                        )
                        logs = c.logs(tail=20).decode(errors="ignore")
                        console.print(
                            Panel(
                                f"Last 20 log lines:\n{logs}",
                                title="Container Logs",
                                style="yellow",
                            )
                        )
                    elif status == "running":
                        console.print("[green]Container is running normally.")
                    else:
                        console.print(f"[yellow]Container status: {status}")
            except Exception as e:
                console.print(
                    Panel(
                        f"[red]Troubleshooting failed: {e}[/red]",
                        title="Error",
                        style="red",
                    )
                )
            Prompt.ask("Press Enter to return to menu")
        else:
            console.print("[red]Invalid selection. Please choose a valid option.[/red]")
            Prompt.ask("Press Enter to try again")


def project_utilities_menu():
    import subprocess

    while True:
        clear_screen()
        console.print(
            Panel(
                "[bold magenta]Project Utilities[/bold magenta]",
                subtitle="Git & Workspace Tools",
                box=box.DOUBLE,
            )
        )
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_row("[bold green][1][/bold green] Auto-Commit Changes")
        table.add_row("[bold yellow][2][/bold yellow] Clean Workspace")
        table.add_row("[bold cyan][3][/bold cyan] Refactor Project (future)")
        table.add_row("[bold][4][/bold] Back to Main Menu")
        console.print(table)
        choice = Prompt.ask(
            "Select an option", choices=["1", "2", "3", "4"], default="1"
        )
        if choice == "1":
            # Auto-Commit Changes
            try:
                status = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                changes = status.stdout.strip()
                if not changes:
                    console.print(
                        Panel(
                            "[yellow]No changes to commit.[/yellow]",
                            title="Git",
                            style="yellow",
                        )
                    )
                    Prompt.ask("Press Enter to return to menu")
                    continue
                subprocess.run(["git", "add", "."], check=True)
                # Get AI commit message
                resp = requests.post(
                    API_URL,
                    json={
                        "command_type": "generate_commit_message",
                        "payload": changes,
                    },
                    timeout=10,
                )
                resp.raise_for_status()
                commit_msg = (
                    resp.json().get("message")
                    or resp.json().get("commit_message")
                    or "AI Commit"
                )
                commit = subprocess.run(
                    ["git", "commit", "-m", commit_msg], capture_output=True, text=True
                )
                if commit.returncode == 0:
                    console.print(
                        Panel(
                            f"[green]Committed with message:[/green]\n{commit_msg}",
                            title="Git Commit",
                            style="green",
                        )
                    )
                else:
                    console.print(
                        Panel(
                            f"[red]Commit failed:[/red]\n{commit.stderr}",
                            title="Git Commit Error",
                            style="red",
                        )
                    )
            except subprocess.CalledProcessError as e:
                console.print(
                    Panel(
                        f"[red]Git error: {e.stderr or e}",
                        title="Git Error",
                        style="red",
                    )
                )
            except Exception as e:
                console.print(
                    Panel(f"[red]Error: {e}[/red]", title="Error", style="red")
                )
            Prompt.ask("Press Enter to return to menu")
        elif choice == "2":
            # Clean Workspace
            confirm = Prompt.ask(
                "Are you sure you want to clean? [y/N]",
                choices=["y", "Y", "n", "N"],
                default="N",
            )
            if confirm.lower() == "y":
                try:
                    clean = subprocess.run(
                        ["git", "clean", "-fdx"],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    console.print(
                        Panel(
                            f"[green]Workspace cleaned.[/green]\n{clean.stdout}",
                            title="Git Clean",
                            style="green",
                        )
                    )
                except subprocess.CalledProcessError as e:
                    console.print(
                        Panel(
                            f"[red]Clean failed: {e.stderr or e}",
                            title="Git Clean Error",
                            style="red",
                        )
                    )
            else:
                console.print("[yellow]Clean cancelled.[/yellow]")
            Prompt.ask("Press Enter to return to menu")
        elif choice == "3":
            console.print(Panel("Future: AI-driven refactoring...", style="cyan"))
            Prompt.ask("Press Enter to return to menu")
        elif choice == "4":
            break
        else:
            console.print("[red]Invalid selection. Please choose a valid option.[/red]")
            Prompt.ask("Press Enter to try again")


def nexus_configuration_menu():
    while True:
        clear_screen()
        console.print(
            Panel(
                "[bold blue]Nexus Configuration[/bold blue]",
                subtitle="Omnitide Codex Gateway",
                box=box.DOUBLE,
            )
        )
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_row("[bold green][1][/bold green] View Current LLM")
        table.add_row("[bold yellow][2][/bold yellow] Set Default LLM (future)")
        table.add_row("[bold magenta][3][/bold magenta] Manage Nexus Memory (future)")
        table.add_row("[bold cyan][4][/bold cyan] View Agent Protocols (future)")
        table.add_row("[bold][5][/bold] Back to Main Menu")
        console.print(table)
        choice = Prompt.ask(
            "Select an option", choices=["1", "2", "3", "4", "5"], default="1"
        )
        if choice == "1":
            # View Current LLM
            try:
                resp = requests.post(
                    API_URL,
                    json={"command_type": "get_llm_config", "payload": {}},
                    timeout=10,
                )
                resp.raise_for_status()
                llm_info = resp.json()
                console.print(
                    Panel(
                        json.dumps(llm_info, indent=2),
                        title="Current LLM Config",
                        box=box.ROUNDED,
                        style="green",
                    )
                )
            except Exception as e:
                console.print(
                    Panel(
                        f"[red]Failed to get LLM config: {e}[/red]",
                        title="Nexus Error",
                        style="red",
                    )
                )
            Prompt.ask("Press Enter to return to menu")
        elif choice == "2":
            console.print(Panel("Future: Set Default LLM...", style="yellow"))
            Prompt.ask("Press Enter to return to menu")
        elif choice == "3":
            console.print(Panel("Future: Manage Nexus Memory...", style="magenta"))
            Prompt.ask("Press Enter to return to menu")
        elif choice == "4":
            console.print(Panel("Future: View Agent Protocols...", style="cyan"))
            Prompt.ask("Press Enter to return to menu")
        elif choice == "5":
            break
        else:
            console.print("[red]Invalid selection. Please choose a valid option.[/red]")
            Prompt.ask("Press Enter to try again")


def detect_llms():
    # Try to detect available LLMs via Ollama API
    try:
        resp = pyrequests.get("http://localhost:11434/api/tags", timeout=3)
        resp.raise_for_status()
        tags = resp.json().get("models", [])
        return [m["name"] for m in tags]
    except Exception:
        return []


def setup_wizard():
    clear_screen()
    console.print(
        Panel(
            "[bold cyan]Omnitide Setup & Workflow Wizard[/bold cyan]",
            subtitle="Guided Configuration",
            box=box.DOUBLE,
        )
    )
    console.print(
        "\n[bold]Welcome! This wizard will help you set up, configure, and understand all workflows in this project.[/bold]\n"
    )
    # Docker check
    import shutil

    if not shutil.which("docker"):
        console.print(
            "[red]Docker is not installed or not in PATH. Please install Docker before continuing.[/red]"
        )
        Prompt.ask("Press Enter to exit wizard")
        return
    else:
        console.print("[green]Docker is installed.[/green]")
    # Docker image check
    import docker

    client = docker.from_env()
    images = client.images.list()
    image_names = [tag for img in images for tag in img.tags]
    if not any("duo-project" in tag for tag in image_names):
        console.print("[yellow]Docker image 'duo-project' not found. Building now...")
        os.system("docker build -t duo-project .")
        console.print("[green]Docker image built.[/green]")
    else:
        console.print("[green]Docker image 'duo-project' found.")
    # LLM detection and selection
    llms = detect_llms()
    if llms:
        console.print("\n[bold]Available LLMs detected:[/bold]")
        for idx, llm in enumerate(llms, 1):
            console.print(f"  [{idx}] {llm}")
        llm_choice = Prompt.ask(
            "Select LLM by number",
            choices=[str(i) for i in range(1, len(llms) + 1)],
            default="1",
        )
        selected_llm = llms[int(llm_choice) - 1]
        set_key(LLM_ENV_PATH, "OLLAMA_MODEL", selected_llm)
        console.print(f"[green]Selected LLM: {selected_llm} (saved to .env)[/green]")
    else:
        console.print("[yellow]No LLMs detected via Ollama. Using default: gemma:2b")
        set_key(LLM_ENV_PATH, "OLLAMA_MODEL", "gemma:2b")
    # Explain main workflows
    console.print("\n[bold]Workflows available:[/bold]")
    console.print(
        "- [cyan]Code Generation[/cyan]: Use LLMs to generate code from high-level descriptions."
    )
    console.print(
        "- [cyan]Agent Execution[/cyan]: Run ExWork, Scribe, and other agents for automation, validation, and review."
    )
    console.print(
        "- [cyan]Project Utilities[/cyan]: Git, cleaning, refactoring, and more."
    )
    console.print(
        "- [cyan]Nexus Backend[/cyan]: Manage the backend server and Docker containers."
    )
    console.print(
        "- [cyan]New Project Creation[/cyan]: Bootstrap a new project from this template."
    )
    console.print(
        "\n[bold]All scripts and agents in the workspace will be auto-discovered and available from the menu.[/bold]"
    )
    Prompt.ask("Press Enter to continue to the main menu")


def discover_scripts():
    # Discover all .py scripts in the workspace root (excluding hidden/venv/test folders)
    scripts = []
    cwd = os.getcwd()
    for fname in os.listdir(cwd):
        if (
            fname.endswith(".py")
            and not fname.startswith(".")
            and fname not in ["setup_duo.sh"]
        ):
            scripts.append(fname)
    return scripts


def main_menu():
    while True:
        clear_screen()
        console.print(
            Panel(
                "[bold cyan]Omnitide VSCode Bridge[/bold cyan]",
                subtitle="AI Assistant Menu",
                box=box.DOUBLE,
            )
        )
        table = Table(show_header=False, box=box.SIMPLE)
        table.add_row("[bold green][W][/bold green] Setup & Workflow Wizard")
        table.add_row("[bold green][1][/bold green] Generate Code")
        table.add_row("[bold yellow][2][/bold yellow] Manage Environment")
        table.add_row("[bold magenta][3][/bold magenta] Project Utilities")
        table.add_row("[bold blue][4][/bold blue] Nexus Configuration")
        table.add_row("[bold green][N][/bold green] New Project")
        table.add_row("[bold red][X][/bold red] Exit Nexus")
        table.add_row("[bold red][A][/bold red] Run Agent/Script")
        table.add_row("[bold cyan][H][/bold cyan] Help & Workflow Guide")
        table.add_row("[bold red][F][/bold red] Heal Project (Auto-Fix Everything)")
        console.print(table)
        scripts = discover_scripts()
        choice = Prompt.ask(
            "Select an option",
            choices=[
                "W",
                "w",
                "1",
                "2",
                "3",
                "4",
                "X",
                "x",
                "A",
                "a",
                "N",
                "n",
                "H",
                "h",
                "F",
                "f",
            ],
            default="1",
        )
        if choice.lower() == "w":
            setup_wizard()
        elif choice == "1":
            desc = Prompt.ask("Enter a high-level description for code generation")
            dispatch_command("generate_code", desc)
            Prompt.ask("Press Enter to return to menu")
        elif choice == "2":
            manage_environment_menu()
            Prompt.ask("Press Enter to return to menu")
        elif choice == "3":
            project_utilities_menu()
            Prompt.ask("Press Enter to return to menu")
        elif choice == "4":
            nexus_configuration_menu()
            Prompt.ask("Press Enter to return to menu")
        elif choice.lower() == "x":
            console.print("[bold green]Goodbye![/bold green]")
            break
        elif choice.lower() == "a":
            # Run agent/script (auto-discovered)
            agent_table = Table(show_header=True, header_style="bold magenta")
            agent_table.add_column("Option")
            agent_table.add_column("Agent/Script")
            for idx, script in enumerate(scripts, 1):
                agent_table.add_row(str(idx), script)
            agent_table.add_row("X", "Back to Main Menu")
            console.print(agent_table)
            agent_choices = [str(i) for i in range(1, len(scripts) + 1)] + ["X", "x"]
            agent_choice = Prompt.ask(
                "Select agent/script to run", choices=agent_choices, default="1"
            )
            if agent_choice.lower() == "x":
                pass
            else:
                idx = int(agent_choice) - 1
                if 0 <= idx < len(scripts):
                    os.system(f"python3 {scripts[idx]}")
            Prompt.ask("Press Enter to return to menu")
        elif choice.lower() == "n":
            # New Project creation
            import shutil

            new_proj_name = Prompt.ask("Enter new project name (no spaces)")
            new_proj_path = os.path.join("/workspace", new_proj_name)
            if os.path.exists(new_proj_path):
                console.print(f"[red]Directory {new_proj_path} already exists![/red]")
            else:
                shutil.copytree(
                    "/workspace",
                    new_proj_path,
                    ignore=shutil.ignore_patterns(
                        ".git",
                        "test_env",
                        "__pycache__",
                        "*.pyc",
                        "*.pyo",
                        "*.egg-info",
                        "venv",
                        ".*",
                        "omnitide",
                        "setup_duo.sh",
                    ),
                )
                console.print(f"[green]New project created at {new_proj_path}[/green]")
                # Optionally, re-init git
                os.system(f"cd {new_proj_path} && rm -rf .git && git init")
                console.print(
                    f"[yellow]Initialized new git repo in {new_proj_path}[/yellow]"
                )
            Prompt.ask("Press Enter to return to menu")
        elif choice.lower() == "h":
            console.print(
                Panel(
                    "[bold]Omnitide Workflow Guide[/bold]\n\n- [green]Setup & Workflow Wizard[/green]: Guides you through zero-touch setup, LLM selection, and config.\n- [green]Generate Code[/green]: Use LLMs for code synthesis.\n- [green]Manage Environment[/green]: Docker, backend, and troubleshooting.\n- [green]Project Utilities[/green]: Git, cleaning, refactoring.\n- [green]Nexus Configuration[/green]: LLM and backend settings.\n- [green]New Project[/green]: Bootstrap a new project from this template.\n- [green]Run Agent/Script[/green]: Launch any discovered agent or script.\n\nAll agents/scripts use the unified .env config for LLM and environment.\nAll features are accessible from this menu.",
                    title="Help & Workflow Guide",
                    style="cyan",
                )
            )
            Prompt.ask("Press Enter to return to menu")
        elif choice.lower() == "f":
            console.print(
                Panel(
                    "[bold green]Running Ultimate Project Healer...[/bold green]",
                    title="Heal Project",
                    style="green",
                )
            )
            os.system("python3 heal_project.py")
            Prompt.ask("Press Enter to return to menu")
        else:
            console.print("[red]Invalid selection. Please choose a valid option.[/red]")
            Prompt.ask("Press Enter to try again")


if __name__ == "__main__":
    main_menu()
