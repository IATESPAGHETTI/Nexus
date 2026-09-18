import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import audit  # noqa: E402
import tools  # noqa: E402


def test_tool_calls_are_recorded_in_audit_log():
    audit.clear()
    tools.run_diagnostic(name="connectivity_check")
    tools.run_diagnostic(name="not_a_real_diagnostic")

    entries = audit.recent()
    assert len(entries) == 2
    # most recent first
    assert entries[0]["tool"] == "run_diagnostic"
    assert entries[0]["ok"] is False
    assert entries[0]["error"] is not None
    assert entries[1]["ok"] is True
    assert entries[1]["error"] is None
    assert all("duration_ms" in e and "timestamp" in e for e in entries)
