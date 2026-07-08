"""Rule baselines for both seats.

Whether the LLM agents earn their keep is an experimental question — these
baselines can be swapped into either seat via the harness's per-seat flag.
"""

from __future__ import annotations

from .seats import Seat1, Seat2, Seat1Output, Seat2Output

_ANCHOR_NOTE = {"no_clue_found_anchor_followed": True}


# ---------------------------------------------------------------- helpers
def _row_by_cid(board: list, cid: str) -> dict | None:
    for r in board:
        if r["cid"] == cid:
            return r
    return None


def _capacity_anchor(subject: str, digest: dict) -> float | None:
    nb = digest.get("neighbors", {}).get(subject, {})
    return nb.get("anchor_mean")


def _zone(a: float, zones: dict) -> str:
    if a >= zones["pi_hi"]:
        return "refute_zone"
    edge = zones.get("support_edge")
    if edge is not None and a < edge:
        return "support_zone"
    return "middle_zone"


def _edge_distance(a: float, zones: dict) -> float:
    """Distance to the nearest deciding zone edge."""
    ds = [abs(a - zones["pi_hi"])]
    if zones.get("support_edge") is not None:
        ds.append(abs(a - zones["support_edge"]))
    return min(ds)


def zone_distance_grade(cid: str, item: str, board: list,
                        digest: dict) -> str:
    """Grade an item by the anchor's distance to the nearest zone edge.
    item is 'supported' | 'refuted' | 'direct'."""
    row = _row_by_cid(board, cid)
    if row is None:
        return "mid"
    zones = digest.get("zones", {})
    if row["type"] == "capacity":
        a = row.get("hourly_mean")
        if a is None:
            a = _capacity_anchor(row["subject"], digest)
        if a is None:
            return "mid"
        z = _zone(a, zones)
        far = _edge_distance(a, zones) > 0.10
        if item == "direct":
            return "high" if (z != "middle_zone" and far) else \
                   ("low" if z == "middle_zone" and far else "mid")
        agrees = (z == "support_zone") == (item == "supported")
        if z == "middle_zone":
            return "mid"
        if agrees:
            return "high" if far else "mid"
        return "low"
    # coverage / robustness: distance of the point estimate to the threshold
    p, thr = None, None
    if row["type"] == "coverage":
        p, thr = row.get("p_hat"), zones.get("theta", 0.9)
    elif row["type"] == "robustness":
        # supported means the top share stays BELOW kappa
        ts = row.get("top_share")
        if ts is not None:
            p, thr = 1.0 - ts, 1.0 - zones.get("kappa", 0.6)
    if p is None or thr is None:
        return "mid"
    d = p - thr
    if item == "direct":
        return "high" if abs(d) > 0.07 else "mid"
    agrees = (d > 0) == (item == "supported")
    if agrees:
        return "high" if abs(d) > 0.07 else "mid"
    return "low" if abs(d) > 0.07 else "mid"


# ---------------------------------------------------------------- Seat 1
class RuleSeat1AllMid(Seat1):
    """Constant-grade rule (all mid): reduces the code-computed ordering to
    the greedy score flip-impact x population / price."""
    name = "rule1-allmid"

    def prioritize(self, board, deps, digest) -> Seat1Output:
        grades = {}
        for r in deps:
            grades[r.row_id()] = {"grade": "mid", "rationale": "constant rule",
                                  **_ANCHOR_NOTE}
        for row in board:
            if row["ticket"]:
                grades[f"{row['cid']}=direct"] = {
                    "grade": "mid", "rationale": "constant rule", **_ANCHOR_NOTE}
        return Seat1Output(grades=grades, source="rule")


class RuleSeat1ZoneDistance(Seat1):
    """Slightly smarter baseline: grade by the anchor's distance to the
    nearest zone edge."""
    name = "rule1-zonedist"

    def prioritize(self, board, deps, digest) -> Seat1Output:
        grades = {}
        for r in deps:
            g = zone_distance_grade(r.lever_cid, r.outcome, board, digest)
            grades[r.row_id()] = {"grade": g, "rationale": "zone-distance rule",
                                  **_ANCHOR_NOTE}
        for row in board:
            if row["ticket"]:
                g = zone_distance_grade(row["cid"], "direct", board, digest)
                grades[f"{row['cid']}=direct"] = {
                    "grade": g, "rationale": "zone-distance rule", **_ANCHOR_NOTE}
        return Seat1Output(grades=grades, source="rule")


# ---------------------------------------------------------------- Seat 2
def predict_bucket(action, board, digest) -> tuple[str, str]:
    """Mechanical (bucket, grade) prediction by placing the anchor against
    the bucket walls — shared by the rule baseline and the fallback path."""
    row = _row_by_cid(board, action.claim_cid)
    zones = digest.get("zones", {})
    theta = zones.get("theta", 0.9)
    if action.kind == "pm_hourly":
        a = _capacity_anchor(row["subject"], digest) if row else None
        if a is None:
            return "middle_zone", "low"
        z = _zone(a, zones)
        return z, ("high" if _edge_distance(a, zones) > 0.10 else "mid")
    if action.kind == "pm_15min":
        a = (row or {}).get("hourly_mean")
        if a is None and row is not None:
            a = _capacity_anchor(row["subject"], digest)
        if a is None:
            return "support", "low"
        return ("refute", "mid") if a >= zones.get("pi_hi", 0.85) - 0.05 \
            else ("support", "mid")
    if action.kind in ("coverage_densify", "bg_sweep"):
        p = (row or {}).get("p_hat")
        if p is None:
            return "still_straddling", "low"
        if p >= theta + 0.03:
            return "clears_theta", "mid"
        if p <= theta - 0.07:
            return "falls_below_theta", "mid"
        return "still_straddling", "mid"
    if action.kind == "robustness_densify":
        ts = (row or {}).get("top_share")
        kappa = zones.get("kappa", 0.6)
        if ts is None:
            return "still_ambiguous", "low"
        if ts <= kappa - 0.07:
            return "diverse", "mid"
        if ts >= kappa + 0.07:
            return "concentrated", "mid"
        return "still_ambiguous", "mid"
    if action.kind == "ring_sample":
        return "clean", "mid"
    if action.kind == "profile":
        return "anchor_confirms", "mid"
    return action.buckets[0], "low"


def mechanical_contingencies(action) -> dict:
    """One line per outcome bucket, derived from the adjudication criteria."""
    from ..planning.menu import AMBIGUOUS
    amb = AMBIGUOUS.get(action.kind)
    out = {}
    for b in action.buckets:
        if b == amb:
            out[b] = (f"still ambiguous -> forced follow-up "
                      f"(worst-case +{action.followup_price})")
        elif b == "contaminated":
            out[b] = "integrity refuted -> boundary expansion forced"
        else:
            out[b] = "claim resolves; re-run flip tests and lifecycle"
    return out


class RuleSeat2Cheapest(Seat2):
    """Always the cheapest action touching the target claim; escalation only
    when a held measurement already proves the cheap tier cannot decide
    (the menu already encodes this: a middle-zone hourly hold means only the
    15-minute action is offered for that claim)."""
    name = "rule2-cheapest"

    def choose(self, candidates, menu, digest, constants, deps) -> Seat2Output:
        board = constants["board"]
        for cid in candidates:
            acts = sorted((a for a in menu
                           if a.claim_cid == cid and a.kind != "profile"),
                          key=lambda a: (a.price, a.aid))
            if acts:
                a = acts[0]
                bucket, grade = predict_bucket(a, board, digest)
                return Seat2Output(
                    action_aid=a.aid, predicted_bucket=bucket, grade=grade,
                    contingencies=mechanical_contingencies(a),
                    rationale="cheapest action touching the target claim",
                    source="rule")
        # nothing resolving on any candidate: fall back to any cheapest action
        acts = sorted(menu, key=lambda x: (x.price, x.aid))
        if not acts:
            raise RuntimeError("empty action menu for seat 2")
        a = acts[0]
        bucket, grade = predict_bucket(a, board, digest)
        return Seat2Output(action_aid=a.aid, predicted_bucket=bucket,
                           grade=grade,
                           contingencies=mechanical_contingencies(a),
                           judgment_firming=(a.kind == "profile"),
                           rationale="no resolving action on candidates; "
                                     "cheapest available", source="rule")
