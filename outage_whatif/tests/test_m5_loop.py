"""M5 tests: round loop end-to-end with both seats on rule baselines."""

from pathlib import Path

import pytest

from outage_whatif.agents import RuleSeat1AllMid, RuleSeat2Cheapest
from outage_whatif.config import Config
from outage_whatif.loop import CaseRunner, CaseSpec
from outage_whatif.loop.report import DECLARED_BOUNDARY, P_MIN_DISCLOSURE
from outage_whatif.planning import build_calibration_table
from outage_whatif.provider import SimProvider, generate_world

CFG = Config()
CASE = Path(__file__).parent.parent / "cases" / "case01_calibration.yaml"


def _run(seed_offset=0):
    spec = CaseSpec.load(CASE)
    spec.seed += seed_offset
    world = generate_world(spec.sim, spec.seed, CFG)
    calib = build_calibration_table({spec.name: world}, CFG, days=7)
    runner = CaseRunner(spec, SimProvider(world), RuleSeat1AllMid(),
                        RuleSeat2Cheapest(), CFG, calib)
    return runner, runner.run(arm="rule/rule")


def test_rule_rule_end_to_end():
    runner, res = _run()
    assert res.spent <= res.budget + 1e-6
    assert res.rounds >= 1
    assert res.stop_reason
    assert res.verdict_overall in {
        "fully absorbable", "locally degraded", "severe hole exists",
        "undecided"} or "blocked" in res.verdict_overall
    # some money was actually spent through the ledger
    assert res.ledger_entries and res.spent > 0
    # every ledger entry names its purpose
    assert all(e["purpose"] for e in res.ledger_entries)
    # per-subregion verdicts exist for settlements and the background region
    assert "BG" in res.per_subregion


def test_run_reproducible():
    _, r1 = _run()
    _, r2 = _run()
    assert r1.verdict_overall == r2.verdict_overall
    assert r1.spent == r2.spent
    assert r1.rounds == r2.rounds
    assert r1.per_subregion == r2.per_subregion
    assert [e["aid"] for e in r1.ledger_entries] == \
           [e["aid"] for e in r2.ledger_entries]


def test_report_mandated_content():
    runner, res = _run()
    md = res.report_md
    assert DECLARED_BOUNDARY in md
    assert P_MIN_DISCLOSURE in md
    # every policy value is stated
    for name in ("theta", "pi_hi", "kappa", "P_min", "P0", "sigma"):
        assert name in md
    assert "Budget ledger" in md
    assert "Agent ledgers" in md
    assert f"Total spent: {res.spent}" in md
    # supported capacity claims phrased as designed
    if "unverified_assumption" in md:
        assert "budget exhaustion" in md


def test_stop_never_overspends_and_target_rrc_last():
    runner, res = _run()
    assert runner.remaining >= -1e-6
    rrc = [e for e in res.ledger_entries
           if e["purpose"].startswith("target baseline RRC")]
    if rrc:
        assert res.ledger_entries[-1] is rrc[-1]


def test_static_area_run_completes_without_integrity_machinery():
    cfg = Config(static_area_km=12.0)   # covers the whole sim world
    spec = CaseSpec.load(CASE)
    world = generate_world(spec.sim, spec.seed, cfg)
    calib = build_calibration_table({spec.name: world}, cfg, days=7)
    runner = CaseRunner(spec, SimProvider(world), RuleSeat1AllMid(),
                        RuleSeat2Cheapest(), cfg, calib)
    res = runner.run(arm="rule/rule")
    assert res.stop_reason and res.rounds >= 1
    assert res.boundary_expansions == 0
    assert not [c for c in runner.claims.all() if c.ctype == "integrity"]
    assert not runner.deferred_settlements   # square swallows everything
