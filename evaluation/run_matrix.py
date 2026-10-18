"""Live experiment matrix: several prompt/topology/framework arms x blind scenarios x repeats.

    .venv-orchestrator/Scripts/python evaluation/run_matrix.py --plan                       # dry run: size, time, cost
    .venv-orchestrator/Scripts/python evaluation/run_matrix.py --arms hub_default,blackboard \
        --scenarios FI-db-slowdown,CTRL-healthy --repeats 1
    .venv-orchestrator/Scripts/python evaluation/run_matrix.py --resume evaluation/results/matrix-<ts>.jsonl

Needs production (8001) and backend (8000) already running. It starts/stops the 7 agent services itself (own
environment per group of arms). Every finished run is appended to a .jsonl file at once, so an interrupted
matrix resumes without repeating (or re-paying for) completed runs. Real runs only: nothing is simulated.
Agents receive ONLY the blind symptom text; ground truth is read here, after the run, for scoring.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for p in (HERE, ROOT / "orchestrator", ROOT / "fault_injection", ROOT):
    sys.path.insert(0, str(p))

import baselines  # noqa: E402
import injector  # noqa: E402
import matrix  # noqa: E402
import scenarios  # noqa: E402
import scoring  # noqa: E402
from stack import AgentStack  # noqa: E402

RESULTS_DIR = HERE / "results"
PRODUCTION = os.environ.get("PRODUCTION_BASE_URL", "http://127.0.0.1:8001")
BACKEND = os.environ.get("NEXUS_BACKEND_URL", "http://127.0.0.1:8000")
SEC_PER_NEXUS_RUN = 150  # observed ~100-200 s; used only for the --plan estimate
TOKENS_PER_NEXUS_RUN = 18000  # observed 16.5k-17.2k (diagnosis only); used only for the --plan estimate


def _http(method: str, url: str, timeout: float = 30) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, method=method), timeout=timeout).read()


def customer_traffic(n: int) -> None:
    """Same customer-side requests the dashboard sends (the only way latency faults leave a signal)."""
    for i in range(n):
        try:
            _http("GET", f"{PRODUCTION}/orders" if i % 2 == 0 else f"{PRODUCTION}/orders/1")
        except Exception:  # noqa: BLE001 -- failing requests are the point of several faults
            pass


def reset_shop() -> None:
    _http("POST", f"{PRODUCTION}/admin/reset")


def deepseek_balance() -> float | None:
    """Account balance in USD from the provider's own endpoint; the key is read, never printed."""
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None
    try:
        req = urllib.request.Request("https://api.deepseek.com/user/balance", headers={"Authorization": f"Bearer {key}"})
        data = json.loads(urllib.request.urlopen(req, timeout=15).read())
        return float(data["balance_infos"][0]["total_balance"])
    except Exception:  # noqa: BLE001
        return None


def agent_error_count(incident_id: str | None) -> int:
    """How many model/tool errors the agents reported during this run (from their AGENT_MONITOR events). A run with errors
    (typically provider rate limits) must not be scored as if the system had reasoned its way to an abstention."""
    if not incident_id:
        return 0
    try:
        events = json.loads(_http("GET", f"{BACKEND}/incidents/{incident_id}/events"))["events"]
    except Exception:  # noqa: BLE001
        return 0
    return sum(int((e.get("payload") or {}).get("errors", 0) or 0) for e in events if e.get("event_type") == "AGENT_MONITOR")


def leading_statement(incident: dict) -> str | None:
    hyps = [h for h in (incident.get("hypotheses") or []) if h.get("status") in ("SUPPORTED", "PROPOSED", "UNDER_REVIEW", "NEEDS_EVIDENCE")]
    return max(hyps, key=lambda h: h.get("confidence", 0.0)).get("statement") if hyps else None


def baseline_usage_cost(raw: dict):
    usage = raw.get("usage")
    return dict(usage) if usage else scoring.TOKEN_COST_UNAVAILABLE


def nexus_token_cost(incident: dict):
    total = (incident.get("token_usage") or {}).get("total")
    if not isinstance(total, dict) or not total.get("llm_calls"):
        return scoring.TOKEN_COST_UNAVAILABLE
    return {k: total.get(k, 0) for k in ("llm_calls", "prompt_tokens", "completion_tokens", "total_tokens")}


async def run_one(arm: matrix.Arm, scenario_id: str, repeat: int) -> dict:
    from investigation import run_investigation  # imported late: needs the orchestrator venv

    scenario = scenarios.get_scenario(scenario_id)
    truth = scenarios.get_ground_truth(scenario_id)["ground_truth_root_cause"]
    symptom = scenarios.blind_symptom(scenario_id)  # never scenario["description"], which names the cause

    reset_shop()
    customer_traffic(10)
    if scenario["fault_type"]:
        injector.inject(scenario_id)   # may inject several faults for the held-out two-fault scenarios
    customer_traffic(25)
    base = {"arm": arm.name, "scenario_id": scenario_id, "repeat": repeat, "ground_truth_root_cause": truth}
    started = time.perf_counter()
    try:
        if arm.kind == "baseline":
            raw = await asyncio.to_thread(baselines.single_agent_baseline, symptom)
            rec = scoring.score_run(raw["root_cause"], truth, abstained=raw["root_cause"] == "unknown")
            rec.update({"latency_seconds": raw["latency_seconds"], "token_cost": baseline_usage_cost(raw), "tool_calls": 0})
            return {**base, **rec, "status": "BASELINE"}
        saved = {k: os.environ.get(k) for k in [*arm.agent_env_dict(), *arm.run_env_dict()]}
        os.environ.update(arm.agent_env_dict())
        os.environ.update(arm.run_env_dict())
        try:
            incident = await run_investigation(symptom, skip_critic=arm.skip_critic, trigger_recovery=False)
        finally:
            for k, v in saved.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        latency = time.perf_counter() - started
        abstained = incident.get("status") == "ABSTAINED"
        statement = None if abstained else leading_statement(incident)
        predicted = scoring.classify_statement(statement)
        rec = scoring.score_run(predicted, truth, abstained=abstained)
        rec.update({
            "latency_seconds": round(latency, 1), "token_cost": nexus_token_cost(incident),
            "tool_calls": sum(len(f.get("evidence", []) or []) for f in (incident.get("agent_findings") or {}).values()),
            "incident_id": incident.get("incident_id"), "trace_id": incident.get("trace_id"),
            "status": incident.get("status"), "loops_used": (incident.get("decision") or {}).get("loops_used"),
            "predicted_statement": statement, "run_config": incident.get("run_config"),
            "agent_errors": agent_error_count(incident.get("incident_id")),
        })
        return {**base, **rec}
    finally:
        try:
            injector.clear()
        except Exception:  # noqa: BLE001
            pass


def rescore(record: dict) -> dict:
    """Re-judge a stored NEXUS run with the CURRENT scorer from its stored hypothesis text, so every run in a report is
    scored by the same code even if the scorer was improved while the matrix was running."""
    if record.get("status") == "BASELINE" or "predicted_statement" not in record:
        return record
    abstained = record.get("status") == "ABSTAINED"
    predicted = scoring.classify_statement(None if abstained else record.get("predicted_statement"))
    updated = scoring.score_run(predicted, record["ground_truth_root_cause"], abstained=abstained)
    return {**record, **updated}


def load_done(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_report(runs: list[dict], arms: list[matrix.Arm], scenario_ids: list[str], repeats: int, balance_delta: float | None,
                 price_in: float, price_out: float) -> dict:
    by_arm = {a.name: [r for r in runs if r["arm"] == a.name] for a in arms}
    summaries = {n: matrix.summarize_arm(rs, price_in, price_out) for n, rs in by_arm.items() if rs}
    from runtime_config import resolve_runtime_config
    provider, model = resolve_runtime_config()
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "runtime": f"{provider}/{model}",
        "scenarios": scenario_ids, "repeats": repeats, "price_in_per_m": price_in, "price_out_per_m": price_out,
        "balance_delta_usd": balance_delta, "est_cost_usd_total": round(sum(s["est_cost_usd_total"] for s in summaries.values()), 4),
        "arms": summaries, "repeatability": {n: matrix.repeatability(rs) for n, rs in by_arm.items() if rs},
        "arm_definitions": {a.name: {"description": a.description, "compares": a.compares} for a in arms if by_arm[a.name]},
        "runs": runs, "caveats": matrix.STANDARD_CAVEATS,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arms", default=",".join(a.name for a in matrix.ARMS))
    ap.add_argument("--set", choices=["core", "holdout", "all"], default="core",
                    help="core = the 5 tuned faults + healthy control; holdout = reworded + two-fault scenarios (run with prompts/scorer FROZEN)")
    ap.add_argument("--scenarios", default=None, help="explicit comma-separated scenario ids (overrides --set)")
    ap.add_argument("--repeats", type=int, default=2)
    ap.add_argument("--resume", default=None, help="a matrix-*.jsonl file to continue")
    ap.add_argument("--retries", type=int, default=2, help="re-run a run whose agents reported errors (e.g. provider rate limits)")
    ap.add_argument("--retry-wait", type=int, default=65, help="seconds to wait before a retry (free tiers limit requests per minute)")
    ap.add_argument("--plan", action="store_true", help="print the size/time/cost estimate and exit")
    ap.add_argument("--report-only", default=None, help="a matrix-*.jsonl file: re-score with the current scorer and write the report, no runs")
    ap.add_argument("--max-spend-usd", type=float, default=1.0, help="stop when the ESTIMATED spend reaches this")
    ap.add_argument("--price-in", type=float, default=float(os.environ.get("NEXUS_PRICE_IN_PER_M", matrix.DEFAULT_PRICE_IN_PER_M)))
    ap.add_argument("--price-out", type=float, default=float(os.environ.get("NEXUS_PRICE_OUT_PER_M", matrix.DEFAULT_PRICE_OUT_PER_M)))
    args = ap.parse_args(argv)

    if args.report_only:
        path = Path(args.report_only)
        runs = [rescore(r) for r in load_done(path)]
        arms_present = [a for a in matrix.ARMS if any(r["arm"] == a.name for r in runs)]
        ids = sorted({r["scenario_id"] for r in runs}, key=lambda s: (s.startswith("CTRL"), s))
        reps = 1 + max(r["repeat"] for r in runs)
        report = build_report(runs, arms_present, ids, reps, None, args.price_in, args.price_out)
        path.with_suffix(".json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        path.with_suffix(".md").write_text(matrix.render_markdown(report), encoding="utf-8")
        print(matrix.render_markdown(report))
        return 0

    arms = [matrix.ARMS_BY_NAME[n] for n in args.arms.split(",") if n]
    core = [*(s["scenario_id"] for s in scenarios.SCENARIOS), "CTRL-healthy"]
    holdout = [*(s["scenario_id"] for s in scenarios.HOLDOUT_SCENARIOS), "HO-healthy-control"]
    chosen = {"core": core, "holdout": holdout, "all": core + holdout}[args.set]
    scenario_ids = [s for s in (args.scenarios.split(",") if args.scenarios else chosen) if s]
    total_runs = len(arms) * len(scenario_ids) * args.repeats
    nexus_runs = sum(1 for a in arms if a.kind == "nexus") * len(scenario_ids) * args.repeats
    est_cost = nexus_runs * matrix.estimate_cost_usd(int(TOKENS_PER_NEXUS_RUN * 0.92), int(TOKENS_PER_NEXUS_RUN * 0.08), args.price_in, args.price_out)
    print(f"plan: {len(arms)} arms x {len(scenario_ids)} scenarios x {args.repeats} repeats = {total_runs} runs "
          f"({nexus_runs} full investigations). Estimated {nexus_runs * SEC_PER_NEXUS_RUN / 3600:.1f} h, "
          f"~{nexus_runs * TOKENS_PER_NEXUS_RUN / 1e6:.1f}M tokens, ~${est_cost:.2f} (estimate).")
    if args.plan:
        return 0

    from dotenv import load_dotenv
    for parent in HERE.parents:
        if (parent / ".env").exists():
            load_dotenv(parent / ".env")
            break
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = Path(args.resume) if args.resume else RESULTS_DIR / f"matrix-{time.strftime('%Y%m%dT%H%M%S')}.jsonl"
    runs = load_done(out)
    done = {(r["arm"], r["scenario_id"], r["repeat"]) for r in runs}
    balance_start = deepseek_balance()
    print(f"results file: {out}; resuming with {len(runs)} finished runs; balance start: {balance_start}", flush=True)

    stack = AgentStack()
    spent = sum(matrix.estimate_cost_usd(matrix.run_tokens(r)["prompt"], matrix.run_tokens(r)["completion"], args.price_in, args.price_out) for r in runs)
    try:
        for env_key, group in matrix.group_by_agent_env(arms):
            todo = [(a, s, i) for i in range(args.repeats) for s in scenario_ids for a in group if (a.name, s, i) not in done]
            if not todo:
                continue
            if any(a.kind == "nexus" for a, _, _ in todo):
                print(f"[stack] starting agents with {dict(env_key) or 'default env'}", flush=True)
                stack.start(dict(env_key))
            for arm, sid, rep in todo:
                if spent >= args.max_spend_usd:
                    print(f"[stop] estimated spend ${spent:.3f} reached --max-spend-usd; resume later with --resume {out}")
                    raise SystemExit(0)
                rec = asyncio.run(run_one(arm, sid, rep))
                attempts = 1
                while rec.get("agent_errors", 0) > 0 and attempts <= args.retries:   # provider errors: pause, then run again
                    print(f"   run had {rec['agent_errors']} agent error(s) (rate limit?); waiting {args.retry_wait}s, retry {attempts}/{args.retries}", flush=True)
                    time.sleep(args.retry_wait)
                    rec = asyncio.run(run_one(arm, sid, rep))
                    attempts += 1
                rec["attempts"] = attempts
                rec["invalid"] = rec.get("agent_errors", 0) > 0     # still failing after the retries: excluded from accuracy, counted separately
                t = matrix.run_tokens(rec)
                spent += matrix.estimate_cost_usd(t["prompt"], t["completion"], args.price_in, args.price_out)
                runs.append(rec)
                with out.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, default=str) + "\n")
                print(f"[{len(runs)}] {arm.name:20s} {sid:24s} #{rep} -> {rec['predicted_root_cause']:20s} "
                      f"{'INVALID' if rec.get('invalid') else ('OK ' if rec['correct'] else 'BAD')} {rec['latency_seconds']}s {t['total']} tok (est spend ${spent:.3f})", flush=True)
    finally:
        stack.stop()

    balance_end = deepseek_balance()
    delta = round(balance_start - balance_end, 2) if balance_start is not None and balance_end is not None else None
    report = build_report(runs, arms, scenario_ids, args.repeats, delta, args.price_in, args.price_out)
    (out.with_suffix(".json")).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    (out.with_suffix(".md")).write_text(matrix.render_markdown(report), encoding="utf-8")
    print(matrix.render_markdown(report))
    print(f"report: {out.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
