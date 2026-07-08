"""Population raster segmentation (deterministic).

Pipeline (Section 3 of the design):
  1. density-filter the raster;
  2. 8-connected clustering of remaining pixels -> settlement subregions;
  3. merge small fragments; pool stray population into one background region;
  4. [POLICY] P_min filter: settlements with population < P_min get no
     individual claims and are absorbed into the background region.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage

from ..config import Config


@dataclass
class PopulationRaster:
    """pop[iy, ix] people per pixel; pixel (0,0) has its lower-left corner
    at (x0, y0); pixel size = pixel_m metres."""
    pop: np.ndarray
    x0: float
    y0: float
    pixel_m: float

    def pixel_center(self, iy: int, ix: int) -> tuple[float, float]:
        return (self.x0 + (ix + 0.5) * self.pixel_m,
                self.y0 + (iy + 0.5) * self.pixel_m)

    def total(self) -> float:
        return float(self.pop.sum())


@dataclass
class Subregion:
    """A populated settlement subregion (or the background region)."""
    sid: str
    pixels: list = field(default_factory=list)     # list[(iy, ix)]
    population: float = 0.0
    centroid: tuple = (0.0, 0.0)                   # metres
    is_background: bool = False
    # settlements < P_min absorbed here (background only); for the report
    absorbed_small_settlements: int = 0
    absorbed_small_population: float = 0.0

    def pixel_centers(self, raster: PopulationRaster) -> list[tuple[float, float]]:
        return [raster.pixel_center(iy, ix) for iy, ix in self.pixels]


_EIGHT_CONNECTED = np.ones((3, 3), dtype=int)


def segment_raster(raster: PopulationRaster, cfg: Config) -> tuple[list[Subregion], Subregion]:
    """Return (settlement subregions, background region).

    The background region owns: stray population below the density filter,
    fragments smaller than min_settlement_pixels, and settlements with
    population < P_min ([POLICY]).  The Track-2 background grid still covers
    it; the report must disclose the P_min absorption.
    """
    dense = raster.pop >= cfg.density_min_pop
    labels, n_lab = ndimage.label(dense, structure=_EIGHT_CONNECTED)

    background = Subregion(sid="BG", is_background=True)
    # stray population: everything failing the density filter
    background.population += float(raster.pop[~dense].sum())

    settlements: list[Subregion] = []
    for lab in range(1, n_lab + 1):
        ys, xs = np.nonzero(labels == lab)
        pixels = list(zip(ys.tolist(), xs.tolist()))
        pop = float(raster.pop[ys, xs].sum())
        if len(pixels) < cfg.min_settlement_pixels:
            # small fragment -> pooled into background
            background.population += pop
            background.pixels.extend(pixels)
            continue
        if pop < cfg.policy.P_min:
            # [POLICY] P_min filter: absorbed into background, disclosed in report
            background.population += pop
            background.pixels.extend(pixels)
            background.absorbed_small_settlements += 1
            background.absorbed_small_population += pop
            continue
        w = raster.pop[ys, xs]
        cx = float(np.average(raster.x0 + (xs + 0.5) * raster.pixel_m, weights=w))
        cy = float(np.average(raster.y0 + (ys + 0.5) * raster.pixel_m, weights=w))
        settlements.append(Subregion(
            sid="", pixels=pixels, population=pop, centroid=(cx, cy)))

    # deterministic IDs: sort by population descending, then centroid
    settlements.sort(key=lambda s: (-s.population, s.centroid))
    for i, s in enumerate(settlements, start=1):
        s.sid = f"V{i}"
    return settlements, background
