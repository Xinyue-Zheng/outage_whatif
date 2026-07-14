"""Dev utility: run exactly ONE round and dump its artifacts to a test path.

    python -m outage_whatif.dev_one_round cases/case03.yaml [--out outage_whatif/runs/_test]

Does not call CaseRunner.finish() (no close-out, no report.md, no final
target-RRC purchase) — this is deliberately "just round 1", not a full run,
so you can inspect exactly what one investigator round produces before
wiring your own LLM client / provider in.  Writes to <out>/<case_name>/:
round_trace.jsonl, ledger.json, notebook.md, events.log, llm_io.log (every
LLM call's full system+user input and raw response/error, plain text —
override the path with --log, see Investigator.log_path).
"""

from __future__ import annotations

import argparse
import json
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
from .run_case import _print_round, _resolve_case

PKG = Path(__file__).parent


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Run one investigation round and dump its artifacts.")
    ap.add_argument("case", help="case YAML (e.g. cases/case03.yaml)")
    ap.add_argument("--out", default=str(PKG / "runs" / "_test"),
                    help="output root; artifacts land in <out>/<case_name>/")
    ap.add_argument("--llm", choices=("demo", "ollama"), default="demo")
    ap.add_argument("--log", default=None,
                    help="LLM input/output log path (default: "
                         "<out>/<case_name>/llm_io.log)")
    args = ap.parse_args(argv)

    spec = CaseSpec.load(_resolve_case(args.case))
    if not spec.sim:
        raise SystemExit(f"case {spec.name} has no sim block; this dev "
                         f"script only drives simulator cases")
    world = generate_world(spec.sim, spec.seed, CFG)
    provider = SimProvider(world)
    calib = load_calibration()

    client = (OllamaLLM(model=CFG.llm_model, max_tokens=CFG.llm_max_tokens,
                        host=CFG.ollama_host or None)
              if args.llm == "ollama" else DemoInvestigatorClient())

    out_dir = Path(args.out) / spec.name
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = Path(args.log) if args.log else out_dir / "llm_io.log"
    log_path.write_text("")     # start fresh each run, not append-forever

    # run_dir=None: we dump artifacts ourselves below, not via finish()
    runner = CaseRunner(spec, provider,
                        Investigator(client, CFG, log_path=log_path), CFG,
                        calib, run_dir=None)
    print(f"case {spec.name}: target {runner.target}, budget {spec.budget}, "
          f"analysis hour {runner.analysis_hour:02d}:00 "
          f"({spec.analysis_hour_rule})")

    n0 = len(runner.trace)
    runner.step()                        # exactly ONE round, no close-out
    _print_round(runner.trace[n0:], {})

    (out_dir / "round_trace.jsonl").write_text(
        "\n".join(json.dumps(r, default=str) for r in runner.trace))
    (out_dir / "ledger.json").write_text(
        json.dumps(runner.ledger.entries, indent=2))
    (out_dir / "notebook.md").write_text(
        "# Investigator notebook (round 1)\n\n"
        + "\n".join(f"- {line}" for line in runner.notebook) + "\n")
    (out_dir / "events.log").write_text("\n".join(runner.events))

    print(f"\nround {runner.round_no} done; remaining budget "
          f"{runner.remaining}; artifacts written to {out_dir}/ "
          f"(LLM input/output: {log_path})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
