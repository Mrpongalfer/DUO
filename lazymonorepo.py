#!/usr/bin/env python3
"""
LazyMonorepo: Bleeding-edge, elegantly simple yet comprehensive TUI for monorepo healing, refactor, and automation.
Now with arrow-key navigation, config-driven remapping, and dynamic workflows!
"""
from pathlib import Path
import subprocess
import yaml
import questionary

CONFIG_PATH = Path(__file__).parent / "lazymonorepo_config.yaml"
ROOT = Path(__file__).parent.resolve()

# Load config
if CONFIG_PATH.exists():
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)
else:
    config = {}

MENU = [
    "Inventory & Map Repo",
    "Find & Delete Duplicates",
    "Bulk Refactor Imports/Paths",
    "Merge requirements.txt",
    "Run Healing Script",
    "Lint & Format All",
    "Run Tests",
    "AI Suggest Fixes",
    "Git Status & Commit",
    "Diagnose & Autofix Docker/Compose Issues",
    "Run Nexus Omniengine Agent",
    "Start Omnitide Dashboard",
    "Trigger Full Self-Heal Cycle",
    "Vectorize All Source Code",
    "Generate System Health Report",
    "Secure Key/Secret/SSH/GPG Management",
    "Remap/Configure Paths & Agents",
    "Exit",
]


def run(cmd, shell=True, check=False):
    print(f"\n>>> {cmd}")
    return subprocess.run(cmd, shell=shell, check=check)


def remap_config():
    print("\n--- Remap/Configure Paths & Agents ---")
    for key in config:
        newval = questionary.text(f"{key} [{config[key]}]:").ask()
        if newval:
            config[key] = newval
    with open(CONFIG_PATH, "w") as f:
        yaml.safe_dump(config, f)
    print("Config updated!")


def menu():
    while True:
        choice = questionary.select(
            "Choose an action:",
            choices=MENU,
        ).ask()
        if choice == "Inventory & Map Repo":
            run(f"tree -L 2 {ROOT}")
        elif choice == "Find & Delete Duplicates":
            run(f"fdupes -r {ROOT}")
            if questionary.confirm("Delete all duplicates found by fdupes?").ask():
                run(f"fdupes -rdN {ROOT}")
        elif choice == "Bulk Refactor Imports/Paths":
            pattern = questionary.text(
                "Enter import/path pattern to refactor (e.g. old_pkg):"
            ).ask()
            repl = questionary.text("Replace with:").ask()
            run(f"rg -l '{pattern}' {ROOT} | xargs sed -i 's/{pattern}/{repl}/g'")
        elif choice == "Merge requirements.txt":
            reqs = list(ROOT.glob("**/requirements.txt"))
            merged = set()
            for req in reqs:
                with open(req) as f:
                    merged.update(
                        line.strip()
                        for line in f
                        if line.strip() and not line.startswith("#")
                    )
            merged = sorted(merged)
            with open(ROOT / "requirements.txt", "w") as f:
                f.write("# Merged by LazyMonorepo\n" + "\n".join(merged) + "\n")
            print(f"Merged {len(reqs)} requirements.txt files into root requirements.txt.")
        elif choice == "Run Healing Script":
            if (ROOT / "heal_project.py").exists():
                run(config.get("heal_script", f"python3 {ROOT}/heal_project.py"))
            else:
                print("heal_project.py not found!")
        elif choice == "Lint & Format All":
            run("black .")
            run("ruff check . --fix")
        elif choice == "Run Tests":
            if (ROOT / "test_runner.sh").exists():
                run(f"bash {ROOT}/test_runner.sh")
            else:
                run("pytest")
        elif choice == "AI Suggest Fixes":
            print("AI Suggestion: Use Copilot or run llm_code_generator.py for deeper healing.")
            if (ROOT / "llm_code_generator.py").exists():
                run(f"python3 {ROOT}/llm_code_generator.py")
        elif choice == "Git Status & Commit":
            run("git status")
            if questionary.confirm("Commit all changes?").ask():
                msg = questionary.text("Commit message:").ask()
                run(f"git add -A && git commit -m '{msg}'")
        elif choice == "Diagnose & Autofix Docker/Compose Issues":
            print("\n--- Docker/Compose Diagnostics ---")
            run("docker info || (echo 'Docker daemon not running or not installed!' && exit 1)")
            run("docker compose version || docker-compose --version || (echo 'docker-compose not found!' && exit 1)")
            if (ROOT / "Dockerfile").exists():
                run(f"docker build -t lazy-diagnose-test -f {ROOT}/Dockerfile . || echo 'Docker build failed! Check Dockerfile.'")
            else:
                print("No Dockerfile found.")
            if (ROOT / "docker-compose.yaml").exists():
                run(f"docker compose -f {ROOT}/docker-compose.yaml config || echo 'docker-compose.yaml has errors!'")
            else:
                print("No docker-compose.yaml found.")
            print("\nIf you see errors above, try running 'docker system prune' or 'docker compose down --remove-orphans' to clean up.")
            print("For autofix, try: 'docker system prune -af' (WARNING: removes all unused containers/images!)")
        elif choice == "Run Nexus Omniengine Agent":
            run(config.get("nexus_agent", "python3 games/nexus_omniengine_v3/installer.py"))
        elif choice == "Start Omnitide Dashboard":
            run(config.get("omnitide_dashboard", "python3 omnitide-vscode-bridge/main.py"))
        elif choice == "Trigger Full Self-Heal Cycle":
            run(config.get("heal_script", f"python3 {ROOT}/heal_project.py"))
            run("black .")
            run("ruff check . --fix")
            run("pytest")
            run(config.get("vectorizer_script", "python3 vectorize_constitution.py"))
        elif choice == "Vectorize All Source Code":
            run(config.get("vectorizer_script", "python3 vectorize_constitution.py"))
        elif choice == "Generate System Health Report":
            run("git status")
            run("poetry check")
            run("docker info || echo 'Docker not running!'")
            run("pytest --maxfail=1 --disable-warnings")
            print("Check above for any errors or warnings.")
        elif choice == "Secure Key/Secret/SSH/GPG Management":
            print("\n--- Secure Key/Secret/SSH/GPG Management ---")
            print("1. List SSH keys: ls ~/.ssh/*.pub")
            print("2. Add SSH key to agent: ssh-add ~/.ssh/id_ed25519")
            print("3. List GPG keys: gpg --list-secret-keys --keyid-format LONG")
            print("4. Export GPG public key: gpg --armor --export <KEYID>")
            print("5. Import GPG key: gpg --import <file>")
            print("6. Edit secrets: use 'pass', 'gopass', or 'sops' for encrypted secret management.")
            print("7. For .env secrets: use 'dotenv-vault' or 'direnv' for secure .env workflows.")
            print("8. For GitHub/GitLab: use their web UI for managing deploy keys and secrets.")
            print("9. For hacky/fast secret sharing: use 'age', 'gpg', or 'qrencode' to encrypt and share secrets.")
            print("\n[Tip] Use 'pass' (https://www.passwordstore.org/) for CLI password management, and 'gopass' for team workflows.")
        elif choice == "Remap/Configure Paths & Agents":
            remap_config()
        elif choice == "Exit":
            print("Bye!")
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    menu()
