"""M2 tests: simulator reproducibility, pricing, same-site filtering."""

import pytest

from outage_whatif.config import Config
from outage_whatif.geometry.footprint import analyze_coverage_point
from outage_whatif.provider import (PriceBook, SimProvider, Window,
                                    generate_world)
from outage_whatif.provider.interface import PointCoverage
from outage_whatif.provider.simulator import World, SimCell

CFG = Config()
SPEC = {"headroom": "mixed", "weak_neighbors": 1, "village_count": 7,
        "n_extra_sites": 1}


def _window():
    return Window.parse("2026-07-20T10:00", "2026-07-20T18:00")


# ------------------------------------------------------------ reproducibility
def test_world_reproducible_from_seed():
    w1, w2 = generate_world(SPEC, 42, CFG), generate_world(SPEC, 42, CFG)
    assert w1.sites == w2.sites
    assert [c.cell_id for c in w1.cells] == [c.cell_id for c in w2.cells]
    assert w1.u_base == w2.u_base
    assert [(v.name, v.x, v.pop) for v in w1.villages] == \
           [(v.name, v.x, v.pop) for v in w2.villages]

    p1, p2 = SimProvider(w1), SimProvider(w2)
    pts = [(4000.0, 4100.0), (5200.0, 6100.0)]
    assert p1.query_coverage(pts) == p2.query_coverage(pts)
    win = _window()
    d1, c1 = p1.query_pm(["S4"], "prb_util", "15min", win)
    d2, c2 = p2.query_pm(["S4"], "prb_util", "15min", win)
    assert d1["S4"].samples == d2["S4"].samples and c1 == c2


def test_different_seed_differs():
    w1, w2 = generate_world(SPEC, 42, CFG), generate_world(SPEC, 43, CFG)
    assert w1.sites != w2.sites or w1.u_base != w2.u_base


def test_forced_villages_present():
    w = generate_world(SPEC, 7, CFG)
    names = {v.name for v in w.villages}
    assert {"big", "straddler", "ghost", "tiny"} <= names
    ghost = next(v for v in w.villages if v.name == "ghost")
    assert not ghost.in_raster
    # the raster genuinely omits the ghost village: total raster mass is
    # bounded by the in-raster village populations (spillover from neighbours
    # may put a little mass near the ghost, but the ghost adds none)
    raster = w.raster()
    in_raster_pop = sum(v.pop for v in w.villages if v.in_raster)
    assert raster.total() <= in_raster_pop + 1e-6
    ix, iy = int(ghost.x // 100), int(ghost.y // 100)
    patch = raster.pop[max(iy - 2, 0):iy + 3, max(ix - 2, 0):ix + 3]
    assert patch.sum() < ghost.pop * 0.25


# ------------------------------------------------------------ pricing
def test_price_function_rules():
    book = PriceBook()
    # coverage super-linear: doubling points more than doubles price
    assert book.coverage(40) > 2 * book.coverage(20)
    # PM scales with granularity factor, entities, hours
    assert book.pm("15min", 1, 8) == pytest.approx(4 * book.pm("hourly", 1, 8))
    assert book.pm("hourly", 3, 8) == pytest.approx(3 * book.pm("hourly", 1, 8))
    assert book.profile("same_weekday") > 0
    assert book.quote("coverage", n_points=10) == book.coverage(10)


def test_pm_window_and_granularity_shape():
    w = generate_world(SPEC, 11, CFG)
    prov = SimProvider(w)
    win = _window()
    hourly, _ = prov.query_pm(["S4"], "prb_util", "hourly", win)
    q15, _ = prov.query_pm(["S4"], "prb_util", "15min", win)
    assert len(hourly["S4"].samples) == 8
    assert len(q15["S4"].samples) == 32
    assert all(0.0 <= v <= 1.0 for v in q15["S4"].values())
    # holiday factor lifts weekday-shape load (2026-07-04 is in the calendar)
    hol, _ = prov.query_pm(["S4"], "prb_util", "hourly",
                           Window.parse("2026-07-04T10:00", "2026-07-04T18:00"))
    # same clock hours, holiday vs a plain Monday: holiday mean higher than sunday-like
    sun, _ = prov.query_pm(["S4"], "prb_util", "hourly",
                           Window.parse("2026-07-05T10:00", "2026-07-05T18:00"))
    import numpy as np
    assert np.mean(hol["S4"].values()) > np.mean(sun["S4"].values())


# ------------------------------------------------------------ same-site filtering
def test_same_site_filtering_changes_best_alternative():
    """Constructed scenario: near the target site, co-sited cells are the
    strongest backups.  Omitting same-site filtering keeps them as
    'alternatives' and overstates absorbability."""
    target_cells = [SimCell(f"T_c{k}", "T", 5000, 5000, 120.0 * k, 0.0)
                    for k in range(3)]
    far_cell = [SimCell("F_c0", "F", 11000, 5000, 180.0, 0.0)]
    w = World(seed=1, field_m=12000, sites={"T": (5000, 5000), "F": (11000, 5000)},
              cells=target_cells + far_cell, target_site="T", villages=[],
              u_base={"T": 0.3, "F": 0.3}, spikiness={"T": 0.1, "F": 0.1},
              cell_factor={c.cell_id: 1.0 for c in target_cells + far_cell},
              terrain_amp=0.0)
    roster = {c.cell_id: c.site_id for c in w.cells}
    pc = w.coverage_at(5100, 5000)     # 100 m from target, 5.9 km from F
    with_filter = analyze_coverage_point(pc, "T", roster, CFG.tau_acc)
    without = analyze_coverage_point(pc, "T", roster, CFG.tau_acc,
                                     same_site_filtering=False)
    assert with_filter.in_footprint and without.in_footprint
    # broken variant finds a strong co-sited "alternative" -> overstates
    assert without.alt_ok and without.alt_owner == "T"
    # mandatory filter deletes every target cell -> only F remains, too far
    assert with_filter.alt_owner in (None, "F")
    assert not with_filter.alt_ok


def test_coverage_top5_structure():
    w = generate_world(SPEC, 5, CFG)
    pc = w.coverage_at(5000, 5000)
    assert isinstance(pc, PointCoverage)
    assert len(pc.backups) == 5
    rsrps = [pc.serving[1]] + [r for _, r in pc.backups]
    assert rsrps == sorted(rsrps, reverse=True)
