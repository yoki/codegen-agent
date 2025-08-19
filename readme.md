# CodeGen Agent

LLM-assisted data analysis that can:
- Generate Python code from a natural-language request
- Execute the code against *your* variables in a disposable Docker container (root-in-container), with inputs mounted read-only and outputs mounted read-write
- Optionally provide IPython/Jupyter UX; otherwise use `core/*` programmatically

Use as a Python library.

## Project Structure

```
codegen_agent/
├── core/                   # Core functionality for programmatic use
│   ├── execution/          # Code execution in Docker containers
│   │   ├── docker_runtime.py    # Docker container management
│   │   ├── prelude.py           # Python environment setup
│   │   └── runner.py            # Code execution orchestration
│   ├── llm_client.py       # LLM API client interface
│   ├── llm_service.py      # LLM service abstraction
│   ├── load_dotenv.py      # Environment configuration
│   ├── models.py           # Data models and schemas
│   └── workflow.py         # End-to-end workflow orchestration
└── ipy/                    # IPython/Jupyter integration
    ├── display.py          # Rich display utilities
    └── magic_agent.py      # Jupyter magic commands

samples/                    # Example usage scripts
├── codegen_then_exec.py    # Basic code generation and execution
├── container_safety.py    # Container security demonstrations
├── e2e_gemini.py          # End-to-end example with Gemini LLM
├── large_variable_passthrough.py  # Handling large data variables
└── workflow_retry.py      # Error handling and retry logic

sandbox/
└── Dockerfile.runner      # Docker image for safe code execution
```

## Key Features

- **Safe Execution**: Code runs in isolated Docker containers with read-only input mounts
- **Jupyter Support**: Magic commands for interactive data analysis

## Quick Start

### Programmatic Usage

```python
from codegen_agent.core.workflow import CodeGenWorkflow

# Initialize workflow with your LLM configuration
workflow = CodeGenWorkflow()

# Generate and execute code
result = workflow.run("Create a bar chart of sales by month", 
                     variables={"sales_data": df})
```

### Jupyter Magic Commands

```python
%load_ext codegen_agent.ipy.magic_agent

%%agent
Create a scatter plot showing the correlation between price and sales
```

## Installation
Needs to configure LLM keys in .env file with following contents.

```
GEMINI_API_KEY_FOR_CODEGEN_AGENT=your_api_key_here
```
It will first read `CODEGEN_AGENT_DOTENV_PATH` environment variable. after that fall back to defaults, first current directory, then home directory, and app default.

### Windows
Default location is `%LOCALAPPDATA%\codegen_agent\State\.env`

### WSL
Default location is `~/.config/codegen-agent/.env`

### Devcontainer/Docker
Default location is `/secrets/codegen_agent/.env` 
Mount something like this in `devcontainer.json`.

```
    "mounts": [
        "type=bind,source=/mnt/c/my-path-to-secret,target=/secrets/codegen_agent,readonly",
    ],
```


## Log
LLM communication log is output to following location

```sh
<CODEGEN_AGENT_STATE>/log/codegen_agent.log # if CODEGEN_AGENT_STATE is set
%LOCALAPPDATA%\codegen_agent\State\log\codegen_agent.log # windows
~/.config/codegen-agent/log/codegen_agent.log  # WSL or devcontainer
```

In devcontainer, recommended to set env-var like this to see easy access to AI logs.  
```
    "containerEnv": {
        "CODEGEN_AGENT_STATE": "/workspaces/${localWorkspaceFolderBasename}/codegen_agent_state"
    },

```
