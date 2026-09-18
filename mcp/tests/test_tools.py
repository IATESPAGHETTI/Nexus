"""Unit tests for the 7 MCP diagnostic tools (mcp/tools.py).

Requires the Phase 2 simulated production service running and reachable at
PRODUCTION_BASE_URL (default http://localhost:8001) — these tools genuinely call
it over HTTP, nothing here is mocked. Start it with:

    uvicorn service:app --port 8001   (from production/, using its own venv)
    or: docker compose up -d production

Run with the isolated mcp venv:
    .venv-mcp/Scripts/python -m pytest mcp/tests -q
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tools  # noqa: E402


def test_get_metrics():
    result = tools.get_metrics()
    assert result["ok"] is True
    assert "request_count" in result
    assert "by_endpoint" in result


def test_query_logs_default():
    result = tools.query_logs()
    assert result["ok"] is True
    assert isinstance(result["entries"], list)
    assert result["count"] == len(result["entries"])


def test_query_logs_filters_by_level():
    result = tools.query_logs(level="ERROR", limit=50)
    assert result["ok"] is True
    assert all(e["level"] == "ERROR" for e in result["entries"])


def test_query_logs_rejects_bad_level():
    result = tools.query_logs(level="VERBOSE")
    assert result["ok"] is False
    assert "level" in result["error"]


def test_get_trace_recent():
    tools.query_logs()  # generate at least one request/trace first
    result = tools.get_trace()
    assert result["ok"] is True
    assert isinstance(result["traces"], list)


def test_get_trace_not_found():
    result = tools.get_trace(trace_id="does-not-exist")
    assert result["ok"] is False
    assert "error" in result


def test_get_trace_roundtrip():
    recent = tools.get_trace()
    assert recent["traces"], "expected at least one trace to exist by now"
    trace_id = recent["traces"][0]["trace_id"]
    result = tools.get_trace(trace_id=trace_id)
    assert result["ok"] is True
    assert result["trace"]["trace_id"] == trace_id


def test_get_recent_deployments():
    result = tools.get_recent_deployments(limit=2)
    assert result["ok"] is True
    assert len(result["changes"]) <= 2


def test_get_database_stats():
    result = tools.get_database_stats()
    assert result["ok"] is True
    assert result["table_row_counts"]["orders"] == 10


def test_run_diagnostic_connectivity():
    result = tools.run_diagnostic(name="connectivity_check")
    assert result["ok"] is True
    assert result["reachable"] is True


def test_run_diagnostic_error_rate():
    result = tools.run_diagnostic(name="error_rate_check")
    assert result["ok"] is True
    assert 0.0 <= result["error_rate"] <= 1.0


def test_run_diagnostic_order_status():
    result = tools.run_diagnostic(name="order_status_check")
    assert result["ok"] is True
    assert sum(result["orders_by_status"].values()) == 10


def test_run_diagnostic_rejects_unknown_name():
    result = tools.run_diagnostic(name="drop_all_tables")
    assert result["ok"] is False
    assert "error" in result


def test_get_git_diff_default_paths():
    result = tools.get_git_diff()
    assert result["ok"] is True
    assert "commit_history_available" in result
    assert "uncommitted_changes_stat" in result


def test_get_git_diff_rejects_disallowed_path():
    result = tools.get_git_diff(paths=["../../etc"])
    assert result["ok"] is False
    assert "allowed path list" in result["error"]


def test_get_git_diff_rejects_out_of_scope_top_level_dir():
    result = tools.get_git_diff(paths=["agents"])
    assert result["ok"] is False
