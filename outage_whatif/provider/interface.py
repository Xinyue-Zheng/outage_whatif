"""DataProvider interface — the seam between the analysis system and the
(not yet existing) data platform.  The simulator implements it today; a real
platform adapter would implement the same interface later.

Every paid method returns ``(data, charged_price)``.  ``quote`` prices an
action without buying.  Budget accounting lives in the loop's ledger, not
here.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime


# ------------------------------------------------------------- free inputs
@dataclass
class Topology:
    """Free input: all eNodeB coordinates, cell->site roster, optional azimuths.
    Useful but possibly stale/incomplete."""
    sites: dict                      # site_id -> (x, y) metres
    roster: dict                     # cell_id -> site_id
    azimuths: dict = field(default_factory=dict)   # cell_id -> degrees


# ------------------------------------------------------------- paid results
@dataclass
class PointCoverage:
    x: float
    y: float
    serving: tuple                   # (cell_id, rsrp)
    backups: list                    # [(cell_id, rsrp)] top-5


@dataclass
class PMSeries:
    entity: str
    metric: str                      # rrc_conn | prb_util | throughput | volume
    granularity: str                 # hourly | 15min
    samples: list                    # [(iso_timestamp, value)]

    def values(self) -> list:
        return [v for _, v in self.samples]


@dataclass
class Profile:
    """Judgment-firming product: summarized historical load profile.
    Changes no claim directly — only the anchor digest."""
    site: str
    kind: str                        # same_weekday | holiday_last_year
    hourly_mean: list                # 24 floats (PRB utilisation)
    hourly_var: list                 # 24 floats


@dataclass(frozen=True)
class Window:
    start: datetime
    end: datetime

    @property
    def hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600.0

    @classmethod
    def parse(cls, start_iso: str, end_iso: str) -> "Window":
        return cls(datetime.fromisoformat(start_iso), datetime.fromisoformat(end_iso))


# ------------------------------------------------------------- interface
class DataProvider(abc.ABC):
    """All paid data flows through here."""

    @abc.abstractmethod
    def topology(self) -> Topology:
        """Free input."""

    @abc.abstractmethod
    def population_raster(self):
        """Free input: PopulationRaster (possibly stale/incomplete)."""

    @abc.abstractmethod
    def query_coverage(self, points: list) -> tuple[list, float]:
        """points: [(x, y)] -> ([PointCoverage], charged price)."""

    @abc.abstractmethod
    def query_pm(self, entities: list, metric: str, granularity: str,
                 window: Window) -> tuple[dict, float]:
        """-> ({entity: PMSeries}, charged price)."""

    @abc.abstractmethod
    def buy_profile(self, site: str, kind: str) -> tuple[Profile, float]:
        ...

    @abc.abstractmethod
    def quote(self, kind: str, **params) -> float:
        """Price an action without buying it.
        kinds: coverage(n_points) | pm(granularity, n_entities, hours)
             | profile(profile_kind)."""
