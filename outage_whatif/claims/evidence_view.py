"""Evidence views: everything adjudication needs, computed from raw stores.

Assignments (deterministic):
* a settlement owns every evidence cell containing one of its raster pixels;
* the background region owns sampled cells inside the boundary owned by no
  settlement and not in the integrity ring;
* integrity sector s owns sampled cells whose center lies in the ring of s.
Overlap between a straddling settlement and the ring is intentional — ring
contamination is exactly how a straddler refutes integrity and triggers
boundary expansion.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ..config import Config
from ..geometry.boundary import Boundary
from ..geometry.evidence import CellVote, EvidenceGrid, cell_of
from ..geometry.raster import PopulationRaster, Subregion


@dataclass
class PMStore:
    """Held PM evidence: PRB utilisation values in the outage-matched window."""
    hourly: dict = field(default_factory=dict)    # entity -> [values]
    q15: dict = field(default_factory=dict)       # entity -> [values]

    def hourly_mean(self, entity: str):
        v = self.hourly.get(entity)
        return sum(v) / len(v) if v else None


def subregion_cells(sub: Subregion, raster: PopulationRaster,
                    cell_m: float) -> set:
    """Evidence cells belonging to a settlement (via its pixel centers)."""
    return {cell_of(*raster.pixel_center(iy, ix), cell_m)
            for iy, ix in sub.pixels}


@dataclass
class EvidenceView:
    """Per-round snapshot of aggregated evidence, keyed the way claims need it."""
    votes_by_sid: dict = field(default_factory=dict)     # sid -> [CellVote]
    ring_votes: dict = field(default_factory=dict)       # sector -> [CellVote]
    owner_shares: dict = field(default_factory=dict)     # sid -> {site: share}
    unsampled_cells: dict = field(default_factory=dict)  # sid -> [cell]

    def major_exits(self, sid: str, sigma: float) -> list:
        return sorted(s for s, sh in self.owner_shares.get(sid, {}).items()
                      if sh >= sigma)

    def all_major_exits(self, sigma: float) -> dict:
        """site -> [sids it is a major exit for]"""
        out: dict[str, list] = {}
        for sid in self.owner_shares:
            for s in self.major_exits(sid, sigma):
                out.setdefault(s, []).append(sid)
        return out


def build_view(grid: EvidenceGrid, subregions: dict, background: Subregion,
               raster: PopulationRaster, boundary: Boundary,
               cfg: Config) -> EvidenceView:
    """subregions: sid -> Subregion (settlements only)."""
    view = EvidenceView()
    sampled = grid.sampled_cells()
    assigned: set = set()

    for sid, sub in subregions.items():
        cells = subregion_cells(sub, raster, cfg.evidence_cell_m)
        have = cells & sampled
        assigned |= have
        view.votes_by_sid[sid] = grid.votes(have)
        view.unsampled_cells[sid] = sorted(cells - sampled)

    # integrity ring, by sector (cell center decides)
    ring_cells: dict[int, list] = {s: [] for s in range(boundary.n_sectors)}
    # background: sampled, inside boundary, not settlement, not ring
    bg_cells = []
    for c in sampled:
        cx = (c[0] + 0.5) * cfg.evidence_cell_m
        cy = (c[1] + 0.5) * cfg.evidence_cell_m
        if boundary.in_ring(cx, cy):
            ring_cells[boundary.sector(cx, cy)].append(c)
        if c in assigned:
            continue
        if boundary.contains(cx, cy):
            bg_cells.append(c)
    for s, cells in ring_cells.items():
        view.ring_votes[s] = grid.votes(cells)
    view.votes_by_sid["BG"] = grid.votes(bg_cells)
    view.unsampled_cells["BG"] = []          # background densifies via Track 2

    # owner shares over footprint cells
    for sid, votes in view.votes_by_sid.items():
        fp = [v for v in votes if v.in_footprint]
        owners = Counter(v.alt_owner for v in fp if v.alt_owner)
        n = len(fp)
        view.owner_shares[sid] = ({s: c / n for s, c in owners.items()}
                                  if n else {})
    return view
