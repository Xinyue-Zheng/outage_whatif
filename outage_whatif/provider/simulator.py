"""Synthetic rural scenario simulator.

Generates, from a seed and a small scenario spec, a deterministic World:

* site layout: perturbed 3x3 grid (+ optional extra sites), 3 sectors/site;
* per-cell propagation: pathloss + 3GPP-style azimuth pattern + smooth
  deterministic terrain field -> serving/backup RSRP rankings per coordinate;
* synthetic population: villages of varied sizes, including (forced) one
  missing from the raster but present in "reality" — the canonical
  residual-mechanism test: it surfaces as an unaccounted heavy cell whose
  residual_map points at it, registrable via
  RegisterObject(provenance="residual") — plus one below P_min (the
  importance-floor test) and one large one;
* per-site/cell synthetic load series (weekday/weekend/holiday structure,
  controllable headroom, deterministic hash-noise spikes) queryable over any
  window at hourly or 15-minute granularity.

Everything is a pure function of (spec, seed): a full case run is
reproducible from the case spec and seed alone.
"""

from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import numpy as np

from ..config import Config
from ..geometry.raster import PopulationRaster
from .interface import (DataProvider, PMSeries, PointCoverage, Profile,
                        Topology, Window)
from .pricing import PriceBook


# ------------------------------------------------------------------ helpers
def _u01(seed: int, *keys) -> float:
    """Deterministic uniform(0,1) from a seed and arbitrary keys (stable
    across processes — uses sha256, never Python's hash())."""
    h = hashlib.sha256(repr((seed,) + keys).encode()).digest()
    return struct.unpack(">I", h[:4])[0] / 2 ** 32


DIURNAL = [0.35, 0.30, 0.28, 0.27, 0.28, 0.32, 0.42, 0.55, 0.65, 0.70, 0.72,
           0.75, 0.78, 0.76, 0.74, 0.75, 0.80, 0.88, 0.95, 1.00, 0.98, 0.90,
           0.70, 0.50]


def day_type(d: date, holidays: set) -> str:
    if d.isoformat() in holidays:
        return "holiday"
    return {5: "sat", 6: "sun"}.get(d.weekday(), "weekday")


DAY_FACTOR = {"weekday": 1.00, "sat": 0.85, "sun": 0.72, "holiday": 1.15}


# ------------------------------------------------------------------ world
@dataclass
class SimCell:
    cell_id: str
    site_id: str
    x: float
    y: float
    azimuth: float          # degrees
    power_offset: float     # dB (site-level deficit applied to all its cells)


@dataclass
class TrueVillage:
    name: str
    x: float
    y: float
    pop: float
    radius: float           # metres
    in_raster: bool = True
    seasonal: bool = False  # e.g. summer-only settlement


@dataclass
class World:
    seed: int
    field_m: float
    sites: dict                     # site_id -> (x, y)
    cells: list                     # [SimCell]
    target_site: str
    villages: list                  # [TrueVillage]
    u_base: dict                    # site_id -> base PRB utilisation (hidden)
    spikiness: dict                 # site_id -> spike propensity (hidden)
    cell_factor: dict               # cell_id -> load share factor (hidden)
    holidays: set = field(default_factory=set)
    holiday_factor: float = 1.15
    terrain_amp: float = 3.0

    # -------------------------------------------------- radio
    def _terrain(self, x: float, y: float, k: int) -> float:
        """Smooth deterministic per-cell shadowing field (dB)."""
        p1 = 2 * math.pi * _u01(self.seed, "ph1", k)
        p2 = 2 * math.pi * _u01(self.seed, "ph2", k)
        p3 = 2 * math.pi * _u01(self.seed, "ph3", k)
        return (self.terrain_amp * math.sin(x / 1300.0 + p1) * math.cos(y / 1700.0 + p2)
                + 0.6 * self.terrain_amp * math.sin((x + y) / 900.0 + p3))

    def rsrp(self, cell: SimCell, x: float, y: float) -> float:
        d = max(math.hypot(x - cell.x, y - cell.y), 25.0)
        # 32 dB/decade with a 90-degree beam puts the boresight footprint
        # edge at ~2.2 km for tau_acc=-110 (comparable to the 2.6 km grid
        # pitch): neighbor sites at one grid pitch can — but do not always —
        # qualify as best alternatives.
        pl = 32.0 * math.log10(d / 25.0)
        ang = math.degrees(math.atan2(y - cell.y, x - cell.x))
        diff = abs((ang - cell.azimuth + 180.0) % 360.0 - 180.0)
        gain = -min(12.0 * (diff / 90.0) ** 2, 18.0)
        k = int(hashlib.sha256(cell.cell_id.encode()).hexdigest()[:4], 16)
        return -48.0 - pl + gain + cell.power_offset + self._terrain(x, y, k)

    def coverage_at(self, x: float, y: float) -> PointCoverage:
        ranked = sorted(((self.rsrp(c, x, y), c.cell_id) for c in self.cells),
                        key=lambda t: (-t[0], t[1]))
        serving = (ranked[0][1], round(ranked[0][0], 1))
        backups = [(cid, round(r, 1)) for r, cid in ranked[1:6]]
        return PointCoverage(x=x, y=y, serving=serving, backups=backups)

    # -------------------------------------------------- load
    def _entity_u(self, entity: str) -> tuple[str, float]:
        """(site_id, base utilisation) for a site or cell entity."""
        if entity in self.u_base:
            return entity, self.u_base[entity]
        site = entity.rsplit("_c", 1)[0]
        return site, self.u_base[site] * self.cell_factor[entity]

    def hourly_prb(self, entity: str, ts: datetime) -> float:
        site, u = self._entity_u(entity)
        dt = day_type(ts.date(), self.holidays)
        f = self.holiday_factor if dt == "holiday" else DAY_FACTOR[dt]
        noise = 0.06 * (_u01(self.seed, "hn", entity, ts.isoformat()) - 0.5)
        return float(np.clip(u * DIURNAL[ts.hour] * f + noise, 0.02, 0.99))

    def q15_prb(self, entity: str, ts: datetime) -> float:
        site, _ = self._entity_u(entity)
        base = self.hourly_prb(entity, ts.replace(minute=0))
        p_spike = float(np.clip(self.spikiness[site] * (0.25 + base), 0.0, 0.55))
        v = base + 0.05 * (_u01(self.seed, "q15n", entity, ts.isoformat()) - 0.5)
        if _u01(self.seed, "spk", entity, ts.isoformat()) < p_spike:
            v += 0.12 + 0.28 * _u01(self.seed, "amp", entity, ts.isoformat())
        return float(np.clip(v, 0.02, 1.0))

    def _metric(self, kind: str, prb: float, entity: str, ts) -> float:
        if kind == "prb_util":
            return round(prb, 4)
        if kind == "rrc_conn":
            return round(650.0 * prb + 25.0 * _u01(self.seed, "rrc", entity,
                                                   ts.isoformat()), 1)
        if kind == "throughput":                       # Mbps, degrades with load
            return round(80.0 * (1.05 - prb), 2)
        if kind == "volume":                           # GB per bin
            return round(2.4 * prb, 3)
        raise ValueError(f"unknown metric {kind!r}")

    def pm_series(self, entity: str, metric: str, granularity: str,
                  window: Window) -> PMSeries:
        step = timedelta(hours=1) if granularity == "hourly" else timedelta(minutes=15)
        samples = []
        ts = window.start
        while ts < window.end:
            prb = (self.hourly_prb(entity, ts) if granularity == "hourly"
                   else self.q15_prb(entity, ts))
            samples.append((ts.isoformat(), self._metric(metric, prb, entity, ts)))
            ts += step
        return PMSeries(entity=entity, metric=metric, granularity=granularity,
                        samples=samples)

    # -------------------------------------------------- free inputs
    def topology(self) -> Topology:
        return Topology(sites=dict(self.sites),
                        roster={c.cell_id: c.site_id for c in self.cells},
                        azimuths={c.cell_id: c.azimuth for c in self.cells})

    def raster(self, pixel_m: float = 100.0) -> PopulationRaster:
        n = int(self.field_m / pixel_m)
        pop = np.zeros((n, n))
        rng = np.random.default_rng(self.seed + 991)
        for v in self.villages:
            if not v.in_raster:
                continue                        # the deliberately omitted village
            # spread the village uniformly over its disc (deterministic;
            # no stray far-out pixels — the raster region matches reality)
            k = max(int((v.radius / pixel_m) ** 2 * 3), 6)
            ang = rng.uniform(0, 2 * np.pi, size=k)
            rr = v.radius * np.sqrt(rng.uniform(0, 1, size=k))
            xs = v.x + rr * np.cos(ang)
            ys = v.y + rr * np.sin(ang)
            w = v.pop / k
            for px, py in zip(xs, ys):
                ix, iy = int(px // pixel_m), int(py // pixel_m)
                if 0 <= ix < n and 0 <= iy < n:
                    pop[iy, ix] += w
        return PopulationRaster(pop=pop, x0=0.0, y0=0.0, pixel_m=pixel_m)


# ------------------------------------------------------------------ generator
HEADROOM_RANGES = {
    "ample": (0.18, 0.42),
    "tight": (0.55, 0.80),
    "mixed": (0.25, 0.72),
}


def generate_world(spec: dict, seed: int, cfg: Config) -> World:
    """Build a World from a scenario spec.  spec keys (all optional):
    headroom: ample|tight|mixed; weak_neighbors: int; village_count: int;
    n_extra_sites: int; holiday_factor: float; spikiness: low|high|mixed."""
    rng = np.random.default_rng(seed)
    field_m = 12000.0
    pitch = 2600.0

    # ---- sites: perturbed 3x3 grid, target = centre site
    sites, order = {}, []
    for gy in range(3):
        for gx in range(3):
            sid = f"S{gy * 3 + gx + 1}"
            x = 3400.0 + gx * pitch + rng.uniform(-380, 380)
            y = 3400.0 + gy * pitch + rng.uniform(-380, 380)
            sites[sid] = (x, y)
            order.append(sid)
    for i in range(int(spec.get("n_extra_sites", 0))):
        sid = f"S{10 + i}"
        ang = rng.uniform(0, 2 * math.pi)
        # close enough to the target to be genuine absorption alternatives
        r = rng.uniform(2400, 3800)
        sites[sid] = (sites["S5"][0] + r * math.cos(ang),
                      sites["S5"][1] + r * math.sin(ang))
        order.append(sid)
    target = "S5"

    # ---- per-site power deficits (weak neighbors -> coverage holes)
    power_offset = {sid: 0.0 for sid in order}
    ring = [s for s in order if s != target]
    weak = list(rng.permutation(ring))[: int(spec.get("weak_neighbors", 0))]
    for sid in weak:
        power_offset[sid] = -float(rng.uniform(9.0, 14.0))

    # ---- cells: 3 sectors per site with a per-site rotation
    cells = []
    for sid in order:
        rot = float(rng.uniform(0, 120))
        for k in range(3):
            cells.append(SimCell(cell_id=f"{sid}_c{k}", site_id=sid,
                                 x=sites[sid][0], y=sites[sid][1],
                                 azimuth=(rot + 120.0 * k) % 360.0,
                                 power_offset=power_offset[sid]))

    # ---- hidden load parameters
    lo, hi = HEADROOM_RANGES[spec.get("headroom", "mixed")]
    u_base = {sid: float(rng.uniform(lo, hi)) for sid in order}
    spk_mode = spec.get("spikiness", "mixed")
    spk_rng = {"low": (0.02, 0.10), "high": (0.15, 0.35),
               "mixed": (0.03, 0.30)}[spk_mode]
    spikiness = {sid: float(rng.uniform(*spk_rng)) for sid in order}
    cell_factor = {}
    for sid in order:
        f = rng.uniform(0.6, 1.4, size=3)
        f = f / f.mean()
        for k in range(3):
            cell_factor[f"{sid}_c{k}"] = float(f[k])

    # ---- villages (populations are hidden truth; raster may omit/miss)
    tx, ty = sites[target]
    # placement scale: 0.75 x median distance to the 6 nearest neighbor
    # sites — keeps the forced villages inside the target's plausible
    # footprint (a simulator-internal constant, not an analysis boundary)
    dists = sorted(math.hypot(x - tx, y - ty)
                   for sid, (x, y) in sites.items() if sid != target)
    r0 = 0.75 * float(np.median(np.array(dists[:6])))

    def _place(dist_lo, dist_hi):
        ang = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(dist_lo, dist_hi)
        return tx + r * math.cos(ang), ty + r * math.sin(ang)

    villages = []
    # forced: one large village, well inside the footprint
    x, y = _place(0.30 * r0, 0.65 * r0)
    villages.append(TrueVillage("big", x, y, float(rng.uniform(1.6, 3.2)) * 200.0,
                                rng.uniform(180, 300)))
    # forced: one near the footprint edge (an ordinary pin; historically the
    # "boundary straddler" of the boundary-based architecture)
    x, y = _place(0.97 * r0, 1.03 * r0)
    villages.append(TrueVillage("straddler", x, y, float(rng.uniform(90, 260)),
                                rng.uniform(200, 320)))
    # forced: one present in reality but MISSING from the raster — the
    # residual-mechanism test (unaccounted heavy cell -> residual_map ->
    # RegisterObject(provenance="residual"))
    x, y = _place(0.45 * r0, 0.85 * r0)
    villages.append(TrueVillage("ghost", x, y, float(rng.uniform(80, 160)),
                                rng.uniform(120, 220), in_raster=False))
    # forced: one below P_min (importance-floor test)
    x, y = _place(0.35 * r0, 0.90 * r0)
    villages.append(TrueVillage("tiny", x, y, float(rng.uniform(15, 45)),
                                rng.uniform(80, 140)))
    # the rest: random villages, one may be seasonal
    n_more = max(int(spec.get("village_count", 7)) - len(villages), 0)
    for i in range(n_more):
        x, y = _place(0.30 * r0, 1.05 * r0)
        villages.append(TrueVillage(
            f"v{i}", x, y, float(rng.lognormal(math.log(120), 0.7)),
            rng.uniform(120, 280), seasonal=(i == 0 and bool(spec.get("seasonal", False)))))

    return World(seed=seed, field_m=field_m, sites=sites, cells=cells,
                 target_site=target, villages=villages, u_base=u_base,
                 spikiness=spikiness, cell_factor=cell_factor,
                 holidays=set(cfg.holidays),
                 holiday_factor=float(spec.get("holiday_factor", 1.15)))


# ------------------------------------------------------------------ provider
class SimProvider(DataProvider):
    """DataProvider backed by a World.  Returns (data, charged_price)."""

    def __init__(self, world: World, pricebook: PriceBook | None = None):
        self.world = world
        self.book = pricebook or PriceBook()

    def topology(self) -> Topology:
        return self.world.topology()

    def population_raster(self) -> PopulationRaster:
        return self.world.raster()

    def query_coverage(self, points):
        data = [self.world.coverage_at(x, y) for x, y in points]
        return data, self.book.coverage(len(points))

    def query_pm(self, entities, metric, granularity, window: Window):
        data = {e: self.world.pm_series(e, metric, granularity, window)
                for e in entities}
        return data, self.book.pm(granularity, len(entities), window.hours)

    def buy_profile(self, site: str, kind: str, hour: int | None = None):
        w = self.world
        if kind == "same_weekday":
            # mean/var per hour over the 8 most recent same-weekdays before a
            # fixed reference date (deterministic).
            ref = datetime(2026, 6, 29)          # a Monday; offset by weekday below
            days = [ref - timedelta(days=7 * i) for i in range(8)]
            series = [[w.hourly_prb(site, d.replace(hour=h)) for d in days]
                      for h in range(24)]
        elif kind == "holiday_last_year":
            hols = sorted(d for d in w.holidays if d.startswith("2025"))
            days = [datetime.fromisoformat(d) for d in hols[:3]] or [datetime(2025, 12, 25)]
            series = [[w.hourly_prb(site, d.replace(hour=h)) for d in days]
                      for h in range(24)]
        elif kind == "matched_hour":
            # the analysis hour's distribution over a 12-week same-weekday
            # horizon; Profile keeps its 24-slot shape by repeating the
            # single-hour statistic in every slot (documented judgment-
            # firming product — consumers read one hour of it).
            if hour is None:
                raise ValueError("matched_hour profile requires hour=")
            ref = datetime(2026, 6, 29)
            days = [ref - timedelta(days=7 * i) for i in range(12)]
            vals = [w.hourly_prb(site, d.replace(hour=int(hour)))
                    for d in days]
            series = [vals for _ in range(24)]
        else:
            raise ValueError(f"unknown profile kind {kind!r}")
        prof = Profile(site=site, kind=kind,
                       hourly_mean=[round(float(np.mean(s)), 4) for s in series],
                       hourly_var=[round(float(np.var(s)), 5) for s in series])
        return prof, self.book.profile(kind)

    def quote(self, kind: str, **params) -> float:
        return self.book.quote(kind, **params)
