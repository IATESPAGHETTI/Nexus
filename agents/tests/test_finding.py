"""Unit tests for agents/common/finding.py — pure logic, no LLM/network calls."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

from finding import build_finding, make_evidence_item  # noqa: E402


def test_evidence_item_has_unique_id_and_timestamp():
    item = make_evidence_item("get_metrics", {}, {"ok": True, "request_count": 5})
    assert item["evidence_id"].startswith("ev-")
    assert item["tool"] == "get_metrics"
    assert item["result"]["request_count"] == 5
    assert "timestamp" in item


def test_build_finding_parses_confidence_line():
    evidence = [make_evidence_item("get_metrics", {}, {"ok": True})]
    finding = build_finding(
        "metrics_agent", evidence, "Everything looks fine.\nCONFIDENCE: 0.87"
    )
    assert finding["confidence"] == 0.87
    assert "CONFIDENCE" not in finding["interpretation"]
    assert finding["interpretation"] == "Everything looks fine."
    assert finding["limitations"] == "none noted"


def test_build_finding_parses_markdown_bold_confidence_line():
    # Real model output observed during Phase 5 testing: "**CONFIDENCE:** 0.68"
    # instead of the plain "CONFIDENCE: 0.68" form.
    evidence = [make_evidence_item("get_git_diff", {}, {"ok": True})]
    finding = build_finding(
        "change_analysis_agent",
        evidence,
        "The most recent change looks unrelated to this failure.\n\n**CONFIDENCE:** 0.68",
    )
    assert finding["confidence"] == 0.68
    assert "CONFIDENCE" not in finding["interpretation"]
    assert finding["interpretation"] == "The most recent change looks unrelated to this failure."


def test_build_finding_defaults_confidence_when_missing():
    evidence = [make_evidence_item("get_metrics", {}, {"ok": True})]
    finding = build_finding("metrics_agent", evidence, "Everything looks fine, no number given.")
    assert finding["confidence"] == 0.3
    assert "did not report a parseable CONFIDENCE" in finding["limitations"]


def test_build_finding_clamps_out_of_range_confidence():
    evidence = [make_evidence_item("get_metrics", {}, {"ok": True})]
    finding = build_finding("metrics_agent", evidence, "text\nCONFIDENCE: 1.0")
    assert finding["confidence"] == 1.0


def test_build_finding_notes_empty_evidence():
    finding = build_finding("metrics_agent", [], "No tools were called.\nCONFIDENCE: 0.1")
    assert "no MCP tool evidence" in finding["limitations"]
    assert finding["observation"] == "No MCP tool call succeeded; no evidence was gathered."


def test_build_finding_notes_failed_tool_call():
    evidence = [make_evidence_item("get_trace", {"trace_id": "x"}, {"ok": False, "error": "not found"})]
    finding = build_finding("logs_traces_agent", evidence, "The trace was not found.\nCONFIDENCE: 0.9")
    assert "ok=False" in finding["limitations"]


def test_build_finding_schema_shape():
    evidence = [make_evidence_item("get_database_stats", {}, {"ok": True, "table_row_counts": {}})]
    finding = build_finding("database_agent", evidence, "DB looks fine.\nCONFIDENCE: 0.5")
    required_keys = {
        "finding_id",
        "agent",
        "observation",
        "source",
        "window",
        "evidence",
        "interpretation",
        "confidence",
        "limitations",
    }
    assert required_keys.issubset(finding.keys())
    assert finding["source"] == "database_agent"
    assert set(finding["window"].keys()) == {"start", "end"}
