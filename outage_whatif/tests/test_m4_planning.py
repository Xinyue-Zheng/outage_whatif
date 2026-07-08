"""M4 tests: sampling tracks, action menu + quartiles, calibration."""

import numpy as np
import pytest

from outage_whatif.claims import Claim, ClaimSet, EvidenceView, initial_claims
from outage_whatif.claims.model import CAPACITY, UNDECIDED
from outage_whatif.config import Config
from outage_whatif.geometry import Boundary, PopulationRaster, Subregion
from outage_whatif.geometry.evidence import cell_of
from outage_whatif.geometry.wilson import n_all_pass_clears
from outage_whatif.planning import (Action, allocation_for,
                                    background_grid_points,
                                    build_calibration_table, build_menu,
                                    cheapest_price_map, densify_cells,
                                    initial_settlement_points)
from outage_whatif.provider import SimProvider, Window, generate_world

CFG = Config()


def _sub(pop, n_pix=40):
    pixels = [(20 + i // 10, 20 + i % 10) for i in range(n_pix)]
    pop_arr = np.zeros((60, 60))
    for iy, ix in pixels:
        pop_arr[iy, ix] = pop / n_pix
    raster = PopulationRaster(pop=pop_arr, x0=0.0, y0=0.0, pixel_m=100.0)
    xs = [raster.pixel_center(iy, ix) for iy, ix in pixels]
    cx = float(np.mean([p[0] for p in xs]))
    cy = float(np.mean([p[1] for p in xs]))
    return Subregion(sid="V1", pixels=pixels, population=pop,
                     centroid=(cx, cy)), raster


# --------------------------------------------------------------- sampling
def test_track1_allocation_rules():
    small, _ = _sub(60)
    assert allocation_for(small, CFG) == max(4, int(np.ceil(60 / (200 / 8))))
    tiny, _ = _sub(51)
    assert allocation_for(tiny, CFG) >= CFG.min_points_per_settlement
    big, _ = _sub(500)
    assert allocation_for(big, CFG) == n_all_pass_clears(CFG.policy.theta, CFG.z)


def test_track1_points_edge_first_one_per_cell():
    sub, raster = _sub(500, n_pix=60)
    rng = np.random.default_rng(3)
    pts = initial_settlement_points(sub, raster, CFG, rng)
    cells = [cell_of(x, y, CFG.evidence_cell_m) for x, y in pts]
    assert len(cells) == len(set(cells))          # one point per evidence cell
    # first sampled cell is farther from the centroid than the last (edge first)
    cx, cy = sub.centroid
    d0 = np.hypot(pts[0][0] - cx, pts[0][1] - cy)
    dl = np.hypot(pts[-1][0] - cx, pts[-1][1] - cy)
    assert d0 >= dl


def test_densify_targets_only_unsampled_cells():
    sub, raster = _sub(500, n_pix=60)
    rng = np.random.default_rng(3)
    all_cells = {cell_of(*raster.pixel_center(iy, ix), CFG.evidence_cell_m)
                 for iy, ix in sub.pixels}
    unsampled = sorted(all_cells)[:3]
    pts = densify_cells(sub, raster, unsampled, CFG, rng)
    assert 0 < len(pts) <= 3
    assert all(cell_of(x, y, CFG.evidence_cell_m) in set(unsampled)
               for x, y in pts)


def test_track2_background_grid_never_zero():
    b = Boundary(center=(6000.0, 6000.0), radii=[2000.0] * 8, n_sectors=8,
                 ring_width_factor=0.25)
    rng = np.random.default_rng(5)
    pts = background_grid_points(b, CFG, rng)
    assert len(pts) > 0
    r_max = 2000.0 * 1.25
    assert all(np.hypot(x - 6000, y - 6000) <= r_max for x, y in pts)


# --------------------------------------------------------------- menu
def _menu_fixture():
    world = generate_world({"headroom": "mixed", "village_count": 6}, 21, CFG)
    prov = SimProvider(world)
    raster = prov.population_raster()
    from outage_whatif.geometry.raster import segment_raster
    settlements, bg = segment_raster(raster, CFG)
    subregions = {s.sid: s for s in settlements}
    boundary = Boundary.initial(world.sites[world.target_site],
                                list(world.sites.values()), CFG)
    claims = initial_claims(subregions, bg, CFG)
    claims.add(Claim(cid="CAP:S2", ctype=CAPACITY, subject="S2",
                     state=UNDECIDED, detail={"tier": "none"}))
    view = EvidenceView(
        votes_by_sid={sid: [] for sid in subregions},
        unsampled_cells={sid: [(1, 1), (1, 2), (2, 2)] for sid in subregions})
    win = Window.parse("2026-07-20T10:00", "2026-07-20T18:00")
    return claims, view, subregions, bg, raster, boundary, prov, win, world


def test_menu_quartiles_buckets_and_prices():
    claims, view, subs, bg, raster, boundary, prov, win, world = _menu_fixture()
    rng = np.random.default_rng(9)
    menu = build_menu(claims, view, subs, bg, raster, boundary, prov, win,
                      CFG, rng, round_no=1, owned_profiles=set(), purchased=set())
    assert menu
    kinds = {a.kind for a in menu}
    assert "pm_hourly" in kinds and "ring_sample" in kinds
    assert "profile" in kinds                      # judgment-firming offer
    for a in menu:
        assert 1 <= a.quartile <= 4
        assert a.buckets, a.kind
        assert a.price > 0
    # hourly PM carries its worst-case follow-up (the 15-min purchase)
    pm = next(a for a in menu if a.kind == "pm_hourly")
    assert pm.followup_price == pytest.approx(
        prov.quote("pm", granularity="15min", n_entities=1, hours=8))
    assert pm.buckets == ["support_zone", "middle_zone", "refute_zone"]
    # quartile 1 exists and belongs to the cheapest action(s)
    q1 = [a for a in menu if a.quartile == 1]
    assert min(a.price for a in menu) == min(a.price for a in q1)
    # cheapest resolving action per claim (profiles excluded)
    cp = cheapest_price_map(menu)
    assert "CAP:S2" in cp
    assert cp["CAP:S2"] == pm.price


def test_menu_duplicate_suppression():
    claims, view, subs, bg, raster, boundary, prov, win, world = _menu_fixture()
    rng = np.random.default_rng(9)
    menu = build_menu(claims, view, subs, bg, raster, boundary, prov, win,
                      CFG, rng, round_no=1, owned_profiles=set(), purchased=set())
    pm = next(a for a in menu if a.kind == "pm_hourly")
    prof = next(a for a in menu if a.kind == "profile")
    menu2 = build_menu(claims, view, subs, bg, raster, boundary, prov, win,
                       CFG, rng, round_no=2,
                       owned_profiles={(prof.params["site"],
                                        prof.params["profile_kind"])},
                       purchased={pm.signature()})
    sigs = {a.signature() for a in menu2}
    assert pm.signature() not in sigs
    assert all(not (a.kind == "profile"
                    and a.params["site"] == prof.params["site"]
                    and a.params["profile_kind"] == prof.params["profile_kind"])
               for a in menu2)


# --------------------------------------------------------------- calibration
def test_calibration_edge_placement():
    # low spikiness world -> some safe support zone should exist
    calm = generate_world({"headroom": "ample", "spikiness": "low"}, 31, CFG)
    tab = build_calibration_table({"calm": calm}, CFG, days=14)
    assert tab.support_edge is not None
    assert 0.0 < tab.support_edge <= CFG.policy.pi_hi
    # every populated bucket strictly below the edge respects the 5% line
    for b, r in enumerate(tab.bucket_rates):
        if r is None:
            continue
        if (b + 1) / 10 <= tab.support_edge:
            assert r <= CFG.policy.calib_false_pass_max
    assert tab.version.startswith("calib-v1")


def test_calibration_no_safe_edge():
    # pathological platform where every hour hides 15-min spikes above pi_hi,
    # regardless of the hourly mean -> no bucket is safe -> the hourly tier
    # loses the right to declare support
    base = generate_world({"headroom": "tight", "spikiness": "high"}, 33, CFG)

    class SpikyWorld:
        sites = base.sites
        hourly_prb = staticmethod(base.hourly_prb)

        @staticmethod
        def q15_prb(entity, ts):
            return 0.99

    tab = build_calibration_table({"wild": SpikyWorld()}, CFG, days=7)
    assert tab.support_edge is None


def test_calibration_roundtrip(tmp_path):
    calm = generate_world({"headroom": "ample", "spikiness": "low"}, 31, CFG)
    tab = build_calibration_table({"calm": calm}, CFG, days=7)
    p = tmp_path / "calib.json"
    tab.save(p)
    tab2 = tab.load(p)
    assert tab2.support_edge == tab.support_edge
    assert tab2.bucket_rates == tab.bucket_rates
