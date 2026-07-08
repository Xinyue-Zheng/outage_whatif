"""Analysis boundary: initial radius, direction sectors, integrity ring.

The initial boundary is deliberately rough (R0 = 0.75 x median distance to
the 6 nearest neighboring sites); the integrity claims are its correction
loop.  The boundary carries a per-sector radius so refuted integrity in one
direction expands only that sector.

Static mode (``cfg.static_area_km > 0``): the boundary is the full data
square (side = static_area_km, centered on the target), containment is an
exact square test, and there is NO integrity ring — the area is
definitionally complete, so integrity claims are never created (see
claims/lifecycle.py) and no expansion can occur.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ..config import Config


def initial_radius(target_xy: tuple[float, float],
                   site_xys: list[tuple[float, float]],
                   cfg: Config) -> float:
    """R0 = r0_factor x median distance to the n nearest neighboring sites."""
    tx, ty = target_xy
    d = sorted(math.hypot(x - tx, y - ty) for x, y in site_xys
               if (x, y) != (tx, ty))
    if not d:
        raise ValueError("no neighboring sites")
    nearest = np.array(d[:cfg.n_neighbors_for_r0])
    return cfg.r0_factor * float(np.median(nearest))


def sector_of(x: float, y: float, cx: float, cy: float, n_sectors: int) -> int:
    """Direction sector index (0..n_sectors-1) of a point around a center."""
    ang = math.atan2(y - cy, x - cx) % (2 * math.pi)
    return min(int(ang / (2 * math.pi / n_sectors)), n_sectors - 1)


@dataclass
class Boundary:
    """Per-sector analysis boundary around the target site."""
    center: tuple[float, float]
    radii: list = field(default_factory=list)   # one radius per sector
    n_sectors: int = 8
    ring_width_factor: float = 0.25
    expansions: int = 0
    static_half_m: float = 0.0                  # >0: exact square half-side

    @classmethod
    def initial(cls, target_xy, site_xys, cfg: Config) -> "Boundary":
        if cfg.static_area_km > 0:
            # static mode: the full data square, centered on the target
            half = cfg.static_area_km * 1000.0 / 2.0
            return cls(center=target_xy, radii=[half] * cfg.n_sectors,
                       n_sectors=cfg.n_sectors, ring_width_factor=0.0,
                       static_half_m=half)
        r0 = initial_radius(target_xy, site_xys, cfg)
        return cls(center=target_xy, radii=[r0] * cfg.n_sectors,
                   n_sectors=cfg.n_sectors,
                   ring_width_factor=cfg.ring_width_factor)

    def sector(self, x: float, y: float) -> int:
        return sector_of(x, y, self.center[0], self.center[1], self.n_sectors)

    def radius_at(self, x: float, y: float) -> float:
        return self.radii[self.sector(x, y)]

    def contains(self, x: float, y: float) -> bool:
        if self.static_half_m > 0:
            return (abs(x - self.center[0]) <= self.static_half_m
                    and abs(y - self.center[1]) <= self.static_half_m)
        return math.hypot(x - self.center[0], y - self.center[1]) <= self.radius_at(x, y)

    def in_ring(self, x: float, y: float) -> bool:
        """Inside the integrity ring [R_sector, R_sector * (1 + width_factor)].
        Static mode has no ring — the boundary is definitionally complete."""
        if self.static_half_m > 0:
            return False
        r = math.hypot(x - self.center[0], y - self.center[1])
        rs = self.radius_at(x, y)
        return rs < r <= rs * (1.0 + self.ring_width_factor)

    def expand_sector(self, sector: int, factor: float) -> None:
        self.radii[sector] *= factor
        self.expansions += 1

    def ring_points(self, sector: int, k: int, rng: np.random.Generator
                    ) -> list[tuple[float, float]]:
        """k random points inside the integrity ring of one sector (seeded)."""
        cx, cy = self.center
        a0 = sector * 2 * math.pi / self.n_sectors
        a1 = (sector + 1) * 2 * math.pi / self.n_sectors
        rs = self.radii[sector]
        pts = []
        for _ in range(k):
            ang = rng.uniform(a0, a1)
            # uniform in area over the annulus
            r = math.sqrt(rng.uniform(rs ** 2, (rs * (1 + self.ring_width_factor)) ** 2))
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        return pts
