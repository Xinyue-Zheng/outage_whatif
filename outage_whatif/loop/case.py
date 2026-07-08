"""Case specification: target site, the ticket's FULL outage window
(possibly many hours; weekday/holiday/season flags derived from it), total
budget B, the simulator scenario block, and the analysis hour.

Per-hour semantics: one run answers one conditional question — "IF the
outage's effect is evaluated at ``analysis_hour``, can neighbors absorb the
target's users?".  One run = one (case, analysis_hour) pair.  The hour must
lie inside the ticket window (validated at runner init); when omitted, the
[POLICY] default rule fires (busiest window hour per a held target profile,
else the window midpoint) and the report records which rule fired."""

from __future__ import annotations

import dataclasses
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
    window: Window               # the ticket's full outage window
    sim: dict = field(default_factory=dict)
    target_site: str | None = None    # None -> simulator's default target
    analysis_hour: int | None = None  # clock-hour within the window
    analysis_hour_rule: str = ""      # how the hour was chosen (report)

    @classmethod
    def load(cls, path: str | Path) -> "CaseSpec":
        d = yaml.safe_load(Path(path).read_text())
        ah = d.get("analysis_hour")
        return cls(name=d["name"], kind=d.get("kind", "blind"),
                   seed=int(d["seed"]), budget=float(d["budget"]),
                   window=Window.parse(d["outage_start"], d["outage_end"]),
                   sim=d.get("sim", {}) or {},
                   target_site=d.get("target_site"),
                   analysis_hour=None if ah is None else int(ah),
                   analysis_hour_rule="explicit (case file)"
                                      if ah is not None else "")

    def resolve_analysis_hour(self, cfg: Config,
                              target_profile: list | None = None) -> int:
        """Validate an explicit analysis_hour or apply the [POLICY] default
        rule.  Raises ValueError (case rejected) if the explicit hour lies
        outside the ticket window.  Stamps the hour onto ``window`` so all
        downstream consumers (menu, provider, digest) see it."""
        from ..planning.comparable import (default_analysis_hour,
                                           validate_analysis_hour)
        if self.analysis_hour is not None:
            validate_analysis_hour(self.window, self.analysis_hour)
            if not self.analysis_hour_rule:
                self.analysis_hour_rule = "explicit"
        else:
            h, rule = default_analysis_hour(self.window, target_profile)
            self.analysis_hour = h
            self.analysis_hour_rule = f"[POLICY] default rule: {rule}"
        self.window = dataclasses.replace(self.window,
                                          analysis_hour=self.analysis_hour)
        return self.analysis_hour

    def calendar_flags(self, cfg: Config) -> dict:
        d = self.window.start.date()
        dt = day_type(d, set(cfg.holidays))
        flags = {
            "date": d.isoformat(),
            "weekday": d.strftime("%A"),
            "day_type": dt,
            "holiday": dt == "holiday",
            "season": "summer" if d.month in cfg.summer_months else "off-season",
            "hours": f"{self.window.start.hour:02d}:00-{self.window.end.hour:02d}:00",
        }
        if self.analysis_hour is not None:
            h = self.analysis_hour
            first, last = self.window.start.hour, self.window.end.hour - 1
            flags.update({
                "analysis_hour": h,
                "analysis_hour_weekday": d.strftime("%A"),
                "analysis_hour_holiday_class": dt,
                "analysis_hour_position": ("first hour" if h == first else
                                           "last hour" if h == last else
                                           "middle"),
            })
        return flags
