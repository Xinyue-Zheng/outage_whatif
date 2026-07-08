"""Flip test and dependency table (deterministic; recomputed after every
data update).

Flip test: set an open claim to supported -> verdict; to refuted -> verdict;
different outputs -> the claim holds a ticket; same -> spending on it is
forbidden.

Dependency table: the same computation one step deeper — for each ticketed
lever and outcome, which other tickets die and how much their cheapest
resolving actions would have cost (the savings).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..claims.model import REFUTED, SUPPORTED
from .verdict import Verdict, VerdictContext, compute_verdict


def flip_ticket(cid: str, states: dict, ctx: VerdictContext,
                extra_overrides: dict | None = None) -> bool:
    base = dict(extra_overrides or {})
    v_sup = compute_verdict(states, ctx, {**base, cid: SUPPORTED})
    v_ref = compute_verdict(states, ctx, {**base, cid: REFUTED})
    return v_sup.key() != v_ref.key()


def flip_all_tickets(open_cids: list, states: dict, ctx: VerdictContext,
                     extra_overrides: dict | None = None) -> dict:
    return {cid: flip_ticket(cid, states, ctx, extra_overrides)
            for cid in open_cids}


@dataclass
class DepRow:
    lever_cid: str
    outcome: str                       # supported | refuted
    consequence: str                   # human-readable chain
    dead_tickets: list = field(default_factory=list)
    savings: float = 0.0

    def row_id(self) -> str:
        return f"{self.lever_cid}={self.outcome}"


def _verdict_delta(v0: Verdict, v1: Verdict) -> str:
    parts = []
    for sid, sv1 in sorted(v1.per_subregion.items()):
        sv0 = v0.per_subregion.get(sid)
        if sv0 and sv0.tier != sv1.tier:
            parts.append(f"{sid} tier {sv0.tier}->{sv1.tier}")
    if v0.overall != v1.overall:
        parts.append(f"overall {v0.overall!r}->{v1.overall!r}")
    return "; ".join(parts) if parts else "no verdict change"


def dependency_table(open_cids: list, states: dict, ctx: VerdictContext,
                     price_of) -> list[DepRow]:
    """price_of(cid) -> price of the claim's cheapest resolving action
    (0.0 if none is on the menu)."""
    base_tickets = flip_all_tickets(open_cids, states, ctx)
    ticketed = [c for c in open_cids if base_tickets[c]]
    v0 = compute_verdict(states, ctx)
    rows: list[DepRow] = []
    for lever in ticketed:
        for outcome in (SUPPORTED, REFUTED):
            ov = {lever: outcome}
            v1 = compute_verdict(states, ctx, ov)
            others = [c for c in open_cids if c != lever]
            new_tickets = flip_all_tickets(others, states, ctx, ov)
            dead = sorted(c for c in others
                          if base_tickets.get(c) and not new_tickets[c])
            savings = round(sum(price_of(c) or 0.0 for c in dead), 2)
            chain = _verdict_delta(v0, v1)
            if dead:
                chain += " => tickets die: " + ", ".join(dead)
            rows.append(DepRow(lever_cid=lever, outcome=outcome,
                               consequence=chain, dead_tickets=dead,
                               savings=savings))
    return rows
