"""The verdict function (deterministic).

Definitional rules (no discretion):
* refuted integrity blocks the run until boundary expansion;
* refuted coverage -> hole; a hole is severe iff subregion population >= P0;
* coverage + capacity (strict 15-min tier, or calibrated lenient hourly
  tier) + robustness all supported -> absorbable.

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
OVERALL_UND = "undecided"
OVERALL_BLOCKED = "blocked (integrity refuted — boundary expansion required)"


@dataclass(frozen=True)
class SubVerdict:
    tier: str
    severe: bool = False
    bottleneck_type: str | None = None       # claim type that limited the tier
    bottleneck_subject: str | None = None    # e.g. the congested neighbor


@dataclass
class Verdict:
    overall: str
    blocked: bool
    per_subregion: dict = field(default_factory=dict)   # sid -> SubVerdict

    def key(self) -> tuple:
        """Comparable identity for flip tests / stability checks."""
        return (self.overall, self.blocked,
                tuple(sorted((s, v.tier, v.severe)
                             for s, v in self.per_subregion.items())))


@dataclass
class VerdictContext:
    """Everything the verdict needs besides the claim states themselves —
    fixed while a flip test perturbs states."""
    sids: list                                # settlement sids + "BG"
    populations: dict                         # sid -> population
    major_exits: dict                         # sid -> [neighbor sites]
    unaffected: dict = field(default_factory=dict)   # sid -> bool
    drilled: dict = field(default_factory=dict)      # parent cid -> [child cids]
    integrity_cids: list = field(default_factory=list)
    top_owner: dict = field(default_factory=dict)    # sid -> site (robustness)
    policy: Policy = field(default_factory=Policy)

    @classmethod
    def from_claims(cls, claims, view, populations, policy) -> "VerdictContext":
        sids = sorted(populations)
        ctx = cls(sids=sids, populations=dict(populations),
                  major_exits={sid: view.major_exits(sid, policy.sigma)
                               for sid in sids},
                  policy=policy)
        for c in claims.alive():
            if c.ctype == "coverage":
                ctx.unaffected[c.subject] = c.detail.get("unaffected", False)
            elif c.ctype == "integrity":
                ctx.integrity_cids.append(c.cid)
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

    blocked = any(eff(cid) == REFUTED for cid in ctx.integrity_cids)
    integrity_open = any(eff(cid) == UNDECIDED for cid in ctx.integrity_cids)

    per: dict[str, SubVerdict] = {}
    for sid in ctx.sids:
        pop = ctx.populations.get(sid, 0.0)
        severe_pop = pop >= ctx.policy.P0
        cov = eff(f"COV:{sid}")
        if ctx.unaffected.get(sid, False) and f"COV:{sid}" not in ov:
            per[sid] = SubVerdict(ABSORBABLE)
            continue
        cap_states = {s: eff(f"CAP:{s}") for s in ctx.major_exits.get(sid, [])}
        refuted_caps = sorted(s for s, st in cap_states.items() if st == REFUTED)
        open_caps = sorted(s for s, st in cap_states.items() if st == UNDECIDED)
        # A refuted major-exit capacity is TERMINAL for the subregion: it is
        # degraded and further coverage/robustness spending cannot change
        # that (this is what lets downstream tickets die in the dependency
        # table, per the design's worked example).
        if refuted_caps:
            per[sid] = SubVerdict(DEGRADED, bottleneck_type="capacity",
                                  bottleneck_subject=refuted_caps[0])
            continue
        if cov == REFUTED:
            per[sid] = SubVerdict(HOLE, severe=severe_pop,
                                  bottleneck_type="coverage")
            continue
        if cov == UNDECIDED:
            per[sid] = SubVerdict(UND, bottleneck_type="coverage")
            continue
        rob = eff(f"ROB:{sid}")
        # Refuted robustness pins the tier at "degraded" even while capacity
        # claims remain open — either capacity outcome leaves the subregion
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

    if blocked:
        return Verdict(OVERALL_BLOCKED, True, per)
    tiers = [v.tier for v in per.values()]
    severe = any(v.tier == HOLE and v.severe for v in per.values())
    if severe:
        overall = OVERALL_SEVERE
    elif UND in tiers or integrity_open:
        overall = OVERALL_UND
    elif HOLE in tiers or DEGRADED in tiers:
        overall = OVERALL_DEGRADED
    else:
        overall = OVERALL_FULL
    return Verdict(overall, False, per)
