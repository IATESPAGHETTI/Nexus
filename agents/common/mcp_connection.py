"""Connection params for reaching the real Phase 3 MCP server from an ADK agent.

Agents never import mcp/tools.py directly and never talk to production/ HTTP
endpoints themselves — they only get evidence through the actual MCP server
(mcp/server.py) over the real Model Context Protocol (stdio), launched with ITS
OWN isolated interpreter/dependencies (.venv-mcp/), not the agents/ venv. This
keeps the Phase 3 MCP layer as a standalone, independently-versioned service that
agents merely connect to, matching root CLAUDE.md's dependency isolation rule.
"""

import os
from pathlib import Path

from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

REPO_ROOT = Path(__file__).resolve().parents[2]
MCP_DIR = REPO_ROOT / "mcp"

if (REPO_ROOT / ".venv-mcp" / "Scripts" / "python.exe").exists():
    MCP_SERVER_PYTHON = REPO_ROOT / ".venv-mcp" / "Scripts" / "python.exe"  # Windows
else:
    MCP_SERVER_PYTHON = REPO_ROOT / ".venv-mcp" / "bin" / "python"  # POSIX

MCP_SERVER_SCRIPT = MCP_DIR / "server.py"

# Containers have one interpreter that holds the MCP dependencies: NEXUS_MCP_PYTHON (a command name or a path)
# replaces the local .venv-mcp lookup. Unset = unchanged local behaviour.
_MCP_PYTHON_OVERRIDE = os.environ.get("NEXUS_MCP_PYTHON")
if _MCP_PYTHON_OVERRIDE:
    MCP_SERVER_PYTHON = Path(_MCP_PYTHON_OVERRIDE)

MCP_CONNECT_TIMEOUT_SECONDS = 15.0

# The MCP SDK starts the tool server with a MINIMAL environment (PATH, HOME, ...), not ours. Settings the tool
# server needs must be passed explicitly or it silently falls back to its local defaults (e.g. 127.0.0.1:8001,
# which is wrong inside a container).
_PASSTHROUGH_ENV = ("PRODUCTION_BASE_URL", "NEXUS_ENABLE_GIT_DIFF")


def mcp_server_env() -> dict[str, str]:
    return {k: os.environ[k] for k in _PASSTHROUGH_ENV if os.environ.get(k)}


def mcp_server_connection_params() -> StdioConnectionParams:
    if not _MCP_PYTHON_OVERRIDE and not MCP_SERVER_PYTHON.exists():
        raise RuntimeError(
            f"MCP server interpreter not found at {MCP_SERVER_PYTHON}. "
            "Create it first: python -m venv .venv-mcp && "
            ".venv-mcp/Scripts/python -m pip install -r mcp/requirements.txt"
        )
    return StdioConnectionParams(
        server_params=StdioServerParameters(
            command=str(MCP_SERVER_PYTHON),
            args=[str(MCP_SERVER_SCRIPT)],
            cwd=str(MCP_DIR),
            env=mcp_server_env(),
        ),
        timeout=MCP_CONNECT_TIMEOUT_SECONDS,
    )
