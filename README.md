# Project Overview

This repository contains two primary agents, **Ex-Work Agent** (`exworkagent0.py`) and **Scribe Agent** (`scribe0.py`), designed for robust task execution, dynamic learning, and DevOps integration.

## Features

### Ex-Work Agent (`exworkagent0.py`)
- **Dynamic Learning**:
  - Implements `learn_from_failures` to dynamically adapt and register new handlers.
  - Supports recursive learning and handler refinement.
- **Interactive Mode**:
  - Allows users to configure tasks and execute pipelines interactively.
- **DevOps Integration**:
  - Includes tools like Black, Flake8, and Ruff for formatting, linting, and static analysis.
- **Task Handlers**:
  - Provides a variety of handlers for tasks like file operations, script execution, and LLM integration.

### Scribe Agent (`scribe0.py`)
- **Validation Pipeline**:
  - Executes a series of validation steps, including formatting, linting, type checking, and test generation.
- **Dynamic Learning**:
  - Includes `learn_from_failures` for adaptive task handling.
- **Interactive Mode**:
  - Offers an interactive interface for configuring and executing validation steps.
- **DevOps Best Practices**:
  - Integrates tools like Black, Flake8, and Ruff.
- **AI Integration**:
  - Uses LLMs for tasks like test generation and code review.

### Dockerization
- A `Dockerfile` is included to containerize the project, ensuring compatibility and ease of deployment.

### Rules and Protocols
- The `Rules/` directory contains documents defining interaction principles, protocols, and guidelines for agent behavior.

## Usage

### Running Ex-Work Agent
```bash
python exworkagent0.py --interactive
```

### Running Scribe Agent
```bash
python scribe0.py --interactive
```

### Docker
To build and run the Docker container:
```bash
docker build -t agent-container .
docker run -it agent-container
```

## Development

### Setting Up
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run linting and formatting:
   ```bash
   black .
   flake8 .
   ruff check .
   ```

### Testing
- Validate interactive modes and DevOps integrations.
- Test the Docker container to ensure it runs the agents correctly.

## Contributing
Please follow the guidelines in `Rules/` for contributing to this project.

## License
This project is licensed under the MIT License.
