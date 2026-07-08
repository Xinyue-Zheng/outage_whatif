"""The round loop as a LangGraph StateGraph.

One CaseRunner round == one invocation of the compiled graph
(``CaseRunner.step()``); the run-level while-loop stays in
``CaseRunner.run()`` so a round remains the unit of stepping/testing.

    START -> advance -> adjudicate_lifecycle -> assess
        assess    -> expand_boundary -> END          (verdict blocked)
        assess    -> stop_check      -> END          (stop / idle round)
                                     -> build_tables -> seat1
        seat1     -> END                             (empty ordering: idle)
                  -> seat2
        seat2     -> END                             (no compliant action)
                  -> execute -> END

All state that survives between rounds lives on the CaseRunner; the graph
state carries only intra-round intermediates.  ``stop=True`` in the final
state means the run should stop after this round.
"""

from __future__ import annotations

import dataclasses
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ..agents.baselines import mechanical_contingencies, predict_bucket
from ..agents.seats import Seat2Output
from ..claims import run_lifecycle
from ..planning.menu import build_menu, cheapest_price_map
from ..verdict import compute_verdict, dependency_table, flip_all_tickets
from .tables import build_board, build_digest


class RoundState(TypedDict, total=False):
    rng: Any                    # this round's seeded generator
    view: Any                   # EvidenceView after adjudication
    menu: list                  # full action menu
    price_map: dict             # cid -> cheapest resolving price
    deps: list                  # dependency table rows
    affordable: list
    affordable_ticketed: list
    board: list                 # claim board (agents' world)
    digest: dict                # anchor digest (agents' world)
    out1: Any                   # Seat1Output
    candidates: list            # leader + runners-up cids
    menu2: list                 # menu filtered to the candidates
    out2: Any                   # Seat2Output (compliant)
    stop: bool                  # run should stop after this round
    goto: str                   # routing decision of the node just run


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
    """JSON-safe trace record of one node's decision (None = don't record).

    The raw data returned by each paid query is recorded separately by the
    runner's purchase hooks (node == "query"); the executed-action outcome
    is recorded by the execute node itself (node == "execute")."""
    if node in ("build_tables", "execute"):
        return None                        # tables are huge / traced in-node
    rec = {"round": runner.round_no, "node": node}
    if "stop" in update:
        rec["stop"], rec["stop_reason"] = update["stop"], runner.stop_reason
    if "goto" in update:
        rec["goto"] = update["goto"]
    if node == "adjudicate_lifecycle":
        rec["claim_states"] = {c.cid: c.state for c in runner.claims.all()}
    elif node == "assess":
        rec["verdict"] = (runner.verdict_history[-1]
                          if runner.verdict_history else None)
        rec["tickets"] = [c.cid for c in runner.claims.open() if c.ticket]
        rec["menu"] = [{"aid": a.aid, "kind": a.kind, "claim": a.claim_cid,
                        "price": a.price, "quartile": a.quartile,
                        "description": a.description}
                       for a in update.get("menu", [])]
        rec["deps"] = [{"row": r.row_id(), "lever": r.lever_cid,
                        "savings": r.savings}
                       for r in update.get("deps", [])]
    elif node == "stop_check":
        rec["n_affordable"] = len(update.get("affordable", []))
        rec["n_affordable_ticketed"] = len(update.get("affordable_ticketed",
                                                      []))
        rec["remaining_budget"] = runner.remaining
    elif node == "expand_boundary":
        rec["boundary_expansions"] = runner.boundary.expansions
    elif node == "seat1":
        out1 = update.get("out1")
        if out1 is not None:
            rec["source"] = out1.source
            rec["fallback_used"] = out1.fallback_used
            rec["grades"] = out1.grades
        rec["candidates"] = update.get("candidates")
    elif node == "seat2":
        out2 = update.get("out2")
        if out2 is not None:
            rec.update({"source": out2.source,
                        "fallback_used": out2.fallback_used,
                        "action_aid": out2.action_aid,
                        "predicted_bucket": out2.predicted_bucket,
                        "grade": out2.grade,
                        "judgment_firming": out2.judgment_firming,
                        "contingencies": out2.contingencies,
                        "rationale": out2.rationale})
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
        view = runner._rebuild()
        events = run_lifecycle(runner.claims, view, runner.subregions,
                               runner.raster, runner.topology.roster, cfg,
                               runner.round_no)
        for e in events:
            runner._log(e)
        if events:
            view = runner._rebuild()
        runner._record_widths()
        return {"view": view}

    def assess(state: RoundState) -> RoundState:
        """Menu, flip-test tickets, verdict, dependency table."""
        view = state["view"]
        menu = build_menu(runner.claims, view, runner.subregions,
                          runner.background, runner.raster, runner.boundary,
                          runner.provider, runner.spec.window, cfg,
                          state["rng"], runner.round_no,
                          set(runner.owned_profiles), runner.ledger.signatures)
        price_map = cheapest_price_map(menu)

        ctx = runner._verdict_ctx(view)
        states = runner.claims.states()
        open_cids = [c.cid for c in runner.claims.open()]
        tickets = flip_all_tickets(open_cids, states, ctx)
        for c in runner.claims.all():
            c.ticket = tickets.get(c.cid, False)
        verdict = compute_verdict(states, ctx)
        runner.verdict_history.append(verdict.key())
        deps = dependency_table(open_cids, states, ctx,
                                lambda cid: price_map.get(cid, 0.0))
        return {"menu": menu, "price_map": price_map, "deps": deps,
                "goto": "expand_boundary" if verdict.blocked else "stop_check"}

    def expand_boundary(state: RoundState) -> RoundState:
        """Blocked run: forced boundary expansion, no agents this round."""
        return {"stop": runner._handle_blocked(state["rng"])}

    def stop_check(state: RoundState) -> RoundState:
        ticketed_open = [c for c in runner.claims.open() if c.ticket]
        stable = (len(runner.verdict_history) >= cfg.stable_rounds_to_stop + 1
                  and len({runner.verdict_history[-i - 1]
                           for i in range(cfg.stable_rounds_to_stop + 1)}) == 1)
        if not ticketed_open:
            if stable:
                runner.stop_reason = ("all tickets resolved; verdict unchanged "
                                      f"for {cfg.stable_rounds_to_stop} rounds")
                return {"stop": True, "goto": END}
            runner._log("no ticketed claims; idle round (stability check)")
            runner.idle_rounds += 1
            if runner.idle_rounds > 4:
                runner.stop_reason = "no progress possible (idle-round limit)"
                return {"stop": True, "goto": END}
            return {"goto": END}
        affordable = [a for a in state["menu"] if a.price <= runner.remaining]
        affordable_ticketed = [a for a in affordable
                               if a.claim_cid in {c.cid for c in ticketed_open}
                               or (a.kind == "profile")]
        if not affordable:
            runner.stop_reason = "budget exhausted (no affordable action)"
            return {"stop": True, "goto": END}
        if not affordable_ticketed:
            runner.stop_reason = ("no remaining affordable action can flip "
                                  "anything")
            return {"stop": True, "goto": END}
        return {"affordable": affordable,
                "affordable_ticketed": affordable_ticketed,
                "goto": "build_tables"}

    def build_tables(state: RoundState) -> RoundState:
        """The agents' entire (closed-book) world."""
        view = state["view"]
        board = build_board(runner.claims, view, runner.subregions,
                            runner.background, state["price_map"], cfg)
        digest = build_digest(
            runner.claims, view, runner.subregions, runner.background,
            runner.pm, runner.owned_profiles,
            {**runner.spec.calendar_flags(cfg),
             "_hour_range": (runner.spec.window.start.hour,
                             runner.spec.window.end.hour)},
            runner._zones(), runner.agent_ledgers, runner.width_history,
            runner.round_no)
        return {"board": board, "digest": digest}

    def seat1(state: RoundState) -> RoundState:
        """Agent 1 grades (fuse-aware routing); ordering is a theorem."""
        board, deps, digest = state["board"], state["deps"], state["digest"]
        s1 = runner.base1 if runner.agent_ledgers["agent1"].consume_fuse() \
            else runner.seat1
        if s1 is not runner.seat1:
            runner._log("agent1 fuse active: routed to baseline this round")
        out1 = s1.prioritize(board, deps, digest)
        base1_out = (runner.base1.prioritize(board, deps, digest)
                     if out1.source == "llm" else None)

        # score the previous round's judgment-firming purchase, if any
        if runner.pending_firming is not None:
            aid, cid, old_grade = runner.pending_firming
            new_grade = out1.grades.get(f"{cid}=direct", {}).get("grade")
            runner.agent_ledgers["agent2"].score_firming(
                aid, new_grade is not None and new_grade != old_grade)
            runner.pending_firming = None

        for item_id, g in out1.grades.items():
            cid, kind = item_id.rsplit("=", 1)
            runner.agent_ledgers["agent1"].record_seat1(
                runner.round_no, item_id, cid, kind,
                g.get("grade", "mid") if isinstance(g, dict) else "mid")
        runner.last_seat1_grades = {k: (v.get("grade") if isinstance(v, dict)
                                        else None)
                                    for k, v in out1.grades.items()}

        ranked = runner._ordering(out1, board, deps, state["price_map"],
                                  state["affordable"])
        if not ranked:
            runner._log("ordering empty despite tickets; idle round")
            runner.idle_rounds += 1
            if runner.idle_rounds > 4:
                runner.stop_reason = "no progress possible (idle-round limit)"
                return {"stop": True, "goto": END}
            return {"goto": END}
        candidates = ranked[: 1 + cfg.runners_up]
        if base1_out is not None:
            base_ranked = runner._ordering(base1_out, board, deps,
                                           state["price_map"],
                                           state["affordable"])
            if base_ranked and ranked and base_ranked[0] != ranked[0]:
                runner.divergence_log.append({
                    "round": runner.round_no, "seat": "agent1",
                    "llm_choice": ranked[0],
                    "baseline_choice": base_ranked[0],
                    "rationale": (out1.grades.get(f"{ranked[0]}=direct", {})
                                  or {}).get("rationale", ""),
                    "grade": runner.last_seat1_grades.get(
                        f"{ranked[0]}=direct"),
                })
        return {"out1": out1, "candidates": candidates, "goto": "seat2"}

    def seat2(state: RoundState) -> RoundState:
        """Agent 2 action choice; guardrail + mechanical checks with one
        re-prompt, then rule fallback, then a cheapest-first sweep."""
        board, deps, digest = state["board"], state["deps"], state["digest"]
        candidates = state["candidates"]
        menu2 = [a for a in state["affordable"]
                 if a.claim_cid in candidates]
        if not menu2:
            menu2 = state["affordable_ticketed"]
        constants = {"board": board, "zones": runner._zones(),
                     "escalation_mode": cfg.escalation_mode}
        s2 = runner.base2 if runner.agent_ledgers["agent2"].consume_fuse() \
            else runner.seat2
        if s2 is not runner.seat2:
            runner._log("agent2 fuse active: routed to baseline this round")

        out2 = s2.choose(candidates, menu2, digest, constants, deps)
        rejection = runner._guardrail(out2, menu2) or \
            runner._mechanical_checks(out2, menu2, board, digest)
        if rejection:
            runner._log(f"agent2 rejected: {rejection}; re-prompting once")
            constants2 = {**constants, "rejection": rejection,
                          "rejected_aid": out2.action_aid}
            out2 = s2.choose(candidates, menu2, digest, constants2, deps)
            rejection = runner._guardrail(out2, menu2) or \
                runner._mechanical_checks(out2, menu2, board, digest)
            if rejection:
                runner._log(f"agent2 still non-compliant ({rejection}); "
                            f"routing this round to the fallback rule")
                out2 = runner.base2.choose(candidates, menu2, digest,
                                           constants, deps)
                out2.fallback_used = True
                rejection = runner._guardrail(out2, menu2) or \
                    runner._mechanical_checks(out2, menu2, board, digest)
                if rejection:
                    # scan the menu cheapest-first for ANY compliant action;
                    # if none exists, no compliant spend can flip anything
                    out2 = None
                    for a in sorted(menu2, key=lambda a: (a.price, a.aid)):
                        bucket, grade = predict_bucket(a, board, digest)
                        cand = Seat2Output(
                            action_aid=a.aid, predicted_bucket=bucket,
                            grade=grade,
                            contingencies=mechanical_contingencies(a),
                            rationale="fallback sweep", source="rule",
                            fallback_used=True)
                        if not (runner._guardrail(cand, menu2) or
                                runner._mechanical_checks(cand, menu2, board,
                                                          digest)):
                            out2 = cand
                            break
                    if out2 is None:
                        runner.stop_reason = ("no guardrail-compliant "
                                              "affordable action can flip "
                                              "anything")
                        return {"stop": True, "goto": END}
        if out2.source == "llm":
            b2 = runner.base2.choose(candidates, menu2, digest, constants,
                                     deps)
            if b2.action_aid != out2.action_aid:
                runner.divergence_log.append({
                    "round": runner.round_no, "seat": "agent2",
                    "llm_choice": out2.action_aid,
                    "baseline_choice": b2.action_aid,
                    "rationale": out2.rationale, "grade": out2.grade})
        return {"out2": out2, "menu2": menu2, "goto": "execute"}

    def execute(state: RoundState) -> RoundState:
        """Pay, update evidence, re-adjudicate, reconcile the ledgers."""
        out2 = state["out2"]
        action = next(a for a in state["menu2"] if a.aid == out2.action_aid)
        runner.agent_ledgers["agent2"].record_seat2(
            runner.round_no, action.aid, action.claim_cid,
            out2.predicted_bucket, out2.grade,
            out2.judgment_firming or action.kind == "profile")

        runner.idle_rounds = 0
        actual_bucket, view = runner._execute(action, out2)
        runner._log(f"executed {action.aid} ({action.description}) price="
                    f"{action.price}; predicted={out2.predicted_bucket} "
                    f"actual={actual_bucket}")
        runner.trace.append(json_safe({
            "round": runner.round_no, "node": "execute",
            "aid": action.aid, "kind": action.kind,
            "claim": action.claim_cid, "price": action.price,
            "description": action.description,
            "predicted_bucket": out2.predicted_bucket,
            "actual_bucket": actual_bucket,
            "claim_state_after": (runner.claims.get(action.claim_cid).state
                                  if action.claim_cid in runner.claims
                                  else None)}))

        if action.kind == "profile":
            runner.pending_firming = (
                action.aid, action.claim_cid,
                runner.last_seat1_grades.get(f"{action.claim_cid}=direct"))
        else:
            runner.agent_ledgers["agent2"].reconcile_seat2(action.aid,
                                                           actual_bucket)
        if action.claim_cid in runner.claims:
            new_state = runner.claims.get(action.claim_cid).state
            runner.agent_ledgers["agent1"].reconcile_seat1_on_execution(
                action.claim_cid, new_state)
        return {"view": view}

    # ------------------------------------------------------------- wiring
    def route(state: RoundState) -> str:
        return state["goto"]

    g = StateGraph(RoundState)
    g.add_node("advance", advance)
    g.add_node("adjudicate_lifecycle", adjudicate_lifecycle)
    g.add_node("assess", assess)
    g.add_node("expand_boundary", expand_boundary)
    g.add_node("stop_check", stop_check)
    g.add_node("build_tables", build_tables)
    g.add_node("seat1", seat1)
    g.add_node("seat2", seat2)
    g.add_node("execute", execute)

    g.add_edge(START, "advance")
    g.add_conditional_edges("advance", route, ["adjudicate_lifecycle", END])
    g.add_edge("adjudicate_lifecycle", "assess")
    g.add_conditional_edges("assess", route, ["expand_boundary", "stop_check"])
    g.add_edge("expand_boundary", END)
    g.add_conditional_edges("stop_check", route, ["build_tables", END])
    g.add_edge("build_tables", "seat1")
    g.add_conditional_edges("seat1", route, ["seat2", END])
    g.add_conditional_edges("seat2", route, ["execute", END])
    g.add_edge("execute", END)
    return g.compile()
