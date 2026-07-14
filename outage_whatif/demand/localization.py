"""Cell localization book: where does each target cell's demand sit?

Per target roster cell c the book tracks

* ``T[c]`` — busy-window traffic (mean RRC-connected users over the matched
  analysis hours) once cell-level KPI has been purchased, else unknown;
* ``status(c)`` — accounted (every sampled unit served by c lies inside a
  registered non-dismissed object) | unaccounted (some sampled unit served
  by c is unmapped) | unknown (fewer than n_min_units_per_cell units);
* ``empirical_direction(c)`` — circular mean + dispersion of the bearings
  (from the target site) of owned points served by c; undefined below
  min_dir_samples units.

Derived instruments: ``residual_bound`` (unaccounted share of known target
traffic), ``importance_bound(obj)`` (traffic attributable to an object),
``residual_map`` (per-cell dict incl. coordinates of sampled-but-unmapped
points), and hole severity.  Sums and set intersections only — traffic is
never split across objects.
"""

from __future__ import annotations

import math
from collections import defaultdict

from ..config import Config
from ..geometry.evidence import cell_of
from ..verdict.verdict import SEVERE_NO, SEVERE_UND, SEVERE_YES

ACCOUNTED = "accounted"
UNACCOUNTED = "unaccounted"
UNKNOWN = "unknown"


class CellLocalizationBook:
    def __init__(self, target: str, target_xy: tuple, target_cells: list):
        self.target = target
        self.target_xy = target_xy
        self.cells = sorted(target_cells)          # target roster cell ids
        self.traffic: dict = {}                    # cell -> T[c]
        self._points: dict = defaultdict(list)     # cell -> [(x, y)]
        # a site-level target_kpi purchase (cheaper, 1 entity) gives one
        # whole-site total; it is never split into per-cell T[c] ("traffic
        # is never split") so it does not close the demand-ledger gap —
        # it is a coarse, cheap peek the agent may buy before committing
        # to the full per-cell purchase.
        self.site_total: float | None = None

    # ---------------- feeding
    def add_point(self, x: float, y: float, serving_cell: str) -> None:
        """Record one purchased coverage point served by a target cell."""
        if serving_cell in self.cells:
            self._points[serving_cell].append((x, y))

    def set_traffic(self, cell: str, value: float) -> None:
        if cell in self.cells:
            self.traffic[cell] = float(value)

    def set_site_total(self, value: float) -> None:
        self.site_total = float(value)

    # ---------------- per-cell reads
    def T(self, cell: str) -> float | None:
        return self.traffic.get(cell)

    def units(self, cell: str, cfg: Config) -> dict:
        """Sampled evidence units served by a cell: unit -> [(x, y) points]."""
        out: dict = defaultdict(list)
        for x, y in self._points.get(cell, []):
            out[cell_of(x, y, cfg.evidence_cell_m)].append((x, y))
        return out

    def status(self, cell: str, registry, raster, cfg: Config) -> str:
        units = self.units(cell, cfg)
        if len(units) < cfg.n_min_units_per_cell:
            return UNKNOWN
        for pts in units.values():
            if not any(registry.containing(x, y, raster) for x, y in pts):
                return UNACCOUNTED
        return ACCOUNTED

    def unmapped_points(self, cell: str, registry, raster,
                        cfg: Config) -> list:
        """Sampled points served by the cell lying inside no registered
        non-dismissed object — where the residual demand physically sits."""
        return [(round(x, 1), round(y, 1))
                for x, y in self._points.get(cell, [])
                if not registry.containing(x, y, raster)]

    def empirical_direction(self, cell: str, cfg: Config) -> dict | None:
        """Circular mean + dispersion of the bearings of owned points served
        by the cell; None below min_dir_samples units."""
        units = self.units(cell, cfg)
        if len(units) < cfg.min_dir_samples:
            return None
        tx, ty = self.target_xy
        angs = [math.atan2(y - ty, x - tx)
                for pts in units.values() for x, y in pts]
        s = sum(math.sin(a) for a in angs) / len(angs)
        c = sum(math.cos(a) for a in angs) / len(angs)
        r = math.hypot(s, c)
        return {"mean_bearing_deg": round(math.degrees(math.atan2(s, c)) % 360, 1),
                "dispersion": round(1.0 - r, 3),     # 0 = tight beam
                "n_units": len(units)}

    def explanations(self, cell: str, registry, raster) -> set:
        """Non-dismissed objects containing >= 1 sampled point served by the
        cell (set intersection, no splitting)."""
        out = set()
        for x, y in self._points.get(cell, []):
            out |= {o.id for o in registry.containing(x, y, raster)}
        return out

    # ---------------- derived instruments
    def residual_bound(self, registry, raster, cfg: Config) -> float | None:
        """Unaccounted share of the target's busy-window traffic.  None
        while any target cell's T is unknown (no complete demand ledger —
        an audit gap, not a number)."""
        if any(c not in self.traffic for c in self.cells):
            return None
        total = sum(self.traffic.values())
        if total <= 0:
            return 0.0
        bad = sum(self.traffic[c] for c in self.cells
                  if self.status(c, registry, raster, cfg) != ACCOUNTED)
        return round(bad / total, 4)

    def importance_bound(self, oid: str, registry, raster,
                         cfg: Config) -> float:
        """Upper bound on the traffic attributable to an object: the full
        T[c] of every cell with >= 1 sampled point served by c inside the
        object (whole cells, never split; unknown T contributes 0 — the
        audit separately flags unknown heavy cells)."""
        return round(sum(
            self.traffic.get(cell, 0.0)
            for cell in self.cells
            if oid in self.explanations(cell, registry, raster)), 2)

    def residual_map(self, registry, raster, cfg: Config) -> dict:
        """Per-cell view of where unaccounted demand sits."""
        out = {}
        for cell in self.cells:
            out[cell] = {
                "T": self.traffic.get(cell),
                "status": self.status(cell, registry, raster, cfg),
                "n_units": len(self.units(cell, cfg)),
                "unmapped_points": self.unmapped_points(cell, registry,
                                                        raster, cfg),
                "direction": self.empirical_direction(cell, cfg),
            }
        return out

    def hole_severity(self, oid: str, intact_ids: set, registry, raster,
                      cfg: Config) -> str:
        """Severity of a holed object (verdict rule):

        * SEVERE if the object is the sole non-dismissed explanation for
          some cell with T[c] >= T_severe;
        * severity UNDECIDED if a sole-explained cell's T is still unknown,
          or the object shares all its cells with intact objects
          (resolvable by drill-down or, at close-out, the policy default);
        * NOT SEVERE otherwise.
        """
        my_cells = [c for c in self.cells
                    if oid in self.explanations(c, registry, raster)]
        if not my_cells:
            return SEVERE_NO
        sole = [c for c in my_cells
                if self.explanations(c, registry, raster) == {oid}]
        for c in sole:
            t = self.traffic.get(c)
            if t is not None and t >= cfg.policy.T_severe:
                return SEVERE_YES
        if any(self.traffic.get(c) is None for c in sole):
            return SEVERE_UND
        if not sole and all(
                (self.explanations(c, registry, raster) - {oid}) & intact_ids
                for c in my_cells):
            return SEVERE_UND
        return SEVERE_NO


def footprint_hull(points: list) -> list:
    """Convex hull over the owned target-accessible points (an instrument
    for reporting and empirical-direction context, not a phase).  Returns
    the hull vertices counter-clockwise; fewer than 3 points return as-is."""
    pts = sorted(set((round(x, 1), round(y, 1)) for x, y in points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]
