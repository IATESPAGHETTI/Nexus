"""Connection params for reaching the real Phase 3 MCP server from an ADK agent.

Agents never import mcp/tools.py directly and never talk to production/ HTTP
endpoints themselves — they only get evidence through the actual MCP server
(mcp/server.py) over the real Model Context Protocol (stdio), launched with ITS
OWN isolated interpreter/dependencies (.venv-mcp/), not the agents/ venv. This
keeps the Phase 3 MCP layer as a standalone, independently-versioned service that
agents merely connect to, matching root CLAUDE.md's dependency isolation rule.
"""

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

MCP_CONNECT_TIMEOUT_SECONDS = 15.0


def mcp_server_connection_params() -> StdioConnectionParams:
    if not MCP_SERVER_PYTHON.exists():
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
        ),
        timeout=MCP_CONNECT_TIMEOUT_SECONDS,
    )
