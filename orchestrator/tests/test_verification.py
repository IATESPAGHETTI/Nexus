"""Recovery verification must be decided by a live latency+failure probe.

Regression for a real bug: a db_slowdown incident was marked RESOLVED after a
restart that changed nothing, because verification only checked the metrics
error RATE and a latency-only fault has zero errors.
"""

import asyncio
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import recovery  # noqa: E402


class _Resp:
    def __init__(self, status=200):
        self.status_code = status


def _clock(step_ms):
    """Deterministic perf_counter: each call advances by step_ms/2 so every
    request (two calls) measures exactly step_ms."""
    t = [0.0]

    def now():
        t[0] += step_ms / 2000.0
        return t[0]

    return now


def test_probe_healthy_service_passes():
    result = recovery._probe_service(get=lambda url, timeout: _Resp(200), now=_clock(1.5))
    assert result["healthy"] is True
    assert all(p["median_ms"] < recovery.VERIFICATION_LATENCY_MS for p in result["per_path"].values())


def test_probe_slow_but_error_free_service_fails():
    # the exact db_slowdown shape: every request succeeds, every request is ~260ms
    result = recovery._probe_service(get=lambda url, timeout: _Resp(200), now=_clock(260))
    assert result["healthy"] is False
    assert result["per_path"]["/orders"]["failures"] == 0


def test_probe_failing_service_fails():
    result = recovery._probe_service(get=lambda url, timeout: _Resp(500), now=_clock(1.5))
    assert result["healthy"] is False


def test_probe_unreachable_service_fails():
    def boom(url, timeout):
        raise httpx.ConnectError("down")

    assert recovery._probe_service(get=boom, now=_clock(1.5))["healthy"] is False


def test_verify_is_not_passed_by_a_zero_error_rate_when_probe_is_unhealthy(monkeypatch):
    """The false-RESOLVED bug: metrics agent says error_rate 0.0, service is slow."""
    monkeypatch.setattr(recovery, "_probe_service", lambda: {"healthy": False, "per_path": {}})

    async def fake_call(*a, **k):
        return {"response": {"evidence": [{"result": {"error_rate": 0.0}}]}, "task_id": "t", "context_id": "c"}

    monkeypatch.setattr(recovery, "call_remote_agent", fake_call)
    result = asyncio.run(recovery._verify_recovery("INC-x"))
    assert result["verified"] is False
    assert result["error_rate"] == 0.0


def test_verify_survives_model_outage_and_still_uses_probe(monkeypatch):
    monkeypatch.setattr(recovery, "_probe_service", lambda: {"healthy": True, "per_path": {}})

    async def broken(*a, **k):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(recovery, "call_remote_agent", broken)
    result = asyncio.run(recovery._verify_recovery("INC-x"))
    assert result["verified"] is True
