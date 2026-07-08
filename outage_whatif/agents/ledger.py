"""Purchase ledger and per-agent prediction ledgers with fuses.

Known selection bias (documented per the design): only rows the system
actually chose to act on ever get reconciled — the hit rates measure
performance on chosen rows, not on all graded rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..claims.model import UNDECIDED


@dataclass
class PurchaseLedger:
    entries: list = field(default_factory=list)
    signatures: set = field(default_factory=set)
    spent: float = 0.0

    def record(self, round_no: int, aid: str, kind: str, price: float,
               purpose: str, claim_cid: str | None, signature=None) -> None:
        self.entries.append({
            "round": round_no, "aid": aid, "kind": kind,
            "price": round(price, 2), "purpose": purpose, "claim": claim_cid})
        if signature is not None:
            self.signatures.add(signature)
        self.spent = round(self.spent + price, 2)


@dataclass
class AgentLedger:
    """Per-seat prediction ledger.  Grades of 'mid' are recorded but count
    neither hit nor miss; the two-consecutive-miss fuse routes THIS seat
    only to its baseline rule for the next round."""
    seat: str
    fuse_threshold: int = 2
    records: list = field(default_factory=list)
    consecutive_misses: int = 0
    fuse_trips: int = 0
    fuse_active: bool = False

    # ---------------- recording
    def record_seat1(self, round_no: int, item_id: str, cid: str,
                     kind: str, grade: str) -> None:
        """kind: 'supported' | 'refuted' | 'direct'."""
        self.records.append({"round": round_no, "item": item_id, "cid": cid,
                             "kind": kind, "grade": grade, "resolved": False,
                             "hit": None})

    def record_seat2(self, round_no: int, aid: str, cid: str,
                     predicted_bucket: str, grade: str,
                     judgment_firming: bool = False) -> None:
        self.records.append({"round": round_no, "item": aid, "cid": cid,
                             "kind": "bucket", "grade": grade,
                             "predicted": predicted_bucket,
                             "firming": judgment_firming,
                             "resolved": False, "hit": None})

    # ---------------- reconciliation
    def _score(self, rec: dict, hit: bool | None) -> None:
        rec["resolved"] = True
        rec["hit"] = hit
        if hit is None:                    # mid grades are neutral
            return
        if hit:
            self.consecutive_misses = 0
        else:
            self.consecutive_misses += 1
            if self.consecutive_misses >= self.fuse_threshold:
                self.fuse_active = True
                self.fuse_trips += 1
                self.consecutive_misses = 0

    def reconcile_seat1_on_execution(self, cid: str, new_state: str) -> None:
        """Called when a graded lever's query executes.  Did the outcome
        land where the grade implied?"""
        for rec in self.records:
            if rec["resolved"] or rec["cid"] != cid or rec["kind"] == "bucket":
                continue
            g = rec["grade"]
            if rec["kind"] == "direct":
                decided = new_state != UNDECIDED
                hit = None if g == "mid" else (g == "high") == decided
            else:
                if new_state == UNDECIDED:
                    continue               # not yet decided; keep open
                matched = new_state == rec["kind"]
                hit = None if g == "mid" else (g == "high") == matched
            self._score(rec, hit)

    def reconcile_seat2(self, aid: str, actual_bucket: str) -> None:
        """Bucket predictions reconcile immediately on execution."""
        for rec in self.records:
            if rec["resolved"] or rec["item"] != aid:
                continue
            rec["actual"] = actual_bucket
            g = rec["grade"]
            matched = rec.get("predicted") == actual_bucket
            hit = None if g == "mid" else (g == "high") == matched
            self._score(rec, hit)

    def score_firming(self, aid: str, grade_moved: bool) -> None:
        """A judgment-firming purchase is scored on whether the relevant
        grade actually moved next round."""
        for rec in self.records:
            if rec["item"] == aid and rec.get("firming") and not rec["resolved"]:
                self._score(rec, grade_moved if rec["grade"] != "mid" else None)
                rec["firming_grade_moved"] = grade_moved

    # ---------------- fuse routing
    def consume_fuse(self) -> bool:
        """True if this round must route to the baseline; the fuse then
        resets (DESIGN-GAP: one-round penalty duration)."""
        if self.fuse_active:
            self.fuse_active = False
            return True
        return False

    # ---------------- reporting
    def hit_rates(self) -> dict:
        out = {}
        for g in ("high", "mid", "low"):
            scored = [r for r in self.records
                      if r["grade"] == g and r["resolved"] and r["hit"] is not None]
            graded = [r for r in self.records if r["grade"] == g]
            out[g] = {"graded": len(graded), "scored": len(scored),
                      "hits": sum(r["hit"] for r in scored),
                      "rate": (round(sum(r["hit"] for r in scored) / len(scored), 3)
                               if scored else None)}
        return out

    def recent_misses(self, n_rounds: int = 3, now_round: int = 0) -> int:
        return sum(1 for r in self.records
                   if r["resolved"] and r["hit"] is False
                   and r["round"] >= now_round - n_rounds)

    def summary(self, now_round: int = 0) -> dict:
        return {"hit_rate_per_grade": self.hit_rates(),
                "misses_last_3_rounds": self.recent_misses(3, now_round),
                "consecutive_misses": self.consecutive_misses,
                "fuse_active": self.fuse_active,
                "fuse_trips": self.fuse_trips,
                "selection_bias_note": "only chosen rows get tested"}
