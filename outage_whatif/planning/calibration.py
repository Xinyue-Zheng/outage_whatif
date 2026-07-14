"""Calibration of the hourly capacity tier (offline script + runtime table).

From 15-minute data of the calibration cases, build the
hourly-mean-bucket -> 15-minute-spike-rate table and place the support-zone
edge at the highest bucket boundary where the false-pass rate stays
<= calib_false_pass_max ([POLICY], default 5%).  If no bucket satisfies it,
the hourly tier loses the right to declare support (support_edge = None).

The table is stored as a versioned JSON artifact and loaded at runtime.

Run offline:  python -m outage_whatif.planning.calibration
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

    Matched-hour samples (per-hour semantics): one sample = one
    (site, anchor-day, clock-hour) slot, whose hourly-mean input is the
    MEAN of the k matched weekly occurrences of that hour (same weekday,
    k = cfg.policy.comparable_days_k) — exactly what the hourly tier now
    adjudicates — paired with whether the 4k matched 15-minute bins would
    refute at the 15-minute tier (fraction >= pi_hi above
    cap15_refute_frac).  A false pass = matched-hour mean in a candidate
    support bucket while the matched bins refute.  Table format unchanged.
    """
    pol = cfg.policy
    k = pol.comparable_days_k
    counts = [0] * N_BUCKETS
    spikes = [0] * N_BUCKETS
    t0 = datetime.fromisoformat(start)
    for name, w in sorted(worlds.items()):
        for site in sorted(w.sites):
            for d in range(0, days, 7):       # one anchor day per week
                day = t0 + timedelta(days=d)
                for h in range(24):
                    stamps = [day.replace(hour=h) - timedelta(weeks=i)
                              for i in range(k)]
                    m = sum(w.hourly_prb(site, ts) for ts in stamps) / k
                    b = min(int(m * N_BUCKETS), N_BUCKETS - 1)
                    bins = [w.q15_prb(site, ts + timedelta(minutes=15 * q))
                            for ts in stamps for q in range(4)]
                    frac = sum(v >= pol.pi_hi for v in bins) / len(bins)
                    counts[b] += 1
                    spikes[b] += int(frac > pol.cap15_refute_frac)

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
        version=f"calib-v2-matched-{days}d-{len(worlds)}cases",
        support_edge=edge,
        bucket_rates=[None if r is None else round(r, 4) for r in rates],
        bucket_counts=counts,
        false_pass_max=pol.calib_false_pass_max,
        sources=sorted(worlds))


# --------------------------------------------------------- artifact plumbing
CASES_DIR = Path(__file__).parent.parent / "cases"
ARTIFACT = CASES_DIR / "calibration_table.json"


def build_and_save_calibration(cfg: Config | None = None,
                               cases_dir: Path = CASES_DIR,
                               artifact: Path = ARTIFACT) -> CalibrationTable:
    """Build the table from the calibration cases' simulated worlds and
    store it as the versioned artifact the runtime loads."""
    # local imports: loop.case and provider.simulator import planning back
    from ..config import CFG
    from ..loop.case import CaseSpec
    from ..provider.simulator import generate_world
    cfg = cfg or CFG
    worlds = {}
    for path in sorted(cases_dir.glob("*.yaml")):
        spec = CaseSpec.load(path)
        if spec.kind == "calibration":
            worlds[spec.name] = generate_world(spec.sim, spec.seed, cfg)
    if not worlds:
        raise RuntimeError(f"no calibration cases found in {cases_dir}")
    table = build_calibration_table(worlds, cfg, days=28)
    table.save(artifact)
    return table


def load_calibration(artifact: Path = ARTIFACT) -> CalibrationTable | None:
    if artifact.exists():
        return CalibrationTable.load(artifact)
    return None


if __name__ == "__main__":
    t = build_and_save_calibration()
    print(f"saved {ARTIFACT}")
    print(f"version={t.version} support_edge={t.support_edge}")
    print(f"bucket_rates={t.bucket_rates}")
