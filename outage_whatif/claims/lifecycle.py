"""Claim lifecycle (code, every round).

* new exit neighbors discovered by densification spawn capacity claims
  (flip-tested at birth by the loop's post-lifecycle flip pass);
* neighbors that stop being anyone's best alternative die;
* a coverage claim undecided through two densifications with spatially
  clustered pass/fail cells triggers a subregion split;
* a capacity claim stuck at site level drills down to per-cell children.
"""

from __future__ import annotations

import math

import numpy as np

from ..config import Config
from ..geometry.raster import PopulationRaster, Subregion
from .evidence_view import EvidenceView
from .model import (CAPACITY, COVERAGE, INTEGRITY, ROBUSTNESS, UNDECIDED,
                    Claim, ClaimSet)


def initial_claims(subregions: dict, background: Subregion, cfg: Config,
                   round_no: int = 0) -> ClaimSet:
    """Coverage + robustness per settlement subregion and for the background
    region; one integrity claim per boundary direction sector.  Capacity
    claims are instantiated only after sampling reveals exit neighbors.
    Static-area mode (cfg.static_area_km > 0): the boundary is the full
    data square, definitionally complete — no integrity claims."""
    claims = ClaimSet()
    for sid in sorted(subregions) + ["BG"]:
        claims.add(Claim(cid=f"COV:{sid}", ctype=COVERAGE, subject=sid,
                         born_round=round_no,
                         remedy="sample this subregion's evidence cells"))
        claims.add(Claim(cid=f"ROB:{sid}", ctype=ROBUSTNESS, subject=sid,
                         born_round=round_no,
                         remedy="sample this subregion's evidence cells"))
    if cfg.static_area_km <= 0:
        for s in range(cfg.n_sectors):
            claims.add(Claim(cid=f"INT:{s}", ctype=INTEGRITY, subject=str(s),
                             born_round=round_no,
                             remedy="sample the integrity ring in this sector"))
    return claims

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
def run_lifecycle(claims: ClaimSet, view: EvidenceView, subregions: dict,
                  raster: PopulationRaster, roster: dict, cfg: Config,
                  round_no: int) -> list[str]:
    """Mutates claims and subregions; returns human-readable event log lines."""
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

    # ---- coverage subregion split
    for c in list(claims.by_type(COVERAGE)):
        if (c.state != UNDECIDED or c.subject == "BG" or c.children
                or c.densifications < cfg.split_after_densifications):
            continue
        centroids = _pass_fail_clustered(view.votes_by_sid.get(c.subject, []), cfg)
        if centroids is None:
            continue
        sub = subregions.pop(c.subject)
        a, b = _split_subregion(sub, raster, *centroids)
        if not a.pixels or not b.pixels:
            subregions[c.subject] = sub      # degenerate split; keep parent
            continue
        subregions[a.sid], subregions[b.sid] = a, b
        for child in (a, b):
            cov = claims.add(Claim(cid=f"COV:{child.sid}", ctype=COVERAGE,
                                   subject=child.sid, born_round=round_no,
                                   parent=c.cid,
                                   remedy="densify unsampled evidence cells"))
            c.children.append(cov.cid)
            claims.add(Claim(cid=f"ROB:{child.sid}", ctype=ROBUSTNESS,
                             subject=child.sid, born_round=round_no,
                             parent=f"ROB:{c.subject}",
                             remedy="sample this subregion's evidence cells"))
        c.alive = False
        rob_cid = f"ROB:{c.subject}"
        if rob_cid in claims:
            claims.get(rob_cid).alive = False
        events.append(f"split {c.subject} -> {a.sid}, {b.sid} "
                      f"(clustered pass/fail cells after "
                      f"{c.densifications} densifications)")

    # ---- capacity drill-down to per-cell children
    # DESIGN-GAP: trigger = stuck undecided at site level (middle zone) for
    # >= drilldown_after_rounds rounds; the spec names the mechanism but not
    # the exact trigger.  Disabled entirely when cfg.capacity_drilldown is
    # False (site-level analysis; data source has no per-cell PM) — the
    # stuck claim's remedy stays the 15-minute site query.
    for c in list(claims.by_type(CAPACITY)) if cfg.capacity_drilldown else []:
        if (c.parent is not None or c.drilled or c.state != UNDECIDED
                or c.detail.get("zone") != "middle_zone"
                or c.rounds_undecided < cfg.drilldown_after_rounds):
            continue
        cells = sorted(cell for cell, site in roster.items()
                       if site == c.subject)
        for cell in cells:
            kid = claims.add(Claim(cid=f"CAP:{c.subject}:{cell}",
                                   ctype=CAPACITY, subject=cell,
                                   born_round=round_no, parent=c.cid,
                                   remedy="buy per-cell PM for the outage-matched window"))
            c.children.append(kid.cid)
        c.drilled = True
        events.append(f"drilled down {c.cid} -> {len(cells)} per-cell children")

    return events
