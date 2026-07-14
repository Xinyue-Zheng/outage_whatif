"""Round-by-round demo runner.

    python -m outage_whatif.run_case cases/case03.yaml --rounds 8 [--pause]

Runs the investigation on the simulator, printing each round's briefing,
the agent's tool calls, the committing action, the gate result, and the
post-round state deltas.  Artifacts land in runs/<case>/: trace.jsonl,
ledger.json, notebook.md, events.log (+ report.md).

Default LLM transport is the deterministic demo client (no Ollama needed);
``--llm ollama`` uses the configured Ollama server.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .agents.demo_client import DemoInvestigatorClient
from .agents.investigator import Investigator
from .agents.llm import OllamaLLM
from .config import CFG
from .loop.case import CaseSpec
from .loop.engine import CaseRunner
from .planning.calibration import load_calibration
from .provider.simulator import SimProvider, generate_world

PKG = Path(__file__).parent


def _resolve_case(arg: str) -> Path:
    p = Path(arg)
    for cand in (p, PKG / arg, PKG.parent / arg,
                 PKG / "cases" / p.name):
        if cand.exists():
            return cand
    hits = sorted((PKG / "cases").glob(f"{p.stem}*.yaml"))
    if hits:
        return hits[0]
    raise SystemExit(f"case file not found: {arg}")


# ------------------------------------------------------------- printing
def _print_round(entries: list, prev_states: dict) -> dict:
    """Pretty-print one round's trace records; returns claim states."""
    states = dict(prev_states)
    for rec in entries:
        node = rec.get("node")
        if node == "briefing":
            print("\n" + "=" * 72)
            print(rec["briefing"])
            print("-" * 72)
        elif node == "investigator":
            for tc in rec.get("tool_calls") or []:
                res = tc["result"]
                if len(res) > 160:
                    res = res[:160] + "..."
                print(f"  TOOL {tc['tool']} {tc['args']} -> {res}")
            if rec.get("commit"):
                print(f"  COMMIT {rec['commit']}")
            for inc in rec.get("incidents") or []:
                print(f"  INCIDENT: {inc}")
        elif node == "gate":
            if rec.get("denial"):
                print(f"  GATE: DENIED — {rec['denial']}")
            elif rec.get("approved"):
                print(f"  GATE: approved {rec['approved']}")
        elif node == "execute":
            if rec.get("aid"):
                print(f"  EXECUTED {rec['aid']} price={rec['price']} "
                      f"actual_bucket={rec.get('actual_bucket')}")
        elif node == "reconcile":
            new = rec.get("claim_states", {})
            deltas = [f"{cid}: {states.get(cid, 'new')} -> {st}"
                      for cid, st in sorted(new.items())
                      if states.get(cid) != st]
            if deltas:
                print("  STATE DELTAS: " + "; ".join(deltas))
            print(f"  REMAINING BUDGET: {rec.get('remaining_budget')}")
            states = new
        elif node == "stop_check" and rec.get("stop"):
            print(f"\n  STOP: {rec.get('stop_reason')}")
    return states


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Run one what-if investigation round by round.")
    ap.add_argument("case", help="case YAML (e.g. cases/case03.yaml)")
    ap.add_argument("--rounds", type=int, default=None,
                    help="stop after N rounds regardless of the stop rules")
    ap.add_argument("--pause", action="store_true",
                    help="wait for Enter between rounds")
    ap.add_argument("--llm", choices=("demo", "ollama"), default="demo",
                    help="LLM transport (default: deterministic demo client)")
    args = ap.parse_args(argv)

    spec = CaseSpec.load(_resolve_case(args.case))
    if not spec.sim:
        raise SystemExit(f"case {spec.name} has no sim block; only "
                         f"simulator cases can run here (FileProvider is "
                         f"not implemented)")
    world = generate_world(spec.sim, spec.seed, CFG)
    provider = SimProvider(world)
    calib = load_calibration()
    if calib is None:
        print("note: no calibration artifact "
              "(run python -m outage_whatif.planning.calibration); "
              "the hourly tier cannot declare support this run")
    client = (OllamaLLM(model=CFG.llm_model, max_tokens=CFG.llm_max_tokens,
                        host=CFG.ollama_host or None)
              if args.llm == "ollama" else DemoInvestigatorClient())

    run_dir = PKG / "runs" / spec.name
    runner = CaseRunner(spec, provider, Investigator(client, CFG), CFG,
                        calib, run_dir)
    print(f"case {spec.name}: target {runner.target}, "
          f"budget {spec.budget}, analysis hour "
          f"{runner.analysis_hour:02d}:00 ({spec.analysis_hour_rule})")

    states: dict = {}
    while True:
        n0 = len(runner.trace)
        alive = runner.step()
        states = _print_round(runner.trace[n0:], states)
        if not alive:
            break
        if args.rounds is not None and runner.round_no >= args.rounds:
            runner.stop_reason = f"round cap ({args.rounds}) reached"
            print(f"\n  STOP: {runner.stop_reason}")
            break
        if args.pause:
            input("-- Enter for next round --")

    result = runner.finish()
    print("\n" + "=" * 72)
    print(f"VERDICT: {result.verdict_overall}")
    for sid, v in sorted(result.per_object.items()):
        print(f"  {sid}: {v['tier']} ({v['severe']}; "
              f"bottleneck={v['bottleneck']})")
    print(f"spent {result.spent} of {result.budget} over {result.rounds} "
          f"rounds — {result.stop_reason}")
    if result.unverified_assumptions:
        print("unverified assumptions:")
        for u in result.unverified_assumptions:
            print(f"  - {u}")
    print(f"artifacts: {run_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
