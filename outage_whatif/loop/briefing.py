"""The briefing: the investigator's opening view of the round.

Plain text, ~1.5k tokens ceiling, stable field labels — the citation
validator checks verbatim substrings of exactly this rendering (plus this
turn's tool outputs).  Everything else the agent wants, it asks for through
the read-only tools.
"""

from __future__ import annotations


def claim_position(claim, cfg) -> str:
    """One-line evidence position of a claim (stable wording)."""
    d = claim.detail
    if claim.ctype == "coverage":
        if d.get("unaffected"):
            return "object outside target footprint (unaffected)"
        n, k = d.get("footprint_cells"), d.get("passing")
        if not n:
            return "no footprint cells sampled yet"
        return (f"{k}/{n} footprint cells pass, Wilson {d.get('interval')} "
                f"vs theta={cfg.policy.theta}")
    if claim.ctype == "capacity":
        if d.get("tier") == "15min":
            return (f"15-min spike fraction {d.get('spike_frac')} vs "
                    f"{cfg.policy.cap15_refute_frac}")
        if d.get("hourly_mean") is not None:
            return (f"hourly mean PRB {d.get('hourly_mean')} in "
                    f"{d.get('zone')} (edge={d.get('support_edge')}, "
                    f"pi_hi={cfg.policy.pi_hi})")
        return "no PM held for the outage-matched window"
    # robustness
    if d.get("top_owner"):
        return (f"top owner {d.get('top_owner')} share {d.get('top_share')}, "
                f"Wilson {d.get('interval')} vs kappa={cfg.policy.kappa}")
    return "no owner data yet"


def cheapest_remedy(claim, view, subregions, provider, cfg,
                    k_hours: int) -> tuple[str, float] | None:
    """(description, quote) of the cheapest known resolving purchase for an
    open claim — informative only; the agent still shapes its own request."""
    if claim.ctype in ("coverage", "robustness"):
        unsampled = view.unsampled_cells.get(claim.subject, [])
        n = min(cfg.densify_cells_per_round, len(unsampled))
        if n == 0:
            return None
        q = provider.quote("coverage", n_points=n)
        return (f"densify {n} unsampled cells", round(q, 2))
    if claim.ctype == "capacity":
        if claim.drilled:
            return None                      # children carry their remedies
        if claim.detail.get("tier") in (None, "none"):
            q = provider.quote("pm", granularity="hourly", n_entities=1,
                               hours=k_hours)
            return (f"pm_hourly {claim.subject} over {k_hours} matched hours",
                    round(q, 2))
        q = provider.quote("pm", granularity="15min", n_entities=1,
                           hours=k_hours)
        return (f"pm_15min {claim.subject} over {k_hours} matched hours",
                round(q, 2))
    return None


def render_briefing(runner, gaps: list, view) -> str:
    cfg = runner.cfg
    k = cfg.policy.comparable_days_k
    lines = []
    a = lines.append

    flags = runner.spec.calendar_flags(cfg)
    a(f"ROUND {runner.round_no} — case {runner.spec.name}, "
      f"target {runner.target}")
    a(f"BUDGET: initial={runner.spec.budget:.2f} "
      f"spent={runner.ledger.spent:.2f} remaining={runner.remaining:.2f}")
    a(f"ANALYSIS HOUR: {runner.analysis_hour:02d}:00 "
      f"({flags['weekday']}, {flags['day_type']}; k={k} matched days; "
      f"rule: {runner.spec.analysis_hour_rule})")

    a("TICKETED CLAIMS (flip test says spending can matter):")
    ticketed = [c for c in runner.claims.open() if c.ticket]
    if not ticketed:
        a("  none")
    for c in sorted(ticketed, key=lambda c: c.cid):
        rem = cheapest_remedy(c, view, runner.subregions(), runner.provider,
                              cfg, k)
        rem_s = f"{rem[0]} ~ {rem[1]}" if rem else "no known remedy"
        a(f"  {c.cid} | {c.ctype} | {claim_position(c, cfg)} | "
          f"remedy: {rem_s}")

    a("OPEN GAPS (audit):")
    if not gaps:
        a("  none")
    for g in gaps:
        a(f"  {g.line()}")

    rb = runner.book.residual_bound(runner.registry, runner.raster, cfg)
    trend = ", ".join("?" if v is None else f"{v:.3f}"
                      for v in runner.residual_history[-4:]) or "-"
    a(f"RESIDUAL BOUND: "
      f"{'unknown (demand ledger incomplete)' if rb is None else rb} "
      f"(rho_residual={cfg.policy.rho_residual}); trend: {trend}")

    last = runner.agent_ledger.last_reconciled()
    if last:
        verdict = ("neutral (mid)" if last["hit"] is None
                   else "HIT" if last["hit"] else "MISS")
        a(f"LAST PURCHASE: {last['item']} predicted={last['predicted']} "
          f"actual={last.get('actual')} -> {verdict} "
          f"(confidence={last['grade']})")
    else:
        a("LAST PURCHASE: none reconciled yet")

    hr = runner.agent_ledger.hit_rates()
    a("HIT RATES: " + "; ".join(
        f"{g}: {v['hits']}/{v['scored']}" +
        (f" ({v['rate']})" if v["rate"] is not None else "")
        for g, v in hr.items()))

    a(f"NOTEBOOK (last line): "
      f"{runner.notebook[-1] if runner.notebook else '(empty)'}")
    return "\n".join(lines)
