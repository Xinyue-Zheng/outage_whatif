"""M1 tests: Wilson machinery, segmentation, evidence cells."""

import numpy as np
import pytest

from outage_whatif.config import Config
from outage_whatif.geometry import (
    EvidenceGrid, PopulationRaster, cell_of, n_all_pass_clears,
    segment_raster, wilson_interval)
from outage_whatif.geometry.evidence import PointObs

CFG = Config()


# ---------------------------------------------------------------- Wilson
def test_wilson_4_of_6_is_undecided_by_arithmetic():
    """Design test: 4 of 6 cells -> interval ~ [0.30, 0.90] -> straddles theta."""
    lo, hi = wilson_interval(4, 6, z=1.96)
    assert lo == pytest.approx(0.30, abs=0.02)
    assert hi == pytest.approx(0.90, abs=0.02)
    theta = CFG.policy.theta
    assert lo < theta < hi or hi == pytest.approx(theta, abs=0.02)
    # not entirely above and not entirely below theta -> undecided
    assert not (lo > theta)
    assert not (hi < theta)


def test_wilson_bounds_and_monotonicity():
    assert wilson_interval(0, 0) == (0.0, 1.0)
    lo0, hi0 = wilson_interval(0, 10)
    assert lo0 == 0.0 and hi0 < 0.35
    lo1, hi1 = wilson_interval(10, 10)
    assert hi1 == 1.0 and lo1 > 0.65
    # more evidence at same proportion tightens the interval
    lo_a, hi_a = wilson_interval(9, 10)
    lo_b, hi_b = wilson_interval(90, 100)
    assert (hi_b - lo_b) < (hi_a - lo_a)


def test_decide_in_one_round_allocation_is_computed():
    """theta=0.90, z=1.96 -> 35 evidence cells; must come from the formula."""
    n = n_all_pass_clears(0.90, 1.96)
    assert n == 35
    assert wilson_interval(n, n)[0] > 0.90
    assert wilson_interval(n - 1, n - 1)[0] <= 0.90
    # different theta gives a different n (nothing hardcoded)
    assert n_all_pass_clears(0.80, 1.96) < 35


# ---------------------------------------------------------------- segmentation
def _raster_with_villages():
    pop = np.zeros((60, 60))
    pop[10:14, 10:14] = 30.0     # village A: 16 px * 30 = 480
    pop[40:43, 40:43] = 12.0     # village B: 9 px * 12 = 108
    pop[50:52, 8:10] = 8.0       # small settlement: 4 px * 8 = 32 < P_min
    pop[5, 50] = 5.0             # fragment: 1 px < min_settlement_pixels
    pop[30, 30] = 0.5            # below density filter -> stray
    return PopulationRaster(pop=pop, x0=0.0, y0=0.0, pixel_m=100.0)


def test_segmentation_p_min_and_background():
    raster = _raster_with_villages()
    settlements, bg = segment_raster(raster, CFG)
    assert [s.sid for s in settlements] == ["V1", "V2"]
    assert settlements[0].population == pytest.approx(480)
    assert settlements[1].population == pytest.approx(108)
    # background pools: sub-P_min settlement + fragment + stray
    assert bg.absorbed_small_settlements == 1
    assert bg.absorbed_small_population == pytest.approx(32)
    assert bg.population == pytest.approx(32 + 5 + 0.5)
    # total mass conserved
    total = sum(s.population for s in settlements) + bg.population
    assert total == pytest.approx(raster.total())


def test_eight_connected_clustering_joins_diagonals():
    pop = np.zeros((10, 10))
    pop[2, 2] = pop[3, 3] = pop[4, 4] = 60.0   # diagonal chain
    raster = PopulationRaster(pop=pop, x0=0.0, y0=0.0, pixel_m=100.0)
    settlements, bg = segment_raster(raster, CFG)
    assert len(settlements) == 1
    assert settlements[0].population == pytest.approx(180)


# ---------------------------------------------------------------- evidence cells
def test_evidence_cell_majority_vote_single_unit():
    grid = EvidenceGrid(cell_m=300.0)
    # three points in the same 300 m cell: 2 pass / 1 fail -> one passing unit
    grid.add(PointObs(10, 10, True, True, "S2"))
    grid.add(PointObs(100, 100, True, True, "S2"))
    grid.add(PointObs(250, 250, True, False, "S3"))
    assert len(grid.sampled_cells()) == 1
    v = grid.vote((0, 0))
    assert v.n_points == 3
    assert v.in_footprint and v.alt_ok
    assert v.alt_owner == "S2"


def test_evidence_cell_out_of_footprint_majority():
    grid = EvidenceGrid(cell_m=300.0)
    grid.add(PointObs(10, 10, False, False, None))
    grid.add(PointObs(20, 20, False, False, None))
    grid.add(PointObs(30, 30, True, True, "S2"))
    v = grid.vote((0, 0))
    assert not v.in_footprint and not v.alt_ok


def test_cell_indexing():
    assert cell_of(0, 0, 300) == (0, 0)
    assert cell_of(299.9, 299.9, 300) == (0, 0)
    assert cell_of(300.0, 0, 300) == (1, 0)
    assert cell_of(-1, -1, 300) == (-1, -1)
