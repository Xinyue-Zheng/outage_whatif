"""LLM seats.  The prompts embed the design's protocols verbatim; every
response is mechanically validated (schema completeness, verbatim citations,
re-verified arithmetic).  Any violation: one retry with the reason, then the
round falls back to the rule baseline for that seat only.
"""

from __future__ import annotations

from ..loop.tables import render_board, render_deps, render_digest, render_menu
from .baselines import RuleSeat1AllMid, RuleSeat2Cheapest
from .llm import LLMClient, LLMError
from .schemas import (SEAT1_SCHEMA, SEAT2_SCHEMA, validate_seat1,
                      validate_seat2)
from .seats import Seat1, Seat2, Seat1Output, Seat2Output

SEAT1_SYSTEM = """\
You are Agent 1 (claim prioritization) in a budget-constrained what-if
analysis of a cellular base-station outage.  Your ENTIRE world is the three
tables below (claim board, dependency table, anchor digest) — closed book.
You never order actions, choose actions, or spend money.  You produce exactly
one judgment: the prior likelihood of what a query will return before it is
run, as a grade in {high, mid, low} for every ticketed item.

Follow this protocol EXACTLY:
(i) enumerate the ticketed items: every ticketed dependency row
    (item id "CID=supported" / "CID=refuted") and every ticketed claim's
    direct resolution (item id "CID=direct");
(ii) anchor lookup — quote the relevant anchor digest (or board) field
    VERBATIM in the "citation" field; a fabricated citation is rejected;
(iii) set the default grade from the anchor mechanically (anchor clearly in
     a deciding zone and far from its edge -> high for the agreeing outcome,
     low for the contradicting one; near an edge or in a middle zone -> mid;
     no anchor -> mid);
(iv) clue scan — you may adjust a grade by AT MOST ONE STEP, and only by
     naming its clue in the "clue" field: a holiday flag, an in-case
     measurement diverging from history, a seasonal-settlement marker, or
     your own recent misses on similar judgments (see the agent ledger in the
     digest).  If no clue was found, set clue to null and declare
     "no_clue_found_anchor_followed": true;
(v) emit the JSON.
"""

SEAT2_SYSTEM = """\
You are Agent 2 (action selection) in a budget-constrained what-if analysis
of a cellular base-station outage.  You are given the winning target claim
plus runners-up, an action menu filtered by code, the anchor digest, and the
zone-edge constants.  Your ENTIRE world is this material — closed book.

Follow this protocol EXACTLY:
(i) enumerate the candidate actions cheapest-first — the cheapest resolving
    action is the incumbent;
(ii) predict an outcome bucket + grade for each candidate by placing the
     anchor against the bucket walls (zone edges given in the digest);
(iii) decisiveness accounting: effective cost = sticker price + the follow-up
     price forced by the predicted bucket, computed WORST-CASE (a predicted
     middle/ambiguous bucket forces its follow-up with certainty).  Choosing
     any non-cheapest action REQUIRES exhibiting this arithmetic in the
     "escalation" object; the code re-verifies the arithmetic — only the
     bucket predictions inside it belong to you;
(iv) firming option: if your own prediction grade is low because an anchor is
     suspect, you may instead buy a historical profile, flagged
     "judgment_firming": true — it will be scored on whether the relevant
     grade actually moved next round;
(v) emit the JSON with a contingency line for EVERY bucket in the chosen
    action's outcome space (a missing bucket is rejected), plus a verbatim
    "citation" from the provided tables.

Guardrail you must respect: a top-quartile (Q4) action requires grade=high
unless a prerequisite on the same claim was already resolved cheaply.  If you
target a runner-up instead of the leader, you MUST cite the enabling
dependency row id verbatim in "veto_justification".
"""


class LLMSeat1(Seat1):
    name = "llm1"

    def __init__(self, client: LLMClient, retries: int = 1):
        self.client = client
        self.retries = retries
        self.fallback = RuleSeat1AllMid()

    def prioritize(self, board, deps, digest) -> Seat1Output:
        tables = "\n\n".join([render_board(board), render_deps(deps),
                              render_digest(digest)])
        expected = {r.row_id() for r in deps}
        expected |= {f"{row['cid']}=direct" for row in board if row["ticket"]}
        user = (f"{tables}\n\nTicketed items requiring a grade "
                f"({len(expected)}): {sorted(expected)}\n\nEmit the JSON now.")
        reason = None
        for _ in range(1 + self.retries):
            prompt = user if reason is None else (
                f"{user}\n\nYOUR PREVIOUS RESPONSE WAS REJECTED: {reason}\n"
                f"Fix it and emit compliant JSON.")
            try:
                resp = self.client.complete_json(SEAT1_SYSTEM, prompt,
                                                 SEAT1_SCHEMA)
            except LLMError as e:
                reason = str(e)
                continue
            reason = validate_seat1(resp, expected, tables)
            if reason is None:
                grades = {it["item_id"]: {
                    "grade": it["grade"], "rationale": it["rationale"],
                    "citation": it["citation"], "clue": it.get("clue"),
                    "no_clue_found_anchor_followed":
                        it["no_clue_found_anchor_followed"]}
                    for it in resp["items"]}
                return Seat1Output(grades=grades, source="llm", raw=resp)
        out = self.fallback.prioritize(board, deps, digest)
        out.source = "llm"
        out.fallback_used = True
        return out


class LLMSeat2(Seat2):
    name = "llm2"

    def __init__(self, client: LLMClient, retries: int = 1):
        self.client = client
        self.retries = retries
        self.fallback = RuleSeat2Cheapest()

    def choose(self, candidates, menu, digest, constants, deps) -> Seat2Output:
        board = constants["board"]
        tables = "\n\n".join([render_board(board), render_deps(deps),
                              render_digest(digest), render_menu(menu)])
        user = (f"{tables}\n\nTarget claims (leader first, then runners-up): "
                f"{candidates}\nzone constants: {constants['zones']}\n"
                f"escalation_mode: {constants.get('escalation_mode')}\n")
        if constants.get("rejection"):
            user += (f"\nYOUR PREVIOUS CHOICE ({constants.get('rejected_aid')}) "
                     f"WAS REJECTED BY THE GUARDRAIL/CHECKS: "
                     f"{constants['rejection']}\nChoose differently.\n")
        user += "\nEmit the JSON now."
        reason = None
        for _ in range(1 + self.retries):
            prompt = user if reason is None else (
                f"{user}\n\nYOUR PREVIOUS RESPONSE WAS REJECTED: {reason}\n"
                f"Fix it and emit compliant JSON.")
            try:
                resp = self.client.complete_json(SEAT2_SYSTEM, prompt,
                                                 SEAT2_SCHEMA)
            except LLMError as e:
                reason = str(e)
                continue
            reason = validate_seat2(resp, menu, candidates, tables, deps)
            if reason is None:
                return Seat2Output(
                    action_aid=resp["chosen_aid"],
                    predicted_bucket=resp["predicted_bucket"],
                    grade=resp["grade"],
                    contingencies={c["bucket"]: c["line"]
                                   for c in resp["contingencies"]},
                    escalation=resp.get("escalation"),
                    judgment_firming=bool(resp.get("judgment_firming")),
                    veto_justification=resp.get("veto_justification"),
                    rationale=resp.get("rationale", ""),
                    source="llm", raw=resp)
        out = self.fallback.choose(candidates, menu, digest, constants, deps)
        out.source = "llm"
        out.fallback_used = True
        return out
