"""Offline calibration script (Section 9).

Builds the hourly-mean-bucket -> 15-minute-spike-rate table from the
CALIBRATION cases' simulated 15-minute data, places the support-zone edge at
<= 5% false-pass rate, and stores the table as a versioned artifact that the
runtime loads.

Run:  python -m outage_whatif.eval.calibrate
"""

from __future__ import annotations

from pathlib import Path

from ..config import CFG, Config
from ..loop.case import CaseSpec
from ..planning.calibration import CalibrationTable, build_calibration_table
from ..provider.simulator import generate_world

CASES_DIR = Path(__file__).parent.parent / "cases"
ARTIFACT = CASES_DIR / "calibration_table.json"


def build_and_save_calibration(cfg: Config = CFG,
                               cases_dir: Path = CASES_DIR,
                               artifact: Path = ARTIFACT) -> CalibrationTable:
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
