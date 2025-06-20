import paramiko


class FileManagerTool:
    def __init__(self, hostname, username, key_path):
        self.hostname = hostname
        self.username = username
        self.key_path = key_path

    def read_file(self, remote_path):
        key = paramiko.RSAKey.from_private_key_file(self.key_path)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.hostname, username=self.username, pkey=key)
        sftp = client.open_sftp()
        with sftp.open(remote_path, "r") as f:
            content = f.read()
        sftp.close()
        client.close()
        return content

    def write_file(self, remote_path, content):
        key = paramiko.RSAKey.from_private_key_file(self.key_path)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.hostname, username=self.username, pkey=key)
        sftp = client.open_sftp()
        with sftp.open(remote_path, "w") as f:
            f.write(content)
        sftp.close()
        client.close()
        return True
