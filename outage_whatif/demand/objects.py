"""Demand objects and their registry.

A demand object is a hypothesis about where demand on the target sits — an
area (settlement), later possibly a line (road) or point (facility).  The
population raster is a candidate-pin generator, not the demand definition:
raster settlements intersecting the candidate zone become HYPOTHESIZED
objects; the agent may register further objects (from residual evidence or
its own judgment).  State transitions are code, not agent:

* hypothesized -> confirmed: >= 1 purchased point inside the object shows
  the target above tau_acc (confirmation auto-opens one COV + one ROB
  claim, flip-tested at birth by the loop);
* hypothesized/confirmed -> dismissed: an agent DismissRequest verified by
  the instrument (>= dismiss_min_units sampled evidence units inside, none
  showing the target);
* confirmed -> adjudicated: every claim of the object is decided.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..config import Config
from ..geometry.evidence import EvidenceGrid, units_of_geometry
from ..geometry.raster import PopulationRaster, Subregion, segment_raster

HYPOTHESIZED = "hypothesized"
CONFIRMED = "confirmed"
DISMISSED = "dismissed"
ADJUDICATED = "adjudicated"


@dataclass
class DemandObject:
    id: str
    geometry_type: str                      # "area" ("line"/"point" reserved)
    pixels_or_geom: Subregion               # area objects reuse Subregion
    provenance: list[str]                   # "raster" | "residual" | "agent"
    provenance_note: str | None = None
    state: str = HYPOTHESIZED
    claim_ids: list = field(default_factory=list)

    @property
    def population(self) -> float:
        return self.pixels_or_geom.population

    @property
    def centroid(self) -> tuple[float, float]:
        return self.pixels_or_geom.centroid

    def evidence_cells(self, raster: PopulationRaster, cell_m: float) -> set:
        return units_of_geometry(self.geometry_type, self.pixels_or_geom,
                                 raster, cell_m)

    def contains(self, x: float, y: float, raster: PopulationRaster) -> bool:
        """Is a coordinate inside the object?  Area: pixel membership."""
        if self.geometry_type != "area":
            raise NotImplementedError("area geometry only for now")
        ix = math.floor((x - raster.x0) / raster.pixel_m)
        iy = math.floor((y - raster.y0) / raster.pixel_m)
        return (iy, ix) in self._pixel_set()

    def _pixel_set(self) -> set:
        if not hasattr(self, "_pixels_cached"):
            self._pixels_cached = set(self.pixels_or_geom.pixels)
        return self._pixels_cached


def in_candidate_zone(x: float, y: float, target_xy: tuple, sites: dict,
                      margin_m: float) -> bool:
    """Candidate zone: the point is closer to the target than to its
    second-nearest site, buffered outward by margin_m."""
    tx, ty = target_xy
    dt = math.hypot(x - tx, y - ty)
    d = sorted(math.hypot(x - sx, y - sy) for sx, sy in sites.values())
    d2 = d[1] if len(d) > 1 else float("inf")
    return dt <= d2 + margin_m


def build_candidates(topology, target: str, raster: PopulationRaster,
                     cfg: Config) -> "ObjectRegistry":
    """Candidate pins: every segment_raster settlement intersecting the
    candidate zone becomes a hypothesized area object (IDs V1, V2, ... by
    population).  There is no boundary object: settlements outside the zone
    are simply never offered."""
    target_xy = topology.sites[target]
    settlements, _bg = segment_raster(raster, cfg)     # sorted by population
    registry = ObjectRegistry()
    n = 0
    for sub in settlements:
        hit = any(in_candidate_zone(*raster.pixel_center(iy, ix), target_xy,
                                    topology.sites, cfg.policy.candidate_margin_m)
                  for iy, ix in sub.pixels)
        if not hit:
            continue
        n += 1
        sub.sid = f"V{n}"
        registry.add(DemandObject(id=sub.sid, geometry_type="area",
                                  pixels_or_geom=sub, provenance=["raster"]))
    return registry


class ObjectRegistry:
    """All demand objects of a run, by id."""

    def __init__(self):
        self._o: dict[str, DemandObject] = {}
        self._n_registered = 0

    # ---------------- access
    def add(self, obj: DemandObject) -> DemandObject:
        if obj.id in self._o:
            raise KeyError(f"duplicate object id {obj.id}")
        self._o[obj.id] = obj
        return obj

    def get(self, oid: str) -> DemandObject:
        return self._o[oid]

    def __contains__(self, oid: str) -> bool:
        return oid in self._o

    def all(self) -> list[DemandObject]:
        return list(self._o.values())

    def by_state(self, state: str) -> list[DemandObject]:
        return [o for o in self._o.values() if o.state == state]

    def non_dismissed(self) -> list[DemandObject]:
        return [o for o in self._o.values() if o.state != DISMISSED]

    def containing(self, x: float, y: float,
                   raster: PopulationRaster) -> list[DemandObject]:
        return [o for o in self.non_dismissed() if o.contains(x, y, raster)]

    # ---------------- agent-initiated creation
    def register(self, x: float, y: float, radius_m: float, provenance: str,
                 note: str | None, raster: PopulationRaster) -> DemandObject:
        """RegisterObject: a new hypothesized area object over the raster
        pixels within radius_m of (x, y) — the pixels may carry no
        population (that is the point for residual registrations)."""
        pixels = []
        n_y, n_x = raster.pop.shape
        r_pix = int(radius_m / raster.pixel_m) + 1
        cx = math.floor((x - raster.x0) / raster.pixel_m)
        cy = math.floor((y - raster.y0) / raster.pixel_m)
        for iy in range(max(cy - r_pix, 0), min(cy + r_pix + 1, n_y)):
            for ix in range(max(cx - r_pix, 0), min(cx + r_pix + 1, n_x)):
                px, py = raster.pixel_center(iy, ix)
                if math.hypot(px - x, py - y) <= radius_m:
                    pixels.append((iy, ix))
        if not pixels:
            raise ValueError("registered object contains no raster pixels")
        self._n_registered += 1
        oid = f"R{self._n_registered}"
        pop = float(sum(raster.pop[iy, ix] for iy, ix in pixels))
        sub = Subregion(sid=oid, pixels=pixels, population=pop,
                        centroid=(x, y))
        return self.add(DemandObject(id=oid, geometry_type="area",
                                     pixels_or_geom=sub,
                                     provenance=[provenance],
                                     provenance_note=note))

    # ---------------- code state transitions
    def refresh_confirmations(self, points, raster: PopulationRaster) -> list:
        """points: iterable of PointObs (purchased coverage evidence).
        Any hypothesized object containing a point with the target above
        tau_acc (in_footprint) becomes CONFIRMED.  Returns the newly
        confirmed objects; the caller opens their claims and flip-tests
        them at birth."""
        newly = []
        hyp = self.by_state(HYPOTHESIZED)
        if not hyp:
            return newly
        for obj in hyp:
            if any(p.in_footprint and obj.contains(p.x, p.y, raster)
                   for p in points):
                obj.state = CONFIRMED
                newly.append(obj)
        return newly

    def verify_dismiss(self, oid: str, grid: EvidenceGrid,
                       raster: PopulationRaster,
                       cfg: Config) -> str | None:
        """Instrument check of an agent DismissRequest.  Returns None if the
        dismissal is verified (>= dismiss_min_units sampled evidence units
        inside the object, none showing the target), else the denial
        reason."""
        obj = self._o[oid]
        if obj.state == DISMISSED:
            return f"{oid} is already dismissed"
        cells = obj.evidence_cells(raster, grid.cell_m)
        votes = grid.votes(cells & grid.sampled_cells())
        if len(votes) < cfg.dismiss_min_units:
            return (f"only {len(votes)} sampled evidence units inside {oid}; "
                    f"dismissal needs >= {cfg.dismiss_min_units}")
        showing = [v for v in votes if v.in_footprint]
        if showing:
            return (f"{len(showing)} sampled units inside {oid} show the "
                    f"target — cannot dismiss")
        return None

    def dismiss(self, oid: str) -> DemandObject:
        obj = self._o[oid]
        obj.state = DISMISSED
        return obj

    def mark_adjudicated(self, claims) -> list:
        """Confirmed objects whose every claim is decided become
        ADJUDICATED (bookkeeping for the briefing/audit)."""
        done = []
        for obj in self.by_state(CONFIRMED):
            own = [claims.get(cid) for cid in obj.claim_ids if cid in claims]
            if own and all(c.state != "undecided" for c in own if c.alive):
                obj.state = ADJUDICATED
                done.append(obj)
        return done
