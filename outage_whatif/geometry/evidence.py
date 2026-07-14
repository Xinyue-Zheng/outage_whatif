"""Effective-evidence cells.

A fixed 300 m grid; multiple sampled points inside one cell contribute a
single evidence unit by majority vote.  All coverage/robustness statistics
count evidence cells, never raw points.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field


def cell_of(x: float, y: float, cell_m: float) -> tuple[int, int]:
    """Evidence-cell index of a coordinate (grid anchored at the origin)."""
    return (math.floor(x / cell_m), math.floor(y / cell_m))


def units_of_geometry(geometry_type: str, pixels_or_geom, raster,
                      cell_m: float) -> set:
    """Evidence units of a demand object.

    EXTENSION POINT (geometry): "area" is the only implemented geometry —
    its units are the evidence cells containing the object's raster pixels.
    "line" (e.g. a road) and "point" (e.g. a facility) are reserved; their
    unit definitions land here so every consumer keeps counting units the
    same way.
    """
    if geometry_type == "area":
        return {cell_of(*raster.pixel_center(iy, ix), cell_m)
                for iy, ix in pixels_or_geom.pixels}
    raise NotImplementedError(
        f"geometry {geometry_type!r} is reserved (area only for now)")


@dataclass
class PointObs:
    """One sampled coverage point, post-processed against the topology.

    in_footprint : target site serves OR is a top-5 backup above tau_acc
    alt_ok       : best alternative (after same-site deletion) >= tau_acc
    alt_owner    : site id of the best alternative (None if none exists)
    """
    x: float
    y: float
    in_footprint: bool
    alt_ok: bool
    alt_owner: str | None


@dataclass
class CellVote:
    """Majority-vote aggregate of the points inside one evidence cell."""
    cell: tuple[int, int]
    n_points: int = 0
    in_footprint: bool = False
    alt_ok: bool = False
    alt_owner: str | None = None
    center: tuple[float, float] = (0.0, 0.0)


@dataclass
class EvidenceGrid:
    """Holds all sampled coverage points, keyed by evidence cell."""
    cell_m: float
    points: dict = field(default_factory=dict)   # cell -> list[PointObs]

    def add(self, obs: PointObs) -> None:
        self.points.setdefault(cell_of(obs.x, obs.y, self.cell_m), []).append(obs)

    def sampled_cells(self) -> set[tuple[int, int]]:
        return set(self.points)

    def vote(self, cell: tuple[int, int]) -> CellVote | None:
        """Single evidence unit for a cell: strict majority on each boolean,
        plurality on the alternative owner (footprint points only)."""
        pts = self.points.get(cell)
        if not pts:
            return None
        n = len(pts)
        fp = sum(p.in_footprint for p in pts) * 2 > n
        fp_pts = [p for p in pts if p.in_footprint]
        if fp and fp_pts:
            ok = sum(p.alt_ok for p in fp_pts) * 2 > len(fp_pts)
            owners = Counter(p.alt_owner for p in fp_pts if p.alt_owner is not None)
            owner = None
            if owners:
                # deterministic tie-break: count desc, then owner id
                owner = sorted(owners.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        else:
            ok, owner = False, None
        cx = (cell[0] + 0.5) * self.cell_m
        cy = (cell[1] + 0.5) * self.cell_m
        return CellVote(cell=cell, n_points=n, in_footprint=fp,
                        alt_ok=ok, alt_owner=owner, center=(cx, cy))

    def votes(self, cells=None) -> list[CellVote]:
        cells = self.sampled_cells() if cells is None else cells
        out = [self.vote(c) for c in sorted(cells)]
        return [v for v in out if v is not None]
