"""Point-placement helpers (deterministic).

Nothing here auto-executes: densification is the named remedy of an
undecided coverage/robustness claim (a purchase the agent must request and
the gate must approve), and random exploration probes are a suggested
gap-remedy surfaced by the audit — never a fixed startup phase.
"""

from __future__ import annotations

import math

import numpy as np

from ..config import Config
from ..geometry.evidence import cell_of
from ..geometry.raster import PopulationRaster, Subregion


def _cells_edge_first(sub: Subregion, raster: PopulationRaster,
                      cfg: Config) -> list:
    """An area object's evidence cells ordered edge-first (distance from the
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
    """A sample coordinate inside the given cell, at one of the object's
    pixels there (jittered within the pixel)."""
    cands = [(iy, ix) for iy, ix in sub.pixels
             if cell_of(*raster.pixel_center(iy, ix), cfg.evidence_cell_m) == cell]
    iy, ix = cands[rng.integers(len(cands))]
    x, y = raster.pixel_center(iy, ix)
    j = raster.pixel_m / 2.0
    return (x + rng.uniform(-j, j), y + rng.uniform(-j, j))


def object_points(sub: Subregion, raster: PopulationRaster, cfg: Config,
                  rng: np.random.Generator, k: int) -> list:
    """Up to k points, one per evidence cell, edge-first — the standard
    probe layout for an area object."""
    order = _cells_edge_first(sub, raster, cfg)
    return [_point_in_cell(sub, raster, c, cfg, rng) for c in order[:k]]


def densify_cells(sub: Subregion, raster: PopulationRaster, unsampled: list,
                  cfg: Config, rng: np.random.Generator,
                  k: int | None = None) -> list:
    """Remedy for an undecided coverage/robustness claim: points in up to k
    *unsampled* evidence cells, edge-first."""
    k = k if k is not None else cfg.densify_cells_per_round
    order = [c for c in _cells_edge_first(sub, raster, cfg) if c in set(unsampled)]
    return [_point_in_cell(sub, raster, c, cfg, rng) for c in order[:k]]
