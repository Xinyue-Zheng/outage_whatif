"""The case runner (investigator architecture).

Cross-round state lives here: the object registry, the cell localization
book, claims, evidence, ledgers, notebook.  One round = one invocation of
the LangGraph round graph (graph.py):

    advance -> adjudicate_lifecycle -> assess -> stop_check -> briefing
        -> investigator (tool loop) -> gate -> execute -> reconcile

There is no initial sampling phase: the round-zero audit (demand ledger
absent, objects hypothesized) is what makes exploration fundable, and the
~8 suggested random probes are a purchase the agent may make — never
auto-executed.
"""

from __future__ import annotations

import copy
import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..agents.investigator import Investigator
from ..agents.ledger import AgentLedger, PurchaseLedger
from ..claims import (PMStore, adjudicate_all, build_view, open_claims_for,
                      run_lifecycle)
from ..claims.lifecycle import _pass_fail_clustered, _split_subregion
from ..claims.model import (CAPACITY, REFUTED, SUPPORTED, UNDECIDED, Claim,
                            ClaimSet)
from ..config import Config
from ..demand import CellLocalizationBook, build_candidates, footprint_hull
from ..demand.objects import ADJUDICATED, CONFIRMED, DISMISSED, DemandObject
from ..geometry.evidence import EvidenceGrid
from ..geometry.footprint import analyze_coverage_point
from ..planning.calibration import CalibrationTable
from ..planning.comparable import matched_hour_windows
from ..planning.sampling import densify_cells, object_points, random_probe_points
from ..verdict import VerdictContext, compute_verdict, flip_all_tickets
from ..verdict.verdict import (DEGRADED, HOLE, OVERALL_DEGRADED, OVERALL_FULL,
                               OVERALL_SEVERE, OVERALL_UND, SEVERE_NO,
                               SEVERE_UND, SubVerdict, UND, Verdict)
from .audit import audit
from .case import CaseSpec
from .gate import PurchaseRequest, outcome_space, price_request


@dataclass
class RunResult:
    case: str
    verdict_overall: str
    per_object: dict
    spent: float
    budget: float
    rounds: int
    stop_reason: str
    unverified_assumptions: list
    ledger_entries: list
    agent_summary: dict
    incidents: list
    events: list
    notebook: list
    report_md: str = ""


class CaseRunner:
    def __init__(self, spec: CaseSpec, provider, investigator: Investigator,
                 cfg: Config, calib: CalibrationTable | None = None,
                 run_dir: Path | None = None):
        self.spec = spec
        self.provider = provider
        self.investigator = investigator
        self.cfg = cfg
        self.support_edge = calib.support_edge if calib else None
        self.run_dir = run_dir

        # per-hour semantics: validate / default-select the analysis hour
        # (an invalid explicit hour rejects the case here) and precompute
        # the k matched one-hour windows for capacity evidence
        self.analysis_hour = spec.resolve_analysis_hour(cfg)
        self.matched_windows = matched_hour_windows(
            spec.window, self.analysis_hour, cfg)

        self.topology = provider.topology()
        self.target = spec.target_site or provider.world.target_site
        self.raster = provider.population_raster()

        # demand layer
        self.registry = build_candidates(self.topology, self.target,
                                         self.raster, cfg)
        target_cells = sorted(c for c, s in self.topology.roster.items()
                              if s == self.target)
        self.book = CellLocalizationBook(
            self.target, self.topology.sites[self.target], target_cells)
        self.probes = random_probe_points(
            self.topology.sites[self.target], self.topology.sites, cfg,
            np.random.default_rng(spec.seed * 7919))
        self.residual_investigated = False

        # evidence + claims
        self.claims = ClaimSet()
        self.grid = EvidenceGrid(cell_m=cfg.evidence_cell_m)
        self.pm = PMStore()
        self.owned_profiles: dict = {}
        self.all_points: list = []           # every purchased PointObs

        # ledgers + agent bookkeeping
        self.ledger = PurchaseLedger()
        self.agent_ledger = AgentLedger("investigator")
        self.notebook: list[str] = []
        self.incidents: list = []
        self.accepted_defaults: list = []

        # loop bookkeeping
        self.round_no = 0
        self.idle_rounds = 0                 # consecutive rounds w/o execution
        self.events: list[str] = []
        self.verdict_history: list[tuple] = []
        self.residual_history: list = []
        self.unverified: list[str] = []
        self.stop_reason = ""
        self.trace: list[dict] = []
        self._round_graph = None

    # ---------------------------------------------------------- plumbing
    @property
    def remaining(self) -> float:
        return round(self.spec.budget - self.ledger.spent, 2)

    def _rng(self) -> np.random.Generator:
        return np.random.default_rng(self.spec.seed * 100_003 + self.round_no)

    def _log(self, msg: str) -> None:
        self.events.append(f"[R{self.round_no}] {msg}")

    def subregions(self) -> dict:
        """Live area geometries of the objects under claims."""
        return {o.id: o.pixels_or_geom for o in self.registry.all()
                if o.state in (CONFIRMED, ADJUDICATED)}

    def _trace_query(self, kind: str, aid: str, cid, purpose: str,
                     charged: float, data) -> None:
        from .graph import json_safe
        self.trace.append(json_safe({
            "round": self.round_no, "node": "query", "kind": kind,
            "aid": aid, "target": cid, "purpose": purpose, "price": charged,
            "data": data}))

    # ---------------------------------------------------------- evidence
    def _add_coverage(self, results: list) -> list:
        """Feed purchased coverage points into the grid, the localization
        book, and object confirmation.  Returns the new PointObs."""
        new_obs = []
        for pc in results:
            obs = analyze_coverage_point(pc, self.target,
                                         self.topology.roster,
                                         self.cfg.tau_acc)
            self.grid.add(obs)
            new_obs.append(obs)
            self.book.add_point(pc.x, pc.y, pc.serving[0])
        self.all_points.extend(new_obs)
        self._refresh_confirmations()
        return new_obs

    def _refresh_confirmations(self) -> None:
        newly = self.registry.refresh_confirmations(self.all_points,
                                                    self.raster)
        for obj in newly:
            made = open_claims_for(obj.id, self.claims, self.round_no)
            obj.claim_ids = [c.cid for c in made]
            self._log(f"object {obj.id} confirmed (target visible inside); "
                      f"claims opened: {', '.join(c.cid for c in made)}")

    def _rebuild(self):
        view = build_view(self.grid, self.subregions(), self.cfg, self.raster)
        adjudicate_all(self.claims, view, self.pm, self.support_edge, self.cfg)
        self.registry.mark_adjudicated(self.claims)
        return view

    # ---------------------------------------------------------- verdict
    def _populations(self) -> dict:
        return {o.id: o.population for o in self.registry.all()
                if o.state in (CONFIRMED, ADJUDICATED)}

    def _severity_map(self) -> dict:
        objs = [o for o in self.registry.all()
                if o.state in (CONFIRMED, ADJUDICATED)]
        intact = {o.id for o in objs
                  if f"COV:{o.id}" in self.claims
                  and self.claims.get(f"COV:{o.id}").state != REFUTED}
        return {o.id: self.book.hole_severity(o.id, intact - {o.id},
                                              self.registry, self.raster,
                                              self.cfg)
                for o in objs}

    def _verdict_ctx(self, view) -> VerdictContext:
        rb = self.book.residual_bound(self.registry, self.raster, self.cfg)
        return VerdictContext.from_claims(
            self.claims, view, self._populations(), self.cfg.policy,
            hole_severity=self._severity_map(),
            residual_bound=rb if rb is not None else 1.0,
            residual_ok=(rb is not None
                         and rb <= self.cfg.policy.rho_residual))

    def _gaps(self, view=None) -> list:
        return audit(self.book, self.registry, self.claims, self.raster,
                     self.cfg, probes=self.probes,
                     residual_investigated=self.residual_investigated)

    # ---------------------------------------------------------- tools
    def build_tools(self, view, gaps, tickets) -> dict:
        """The investigator's read-only tools (notebook_write excepted)."""
        cfg, book, registry, raster = (self.cfg, self.book, self.registry,
                                       self.raster)

        def get_object(args):
            oid = args.get("id") or args.get("object")
            if oid not in registry:
                return f"no object {oid!r}"
            o = registry.get(oid)
            return {"id": o.id, "state": o.state, "provenance": o.provenance,
                    "note": o.provenance_note,
                    "population": round(o.population, 1),
                    "centroid": [round(v, 1) for v in o.centroid],
                    "n_evidence_cells": len(o.evidence_cells(
                        raster, cfg.evidence_cell_m)),
                    "claims": list(o.claim_ids),
                    "importance_bound": book.importance_bound(
                        o.id, registry, raster, cfg)}

        def get_claim(args):
            cid = args.get("cid") or args.get("claim")
            if cid not in self.claims:
                return f"no claim {cid!r}"
            c = self.claims.get(cid)
            return {"cid": c.cid, "type": c.ctype, "subject": c.subject,
                    "state": c.state, "ticket": bool(c.ticket),
                    "remedy": c.remedy, "detail": c.detail,
                    "children": list(c.children)}

        def list_claims(args):
            return [{"cid": c.cid, "type": c.ctype, "state": c.state,
                     "ticket": bool(c.ticket)}
                    for c in sorted(self.claims.alive(), key=lambda c: c.cid)]

        def price(args):
            try:
                req = self._resolve_purchase(
                    {"kind": args.get("kind"),
                     "target": args.get("target", ""),
                     "params": args.get("params") or {},
                     "predicted_bucket": "", "confidence": "mid",
                     "citation": ""})
            except Exception as e:
                return f"cannot price: {e}"
            return {"kind": req.kind, "price": req.price,
                    "resolved_params": {k: (f"{len(v)} points"
                                            if k == "points" else v)
                                        for k, v in req.params.items()}}

        tools = {
            "get_object": get_object,
            "get_claim": get_claim,
            "list_claims": list_claims,
            "list_gaps": lambda a: [g.line() for g in gaps],
            "price": price,
            "flip": lambda a: {"cid": a.get("cid"),
                               "ticket": bool(tickets.get(a.get("cid")))},
            "outcome_space": lambda a: outcome_space(a.get("kind", "")),
            "residual_map": lambda a: book.residual_map(registry, raster, cfg),
            "footprint": lambda a: {"hull": footprint_hull(
                [(p.x, p.y) for p in self.all_points if p.in_footprint])},
            "history_profile": self._tool_history_profile,
            "run_adjudication_dry": lambda a: self._tool_dry_run(view),
            "notebook_read": lambda a: self.notebook[-10:] or ["(empty)"],
            "notebook_write": self._tool_notebook_write,
        }
        return tools

    def _tool_history_profile(self, args):
        site = args.get("site")
        owned = {f"{s}/{kind}": {
                     "at_analysis_hour": prof.hourly_mean[self.analysis_hour],
                     "hourly_mean": prof.hourly_mean}
                 for (s, kind), prof in self.owned_profiles.items()
                 if site in (None, s)}
        kinds = ["same_weekday", "matched_hour"]
        if self.spec.calendar_flags(self.cfg)["holiday"]:
            kinds.append("holiday_last_year")
        quotes = {k: self.provider.quote("profile", kind=k) for k in kinds}
        return {"owned": owned or "none purchased",
                "purchasable_kinds_with_quotes": quotes}

    def _tool_dry_run(self, view):
        shadow = copy.deepcopy(self.claims)
        adjudicate_all(shadow, view, self.pm, self.support_edge, self.cfg)
        states = {c.cid: c.state for c in shadow.alive()}
        v = compute_verdict(states, self._verdict_ctx(view))
        return {"states": states, "verdict": v.overall,
                "per_object": {sid: sv.tier
                               for sid, sv in v.per_subregion.items()}}

    def _tool_notebook_write(self, args):
        text = str(args.get("text", "")).strip()
        if not text:
            return "notebook_write needs non-empty 'text'"
        self.notebook.append(f"[R{self.round_no}] {text}")
        return "ok"

    # ---------------------------------------------------------- purchases
    def _resolve_purchase(self, commit: dict) -> PurchaseRequest:
        """Resolve an agent purchase into concrete, priced params.  Point
        selection is deterministic per (seed, round), so the price tool and
        the execution see identical requests."""
        kind = commit["kind"]
        target = commit.get("target", "")
        params = dict(commit.get("params") or {})
        rng = self._rng()
        k = self.cfg.policy.comparable_days_k

        if kind == "probe":
            if params.get("use_suggested_probes"):
                params["points"] = list(self.probes)
            elif "object" in params:
                oid = params["object"]
                if oid not in self.registry:
                    raise ValueError(f"no object {oid!r} to probe")
                sub = self.registry.get(oid).pixels_or_geom
                n = int(params.get("n", self.cfg.dismiss_min_units))
                params["points"] = object_points(sub, self.raster, self.cfg,
                                                 rng, k=n)
            else:
                pts = params.get("points")
                if not pts or not isinstance(pts, list):
                    raise ValueError("probe needs points, an object, or "
                                     "use_suggested_probes")
                params["points"] = [(float(x), float(y)) for x, y in pts]
        elif kind == "densify":
            if target not in self.claims:
                raise ValueError(f"densify target {target!r} is not a claim")
            c = self.claims.get(target)
            sub = self.subregions().get(c.subject)
            if sub is None:
                raise ValueError(f"claim {target} has no area object")
            view = build_view(self.grid, self.subregions(), self.cfg,
                              self.raster)
            unsampled = view.unsampled_cells.get(c.subject, [])
            pts = densify_cells(sub, self.raster, unsampled, self.cfg, rng)
            if not pts:
                raise ValueError(f"no unsampled evidence cells left in "
                                 f"{c.subject}")
            params["points"] = pts
        elif kind in ("pm_hourly", "pm_15min"):
            ents = params.get("entities")
            if not ents:
                if target in self.claims:
                    ents = [self.claims.get(target).subject]
                else:
                    raise ValueError("pm purchase needs entities")
            params["entities"] = list(ents)
        elif kind == "target_kpi":
            params["entities"] = list(self.book.cells)
        elif kind == "profile":
            if "site" not in params or "profile_kind" not in params:
                raise ValueError("profile needs site and profile_kind")
        else:
            raise ValueError(f"unknown purchase kind {kind!r}")

        req = PurchaseRequest(
            kind=kind, target=target, params=params,
            predicted_bucket=commit.get("predicted_bucket", ""),
            confidence=commit.get("confidence", ""),
            citation=commit.get("citation", ""),
            rationale=commit.get("rationale", ""))
        req.price = price_request(req, self.provider, self.cfg, k)
        req.aid = f"R{self.round_no}:{kind}:{target or 'exploration'}"
        return req

    def _execute_purchase(self, req: PurchaseRequest) -> str:
        """Pay, store data, re-adjudicate.  Returns the ACTUAL bucket."""
        purpose = f"resolve {req.target}" if req.target else "exploration"
        if req.kind in ("probe", "densify"):
            data, charged = self.provider.query_coverage(req.params["points"])
            new_obs = self._add_coverage(data)
            if req.kind == "densify" and req.target in self.claims:
                self.claims.get(req.target).densifications += 1
            self._last_probe_obs = new_obs
        elif req.kind in ("pm_hourly", "pm_15min"):
            gran = "hourly" if req.kind == "pm_hourly" else "15min"
            data, charged = self.provider.query_pm_matched(
                req.params["entities"], "prb_util", gran,
                self.matched_windows)
            store = self.pm.hourly if gran == "hourly" else self.pm.q15
            for ent, series in data.items():
                store[ent] = series.values()
        elif req.kind == "target_kpi":
            data, charged = self.provider.query_pm_matched(
                req.params["entities"], "rrc_conn", "hourly",
                self.matched_windows)
            self._new_traffic = {}
            for ent, series in data.items():
                vals = series.values()
                t = round(sum(vals) / max(len(vals), 1), 1)
                self.book.set_traffic(ent, t)
                self._new_traffic[ent] = t
        elif req.kind == "profile":
            p = req.params
            self._anchor_before = self.pm.hourly_mean(p["site"])
            data, charged = self.provider.buy_profile(
                p["site"], p["profile_kind"],
                hour=(self.analysis_hour
                      if p["profile_kind"] == "matched_hour" else None))
            self.owned_profiles[(p["site"], p["profile_kind"])] = data
        else:
            raise ValueError(req.kind)

        if req.target == "GAP:residual" or (
                req.kind == "probe" and req.target.startswith("GAP:")):
            self.residual_investigated = True
        self.ledger.record(self.round_no, req.aid, req.kind, charged,
                           purpose, req.target)
        self._trace_query(req.kind, req.aid, req.target, purpose, charged,
                          data)
        self._rebuild()
        return self._actual_bucket(req)

    def _actual_bucket(self, req: PurchaseRequest) -> str:
        if req.kind == "probe":
            obs = getattr(self, "_last_probe_obs", [])
            hits = sum(o.in_footprint for o in obs)
            if hits == len(obs) and obs:
                return "target_present"
            if hits == 0:
                return "target_absent"
            return "mixed"
        claim = (self.claims.get(req.target)
                 if req.target in self.claims else None)
        st = claim.state if claim else UNDECIDED
        if req.kind == "densify":
            if st == UNDECIDED:
                return "still_straddling"
            if claim.ctype == "robustness":
                # supported = concentration interval below kappa
                return "interval_below" if st == SUPPORTED else "interval_above"
            return "interval_above" if st == SUPPORTED else "interval_below"
        if req.kind == "pm_hourly":
            return (claim.detail.get("zone") or "middle_zone") if claim \
                else "middle_zone"
        if req.kind == "pm_15min":
            return "refute" if st == REFUTED else "support"
        if req.kind == "target_kpi":
            heavy = any(t >= self.cfg.policy.T_material
                        for t in getattr(self, "_new_traffic", {}).values())
            return "heavy_cells_present" if heavy else "all_cells_light"
        if req.kind == "profile":
            prof = self.owned_profiles[(req.params["site"],
                                        req.params["profile_kind"])]
            wmean = prof.hourly_mean[self.analysis_hour]
            before = getattr(self, "_anchor_before", None)
            if before is None or abs(wmean - before) > 0.08:
                return "anchor_shifts"
            return "anchor_confirms"
        return "unknown"

    # ---------------------------------------------------------- free commits
    def _execute_commit(self, commit: dict) -> None:
        """Non-purchase committing actions (gate-approved)."""
        action = commit["action"]
        if action == "register_object":
            obj = self.registry.register(
                float(commit["x"]), float(commit["y"]),
                float(commit["radius_m"]), commit["provenance"],
                commit.get("note"), self.raster)
            if commit["provenance"] == "residual":
                self.residual_investigated = True
            self._log(f"object {obj.id} registered "
                      f"(provenance={commit['provenance']}, "
                      f"note={commit.get('note')!r})")
            self._refresh_confirmations()
        elif action == "dismiss":
            oid = commit["object"]
            self.registry.dismiss(oid)
            for cid in self.registry.get(oid).claim_ids:
                if cid in self.claims:
                    self.claims.get(cid).alive = False
            self._log(f"object {oid} dismissed (instrument-verified)")
        elif action == "split":
            self._execute_split(commit["object"])
        elif action == "drill_down":
            self._execute_drilldown(commit["claim"])
        elif action == "accept_default":
            item, note = commit["item"], commit.get("note", "")
            self.accepted_defaults.append({"item": item, "note": note,
                                           "round": self.round_no})
            self.unverified.append(
                f"{item}: conservative policy default accepted by the "
                f"investigator ({note or 'no note'})")
            self._log(f"policy default accepted for {item}")
        elif action == "declare_done":
            self.stop_reason = "declared done (audit empty)"
            self._log("investigator declared the investigation done")
        self._rebuild()

    def _execute_split(self, oid: str) -> None:
        obj = self.registry.get(oid)
        sub = obj.pixels_or_geom
        view = build_view(self.grid, self.subregions(), self.cfg, self.raster)
        centroids = _pass_fail_clustered(view.votes_by_sid.get(oid, []),
                                         self.cfg)
        a, b = _split_subregion(sub, self.raster, *centroids)
        cov = self.claims.get(f"COV:{oid}")
        for child in (a, b):
            child_obj = self.registry.add(DemandObject(
                id=child.sid, geometry_type="area", pixels_or_geom=child,
                provenance=obj.provenance + ["split"],
                provenance_note=f"split of {oid}", state=CONFIRMED))
            made = open_claims_for(child.sid, self.claims, self.round_no)
            child_obj.claim_ids = [c.cid for c in made]
            cov.children.append(f"COV:{child.sid}")
        for cid in (f"COV:{oid}", f"ROB:{oid}"):
            if cid in self.claims:
                self.claims.get(cid).alive = False
        obj.state = DISMISSED
        obj.provenance_note = f"split into {a.sid}, {b.sid}"
        self._log(f"split {oid} -> {a.sid}, {b.sid} (clustered pass/fail)")

    def _execute_drilldown(self, cid: str) -> None:
        c = self.claims.get(cid)
        cells = sorted(cell for cell, site in self.topology.roster.items()
                       if site == c.subject)
        for cell in cells:
            kid = self.claims.add(Claim(
                cid=f"CAP:{c.subject}:{cell}", ctype=CAPACITY, subject=cell,
                born_round=self.round_no, parent=c.cid,
                remedy="buy per-cell PM for the outage-matched window"))
            c.children.append(kid.cid)
        c.drilled = True
        self._log(f"drilled down {cid} -> {len(cells)} per-cell children")

    # ---------------------------------------------------------- gate checks
    def check_commit(self, commit: dict, gaps: list, tickets: dict,
                     shown_text: str):
        """Gate a committing action.  Returns (request_or_None, denial)."""
        from .gate import GateState, gate
        action = commit.get("action")
        if action == "purchase":
            try:
                req = self._resolve_purchase(commit)
            except ValueError as e:
                return None, str(e)
            state = GateState(
                claims=self.claims, gap_ids={g.gap_id for g in gaps},
                flip=lambda cid: bool(tickets.get(cid)),
                shown_text=shown_text, remaining=self.remaining,
                budget_initial=self.spec.budget,
                purchased_signatures=self.ledger.signatures)
            denial = gate(req, state)
            return (req, denial) if denial is None else (None, denial)
        if action == "register_object":
            n_y, n_x = self.raster.pop.shape
            x, y = float(commit["x"]), float(commit["y"])
            if not (self.raster.x0 <= x < self.raster.x0 + n_x * self.raster.pixel_m
                    and self.raster.y0 <= y < self.raster.y0 + n_y * self.raster.pixel_m):
                return None, f"({x}, {y}) lies outside the data raster"
            if float(commit["radius_m"]) <= 0:
                return None, "radius_m must be positive"
            return None, None
        if action == "dismiss":
            oid = commit["object"]
            if oid not in self.registry:
                return None, f"no object {oid!r}"
            reason = self.registry.verify_dismiss(oid, self.grid, self.raster,
                                                  self.cfg)
            return None, reason
        if action == "split":
            oid = commit["object"]
            if oid not in self.registry:
                return None, f"no object {oid!r}"
            cov = f"COV:{oid}"
            if cov not in self.claims or not self.claims.get(cov).alive \
                    or self.claims.get(cov).state != UNDECIDED:
                return None, f"split requires an open coverage claim on {oid}"
            view = build_view(self.grid, self.subregions(), self.cfg,
                              self.raster)
            if _pass_fail_clustered(view.votes_by_sid.get(oid, []),
                                    self.cfg) is None:
                return None, (f"pass/fail cells of {oid} are not spatially "
                              f"clustered — split refused")
            return None, None
        if action == "drill_down":
            cid = commit["claim"]
            if not self.cfg.capacity_drilldown:
                return None, ("capacity_drilldown is disabled for this run "
                              "(site-level data source)")
            if cid not in self.claims:
                return None, f"no claim {cid!r}"
            c = self.claims.get(cid)
            if c.ctype != CAPACITY or c.parent is not None or c.drilled:
                return None, f"{cid} is not an undrilled site capacity claim"
            if c.state != UNDECIDED or c.detail.get("zone") != "middle_zone":
                return None, (f"drill-down requires a claim stuck in the "
                              f"hourly middle zone; {cid} is "
                              f"{c.state}/{c.detail.get('zone')}")
            return None, None
        if action == "accept_default":
            item = commit["item"]
            if item not in self.claims and item not in self.registry:
                return None, f"{item!r} names neither a claim nor an object"
            return None, None
        if action == "declare_done":
            blockers = [g.gap_id for g in gaps]
            blockers += [c.cid for c in self.claims.open() if c.ticket]
            if blockers:
                return None, (f"cannot declare done — open items remain: "
                              f"{', '.join(sorted(blockers)[:8])}")
            return None, None
        return None, f"unknown committing action {action!r}"

    # ---------------------------------------------------------- round
    def step(self) -> bool:
        """One round == one graph invocation.  False = stop."""
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

    # ---------------------------------------------------------- close-out
    def _final_verdict(self):
        view = self._rebuild()
        ctx = self._verdict_ctx(view)
        verdict = compute_verdict(self.claims.states(), ctx)
        exhausted = ("budget" in self.stop_reason
                     or "no progress" in self.stop_reason
                     or "max rounds" in self.stop_reason
                     or "round cap" in self.stop_reason)
        if not exhausted:
            return verdict, view
        # conservative defaults (direction: degrade) ONLY at exhaustion:
        # undecided tiers become "degraded" — never a fabricated hole —
        # severity-undecided holes are reported severe, and every default
        # is flagged unverified_assumption.
        per = {}
        for sid, sv in verdict.per_subregion.items():
            if sv.tier == UND:
                per[sid] = SubVerdict(DEGRADED, severe=SEVERE_NO,
                                      bottleneck_type=sv.bottleneck_type,
                                      bottleneck_subject=sv.bottleneck_subject)
                self.unverified.append(
                    f"{sid}: tier undecided at stop ({self.stop_reason}; "
                    f"open {sv.bottleneck_type} claim); conservatively "
                    f"reported as degraded")
            elif sv.tier == HOLE and sv.severe == SEVERE_UND:
                per[sid] = SubVerdict(HOLE, severe="severe",
                                      bottleneck_type=sv.bottleneck_type,
                                      bottleneck_subject=sv.bottleneck_subject)
                self.unverified.append(
                    f"{sid}: hole severity undecided at stop; conservatively "
                    f"reported severe (policy default)")
            else:
                per[sid] = sv
        tiers = [v.tier for v in per.values()]
        if any(v.tier == HOLE and v.severe == "severe" for v in per.values()):
            overall = OVERALL_SEVERE
        elif HOLE in tiers or DEGRADED in tiers:
            overall = OVERALL_DEGRADED
        elif ctx.residual_ok:
            overall = OVERALL_FULL
        else:
            overall = OVERALL_UND
            self.unverified.append(
                "residual demand bound above rho_residual (or unknown) at "
                "stop — full absorption not declarable")
        return Verdict(overall, per), view

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

    def finish(self) -> RunResult:
        if not self.stop_reason:
            self.stop_reason = "stopped"
        self._buy_target_baseline()
        verdict, view = self._final_verdict()

        result = RunResult(
            case=self.spec.name,
            verdict_overall=verdict.overall,
            per_object={sid: {"tier": sv.tier, "severe": sv.severe,
                              "bottleneck": (sv.bottleneck_type,
                                             sv.bottleneck_subject)}
                        for sid, sv in verdict.per_subregion.items()},
            spent=self.ledger.spent, budget=self.spec.budget,
            rounds=self.round_no, stop_reason=self.stop_reason,
            unverified_assumptions=list(self.unverified),
            ledger_entries=list(self.ledger.entries),
            agent_summary=self.agent_ledger.summary(self.round_no),
            incidents=list(self.incidents),
            events=list(self.events), notebook=list(self.notebook))
        from .report import render_report
        result.report_md = render_report(self, verdict, result)
        if self.run_dir is not None:
            self.run_dir.mkdir(parents=True, exist_ok=True)
            (self.run_dir / "ledger.json").write_text(
                json.dumps(self.ledger.entries, indent=2))
            (self.run_dir / "events.log").write_text("\n".join(self.events))
            (self.run_dir / "notebook.md").write_text(
                "# Investigator notebook\n\n"
                + "\n".join(f"- {line}" for line in self.notebook) + "\n")
            (self.run_dir / "trace.jsonl").write_text(
                "\n".join(json.dumps(r, default=str) for r in self.trace))
            (self.run_dir / "report.md").write_text(result.report_md)
        return result

    def run(self, rounds: int | None = None) -> RunResult:
        while self.step():
            if rounds is not None and self.round_no >= rounds:
                if not self.stop_reason:
                    self.stop_reason = f"round cap ({rounds}) reached"
                break
        return self.finish()
