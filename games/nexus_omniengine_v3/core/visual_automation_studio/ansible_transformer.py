import yaml


def generate_ansible(workflow, output_path):
    """
    Generate an Ansible YAML playbook from a conceptual workflow definition.
    """
    playbook = []
    for stage in workflow:
        playbook.append(
            {
                "name": stage.get("name", "Unnamed Stage"),
                "hosts": stage.get("hosts", "localhost"),
                "tasks": stage.get("tasks", []),
            }
        )
    with open(output_path, "w") as f:
        yaml.dump(playbook, f)
    print(f"Ansible playbook generated at {output_path}")


if __name__ == "__main__":
    # Example usage for demonstration
    workflow = [
        {
            "name": "Install dependencies",
            "hosts": "localhost",
            "tasks": [
                {"name": "Install git", "apt": {"name": "git", "state": "present"}},
                {
                    "name": "Install python3",
                    "apt": {"name": "python3", "state": "present"},
                },
            ],
        },
        {
            "name": "Run custom script",
            "hosts": "localhost",
            "tasks": [{"name": "Run script", "shell": "echo Hello World"}],
        },
    ]
    generate_ansible(workflow, "example_playbook.yml")
