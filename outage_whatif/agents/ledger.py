"""Purchase ledger and the agent's prediction ledger.

The prediction ledger is bookkeeping only: per-grade hit rates are recorded
and shown back to the agent in the briefing, but nothing routes decisions
away from the agent.

Known selection bias (documented per the design): only rows the system
actually chose to act on ever get reconciled — the hit rates measure
performance on chosen rows, not on all graded rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field


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
    """Prediction ledger.  Grades of 'mid' are recorded but count neither
    hit nor miss."""
    seat: str = "investigator"
    records: list = field(default_factory=list)
    consecutive_misses: int = 0

    # ---------------- recording
    def record_prediction(self, round_no: int, item_id: str, cid: str,
                          predicted_bucket: str, grade: str) -> None:
        """One committed purchase = one bucket prediction at a grade."""
        self.records.append({"round": round_no, "item": item_id, "cid": cid,
                             "kind": "bucket", "grade": grade,
                             "predicted": predicted_bucket,
                             "resolved": False, "hit": None})

    # ---------------- reconciliation
    def _score(self, rec: dict, hit: bool | None) -> None:
        rec["resolved"] = True
        rec["hit"] = hit
        if hit is None:                    # mid grades are neutral
            return
        self.consecutive_misses = 0 if hit else self.consecutive_misses + 1

    def reconcile(self, item_id: str, actual_bucket: str) -> None:
        """Bucket predictions reconcile immediately on execution."""
        for rec in self.records:
            if rec["resolved"] or rec["item"] != item_id:
                continue
            rec["actual"] = actual_bucket
            g = rec["grade"]
            matched = rec.get("predicted") == actual_bucket
            hit = None if g == "mid" else (g == "high") == matched
            self._score(rec, hit)

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

    def last_reconciled(self) -> dict | None:
        """The most recent resolved prediction (briefing: predicted vs
        actual, hit/miss)."""
        done = [r for r in self.records if r["resolved"]]
        return done[-1] if done else None

    def summary(self, now_round: int = 0) -> dict:
        return {"hit_rate_per_grade": self.hit_rates(),
                "consecutive_misses": self.consecutive_misses,
                "selection_bias_note": "only chosen rows get tested"}
