"""Phase 10B: thin CLI entrypoint for the full Phase 6/8 investigation flow.

Not a new orchestration path -- calls the exact same `run_investigation()`
that `orchestrator/tests/test_investigation_e2e.py` already exercises. Exists
only so the end-to-end demo (docs/DEMO_RUNBOOK.md) has one command to run
instead of a hand-written `python -c` one-liner. Makes real Groq API calls
and real A2A network calls; requires production/backend/all 7 A2A services
already running (see docs/DEMO_RUNBOOK.md).

Usage:
    .venv-orchestrator/Scripts/python orchestrator/run_demo.py "orders endpoint returning 500s"
    .venv-orchestrator/Scripts/python orchestrator/run_demo.py --no-recovery "..."
"""

import argparse
import asyncio
import json
import sys

from investigation import run_investigation


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("description", help="incident description text handed to the diagnostic agents")
    parser.add_argument("--no-recovery", action="store_true", help="stop at DIAGNOSED/ABSTAINED, skip the Recovery Agent")
    parser.add_argument("--skip-critic", action="store_true", help="ablation: accept the leading hypothesis without the Root-Cause Critic")
    parser.add_argument("--max-loops", type=int, default=None, help="override MAX_REEVALUATION_LOOPS for this run")
    parser.add_argument(
        "--incident-id",
        default=None,
        help="attach to an incident the caller already created via POST /incidents, instead of creating a new one",
    )
    args = parser.parse_args(argv)

    result = asyncio.run(
        run_investigation(
            args.description,
            max_loops=args.max_loops,
            trigger_recovery=not args.no_recovery,
            skip_critic=args.skip_critic,
            incident_id=args.incident_id,
        )
    )
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
