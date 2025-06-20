import json
from langchain.agents import Tool
from langchain.utilities import WikipediaAPIWrapper


def load_tools(tool_names: list, config_path: str = "config/agent_tools_map.json"):
    """
    Dynamically loads LangChain tools based on a list of tool names and a configuration mapping.
    """
    available_tools = {}
    # Load tool mappings from config file
    try:
        with open(config_path, "r") as f:
            tool_map = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Agent tool map not found at {config_path}. Please create it."
        )

    tools_to_load = []
    for tool_name in tool_names:
        tool_name = tool_name.strip()
        if tool_name in tool_map:
            tool_info = tool_map[tool_name]
            if tool_info.get("type") == "langchain_builtin":
                if tool_name == "wikipedia":
                    tools_to_load.append(
                        Tool(
                            name="Wikipedia",
                            func=WikipediaAPIWrapper().run,
                            description="A wrapper around Wikipedia. Use this for general knowledge queries.",
                        )
                    )
                # Add more built-in LangChain tools here as needed.
            elif tool_info.get("type") == "custom":
                tools_to_load.append(
                    Tool(
                        name=tool_info["name"],
                        func=lambda x: f"Custom tool '{tool_info['name']}' executed with input: {x}",
                        description=tool_info["description"],
                    )
                )
            else:
                raise ValueError(f"Unknown tool type for {tool_name}")
        else:
            print(
                f"Warning: Tool '{tool_name}' not found in tool map. Skipping or adding placeholder."
            )
            tools_to_load.append(
                Tool(
                    name=f"Generic_{tool_name}",
                    func=lambda x: f"This is a generic tool for '{tool_name}' with input: {x}",
                    description=f"A generic tool for the capability: {tool_name}",
                )
            )
    return tools_to_load
