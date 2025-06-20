"""
Agent Handler: Nexus OmniEngine v3.0
Drake v0.3 protocol, TPC-compliant
Handles agent lifecycle: start, stop, status, restart
"""

import subprocess
from typing import Optional


class AgentHandler:
    def __init__(self, agent_script: str):
        self.agent_script = agent_script
        self.process: Optional[subprocess.Popen] = None

    def start(self):
        if self.process and self.process.poll() is None:
            print("Agent already running.")
            return
        self.process = subprocess.Popen(["xonsh", "-c", f"python3 {self.agent_script}"])
        print("Agent started.")

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait()
            print("Agent stopped.")
        else:
            print("Agent not running.")

    def status(self):
        if self.process and self.process.poll() is None:
            print("Agent is running.")
            return True
        print("Agent is not running.")
        return False

    def restart(self):
        self.stop()
        self.start()
