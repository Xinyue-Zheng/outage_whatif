"""M3 tests: adjudication, lifecycle, verdict, flip test."""

import numpy as np
import pytest

from outage_whatif.claims import (CAPACITY, COVERAGE, REFUTED, ROBUSTNESS,
                                  SUPPORTED, UNDECIDED, Claim, ClaimSet,
                                  EvidenceView, PMStore, adjudicate_all,
                                  open_claims_for, run_lifecycle)
from outage_whatif.claims.adjudicate import (adjudicate_capacity_leaf,
                                             adjudicate_coverage,
                                             adjudicate_robustness,
                                             capacity_zone)
from outage_whatif.config import Config
from outage_whatif.geometry.evidence import CellVote
from outage_whatif.geometry.raster import PopulationRaster, Subregion
from outage_whatif.verdict import (VerdictContext, compute_verdict,
                                   flip_all_tickets, flip_ticket)
from outage_whatif.verdict.verdict import SEVERE_NO, SEVERE_YES

CFG = Config()


def votes(n_pass, n_fail, owner="S2", owner2=None, x0=0.0):
    """Fabricate footprint cell votes; alternate owners if owner2 given."""
    out = []
    for i in range(n_pass):
        o = owner if (owner2 is None or i % 2 == 0) else owner2
        out.append(CellVote(cell=(i, 0), n_points=1, in_footprint=True,
                            alt_ok=True, alt_owner=o,
                            center=(x0 + i * 300.0, 150.0)))
    for i in range(n_fail):
        out.append(CellVote(cell=(i, 1), n_points=1, in_footprint=True,
                            alt_ok=False, alt_owner=owner,
                            center=(x0 + i * 300.0, 450.0)))
    return out


def view_for(sid, cell_votes, census=False):
    v = EvidenceView()
    v.votes_by_sid[sid] = cell_votes
    fp = [c for c in cell_votes if c.in_footprint]
    owners = {}
    for c in fp:
        if c.alt_owner:
            owners[c.alt_owner] = owners.get(c.alt_owner, 0) + 1
    v.owner_shares[sid] = {s: k / len(fp) for s, k in owners.items()} if fp else {}
    # unless census=True, some cells remain unsampled -> Wilson inference
    v.unsampled_cells[sid] = [] if census else [(99, 99)]
    return v


# ------------------------------------------------------------- adjudication
def test_coverage_adjudication_three_ways():
    c = Claim(cid="COV:V1", ctype=COVERAGE, subject="V1")
    # 4 of 6 -> interval straddles theta -> undecided with named remedy
    adjudicate_coverage(c, view_for("V1", votes(4, 2)), CFG)
    assert c.state == UNDECIDED and "densify" in c.remedy
    # 40 of 40 -> supported
    adjudicate_coverage(c, view_for("V1", votes(40, 0)), CFG)
    assert c.state == SUPPORTED
    # 10 of 40 -> refuted
    adjudicate_coverage(c, view_for("V1", votes(10, 30)), CFG)
    assert c.state == REFUTED


def test_coverage_census_decides_exactly():
    """Once every evidence cell of a finite subregion is sampled, the exact
    proportion decides against theta — small villages are not condemned to
    permanent undecidedness by the Wilson interval."""
    c = Claim(cid="COV:V1", ctype=COVERAGE, subject="V1")
    # 6/6 pass, census complete -> supported although Wilson lo = 0.61 < theta
    adjudicate_coverage(c, view_for("V1", votes(6, 0), census=True), CFG)
    assert c.state == SUPPORTED and c.detail.get("census")
    # 4/6 with census -> exact 0.667 < 0.9 -> refuted
    adjudicate_coverage(c, view_for("V1", votes(4, 2), census=True), CFG)
    assert c.state == REFUTED
    r = Claim(cid="ROB:V1", ctype=ROBUSTNESS, subject="V1")
    adjudicate_robustness(r, view_for("V1", votes(6, 0, owner="S2",
                                                  owner2="S3"), census=True), CFG)
    assert r.state == SUPPORTED       # exact top share 0.5 <= kappa


def test_coverage_unaffected_subregion():
    out = [CellVote(cell=(i, 0), n_points=1, in_footprint=False, alt_ok=False,
                    alt_owner=None, center=(i * 300.0, 0.0)) for i in range(8)]
    c = Claim(cid="COV:V9", ctype=COVERAGE, subject="V9")
    adjudicate_coverage(c, view_for("V9", out), CFG)
    assert c.state == SUPPORTED and c.detail["unaffected"]


def test_capacity_two_tier_and_calibration_gate():
    pol = CFG.policy
    edge = 0.55
    assert capacity_zone(0.40, edge, CFG) == "support_zone"
    assert capacity_zone(0.70, edge, CFG) == "middle_zone"
    assert capacity_zone(0.90, edge, CFG) == "refute_zone"
    # no safe edge -> the hourly tier cannot declare support
    assert capacity_zone(0.05, None, CFG) == "middle_zone"

    c = Claim(cid="CAP:S2", ctype=CAPACITY, subject="S2")
    pm = PMStore(hourly={"S2": [0.4] * 8})
    adjudicate_capacity_leaf(c, pm, edge, CFG)
    assert c.state == SUPPORTED and c.detail["tier"] == "hourly"
    assert c.detail["phrase"] == "no capacity obstacle found"

    pm = PMStore(hourly={"S2": [0.7] * 8})
    adjudicate_capacity_leaf(c, pm, edge, CFG)
    assert c.state == UNDECIDED and "15-minute" in c.remedy

    # 15-minute tier decides definitively
    n = 32
    bad = int(pol.cap15_refute_frac * n) + 2
    pm = PMStore(hourly={"S2": [0.7] * 8},
                 q15={"S2": [0.95] * bad + [0.5] * (n - bad)})
    adjudicate_capacity_leaf(c, pm, edge, CFG)
    assert c.state == REFUTED
    pm = PMStore(q15={"S2": [0.5] * n})
    adjudicate_capacity_leaf(c, pm, edge, CFG)
    assert c.state == SUPPORTED


def test_robustness_adjudication():
    c = Claim(cid="ROB:V1", ctype=ROBUSTNESS, subject="V1")
    # all one owner, many cells -> concentrated -> refuted
    adjudicate_robustness(c, view_for("V1", votes(30, 0)), CFG)
    assert c.state == REFUTED and c.detail["top_owner"] == "S2"
    # 50/50 two owners, many cells -> hi < kappa -> supported
    adjudicate_robustness(c, view_for("V1", votes(100, 0, owner="S2", owner2="S3")), CFG)
    assert c.state == SUPPORTED
    # few cells -> undecided
    adjudicate_robustness(c, view_for("V1", votes(3, 0)), CFG)
    assert c.state == UNDECIDED


# ------------------------------------------------------------- verdict
def _ctx(pop=100, majors=("S2",), severity=None):
    return VerdictContext(sids=["V1"], populations={"V1": pop},
                          major_exits={"V1": list(majors)},
                          hole_severity=severity or {}, policy=CFG.policy)


def test_verdict_definitional_rules():
    # refuted coverage -> hole; severe iff the localization book says the
    # object is the sole explanation for a heavy cell
    states = {"COV:V1": REFUTED, "CAP:S2": SUPPORTED, "ROB:V1": SUPPORTED}
    v = compute_verdict(states, _ctx(severity={"V1": SEVERE_YES}))
    assert v.per_subregion["V1"].tier == "hole"
    assert v.per_subregion["V1"].severe == SEVERE_YES
    assert v.overall == "severe hole exists"
    v = compute_verdict(states, _ctx())
    assert v.per_subregion["V1"].severe == SEVERE_NO
    assert v.overall == "locally degraded"
    # all three supported -> absorbable / fully absorbable
    states["COV:V1"] = SUPPORTED
    v = compute_verdict(states, _ctx())
    assert v.per_subregion["V1"].tier == "absorbable"
    assert v.overall == "fully absorbable"


def test_verdict_residual_bound_qualifies_full_absorption():
    states = {"COV:V1": SUPPORTED, "CAP:S2": SUPPORTED, "ROB:V1": SUPPORTED}
    ctx = _ctx()
    ctx.residual_ok = False
    v = compute_verdict(states, ctx)
    assert v.per_subregion["V1"].tier == "absorbable"
    assert v.overall == "undecided/qualified"


def test_verdict_capacity_refutation_is_terminal():
    states = {"COV:V1": UNDECIDED, "CAP:S2": REFUTED, "ROB:V1": UNDECIDED}
    v = compute_verdict(states, _ctx(pop=500))
    sv = v.per_subregion["V1"]
    assert sv.tier == "degraded"
    assert sv.bottleneck_type == "capacity" and sv.bottleneck_subject == "S2"


def test_flip_ticket_revoked_by_neighbor_refutation():
    """A neighbor capacity refutation degrades the object, revoking the
    object's coverage ticket (the gate re-checks this at purchase time)."""
    ctx = _ctx(pop=100)
    states = {"COV:V1": UNDECIDED, "CAP:S2": UNDECIDED, "ROB:V1": UNDECIDED}
    open_cids = ["COV:V1", "CAP:S2", "ROB:V1"]

    tickets = flip_all_tickets(open_cids, states, ctx)
    assert tickets["COV:V1"]           # hole vs (capacity-gated) outcome differ
    assert tickets["CAP:S2"]
    # robustness is masked while coverage/capacity are open -> no ticket
    assert not tickets["ROB:V1"]

    # the flip test confirms revocation under the override
    assert not flip_ticket("COV:V1", states, ctx, {"CAP:S2": REFUTED})


# ------------------------------------------------------------- lifecycle
def _mini_raster():
    pop = np.zeros((30, 30))
    pop[10:12, 10:14] = 25.0
    return PopulationRaster(pop=pop, x0=0.0, y0=0.0, pixel_m=100.0)


def test_lifecycle_spawn_and_kill_capacity():
    raster = _mini_raster()
    sub = Subregion(sid="V1", pixels=[(10, 10), (10, 11), (10, 12), (10, 13),
                                      (11, 10), (11, 11), (11, 12), (11, 13)],
                    population=200.0, centroid=(1150.0, 1050.0))
    subregions = {"V1": sub}
    claims = ClaimSet()
    open_claims_for("V1", claims)
    view = view_for("V1", votes(10, 0, owner="S2"))
    ev = run_lifecycle(claims, view, subregions, raster, {}, CFG, round_no=1)
    assert "CAP:S2" in claims and claims.get("CAP:S2").alive
    assert any("spawned CAP:S2" in e for e in ev)
    # S2 stops being anyone's best alternative -> claim dies
    view2 = view_for("V1", votes(10, 0, owner="S4"))
    ev2 = run_lifecycle(claims, view2, subregions, raster, {}, CFG, round_no=2)
    assert not claims.get("CAP:S2").alive
    assert any("killed CAP:S2" in e for e in ev2)


def test_lifecycle_split_on_clustered_pass_fail():
    raster = _mini_raster()
    pixels = [(iy, ix) for iy in (10, 11) for ix in range(10, 20)]
    sub = Subregion(sid="V1", pixels=pixels, population=200.0,
                    centroid=(1500.0, 1100.0))
    subregions = {"V1": sub}
    raster.pop[10:12, 10:20] = 10.0
    claims = ClaimSet()
    open_claims_for("V1", claims)
    cov = claims.get("COV:V1")
    cov.state = UNDECIDED
    cov.densifications = CFG.split_after_densifications
    # pass cells on the left (x~1100), fail cells on the right (x~1900):
    # separation 800 m > 1.5 evidence cells -> clustered
    cvs = ([CellVote(cell=(3, i), n_points=1, in_footprint=True, alt_ok=True,
                     alt_owner="S2", center=(1100.0 + i * 10, 1100.0))
            for i in range(3)] +
           [CellVote(cell=(6, i), n_points=1, in_footprint=True, alt_ok=False,
                     alt_owner="S2", center=(1900.0 + i * 10, 1100.0))
            for i in range(3)])
    view = view_for("V1", cvs)
    ev = run_lifecycle(claims, view, subregions, raster, {}, CFG, round_no=3)
    assert any("split V1" in e for e in ev)
    assert "V1" not in subregions and {"V1a", "V1b"} <= set(subregions)
    assert not claims.get("COV:V1").alive
    assert claims.get("COV:V1a").alive and claims.get("COV:V1b").alive
    assert claims.get("ROB:V1a").alive
    # population conserved across the split
    assert (subregions["V1a"].population + subregions["V1b"].population
            == pytest.approx(200.0))


def test_lifecycle_capacity_drilldown():
    raster = _mini_raster()
    subregions = {}
    claims = ClaimSet()
    cap = claims.add(Claim(cid="CAP:S2", ctype=CAPACITY, subject="S2",
                           state=UNDECIDED,
                           detail={"zone": "middle_zone"},
                           rounds_undecided=CFG.drilldown_after_rounds))
    roster = {"S2_c0": "S2", "S2_c1": "S2", "S2_c2": "S2", "S3_c0": "S3"}
    view = EvidenceView(owner_shares={"V1": {"S2": 1.0}})
    ev = run_lifecycle(claims, view, subregions, raster, roster, CFG, round_no=4)
    assert cap.drilled
    assert len(cap.children) == 3
    assert "CAP:S2:S2_c1" in claims
    assert any("drilled down" in e for e in ev)


def test_lifecycle_drilldown_disabled_for_site_level_analysis():
    import dataclasses
    cfg = dataclasses.replace(CFG, capacity_drilldown=False)
    raster = _mini_raster()
    claims = ClaimSet()
    cap = claims.add(Claim(cid="CAP:S2", ctype=CAPACITY, subject="S2",
                           state=UNDECIDED,
                           detail={"zone": "middle_zone"},
                           rounds_undecided=cfg.drilldown_after_rounds))
    roster = {"S2_c0": "S2", "S2_c1": "S2", "S2_c2": "S2"}
    view = EvidenceView(owner_shares={"V1": {"S2": 1.0}})
    ev = run_lifecycle(claims, view, {}, raster, roster, cfg, round_no=4)
    assert not cap.drilled and not cap.children
    assert not any("drilled down" in e for e in ev)
