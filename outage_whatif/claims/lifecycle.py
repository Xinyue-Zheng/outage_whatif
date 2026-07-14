"""Claim lifecycle.

Code-run every round: newly revealed exit neighbors spawn capacity claims
(flip-tested at birth by the loop's post-lifecycle flip pass); neighbors
that stop being anyone's best alternative die.  Claims for demand objects
open on CONFIRMATION (``open_claims_for``), never at startup.

Subregion splitting and capacity drill-down are agent-committed actions in
the investigator architecture (SplitObject / DrillDown, instrument-checked
by the gate); the split machinery lives here and is called by the engine.
"""

from __future__ import annotations

import math

import numpy as np

from ..config import Config
from ..geometry.raster import PopulationRaster, Subregion
from .evidence_view import EvidenceView
from .model import (CAPACITY, COVERAGE, ROBUSTNESS, Claim, ClaimSet)


def open_claims_for(sid: str, claims: ClaimSet, round_no: int = 0) -> list:
    """Open one COV + one ROB claim for a (newly confirmed) demand object.
    Returns the created claims; the caller flip-tests them at birth."""
    made = []
    for prefix, ctype in (("COV", COVERAGE), ("ROB", ROBUSTNESS)):
        cid = f"{prefix}:{sid}"
        if cid not in claims:
            made.append(claims.add(Claim(
                cid=cid, ctype=ctype, subject=sid, born_round=round_no,
                remedy="sample this object's evidence cells")))
    return made


# --------------------------------------------------------------- split helper
def _pass_fail_clustered(votes, cfg: Config) -> tuple | None:
    """If pass and fail footprint cells form spatially separated groups,
    return (pass_centroid, fail_centroid); else None."""
    fp = [v for v in votes if v.in_footprint]
    passes = [v.center for v in fp if v.alt_ok]
    fails = [v.center for v in fp if not v.alt_ok]
    if len(passes) < 2 or len(fails) < 2:
        return None
    pc = (float(np.mean([p[0] for p in passes])),
          float(np.mean([p[1] for p in passes])))
    fc = (float(np.mean([p[0] for p in fails])),
          float(np.mean([p[1] for p in fails])))
    sep = math.hypot(pc[0] - fc[0], pc[1] - fc[1])
    if sep > cfg.cluster_sep_cells * cfg.evidence_cell_m:
        return pc, fc
    return None


def _split_subregion(sub: Subregion, raster: PopulationRaster,
                     pc: tuple, fc: tuple) -> tuple[Subregion, Subregion]:
    """Partition pixels by the perpendicular bisector of the pass/fail
    centroids.  Child 'a' is on the pass side."""
    mx, my = (pc[0] + fc[0]) / 2.0, (pc[1] + fc[1]) / 2.0
    dx, dy = pc[0] - fc[0], pc[1] - fc[1]
    a = Subregion(sid=f"{sub.sid}a")
    b = Subregion(sid=f"{sub.sid}b")
    for iy, ix in sub.pixels:
        x, y = raster.pixel_center(iy, ix)
        side = (x - mx) * dx + (y - my) * dy
        child = a if side >= 0 else b
        child.pixels.append((iy, ix))
        child.population += float(raster.pop[iy, ix])
    for child in (a, b):
        if child.pixels:
            xs = [raster.pixel_center(iy, ix)[0] for iy, ix in child.pixels]
            ys = [raster.pixel_center(iy, ix)[1] for iy, ix in child.pixels]
            child.centroid = (float(np.mean(xs)), float(np.mean(ys)))
    return a, b


# --------------------------------------------------------------- lifecycle
def run_lifecycle(claims: ClaimSet, view: EvidenceView, cfg: Config,
                  round_no: int) -> list[str]:
    """Mutates claims; returns human-readable event log lines."""
    events: list[str] = []
    pol = cfg.policy

    # age open claims
    for c in claims.open():
        c.rounds_undecided += 1

    # ---- spawn capacity claims for newly revealed genuine exit neighbors
    majors = view.all_major_exits(pol.sigma)          # site -> [sids]
    for site in sorted(majors):
        cid = f"CAP:{site}"
        if cid not in claims:
            claims.add(Claim(cid=cid, ctype=CAPACITY, subject=site,
                             born_round=round_no,
                             remedy="buy hourly PM for the outage-matched window",
                             detail={"serves": sorted(majors[site])}))
            events.append(f"spawned {cid} (major exit for "
                          f"{', '.join(sorted(majors[site]))})")
        else:
            claims.get(cid).detail["serves"] = sorted(majors[site])

    # ---- kill capacity claims for neighbors no longer anyone's major exit
    for c in claims.by_type(CAPACITY):
        if c.parent is None and c.subject not in majors:
            c.alive = False
            for k in c.children:
                claims.get(k).alive = False
            events.append(f"killed {c.cid} (no longer anyone's best alternative)")

    return events
