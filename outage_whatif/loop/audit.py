"""The audit: what does the current state NOT yet account for?

Deterministic code, run every round.  Each Gap names something the verdict
cannot yet stand on, with a stake (T[c] or an importance bound) and a
suggested remedy the agent may buy.  The round-zero audit is naturally
non-empty — that is what makes exploration fundable.

Gap kinds:
* demand_ledger_absent — no complete cell-level busy-window KPI for the
  target;
* cell_unlocalized — a target cell whose demand is unknown/unaccounted
  while T[c] >= T_material or T[c] is unknown;
* object_hypothesized — a candidate object neither confirmed nor dismissed;
* object_open_claims — an object above importance_floor with an open claim;
* residual_uninvestigated — residual_bound exceeds rho_residual and nothing
  has been bought against it yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Config
from ..demand.localization import ACCOUNTED, CellLocalizationBook
from ..demand.objects import CONFIRMED, HYPOTHESIZED, ObjectRegistry


@dataclass
class Gap:
    gap_id: str
    kind: str
    subject: str
    stake: float | None                 # T[c] or importance bound (traffic)
    remedy: str
    suggested_points: list = field(default_factory=list)

    def line(self) -> str:
        stake = "T unknown" if self.stake is None else f"stake={self.stake}"
        return f"{self.gap_id} | {self.kind} | {self.subject} | {stake} | {self.remedy}"


def audit(book: CellLocalizationBook, registry: ObjectRegistry, claims,
          raster, cfg: Config, probes: list | None = None,
          residual_investigated: bool = False) -> list[Gap]:
    """probes: the ~suggested_random_probes exploration locations generated
    at setup — surfaced as a suggested remedy, never auto-executed."""
    gaps: list[Gap] = []
    probes = probes or []

    # ---- demand ledger
    missing_T = [c for c in book.cells if c not in book.traffic]
    if missing_T:
        gaps.append(Gap(
            gap_id="GAP:ledger", kind="demand_ledger_absent",
            subject=book.target, stake=None,
            remedy=(f"buy cell-level busy-window KPI for the target "
                    f"({len(missing_T)} of {len(book.cells)} cells unknown); "
                    f"a cheaper site-level peek "
                    f"(target_kpi granularity='site', 1 entity) is also "
                    f"available but does not close this gap")))

    # ---- per-cell localization
    for cell in book.cells:
        t = book.T(cell)
        status = book.status(cell, registry, raster, cfg)
        if status == ACCOUNTED:
            continue
        if t is None or t >= cfg.policy.T_material:
            gaps.append(Gap(
                gap_id=f"GAP:cell:{cell}", kind="cell_unlocalized",
                subject=cell, stake=t,
                remedy=("buy coverage probes along this cell's empirical "
                        "direction (see residual_map) or register the "
                        "object the demand points at"),
                suggested_points=list(probes)))

    # ---- objects
    for obj in registry.by_state(HYPOTHESIZED):
        gaps.append(Gap(
            gap_id=f"GAP:obj:{obj.id}", kind="object_hypothesized",
            subject=obj.id,
            stake=book.importance_bound(obj.id, registry, raster, cfg) or None,
            remedy=("buy coverage probes inside the object to confirm it "
                    "(target visible) or request dismissal "
                    f"(>= {cfg.dismiss_min_units} units, none showing the "
                    "target)")))
    for obj in registry.by_state(CONFIRMED):
        open_cids = [cid for cid in obj.claim_ids
                     if cid in claims and claims.get(cid).alive
                     and claims.get(cid).state == "undecided"]
        if not open_cids:
            continue
        imp = book.importance_bound(obj.id, registry, raster, cfg)
        if imp >= cfg.policy.importance_floor:
            gaps.append(Gap(
                gap_id=f"GAP:claims:{obj.id}", kind="object_open_claims",
                subject=obj.id, stake=imp,
                remedy=f"resolve open claims: {', '.join(sorted(open_cids))}"))

    # ---- residual
    rb = book.residual_bound(registry, raster, cfg)
    if rb is not None and rb > cfg.policy.rho_residual \
            and not residual_investigated:
        gaps.append(Gap(
            gap_id="GAP:residual", kind="residual_uninvestigated",
            subject=book.target, stake=round(rb, 4),
            remedy=("residual bound exceeds rho_residual: follow the "
                    "residual_map (unmapped point coordinates) — buy probes "
                    "there or RegisterObject(provenance='residual')"),
            suggested_points=list(probes)))

    return gaps
