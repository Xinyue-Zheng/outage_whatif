"""Calibration of the hourly capacity tier (offline script + runtime table).

From 15-minute data of the calibration cases, build the
hourly-mean-bucket -> 15-minute-spike-rate table and place the support-zone
edge at the highest bucket boundary where the false-pass rate stays
<= calib_false_pass_max ([POLICY], default 5%).  If no bucket satisfies it,
the hourly tier loses the right to declare support (support_edge = None).

The table is stored as a versioned JSON artifact and loaded at runtime.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from ..config import Config

N_BUCKETS = 10


@dataclass
class CalibrationTable:
    version: str
    support_edge: float | None
    bucket_rates: list = field(default_factory=list)   # spike rate per bucket
    bucket_counts: list = field(default_factory=list)
    false_pass_max: float = 0.05
    sources: list = field(default_factory=list)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.__dict__, indent=2))

    @classmethod
    def load(cls, path: Path) -> "CalibrationTable":
        return cls(**json.loads(path.read_text()))


def build_calibration_table(worlds: dict, cfg: Config,
                            days: int = 28,
                            start: str = "2026-05-04") -> CalibrationTable:
    """worlds: {case_name: World} for the calibration cases.

    For every site-hour in the calibration span, pair the hourly mean with
    whether its 15-minute bins contain a spike that the 15-minute tier
    would count against pi_hi.  A false pass = hourly mean in a candidate
    support bucket while the hour spikes.
    """
    pol = cfg.policy
    counts = [0] * N_BUCKETS
    spikes = [0] * N_BUCKETS
    t0 = datetime.fromisoformat(start)
    for name, w in sorted(worlds.items()):
        for site in sorted(w.sites):
            for d in range(days):
                day = t0 + timedelta(days=d)
                for h in range(24):
                    ts = day.replace(hour=h)
                    m = w.hourly_prb(site, ts)
                    b = min(int(m * N_BUCKETS), N_BUCKETS - 1)
                    spiked = any(
                        w.q15_prb(site, ts + timedelta(minutes=15 * q)) >= pol.pi_hi
                        for q in range(4))
                    counts[b] += 1
                    spikes[b] += int(spiked)

    rates = [spikes[b] / counts[b] if counts[b] else None
             for b in range(N_BUCKETS)]

    # highest edge e = (b+1)/N such that every populated bucket below e has
    # a spike rate <= false_pass_max
    edge = None
    for b in range(N_BUCKETS):
        r = rates[b]
        if r is None:
            continue                      # empty bucket: no evidence against
        if r <= pol.calib_false_pass_max:
            edge = (b + 1) / N_BUCKETS
        else:
            break
    # a support zone above pi_hi would be self-contradictory
    if edge is not None:
        edge = min(edge, pol.pi_hi)

    return CalibrationTable(
        version=f"calib-v1-{days}d-{len(worlds)}cases",
        support_edge=edge,
        bucket_rates=[None if r is None else round(r, 4) for r in rates],
        bucket_counts=counts,
        false_pass_max=pol.calib_false_pass_max,
        sources=sorted(worlds))
