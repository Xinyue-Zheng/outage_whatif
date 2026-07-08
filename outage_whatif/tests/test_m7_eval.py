"""M7 tests: calibration artifact, swap harness, metrics, oracle."""

from pathlib import Path

import pytest

from outage_whatif.config import CFG
from outage_whatif.eval import (build_and_save_calibration, case_metrics,
                                load_cases, oracle_run, run_case)
from outage_whatif.eval.harness import make_seat1, make_seat2
from outage_whatif.provider.simulator import generate_world, ground_truth

CASES = Path(__file__).parent.parent / "cases"


def test_ten_cases_two_calibration_eight_blind():
    cases = load_cases()
    assert len(cases) == 10
    kinds = [c.kind for c in cases]
    assert kinds.count("calibration") == 2
    assert kinds.count("blind") == 8
    assert len({c.seed for c in cases}) == 10


def test_calibration_artifact_roundtrip(tmp_path):
    artifact = tmp_path / "calib.json"
    t = build_and_save_calibration(CFG, CASES, artifact)
    assert artifact.exists()
    assert t.sources == ["case01", "case02"]


def test_seat_flags():
    assert make_seat1("rule").name == "rule1-allmid"
    assert make_seat1("zonedist").name == "rule1-zonedist"
    assert make_seat2("rule").name == "rule2-cheapest"
    with pytest.raises(ValueError):
        make_seat1("bogus")


def test_swap_harness_and_metrics_smoke(tmp_path):
    spec = next(c for c in load_cases() if c.name == "case01")
    runner, result = run_case(spec, "rule/rule", CFG, calib=None,
                              run_dir=tmp_path / "run")
    world = generate_world(spec.sim, spec.seed, CFG)
    gt = ground_truth(world, CFG, spec.window)
    m = case_metrics(runner, result, gt)
    assert m["overall_sys"] and m["overall_gt"]
    assert m["spend"] <= m["budget"]
    assert m["matched_villages"] >= 1
    assert 0.0 <= (m["tier_acc"] or 0.0) <= 1.0
    # run artifacts are written
    assert (tmp_path / "run" / "report.md").exists()
    assert (tmp_path / "run" / "divergence.json").exists()
    assert (tmp_path / "run" / "ledger.json").exists()


def test_oracle_outperforms_or_matches_budgeted_run():
    spec = next(c for c in load_cases() if c.name == "case01")
    _, budgeted = run_case(spec, "rule/rule", CFG)
    o_runner, o_result = oracle_run(spec, CFG)
    # the oracle is never budget-stopped and leaves no unverified assumptions
    assert "budget" not in o_result.stop_reason
    assert not any("budget exhaustion" in u
                   for u in o_result.unverified_assumptions)
    assert o_result.spent >= budgeted.spent - 1e-6
