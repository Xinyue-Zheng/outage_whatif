"""Flip test (deterministic; recomputed after every data update).

Set an open claim to supported -> verdict; to refuted -> verdict; different
outputs -> the claim holds a ticket; same -> spending on it is forbidden.
Relevance is checked at purchase time by the spend gate — there is no
rendered dependency table.
"""

from __future__ import annotations

from ..claims.model import REFUTED, SUPPORTED
from .verdict import VerdictContext, compute_verdict


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
