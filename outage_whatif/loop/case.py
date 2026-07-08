"""Case specification: target site, outage window (weekday/holiday/season
flags derived from it), total budget B, plus the simulator scenario block."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..config import Config
from ..provider.interface import Window
from ..provider.simulator import day_type


@dataclass
class CaseSpec:
    name: str
    kind: str                    # calibration | blind
    seed: int
    budget: float
    window: Window
    sim: dict = field(default_factory=dict)
    target_site: str | None = None    # None -> simulator's default target

    @classmethod
    def load(cls, path: str | Path) -> "CaseSpec":
        d = yaml.safe_load(Path(path).read_text())
        return cls(name=d["name"], kind=d.get("kind", "blind"),
                   seed=int(d["seed"]), budget=float(d["budget"]),
                   window=Window.parse(d["outage_start"], d["outage_end"]),
                   sim=d.get("sim", {}) or {},
                   target_site=d.get("target_site"))

    def calendar_flags(self, cfg: Config) -> dict:
        d = self.window.start.date()
        dt = day_type(d, set(cfg.holidays))
        return {
            "date": d.isoformat(),
            "weekday": d.strftime("%A"),
            "day_type": dt,
            "holiday": dt == "holiday",
            "season": "summer" if d.month in cfg.summer_months else "off-season",
            "hours": f"{self.window.start.hour:02d}:00-{self.window.end.hour:02d}:00",
        }
