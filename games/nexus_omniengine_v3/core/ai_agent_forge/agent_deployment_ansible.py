import yaml


def generate_ansible_deploy(agent_config, output_path):
    """
    Generate an Ansible YAML deployment file for the given agent configuration.
    """
    playbook = [
        {
            "name": f"Deploy {agent_config['role']} agent",
            "hosts": "localhost",
            "tasks": [
                {
                    "name": "Create agent config file",
                    "copy": {
                        "content": yaml.dump(agent_config),
                        "dest": f"/etc/nexus_agents/{agent_config['role']}_agent.yaml",
                    },
                },
                {
                    "name": "Start agent service",
                    "systemd": {
                        "name": f"{agent_config['role']}_agent",
                        "enabled": True,
                        "state": "started",
                        "daemon_reload": True,
                    },
                },
            ],
        }
    ]
    with open(output_path, "w") as f:
        yaml.dump(playbook, f)
    print(f"Ansible deployment playbook written to {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate Ansible deployment playbook for an agent."
    )
    parser.add_argument(
        "--config", required=True, help="Path to agent YAML config file"
    )
    parser.add_argument(
        "--output", required=True, help="Output path for Ansible playbook"
    )
    args = parser.parse_args()
    with open(args.config) as f:
        agent_config = yaml.safe_load(f)
    generate_ansible_deploy(agent_config, args.output)
