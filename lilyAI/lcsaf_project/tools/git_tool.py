import paramiko


class GitTool:
    def __init__(self, hostname, username, key_path):
        self.hostname = hostname
        self.username = username
        self.key_path = key_path

    def git_command(self, repo_path, command):
        key = paramiko.RSAKey.from_private_key_file(self.key_path)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.hostname, username=self.username, pkey=key)
        cmd = f"cd {repo_path} && {command}"
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode()
        err = stderr.read().decode()
        client.close()
        return {"output": out, "error": err}
