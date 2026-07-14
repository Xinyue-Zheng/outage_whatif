"""Evidence views: everything adjudication needs, computed from raw stores.

Assignments (deterministic):
* a demand object owns every evidence cell containing one of its raster
  pixels (area objects; line/point geometries are a reserved extension);
* the background bucket "BG" owns every sampled cell owned by no object.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ..config import Config
from ..geometry.evidence import EvidenceGrid, cell_of
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
    """Evidence cells belonging to an area object (via its pixel centers)."""
    return {cell_of(*raster.pixel_center(iy, ix), cell_m)
            for iy, ix in sub.pixels}


@dataclass
class EvidenceView:
    """Per-round snapshot of aggregated evidence, keyed the way claims need it."""
    votes_by_sid: dict = field(default_factory=dict)     # sid -> [CellVote]
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


def build_view(grid: EvidenceGrid, subregions: dict, cfg: Config,
               raster: PopulationRaster) -> EvidenceView:
    """subregions: sid -> Subregion for the area objects under claims."""
    view = EvidenceView()
    sampled = grid.sampled_cells()
    assigned: set = set()

    for sid, sub in subregions.items():
        cells = subregion_cells(sub, raster, cfg.evidence_cell_m)
        have = cells & sampled
        assigned |= have
        view.votes_by_sid[sid] = grid.votes(have)
        view.unsampled_cells[sid] = sorted(cells - sampled)

    # background: every sampled cell owned by no object
    bg_cells = sorted(sampled - assigned)
    view.votes_by_sid["BG"] = grid.votes(bg_cells)
    view.unsampled_cells["BG"] = []      # BG has no finite cell inventory

    # owner shares over footprint cells
    for sid, votes in view.votes_by_sid.items():
        fp = [v for v in votes if v.in_footprint]
        owners = Counter(v.alt_owner for v in fp if v.alt_owner)
        n = len(fp)
        view.owner_shares[sid] = ({s: c / n for s, c in owners.items()}
                                  if n else {})
    return view
