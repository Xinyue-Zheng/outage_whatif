"""Seat interfaces and output types shared by LLM seats and rule baselines.

Exactly one judgment is delegated to the seats: the prior likelihood of
what a query will return before it is run.  Everything else — ordering,
arithmetic, adjudication — is code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

GRADES = ("high", "mid", "low")


@dataclass
class Seat1Output:
    """Agent 1 — claim prioritization.  One likelihood grade per ticketed
    dependency row (item id "CID=outcome") and per ticketed claim's direct
    resolution (item id "CID=direct").  No ordering, no action choice, no
    spending — the ordering is a theorem of these grades."""
    grades: dict = field(default_factory=dict)
    # item_id -> {"grade": g, "rationale": str,
    #             "no_clue_found_anchor_followed": bool}
    source: str = "rule"               # rule | llm
    fallback_used: bool = False
    raw: dict | None = None            # LLM raw response, for the run log


@dataclass
class Seat2Output:
    """Agent 2 — action selection among the leader + runners-up."""
    action_aid: str
    predicted_bucket: str
    grade: str
    contingencies: dict = field(default_factory=dict)   # bucket -> line
    escalation: dict | None = None
    # {"chosen_effective_cost": x, "incumbent_effective_cost": y,
    #  "incumbent_aid": aid, "predicted_incumbent_bucket": b}
    judgment_firming: bool = False
    veto_justification: str | None = None   # cites a dependency row id
    rationale: str = ""
    source: str = "rule"
    fallback_used: bool = False
    raw: dict | None = None


class Seat1:
    """Interface: prioritize(board, deps, digest) -> Seat1Output.
    board/deps/digest are the three code-produced tables — the seat's
    entire world (closed book)."""
    name = "seat1"

    def prioritize(self, board: list, deps: list, digest: dict) -> Seat1Output:
        raise NotImplementedError


class Seat2:
    """Interface: choose(candidates, menu, digest, constants) -> Seat2Output.
    candidates: target claim cids (leader first, then runners-up);
    menu: Actions filtered by code to those claims + dependency-licensed
    cross-modal actions."""
    name = "seat2"

    def choose(self, candidates: list, menu: list, digest: dict,
               constants: dict, deps: list) -> Seat2Output:
        raise NotImplementedError
