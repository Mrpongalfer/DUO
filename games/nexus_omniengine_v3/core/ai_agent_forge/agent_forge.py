import os
import yaml
from langchain.agents import initialize_agent, AgentType
from langchain.chat_models import ChatOpenAI
from games.nexus_omniengine_v3.core.ai_agent_forge.utils import load_tools


def create_agent():
    """
    Interactive TUI-style prompt to create an AI agent configuration and save it as a YAML file.
    """
    print("=== Nexus OmniEngine AI Agent Forge ===")
    role = input(
        "Enter agent role (e.g., 'devops', 'security', 'data_scientist'): "
    ).strip()
    capabilities = input(
        "Enter agent capabilities (comma-separated, e.g., 'web_scraping,code_gen,wikipedia'): "
    ).split(",")
    security_constraints = input(
        "Enter security constraints (comma-separated, e.g., 'no_network,read_only_fs'): "
    ).split(",")

    # Load tools based on capabilities
    tools = load_tools([c.strip() for c in capabilities])

    agent_config = {
        "role": role,
        "capabilities": [c.strip() for c in capabilities],
        "security_constraints": [s.strip() for s in security_constraints],
        "tools": [t.name for t in tools],
        "llm": "openai-gpt-4",
        "agent_type": str(AgentType.ZERO_SHOT_REACT_DESCRIPTION),
    }

    # Save agent config to YAML
    agents_dir = os.path.join(os.path.dirname(__file__), "../../../agents")
    os.makedirs(agents_dir, exist_ok=True)
    agent_path = os.path.join(agents_dir, f"{role}_agent.yaml")
    with open(agent_path, "w") as f:
        yaml.dump(agent_config, f)
    print(f"Agent configuration saved to {agent_path}")

    # Optionally, initialize the agent (for demonstration)
    llm = ChatOpenAI()
    agent = initialize_agent(
        tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True
    )
    print(f"Agent '{role}' initialized with tools: {[t.name for t in tools]}")
    return agent_config


if __name__ == "__main__":
    create_agent()
