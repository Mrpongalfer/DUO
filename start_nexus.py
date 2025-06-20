#!/usr/bin/env python3
import os
import subprocess
import sys

#!/usr/bin/env python3
#!/usr/bin/env python3
#!/usr/bin/env python3
#!/usr/bin/env python3
#!/usr/bin/env python3
#!/usr/bin/env python3
#!/usr/bin/env python3
#!/usr/bin/env python3
#!/usr/bin/env python3
#!/usr/bin/env python3

CONTAINER_NAME = "omnitide_nexus_instance"
IMAGE_NAME = "omnitide-nexus-agent"
DOCKERFILE_PATH = "./Dockerfile"
HOST_PORT = "5000"
CONTAINER_PORT = "5000"
CODEBASE_PATH = os.path.abspath(os.getcwd())
ENV_VARS = [
    "-e",
    "OLLAMA_HOST=http://host.docker.internal:11434",
    "-e",
    "OLLAMA_MODEL=llama3",
]


def run_command(cmd, capture_output=False):
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, capture_output=capture_output, text=True
        )
        return result.stdout.strip() if capture_output else None
    except subprocess.CalledProcessError as e:
        if capture_output and e.stdout:
            print(e.stdout)
        print(f"Command failed: {e}")
        sys.exit(1)


def container_exists(name):
    cmd = f"docker ps -a --filter 'name=^{name}$' --format '{{{{.Names}}}}'"
    output = run_command(cmd, capture_output=True)
    return name in output.splitlines() if output else False


def container_running(name):
    cmd = f"docker ps --filter 'name=^{name}$' --format '{{{{.Names}}}}'"
    output = run_command(cmd, capture_output=True)
    return name in output.splitlines() if output else False


def image_exists(image):
    cmd = f"docker images --format '{{{{.Repository}}}}' | grep -w {image} || true"
    output = run_command(cmd, capture_output=True)
    return image in output.splitlines() if output else False


def build_image():
    print(f"Building Docker image '{IMAGE_NAME}'...")
    cmd = f"docker build -t {IMAGE_NAME} -f {DOCKERFILE_PATH} ."
    run_command(cmd)


def start_container():
    print(f"Starting container '{CONTAINER_NAME}'...")
    cmd = (
        [
            "docker",
            "run",
            "-d",
            "--name",
            CONTAINER_NAME,
            "-p",
            f"{HOST_PORT}:{CONTAINER_PORT}",
            "-v",
            f"{CODEBASE_PATH}:/app/codebase",
        ]
        + ENV_VARS
        + [IMAGE_NAME]
    )
    run_command(" ".join(cmd))


def main():
    if not image_exists(IMAGE_NAME):
        build_image()
    if not container_exists(CONTAINER_NAME):
        start_container()
    elif not container_running(CONTAINER_NAME):
        print(f"Container '{CONTAINER_NAME}' exists but is not running. Starting...")
        run_command(f"docker start {CONTAINER_NAME}")
    else:
        print(f"Container '{CONTAINER_NAME}' is already running.")


if __name__ == "__main__":
    main()
