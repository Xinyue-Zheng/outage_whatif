"""Sampling plan (deterministic).

Track 1 (workhorse): per-settlement point allocation proportional to
population, minimum 4 points; settlements >= P0 get a decide-in-one-round
allocation (the evidence-cell count where an all-pass Wilson lower bound
clears theta — computed from theta and z, never hardcoded).  Edge cells are
placed before center cells.

Track 2 (fuse): 3 km background grid, 2-3 random points per tile;
responsible for the footprint outline, the boundary ring, and
population-map omissions; never reduced to zero.

Densification triggers implemented: (a) undecided coverage claim ->
densify unsampled cells; (b) mixed-result boundary cells only if the flip
test says the position matters (enforced by the loop: only ticketed claims
get menu actions).  (c) The off-menu directed-probe channel is CLOSED in
this version — no critic exists to review it; do not add probe actions
outside the menu.
"""

from __future__ import annotations

import math

import numpy as np

from ..config import Config
from ..geometry.evidence import cell_of
from ..geometry.raster import PopulationRaster, Subregion
from ..geometry.wilson import n_all_pass_clears


def allocation_for(sub: Subregion, cfg: Config) -> int:
    """Evidence-cell allocation for a settlement.

    DESIGN-GAP: "proportional to population" is realised as one cell per
    P0/8 of population; the design fixes only the minimum (4) and the
    decide-in-one-round allocation for settlements >= P0.
    """
    pol = cfg.policy
    if sub.population >= pol.P0:
        return n_all_pass_clears(pol.theta, cfg.z)
    prop = math.ceil(sub.population / (pol.P0 / 8.0))
    return max(cfg.min_points_per_settlement, prop)


def _cells_edge_first(sub: Subregion, raster: PopulationRaster,
                      cfg: Config) -> list:
    """Settlement evidence cells ordered edge-first (distance from the
    centroid, descending), deterministically tie-broken."""
    cells: dict[tuple, list] = {}
    for iy, ix in sub.pixels:
        x, y = raster.pixel_center(iy, ix)
        cells.setdefault(cell_of(x, y, cfg.evidence_cell_m), []).append((x, y))
    cx, cy = sub.centroid

    def edge_key(item):
        cell, pts = item
        d = max(math.hypot(x - cx, y - cy) for x, y in pts)
        return (-d, cell)

    return [cell for cell, _ in sorted(cells.items(), key=edge_key)]


def _point_in_cell(sub: Subregion, raster: PopulationRaster, cell: tuple,
                   cfg: Config, rng: np.random.Generator) -> tuple:
    """A sample coordinate inside the given cell, at one of the settlement's
    pixels there (jittered within the pixel)."""
    cands = [(iy, ix) for iy, ix in sub.pixels
             if cell_of(*raster.pixel_center(iy, ix), cfg.evidence_cell_m) == cell]
    iy, ix = cands[rng.integers(len(cands))]
    x, y = raster.pixel_center(iy, ix)
    j = raster.pixel_m / 2.0
    return (x + rng.uniform(-j, j), y + rng.uniform(-j, j))


def initial_settlement_points(sub: Subregion, raster: PopulationRaster,
                              cfg: Config, rng: np.random.Generator) -> list:
    """Track-1 initial points: one per allocated evidence cell, edge first."""
    order = _cells_edge_first(sub, raster, cfg)
    n = min(allocation_for(sub, cfg), len(order))
    return [_point_in_cell(sub, raster, c, cfg, rng) for c in order[:n]]


def densify_cells(sub: Subregion, raster: PopulationRaster, unsampled: list,
                  cfg: Config, rng: np.random.Generator,
                  k: int | None = None) -> list:
    """Remedy for an undecided coverage/robustness claim: points in up to k
    *unsampled* evidence cells, edge-first."""
    k = k if k is not None else cfg.densify_cells_per_round
    order = [c for c in _cells_edge_first(sub, raster, cfg) if c in set(unsampled)]
    return [_point_in_cell(sub, raster, c, cfg, rng) for c in order[:k]]


def background_grid_points(boundary, cfg: Config,
                           rng: np.random.Generator) -> list:
    """Track-2 fuse: random points per 3 km tile over the boundary bounding
    box including the integrity ring (the full square in static mode).
    Never reduced to zero."""
    cx, cy = boundary.center
    static = boundary.static_half_m > 0
    r_max = (boundary.static_half_m if static
             else max(boundary.radii) * (1.0 + boundary.ring_width_factor))
    g = cfg.background_grid_m
    pts = []
    x0 = math.floor((cx - r_max) / g) * g
    y0 = math.floor((cy - r_max) / g) * g
    x = x0
    while x < cx + r_max:
        y = y0
        while y < cy + r_max:
            for _ in range(int(cfg.background_pts_per_tile)):
                px, py = x + rng.uniform(0, g), y + rng.uniform(0, g)
                # keep points inside the analysis area (disc + ring | square)
                if (boundary.contains(px, py) if static
                        else math.hypot(px - cx, py - cy) <= r_max):
                    pts.append((px, py))
            y += g
        x += g
    return pts
