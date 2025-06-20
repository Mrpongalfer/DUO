"""
Agent Service: Nexus OmniEngine v3.0
Drake v0.3 protocol, TPC-compliant
Service interface for agent orchestration and management
"""

from .agent_handler import AgentHandler


class AgentService:
    def __init__(self, agent_script: str):
        self.handler = AgentHandler(agent_script)

    def deploy(self):
        self.handler.start()

    def remove(self):
        self.handler.stop()

    def status(self):
        return self.handler.status()

    def update(self):
        self.handler.restart()
