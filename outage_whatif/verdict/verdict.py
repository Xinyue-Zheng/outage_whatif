"""The verdict function (deterministic).

Definitional rules (no discretion):
* refuted coverage -> hole;
* refuted major-exit capacity or refuted robustness -> degraded;
* coverage + capacity (strict 15-min tier, or calibrated lenient hourly
  tier) + robustness all supported -> absorbable.

Severity of a hole is a demand-localization question, not a population
question: a hole is severe iff its object is the sole non-dismissed
registered explanation for some target cell carrying material busy-window
traffic (T[c] >= T_severe).  If the holed object shares all its cells with
intact objects the severity is undecided (resolvable by drill-down or, at
close-out, by the conservative policy default).

Policy rules are exactly the [POLICY] constants in config.Policy.

The overriding principle — ambiguity still resolvable by an affordable
in-budget query yields "undecided + named remedy", never a guessed tier —
is enforced by the loop: conservative defaults (direction: degrade) are
applied only at budget exhaustion and flagged `unverified_assumption`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..claims.model import REFUTED, SUPPORTED, UNDECIDED
from ..config import Policy

ABSORBABLE = "absorbable"
DEGRADED = "degraded"
HOLE = "hole"
UND = "undecided"

OVERALL_FULL = "fully absorbable"
OVERALL_DEGRADED = "locally degraded"
OVERALL_SEVERE = "severe hole exists"
OVERALL_UND = "undecided/qualified"

SEVERE_YES = "severe"
SEVERE_NO = "not severe"
SEVERE_UND = "severity undecided"


@dataclass(frozen=True)
class SubVerdict:
    tier: str
    severe: str = SEVERE_NO                  # severe | not severe | severity undecided
    bottleneck_type: str | None = None       # claim type that limited the tier
    bottleneck_subject: str | None = None    # e.g. the congested neighbor


@dataclass
class Verdict:
    overall: str
    per_subregion: dict = field(default_factory=dict)   # sid -> SubVerdict

    def key(self) -> tuple:
        """Comparable identity for flip tests / stability checks."""
        return (self.overall,
                tuple(sorted((s, v.tier, v.severe)
                             for s, v in self.per_subregion.items())))


@dataclass
class VerdictContext:
    """Everything the verdict needs besides the claim states themselves —
    fixed while a flip test perturbs states."""
    sids: list                                # object sids + "BG"
    populations: dict                         # sid -> population (reporting)
    major_exits: dict                         # sid -> [neighbor sites]
    unaffected: dict = field(default_factory=dict)   # sid -> bool
    drilled: dict = field(default_factory=dict)      # parent cid -> [child cids]
    top_owner: dict = field(default_factory=dict)    # sid -> site (robustness)
    # demand localization: sid -> severity string (SEVERE_*), computed by the
    # localization book (sole-explanation test over heavy cells); objects
    # absent from the map are "not severe" holes.
    hole_severity: dict = field(default_factory=dict)
    # residual demand not accounted for by any registered object (upper bound)
    residual_bound: float = 0.0
    residual_ok: bool = True                  # residual_bound <= rho_residual
    policy: Policy = field(default_factory=Policy)

    @classmethod
    def from_claims(cls, claims, view, populations, policy,
                    hole_severity: dict | None = None,
                    residual_bound: float = 0.0,
                    residual_ok: bool = True) -> "VerdictContext":
        sids = sorted(populations)
        ctx = cls(sids=sids, populations=dict(populations),
                  major_exits={sid: view.major_exits(sid, policy.sigma)
                               for sid in sids},
                  hole_severity=dict(hole_severity or {}),
                  residual_bound=residual_bound, residual_ok=residual_ok,
                  policy=policy)
        for c in claims.alive():
            if c.ctype == "coverage":
                ctx.unaffected[c.subject] = c.detail.get("unaffected", False)
            elif c.ctype == "capacity" and c.drilled:
                ctx.drilled[c.cid] = list(c.children)
            elif c.ctype == "robustness":
                ctx.top_owner[c.subject] = c.detail.get("top_owner")
        return ctx


def _effective(cid: str, states: dict, ctx: VerdictContext,
               overrides: dict) -> str:
    """State of a claim under overrides; drilled capacity parents aggregate
    their children unless the parent itself is overridden."""
    if cid in overrides:
        return overrides[cid]
    if cid in ctx.drilled:
        kid_states = [_effective(k, states, ctx, overrides)
                      for k in ctx.drilled[cid]]
        if REFUTED in kid_states:
            return REFUTED
        if kid_states and all(s == SUPPORTED for s in kid_states):
            return SUPPORTED
        return UNDECIDED
    return states.get(cid, UNDECIDED)


def compute_verdict(states: dict, ctx: VerdictContext,
                    overrides: dict | None = None) -> Verdict:
    """Pure function: claim states (+ optional flip overrides) -> verdict."""
    ov = overrides or {}
    eff = lambda cid: _effective(cid, states, ctx, ov)  # noqa: E731

    per: dict[str, SubVerdict] = {}
    for sid in ctx.sids:
        cov = eff(f"COV:{sid}")
        if ctx.unaffected.get(sid, False) and f"COV:{sid}" not in ov:
            per[sid] = SubVerdict(ABSORBABLE)
            continue
        cap_states = {s: eff(f"CAP:{s}") for s in ctx.major_exits.get(sid, [])}
        refuted_caps = sorted(s for s, st in cap_states.items() if st == REFUTED)
        open_caps = sorted(s for s, st in cap_states.items() if st == UNDECIDED)
        # A refuted major-exit capacity is TERMINAL for the object: it is
        # degraded and further coverage/robustness spending cannot change
        # that (this is what lets downstream tickets die under flip
        # overrides).
        if refuted_caps:
            per[sid] = SubVerdict(DEGRADED, bottleneck_type="capacity",
                                  bottleneck_subject=refuted_caps[0])
            continue
        if cov == REFUTED:
            per[sid] = SubVerdict(HOLE,
                                  severe=ctx.hole_severity.get(sid, SEVERE_NO),
                                  bottleneck_type="coverage")
            continue
        if cov == UNDECIDED:
            per[sid] = SubVerdict(UND, bottleneck_type="coverage")
            continue
        rob = eff(f"ROB:{sid}")
        # Refuted robustness pins the tier at "degraded" even while capacity
        # claims remain open — either capacity outcome leaves the object
        # degraded, so the tier is decided (and capacity spending here would
        # rightly be forbidden by the flip test).
        if rob == REFUTED:
            per[sid] = SubVerdict(DEGRADED, bottleneck_type="robustness",
                                  bottleneck_subject=ctx.top_owner.get(sid))
            continue
        if open_caps:
            per[sid] = SubVerdict(UND, bottleneck_type="capacity",
                                  bottleneck_subject=open_caps[0])
            continue
        if rob == UNDECIDED:
            per[sid] = SubVerdict(UND, bottleneck_type="robustness")
            continue
        per[sid] = SubVerdict(ABSORBABLE)

    tiers = [v.tier for v in per.values()]
    severe = any(v.tier == HOLE and v.severe == SEVERE_YES
                 for v in per.values())
    if severe:
        overall = OVERALL_SEVERE
    elif UND in tiers:
        overall = OVERALL_UND
    elif HOLE in tiers or DEGRADED in tiers:
        overall = OVERALL_DEGRADED
    elif ctx.residual_ok:
        overall = OVERALL_FULL
    else:
        # everything registered is absorbable, but too much demand remains
        # unaccounted for to declare full absorption
        overall = OVERALL_UND
    return Verdict(overall, per)
