"""The case runner.

Each round: build the three tables -> stop check -> Agent 1 (grades; the
ordering is then a THEOREM of the grades, computed by code) -> Agent 2
(action choice with decisiveness accounting) -> guardrail -> mechanical
checks (duplicate / contradiction; the critic LLM is intentionally absent —
see MECHANICAL-CHECKS EXTENSION POINT below) -> execute ->
re-adjudicate -> lifecycle -> flip tests -> ledger reconciliation.

The round itself is a LangGraph StateGraph (graph.py); ``step()`` runs one
graph invocation.  This module keeps the cross-round state and the
deterministic helpers the graph nodes call.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..agents.baselines import RuleSeat1AllMid, RuleSeat2Cheapest
from ..agents.ledger import AgentLedger, PurchaseLedger
from ..claims import PMStore, adjudicate_all, initial_claims
from ..claims.evidence_view import build_view
from ..claims.model import (COVERAGE, INTEGRITY, REFUTED,
                            ROBUSTNESS, SUPPORTED, UNDECIDED, Claim)
from ..config import Config
from ..geometry.boundary import Boundary
from ..geometry.evidence import EvidenceGrid
from ..geometry.footprint import analyze_coverage_point
from ..geometry.raster import segment_raster
from ..planning.calibration import CalibrationTable
from ..planning.sampling import initial_settlement_points
from ..verdict import VerdictContext, compute_verdict
from .case import CaseSpec


@dataclass
class RunResult:
    case: str
    arm: str
    verdict_overall: str
    per_subregion: dict
    spent: float
    budget: float
    rounds: int
    stop_reason: str
    unverified_assumptions: list
    ledger_entries: list
    agent_summaries: dict
    divergence_log: list
    events: list
    report_md: str
    boundary_expansions: int = 0
    fuse_trips: dict = field(default_factory=dict)


class CaseRunner:
    def __init__(self, spec: CaseSpec, provider, seat1, seat2, cfg: Config,
                 calib: CalibrationTable | None = None,
                 run_dir: Path | None = None):
        self.spec = spec
        self.provider = provider
        self.seat1, self.seat2 = seat1, seat2
        self.base1, self.base2 = RuleSeat1AllMid(), RuleSeat2Cheapest()
        self.cfg = cfg
        self.support_edge = calib.support_edge if calib else None
        self.run_dir = run_dir

        self.topology = provider.topology()
        self.target = spec.target_site or getattr(provider, "world", None).target_site
        self.raster = provider.population_raster()
        self.boundary = Boundary.initial(self.topology.sites[self.target],
                                         list(self.topology.sites.values()), cfg)

        settlements, self.background = segment_raster(self.raster, cfg)
        # claims only for settlements inside the boundary or its ring
        self.subregions = {}
        self.deferred_settlements = {}
        for s in settlements:
            x, y = s.centroid
            if self.boundary.contains(x, y) or self.boundary.in_ring(x, y):
                self.subregions[s.sid] = s
            else:
                self.deferred_settlements[s.sid] = s

        self.claims = initial_claims(self.subregions, self.background, cfg)
        self.grid = EvidenceGrid(cell_m=cfg.evidence_cell_m)
        self.pm = PMStore()
        self.owned_profiles = {}
        self.ledger = PurchaseLedger()
        self.agent_ledgers = {
            "agent1": AgentLedger("agent1", cfg.fuse_consecutive_misses),
            "agent2": AgentLedger("agent2", cfg.fuse_consecutive_misses)}
        self.round_no = 0
        self.events: list[str] = []
        self.divergence_log: list[dict] = []
        self.verdict_history: list[tuple] = []
        self.width_history: dict[str, list] = {}
        self.pending_firming = None            # (aid, cid, grade_at_purchase)
        self.idle_rounds = 0
        self.last_seat1_grades: dict = {}
        self.unverified: list[str] = []
        self.stop_reason = ""
        self._round_graph = None               # compiled lazily (graph.py)
        self.trace: list[dict] = []            # per-node decisions + raw data

    # ---------------------------------------------------------- plumbing
    @property
    def remaining(self) -> float:
        return round(self.spec.budget - self.ledger.spent, 2)

    def _rng(self) -> np.random.Generator:
        return np.random.default_rng(self.spec.seed * 100_003 + self.round_no)

    def _log(self, msg: str) -> None:
        self.events.append(f"[R{self.round_no}] {msg}")

    def _add_coverage(self, results: list) -> None:
        for pc in results:
            self.grid.add(analyze_coverage_point(
                pc, self.target, self.topology.roster, self.cfg.tau_acc))

    def _trace_query(self, kind: str, aid: str, cid, purpose: str,
                     charged: float, data) -> None:
        """Record a paid query's raw result in the run trace (drawable)."""
        from .graph import json_safe
        self.trace.append(json_safe({
            "round": self.round_no, "node": "query", "kind": kind,
            "aid": aid, "claim": cid, "purpose": purpose, "price": charged,
            "data": data}))

    def _buy_coverage(self, points, purpose: str, cid=None, aid="") -> bool:
        price = self.provider.quote("coverage", n_points=len(points))
        if not points or price > self.remaining:
            return False
        data, charged = self.provider.query_coverage(points)
        self._add_coverage(data)
        self.ledger.record(self.round_no, aid or f"init:{purpose}", "coverage",
                           charged, purpose, cid)
        self._trace_query("coverage", aid or f"init:{purpose}", cid, purpose,
                          charged, data)
        return True

    # ---------------------------------------------------------- setup
    def initial_sampling(self) -> None:
        """Round 0: Track 1 (population order) then Track 2 (never zero)."""
        rng = self._rng()
        # reserve the Track-2 fuse first — it is never reduced to zero
        from ..planning.sampling import background_grid_points
        bg_pts = background_grid_points(self.boundary, self.cfg, rng)
        bg_price = self.provider.quote("coverage", n_points=len(bg_pts))

        for sub in sorted(self.subregions.values(), key=lambda s: -s.population):
            pts = initial_settlement_points(sub, self.raster, self.cfg, rng)
            price = self.provider.quote("coverage", n_points=len(pts))
            if price > self.remaining - bg_price:
                self._log(f"initial Track-1 sampling of {sub.sid} deferred "
                          f"(budget)")
                continue
            self._buy_coverage(pts, "Track-1 initial sampling",
                               cid=f"COV:{sub.sid}")
        while bg_pts and bg_price > self.remaining:
            bg_pts = bg_pts[: max(len(bg_pts) - 4, 4)]
            bg_price = self.provider.quote("coverage", n_points=len(bg_pts))
            if len(bg_pts) <= 4:
                break
        self._buy_coverage(bg_pts, "Track-2 fuse grid", cid="COV:BG")

    # ---------------------------------------------------------- per-round core
    def _rebuild(self):
        view = build_view(self.grid, self.subregions, self.background,
                          self.raster, self.boundary, self.cfg)
        adjudicate_all(self.claims, view, self.pm, self.support_edge, self.cfg)
        return view

    def _record_widths(self):
        for c in self.claims.by_type(COVERAGE):
            iv = c.detail.get("interval")
            if iv:
                self.width_history.setdefault(c.subject, []).append(
                    round(iv[1] - iv[0], 3))

    def _zones(self) -> dict:
        return {"support_edge": self.support_edge,
                "pi_hi": self.cfg.policy.pi_hi,
                "theta": self.cfg.policy.theta,
                "kappa": self.cfg.policy.kappa,
                "cap15_refute_frac": self.cfg.policy.cap15_refute_frac}

    def _populations(self) -> dict:
        pops = {sid: s.population for sid, s in self.subregions.items()}
        pops["BG"] = self.background.population
        return pops

    def _verdict_ctx(self, view):
        return VerdictContext.from_claims(self.claims, view,
                                          self._populations(),
                                          self.cfg.policy)

    def _handle_blocked(self, rng) -> bool:
        """Refuted integrity blocks everything until boundary expansion.
        The expansion + resampling is forced, deterministic code."""
        refuted = [c for c in self.claims.by_type(INTEGRITY)
                   if c.state == REFUTED]
        if not refuted:
            return False
        for c in refuted:
            sector = int(c.subject)
            self.boundary.expand_sector(sector, self.cfg.boundary_expand_factor)
            self._log(f"boundary expansion forced in sector {sector} "
                      f"(integrity refuted)")
            pts = self.boundary.ring_points(sector, self.cfg.integrity_min_cells + 1,
                                            rng)
            if not self._buy_coverage(pts, "boundary expansion resampling",
                                      cid=c.cid, aid=f"R{self.round_no}:expand:{sector}"):
                self._log("expansion resampling unaffordable — stopping")
                self.stop_reason = "budget exhausted during forced expansion"
                return True
        # settlements newly inside the boundary get claims + initial samples
        for sid in list(self.deferred_settlements):
            s = self.deferred_settlements[sid]
            x, y = s.centroid
            if self.boundary.contains(x, y) or self.boundary.in_ring(x, y):
                self.subregions[sid] = self.deferred_settlements.pop(sid)
                self.claims.add(Claim(cid=f"COV:{sid}", ctype=COVERAGE,
                                      subject=sid, born_round=self.round_no,
                                      remedy="sample this subregion's evidence cells"))
                self.claims.add(Claim(cid=f"ROB:{sid}", ctype=ROBUSTNESS,
                                      subject=sid, born_round=self.round_no,
                                      remedy="sample this subregion's evidence cells"))
                pts = initial_settlement_points(s, self.raster, self.cfg, rng)
                self._buy_coverage(pts, "Track-1 sampling (post-expansion)",
                                   cid=f"COV:{sid}")
                self._log(f"settlement {sid} entered the boundary; claims spawned")
        return False

    # ---------------------------------------------------------- ordering
    def _ordering(self, out1, board, deps, price_map, menu) -> list:
        """The ordering is a theorem of Agent 1's stated grades."""
        w = self.cfg.grade_weights
        med_price = (statistics.median(a.price for a in menu) if menu else 1.0)
        pops = self._populations()

        def grade_of(item_id, default="mid"):
            g = out1.grades.get(item_id, {})
            return g.get("grade", default) if isinstance(g, dict) else default

        scores = {}
        for row in board:
            if not row["ticket"]:
                continue
            cid = row["cid"]
            stake_proxy = (row["stake_pop"] / self.cfg.policy.P0) * med_price
            score = w[grade_of(f"{cid}=direct")] * stake_proxy
            for r in deps:
                if r.lever_cid == cid:
                    score += w[grade_of(r.row_id())] * r.savings
            price = price_map.get(cid) or med_price
            scores[cid] = score / max(price, 1e-9)
        ranked = sorted(scores, key=lambda c: (-scores[c],
                                               price_map.get(c) or 1e9, c))
        return ranked

    # ---------------------------------------------------------- checks
    def _prerequisite_resolved(self, action) -> bool:
        return any(e["claim"] == action.claim_cid for e in self.ledger.entries)

    def _guardrail(self, out2, menu) -> str | None:
        """Code guardrail, after Agent 2 only.  Returns rejection reason."""
        act = next((a for a in menu if a.aid == out2.action_aid), None)
        if act is None:
            return f"chosen action {out2.action_aid} is not on the filtered menu"
        if act.quartile == 4 and out2.grade != "high" \
                and not self._prerequisite_resolved(act):
            return ("top-quartile price requires a high-confidence grade "
                    "(or a cheaply resolved prerequisite); got "
                    f"grade={out2.grade}")
        return None

    def _mechanical_checks(self, out2, menu, board, digest) -> str | None:
        """Duplicate + contradiction lookups (table lookups, not LLM calls).

        MECHANICAL-CHECKS EXTENSION POINT: a critic LLM reviewing off-menu
        directed probes would slot in here.  There is NO critic in this
        version, and the off-menu directed-probe channel is CLOSED.
        """
        act = next((a for a in menu if a.aid == out2.action_aid), None)
        if act is None:
            return "unknown action"
        if act.signature() in self.ledger.signatures:
            return f"duplicate query: {act.signature()} already purchased"
        row = next((r for r in board if r["cid"] == act.claim_cid), None)
        zones = self._zones()
        b = out2.predicted_bucket
        if b not in act.buckets:
            return (f"predicted bucket {b!r} is not in the action's outcome "
                    f"space {act.buckets}")
        anchor = None
        if row and row["type"] == "capacity":
            anchor = row.get("hourly_mean")
            if anchor is None:
                anchor = digest["neighbors"].get(row["subject"], {}).get("anchor_mean")
        if act.kind == "pm_hourly" and anchor is not None:
            if b == "support_zone" and anchor >= zones["pi_hi"]:
                return (f"contradiction: predicts support_zone while held "
                        f"anchor {anchor} sits in the refute zone")
            if b == "refute_zone" and zones["support_edge"] is not None \
                    and anchor < zones["support_edge"] - 0.15:
                return (f"contradiction: predicts refute_zone while held "
                        f"anchor {anchor} sits deep in the support zone")
        if act.kind == "pm_15min" and b == "support" and anchor is not None \
                and anchor >= zones["pi_hi"]:
            return (f"contradiction: predicts support while held hourly mean "
                    f"{anchor} is at/above pi_hi")
        if act.kind in ("coverage_densify", "bg_sweep") and row:
            iv = row.get("interval")
            if iv:
                if b == "clears_theta" and iv[1] < zones["theta"]:
                    return ("contradiction: predicts clears_theta while the "
                            f"held interval {iv} lies entirely below theta")
                if b == "falls_below_theta" and iv[0] > zones["theta"]:
                    return ("contradiction: predicts falls_below_theta while "
                            f"the held interval {iv} lies entirely above theta")
        return None

    # ---------------------------------------------------------- execution
    def _execute(self, action, out2) -> str:
        """Execute the chosen action, pay, update evidence.  Returns the
        ACTUAL outcome bucket (reconciled immediately)."""
        purpose = ("judgment firming" if out2.judgment_firming or
                   action.kind == "profile" else f"resolve {action.claim_cid}")
        if action.kind in ("coverage_densify", "robustness_densify",
                           "bg_sweep", "ring_sample"):
            data, charged = self.provider.query_coverage(action.params["points"])
            self._add_coverage(data)
            self.ledger.record(self.round_no, action.aid, action.kind, charged,
                               purpose, action.claim_cid, action.signature())
            self._trace_query(action.kind, action.aid, action.claim_cid,
                              purpose, charged, data)
            if action.kind in ("coverage_densify", "bg_sweep"):
                if action.claim_cid in self.claims:
                    self.claims.get(action.claim_cid).densifications += 1
        elif action.kind in ("pm_hourly", "pm_15min"):
            from ..provider.interface import Window
            p = action.params
            data, charged = self.provider.query_pm(
                p["entities"], p["metric"], p["granularity"], self.spec.window)
            for ent, series in data.items():
                store = self.pm.hourly if p["granularity"] == "hourly" else self.pm.q15
                store[ent] = series.values()
            self.ledger.record(self.round_no, action.aid, action.kind, charged,
                               purpose, action.claim_cid, action.signature())
            self._trace_query(action.kind, action.aid, action.claim_cid,
                              purpose, charged, data)
        elif action.kind == "profile":
            p = action.params
            prof, charged = self.provider.buy_profile(p["site"], p["profile_kind"])
            self.owned_profiles[(p["site"], p["profile_kind"])] = prof
            self.ledger.record(self.round_no, action.aid, "profile", charged,
                               purpose, action.claim_cid, action.signature())
            self._trace_query("profile", action.aid, action.claim_cid,
                              purpose, charged, prof)
        else:
            raise ValueError(f"unknown action kind {action.kind}")

        # re-adjudicate and derive the actual outcome bucket
        anchor_before = None
        if action.kind == "profile":
            anchor_before = self.pm.hourly_mean(action.params["site"])
        view = self._rebuild()
        claim = (self.claims.get(action.claim_cid)
                 if action.claim_cid in self.claims else None)
        return self._actual_bucket(action, claim, anchor_before), view

    def _actual_bucket(self, action, claim, anchor_before) -> str:
        st = claim.state if claim else UNDECIDED
        if action.kind == "pm_hourly":
            return claim.detail.get("zone") or "middle_zone"
        if action.kind == "pm_15min":
            return "refute" if st == REFUTED else "support"
        if action.kind in ("coverage_densify", "bg_sweep"):
            return {SUPPORTED: "clears_theta", REFUTED: "falls_below_theta",
                    UNDECIDED: "still_straddling"}[st]
        if action.kind == "robustness_densify":
            return {SUPPORTED: "diverse", REFUTED: "concentrated",
                    UNDECIDED: "still_ambiguous"}[st]
        if action.kind == "ring_sample":
            return {SUPPORTED: "clean", REFUTED: "contaminated",
                    UNDECIDED: "still_undecided"}[st]
        if action.kind == "profile":
            prof = self.owned_profiles[(action.params["site"],
                                        action.params["profile_kind"])]
            h0, h1 = self.spec.window.start.hour, self.spec.window.end.hour
            wmean = (sum(prof.hourly_mean[h] for h in range(h0, h1))
                     / max(h1 - h0, 1))
            if anchor_before is None or abs(wmean - anchor_before) > 0.08:
                return "anchor_shifts"
            return "anchor_confirms"
        return "unknown"

    # ---------------------------------------------------------- round
    def step(self) -> bool:
        """One round == one invocation of the LangGraph round graph
        (built lazily in graph.py; nodes close over this runner).
        Streams node-by-node so every node's decision lands in the run
        trace.  Returns False when the run should stop."""
        if self._round_graph is None:
            from .graph import build_round_graph
            self._round_graph = build_round_graph(self)
        from .graph import serialize_update
        stop = False
        for chunk in self._round_graph.stream({}, stream_mode="updates"):
            for node, update in chunk.items():
                if not update:
                    continue
                stop = update.get("stop", stop)
                rec = serialize_update(self, node, update)
                if rec is not None:
                    self.trace.append(rec)
        return not stop

    # ---------------------------------------------------------- finish
    def _final_verdict(self):
        view = self._rebuild()
        ctx = self._verdict_ctx(view)
        states = self.claims.states()
        verdict = compute_verdict(states, ctx)
        exhausted = ("budget" in self.stop_reason
                     or "affordable" in self.stop_reason
                     or "no progress" in self.stop_reason)
        if not exhausted:
            return verdict, view
        # conservative defaults (direction: degrade) ONLY at exhaustion:
        # undecided subregion tiers become "degraded" — never a fabricated
        # hole — and each assumption is flagged unverified_assumption.
        from ..verdict.verdict import (DEGRADED, HOLE, OVERALL_DEGRADED,
                                       OVERALL_FULL, OVERALL_SEVERE,
                                       SubVerdict, UND, Verdict)
        per = {}
        for sid, sv in verdict.per_subregion.items():
            if sv.tier == UND:
                per[sid] = SubVerdict(DEGRADED, severe=False,
                                      bottleneck_type=sv.bottleneck_type,
                                      bottleneck_subject=sv.bottleneck_subject)
                self.unverified.append(
                    f"{sid}: tier undecided at stop "
                    f"({self.stop_reason}; open {sv.bottleneck_type} claim); "
                    f"conservatively reported as degraded")
            else:
                per[sid] = sv
        for c in self.claims.open():
            if c.ctype == INTEGRITY:
                self.unverified.append(
                    f"{c.cid}: boundary integrity in sector {c.subject} "
                    f"unverified at budget exhaustion")
        tiers = [v.tier for v in per.values()]
        if any(v.tier == HOLE and v.severe for v in per.values()):
            overall = OVERALL_SEVERE
        elif HOLE in tiers or DEGRADED in tiers:
            overall = OVERALL_DEGRADED
        else:
            overall = OVERALL_FULL
        return Verdict(overall, False, per), view

    def _buy_target_baseline(self) -> None:
        """On stop: purchase the target's own baseline RRC last (reporting)."""
        price = self.provider.quote("pm", granularity="hourly", n_entities=1,
                                    hours=self.spec.window.hours)
        if price <= self.remaining:
            data, charged = self.provider.query_pm(
                [self.target], "rrc_conn", "hourly", self.spec.window)
            self.ledger.record(self.round_no, "final:target_rrc", "pm_hourly",
                               charged, "target baseline RRC "
                               "(reporting/validation only)", None)
            self._trace_query("pm_hourly", "final:target_rrc", None,
                              "target baseline RRC", charged, data)
            self.target_rrc = data[self.target].values()
        else:
            self.target_rrc = None
            self._log("target baseline RRC unaffordable at stop")

    def run(self, arm: str = "rule/rule") -> RunResult:
        self.initial_sampling()
        while self.step():
            pass
        if not self.stop_reason:
            self.stop_reason = "stopped"
        self._buy_target_baseline()
        verdict, view = self._final_verdict()

        from .report import render_report
        result = RunResult(
            case=self.spec.name, arm=arm,
            verdict_overall=verdict.overall,
            per_subregion={sid: {"tier": sv.tier, "severe": sv.severe,
                                 "bottleneck": (sv.bottleneck_type,
                                                sv.bottleneck_subject)}
                           for sid, sv in verdict.per_subregion.items()},
            spent=self.ledger.spent, budget=self.spec.budget,
            rounds=self.round_no, stop_reason=self.stop_reason,
            unverified_assumptions=list(self.unverified),
            ledger_entries=list(self.ledger.entries),
            agent_summaries={k: v.summary(self.round_no)
                             for k, v in self.agent_ledgers.items()},
            divergence_log=list(self.divergence_log),
            events=list(self.events), report_md="",
            boundary_expansions=self.boundary.expansions,
            fuse_trips={k: v.fuse_trips for k, v in self.agent_ledgers.items()})
        result.report_md = render_report(self, verdict, result)
        if self.run_dir is not None:
            self.run_dir.mkdir(parents=True, exist_ok=True)
            (self.run_dir / "report.md").write_text(result.report_md)
            (self.run_dir / "ledger.json").write_text(
                json.dumps(self.ledger.entries, indent=2))
            (self.run_dir / "divergence.json").write_text(
                json.dumps(self.divergence_log, indent=2))
            (self.run_dir / "events.log").write_text("\n".join(self.events))
            (self.run_dir / "trace.jsonl").write_text(
                "\n".join(json.dumps(r, default=str) for r in self.trace))
            if self._round_graph is not None:
                (self.run_dir / "round_graph.mmd").write_text(
                    self._round_graph.get_graph().draw_mermaid())
        return result
