"""File-based kill switch (root CLAUDE.md section 20).

A sentinel file, not an env var: `guardrails/executor.py` calls `is_engaged()`
live before EVERY single action (not once per plan), so the switch can be
flipped mid-execution -- e.g. during a demo, `python guardrails/kill_switch.py
engage` (run from repo root, same venv as orchestrator/) while a recovery
plan is executing will stop it before its next action. `.kill_switch` is
gitignored (see repo `.gitignore`); its mere existence is the signal, contents
are unused.
"""

from __future__ import annotations

import sys

from config import KILL_SWITCH_PATH


def is_engaged() -> bool:
    return KILL_SWITCH_PATH.exists()


def engage(reason: str = "") -> None:
    KILL_SWITCH_PATH.parent.mkdir(parents=True, exist_ok=True)
    KILL_SWITCH_PATH.write_text(reason or "kill switch engaged", encoding="utf-8")


def disengage() -> None:
    if KILL_SWITCH_PATH.exists():
        KILL_SWITCH_PATH.unlink()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "engage":
        engage(" ".join(sys.argv[2:]))
        print("kill switch ENGAGED")
    elif cmd == "disengage":
        disengage()
        print("kill switch disengaged")
    elif cmd == "status":
        print("ENGAGED" if is_engaged() else "clear")
    else:
        print("usage: python -m guardrails.kill_switch [engage|disengage|status]")
        sys.exit(1)
