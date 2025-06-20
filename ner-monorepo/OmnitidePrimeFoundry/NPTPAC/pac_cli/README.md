# PAC - Prompt Assembler CLI

This is the main application directory for PAC, the command-line interface
for the Nexus Protocol Toolkit.

## Setup

1.  Ensure you have Python installed (see `../pyproject.toml` for version).
2.  Navigate to this directory (`pac_cli`).
3.  Run the virtual environment setup script: `bash setup_venv.sh`
    This will create a `.venv_pac` directory and install dependencies.

## Running PAC

After setup, you can run PAC using the `npac` launcher located in the
NPT base directory (`../npac`).

Alternatively, activate the virtual environment:
`source .venv_pac/bin/activate`

Then run the main application:
`python app/main.py --help`

## Development

Refer to `../pyproject.toml` for managing dependencies with Poetry (recommended)
or use the `requirements.txt` and `requirements-dev.txt` with pip.

Run tests using `pytest` from this directory (after activating venv and installing dev dependencies).