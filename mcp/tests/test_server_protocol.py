"""Real MCP protocol integration test.

Launches mcp/server.py as a subprocess over stdio and talks to it through an
actual mcp.ClientSession — i.e. real JSON-RPC over the Model Context Protocol,
not a direct Python function call. This is what proves the tools are genuine
MCP tools (per root CLAUDE.md 2.1: "not mocked function labels"), distinct from
test_tools.py's unit tests of the underlying logic.

Requires the Phase 2 simulated production service running and reachable at
PRODUCTION_BASE_URL (default http://localhost:8001).

Run with the isolated mcp venv:
    .venv-mcp/Scripts/python -m pytest mcp/tests/test_server_protocol.py -q
"""

import sys
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

MCP_DIR = Path(__file__).resolve().parents[1]
SERVER_SCRIPT = MCP_DIR / "server.py"


def _server_params() -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
        cwd=str(MCP_DIR),
    )


@pytest.mark.asyncio
async def test_lists_all_seven_tools():
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            names = {t.name for t in result.tools}
            assert names == {
                "get_metrics",
                "query_logs",
                "get_trace",
                "get_recent_deployments",
                "get_git_diff",
                "get_database_stats",
                "run_diagnostic",
            }


@pytest.mark.asyncio
async def test_call_get_metrics_over_protocol():
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_metrics", {})
            assert result.is_error is not True
            assert result.structured_content["ok"] is True
            assert "request_count" in result.structured_content


@pytest.mark.asyncio
async def test_call_run_diagnostic_over_protocol():
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "run_diagnostic", {"name": "connectivity_check"}
            )
            assert result.structured_content["ok"] is True
            assert result.structured_content["reachable"] is True


@pytest.mark.asyncio
async def test_call_run_diagnostic_rejects_unknown_name_over_protocol():
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "run_diagnostic", {"name": "not_a_real_diagnostic"}
            )
            assert result.structured_content["ok"] is False


@pytest.mark.asyncio
async def test_call_get_git_diff_rejects_bad_path_over_protocol():
    async with stdio_client(_server_params()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "get_git_diff", {"paths": ["../../etc"]}
            )
            assert result.structured_content["ok"] is False
