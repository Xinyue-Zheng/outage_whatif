"""M8 tests: per-hour analysis within the ticket's outage window.

Covers: analysis_hour validation, the [POLICY] default selection rule,
comparable-day matching (weekday / holiday / exclusion), the hourly tier
over k matched values, the 15-minute tier over 4k bins, busy_hour_flag,
and the report's mandatory conditionality text.
"""

import dataclasses
from pathlib import Path

import pytest

from outage_whatif.claims.adjudicate import adjudicate_capacity_leaf
from outage_whatif.claims.evidence_view import PMStore
from outage_whatif.claims.model import CAPACITY, REFUTED, SUPPORTED, Claim
from outage_whatif.config import Config
from outage_whatif.loop import CaseSpec
from outage_whatif.planning.comparable import (default_analysis_hour,
                                               matched_hour_windows,
                                               validate_analysis_hour,
                                               window_hours)
from outage_whatif.provider.interface import Window

CFG = Config()
CASE01 = Path(__file__).parent.parent / "cases" / "case01_calibration.yaml"


def _window(start="2026-07-20T10:00", end="2026-07-20T18:00"):
    return Window.parse(start, end)     # Monday, 8-hour ticket window


# --------------------------------------------------------------- validation
def test_analysis_hour_outside_window_rejects_the_case():
    with pytest.raises(ValueError):
        validate_analysis_hour(_window(), 9)      # before the window
    with pytest.raises(ValueError):
        validate_analysis_hour(_window(), 18)     # end hour is exclusive
    validate_analysis_hour(_window(), 10)         # first hour ok
    validate_analysis_hour(_window(), 17)         # last hour ok

    spec = CaseSpec.load(CASE01)
    spec.analysis_hour = 3                        # outside 10..17
    with pytest.raises(ValueError):
        spec.resolve_analysis_hour(CFG)           # init_case rejection


# --------------------------------------------------------------- default rule
def test_default_rule_midpoint_without_profile_and_busiest_with():
    h, rule = default_analysis_hour(_window())
    assert h == window_hours(_window())[4] == 14  # midpoint of 10..17
    assert "midpoint" in rule
    profile = [0.1] * 24
    profile[16] = 0.9                             # busiest window hour
    h2, rule2 = default_analysis_hour(_window(), profile)
    assert h2 == 16 and "busiest" in rule2

    spec = CaseSpec.load(CASE01)                  # no analysis_hour in file
    h3 = spec.resolve_analysis_hour(CFG)
    assert h3 == 14
    assert spec.analysis_hour_rule.startswith("[POLICY]")
    assert spec.window.analysis_hour == 14        # stamped onto the window


# --------------------------------------------------------------- matched days
def test_matched_days_same_weekday_same_hour_most_recent_k_weeks():
    wins = matched_hour_windows(_window(), 17, CFG)
    assert len(wins) == CFG.policy.comparable_days_k == 4
    for w in wins:
        assert w.start.hour == 17 and w.hours == 1.0
        assert w.start.weekday() == 0             # Monday, like the outage
    dates = [w.start.date().isoformat() for w in wins]
    assert dates == ["2026-07-13", "2026-07-06", "2026-06-29", "2026-06-22"]


def test_matched_days_exclude_known_outages_and_extend_back():
    cfg = dataclasses.replace(CFG, known_outage_dates=("2026-07-13",))
    dates = [w.start.date().isoformat()
             for w in matched_hour_windows(_window(), 17, cfg)]
    assert "2026-07-13" not in dates
    assert dates == ["2026-07-06", "2026-06-29", "2026-06-22", "2026-06-15"]


def test_matched_days_holiday_outage_matches_holiday_class():
    hol_win = _window("2026-07-04T10:00", "2026-07-04T18:00")  # holiday
    wins = matched_hour_windows(hol_win, 12, CFG)
    hol = set(CFG.holidays)
    assert wins and all(w.start.date().isoformat() in hol for w in wins)
    assert all(w.start.date().isoformat() < "2026-07-04" for w in wins)


# --------------------------------------------------------------- capacity tiers
def _cap_claim():
    return Claim(cid="CAP:S2", ctype=CAPACITY, subject="S2", born_round=1,
                 remedy="buy hourly PM")


def test_hourly_tier_adjudicates_the_mean_of_k_matched_values():
    pm = PMStore(hourly={"S2": [0.2, 0.3, 0.25, 0.25]})   # mean 0.25
    c = _cap_claim()
    adjudicate_capacity_leaf(c, pm, support_edge=0.5, cfg=CFG)
    assert c.state == SUPPORTED and c.detail["hourly_mean"] == 0.25
    pm2 = PMStore(hourly={"S2": [0.9, 0.86, 0.88, 0.92]})  # mean >= pi_hi
    c2 = _cap_claim()
    adjudicate_capacity_leaf(c2, pm2, support_edge=0.5, cfg=CFG)
    assert c2.state == REFUTED


def test_15min_tier_over_4k_bins_two_spikes_refute_one_is_forgiven():
    # k=4 -> 16 bins; cap15_refute_frac=0.10 -> refute needs > 1.6 bins,
    # i.e. >= 2 spiking bins of 16 (the documented mapping).
    one_spike = [0.9] + [0.3] * 15
    pm = PMStore(q15={"S2": one_spike})
    c = _cap_claim()
    adjudicate_capacity_leaf(c, pm, support_edge=None, cfg=CFG)
    assert c.state == SUPPORTED and c.detail["n_bins"] == 16
    two_spikes = [0.9, 0.9] + [0.3] * 14
    c2 = _cap_claim()
    adjudicate_capacity_leaf(c2, PMStore(q15={"S2": two_spikes}), None, CFG)
    assert c2.state == REFUTED


# --------------------------------------------------------------- digest clues
def test_busy_hour_flag_and_matched_hour_spread_in_digest():
    from outage_whatif.claims.model import ClaimSet
    from outage_whatif.loop.tables import build_digest
    from outage_whatif.provider.interface import Profile

    claims = ClaimSet()
    cap = _cap_claim()
    cap.detail["serves"] = ["V1"]
    claims.add(cap)
    prof = Profile(site="S2", kind="same_weekday",
                   hourly_mean=[0.2] * 17 + [0.8] * 5 + [0.2] * 2,  # 17..21 busy
                   hourly_var=[0.01] * 24)
    pm = PMStore(hourly={"S2": [0.2, 0.4, 0.3, 0.3]})

    class _View:
        votes_by_sid: dict = {}
        unsampled_cells: dict = {}

    def _digest(hour):
        return build_digest(
            claims, _View(), {}, type("BG", (), {"population": 0})(), pm,
            {("S2", "same_weekday"): prof},
            {"analysis_hour": hour, "_hour_range": (10, 18)},
            {"pi_hi": CFG.policy.pi_hi}, {}, {}, 1)

    busy = _digest(18)["neighbors"]["S2"]
    assert busy["busy_hour_flag"] is True
    off = _digest(3)["neighbors"]["S2"]
    assert off["busy_hour_flag"] is False
    spread = busy["matched_hour_spread"]
    assert spread["min"] == 0.2 and spread["max"] == 0.4 and spread["std"] > 0


# --------------------------------------------------------------- report text
def test_report_states_conditionality_verbatim():
    from outage_whatif.agents import RuleSeat1AllMid, RuleSeat2Cheapest
    from outage_whatif.loop import CaseRunner
    from outage_whatif.planning import build_calibration_table
    from outage_whatif.provider import SimProvider, generate_world

    spec = CaseSpec.load(CASE01)
    world = generate_world(spec.sim, spec.seed, CFG)
    calib = build_calibration_table({spec.name: world}, CFG, days=7)
    runner = CaseRunner(spec, SimProvider(world), RuleSeat1AllMid(),
                        RuleSeat2Cheapest(), CFG, calib)
    res = runner.run(arm="rule/rule")
    h = runner.analysis_hour
    assert f"This run assessed analysis hour {h:02d}:00." in res.report_md
    assert "The verdict holds for that hour only." in res.report_md
    assert "were not verified in this run" in res.report_md
    assert "[POLICY] applied" in res.report_md    # default rule fired
