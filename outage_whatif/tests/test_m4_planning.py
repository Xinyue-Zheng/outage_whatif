"""M4 tests: point-placement helpers and calibration."""

import numpy as np
import pytest

from outage_whatif.config import Config
from outage_whatif.geometry import PopulationRaster, Subregion
from outage_whatif.geometry.evidence import cell_of
from outage_whatif.planning import (build_calibration_table, densify_cells,
                                    object_points)
from outage_whatif.provider import generate_world

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


# --------------------------------------------------------------- placement
def test_object_points_edge_first_one_per_cell():
    sub, raster = _sub(500, n_pix=60)
    rng = np.random.default_rng(3)
    pts = object_points(sub, raster, CFG, rng, k=10)
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
    assert tab.version.startswith("calib-v2-matched")


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
