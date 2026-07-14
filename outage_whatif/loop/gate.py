"""The generalized spend gate.

Every committing action passes through ``gate(request, state)``.  For a
PurchaseRequest the checks run in order — schema; price within remaining
budget; target exists and is open; claim targets must hold a flip ticket;
predicted bucket inside the outcome space; citation resolves verbatim
against the briefing + this turn's tool outputs; price within the
confidence cap ({low: 0.02, mid: 0.10, high: 1.0} x initial budget).  A
denial returns the exact failing check as text (fed back to the agent for
its single retry).  Non-purchase commits get their own instrument checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..agents.schemas import GRADES, verify_citation
from ..config import Config

# outcome spaces per purchase kind (finite, code-owned)
OUTCOME_SPACE = {
    "probe": ["target_present", "target_absent", "mixed"],
    "densify": ["interval_above", "interval_below", "still_straddling"],
    "pm_hourly": ["support_zone", "middle_zone", "refute_zone"],
    "pm_15min": ["support", "refute"],
    "target_kpi": ["heavy_cells_present", "all_cells_light"],
    "profile": ["anchor_confirms", "anchor_shifts"],
}

CONFIDENCE_CAPS = {"low": 0.02, "mid": 0.10, "high": 1.0}

COMMIT_ACTIONS = ("purchase", "register_object", "dismiss", "split",
                  "drill_down", "accept_default", "declare_done")


def outcome_space(kind: str) -> list:
    return list(OUTCOME_SPACE.get(kind, []))


@dataclass
class PurchaseRequest:
    """A resolved purchase: params are concrete (points expanded, entities
    named) before the gate sees it."""
    kind: str
    target: str                       # claim_id | gap_id
    params: dict
    predicted_bucket: str
    confidence: str
    citation: str
    rationale: str = ""
    price: float = 0.0                # quoted by code, never by the agent
    aid: str = ""


def price_request(req: PurchaseRequest, provider, cfg: Config,
                  k_hours: int) -> float:
    """One quote per kind; PM is priced over the k matched hours."""
    if req.kind in ("probe", "densify"):
        return provider.quote("coverage", n_points=len(req.params["points"]))
    if req.kind in ("pm_hourly", "pm_15min"):
        gran = "hourly" if req.kind == "pm_hourly" else "15min"
        return provider.quote("pm", granularity=gran,
                              n_entities=len(req.params["entities"]),
                              hours=k_hours)
    if req.kind == "target_kpi":
        return provider.quote("pm", granularity="hourly",
                              n_entities=len(req.params["entities"]),
                              hours=k_hours)
    if req.kind == "profile":
        return provider.quote("profile", kind=req.params["profile_kind"])
    raise ValueError(f"unknown purchase kind {req.kind!r}")


@dataclass
class GateState:
    """Everything the gate reads (assembled by the runner each round)."""
    claims: object                    # ClaimSet
    gap_ids: set
    flip: object                      # callable cid -> bool (ticket)
    shown_text: str                   # briefing + this turn's tool outputs
    remaining: float
    budget_initial: float
    purchased_signatures: set = field(default_factory=set)


def gate(req: PurchaseRequest, state: GateState) -> str | None:
    """None = approved; else the exact failing check as text."""
    # 1. schema
    if req.kind not in OUTCOME_SPACE:
        return (f"unknown purchase kind {req.kind!r}; kinds: "
                f"{sorted(OUTCOME_SPACE)}")
    if req.confidence not in GRADES:
        return f"confidence must be one of {GRADES}, got {req.confidence!r}"
    if not req.target:
        return "purchase must name a target claim_id or gap_id"
    # 2. affordability
    if req.price > state.remaining:
        return (f"price {req.price} exceeds remaining budget "
                f"{state.remaining}")
    # 3. target exists and is open
    is_claim = req.target in state.claims
    if is_claim:
        c = state.claims.get(req.target)
        if not c.alive or c.state != "undecided":
            return (f"claim {req.target} is not open "
                    f"(state={c.state}, alive={c.alive})")
    elif req.target not in state.gap_ids:
        return (f"target {req.target!r} is neither an open claim nor a "
                f"current audit gap")
    # 4. claims must hold a flip ticket
    if is_claim and not state.flip(req.target):
        return (f"claim {req.target} holds no flip ticket — spending on it "
                f"cannot change the verdict")
    # 5. bucket in outcome space
    if req.predicted_bucket not in OUTCOME_SPACE[req.kind]:
        return (f"predicted bucket {req.predicted_bucket!r} not in the "
                f"outcome space {OUTCOME_SPACE[req.kind]} of {req.kind}")
    # 6. citation resolves
    if not verify_citation(req.citation, state.shown_text):
        return (f"citation {req.citation!r} does not appear verbatim in the "
                f"briefing or this turn's tool outputs")
    # 7. confidence cap
    cap = CONFIDENCE_CAPS[req.confidence] * state.budget_initial
    if req.price > cap:
        return (f"price {req.price} exceeds the {req.confidence}-confidence "
                f"cap {round(cap, 2)} "
                f"({CONFIDENCE_CAPS[req.confidence]} x initial budget)")
    # duplicate-query lookup (mechanical)
    sig = _signature(req)
    if sig is not None and sig in state.purchased_signatures:
        return f"duplicate query: {sig} was already purchased"
    return None


def _signature(req: PurchaseRequest):
    """Dedup identity: PM/profile queries repeat data; probes/densify hit
    fresh points every time (no signature)."""
    if req.kind in ("pm_hourly", "pm_15min", "target_kpi"):
        gran = "15min" if req.kind == "pm_15min" else "hourly"
        return (req.kind, tuple(sorted(req.params["entities"])), gran)
    if req.kind == "profile":
        return ("profile", req.params["site"], req.params["profile_kind"])
    return None
