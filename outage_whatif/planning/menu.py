"""Action menu (deterministic).

Each round, code enumerates the affordable ways to spend the next unit of
budget: one action per open claim's named remedy, plus judgment-firming
profile purchases.  Every action carries:

* price (from the price function, via provider.quote);
* price quartile *within the current menu* — "cheap"/"expensive" exist only
  as quartiles;
* its finite outcome-bucket space derived from the adjudication criteria;
* the worst-case follow-up price forced by an ambiguous predicted bucket
  (decisiveness accounting, escalation_mode=worst_case).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..claims.model import CAPACITY, COVERAGE, INTEGRITY, ROBUSTNESS, ClaimSet
from ..config import Config
from .sampling import background_grid_points, densify_cells

# outcome-bucket spaces, derived from the adjudication criteria
BUCKETS = {
    "coverage_densify": ["clears_theta", "still_straddling", "falls_below_theta"],
    "robustness_densify": ["diverse", "still_ambiguous", "concentrated"],
    "bg_sweep": ["clears_theta", "still_straddling", "falls_below_theta"],
    "pm_hourly": ["support_zone", "middle_zone", "refute_zone"],
    "pm_15min": ["support", "refute"],
    "ring_sample": ["clean", "contaminated", "still_undecided"],
    "profile": ["anchor_confirms", "anchor_shifts"],
}
# the ambiguous bucket of each kind (forces its follow-up, worst-case)
AMBIGUOUS = {
    "coverage_densify": "still_straddling",
    "robustness_densify": "still_ambiguous",
    "bg_sweep": "still_straddling",
    "pm_hourly": "middle_zone",
    "ring_sample": "still_undecided",
}


@dataclass
class Action:
    aid: str
    kind: str
    claim_cid: str
    price: float
    params: dict = field(default_factory=dict)
    buckets: list = field(default_factory=list)
    followup_price: float = 0.0        # forced by the ambiguous bucket
    quartile: int = 0                  # 1 (cheapest) .. 4 (top), within menu
    description: str = ""

    def signature(self) -> tuple:
        """Identity for the duplicate-query check."""
        if self.kind in ("pm_hourly", "pm_15min"):
            p = self.params
            return (self.kind, tuple(p["entities"]), p["granularity"],
                    p["window_key"])
        if self.kind == "profile":
            return (self.kind, self.params["site"], self.params["profile_kind"])
        # sampling actions target fresh cells/points each time -> unique
        return (self.kind, self.aid)


def _assign_quartiles(actions: list) -> None:
    if not actions:
        return
    prices = sorted(a.price for a in actions)
    n = len(prices)
    for a in actions:
        rank = prices.index(a.price)
        a.quartile = min(int(4 * rank / n) + 1, 4)


def build_menu(claims: ClaimSet, view, subregions: dict, background,
               raster, boundary, provider, window, cfg: Config,
               rng: np.random.Generator, round_no: int,
               owned_profiles: set, purchased: set) -> list:
    """Menu of actions for the current round.  ``purchased`` holds action
    signatures already bought (duplicate queries never enter the menu);
    ``owned_profiles`` holds (site, kind) pairs."""
    acts: list[Action] = []
    # capacity evidence = k matched occurrences of the analysis hour on
    # comparable days; PM price formula unchanged, hours = k matched hours
    k_hours = cfg.policy.comparable_days_k
    win_key = (window.start.isoformat(), window.end.isoformat(),
               "matched", window.analysis_hour, k_hours)

    def pm_action(kind: str, entity: str, gran: str, cid: str) -> Action | None:
        price = provider.quote("pm", granularity=gran, n_entities=1,
                               hours=k_hours)
        a = Action(
            aid=f"R{round_no}:{kind}:{entity}", kind=kind, claim_cid=cid,
            price=price,
            params={"entities": [entity], "granularity": gran,
                    "window_key": win_key, "metric": "prb_util"},
            buckets=list(BUCKETS[kind]),
            followup_price=(provider.quote("pm", granularity="15min",
                                           n_entities=1, hours=k_hours)
                            if kind == "pm_hourly" else 0.0),
            description=f"{gran} PRB for {entity} at the analysis hour "
                        f"({window.analysis_hour}:00) over {k_hours} "
                        f"matched comparable days")
        return None if a.signature() in purchased else a

    for c in claims.open():
        if c.ctype in (COVERAGE, ROBUSTNESS):
            sid = c.subject
            if sid == "BG":
                pts = background_grid_points(boundary, cfg, rng)
                pts = pts[: max(cfg.background_pts_per_tile * 4, 6)]
                if pts:
                    acts.append(Action(
                        aid=f"R{round_no}:bg_sweep:{c.cid}", kind="bg_sweep",
                        claim_cid=c.cid,
                        price=provider.quote("coverage", n_points=len(pts)),
                        params={"points": pts},
                        buckets=list(BUCKETS["bg_sweep"]),
                        followup_price=provider.quote("coverage", n_points=len(pts)),
                        description=f"background-grid sweep, {len(pts)} points"))
                continue
            sub = subregions.get(sid)
            unsampled = view.unsampled_cells.get(sid, [])
            if sub is None or not unsampled:
                continue
            kind = ("coverage_densify" if c.ctype == COVERAGE
                    else "robustness_densify")
            pts = densify_cells(sub, raster, unsampled, cfg, rng)
            if not pts:
                continue
            acts.append(Action(
                aid=f"R{round_no}:{kind}:{c.cid}", kind=kind, claim_cid=c.cid,
                price=provider.quote("coverage", n_points=len(pts)),
                params={"points": pts},
                buckets=list(BUCKETS[kind]),
                followup_price=provider.quote("coverage", n_points=len(pts)),
                description=f"densify {len(pts)} unsampled evidence cells in {sid}"))
        elif c.ctype == CAPACITY:
            if c.drilled:
                continue                    # children carry their own actions
            entity = c.subject
            tier = c.detail.get("tier")
            if tier in (None, "none"):
                a = pm_action("pm_hourly", entity, "hourly", c.cid)
            else:                           # hourly held, middle zone
                a = pm_action("pm_15min", entity, "15min", c.cid)
            if a:
                acts.append(a)
        elif c.ctype == INTEGRITY:
            sector = int(c.subject)
            k = cfg.integrity_min_cells + 1
            pts = boundary.ring_points(sector, k, rng)
            acts.append(Action(
                aid=f"R{round_no}:ring_sample:{c.cid}", kind="ring_sample",
                claim_cid=c.cid,
                price=provider.quote("coverage", n_points=len(pts)),
                params={"points": pts, "sector": sector},
                buckets=list(BUCKETS["ring_sample"]),
                followup_price=provider.quote("coverage", n_points=len(pts)),
                description=f"sample {len(pts)} ring points in sector {sector}"))

    # judgment-firming profile purchases (cross-modal, dependency-licensed)
    from ..provider.simulator import day_type
    is_holiday = day_type(window.start.date(), set(cfg.holidays)) == "holiday"
    for c in claims.by_type(CAPACITY):
        if c.parent is not None or not c.alive:
            continue
        site = c.subject
        kinds = ["same_weekday", "matched_hour"] \
            + (["holiday_last_year"] if is_holiday else [])
        for pk in kinds:
            if (site, pk) in owned_profiles:
                continue
            desc = (f"analysis-hour ({window.analysis_hour}:00) distribution "
                    f"over a 12-week horizon for {site} "
                    f"— judgment-firming, changes no claim directly"
                    if pk == "matched_hour" else
                    f"historical profile ({pk}) for {site} "
                    f"— judgment-firming, changes no claim directly")
            acts.append(Action(
                aid=f"R{round_no}:profile:{site}:{pk}", kind="profile",
                claim_cid=c.cid,
                price=provider.quote("profile", profile_kind=pk),
                params={"site": site, "profile_kind": pk,
                        "hour": window.analysis_hour},
                buckets=list(BUCKETS["profile"]),
                description=desc))

    acts = [a for a in acts if a.signature() not in purchased]
    _assign_quartiles(acts)
    return acts


def cheapest_price_map(actions: list) -> dict:
    """claim cid -> price of its cheapest resolving action (profiles are
    judgment-firming, not resolving, and are excluded)."""
    out: dict[str, float] = {}
    for a in actions:
        if a.kind == "profile":
            continue
        if a.claim_cid not in out or a.price < out[a.claim_cid]:
            out[a.claim_cid] = a.price
    return out
