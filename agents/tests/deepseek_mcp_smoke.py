"""One-shot REAL DeepSeek -> ADK -> LiteLLM -> MCP -> Finding smoke test.

This is intentionally NOT a mocked test. It makes one real DeepSeek API call
through ADK's LiteLlm bridge, and the metrics agent then makes a real MCP
`get_metrics` tool call (stdio to mcp/server.py) that itself performs a real
HTTP request to the running production service.

Run manually with the agents venv while production/ is reachable:

    .venv-agents/Scripts/python agents/tests/deepseek_mcp_smoke.py

Requires:
  - DEEPSEEK_API_KEY in repo-root .env
  - production/ reachable at http://localhost:8001
  - .venv-mcp/ present (agents/common/mcp_connection.py launches mcp/server.py
    with that isolated interpreter)

Exit code 0 = pass, 1 = fail. Never prints the API key.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

import agents.metrics.agent as metrics_agent_mod  # noqa: E402
from runtime_config import litellm_model_name, resolve_runtime_config  # noqa: E402


def main() -> int:
    provider, model = resolve_runtime_config()
    print(f"resolved provider: {provider}")
    print(f"resolved model: {model}")
    print(f"litellm model string: {litellm_model_name()}")

    finding = asyncio.run(metrics_agent_mod.investigate())

    evidence = finding.get("evidence") or []
    tools = [item.get("tool") for item in evidence]
    tool_oks = [
        bool(item.get("result", {}).get("ok"))
        for item in evidence
        if isinstance(item.get("result"), dict)
    ]

    print(f"finding_id: {finding.get('finding_id')}")
    print(f"evidence tools: {tools}")
    print(f"evidence ok flags: {tool_oks}")
    print(f"interpretation: {finding.get('interpretation', '')[:400]!r}")

    success = (
        provider == "deepseek"
        and model == "deepseek-chat"
        and litellm_model_name() == "deepseek/deepseek-chat"
        and "get_metrics" in tools
        and any(tool_oks)
        and isinstance(finding.get("finding_id"), str)
        and finding["finding_id"].startswith("find-")
        and bool(finding.get("interpretation"))
    )

    print("SMOKE RESULT:", "PASS" if success else "FAIL")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
