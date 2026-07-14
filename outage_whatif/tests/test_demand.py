"""Demand-layer tests: candidate zone, confirm/dismiss transitions, cell
statuses, residual/importance bounds, severity, and the ghost-village
(residual registration) path."""

import numpy as np
import pytest

from outage_whatif.claims import ClaimSet, open_claims_for
from outage_whatif.config import Config
from outage_whatif.demand import (CellLocalizationBook, ObjectRegistry,
                                  build_candidates, footprint_hull)
from outage_whatif.demand.localization import (ACCOUNTED, UNACCOUNTED,
                                               UNKNOWN)
from outage_whatif.demand.objects import in_candidate_zone
from outage_whatif.geometry.evidence import EvidenceGrid, PointObs
from outage_whatif.geometry.raster import PopulationRaster
from outage_whatif.planning.sampling import random_probe_points
from outage_whatif.provider import SimProvider, Topology, Window, generate_world
from outage_whatif.verdict.verdict import SEVERE_NO, SEVERE_UND, SEVERE_YES

CFG = Config()

SITES = {"T": (1200.0, 1200.0), "S2": (5000.0, 1200.0), "S3": (1200.0, 5000.0)}
CELLS = ["T_c0", "T_c1", "T_c2"]


def _raster():
    pop = np.zeros((60, 60))
    pop[10:14, 10:14] = 30.0     # village near the target -> candidate
    pop[44:47, 44:47] = 40.0     # village far beyond the second site -> not
    return PopulationRaster(pop=pop, x0=0.0, y0=0.0, pixel_m=100.0)


def _topology():
    return Topology(sites=dict(SITES),
                    roster={c: "T" for c in CELLS})


# ------------------------------------------------------------ candidate zone
def test_candidate_zone_membership():
    m = CFG.policy.candidate_margin_m
    assert in_candidate_zone(1300.0, 1300.0, SITES["T"], SITES, m)
    # far corner: target is much farther than the two other sites
    assert not in_candidate_zone(4500.0, 4500.0, SITES["T"], SITES, m)


def test_build_candidates_filters_and_renumbers():
    registry = build_candidates(_topology(), "T", _raster(), CFG)
    objs = registry.all()
    assert len(objs) == 1                       # far village never offered
    obj = objs[0]
    assert obj.id == "V1" and obj.state == "hypothesized"
    assert obj.provenance == ["raster"]
    assert obj.geometry_type == "area"
    assert obj.population == pytest.approx(16 * 30.0)


def test_random_probes_stay_in_zone():
    rng = np.random.default_rng(4)
    pts = random_probe_points(SITES["T"], SITES, CFG, rng)
    assert len(pts) == CFG.suggested_random_probes
    m = CFG.policy.candidate_margin_m
    assert all(in_candidate_zone(x, y, SITES["T"], SITES, m) for x, y in pts)


# ------------------------------------------------------------ transitions
def test_confirmation_needs_target_visible_point_inside():
    registry = build_candidates(_topology(), "T", _raster(), CFG)
    raster = _raster()
    # a point inside V1 but NOT showing the target: no confirmation
    assert registry.refresh_confirmations(
        [PointObs(1150, 1150, False, False, None)], raster) == []
    # outside the object, showing the target: still no confirmation
    assert registry.refresh_confirmations(
        [PointObs(3000, 3000, True, True, "S2")], raster) == []
    # inside + target above tau_acc -> confirmed; claims open (by the loop)
    newly = registry.refresh_confirmations(
        [PointObs(1150, 1150, True, True, "S2")], raster)
    assert [o.id for o in newly] == ["V1"]
    assert registry.get("V1").state == "confirmed"
    claims = ClaimSet()
    made = open_claims_for("V1", claims)
    assert {c.cid for c in made} == {"COV:V1", "ROB:V1"}


def test_dismissal_is_instrument_verified():
    registry = build_candidates(_topology(), "T", _raster(), CFG)
    raster = _raster()
    grid = EvidenceGrid(cell_m=CFG.evidence_cell_m)
    # too few sampled units inside
    grid.add(PointObs(1050, 1050, False, False, None))
    reason = registry.verify_dismiss("V1", grid, raster, CFG)
    assert reason and "units" in reason
    # enough units, but one unit shows the target
    for xy in ((1050, 1350), (1350, 1050)):
        grid.add(PointObs(*xy, False, False, None))
    grid.add(PointObs(1350, 1350, True, True, "S2"))
    reason = registry.verify_dismiss("V1", grid, raster, CFG)
    assert reason and "show the target" in reason
    # enough units, none showing the target -> verified
    grid2 = EvidenceGrid(cell_m=CFG.evidence_cell_m)
    for xy in ((1050, 1050), (1050, 1350), (1350, 1050), (1350, 1350)):
        grid2.add(PointObs(*xy, False, False, None))
    assert registry.verify_dismiss("V1", grid2, raster, CFG) is None
    registry.dismiss("V1")
    assert registry.get("V1").state == "dismissed"
    assert registry.non_dismissed() == []


# ------------------------------------------------------------ localization
def _book_with_objects():
    raster = _raster()
    registry = build_candidates(_topology(), "T", _raster(), CFG)
    book = CellLocalizationBook("T", SITES["T"], CELLS)
    # T_c0: three units, all inside V1 (pixels 10..13 -> 1000..1400 m)
    for xy in ((1050, 1050), (1050, 1350), (1350, 1350)):
        book.add_point(*xy, "T_c0")
    # T_c1: three units, one outside every object
    for xy in ((1350, 1050), (1150, 1150), (2500, 900)):
        book.add_point(*xy, "T_c1")
    # T_c2: a single unit -> unknown
    book.add_point(900, 2500, "T_c2")
    return book, registry, raster


def test_cell_statuses():
    book, registry, raster = _book_with_objects()
    assert book.status("T_c0", registry, raster, CFG) == ACCOUNTED
    assert book.status("T_c1", registry, raster, CFG) == UNACCOUNTED
    assert book.status("T_c2", registry, raster, CFG) == UNKNOWN


def test_residual_and_importance_bounds():
    book, registry, raster = _book_with_objects()
    # ledger incomplete -> no residual bound (audit gap instead)
    assert book.residual_bound(registry, raster, CFG) is None
    book.set_traffic("T_c0", 100.0)
    book.set_traffic("T_c1", 60.0)
    book.set_traffic("T_c2", 40.0)
    # unaccounted + unknown cells count against the bound; no splitting
    assert book.residual_bound(registry, raster, CFG) == pytest.approx(0.5)
    # V1 intersects T_c0 and T_c1 -> whole T of both cells counts
    assert book.importance_bound("V1", registry, raster, CFG) == \
        pytest.approx(160.0)
    rm = book.residual_map(registry, raster, CFG)
    assert rm["T_c1"]["status"] == UNACCOUNTED
    assert (2500.0, 900.0) in rm["T_c1"]["unmapped_points"]
    assert rm["T_c0"]["direction"] is not None
    assert rm["T_c2"]["direction"] is None       # below min_dir_samples


def test_hole_severity_rules():
    book, registry, raster = _book_with_objects()
    book.set_traffic("T_c0", 250.0)              # >= T_severe
    book.set_traffic("T_c1", 60.0)
    book.set_traffic("T_c2", 40.0)
    # V1 is the sole explanation of heavy T_c0 -> severe
    assert book.hole_severity("V1", set(), registry, raster, CFG) == SEVERE_YES
    # light sole cell -> not severe
    book.set_traffic("T_c0", 100.0)
    assert book.hole_severity("V1", set(), registry, raster, CFG) == SEVERE_NO
    # sole cell with unknown T -> severity undecided
    del book.traffic["T_c0"]
    assert book.hole_severity("V1", set(), registry, raster, CFG) == SEVERE_UND
    # V1 shares ALL its cells with an intact object -> severity undecided
    book.set_traffic("T_c0", 250.0)
    twin = registry.register(1200.0, 1200.0, 300.0, "agent", "twin", raster)
    assert book.hole_severity("V1", {twin.id}, registry, raster, CFG) \
        == SEVERE_UND


# ------------------------------------------------------------ ghost village
def test_ghost_registration_path():
    """The canonical residual mechanism: demand points at empty raster ->
    RegisterObject(provenance='residual') -> confirmation on evidence."""
    raster = _raster()
    registry = build_candidates(_topology(), "T", raster, CFG)
    book = CellLocalizationBook("T", SITES["T"], CELLS)
    for xy in ((2400, 800), (2500, 1200), (2800, 900)):
        book.add_point(*xy, "T_c2")              # served demand, empty raster
    book.set_traffic("T_c2", 180.0)
    assert book.status("T_c2", registry, raster, CFG) == UNACCOUNTED
    rm = book.residual_map(registry, raster, CFG)
    pts = rm["T_c2"]["unmapped_points"]
    assert len(pts) == 3
    # register where the residual map points, on population-free pixels
    cx = float(np.mean([p[0] for p in pts]))
    cy = float(np.mean([p[1] for p in pts]))
    ghost = registry.register(cx, cy, 300.0, "residual",
                              "unaccounted T_c2 demand", raster)
    assert ghost.id == "R1" and ghost.population == pytest.approx(0.0)
    assert ghost.state == "hypothesized"
    newly = registry.refresh_confirmations(
        [PointObs(cx, cy, True, True, "S2")], raster)
    assert [o.id for o in newly] == ["R1"]
    # the demand is now accounted for
    assert book.status("T_c2", registry, raster, CFG) == ACCOUNTED


# ------------------------------------------------------------ instruments
def test_footprint_hull():
    pts = [(0, 0), (1000, 0), (1000, 1000), (0, 1000), (500, 500), (200, 300)]
    hull = footprint_hull(pts)
    assert set(hull) == {(0, 0), (1000, 0), (1000, 1000), (0, 1000)}
    assert footprint_hull([(0, 0), (10, 10)]) == [(0.0, 0.0), (10.0, 10.0)]


def test_audit_round_zero_is_fundable_and_gaps_close():
    from outage_whatif.loop.audit import audit

    raster = _raster()
    registry = build_candidates(_topology(), "T", raster, CFG)
    book = CellLocalizationBook("T", SITES["T"], CELLS)
    claims = ClaimSet()
    probes = [(1500.0, 1500.0)]
    gaps = audit(book, registry, claims, raster, CFG, probes=probes)
    kinds = {g.kind for g in gaps}
    # round zero: no ledger, unlocalized cells, hypothesized object
    assert {"demand_ledger_absent", "cell_unlocalized",
            "object_hypothesized"} <= kinds
    cell_gap = next(g for g in gaps if g.kind == "cell_unlocalized")
    assert cell_gap.suggested_points == probes    # suggested, never executed

    # fill the ledger, localize all cells, confirm the object with claims
    for xy, c in (((1050, 1050), "T_c0"), ((1050, 1350), "T_c0"),
                  ((1350, 1350), "T_c0")):
        book.add_point(*xy, c)
    for c, t in (("T_c0", 100.0), ("T_c1", 5.0), ("T_c2", 5.0)):
        book.set_traffic(c, t)                    # T_c1/2 below T_material
    registry.refresh_confirmations(
        [PointObs(1150, 1150, True, True, "S2")], raster)
    obj = registry.get("V1")
    obj.claim_ids = [c.cid for c in open_claims_for("V1", claims)]
    gaps2 = audit(book, registry, claims, raster, CFG)
    kinds2 = {g.kind for g in gaps2}
    assert "demand_ledger_absent" not in kinds2
    assert "object_hypothesized" not in kinds2
    # V1 has open claims above the importance floor
    assert "object_open_claims" in kinds2
    # residual: T_c1/T_c2 are unlocalized but light; bound = 10/110 < rho
    assert "residual_uninvestigated" not in kinds2

    # resolve the claims -> the open-claims gap closes too
    for c in claims.alive():
        c.state = "supported"
    gaps3 = audit(book, registry, claims, raster, CFG)
    assert {g.kind for g in gaps3} == {"cell_unlocalized"} or \
        "object_open_claims" not in {g.kind for g in gaps3}


def test_provider_cell_level_pm_for_target():
    """The agent's first granularity decision is real: site-level = 1
    entity, cell-level = n cells, priced by entity count."""
    w = generate_world({"headroom": "mixed"}, 11, CFG)
    prov = SimProvider(w)
    win = Window.parse("2026-07-20T17:00", "2026-07-20T18:00")
    cells = [c.cell_id for c in w.cells if c.site_id == w.target_site]
    assert len(cells) == 3
    site_price = prov.quote("pm", granularity="hourly", n_entities=1, hours=1)
    cell_price = prov.quote("pm", granularity="hourly",
                            n_entities=len(cells), hours=1)
    assert cell_price == pytest.approx(3 * site_price)
    data, charged = prov.query_pm(cells, "rrc_conn", "hourly", win)
    assert set(data) == set(cells) and charged == pytest.approx(cell_price)
    assert all(len(s.samples) == 1 for s in data.values())
