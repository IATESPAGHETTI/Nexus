"""backend/app/demo.py start_agents (the dashboard's agent ON switch): launches only
the fixed allowlisted scripts, skips agents already up, never double-spawns one that
is still booting. Popen and the reachability probe are faked -- nothing is started."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app import demo  # noqa: E402


def _fake(monkeypatch, up):
    launched = []
    monkeypatch.setattr(demo, "check_agents", lambda: {n: n in up for n in demo.AGENT_PORTS})
    monkeypatch.setattr(demo.subprocess, "Popen", lambda cmd, **kw: launched.append(cmd[1]))
    monkeypatch.setattr(demo, "_spawned_at", {})
    # The real agents venv only exists on a developer machine, not on a CI runner.
    monkeypatch.setattr(demo, "AGENTS_PYTHON", Path(sys.executable))
    return launched


def test_starts_only_agents_that_are_down(monkeypatch):
    launched = _fake(monkeypatch, up={"metrics_agent", "evidence_agent"})
    result = demo.start_agents()
    assert sorted(result["already_running"]) == ["evidence_agent", "metrics_agent"]
    assert len(result["started"]) == 5 and not result["failed"]
    assert len(launched) == 5
    assert all(Path(s).name == "a2a_service.py" for s in launched)


def test_does_not_respawn_an_agent_that_is_still_booting(monkeypatch):
    launched = _fake(monkeypatch, up=set())
    demo.start_agents()
    first = len(launched)
    demo.start_agents()  # second click while they are still booting
    assert first == 7 and len(launched) == 7


def test_every_script_is_a_real_file_in_the_repo():
    for script in demo.AGENT_SCRIPTS.values():
        assert (demo.REPO_ROOT / script).is_file(), script


def test_stop_only_kills_agents_this_backend_started(monkeypatch):
    class _Proc:
        def __init__(self, pid):
            self.pid = pid

        def poll(self):
            return None

    killed = []
    monkeypatch.setattr(demo, "_kill_tree", lambda proc: killed.append(proc.pid))
    monkeypatch.setattr(demo, "_spawned_procs", {"metrics_agent": _Proc(11), "evidence_agent": _Proc(22)})
    monkeypatch.setattr(demo, "_spawned_at", {"metrics_agent": 1.0, "evidence_agent": 1.0})
    monkeypatch.setattr(demo, "check_agents", lambda: {"database_agent": True})  # started by hand elsewhere

    result = demo.stop_agents()

    assert sorted(killed) == [11, 22]
    assert sorted(result["stopped"]) == ["evidence_agent", "metrics_agent"]
    assert result["still_running"] == ["database_agent"]  # not ours: reported, never killed
    assert demo._spawned_procs == {}


def test_an_agent_that_died_right_after_launch_is_relaunched_without_waiting_out_the_grace_period(monkeypatch):
    class _Dead:
        def poll(self):
            return 1

    launched = _fake(monkeypatch, up=set())
    monkeypatch.setattr(demo, "_spawned_procs", {"metrics_agent": _Dead()})
    monkeypatch.setattr(demo, "_spawned_at", {"metrics_agent": time.monotonic()})  # "just launched"

    demo.start_agents()

    assert any("metrics" in cmd for cmd in launched)
