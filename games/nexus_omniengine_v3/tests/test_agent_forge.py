"""
Test: agent_forge.py
Drake v0.3 protocol, TPC-compliant
"""

import unittest
from games.nexus_omniengine_v3.core.ai_agent_forge.agent_forge import AgentType, load_tools


class TestAgentForge(unittest.TestCase):
    def test_load_tools(self):
        tools = load_tools(["search", "calculator"])
        self.assertIsInstance(tools, list)
        self.assertTrue(all(callable(t) for t in tools))

    def test_agent_type_enum(self):
        self.assertIn("REACT", AgentType.__members__)
        self.assertIn("OPENAI", AgentType.__members__)


if __name__ == "__main__":
    unittest.main()
