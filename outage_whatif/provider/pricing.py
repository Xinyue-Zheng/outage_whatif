"""The price function — one encapsulated module reflecting platform-style
pricing rules.  ALL prices in the system flow from here; "cheap"/"expensive"
exist only as quartiles within a round's action menu.

Rules:
* coverage: super-linear in area x density.
  DESIGN-GAP: the number of requested points is used as the proxy for
  area x density (each point is one probe of the platform's raster).
* PM: granularity factor x entity count x window length.  No assumption
  that PM is cheap relative to coverage.
* profiles: cheap-ish flat rates.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PriceBook:
    coverage_base: float = 1.0
    coverage_exp: float = 1.15          # super-linearity
    pm_rate: float = 0.8                # per entity-hour at hourly granularity
    pm_gran_factor: dict = field(default_factory=lambda: {
        "hourly": 1.0, "15min": 4.0})
    profile_flat: dict = field(default_factory=lambda: {
        "same_weekday": 5.0, "holiday_last_year": 6.0,
        "matched_hour": 5.5})

    def coverage(self, n_points: int) -> float:
        if n_points <= 0:
            return 0.0
        return round(self.coverage_base * n_points ** self.coverage_exp, 2)

    def pm(self, granularity: str, n_entities: int, hours: float) -> float:
        return round(self.pm_rate * self.pm_gran_factor[granularity]
                     * n_entities * hours, 2)

    def profile(self, kind: str) -> float:
        return self.profile_flat[kind]

    def quote(self, kind: str, **p) -> float:
        if kind == "coverage":
            return self.coverage(p["n_points"])
        if kind == "pm":
            return self.pm(p["granularity"], p["n_entities"], p["hours"])
        if kind == "profile":
            return self.profile(p["profile_kind"])
        raise ValueError(f"unknown action kind {kind!r}")
