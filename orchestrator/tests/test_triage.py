import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import triage  # noqa: E402

ALL = ["metrics_agent", "logs_traces_agent", "change_analysis_agent", "database_agent"]


def test_slow_report_skips_change_analysis():
    sel, skipped = triage.select_agents("Customers report that order requests are responding slowly.", ALL)
    assert "change_analysis_agent" not in sel
    assert {"metrics_agent", "database_agent"} <= set(sel)
    assert [s["agent"] for s in skipped] == ["change_analysis_agent"]
    assert skipped[0]["reason"]


def test_sudden_errors_include_change_analysis_and_skip_database():
    sel, skipped = triage.select_agents("Orders suddenly started failing with errors.", ALL)
    assert "change_analysis_agent" in sel and "database_agent" not in sel


def test_vague_report_still_gets_two_viewpoints():
    sel, _ = triage.select_agents("Something feels off.", ALL)
    assert len(sel) >= 2 and "metrics_agent" in sel


def test_follow_up_only_asks_the_pointed_at_agents():
    sel, skipped = triage.select_agents("Check recent deployments and configuration history.", ALL, first_round=False)
    assert sel == ["change_analysis_agent"]
    assert len(skipped) == 3


def test_follow_up_with_no_pointer_asks_everyone():
    sel, skipped = triage.select_agents("Need something else entirely.", ALL, first_round=False)
    assert sel == ALL and skipped == []
