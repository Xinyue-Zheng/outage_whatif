"""Footprint membership and best-alternative analysis of a coverage point.

Definitions (Section 4 of the design):

* Footprint point: the target site serves the point OR appears among the
  top-5 backups above tau_acc.
* Best alternative: the strongest candidate after deleting *every cell of
  the target site*.  Same-site filtering via the cell->site roster is
  mandatory — a full-site outage removes co-sited backups together.
"""

from __future__ import annotations

from .evidence import PointObs


def analyze_coverage_point(point_cov, target_site: str, roster: dict,
                           tau_acc: float,
                           same_site_filtering: bool = True) -> PointObs:
    """Turn one raw coverage answer into a PointObs.

    ``point_cov`` carries .x, .y, .serving (cell_id, rsrp) and
    .backups [(cell_id, rsrp) x <=5].  ``roster`` maps cell_id -> site_id.

    ``same_site_filtering=False`` exists ONLY to demonstrate in tests that
    omitting the mandatory filter overstates absorbability; production code
    must never pass False.
    """
    candidates = [point_cov.serving] + list(point_cov.backups)

    in_footprint = any(
        roster[cid] == target_site and rsrp >= tau_acc for cid, rsrp in candidates)

    if same_site_filtering:
        alt_pool = [(cid, r) for cid, r in candidates if roster[cid] != target_site]
    else:
        # broken variant: only the specific serving/backup cell is removed
        alt_pool = [(cid, r) for cid, r in candidates
                    if not (roster[cid] == target_site and (cid, r) == point_cov.serving)]

    if alt_pool:
        best_cid, best_rsrp = max(alt_pool, key=lambda t: (t[1], t[0]))
        alt_ok = best_rsrp >= tau_acc
        alt_owner = roster[best_cid]
    else:
        alt_ok, alt_owner = False, None

    return PointObs(x=point_cov.x, y=point_cov.y, in_footprint=in_footprint,
                    alt_ok=alt_ok, alt_owner=alt_owner)
