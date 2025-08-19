# Determines the path for storing state and look for API keys.

import os
from pathlib import Path
from platformdirs import PlatformDirs
from dotenv import load_dotenv


# -------------------------------------------------
# PC specific path for standalone installation
# -------------------------------------------------
def _state_path() -> Path:
    # Linux: ~/.local/state/codegen_agent/
    # Windows: %LOCALAPPDATA%\codegen_agent\State\
    # Devcontainer override: CODEGEN_AGENT_STATE=/workspaces/codegen_agent/state (or any path)

    # First, try to load dotenv from common locations to get potential CODEGEN_AGENT_STATE override
    potential_dotenv_paths = [
        Path.cwd() / ".env",  # Current working directory
        Path.home() / ".env",  # User home directory
        Path("/secrets") / "codegen_agent" / ".env",  # Common devcontainer path
    ]

    # Also check if explicit override is set
    if override_path := os.environ.get("CODEGEN_AGENT_DOTENV_PATH"):
        potential_dotenv_paths.insert(0, Path(override_path))

    # Load dotenv from first available location (without overriding existing env vars)
    for dotenv_path in potential_dotenv_paths:
        if dotenv_path.is_file():
            load_dotenv(dotenv_path, override=False)
            break

    # Now check for state path override after dotenv is loaded
    if state_override := os.environ.get("CODEGEN_AGENT_STATE"):
        found_path = Path(state_override).expanduser().resolve()
    else:
        d = PlatformDirs(appname="codegen_agent")
        found_path = Path(d.user_state_dir)  # single root, portable

    # try to load dotenv
    if (found_path / ".env").is_file():
        # this should load LLM key
        load_dotenv(found_path / ".env", override=False)

    return found_path


STATE_PATH = _state_path()
LOG_PATH = STATE_PATH / "logs"
CACHE_PATH = STATE_PATH / "cache"
GEN_CODES_PATH = STATE_PATH / "gen_codes"

for _p in (STATE_PATH, LOG_PATH, CACHE_PATH, GEN_CODES_PATH):
    _p.mkdir(exist_ok=True)
