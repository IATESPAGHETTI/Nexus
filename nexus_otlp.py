"""OpenTelemetry (OTLP/HTTP JSON) export of a finished investigation's trace (course requirement 9).

Converts the stored span tree (`nexus_trace.build_trace`) into the standard OTLP JSON payload and POSTs it to a collector or
Jaeger when NEXUS_OTLP_ENDPOINT is set (for example http://jaeger:4318/v1/traces). Speaking the protocol directly (it is plain
JSON over HTTP) avoids adding the OpenTelemetry SDK, whose version pins conflict with the ADK stack's.

Each agent becomes its OWN service in the trace (service.name = the agent), the orchestrator is `nexus-orchestrator`, so a trace
viewer shows a genuine cross-service trace: orchestrator -> A2A call -> agent -> model / tool calls. The trace id is the one
that travelled over the wire as a W3C traceparent header.

Honest limits: span times are reconstructed (root from created_at/updated_at in whole seconds, agents from their own clock
readings, inner calls from recorded durations laid out in order), so they are accurate to roughly a second for the root and to
the millisecond only for durations. Export is best-effort and never changes an investigation's outcome.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Any
from urllib.parse import urlparse

SPAN_KIND = {"incident": 1, "a2a_call": 3, "agent": 2}   # INTERNAL, CLIENT, SERVER (everything else INTERNAL)
SCOPE = {"name": "nexus", "version": "1.0"}


def _attr(key: str, value: Any) -> dict | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return {"key": key, "value": {"boolValue": value}}
    if isinstance(value, int):
        return {"key": key, "value": {"intValue": str(value)}}
    if isinstance(value, float):
        return {"key": key, "value": {"doubleValue": value}}
    return {"key": key, "value": {"stringValue": str(value)[:300]}}


# Estimated list prices in USD per million tokens. Same assumption as evaluation/matrix.py (a deepseek-flash peak price): the
# provider is NOT billing this. On a free tier the real cost is $0. Override with NEXUS_PRICE_IN_PER_M / NEXUS_PRICE_OUT_PER_M.
DEFAULT_PRICE_IN_PER_M = 0.30
DEFAULT_PRICE_OUT_PER_M = 1.20


def _price(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


def model_name(incident: dict) -> str:
    """The model that produced the run: stored in run_config, else the current setting, else the provider name."""
    cfg = incident.get("run_config") or {}
    return str(cfg.get("model") or os.environ.get("NEXUS_LLM_MODEL") or cfg.get("llm") or "unknown")


def generation_attrs(span: dict, model: str) -> list[dict]:
    """Langfuse 'generation' fields for one model call: model, token usage and an ESTIMATED cost (see DEFAULT_PRICE_*)."""
    if span.get("kind") != "model_call_finished":
        return []
    n_in, n_out = int(span.get("prompt_tokens") or 0), int(span.get("completion_tokens") or 0)
    price_in, price_out = _price("NEXUS_PRICE_IN_PER_M", DEFAULT_PRICE_IN_PER_M), _price("NEXUS_PRICE_OUT_PER_M", DEFAULT_PRICE_OUT_PER_M)
    cost_in, cost_out = n_in / 1e6 * price_in, n_out / 1e6 * price_out
    usage = {"input": n_in, "output": n_out, "total": n_in + n_out}
    cost = {"input": round(cost_in, 8), "output": round(cost_out, 8), "total": round(cost_in + cost_out, 8)}
    pairs = [
        ("langfuse.observation.type", "generation"), ("gen_ai.request.model", model),
        ("langfuse.observation.usage_details", json.dumps(usage)), ("langfuse.observation.cost_details", json.dumps(cost)),
        ("nexus.cost_basis", f"estimated at ${price_in}/M input and ${price_out}/M output tokens (list-price assumption, not billed)"),
    ]
    return [a for a in (_attr(k, v) for k, v in pairs) if a]


def _attrs(span: dict, incident_id: str, model: str = "unknown") -> list[dict]:
    pairs = [
        ("nexus.incident_id", incident_id), ("nexus.kind", span.get("kind")), ("nexus.time_estimated", True),
        ("nexus.a2a_task_id", span.get("a2a_task_id")), ("nexus.a2a_context_id", span.get("a2a_context_id")),
        ("nexus.prompt_variant", span.get("prompt_variant")), ("nexus.prompt_tokens", span.get("prompt_tokens")),
        ("nexus.completion_tokens", span.get("completion_tokens")), ("nexus.tool_ok", span.get("ok")),
        ("nexus.error_type", span.get("error_type")), ("nexus.trace_id_seen_by_agent", span.get("trace_id_seen_by_agent")),
    ]
    return [a for a in (_attr(k, v) for k, v in pairs) if a] + generation_attrs(span, model)


def _service_of(span: dict, parents: dict[str, dict]) -> str:
    """Service a span belongs to: the nearest agent ancestor (or itself), else the orchestrator."""
    cur = span
    for _ in range(6):
        if cur.get("kind") == "agent":
            return cur["name"].replace("agent ", "", 1)
        parent = parents.get(cur.get("parent_span_id") or "")
        if parent is None:
            break
        cur = parent
    return "nexus-orchestrator"


def to_otlp(trace: dict, incident: dict) -> dict:
    """OTLP/HTTP JSON payload (`{"resourceSpans": [...]}`) for one incident's trace."""
    trace_id = trace.get("trace_id") or ""
    spans = trace.get("spans") or []
    if len(trace_id) != 32 or not spans:
        return {"resourceSpans": []}
    incident_id = str(incident.get("incident_id", ""))
    model = model_name(incident)
    by_id = {s["span_id"]: s for s in spans}
    root = spans[0]
    root_start = root.get("start_unix_s")
    if root_start is None:
        return {"resourceSpans": []}

    def start_ms(s: dict) -> float:
        for key in ("abs_offset_ms", "offset_ms"):
            if s.get("kind") != "incident" and key == "offset_ms" and s.get("parent_span_id") and by_id.get(s["parent_span_id"], {}).get("kind") == "agent":
                continue    # an inner span's offset_ms is relative to its agent, not to the root
            if isinstance(s.get(key), (int, float)):
                return float(s[key])
        parent = by_id.get(s.get("parent_span_id") or "")
        return start_ms(parent) if parent else 0.0

    per_service: dict[str, list[dict]] = {}
    for s in spans:
        start = root_start * 1000 + start_ms(s)
        duration = s.get("duration_ms") if isinstance(s.get("duration_ms"), (int, float)) else 0
        failed = bool(s.get("errors")) or s.get("ok") is False or s.get("kind") in ("tool_error", "model_error")
        otlp_span = {
            "traceId": trace_id, "spanId": s["span_id"],
            "parentSpanId": s.get("parent_span_id") if s.get("parent_span_id") in by_id else "",
            "name": s.get("name", s.get("kind", "span")), "kind": SPAN_KIND.get(s.get("kind"), 1),
            "startTimeUnixNano": str(int(start * 1_000_000)), "endTimeUnixNano": str(int((start + duration) * 1_000_000)),
            "attributes": _attrs(s, incident_id, model), "status": {"code": 2 if failed else 1},
        }
        per_service.setdefault(_service_of(s, by_id), []).append(otlp_span)

    return {"resourceSpans": [
        {"resource": {"attributes": [_attr("service.name", service), _attr("nexus.incident_id", incident_id)]},
         "scopeSpans": [{"scope": SCOPE, "spans": batch}]}
        for service, batch in sorted(per_service.items())
    ]}


def endpoint() -> str:
    return os.environ.get("NEXUS_OTLP_ENDPOINT", "").strip()


def headers(url: str | None = None) -> dict[str, str]:
    """Extra HTTP headers for the export (values are secrets: never log them).

    NEXUS_OTLP_HEADERS uses the OpenTelemetry convention `Key=Value,Key2=Value2`. For Langfuse Cloud, setting
    LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY is enough: the Basic auth header is built from them, and ONLY when the
    endpoint's host is a langfuse.com host, so the keys are never sent to any other collector.
    """
    out: dict[str, str] = {}
    for item in os.environ.get("NEXUS_OTLP_HEADERS", "").split(","):
        key, sep, value = item.partition("=")
        if sep and key.strip():
            out[key.strip()] = value.strip()
    host = urlparse(url if url is not None else endpoint()).hostname or ""
    public, secret = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip(), os.environ.get("LANGFUSE_SECRET_KEY", "").strip()
    if public and secret and (host == "langfuse.com" or host.endswith(".langfuse.com")) and "Authorization" not in out:
        out["Authorization"] = "Basic " + base64.b64encode(f"{public}:{secret}".encode()).decode()
        out.setdefault("x-langfuse-ingestion-version", "4")
    return out


def export(trace: dict, incident: dict, timeout: float = 5.0) -> dict:
    """POST the trace to NEXUS_OTLP_ENDPOINT. Returns {"exported": bool, ...}; never raises."""
    url = endpoint()
    if not url:
        return {"exported": False, "reason": "NEXUS_OTLP_ENDPOINT is not set"}
    payload = to_otlp(trace, incident)
    if not payload["resourceSpans"]:
        return {"exported": False, "reason": "no exportable spans"}
    try:
        import httpx

        response = httpx.post(url, json=payload, headers=headers(url), timeout=timeout)
        ok = response.status_code < 300
        return {"exported": ok, "status": response.status_code, "span_count": sum(len(s["spans"]) for r in payload["resourceSpans"] for s in r["scopeSpans"])}
    except Exception as exc:  # noqa: BLE001 -- tracing must never break an investigation
        return {"exported": False, "reason": f"{type(exc).__name__}"}
