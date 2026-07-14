"""The round loop as a LangGraph StateGraph (investigator architecture).

One CaseRunner round == one invocation of the compiled graph
(``CaseRunner.step()``); the run-level while-loop stays in
``CaseRunner.run()`` so a round remains the unit of stepping/testing.

    START -> advance -> adjudicate_lifecycle -> assess -> stop_check
        stop_check   -> END                          (stop rules fired)
                     -> briefing -> investigator
        investigator -> END                          (round skipped)
                     -> gate
        gate         -> investigator                 (denied; single retry)
                     -> END                          (denied twice)
                     -> execute -> reconcile -> END

All state that survives between rounds lives on the CaseRunner; the graph
state carries only intra-round intermediates.  ``stop=True`` in the final
state means the run should stop after this round.
"""

from __future__ import annotations

import dataclasses
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ..claims import run_lifecycle
from ..verdict import compute_verdict, flip_all_tickets
from .briefing import render_briefing


class RoundState(TypedDict, total=False):
    rng: Any                    # this round's seeded generator
    view: Any                   # EvidenceView after adjudication
    gaps: list                  # audit gaps
    tickets: dict               # cid -> flip ticket
    briefing: str               # rendered briefing text
    outcome: Any                # investigator RoundOutcome
    request: Any                # resolved PurchaseRequest (purchases only)
    commit: dict                # the committed action
    denial: str                 # gate denial being retried
    retry_used: bool
    notebook_written: bool
    actual_bucket: str
    stop: bool
    goto: str


def json_safe(o):
    """Recursively convert a value into something json.dumps accepts."""
    if isinstance(o, dict):
        return {str(k): json_safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [json_safe(v) for v in o]
    if isinstance(o, bool) or o is None or isinstance(o, (str, int)):
        return o
    if isinstance(o, float):
        return round(o, 6)
    if dataclasses.is_dataclass(o):
        return json_safe(dataclasses.asdict(o))
    if hasattr(o, "item"):                 # numpy scalar
        return json_safe(o.item())
    return str(o)


def serialize_update(runner, node, update):
    """JSON-safe trace record of one node's decision (None = skip)."""
    rec = {"round": runner.round_no, "node": node}
    if "stop" in update:
        rec["stop"], rec["stop_reason"] = update["stop"], runner.stop_reason
    if "goto" in update:
        rec["goto"] = update["goto"]
    if node == "adjudicate_lifecycle":
        rec["claim_states"] = {c.cid: c.state for c in runner.claims.all()}
        rec["object_states"] = {o.id: o.state for o in runner.registry.all()}
    elif node == "assess":
        rec["verdict"] = (runner.verdict_history[-1]
                          if runner.verdict_history else None)
        rec["tickets"] = sorted(c for c, t in update.get("tickets", {}).items()
                                if t)
        rec["gaps"] = [g.line() for g in update.get("gaps", [])]
    elif node == "stop_check":
        rec["remaining_budget"] = runner.remaining
    elif node == "briefing":
        rec["briefing"] = update.get("briefing")
    elif node == "investigator":
        out = update.get("outcome")
        if out is not None:
            rec["tool_calls"] = out.tool_calls
            rec["commit"] = out.commit
            rec["incidents"] = out.incidents
        rec["retry"] = update.get("retry_used", False)
    elif node == "gate":
        rec["denial"] = update.get("denial")
        req = update.get("request")
        if req is not None:
            rec["approved"] = {"kind": req.kind, "target": req.target,
                               "price": req.price,
                               "predicted_bucket": req.predicted_bucket,
                               "confidence": req.confidence}
        elif update.get("commit") is not None and not update.get("denial"):
            rec["approved"] = {"action": update["commit"].get("action")}
    elif node == "execute":
        rec["commit"] = update.get("commit", {}).get("action") \
            if update.get("commit") else None
        req = update.get("request")
        if req is not None:
            rec.update({"aid": req.aid, "kind": req.kind,
                        "target": req.target, "price": req.price})
        rec["actual_bucket"] = update.get("actual_bucket")
    elif node == "reconcile":
        rec["claim_states"] = {c.cid: c.state for c in runner.claims.all()}
        rec["remaining_budget"] = runner.remaining
    return json_safe(rec)


def build_round_graph(runner):
    """Compile the one-round graph over a CaseRunner (nodes close over it)."""
    cfg = runner.cfg

    # ------------------------------------------------------------- nodes
    def advance(state: RoundState) -> RoundState:
        runner.round_no += 1
        if runner.round_no > cfg.max_rounds:
            runner.stop_reason = "max rounds safety stop"
            return {"stop": True, "goto": END}
        return {"rng": runner._rng(), "goto": "adjudicate_lifecycle"}

    def adjudicate_lifecycle(state: RoundState) -> RoundState:
        runner._refresh_confirmations()
        view = runner._rebuild()
        events = run_lifecycle(runner.claims, view, cfg, runner.round_no)
        for e in events:
            runner._log(e)
        if events:
            view = runner._rebuild()
        return {"view": view}

    def assess(state: RoundState) -> RoundState:
        """Flip tests, verdict, audit — no menu, no dependency table."""
        view = state["view"]
        ctx = runner._verdict_ctx(view)
        states = runner.claims.states()
        open_cids = [c.cid for c in runner.claims.open()]
        tickets = flip_all_tickets(open_cids, states, ctx)
        for c in runner.claims.all():
            c.ticket = tickets.get(c.cid, False)
        verdict = compute_verdict(states, ctx)
        runner.verdict_history.append(verdict.key())
        runner.residual_history.append(
            runner.book.residual_bound(runner.registry, runner.raster, cfg))
        gaps = runner._gaps(view)
        return {"tickets": tickets, "gaps": gaps, "goto": "stop_check"}

    def stop_check(state: RoundState) -> RoundState:
        from .briefing import cheapest_remedy
        ticketed_open = [c for c in runner.claims.open() if c.ticket]
        gaps = state["gaps"]
        stable = (len(runner.verdict_history) >= cfg.stable_rounds_to_stop + 1
                  and len({runner.verdict_history[-i - 1]
                           for i in range(cfg.stable_rounds_to_stop + 1)}) == 1)
        if runner.stop_reason.startswith("declared done"):
            return {"stop": True, "goto": END}
        if runner.idle_rounds > 4:
            runner.stop_reason = "no progress possible (idle-round limit)"
            return {"stop": True, "goto": END}
        if not ticketed_open:
            if not gaps:
                runner.stop_reason = ("no ticketed claim and no "
                                      "verdict-blocking gap")
                return {"stop": True, "goto": END}
            if stable and all(g.kind == "object_open_claims"
                              for g in gaps):
                runner.stop_reason = ("all tickets resolved; verdict stable "
                                      f"for {cfg.stable_rounds_to_stop} rounds")
                return {"stop": True, "goto": END}
        # budget: can anything still be bought?
        k = cfg.policy.comparable_days_k
        quotes = [runner.provider.quote("coverage", n_points=1)]
        for c in ticketed_open:
            rem = cheapest_remedy(c, state["view"], runner.subregions(),
                                  runner.provider, cfg, k)
            if rem:
                quotes.append(rem[1])
        if runner.remaining < min(quotes):
            runner.stop_reason = ("budget below every open item's cheapest "
                                  "remedy")
            return {"stop": True, "goto": END}
        return {"goto": "briefing"}

    def briefing(state: RoundState) -> RoundState:
        text = render_briefing(runner, state["gaps"], state["view"])
        return {"briefing": text}

    def investigator(state: RoundState) -> RoundState:
        tools = runner.build_tools(state["view"], state["gaps"],
                                   state["tickets"])
        outcome = runner.investigator.run_round(
            state["briefing"], tools,
            rejection=state.get("denial"),
            notebook_written=state.get("notebook_written", False))
        for inc in outcome.incidents:
            runner.incidents.append({"round": runner.round_no,
                                     "incident": inc})
        if outcome.commit is None:
            runner.idle_rounds += 1
            runner._log("round skipped: investigator produced no valid "
                        "commit (incidents logged; no fallback seat)")
            return {"outcome": outcome, "goto": END}
        return {"outcome": outcome, "commit": outcome.commit,
                "notebook_written": outcome.notebook_written, "goto": "gate"}

    def gate_node(state: RoundState) -> RoundState:
        commit = state["commit"]
        req, denial = runner.check_commit(
            commit, state["gaps"], state["tickets"],
            state["outcome"].shown_text)
        if denial is None:
            return {"request": req, "denial": None, "goto": "execute",
                    "commit": commit}
        runner._log(f"gate denied {commit.get('action')}: {denial}")
        if state.get("retry_used"):
            runner.idle_rounds += 1
            runner.incidents.append({"round": runner.round_no,
                                     "incident": f"gate denied twice: "
                                                 f"{denial}"})
            runner._log("round skipped: gate denied the retry too")
            return {"denial": denial, "goto": END}
        return {"denial": denial, "retry_used": True, "goto": "investigator"}

    def execute(state: RoundState) -> RoundState:
        runner.idle_rounds = 0
        commit, req = state["commit"], state.get("request")
        if commit["action"] == "purchase":
            runner.agent_ledger.record_prediction(
                runner.round_no, req.aid, req.target,
                req.predicted_bucket, req.confidence)
            actual = runner._execute_purchase(req)
            return {"actual_bucket": actual, "goto": "reconcile"}
        runner._execute_commit(commit)
        stop = commit["action"] == "declare_done"
        return {"actual_bucket": None, "stop": stop, "goto": "reconcile"}

    def reconcile(state: RoundState) -> RoundState:
        req, actual = state.get("request"), state.get("actual_bucket")
        if req is not None and actual is not None:
            runner.agent_ledger.reconcile(req.aid, actual)
            runner._log(f"executed {req.aid} price={req.price}; "
                        f"predicted={req.predicted_bucket} actual={actual}")
        return {"stop": state.get("stop", False)}

    # ------------------------------------------------------------- wiring
    def route(state: RoundState) -> str:
        return state["goto"]

    g = StateGraph(RoundState)
    g.add_node("advance", advance)
    g.add_node("adjudicate_lifecycle", adjudicate_lifecycle)
    g.add_node("assess", assess)
    g.add_node("stop_check", stop_check)
    g.add_node("briefing", briefing)
    g.add_node("investigator", investigator)
    g.add_node("gate", gate_node)
    g.add_node("execute", execute)
    g.add_node("reconcile", reconcile)

    g.add_edge(START, "advance")
    g.add_conditional_edges("advance", route, ["adjudicate_lifecycle", END])
    g.add_edge("adjudicate_lifecycle", "assess")
    g.add_edge("assess", "stop_check")
    g.add_conditional_edges("stop_check", route, ["briefing", END])
    g.add_edge("briefing", "investigator")
    g.add_conditional_edges("investigator", route, ["gate", END])
    g.add_conditional_edges("gate", route, ["execute", "investigator", END])
    g.add_edge("execute", "reconcile")
    g.add_edge("reconcile", END)
    return g.compile()
