"""Phase 9 blind fault-injection benchmark (root CLAUDE.md section 21,
docs/EVALUATION.md).

For each scenario in fault_injection/scenarios.py:
  1. clear any existing fault, then inject this scenario's real fault
  2. run all 3 comparison arms against the SAME injected fault:
       - single_agent_baseline   (evaluation/baselines.py, arm 1)
       - full_nexus              (orchestrator/investigation.py, arm 2)
       - nexus_no_critic         (orchestrator/investigation.py skip_critic=True, arm 3)
  3. clear the fault
  4. score each arm's diagnosis against fault_injection/scenarios.py's
     ground truth (evaluation/scoring.py) -- ground truth is read here, by
     evaluation/ only, never passed to any agent prompt or MCP tool.

Requires the full live stack running (production/, backend/, all 7 A2A
services) plus GROQ_API_KEY -- this is real, not simulated, evaluation. Run:

    .venv-orchestrator/Scripts/python evaluation/run_experiment.py [scenario_id ...]

With no arguments, runs all 5 scenarios. Writes a JSON report to
evaluation/results/<timestamp>.json and prints the aggregate metrics table.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "orchestrator"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fault_injection"))

import baselines  # noqa: E402
import injector  # noqa: E402
import scenarios  # noqa: E402
import scoring  # noqa: E402
from investigation import run_investigation  # noqa: E402
from runtime_config import is_official_benchmark_config, resolve_runtime_config  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _leading_hypothesis_statement(incident: dict) -> str | None:
    hypotheses = incident.get("hypotheses") or []
    open_ones = [h for h in hypotheses if h.get("status") in ("SUPPORTED", "PROPOSED", "UNDER_REVIEW", "NEEDS_EVIDENCE")]
    if not open_ones:
        return None
    return max(open_ones, key=lambda h: h.get("confidence", 0.0)).get("statement")


async def _run_full_nexus(description: str, skip_critic: bool) -> dict:
    start = time.perf_counter()
    incident = await run_investigation(description, skip_critic=skip_critic, trigger_recovery=False)
    latency = time.perf_counter() - start
    abstained = incident.get("status") == "ABSTAINED"
    statement = _leading_hypothesis_statement(incident) if not abstained else None
    predicted = scoring.classify_statement(statement)
    tool_calls = sum(len(f.get("evidence", []) or []) for f in (incident.get("agent_findings") or {}).values())
    return {
        "incident_id": incident.get("incident_id"),
        "status": incident.get("status"),
        "predicted_statement": statement,
        "predicted_root_cause": predicted,
        "abstained": abstained,
        "latency_seconds": round(latency, 3),
        "tool_calls": tool_calls,
        "token_cost": scoring.token_cost(incident),  # measured, else "Unavailable from provider" (root CLAUDE.md section 8)
    }


async def run_one_scenario(scenario_id: str) -> dict:
    scenario = scenarios.get_scenario(scenario_id)
    ground_truth = scenarios.get_ground_truth(scenario_id)
    description = scenario["description"]

    injector.clear()
    injector.inject(scenario_id)
    try:
        baseline_start = time.perf_counter()
        baseline_raw = baselines.single_agent_baseline(description)
        baseline_result = scoring.score_run(baseline_raw["root_cause"], ground_truth["ground_truth_root_cause"], abstained=False)
        baseline_result["latency_seconds"] = baseline_raw["latency_seconds"]

        full_raw = await _run_full_nexus(description, skip_critic=False)
        full_result = scoring.score_run(full_raw["predicted_root_cause"], ground_truth["ground_truth_root_cause"], abstained=full_raw["abstained"])
        full_result.update({k: v for k, v in full_raw.items() if k not in full_result})

        ablation_raw = await _run_full_nexus(description, skip_critic=True)
        ablation_result = scoring.score_run(ablation_raw["predicted_root_cause"], ground_truth["ground_truth_root_cause"], abstained=ablation_raw["abstained"])
        ablation_result.update({k: v for k, v in ablation_raw.items() if k not in ablation_result})
    finally:
        injector.clear()

    return {
        "scenario_id": scenario_id,
        "ground_truth_root_cause": ground_truth["ground_truth_root_cause"],
        "single_agent_baseline": baseline_result,
        "full_nexus": full_result,
        "nexus_no_critic": ablation_result,
    }


async def main(scenario_ids: list[str]) -> dict:
    provider, model = resolve_runtime_config()
    classification = (
        "official_nexus_benchmark"
        if is_official_benchmark_config(provider, model)
        else "development_validation_not_official_nexus_benchmark"
    )
    print(f"runtime: {provider}/{model}; classification: {classification}", flush=True)
    scenario_ids = scenario_ids or [s["scenario_id"] for s in scenarios.SCENARIOS]
    runs = []
    for scenario_id in scenario_ids:
        print(f"--- running {scenario_id} ---", flush=True)
        result = await run_one_scenario(scenario_id)
        runs.append(result)
        print(json.dumps(result, indent=2, default=str), flush=True)

    aggregates = {
        "single_agent_baseline": scoring.aggregate([r["single_agent_baseline"] for r in runs]),
        "full_nexus": scoring.aggregate([r["full_nexus"] for r in runs]),
        "nexus_no_critic": scoring.aggregate([r["nexus_no_critic"] for r in runs]),
    }
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "runtime_provider": provider,
        "runtime_model": model,
        "evaluation_classification": classification,
        "runs": runs,
        "aggregates": aggregates,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"{report['timestamp'].replace(':', '-')}.json"
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\n=== aggregates ===\n{json.dumps(aggregates, indent=2)}")
    print(f"\nreport written to {out_path}")
    return report


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
