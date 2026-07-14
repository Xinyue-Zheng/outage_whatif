"""M5: the investigator round loop end-to-end (no LLM server).

Eight rounds on the simulator, driven by the deterministic demo client
(a MockLLM-style scripted transport), then the close-out: artifacts,
budget accounting, notebook discipline, and stop behavior.
"""

import json
from pathlib import Path

import pytest

from outage_whatif.agents import Investigator
from outage_whatif.agents.demo_client import DemoInvestigatorClient
from outage_whatif.config import Config
from outage_whatif.loop import CaseRunner, CaseSpec
from outage_whatif.provider import SimProvider, generate_world

CFG = Config()
CASES = Path(__file__).parent.parent / "cases"


def _runner(tmp_path=None, case="case03.yaml"):
    spec = CaseSpec.load(CASES / case)
    world = generate_world(spec.sim, spec.seed, CFG)
    inv = Investigator(DemoInvestigatorClient(), CFG)
    return CaseRunner(spec, SimProvider(world), inv, CFG, calib=None,
                      run_dir=tmp_path)


def test_eight_rounds_end_to_end(tmp_path):
    runner = _runner(tmp_path)
    result = runner.run(rounds=8)

    assert runner.round_no == 8
    assert result.stop_reason == "round cap (8) reached"
    assert result.verdict_overall in {
        "fully absorbable", "locally degraded", "severe hole exists",
        "undecided/qualified"}
    # money was spent through the gate and never over budget
    assert 0 < result.spent <= result.budget
    assert all(e["price"] >= 0 for e in result.ledger_entries)
    # the demo run confirms objects and adjudicates their claims
    assert any(o.state in ("confirmed", "adjudicated")
               for o in runner.registry.all())
    assert runner.claims.alive()

    # ---- artifacts (the acceptance list)
    for name in ("trace.jsonl", "ledger.json", "notebook.md", "events.log"):
        assert (tmp_path / name).exists(), name
    trace = [json.loads(l) for l in
             (tmp_path / "trace.jsonl").read_text().splitlines()]
    nodes = {t["node"] for t in trace}
    assert {"briefing", "investigator", "gate", "reconcile",
            "query"} <= nodes
    # every executed round shows the commit and the gate result
    gates = [t for t in trace if t["node"] == "gate"]
    assert gates and all("approved" in g or g.get("denial") for g in gates)
    ledger = json.loads((tmp_path / "ledger.json").read_text())
    assert round(sum(e["price"] for e in ledger), 2) == result.spent
    # one notebook line per committed round (protocol rule)
    notebook = (tmp_path / "notebook.md").read_text()
    assert "[R1]" in notebook


def test_no_initial_sampling_phase():
    """Round zero buys nothing: the first spend is a gated purchase."""
    runner = _runner()
    assert runner.ledger.spent == 0.0
    assert runner.grid.sampled_cells() == set()
    runner.step()
    assert runner.round_no == 1
    assert all(e["round"] >= 1 for e in runner.ledger.entries)


def test_run_stops_on_max_rounds_safety():
    import dataclasses
    cfg = dataclasses.replace(CFG, max_rounds=3)
    spec = CaseSpec.load(CASES / "case03.yaml")
    world = generate_world(spec.sim, spec.seed, cfg)
    runner = CaseRunner(spec, SimProvider(world),
                        Investigator(DemoInvestigatorClient(), cfg), cfg)
    result = runner.run()
    assert result.rounds <= 4
    assert "max rounds" in result.stop_reason
    # exhaustion close-out: undecided tiers conservatively degraded + flagged
    assert all(v["tier"] != "undecided" for v in result.per_object.values())


def test_budget_exhaustion_stops_and_degrades(tmp_path):
    spec = CaseSpec.load(CASES / "case03.yaml")
    spec.budget = 12.0                       # a couple of purchases at most
    world = generate_world(spec.sim, spec.seed, CFG)
    runner = CaseRunner(spec, SimProvider(world),
                        Investigator(DemoInvestigatorClient(), CFG), CFG)
    result = runner.run(rounds=30)
    assert result.spent <= spec.budget
    assert result.rounds < 30
    assert ("budget" in result.stop_reason
            or "no progress" in result.stop_reason)
    # exhaustion close-out flags what could not be verified
    assert result.unverified_assumptions


def test_declare_done_requires_empty_audit():
    """The demo client declares done only when nothing is left; on a fresh
    case the gate refuses an early declare_done."""
    from outage_whatif.agents import Investigator, MockLLM
    script = [
        {"tool": "notebook_write", "args": {"text": "closing early"}},
        {"commit": {"action": "declare_done", "rationale": "premature"}},
        # retry after the denial: still premature -> round skipped
        {"commit": {"action": "declare_done", "rationale": "again"}},
    ]
    spec = CaseSpec.load(CASES / "case03.yaml")
    world = generate_world(spec.sim, spec.seed, CFG)
    runner = CaseRunner(spec, SimProvider(world),
                        Investigator(MockLLM(script), CFG), CFG)
    runner.step()
    assert runner.stop_reason == ""          # not stopped by declare_done
    assert any("gate denied" in e for e in runner.events)
    assert runner.incidents                  # denied twice -> incident
