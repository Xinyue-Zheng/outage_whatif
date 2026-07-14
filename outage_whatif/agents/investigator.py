"""The investigator: ONE agent seat, a plain-JSON tool loop.

Ollama tool-calling is unreliable, so the loop is a JSON protocol on top of
``LLMClient``: every model response must be exactly one JSON object, either

    {"tool": "<name>", "args": {...}}      (runner executes, result appended)
    {"commit": {"action": "<committing action>", ...}}

Committing actions: purchase | register_object | dismiss | split |
drill_down | accept_default | declare_done — schema-validated here; the
spend gate then verifies purchases.  Protocol rules: at most
max_tool_calls_per_round tool calls; at least one notebook_write before a
commit is accepted; a malformed response gets ONE re-prompt with the
validator error, then the round is skipped with a logged incident (there is
no fallback seat).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..config import Config
from .llm import LLMClient, LLMError

# Ports Part V of the final design (the design document itself is not in
# this repository; this prompt is reconstructed from the migration brief —
# see PROJECT.md drift notes — and should be replaced verbatim when the
# document is available).
SYSTEM_PROMPT = """\
You are the investigator on a budget-constrained what-if analysis of a
cellular network outage.  A target site will be switched off during a
ticketed window; the question — assessed at one analysis hour — is whether
the neighboring sites can absorb the target's users.  You verify NECESSARY
conditions (coverage, capacity, robustness) as three-valued claims over
demand objects; you never predict how traffic would actually redistribute.

Your world each round is the BRIEFING plus whatever you read through the
tools.  Everything enumerable is deterministic code: adjudication,
arithmetic, pricing, the verdict, the flip test.  Exactly one judgment is
yours: the prior likelihood of what a query will return, stated as a
predicted outcome bucket with a confidence grade (high | mid | low).

PROTOCOL — every response must be EXACTLY ONE JSON object, either
  {"tool": "<name>", "args": {...}}
or
  {"commit": {"action": "<action>", ...}}
No prose outside the JSON.  Tools are read-only over the run state:
  get_object {id} | get_claim {cid} | list_claims {} | list_gaps {} |
  price {kind, params} | flip {cid} | outcome_space {kind} |
  residual_map {} | footprint {} | history_profile {site?} |
  run_adjudication_dry {} | notebook_read {} | notebook_write {text}
You may make a limited number of tool calls per round; then you must
commit.  At least one notebook_write must occur before a commit is
accepted — the notebook is your investigation log across rounds.

COMMITTING ACTIONS (one per round):
  {"commit": {"action": "purchase", "kind": "probe|densify|pm_hourly|
     pm_15min|target_kpi|profile", "target": "<claim_id or gap_id>",
     "params": {...}, "predicted_bucket": "<bucket>",
     "confidence": "high|mid|low", "citation": "<verbatim quote>",
     "rationale": "..."}}
     params by kind — probe: {"points": [[x, y], ...]} or {"object": "V1",
     "n": 6} or {"use_suggested_probes": true}; densify: {} (the target
     claim names the object); pm_hourly/pm_15min: {"entities": ["S2"]};
     target_kpi: {} (all target cells); profile: {"site": "S2",
     "profile_kind": "same_weekday|matched_hour|holiday_last_year"}.
  {"commit": {"action": "register_object", "x": ..., "y": ...,
     "radius_m": ..., "provenance": "agent|residual", "note": "..."}}
  {"commit": {"action": "dismiss", "object": "V3"}}
  {"commit": {"action": "split", "object": "V1"}}
  {"commit": {"action": "drill_down", "claim": "CAP:S2"}}
  {"commit": {"action": "accept_default", "item": "<claim or object>",
     "note": "..."}}
  {"commit": {"action": "declare_done", "rationale": "..."}}

RULES THE GATE ENFORCES on purchases (violations come back as one retry):
  the target must exist and be open; claim targets must hold a flip
  ticket; the predicted bucket must be in the kind's outcome space; the
  citation must appear VERBATIM in the briefing or this turn's tool
  outputs; price is computed by code and must fit the remaining budget AND
  your confidence cap (low: 2%, mid: 10%, high: 100% of the initial
  budget).  You never state prices yourself — use the price tool.

HOW AN ENGINEER USUALLY OPENS: first fund the demand ledger (target_kpi —
without T[c] nothing can be prioritized); read the residual_map to see
where served demand is unmapped; confirm or dismiss the biggest
hypothesized pins with a handful of probes; then work ticketed claims in
falling stake order — hourly PM on exit neighbors before 15-minute drill,
densify only claims whose interval genuinely straddles.  Spend small while
your own hit rate is unproven; escalate confidence only where the anchor
evidence you can cite is strong.  Write one notebook line per round: what
you believe, what you bought, what would change your mind.
"""

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "tool": {"type": ["string", "null"]},
        "args": {"type": ["object", "null"]},
        "commit": {"type": ["object", "null"]},
    },
}

_COMMIT_REQUIRED = {
    "purchase": ("kind", "target", "predicted_bucket", "confidence",
                 "citation"),
    "register_object": ("x", "y", "radius_m", "provenance"),
    "dismiss": ("object",),
    "split": ("object",),
    "drill_down": ("claim",),
    "accept_default": ("item",),
    "declare_done": (),
}


def validate_commit(commit) -> str | None:
    """Schema validation of a committing action (kind-specific field
    presence; deeper checks are the gate's job)."""
    if not isinstance(commit, dict):
        return "commit must be a JSON object"
    action = commit.get("action")
    if action not in _COMMIT_REQUIRED:
        return (f"unknown committing action {action!r}; one of "
                f"{sorted(_COMMIT_REQUIRED)}")
    missing = [f for f in _COMMIT_REQUIRED[action] if not commit.get(f)]
    if missing:
        return f"commit {action!r} is missing required fields: {missing}"
    if action == "purchase" and not isinstance(commit.get("params", {}), dict):
        return "purchase params must be an object"
    if action == "register_object" \
            and commit["provenance"] not in ("agent", "residual"):
        return "register_object provenance must be 'agent' or 'residual'"
    return None


@dataclass
class RoundOutcome:
    commit: dict | None                  # None -> round skipped
    shown_text: str                      # briefing + this turn's tool outputs
    tool_calls: list = field(default_factory=list)
    incidents: list = field(default_factory=list)
    notebook_written: bool = False


class Investigator:
    name = "investigator"

    def __init__(self, client: LLMClient, cfg: Config):
        self.client = client
        self.cfg = cfg

    def run_round(self, briefing: str, tools: dict,
                  rejection: str | None = None,
                  notebook_written: bool = False) -> RoundOutcome:
        """One round of the tool loop.  ``tools`` maps name -> callable(args)
        (read-only over state except notebook_write).  ``rejection`` is a
        gate denial being fed back for the single retry."""
        out = RoundOutcome(commit=None, shown_text=briefing,
                           notebook_written=notebook_written)
        user = briefing + "\n\nRespond with exactly one JSON object."
        if rejection:
            user += (f"\n\nYOUR PREVIOUS COMMIT WAS DENIED: {rejection}\n"
                     f"Submit a corrected response.")
        errors_used = 0
        tool_calls = 0

        for _ in range(self.cfg.max_tool_calls_per_round
                       + self.cfg.agent_retries + 2):
            try:
                resp = self.client.complete_json(SYSTEM_PROMPT, user,
                                                 RESPONSE_SCHEMA)
            except (LLMError, ValueError) as e:     # incl. non-JSON output
                resp, err = None, f"transport/JSON error: {e}"
            else:
                err = self._shape_error(resp)

            if err is None and resp.get("tool") is not None:
                name = resp["tool"]
                args = resp.get("args") or {}
                if name not in tools:
                    err = (f"unknown tool {name!r}; available: "
                           f"{sorted(tools)}")
                elif tool_calls >= self.cfg.max_tool_calls_per_round:
                    err = (f"tool budget exhausted "
                           f"({self.cfg.max_tool_calls_per_round} calls); "
                           f"you must commit")
                else:
                    tool_calls += 1
                    try:
                        result = tools[name](args)
                    except Exception as e:          # tool misuse is the
                        result = f"tool error: {e}"  # agent's information
                    text = json.dumps(result, default=str)
                    if len(text) > 4000:
                        text = text[:4000] + "...(truncated)"
                    out.tool_calls.append({"tool": name, "args": args,
                                           "result": text})
                    if name == "notebook_write":
                        out.notebook_written = True
                    block = f"\nTOOL {name} -> {text}\n"
                    out.shown_text += block
                    user += block + "Respond with exactly one JSON object."
                    continue

            if err is None:
                commit = resp["commit"]
                err = validate_commit(commit)
                if err is None and commit.get("action") != "declare_done" \
                        and not out.notebook_written:
                    err = ("protocol rule: at least one notebook_write must "
                           "occur before a commit is accepted")
                if err is None:
                    out.commit = commit
                    return out

            # malformed / protocol violation: one re-prompt, then skip
            out.incidents.append(err)
            errors_used += 1
            if errors_used > self.cfg.agent_retries:
                return out                          # round skipped, no seat swap
            user += (f"\nVALIDATOR ERROR: {err}\n"
                     f"Respond with exactly one corrected JSON object.")
        out.incidents.append("response loop exhausted without a commit")
        return out

    @staticmethod
    def _shape_error(resp) -> str | None:
        if not isinstance(resp, dict):
            return "response must be a JSON object"
        has_tool = resp.get("tool") is not None
        has_commit = resp.get("commit") is not None
        if has_tool == has_commit:
            return ("response must contain exactly one of 'tool' or "
                    "'commit'")
        return None
