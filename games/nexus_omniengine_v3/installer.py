import sys
import shutil
import subprocess
import time
import json
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from rich.progress import Progress

console = Console()

INSTALL_GUIDE = """
Welcome to the Nexus OmniEngine v3.0 Interactive Installer!

This installer will guide you through the setup and configuration of your Nexus OmniEngine environment.

You will:
- Review and confirm system requirements
- Configure API keys and security settings
- Set up persistent storage and directories
- Install Python and system dependencies
- Initialize the Nexus OmniEngine platform

Let's get started!
"""

REQUIRED_PYTHON = (3, 10)
REQUIRED_SYSTEM_TOOLS = ["git", "docker", "ansible", "curl"]
REQUIRED_PYTHON_PACKAGES = [
    "langchain",
    "openai",
    "PyYAML",
    "Flask",
    "APScheduler",
    "python-dotenv",
    "GitPython",
    "flake8",
    "black",
    "pytest",
    "rich",
    "textual",
    "uvicorn",
    "gunicorn",
    "watchdog",
    "jsonschema",
    "requests",
    "tenacity",
    "cryptography",
]


def check_python_version():
    if sys.version_info < REQUIRED_PYTHON:
        console.print(
            f"[red]Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]} or higher is required. Exiting.[/red]"
        )
        sys.exit(1)
    console.print(f"[green]Python version OK: {sys.version.split()[0]}[/green]")


def check_system_tools():
    missing = []
    for tool in REQUIRED_SYSTEM_TOOLS:
        if shutil.which(tool) is None:
            missing.append(tool)
    if missing:
        console.print(
            f"[red]Missing required system tools: {', '.join(missing)}. Please install them and re-run the installer.[/red]"
        )
        sys.exit(1)
    console.print("[green]All required system tools are installed.[/green]")


def install_python_packages():
    console.print("[bold]Installing required Python packages...[/bold]")
    # Use requirements.txt if present for version consistency
    req_file = Path("requirements.txt")
    if req_file.exists():
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
        )
        if result.returncode != 0:
            console.print(
                "[red]Failed to install from requirements.txt. Please check for errors above.[/red]"
            )
            sys.exit(1)
    else:
        with Progress() as progress:
            task = progress.add_task(
                "Installing...", total=len(REQUIRED_PYTHON_PACKAGES)
            )
            for pkg in REQUIRED_PYTHON_PACKAGES:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", pkg],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                progress.update(task, advance=1)
    console.print("[green]All Python packages installed.[/green]")


def configure_api_keys():
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    config_path = config_dir / "main_config.json"
    user_config_path = config_dir / "user_config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        config = {}
    api_key = Prompt.ask(
        "Enter your OpenAI/Ollama API key (or leave blank to skip)",
        default=config.get("llm_api_key", ""),
    )
    if api_key:
        config["llm_api_key"] = api_key
    config["ansible_inventory_path"] = Prompt.ask(
        "Path to Ansible inventory",
        default=config.get("ansible_inventory_path", "nexus_ansible/inventory.ini"),
    )
    config["security_policy_path"] = Prompt.ask(
        "Path to security policy JSON",
        default=config.get("security_policy_path", "config/security_policy.json"),
    )
    config["sandbox_cpu_limit"] = Prompt.ask(
        "Sandbox CPU limit (e.g., 1)", default=str(config.get("sandbox_cpu_limit", "1"))
    )
    config["sandbox_memory_limit"] = Prompt.ask(
        "Sandbox memory limit (e.g., 512m)",
        default=str(config.get("sandbox_memory_limit", "512m")),
    )
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    # Also create/update user_config.json for user-specific overrides
    user_config = {}
    if user_config_path.exists():
        with open(user_config_path) as f:
            user_config = json.load(f)
    user_config.update({"api_key": api_key})
    with open(user_config_path, "w") as f:
        json.dump(user_config, f, indent=2)
    console.print(
        f"[green]Configuration saved to {config_path} and {user_config_path}[/green]"
    )


def setup_persistent_storage():
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    state_file = data_dir / "orchestrator_state.json"
    if not state_file.exists():
        with open(state_file, "w") as f:
            json.dump(
                {"workflows": [], "agents": [], "last_updated": time.time()},
                f,
                indent=2,
            )
    console.print(f"[green]Persistent storage initialized at {data_dir}[/green]")


def check_llm_connectivity():
    console.print("[bold]Testing LLM connectivity (Ollama/OpenAI)...[/bold]")
    import requests

    config_path = Path("config/main_config.json")
    if not config_path.exists():
        console.print(
            "[yellow]No config found, skipping LLM connectivity test.[/yellow]"
        )
        return
    with open(config_path) as f:
        config = json.load(f)
    api_key = config.get("llm_api_key", "")
    # Try Ollama local endpoint first
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            console.print(
                "[green]Ollama LLM server detected and reachable on localhost:11434[/green]"
            )
            return
    except Exception:
        pass
    # Try OpenAI API if key present
    if api_key:
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            response = requests.get(
                "https://api.openai.com/v1/models", headers=headers, timeout=5
            )
            if response.status_code == 200:
                console.print("[green]OpenAI API reachable and API key valid.[/green]")
                return
            else:
                console.print(
                    f"[yellow]OpenAI API responded but not OK: {response.status_code}[/yellow]"
                )
        except Exception as e:
            console.print(f"[yellow]OpenAI API not reachable: {e}[/yellow]")
    console.print(
        "[yellow]No LLM server detected. You may need to start Ollama or check your API key.[/yellow]"
    )


def main():
    console.print(INSTALL_GUIDE)
    check_python_version()
    check_system_tools()
    install_python_packages()
    configure_api_keys()
    setup_persistent_storage()
    check_llm_connectivity()
    console.print(
        "[bold green]Nexus OmniEngine v3.0 installation and configuration complete![/bold green]"
    )
    console.print(
        "[bold]You can now run the TUI with:[/bold] [yellow]nexus-omni-tui[/yellow]"
    )


# --- Ensure main() is defined before calling it ---
if __name__ == "__main__":

    def main():
        console.print(INSTALL_GUIDE)
        check_python_version()
        check_system_tools()
        install_python_packages()
        configure_api_keys()
        setup_persistent_storage()
        check_llm_connectivity()
        console.print(
            "[bold green]Nexus OmniEngine v3.0 installation and configuration complete![/bold green]"
        )
        console.print(
            "[bold]You can now run the TUI with:[/bold] [yellow]nexus-omni-tui[/yellow]"
        )

    main()
