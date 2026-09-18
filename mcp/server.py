"""NEXUS MCP diagnostic server (Phase 3).

Exposes the 7 diagnostic tools defined in tools.py over the real Model Context
Protocol (stdio transport by default). Run standalone for manual testing:

    .venv-mcp/Scripts/python mcp/server.py

Agents (Phase 4+) will connect to this as an MCP client (e.g. ADK's MCPToolset)
rather than importing tools.py directly.
"""

from mcp.server.mcpserver import MCPServer

import tools

mcp_server = MCPServer(name="nexus-diagnostics")

mcp_server.tool(structured_output=True)(tools.get_metrics)
mcp_server.tool(structured_output=True)(tools.query_logs)
mcp_server.tool(structured_output=True)(tools.get_trace)
mcp_server.tool(structured_output=True)(tools.get_recent_deployments)
mcp_server.tool(structured_output=True)(tools.get_git_diff)
mcp_server.tool(structured_output=True)(tools.get_database_stats)
mcp_server.tool(structured_output=True)(tools.run_diagnostic)


if __name__ == "__main__":
    mcp_server.run(transport="stdio")
