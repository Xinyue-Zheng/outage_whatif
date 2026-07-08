"""The three code-produced tables that are the agents' *entire* world
(closed book): claim board, dependency table, anchor digest.

Also renders them as stable text for the LLM prompts — citation
verification checks the agent's quotes against exactly these rendered
strings.
"""

from __future__ import annotations

from ..claims.model import CAPACITY, ClaimSet
from ..config import Config


def stake_pop(claim, subregions: dict, background, cfg: Config) -> float:
    """Population weight of a claim.  DESIGN-GAP: integrity claims carry a
    constant P0 stake (the design does not fix one)."""
    if claim.ctype in ("coverage", "robustness"):
        if claim.subject == "BG":
            return background.population
        sub = subregions.get(claim.subject)
        return sub.population if sub else 0.0
    if claim.ctype == CAPACITY:
        serves = claim.detail.get("serves", [])
        root = claim
        if claim.parent is not None:
            serves = []                     # children inherit the parent stake
        total = 0.0
        for sid in serves or root.detail.get("serves", []):
            if sid == "BG":
                total += background.population
            elif sid in subregions:
                total += subregions[sid].population
        return total
    return float(cfg.policy.P0)


def build_board(claims: ClaimSet, view, subregions: dict, background,
                price_map: dict, cfg: Config) -> list:
    """Claim board: one row per open claim (plus resolved ones for context is
    NOT included — the board is the spending surface)."""
    rows = []
    for c in sorted(claims.alive(), key=lambda c: c.cid):
        row = {
            "cid": c.cid, "type": c.ctype, "subject": c.subject,
            "state": c.state, "ticket": bool(c.ticket),
            "stake_pop": round(stake_pop(c, subregions, background, cfg), 1),
            "remedy": c.remedy,
            "cheapest_price": price_map.get(c.cid),
            "p_hat": None, "interval": None, "hourly_mean": None,
            "zone": None, "spike_frac": None, "top_share": None,
        }
        d = c.detail
        if c.ctype == "coverage":
            n, k = d.get("footprint_cells"), d.get("passing")
            if n:
                row["p_hat"] = round((k or 0) / n, 3)
            row["interval"] = d.get("interval")
            row["position"] = (f"{k}/{n} footprint cells pass, "
                               f"Wilson {d.get('interval')} vs theta={cfg.policy.theta}"
                               if n else "no footprint cells sampled yet")
            if d.get("unaffected"):
                row["position"] = "subregion outside target footprint (unaffected)"
        elif c.ctype == "capacity":
            row["hourly_mean"] = d.get("hourly_mean")
            row["zone"] = d.get("zone")
            row["spike_frac"] = d.get("spike_frac")
            if d.get("tier") == "15min":
                row["position"] = (f"15-min spike fraction {d.get('spike_frac')} "
                                   f"vs {cfg.policy.cap15_refute_frac}")
            elif d.get("hourly_mean") is not None:
                row["position"] = (f"hourly mean PRB {d.get('hourly_mean')} in "
                                   f"{d.get('zone')} (edge={d.get('support_edge')}, "
                                   f"pi_hi={cfg.policy.pi_hi})")
            else:
                row["position"] = "no PM held for the outage-matched window"
        elif c.ctype == "robustness":
            row["top_share"] = d.get("top_share")
            row["interval"] = d.get("interval")
            row["position"] = (f"top owner {d.get('top_owner')} share "
                               f"{d.get('top_share')}, Wilson {d.get('interval')} "
                               f"vs kappa={cfg.policy.kappa}"
                               if d.get("top_owner") else "no owner data yet")
        else:
            row["position"] = (f"{d.get('ring_cells', 0)} ring cells sampled, "
                               f"{d.get('contaminated', 0)} contaminated")
        rows.append(row)
    return rows


def build_digest(claims: ClaimSet, view, subregions: dict, background,
                 pm, owned_profiles: dict, calendar: dict, zones: dict,
                 ledgers: dict, width_history: dict, round_no: int) -> dict:
    """Anchor digest (code-generated)."""
    outage_hours = calendar.get("_hour_range", (10, 18))
    neighbors = {}
    for c in claims.by_type(CAPACITY):
        if c.parent is not None:
            continue
        site = c.subject
        measured = pm.hourly_mean(site)
        q15 = pm.q15.get(site)
        spike = (round(sum(v >= zones["pi_hi"] for v in q15) / len(q15), 3)
                 if q15 else None)
        prof_means = {}
        for (s, kind), prof in owned_profiles.items():
            if s != site:
                continue
            hrs = range(outage_hours[0], outage_hours[1])
            prof_means[kind] = round(
                sum(prof.hourly_mean[h] for h in hrs) / max(len(list(hrs)), 1), 3)
        if measured is not None:
            anchor, src = round(measured, 3), "in-case measurement"
        elif calendar.get("holiday") and "holiday_last_year" in prof_means:
            anchor, src = prof_means["holiday_last_year"], "holiday profile"
        elif "same_weekday" in prof_means:
            anchor, src = prof_means["same_weekday"], "same-weekday profile"
        else:
            anchor, src = None, "none (no history purchased, nothing measured)"
        neighbors[site] = {
            "anchor_mean": anchor, "anchor_source": src,
            "measured_hourly_mean": (round(measured, 3)
                                     if measured is not None else None),
            "measured_spike_frac": spike,
            "profile_window_means": prof_means,
            "serves": c.detail.get("serves", []),
        }

    subs = {}
    for sid in list(subregions) + ["BG"]:
        votes = view.votes_by_sid.get(sid, [])
        fp = [v for v in votes if v.in_footprint]
        subs[sid] = {
            "cells_sampled": len(votes),
            "footprint_cells": len(fp),
            "passing": sum(v.alt_ok for v in fp),
            "remaining_unsampled": len(view.unsampled_cells.get(sid, [])),
            "interval_width_trajectory": width_history.get(sid, []),
        }

    return {
        "calendar": {k: v for k, v in calendar.items() if not k.startswith("_")},
        "neighbors": neighbors,
        "subregions": subs,
        "zones": zones,
        "agents": {name: led.summary(round_no) for name, led in ledgers.items()},
    }


# ------------------------------------------------------------- text rendering
def render_board(board: list) -> str:
    lines = ["CLAIM BOARD (open + resolved-alive claims)",
             "cid | type | state | ticket | stake_pop | position | "
             "cheapest_action_price | remedy"]
    for r in board:
        lines.append(
            f"{r['cid']} | {r['type']} | {r['state']} | "
            f"{'TICKET' if r['ticket'] else 'no-ticket'} | {r['stake_pop']} | "
            f"{r.get('position', '')} | {r['cheapest_price']} | {r['remedy']}")
    return "\n".join(lines)


def render_deps(deps: list) -> str:
    lines = ["DEPENDENCY TABLE (lever=outcome => consequences)",
             "row_id | consequence | dead_tickets | savings"]
    for r in deps:
        lines.append(f"{r.row_id()} | {r.consequence} | "
                     f"{','.join(r.dead_tickets) or '-'} | {r.savings}")
    return "\n".join(lines)


def render_digest(digest: dict) -> str:
    lines = ["ANCHOR DIGEST"]
    c = digest["calendar"]
    lines.append(f"calendar: {c}")
    lines.append(f"zone constants: {digest['zones']}")
    lines.append("exit neighbors:")
    for site, nb in sorted(digest["neighbors"].items()):
        lines.append(f"  {site}: anchor_mean={nb['anchor_mean']} "
                     f"(source: {nb['anchor_source']}); "
                     f"measured_hourly_mean={nb['measured_hourly_mean']}; "
                     f"measured_spike_frac={nb['measured_spike_frac']}; "
                     f"profiles={nb['profile_window_means']}; "
                     f"serves={nb['serves']}")
    lines.append("subregions:")
    for sid, s in sorted(digest["subregions"].items()):
        lines.append(f"  {sid}: sampled={s['cells_sampled']} "
                     f"footprint={s['footprint_cells']} passing={s['passing']} "
                     f"remaining={s['remaining_unsampled']} "
                     f"width_trajectory={s['interval_width_trajectory']}")
    lines.append("agent ledgers:")
    for name, s in digest["agents"].items():
        lines.append(f"  {name}: {s}")
    return "\n".join(lines)


def render_menu(menu: list) -> str:
    lines = ["ACTION MENU (filtered)",
             "aid | kind | claim | price | quartile(1=cheapest..4=top) | "
             "worst-case follow-up | outcome buckets | description"]
    for a in menu:
        lines.append(f"{a.aid} | {a.kind} | {a.claim_cid} | {a.price} | "
                     f"Q{a.quartile} | {a.followup_price} | "
                     f"{'/'.join(a.buckets)} | {a.description}")
    return "\n".join(lines)
