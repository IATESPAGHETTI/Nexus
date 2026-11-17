"""nexus_trace timing + nexus_otlp export (pure, plus a throwaway local HTTP collector). No model, no real network."""
import http.server
import json
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nexus_otlp as otlp  # noqa: E402
import nexus_trace as nt  # noqa: E402

TRACE_ID = "a" * 32
INCIDENT = {"incident_id": "INC-1", "trace_id": TRACE_ID, "root_span_id": "1" * 16, "status": "DIAGNOSED",
            "created_at": "2026-10-18T10:00:00Z", "updated_at": "2026-10-18T10:00:30Z"}


def _monitor(agent, span, parent, started, records, errors=0):
    return {"event_type": "AGENT_MONITOR", "source": agent, "timestamp": "2026-10-18T10:00:30Z", "payload": {
        "agent": agent, "trace_id": TRACE_ID, "span_id": span, "parent_span_id": parent, "started_unix": started, "errors": errors,
        "records": records + [{"seq": 99, "kind": "agent_finished", "total_ms": 5000}]}}


EVENTS = [
    _monitor("metrics_agent", "2" * 16, "3" * 16, 1792317602.0, [   # 2 s after the incident started
        {"seq": 1, "kind": "model_call_finished", "duration_ms": 1000, "span_id": "4" * 16, "prompt_tokens": 50},
        {"seq": 2, "kind": "tool_call_finished", "tool": "get_metrics", "duration_ms": 100, "span_id": "5" * 16, "ok": True}]),
    _monitor("database_agent", "6" * 16, "7" * 16, 1792317612.0, [      # 12 s after: ran AFTER metrics (pipeline)
        {"seq": 1, "kind": "tool_error", "tool": "x", "duration_ms": 10, "span_id": "8" * 16, "error_type": "RuntimeError"}], errors=1),
]
ROOT_START = nt._epoch(INCIDENT["created_at"])


def test_agent_placement_uses_the_agents_own_clock_not_the_event_time():
    tr = nt.build_trace(INCIDENT, EVENTS)
    by_name = {s["name"]: s for s in tr["spans"]}
    assert by_name["agent metrics_agent"]["offset_ms"] == round((1792317602.0 - ROOT_START) * 1000)
    assert by_name["agent database_agent"]["offset_ms"] - by_name["agent metrics_agent"]["offset_ms"] == 10000   # sequential, not simultaneous
    assert by_name["incident INC-1"]["duration_ms"] == 30000
    inner = [s for s in tr["spans"] if s["parent_span_id"] == "2" * 16]
    assert inner[1]["abs_offset_ms"] == by_name["agent metrics_agent"]["offset_ms"] + 1000       # laid out in order after the model call


def test_without_a_clock_reading_it_falls_back_to_event_time_minus_duration():
    ev = json.loads(json.dumps(EVENTS))
    del ev[0]["payload"]["started_unix"]
    span = next(s for s in nt.build_trace(INCIDENT, ev)["spans"] if s["name"] == "agent metrics_agent")
    assert span["offset_ms"] == 30000 - 5000


def test_otlp_payload_is_structurally_valid_and_one_service_per_agent():
    payload = otlp.to_otlp(nt.build_trace(INCIDENT, EVENTS), INCIDENT)
    services = {next(a["value"]["stringValue"] for a in r["resource"]["attributes"] if a["key"] == "service.name"): r for r in payload["resourceSpans"]}
    assert set(services) == {"nexus-orchestrator", "metrics_agent", "database_agent"}
    spans = [s for r in payload["resourceSpans"] for sc in r["scopeSpans"] for s in sc["spans"]]
    ids = {s["spanId"] for s in spans}
    for s in spans:
        assert s["traceId"] == TRACE_ID and len(s["spanId"]) == 16
        assert int(s["endTimeUnixNano"]) >= int(s["startTimeUnixNano"])
        assert s["parentSpanId"] == "" or s["parentSpanId"] in ids                  # no dangling parents
    root = next(s for s in spans if s["parentSpanId"] == "")
    assert root["name"] == "incident INC-1" and root["kind"] == 1
    agent = next(s for s in spans if s["name"] == "agent metrics_agent")
    assert agent["kind"] == 2 and agent["status"]["code"] == 1
    failed = next(s for s in spans if s["name"] == "agent database_agent")
    assert failed["status"]["code"] == 2                                               # errors > 0 -> error status
    assert int(agent["startTimeUnixNano"]) // 1_000_000 == round(1792317602.0 * 1000)


def test_untraceable_input_exports_nothing():
    assert otlp.to_otlp({"trace_id": None, "spans": []}, INCIDENT) == {"resourceSpans": []}
    assert otlp.to_otlp({"trace_id": "short", "spans": [{"span_id": "x"}]}, INCIDENT) == {"resourceSpans": []}


def test_export_is_off_without_an_endpoint_and_never_raises(monkeypatch):
    monkeypatch.delenv("NEXUS_OTLP_ENDPOINT", raising=False)
    assert otlp.export(nt.build_trace(INCIDENT, EVENTS), INCIDENT)["exported"] is False
    monkeypatch.setenv("NEXUS_OTLP_ENDPOINT", "http://127.0.0.1:9/v1/traces")        # nothing listens there
    out = otlp.export(nt.build_trace(INCIDENT, EVENTS), INCIDENT, timeout=1)
    assert out["exported"] is False and "reason" in out


def test_export_posts_the_payload_to_a_collector(monkeypatch):
    received = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            received["path"] = self.path
            received["body"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("NEXUS_OTLP_ENDPOINT", f"http://127.0.0.1:{server.server_port}/v1/traces")
    try:
        out = otlp.export(nt.build_trace(INCIDENT, EVENTS), INCIDENT)
    finally:
        server.shutdown()
    assert out["exported"] is True and out["status"] == 200 and out["span_count"] >= 5
    assert received["path"] == "/v1/traces" and received["body"]["resourceSpans"]


def test_custom_headers_reach_the_collector(monkeypatch):
    received = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            received["auth"] = self.headers.get("Authorization")
            received["extra"] = self.headers.get("X-Team")
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("NEXUS_OTLP_ENDPOINT", f"http://127.0.0.1:{server.server_port}/v1/traces")
    monkeypatch.setenv("NEXUS_OTLP_HEADERS", "Authorization=Bearer test-token, X-Team=nexus")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    try:
        out = otlp.export(nt.build_trace(INCIDENT, EVENTS), INCIDENT)
    finally:
        server.shutdown()
    assert out["exported"] is True
    assert received == {"auth": "Bearer test-token", "extra": "nexus"}   # the explicit header, not the Langfuse keys


def test_langfuse_keys_are_only_sent_to_langfuse_hosts(monkeypatch):
    import base64

    monkeypatch.delenv("NEXUS_OTLP_HEADERS", raising=False)
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    lf = otlp.headers("https://cloud.langfuse.com/api/public/otel/v1/traces")
    assert lf["Authorization"] == "Basic " + base64.b64encode(b"pk-lf-test:sk-lf-test").decode()
    assert lf["x-langfuse-ingestion-version"] == "4"
    assert "Authorization" in otlp.headers("https://us.cloud.langfuse.com/api/public/otel/v1/traces")
    for other in ("http://jaeger:4318/v1/traces", "http://localhost:4318/v1/traces", "https://langfuse.com.evil.example/v1/traces",
                  "https://evil-langfuse.com/v1/traces"):
        assert otlp.headers(other) == {}, other


def test_no_keys_means_no_auth_header(monkeypatch):
    for name in ("NEXUS_OTLP_HEADERS", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert otlp.headers("https://cloud.langfuse.com/api/public/otel/v1/traces") == {}


def _attr_map(span_attrs):
    return {a["key"]: next(iter(a["value"].values())) for a in span_attrs}


def test_model_calls_become_generations_with_usage_and_an_estimated_cost(monkeypatch):
    monkeypatch.delenv("NEXUS_PRICE_IN_PER_M", raising=False)
    monkeypatch.delenv("NEXUS_PRICE_OUT_PER_M", raising=False)
    incident = dict(INCIDENT, run_config={"llm": "gemini", "model": "gemini-3.5-flash-lite"})
    payload = otlp.to_otlp(nt.build_trace(incident, EVENTS), incident)
    spans = [s for r in payload["resourceSpans"] for sc in r["scopeSpans"] for s in sc["spans"]]
    models = [s for s in spans if _attr_map(s["attributes"]).get("langfuse.observation.type") == "generation"]
    assert len(models) == 1                                         # only the one model call; tools and agents are plain spans
    a = _attr_map(models[0]["attributes"])
    assert a["gen_ai.request.model"] == "gemini-3.5-flash-lite"
    usage, cost = json.loads(a["langfuse.observation.usage_details"]), json.loads(a["langfuse.observation.cost_details"])
    assert usage == {"input": 50, "output": 0, "total": 50}
    assert cost["input"] == round(50 / 1e6 * 0.30, 8) and cost["total"] == cost["input"] + cost["output"]
    assert "not billed" in a["nexus.cost_basis"]


def test_prices_can_be_overridden_and_unknown_model_falls_back(monkeypatch):
    monkeypatch.setenv("NEXUS_PRICE_IN_PER_M", "1.0")
    monkeypatch.setenv("NEXUS_PRICE_OUT_PER_M", "2.0")
    monkeypatch.delenv("NEXUS_LLM_MODEL", raising=False)
    span = {"kind": "model_call_finished", "prompt_tokens": 1_000_000, "completion_tokens": 500_000}
    a = _attr_map(otlp.generation_attrs(span, otlp.model_name({"run_config": {"llm": "deepseek"}})))
    assert json.loads(a["langfuse.observation.cost_details"])["total"] == 2.0     # 1M x $1 + 0.5M x $2
    assert a["gen_ai.request.model"] == "deepseek"
    assert otlp.generation_attrs({"kind": "tool_call_finished"}, "m") == []
