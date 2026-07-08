"""Deterministic claim adjudication.

Every rule here is a named function traceable to Section 4 of the design.
All coverage/robustness statistics count evidence cells, never raw points.
"""

from __future__ import annotations

from ..config import Config
from ..geometry.wilson import wilson_interval
from .evidence_view import EvidenceView, PMStore
from .model import (CAPACITY, COVERAGE, INTEGRITY, REFUTED, ROBUSTNESS,
                    SUPPORTED, UNDECIDED, Claim, ClaimSet)

# DESIGN-GAP: a subregion whose sampled cells are mostly outside the target
# footprint is deemed unaffected by the outage (same 30% rule as the
# simulator's ground truth) once minimally sampled.
UNAFFECTED_FOOTPRINT_SHARE = 0.30
UNAFFECTED_MIN_CELLS = 4


def adjudicate_coverage(claim: Claim, view: EvidenceView, cfg: Config) -> None:
    """Wilson interval on the passing proportion over footprint evidence
    cells, tested against theta.  Entirely above -> supported; entirely
    below -> refuted; straddling -> undecided (remedy: densify unsampled
    evidence cells)."""
    votes = view.votes_by_sid.get(claim.subject, [])
    fp = [v for v in votes if v.in_footprint]
    n_all, n = len(votes), len(fp)
    unsampled = len(view.unsampled_cells.get(claim.subject, []))
    census_all = (claim.subject != "BG" and unsampled == 0 and n_all > 0)
    claim.detail.update(cells_sampled=n_all, footprint_cells=n,
                        unsampled=unsampled)
    # unaffected rule: below the minimum cell count it applies only once the
    # census is complete (a tiny fully-sampled settlement with no footprint
    # cells is decidedly outside the target's footprint)
    if (n_all >= UNAFFECTED_MIN_CELLS or census_all) \
            and n < UNAFFECTED_FOOTPRINT_SHARE * n_all:
        claim.state = SUPPORTED
        claim.detail.update(unaffected=True, interval=None)
        claim.remedy = ""
        return
    claim.detail["unaffected"] = False
    if n == 0:
        claim.state = UNDECIDED
        claim.remedy = "sample this subregion's evidence cells"
        claim.detail["interval"] = None
        return
    k = sum(v.alt_ok for v in fp)
    lo, hi = wilson_interval(k, n, cfg.z)
    claim.detail.update(passing=k, interval=(round(lo, 3), round(hi, 3)))
    theta = cfg.policy.theta
    census = (claim.subject != "BG"
              and not view.unsampled_cells.get(claim.subject, []))
    if census:
        # every evidence cell of the (finite) subregion is sampled: the
        # exact proportion decides — Wilson governs only partial sampling.
        claim.detail["census"] = True
        if k / n >= theta:
            claim.state, claim.remedy = SUPPORTED, ""
        else:
            claim.state, claim.remedy = REFUTED, ""
    elif lo > theta:
        claim.state, claim.remedy = SUPPORTED, ""
    elif hi < theta:
        claim.state, claim.remedy = REFUTED, ""
    else:
        claim.state = UNDECIDED
        claim.remedy = "densify unsampled evidence cells"


def capacity_zone(mean: float, support_edge: float | None, cfg: Config) -> str:
    """Hourly-tier zone of an hourly-mean PRB value.  The support-zone edge
    comes from the calibration table; if no safe edge exists the hourly tier
    cannot declare support (no support zone)."""
    if mean >= cfg.policy.pi_hi:
        return "refute_zone"
    if support_edge is not None and mean < support_edge:
        return "support_zone"
    return "middle_zone"


def adjudicate_capacity_leaf(claim: Claim, pm: PMStore,
                             support_edge: float | None, cfg: Config) -> None:
    """Two-tier adjudication for one entity (site, or drilled-down cell)."""
    ent = claim.subject
    q15 = pm.q15.get(ent)
    if q15:
        frac = sum(v >= cfg.policy.pi_hi for v in q15) / len(q15)
        claim.detail.update(tier="15min", spike_frac=round(frac, 3),
                            n_bins=len(q15))
        if frac > cfg.policy.cap15_refute_frac:
            claim.state, claim.remedy = REFUTED, ""
        else:
            claim.state, claim.remedy = SUPPORTED, ""   # strict tier
            claim.detail["phrase"] = "no capacity obstacle found"
        return
    mean = pm.hourly_mean(ent)
    if mean is None:
        claim.state = UNDECIDED
        claim.remedy = "buy hourly PM for the outage-matched window"
        claim.detail.update(tier="none", hourly_mean=None, zone=None)
        return
    zone = capacity_zone(mean, support_edge, cfg)
    claim.detail.update(tier="hourly", hourly_mean=round(mean, 3), zone=zone,
                        support_edge=support_edge)
    if zone == "refute_zone":
        claim.state, claim.remedy = REFUTED, ""
    elif zone == "support_zone":
        claim.state, claim.remedy = SUPPORTED, ""       # calibrated lenient tier
        claim.detail["phrase"] = "no capacity obstacle found"
    else:
        claim.state = UNDECIDED
        claim.remedy = "buy 15-minute PM for the outage-matched window"


def aggregate_capacity_parent(parent: Claim, children: list[Claim]) -> None:
    """Drilled-down site claim aggregates its per-cell children:
    any child refuted -> refuted; all supported -> supported; else undecided."""
    states = [c.state for c in children]
    if REFUTED in states:
        parent.state, parent.remedy = REFUTED, ""
    elif all(s == SUPPORTED for s in states):
        parent.state, parent.remedy = SUPPORTED, ""
    else:
        parent.state = UNDECIDED
        parent.remedy = "resolve per-cell capacity children"
    parent.detail["children_states"] = {c.cid: c.state for c in children}


def adjudicate_robustness(claim: Claim, view: EvidenceView, cfg: Config) -> None:
    """Top owner's share of best alternatives, Wilson-tested against kappa."""
    shares = view.owner_shares.get(claim.subject, {})
    votes = view.votes_by_sid.get(claim.subject, [])
    fp = [v for v in votes if v.in_footprint and v.alt_owner]
    n = len(fp)
    cov = claim.detail.get("coverage_unaffected", False)
    if n == 0:
        claim.state = UNDECIDED if not cov else SUPPORTED
        claim.remedy = "sample this subregion's evidence cells"
        claim.detail["interval"] = None
        return
    top_site = max(shares, key=lambda s: (shares[s], s))
    k = sum(1 for v in fp if v.alt_owner == top_site)
    lo, hi = wilson_interval(k, n, cfg.z)
    claim.detail.update(top_owner=top_site, top_share=round(k / n, 3),
                        interval=(round(lo, 3), round(hi, 3)), n_cells=n)
    kappa = cfg.policy.kappa
    census = (claim.subject != "BG"
              and not view.unsampled_cells.get(claim.subject, []))
    if census:
        claim.detail["census"] = True
        if k / n <= kappa:
            claim.state, claim.remedy = SUPPORTED, ""
        else:
            claim.state, claim.remedy = REFUTED, ""
    elif hi < kappa:
        claim.state, claim.remedy = SUPPORTED, ""
    elif lo > kappa:
        claim.state, claim.remedy = REFUTED, ""
    else:
        claim.state = UNDECIDED
        claim.remedy = "densify unsampled evidence cells"


def adjudicate_integrity(claim: Claim, view: EvidenceView, cfg: Config) -> None:
    """The ring outside boundary sector s must contain essentially no
    footprint points (counted as evidence cells)."""
    sector = int(claim.subject)
    votes = view.ring_votes.get(sector, [])
    contaminated = [v for v in votes if v.in_footprint]
    claim.detail.update(ring_cells=len(votes), contaminated=len(contaminated))
    if contaminated:
        claim.state = REFUTED
        claim.remedy = "expand the boundary in this sector"
    elif len(votes) >= cfg.integrity_min_cells:
        claim.state, claim.remedy = SUPPORTED, ""
    else:
        claim.state = UNDECIDED
        claim.remedy = "sample the integrity ring in this sector"


def adjudicate_all(claims: ClaimSet, view: EvidenceView, pm: PMStore,
                   support_edge: float | None, cfg: Config) -> None:
    """Re-adjudicate every alive claim from current evidence (idempotent)."""
    for c in claims.by_type(COVERAGE):
        adjudicate_coverage(c, view, cfg)
    for c in claims.by_type(ROBUSTNESS):
        cov_cid = f"COV:{c.subject}"
        if cov_cid in claims:
            c.detail["coverage_unaffected"] = \
                claims.get(cov_cid).detail.get("unaffected", False)
        adjudicate_robustness(c, view, cfg)
    caps = claims.by_type(CAPACITY)
    leaves = [c for c in caps if not c.drilled]
    for c in leaves:
        adjudicate_capacity_leaf(c, pm, support_edge, cfg)
    for c in caps:
        if c.drilled:
            kids = [claims.get(k) for k in c.children]
            for k in kids:
                adjudicate_capacity_leaf(k, pm, support_edge, cfg)
            aggregate_capacity_parent(c, kids)
    for c in claims.by_type(INTEGRITY):
        adjudicate_integrity(c, view, cfg)
