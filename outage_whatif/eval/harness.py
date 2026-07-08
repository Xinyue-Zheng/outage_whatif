"""Swap harness, oracle, metrics, divergence log (Section 10).

Identical code, identical budget; per-seat flag in {llm, rule, zonedist}.
Headline experiment: rule/rule vs llm/llm on the 8 blind cases; mixed arms
are ablations on the 2 calibration cases only.  An unlimited-budget
full-sampling oracle run per case gives the ceiling.

Run:  python -m outage_whatif.eval.harness            # all arms
      python -m outage_whatif.eval.harness rule/rule  # one arm
"""

from __future__ import annotations

import dataclasses
import json
import math
import sys
from pathlib import Path

from ..config import CFG, Config
from ..loop.case import CaseSpec
from ..loop.engine import CaseRunner
from ..provider.simulator import SimProvider, generate_world, ground_truth
from .calibrate import build_and_save_calibration, load_calibration

CASES_DIR = Path(__file__).parent.parent / "cases"
RUNS_DIR = Path(__file__).parent.parent / "runs"


# ------------------------------------------------------------- seats
def make_seat1(flag: str, llm_client=None):
    from ..agents import LLMSeat1, RuleSeat1AllMid, RuleSeat1ZoneDistance
    if flag == "rule":
        return RuleSeat1AllMid()
    if flag == "zonedist":
        return RuleSeat1ZoneDistance()
    if flag == "llm":
        return LLMSeat1(llm_client or _default_llm())
    raise ValueError(flag)


def make_seat2(flag: str, llm_client=None):
    from ..agents import LLMSeat2, RuleSeat2Cheapest
    if flag == "rule":
        return RuleSeat2Cheapest()
    if flag == "llm":
        return LLMSeat2(llm_client or _default_llm())
    raise ValueError(flag)


def _default_llm():
    from ..agents import OllamaLLM
    return OllamaLLM(model=CFG.llm_model, max_tokens=CFG.llm_max_tokens,
                     host=CFG.ollama_host or None)


def llm_available() -> bool:
    import json as _json
    import urllib.request
    client = _default_llm()
    try:
        with urllib.request.urlopen(client.host + "/api/tags",
                                    timeout=5) as resp:
            tags = _json.load(resp)
    except OSError:
        return False
    names = {m.get("name", "") for m in tags.get("models", [])}
    return any(n == client.model or n.split(":")[0] == client.model
               for n in names)


# ------------------------------------------------------------- running
def load_cases(cases_dir: Path = CASES_DIR) -> list:
    return [CaseSpec.load(p) for p in sorted(cases_dir.glob("case*.yaml"))]


def select_eval_hour(spec: CaseSpec, cfg: Config = CFG) -> int:
    """Evaluation-side analysis-hour selection: the busiest hour of the
    ticket's actual window (simulator diurnal profile) unless the case file
    specifies one.  Idempotent."""
    if spec.analysis_hour is None:
        from ..planning.comparable import window_hours
        from ..provider.simulator import DIURNAL
        spec.analysis_hour = max(window_hours(spec.window),
                                 key=lambda h: DIURNAL[h])
        spec.analysis_hour_rule = ("eval selection: busiest hour of the "
                                   "ticket window (diurnal profile)")
    return spec.analysis_hour


def run_case(spec: CaseSpec, arm: str, cfg: Config = CFG, calib=None,
             llm_client=None, run_dir: Path | None = None):
    """arm: '<seat1>/<seat2>' with each in {rule, zonedist, llm}.
    One run = one (case, analysis_hour) pair.  Returns (runner, RunResult).
    EXTENSION POINT (hour sweep): a future "sweep all hours of the ticket
    window" would iterate (case, analysis_hour) pairs right here — call
    run_case once per hour with spec.analysis_hour set.  Not implemented."""
    select_eval_hour(spec, cfg)
    s1_flag, s2_flag = arm.split("/")
    world = generate_world(spec.sim, spec.seed, cfg)
    runner = CaseRunner(spec, SimProvider(world),
                        make_seat1(s1_flag, llm_client),
                        make_seat2(s2_flag, llm_client),
                        cfg, calib, run_dir=run_dir)
    result = runner.run(arm=arm)
    return runner, result


def oracle_run(spec: CaseSpec, cfg: Config = CFG, calib=None):
    """Unlimited-budget run: the same code with the budget constraint
    effectively removed — the ceiling for what sequential querying can
    recover."""
    spec = dataclasses.replace(spec, budget=10 ** 7)
    cfg = dataclasses.replace(cfg, max_rounds=300)
    return run_case(spec, "rule/rule", cfg, calib)


# ------------------------------------------------------------- metrics
_TIER_GT = {"absorbable": "absorbable", "degraded": "degraded",
            "hole": "hole", "severe_hole": "severe_hole"}


def _system_tier(sub: dict) -> str:
    if sub["tier"] == "hole" and sub["severe"]:
        return "severe_hole"
    return sub["tier"]


def case_metrics(runner, result, gt: dict) -> dict:
    """Tier accuracy and attribution accuracy vs simulator ground truth.
    GT villages are matched to system subregions by centroid distance;
    villages missing from the raster (the 'ghost') have no individual
    subregion and are excluded from per-village scores (they surface via the
    background region)."""
    centroids = {sid: s.centroid for sid, s in runner.subregions.items()}
    matched, tier_hits, attr_total, attr_hits = 0, 0, 0, 0
    rows = []
    for name, info in gt["villages"].items():
        if not info["in_raster"]:
            continue
        vx, vy = info["xy"]
        best, best_d = None, 1e18
        for sid, (cx, cy) in centroids.items():
            d = math.hypot(cx - vx, cy - vy)
            if d < best_d:
                best, best_d = sid, d
        if best is None or best_d > 800 or best not in result.per_subregion:
            rows.append((name, info["tier"], "unmatched", False))
            continue
        matched += 1
        sys_tier = _system_tier(result.per_subregion[best])
        hit = sys_tier == _TIER_GT[info["tier"]]
        tier_hits += hit
        rows.append((name, info["tier"], f"{best}:{sys_tier}", hit))
        gt_bt = gt["bottlenecks"].get(name, (None, None))
        sys_bt = result.per_subregion[best]["bottleneck"]
        if gt_bt[0] is not None or sys_bt[0] is not None:
            attr_total += 1
            attr_hits += (gt_bt[0] == sys_bt[0]
                          and (gt_bt[0] != "capacity" or gt_bt[1] == sys_bt[1]))
    overall_hit = result.verdict_overall == gt["overall"]
    return {
        "overall_gt": gt["overall"], "overall_sys": result.verdict_overall,
        "overall_hit": overall_hit,
        "tier_acc": round(tier_hits / matched, 3) if matched else None,
        "attr_acc": round(attr_hits / attr_total, 3) if attr_total else None,
        "matched_villages": matched,
        "spend": result.spent, "budget": result.budget,
        "rounds": result.rounds, "stop": result.stop_reason,
        "divergences": len(result.divergence_log),
        "fuse_trips": result.fuse_trips,
        "village_rows": rows,
    }


# ------------------------------------------------------------- experiments
def run_experiments(arms: list | None = None, cfg: Config = CFG,
                    runs_dir: Path = RUNS_DIR) -> str:
    """Headline experiment + ablations + oracle; writes runs/summary.md."""
    calib = load_calibration() or build_and_save_calibration(cfg)
    cases = load_cases()
    blind = [c for c in cases if c.kind == "blind"]
    calib_cases = [c for c in cases if c.kind == "calibration"]

    if arms is None:
        arms = ["rule/rule", "zonedist/rule"]
        if llm_available():
            arms += ["llm/llm"]
    mixed = ["llm/rule", "rule/llm"] if llm_available() else []

    records = []

    def _one(spec, arm):
        h = select_eval_hour(spec, cfg)
        # analysis_hour is part of the run ID: several hours of the same
        # ticket produce distinct artifacts
        run_dir = runs_dir / f"{spec.name}_h{h:02d}_{arm.replace('/', '-')}"
        runner, result = run_case(spec, arm, cfg, calib, run_dir=run_dir)
        world = generate_world(spec.sim, spec.seed, cfg)
        from ..planning.comparable import matched_hour_windows
        gt = ground_truth(world, cfg, spec.window,
                          matched_hour_windows(spec.window, h, cfg))
        m = case_metrics(runner, result, gt)
        records.append({"case": spec.name, "kind": spec.kind, "arm": arm,
                        "analysis_hour": h, **m})
        print(f"  {spec.name} h{h:02d} [{arm}] sys={m['overall_sys']!r} "
              f"gt={m['overall_gt']!r} tier_acc={m['tier_acc']} "
              f"spend={m['spend']} rounds={m['rounds']}")

    for arm in arms:
        print(f"=== arm {arm} (all cases) ===")
        for spec in cases:
            _one(spec, arm)
    for arm in mixed:
        print(f"=== ablation arm {arm} (calibration cases only) ===")
        for spec in calib_cases:
            _one(spec, arm)

    print("=== oracle (unlimited budget) ===")
    for spec in cases:
        h = select_eval_hour(spec, cfg)
        runner, result = oracle_run(spec, cfg, calib)
        world = generate_world(spec.sim, spec.seed, cfg)
        from ..planning.comparable import matched_hour_windows
        gt = ground_truth(world, cfg, spec.window,
                          matched_hour_windows(spec.window, h, cfg))
        m = case_metrics(runner, result, gt)
        records.append({"case": spec.name, "kind": spec.kind,
                        "arm": "oracle", "analysis_hour": h, **m})
        print(f"  {spec.name} [oracle] sys={m['overall_sys']!r} "
              f"gt={m['overall_gt']!r} tier_acc={m['tier_acc']}")

    md = render_summary(records, blind)
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / "summary.md").write_text(md)
    (runs_dir / "metrics.json").write_text(json.dumps(
        [{k: v for k, v in r.items() if k != "village_rows"}
         for r in records], indent=2))
    return md


def render_summary(records: list, blind_cases: list) -> str:
    lines = ["# Evaluation summary", ""]
    if not llm_available():
        lines += ["> **Note:** no Ollama server with model "
                  f"`{CFG.llm_model}` was reachable, so the llm/llm arm "
                  "(and mixed ablations) were skipped. Start the server "
                  "(`ollama serve`, `ollama pull` the model) and run "
                  "`python -m outage_whatif.eval.harness llm/llm` to add "
                  "them.", ""]
    lines += ["## Per-case results", "",
              "| case | kind | arm | GT overall | system overall | hit | "
              "tier acc | attr acc | spend | rounds | divergences |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in records:
        lines.append(
            f"| {r['case']} | {r['kind']} | {r['arm']} | {r['overall_gt']} | "
            f"{r['overall_sys']} | {'Y' if r['overall_hit'] else 'N'} | "
            f"{r['tier_acc']} | {r['attr_acc']} | {r['spend']} | "
            f"{r['rounds']} | {r['divergences']} |")
    lines += ["", "## Arm aggregates (blind cases)", "",
              "| arm | overall acc | mean tier acc | mean attr acc | "
              "mean spend | mean rounds |",
              "|---|---|---|---|---|---|"]
    blind_names = {c.name for c in blind_cases}
    arms = sorted({r["arm"] for r in records})
    for arm in arms:
        rows = [r for r in records
                if r["arm"] == arm and (r["case"] in blind_names
                                        or arm == "oracle")]
        if not rows:
            continue

        def mean(key):
            vals = [r[key] for r in rows if r[key] is not None]
            return round(sum(vals) / len(vals), 3) if vals else None

        oacc = round(sum(r["overall_hit"] for r in rows) / len(rows), 3)
        lines.append(f"| {arm} | {oacc} | {mean('tier_acc')} | "
                     f"{mean('attr_acc')} | {mean('spend')} | "
                     f"{mean('rounds')} |")
    lines += ["", "Divergence logs (per LLM-seat run) are first-class "
              "outputs in `runs/<case>_<arm>/divergence.json`."]
    return "\n".join(lines)


if __name__ == "__main__":
    arms = [sys.argv[1]] if len(sys.argv) > 1 else None
    print(run_experiments(arms=arms))
