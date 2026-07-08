"""M6 tests: LLM seats with a mock client — no API key required.

Mandated coverage: fabricated citation rejection, missing contingency bucket
rejection, guardrail bounce + re-prompt, fuse trip routing one seat only.
"""

from pathlib import Path

import pytest

from outage_whatif.agents import (AgentLedger, LLMSeat1, LLMSeat2, MockLLM,
                                  RuleSeat1AllMid, RuleSeat2Cheapest)
from outage_whatif.agents.seats import Seat1, Seat2, Seat2Output
from outage_whatif.config import Config
from outage_whatif.loop import CaseRunner, CaseSpec
from outage_whatif.planning import build_calibration_table
from outage_whatif.planning.menu import Action, BUCKETS
from outage_whatif.provider import SimProvider, generate_world
from outage_whatif.verdict.flip import DepRow

CFG = Config()
CASE = Path(__file__).parent.parent / "cases" / "case01_calibration.yaml"


# ------------------------------------------------------------- fixtures
def board_fixture():
    def row(cid, ctype, subject, **kw):
        base = {"cid": cid, "type": ctype, "subject": subject,
                "state": "undecided", "ticket": True, "stake_pop": 300.0,
                "position": f"position of {cid}", "cheapest_price": 5.0,
                "remedy": "densify unsampled evidence cells",
                "p_hat": None, "interval": None, "hourly_mean": None,
                "zone": None, "spike_frac": None, "top_share": None}
        base.update(kw)
        return base
    return [row("COV:V1", "coverage", "V1", p_hat=0.8, interval=(0.55, 0.93)),
            row("CAP:S2", "capacity", "S2", cheapest_price=6.4)]


def deps_fixture():
    return [DepRow(lever_cid="CAP:S2", outcome="refuted",
                   consequence="V1 tier undecided->degraded => tickets die: COV:V1",
                   dead_tickets=["COV:V1"], savings=40.0)]


def digest_fixture():
    return {
        "calendar": {"date": "2026-07-20", "weekday": "Monday",
                     "day_type": "weekday", "holiday": False,
                     "season": "summer", "hours": "10:00-18:00"},
        "neighbors": {"S2": {"anchor_mean": 0.41,
                             "anchor_source": "same-weekday profile",
                             "measured_hourly_mean": None,
                             "measured_spike_frac": None,
                             "profile_window_means": {"same_weekday": 0.41},
                             "serves": ["V1"]}},
        "subregions": {"V1": {"cells_sampled": 6, "footprint_cells": 5,
                              "passing": 4, "remaining_unsampled": 3,
                              "interval_width_trajectory": [0.5, 0.38]}},
        "zones": {"support_edge": 0.5, "pi_hi": 0.85, "theta": 0.9,
                  "kappa": 0.6, "cap15_refute_frac": 0.1},
        "agents": {},
    }


def menu_fixture():
    a1 = Action(aid="A1", kind="coverage_densify", claim_cid="COV:V1",
                price=5.0, buckets=list(BUCKETS["coverage_densify"]),
                followup_price=5.0, quartile=1)
    a2 = Action(aid="A2", kind="pm_hourly", claim_cid="CAP:S2", price=6.4,
                buckets=list(BUCKETS["pm_hourly"]), followup_price=25.6,
                quartile=2,
                params={"entities": ["S2"], "granularity": "hourly",
                        "window_key": ("a", "b"), "metric": "prb_util"})
    return [a1, a2]


def seat1_items(citation="CLAIM BOARD", grade="mid"):
    return {"items": [
        {"item_id": i, "grade": grade, "citation": citation,
         "rationale": "anchor followed", "clue": None,
         "no_clue_found_anchor_followed": True}
        for i in ("CAP:S2=refuted", "COV:V1=direct", "CAP:S2=direct")]}


# ------------------------------------------------------------- seat 1
def test_seat1_valid_response_accepted():
    mock = MockLLM([seat1_items()])
    out = LLMSeat1(mock).prioritize(board_fixture(), deps_fixture(),
                                    digest_fixture())
    assert out.source == "llm" and not out.fallback_used
    assert set(out.grades) == {"CAP:S2=refuted", "COV:V1=direct",
                               "CAP:S2=direct"}


def test_seat1_fabricated_citation_rejected_then_fallback():
    """Mandated: fabricated field -> response rejected, one retry, then
    fallback for this round."""
    bad = seat1_items(citation="THE MOON IS MADE OF CHEESE")
    mock = MockLLM([bad, bad])
    out = LLMSeat1(mock).prioritize(board_fixture(), deps_fixture(),
                                    digest_fixture())
    assert len(mock.calls) == 2                        # one retry happened
    assert "REJECTED" in mock.calls[1]["user"]
    assert "fabricated citation" in mock.calls[1]["user"]
    assert out.fallback_used                           # then the rule stepped in
    assert all(g["grade"] == "mid" for g in out.grades.values())


def test_seat1_missing_item_rejected():
    partial = {"items": seat1_items()["items"][:1]}
    mock = MockLLM([partial, seat1_items()])
    out = LLMSeat1(mock).prioritize(board_fixture(), deps_fixture(),
                                    digest_fixture())
    assert len(mock.calls) == 2
    assert "missing grades" in mock.calls[1]["user"]
    assert not out.fallback_used                       # retry fixed it


def test_seat1_missing_anchor_declaration_rejected():
    items = seat1_items()
    items["items"][0]["no_clue_found_anchor_followed"] = False   # clue is null
    mock = MockLLM([items, seat1_items()])
    out = LLMSeat1(mock).prioritize(board_fixture(), deps_fixture(),
                                    digest_fixture())
    assert "no_clue_found_anchor_followed" in mock.calls[1]["user"]
    assert not out.fallback_used


# ------------------------------------------------------------- seat 2
def seat2_resp(aid="A1", bucket="still_straddling", contingencies=None,
               escalation=None, veto=None, grade="mid"):
    menu = menu_fixture()
    act = next(a for a in menu if a.aid == aid)
    if contingencies is None:
        contingencies = [{"bucket": b, "line": f"if {b}: proceed"}
                         for b in act.buckets]
    return {"chosen_aid": aid, "predicted_bucket": bucket, "grade": grade,
            "citation": "CLAIM BOARD", "rationale": "test",
            "contingencies": contingencies, "escalation": escalation,
            "judgment_firming": False, "veto_justification": veto}


def _choose(mock_responses):
    mock = MockLLM(mock_responses)
    seat = LLMSeat2(mock)
    out = seat.choose(["COV:V1", "CAP:S2"], menu_fixture(), digest_fixture(),
                      {"board": board_fixture(),
                       "zones": digest_fixture()["zones"],
                       "escalation_mode": "worst_case"},
                      deps_fixture())
    return out, mock


def test_seat2_valid_cheapest_choice_accepted():
    out, mock = _choose([seat2_resp()])
    assert out.action_aid == "A1" and not out.fallback_used
    assert set(out.contingencies) == set(BUCKETS["coverage_densify"])


def test_seat2_missing_contingency_bucket_rejected():
    """Mandated: schema validation rejects any response missing a bucket."""
    incomplete = seat2_resp(contingencies=[
        {"bucket": "clears_theta", "line": "done"},
        {"bucket": "falls_below_theta", "line": "done"}])   # ambiguous missing
    out, mock = _choose([incomplete, incomplete])
    assert len(mock.calls) == 2
    assert "missing contingency line" in mock.calls[1]["user"]
    assert "still_straddling" in mock.calls[1]["user"]
    assert out.fallback_used


def test_seat2_escalation_arithmetic_reverified():
    # choosing A2 (6.4) over incumbent A1 (5.0): predicted support_zone
    # (decisive) -> effective 6.4; incumbent predicted still_straddling
    # (ambiguous) -> effective 5.0 + 5.0 = 10.0 -> justified
    good_esc = {"chosen_effective_cost": 6.4, "incumbent_aid": "A1",
                "incumbent_effective_cost": 10.0,
                "predicted_incumbent_bucket": "still_straddling"}
    ok = seat2_resp(aid="A2", bucket="support_zone", escalation=good_esc,
                    veto="dependency row CAP:S2=refuted saves 40")
    out, mock = _choose([ok])
    assert out.action_aid == "A2" and not out.fallback_used

    # no arithmetic at all -> rejected
    no_esc = seat2_resp(aid="A2", bucket="support_zone", escalation=None,
                        veto="CAP:S2=refuted")
    out, mock = _choose([no_esc, ok])
    assert "without exhibiting" in mock.calls[1]["user"]
    assert not out.fallback_used

    # wrong arithmetic -> rejected (the code re-verifies it)
    bad_esc = dict(good_esc, incumbent_effective_cost=5.0)
    wrong = seat2_resp(aid="A2", bucket="support_zone", escalation=bad_esc,
                       veto="CAP:S2=refuted")
    out, mock = _choose([wrong, ok])
    assert "does not re-verify" in mock.calls[1]["user"]


def test_seat2_veto_requires_dependency_citation():
    good_esc = {"chosen_effective_cost": 6.4, "incumbent_aid": "A1",
                "incumbent_effective_cost": 10.0,
                "predicted_incumbent_bucket": "still_straddling"}
    no_veto = seat2_resp(aid="A2", bucket="support_zone",
                         escalation=good_esc, veto=None)
    out, mock = _choose([no_veto, no_veto])
    assert "veto" in mock.calls[1]["user"]
    assert out.fallback_used


# ------------------------------------------------------------- fuse
def test_fuse_trips_after_two_consecutive_misses():
    led = AgentLedger("agent2", fuse_threshold=2)
    led.record_seat2(1, "A1", "COV:V1", "clears_theta", "high")
    led.reconcile_seat2("A1", "still_straddling")     # high + mismatch = miss
    assert led.consecutive_misses == 1 and not led.fuse_active
    led.record_seat2(2, "A2", "CAP:S2", "support_zone", "high")
    led.reconcile_seat2("A2", "refute_zone")          # second miss -> trip
    assert led.fuse_active and led.fuse_trips == 1
    assert led.consume_fuse()                          # routes one round
    assert not led.consume_fuse()                      # then resets
    # mid grades are neutral: never hit nor miss
    led.record_seat2(3, "A3", "CAP:S2", "support_zone", "mid")
    led.reconcile_seat2("A3", "refute_zone")
    assert led.consecutive_misses == 0


# ------------------------------------------------------- engine integration
class SpySeat1(Seat1):
    name = "spy1"

    def __init__(self):
        self.calls = 0
        self.inner = RuleSeat1AllMid()

    def prioritize(self, board, deps, digest):
        self.calls += 1
        return self.inner.prioritize(board, deps, digest)


class ScriptedSeat2(Seat2):
    name = "scripted2"

    def __init__(self, scripts):
        self.scripts = list(scripts)
        self.calls = []
        self.inner = RuleSeat2Cheapest()

    def choose(self, candidates, menu, digest, constants, deps):
        self.calls.append(dict(constants))
        fn = self.scripts.pop(0) if self.scripts else None
        if fn is None:
            return self.inner.choose(candidates, menu, digest, constants, deps)
        return fn(self, candidates, menu, digest, constants, deps)


def _runner(seat1, seat2):
    spec = CaseSpec.load(CASE)
    world = generate_world(spec.sim, spec.seed, CFG)
    calib = build_calibration_table({spec.name: world}, CFG, days=7)
    return CaseRunner(spec, SimProvider(world), seat1, seat2, CFG, calib)


def test_guardrail_bounce_and_reprompt():
    """Mandated: non-compliant choice -> rejected with reason -> one
    re-prompt -> compliant choice executes."""
    def bogus(self, candidates, menu, digest, constants, deps):
        return Seat2Output(action_aid="NOT-ON-MENU",
                           predicted_bucket="clears_theta", grade="mid")

    def compliant(self, candidates, menu, digest, constants, deps):
        return self.inner.choose(candidates, menu, digest, constants, deps)

    seat2 = ScriptedSeat2([bogus, compliant])
    runner = _runner(RuleSeat1AllMid(), seat2)
    runner.initial_sampling()
    for _ in range(30):
        if len(seat2.calls) >= 2:
            break
        assert runner.step()
    assert len(seat2.calls) >= 2
    # the second call carried the rejection reason back to the seat
    assert seat2.calls[1].get("rejection")
    assert "not on the filtered menu" in seat2.calls[1]["rejection"]
    assert seat2.calls[1].get("rejected_aid") == "NOT-ON-MENU"
    assert any("re-prompting once" in e for e in runner.events)
    # and something was actually purchased that round
    assert any(e["round"] > 0 for e in runner.ledger.entries)


def test_fuse_routes_one_seat_only():
    """Mandated: a tripped fuse routes THAT seat only to its baseline for a
    round; the other seat keeps working."""
    spy1 = SpySeat1()
    seat2 = ScriptedSeat2([])          # always delegates to the rule
    runner = _runner(spy1, seat2)
    runner.agent_ledgers["agent1"].fuse_active = True
    runner.initial_sampling()
    for _ in range(30):
        if len(seat2.calls) >= 1:
            break
        assert runner.step()
    # round 1 with agents: seat1 was fuse-routed to baseline, seat2 worked
    assert len(seat2.calls) == 1
    assert spy1.calls == 0
    assert any("agent1 fuse active" in e for e in runner.events)
    # fuse resets: the next agent round uses the LLM seat again
    for _ in range(30):
        if len(seat2.calls) >= 2:
            break
        if not runner.step():
            break
    if len(seat2.calls) >= 2:
        assert spy1.calls >= 1
