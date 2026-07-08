"""Strict JSON schemas for the two agent seats, plus the mechanical
validators that reject non-compliant responses (one retry, then fallback).

The API-side schema is static (dynamic keys are arrays, dictionary lookups
happen in the validators); round-specific completeness — every ticketed item
graded, every outcome bucket covered, citations verbatim — is verified here
in code, so the same rejection paths are exercised with the MockLLM.
"""

from __future__ import annotations

from .seats import GRADES

SEAT1_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item_id": {"type": "string"},
                    "grade": {"type": "string",
                              "enum": ["high", "mid", "low"]},
                    "citation": {"type": "string"},
                    "rationale": {"type": "string"},
                    "clue": {"type": ["string", "null"]},
                    "no_clue_found_anchor_followed": {"type": "boolean"},
                },
                "required": ["item_id", "grade", "citation", "rationale",
                             "clue", "no_clue_found_anchor_followed"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["items"],
    "additionalProperties": False,
}

SEAT2_SCHEMA = {
    "type": "object",
    "properties": {
        "chosen_aid": {"type": "string"},
        "predicted_bucket": {"type": "string"},
        "grade": {"type": "string", "enum": ["high", "mid", "low"]},
        "citation": {"type": "string"},
        "rationale": {"type": "string"},
        "contingencies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "bucket": {"type": "string"},
                    "line": {"type": "string"},
                },
                "required": ["bucket", "line"],
                "additionalProperties": False,
            },
        },
        "escalation": {
            "type": ["object", "null"],
            "properties": {
                "chosen_effective_cost": {"type": "number"},
                "incumbent_aid": {"type": "string"},
                "incumbent_effective_cost": {"type": "number"},
                "predicted_incumbent_bucket": {"type": "string"},
            },
            "required": ["chosen_effective_cost", "incumbent_aid",
                         "incumbent_effective_cost",
                         "predicted_incumbent_bucket"],
            "additionalProperties": False,
        },
        "judgment_firming": {"type": "boolean"},
        "veto_justification": {"type": ["string", "null"]},
    },
    "required": ["chosen_aid", "predicted_bucket", "grade", "citation",
                 "rationale", "contingencies", "escalation",
                 "judgment_firming", "veto_justification"],
    "additionalProperties": False,
}


def verify_citation(citation: str, tables_text: str) -> bool:
    """A citation must be a verbatim substring of the code-produced tables."""
    return isinstance(citation, str) and len(citation.strip()) >= 4 \
        and citation.strip() in tables_text


def validate_seat1(resp: dict, expected_items: set, tables_text: str) -> str | None:
    """Returns a rejection reason, or None if compliant."""
    items = resp.get("items")
    if not isinstance(items, list):
        return "response missing 'items' list"
    seen = {}
    for it in items:
        if not isinstance(it, dict) or "item_id" not in it:
            return "malformed item entry"
        if it.get("grade") not in GRADES:
            return f"invalid grade {it.get('grade')!r} for {it.get('item_id')}"
        if not verify_citation(it.get("citation", ""), tables_text):
            return (f"fabricated citation for {it['item_id']}: "
                    f"{it.get('citation')!r} does not appear verbatim in the "
                    f"board/dependency/digest tables")
        if it.get("clue") is None and not it.get("no_clue_found_anchor_followed"):
            return (f"{it['item_id']}: no clue named but "
                    f"no_clue_found_anchor_followed not declared")
        seen[it["item_id"]] = it
    missing = expected_items - set(seen)
    if missing:
        return f"missing grades for ticketed items: {sorted(missing)}"
    return None


def _effective_cost(action, predicted_bucket: str) -> float:
    """Worst-case decisiveness accounting: a predicted ambiguous bucket
    forces the follow-up with certainty (escalation_mode=worst_case)."""
    from ..planning.menu import AMBIGUOUS
    amb = AMBIGUOUS.get(action.kind)
    return round(action.price + (action.followup_price
                                 if predicted_bucket == amb else 0.0), 2)


def validate_seat2(resp: dict, menu: list, candidates: list,
                   tables_text: str, deps: list) -> str | None:
    """Returns a rejection reason, or None if compliant.  Only the bucket
    predictions belong to the agent — the arithmetic is re-verified here."""
    by_aid = {a.aid: a for a in menu}
    aid = resp.get("chosen_aid")
    if aid not in by_aid:
        return f"chosen action {aid!r} is not on the filtered menu"
    action = by_aid[aid]
    if resp.get("grade") not in GRADES:
        return f"invalid grade {resp.get('grade')!r}"
    if resp.get("predicted_bucket") not in action.buckets:
        return (f"predicted bucket {resp.get('predicted_bucket')!r} not in "
                f"the action's outcome space {action.buckets}")
    if not verify_citation(resp.get("citation", ""), tables_text):
        return (f"fabricated citation: {resp.get('citation')!r} does not "
                f"appear verbatim in the tables")
    # a contingency line for EVERY bucket in the chosen action's outcome space
    given = {c.get("bucket") for c in resp.get("contingencies", [])
             if isinstance(c, dict) and c.get("line")}
    missing = [b for b in action.buckets if b not in given]
    if missing:
        return (f"missing contingency line(s) for outcome bucket(s) "
                f"{missing} of {aid}")
    # decisiveness accounting: non-cheapest choices must exhibit the
    # arithmetic, and the arithmetic must check out
    resolving = sorted((a for a in menu if a.kind != "profile"),
                       key=lambda a: (a.price, a.aid))
    if resolving and action.kind != "profile":
        incumbent = resolving[0]
        if action.aid != incumbent.aid:
            esc = resp.get("escalation")
            if not isinstance(esc, dict):
                return ("chose a non-cheapest action without exhibiting "
                        "the escalation arithmetic")
            if esc.get("incumbent_aid") != incumbent.aid:
                return (f"escalation names {esc.get('incumbent_aid')!r} as "
                        f"incumbent; the cheapest action is {incumbent.aid}")
            ib = esc.get("predicted_incumbent_bucket")
            if ib not in incumbent.buckets:
                return (f"predicted incumbent bucket {ib!r} not in "
                        f"{incumbent.buckets}")
            want_chosen = _effective_cost(action, resp["predicted_bucket"])
            want_inc = _effective_cost(incumbent, ib)
            if abs(float(esc.get("chosen_effective_cost", -1)) - want_chosen) > 0.02 \
                    or abs(float(esc.get("incumbent_effective_cost", -1)) - want_inc) > 0.02:
                return (f"escalation arithmetic does not re-verify: chosen "
                        f"effective {want_chosen}, incumbent effective "
                        f"{want_inc} (worst-case rule)")
            if want_chosen > want_inc:
                return ("escalation arithmetic does not justify the choice: "
                        f"chosen effective cost {want_chosen} exceeds the "
                        f"incumbent's {want_inc}")
    # veto variant: targeting a runner-up while the leader has actions
    # requires a justification citing a dependency row verbatim
    leader = candidates[0] if candidates else None
    leader_has_actions = any(a.claim_cid == leader and a.kind != "profile"
                             for a in menu)
    if leader is not None and action.claim_cid != leader and leader_has_actions \
            and action.kind != "profile":
        vj = resp.get("veto_justification")
        row_ids = {r.row_id() for r in deps}
        if not vj or not any(rid in vj for rid in row_ids):
            return ("veto of the leader requires a justification citing a "
                    "dependency row id verbatim")
    return None
