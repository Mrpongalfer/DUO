import paramiko
import logging
from typing import List


class SSHExecutorTool:
    def __init__(self, hostname, username, key_path, whitelist: List[str]):
        self.hostname = hostname
        self.username = username
        self.key_path = key_path
        self.whitelist = whitelist
        self.logger = logging.getLogger("SSHExecutorTool")
        handler = logging.FileHandler("ssh_executor.log")
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def execute(self, command):
        if command not in self.whitelist:
            self.logger.warning(f"Blocked non-whitelisted command: {command}")
            return {"error": "Command not allowed"}
        try:
            wrapped_cmd = f"firejail --whitelist={self.key_path} {command}"
            key = paramiko.RSAKey.from_private_key_file(self.key_path)
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(self.hostname, username=self.username, pkey=key)
            stdin, stdout, stderr = client.exec_command(wrapped_cmd)
            out = stdout.read().decode()
            err = stderr.read().decode()
            client.close()
            self.logger.info(f"Executed: {command}\nOutput: {out}\nError: {err}")
            return {"output": out, "error": err}
        except Exception as e:
            self.logger.error(f"Execution failed: {e}")
            return {"error": str(e)}
