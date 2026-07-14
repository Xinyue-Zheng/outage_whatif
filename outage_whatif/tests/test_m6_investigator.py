"""M6: investigator protocol + spend gate (MockLLM, no server).

Covers: citation rejection, gate denials including the confidence-cap
bounce, the tool-loop limit, notebook-before-commit, malformed -> single
re-prompt -> round skipped (no fallback seat), the flip-ticket rule, and
the instrument checks behind dismiss / drill_down / declare_done.
"""

from pathlib import Path

import pytest

from outage_whatif.agents import Investigator, MockLLM
from outage_whatif.agents.investigator import validate_commit
from outage_whatif.claims import open_claims_for
from outage_whatif.claims.model import CAPACITY, UNDECIDED, Claim
from outage_whatif.config import Config
from outage_whatif.loop import CaseRunner, CaseSpec
from outage_whatif.loop.gate import (CONFIDENCE_CAPS, GateState,
                                     PurchaseRequest, gate, outcome_space)
from outage_whatif.provider import SimProvider, generate_world

CFG = Config()
CASES = Path(__file__).parent.parent / "cases"

BRIEFING = ("ROUND 1 — test\nBUDGET: initial=100.00 spent=0.00 "
            "remaining=100.00\nTICKETED CLAIMS:\n  none\n")

NOTE = {"tool": "notebook_write", "args": {"text": "thinking"}}


def _tools(extra=None):
    calls = []
    tools = {"notebook_write": lambda a: "ok",
             "list_gaps": lambda a: ["GAP:ledger | demand_ledger_absent"],
             "boom": lambda a: (_ for _ in ()).throw(RuntimeError("kaput"))}
    tools.update(extra or {})
    return tools, calls


def _commit(**over):
    c = {"action": "purchase", "kind": "probe", "target": "GAP:ledger",
         "params": {"points": [[100, 100]]},
         "predicted_bucket": "target_present", "confidence": "mid",
         "citation": "BUDGET: initial=100.00", "rationale": "r"}
    c.update(over)
    return {"commit": c}


# ------------------------------------------------------------- protocol
def test_notebook_before_commit_is_enforced():
    inv = Investigator(MockLLM([_commit(), NOTE, _commit()]), CFG)
    tools, _ = _tools()
    out = inv.run_round(BRIEFING, tools)
    # first commit bounced (no notebook line), the retry wrote + committed
    assert out.commit is not None
    assert out.notebook_written
    assert any("notebook_write" in i for i in out.incidents)


def test_malformed_then_retry_then_skip():
    inv = Investigator(MockLLM(["not json at all", {"nope": 1}]), CFG)
    tools, _ = _tools()
    out = inv.run_round(BRIEFING, tools)
    assert out.commit is None                # round skipped, NO fallback seat
    assert len(out.incidents) == 2


def test_tool_loop_limit():
    import dataclasses
    cfg = dataclasses.replace(CFG, max_tool_calls_per_round=2)
    script = [NOTE, {"tool": "list_gaps", "args": {}},
              {"tool": "list_gaps", "args": {}},     # 3rd call -> refused
              _commit()]
    inv = Investigator(MockLLM(script), cfg)
    tools, _ = _tools()
    out = inv.run_round(BRIEFING, tools)
    assert out.commit is not None
    assert len(out.tool_calls) == 2
    assert any("tool budget exhausted" in i for i in out.incidents)


def test_unknown_tool_and_tool_error_are_survivable():
    script = [{"tool": "no_such_tool", "args": {}},   # validator error
              NOTE, {"tool": "boom", "args": {}},     # tool raises -> info
              _commit()]
    inv = Investigator(MockLLM(script), CFG)
    tools, _ = _tools()
    out = inv.run_round(BRIEFING, tools)
    assert out.commit is not None
    assert any("kaput" in t["result"] for t in out.tool_calls)


def test_tool_outputs_join_the_citation_base():
    script = [NOTE, {"tool": "list_gaps", "args": {}}, _commit()]
    inv = Investigator(MockLLM(script), CFG)
    tools, _ = _tools()
    out = inv.run_round(BRIEFING, tools)
    assert "GAP:ledger | demand_ledger_absent" in out.shown_text


def test_commit_schema_validation():
    assert validate_commit({"action": "purchase"})           # missing fields
    assert validate_commit({"action": "warp_drive"})
    assert validate_commit({"action": "register_object", "x": 1, "y": 2,
                            "radius_m": 5, "provenance": "divine"})
    assert validate_commit(_commit()["commit"]) is None
    assert validate_commit({"action": "declare_done"}) is None


# ------------------------------------------------------------- pure gate
def _gate_state(claims=None, tickets=None, gaps=("GAP:ledger",),
                shown="BUDGET: initial=100.00 spent=0", remaining=100.0,
                budget=100.0):
    from outage_whatif.claims.model import ClaimSet
    cs = claims or ClaimSet()
    t = tickets or {}
    return GateState(claims=cs, gap_ids=set(gaps),
                     flip=lambda cid: bool(t.get(cid)),
                     shown_text=shown, remaining=remaining,
                     budget_initial=budget)


def _req(**over):
    r = dict(kind="probe", target="GAP:ledger",
             params={"points": [(1.0, 1.0)]},
             predicted_bucket="target_present", confidence="mid",
             citation="BUDGET: initial=100.00", price=1.0)
    r.update(over)
    return PurchaseRequest(**r)


def test_gate_checks_fire_in_order():
    st = _gate_state()
    assert gate(_req(), st) is None                          # clean pass
    assert "unknown purchase kind" in gate(_req(kind="teleport"), st)
    assert "remaining budget" in gate(_req(price=1000.0), st)
    assert "neither an open claim nor" in gate(_req(target="GAP:nope"), st)
    assert "outcome space" in gate(_req(predicted_bucket="banana"), st)
    assert "verbatim" in gate(_req(citation="I made this up"), st)


def test_gate_flip_ticket_rule():
    from outage_whatif.claims.model import ClaimSet
    cs = ClaimSet()
    open_claims_for("V1", cs)
    st = _gate_state(claims=cs, tickets={"COV:V1": False})
    denial = gate(_req(target="COV:V1", kind="densify",
                       predicted_bucket="interval_above"), st)
    assert "no flip ticket" in denial
    st2 = _gate_state(claims=cs, tickets={"COV:V1": True})
    assert gate(_req(target="COV:V1", kind="densify",
                     predicted_bucket="interval_above"), st2) is None
    # decided claims are not open targets
    cs.get("COV:V1").state = "supported"
    assert "not open" in gate(_req(target="COV:V1", kind="densify",
                                   predicted_bucket="interval_above"), st2)


def test_gate_confidence_caps():
    st = _gate_state()
    assert CONFIDENCE_CAPS == {"low": 0.02, "mid": 0.10, "high": 1.0}
    # 5.0 > 2% of 100 -> low bounced; mid (10) passes; 15 needs high
    assert "confidence cap" in gate(_req(confidence="low", price=5.0), st)
    assert gate(_req(confidence="mid", price=5.0), st) is None
    assert "confidence cap" in gate(_req(confidence="mid", price=15.0), st)
    assert gate(_req(confidence="high", price=15.0), st) is None


def test_outcome_spaces():
    assert outcome_space("probe") == ["target_present", "target_absent",
                                      "mixed"]
    assert outcome_space("densify") == ["interval_above", "interval_below",
                                        "still_straddling"]
    assert outcome_space("pm_hourly") == ["support_zone", "middle_zone",
                                          "refute_zone"]
    assert outcome_space("nonsense") == []


# ------------------------------------------------------------- runner gate
def _runner(script):
    spec = CaseSpec.load(CASES / "case03.yaml")
    world = generate_world(spec.sim, spec.seed, CFG)
    return CaseRunner(spec, SimProvider(world),
                      Investigator(MockLLM(script), CFG), CFG)


def test_confidence_cap_bounce_and_retry_through_the_loop():
    """A low-confidence purchase above 2% of budget is denied by the gate;
    the fed-back retry at high confidence executes."""
    def commit(conf):
        return lambda s, u: {"commit": {
            "action": "purchase", "kind": "target_kpi", "target": "GAP:ledger",
            "params": {}, "predicted_bucket": "heavy_cells_present",
            "confidence": conf,
            "citation": u.split("GAP:ledger | ")[1].split("\n")[0][:40],
            "rationale": "test"}}
    runner = _runner([NOTE, commit("low"), commit("high")])
    # budget 420 -> low cap 8.4 < target_kpi price 9.6 -> bounce
    assert runner.step()
    assert any("confidence cap" in e for e in runner.events)
    assert runner.ledger.spent > 0                  # retry executed
    assert not runner.incidents


def test_target_kpi_site_level_is_cheaper_and_does_not_close_the_ledger_gap():
    """The agent's granularity choice on target_kpi is real: site-level
    buys one entity, sets book.site_total, but never decomposes into
    per-cell T[c] — so the demand-ledger gap stays open."""
    def commit(s, u):
        return {"commit": {
            "action": "purchase", "kind": "target_kpi", "target": "GAP:ledger",
            "params": {"granularity": "site"},
            "predicted_bucket": "heavy_cells_present", "confidence": "mid",
            "citation": u.split("GAP:ledger | ")[1].split("\n")[0][:40],
            "rationale": "cheap peek before the full cell-level buy"}}
    runner = _runner([NOTE, commit])
    k = CFG.policy.comparable_days_k
    site_price = runner.provider.quote("pm", granularity="hourly",
                                       n_entities=1, hours=k)
    cell_price = runner.provider.quote("pm", granularity="hourly",
                                       n_entities=len(runner.book.cells),
                                       hours=k)
    assert site_price < cell_price
    runner.step()
    assert runner.ledger.entries[-1]["price"] == pytest.approx(site_price)
    assert runner.book.site_total is not None
    assert all(c not in runner.book.traffic for c in runner.book.cells)
    assert any(g.kind == "demand_ledger_absent" for g in runner._gaps())


def test_target_kpi_invalid_granularity_rejected():
    bad = {"commit": {
        "action": "purchase", "kind": "target_kpi", "target": "GAP:ledger",
        "params": {"granularity": "county"},
        "predicted_bucket": "heavy_cells_present", "confidence": "mid",
        "citation": "GAP:ledger", "rationale": "test"}}
    runner = _runner([NOTE, bad, bad])
    runner.step()
    assert any("granularity" in str(i) for i in runner.incidents)


def test_citation_rejection_through_the_loop():
    fabricated = {"commit": {
        "action": "purchase", "kind": "target_kpi", "target": "GAP:ledger",
        "params": {}, "predicted_bucket": "heavy_cells_present",
        "confidence": "mid", "citation": "totally invented numbers",
        "rationale": "test"}}
    runner = _runner([NOTE, fabricated, fabricated])
    runner.step()
    assert runner.ledger.spent == 0.0
    assert any("verbatim" in str(i) for i in runner.incidents)


def test_dismiss_needs_instrument_verification():
    dismiss = {"commit": {"action": "dismiss", "object": "V1"}}
    runner = _runner([NOTE, dismiss, dismiss])
    runner.step()
    # nothing sampled inside V1 yet -> denial both times -> incident
    assert runner.registry.get("V1").state == "hypothesized"
    assert any("dismissal needs" in str(i) for i in runner.incidents)


def test_split_object_preconditions_and_execution():
    from outage_whatif.geometry.evidence import PointObs
    runner = _runner([])
    _, denial = runner.check_commit({"action": "split", "object": "V1"},
                                    [], {}, "")
    assert "open coverage claim" in denial
    # a registered object with a wide footprint and clustered pass/fail
    obj = runner.registry.register(6000.0, 6200.0, 800.0, "agent",
                                   "split fixture", runner.raster)
    obj.state = "confirmed"
    made = open_claims_for(obj.id, runner.claims)
    obj.claim_ids = [c.cid for c in made]
    # 4 passing cells in the west, 2 failing in the east: Wilson (0.30,
    # 0.90) straddles theta (claim stays open) and the centroids sit
    # ~1.4 km apart (clustered)
    for xy in ((5250, 6050), (5250, 6350), (5450, 6050), (5450, 6350)):
        runner.grid.add(PointObs(*xy, True, True, "S2"))
    for xy in ((6750, 6050), (6750, 6350)):
        runner.grid.add(PointObs(*xy, True, False, "S3"))
    runner._rebuild()
    split = {"action": "split", "object": obj.id}
    _, denial = runner.check_commit(split, [], {}, "")
    assert denial is None
    runner._execute_split(obj.id)
    a, b = f"{obj.id}a", f"{obj.id}b"
    assert {a, b} <= {o.id for o in runner.registry.all()}
    assert runner.registry.get(obj.id).state == "dismissed"
    assert f"COV:{a}" in runner.claims and f"ROB:{b}" in runner.claims
    assert not runner.claims.get(f"COV:{obj.id}").alive


def test_drill_down_preconditions():
    runner = _runner([])
    drill = {"action": "drill_down", "claim": "CAP:S2"}
    _, denial = runner.check_commit(drill, [], {}, "")
    assert "no claim" in denial
    cap = runner.claims.add(Claim(cid="CAP:S2", ctype=CAPACITY, subject="S2",
                                  state=UNDECIDED, detail={"zone": None}))
    _, denial = runner.check_commit(drill, [], {}, "")
    assert "middle zone" in denial
    # stuck in the hourly middle zone -> approved, children spawn
    cap.detail["zone"] = "middle_zone"
    _, denial = runner.check_commit(drill, [], {}, "")
    assert denial is None
    runner._execute_drilldown("CAP:S2")
    assert cap.drilled and len(cap.children) == 3
    assert "CAP:S2:S5_c1" not in runner.claims      # only S2's cells
    assert all(k.startswith("CAP:S2:S2_c") for k in cap.children)
    # site-level data source: drill-down disabled entirely
    import dataclasses
    runner.cfg = dataclasses.replace(CFG, capacity_drilldown=False)
    _, denial = runner.check_commit(
        {"action": "drill_down", "claim": "CAP:S3"}, [], {}, "")
    assert "disabled" in denial
