"""Comparable-day matching for per-hour capacity evidence ([POLICY]).

The system's question is conditional on one clock-hour (``analysis_hour``)
selected from within the ticket's outage window.  Capacity evidence is the
k matched occurrences of that hour on comparable days:

* same clock-hour AND same weekday, the most recent k weeks before the
  outage date;
* a holiday outage matches holiday-class days instead (most recent
  holidays before the outage — the same holiday last year is reached when
  purchasable from the calendar);
* days on ``cfg.known_outage_dates`` are excluded, and matching extends
  further back until k occurrences are found (bounded).

All constants live in the [POLICY] block (``comparable_days_k``,
``analysis_hour_default_rule``).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from ..config import Config
from ..provider.interface import Window
from ..provider.simulator import day_type

_MAX_EXTRA_WEEKS = 12          # exclusion may push matching this far back


def window_hours(window: Window) -> list[int]:
    """Clock-hours covered by a (same-day) ticket window."""
    return list(range(window.start.hour, max(window.end.hour,
                                             window.start.hour + 1)))


def validate_analysis_hour(window: Window, hour: int) -> None:
    hours = window_hours(window)
    if hour not in hours:
        raise ValueError(
            f"analysis_hour {hour} lies outside the ticket window "
            f"{window.start.isoformat()}..{window.end.isoformat()} "
            f"(valid clock-hours: {hours[0]}..{hours[-1]})")


def default_analysis_hour(window: Window,
                          target_profile_hourly_mean: list | None = None
                          ) -> tuple[int, str]:
    """[POLICY] default selection when the ticket omits analysis_hour:
    busiest hour of the window per the target's historical profile if one
    is already held, else the window midpoint.  Returns (hour, rule)."""
    hours = window_hours(window)
    if target_profile_hourly_mean:
        h = max(hours, key=lambda x: target_profile_hourly_mean[x])
        return h, "busiest hour of window per held target profile"
    return hours[len(hours) // 2], "window midpoint (no target profile held)"


def _hour_window(day: datetime, hour: int) -> Window:
    s = day.replace(hour=hour, minute=0, second=0, microsecond=0)
    return Window(s, s + timedelta(hours=1))


def matched_hour_windows(window: Window, analysis_hour: int,
                         cfg: Config) -> list[Window]:
    """The k matched one-hour windows on comparable days (most recent
    first).  Deterministic function of (window, analysis_hour, cfg)."""
    k = cfg.policy.comparable_days_k
    holidays = set(cfg.holidays)
    excluded = set(cfg.known_outage_dates)
    date0 = window.start.date()
    out: list[Window] = []

    if day_type(date0, holidays) == "holiday":
        # holiday-class matching: most recent holidays strictly before the
        # outage date (includes the same holiday last year when listed)
        for iso in sorted((d for d in holidays if d < date0.isoformat()),
                          reverse=True):
            if iso in excluded:
                continue
            out.append(_hour_window(datetime.fromisoformat(iso),
                                    analysis_hour))
            if len(out) == k:
                break
        return out

    weeks = 1
    while len(out) < k and weeks <= k + _MAX_EXTRA_WEEKS:
        day = window.start - timedelta(weeks=weeks)   # same weekday by construction
        weeks += 1
        iso = day.date().isoformat()
        if iso in excluded:
            continue
        if day_type(day.date(), holidays) != "weekday" \
                and day_type(date0, holidays) != day_type(day.date(), holidays):
            continue          # a matched weekday that falls on a holiday
        out.append(_hour_window(day, analysis_hour))
    return out
