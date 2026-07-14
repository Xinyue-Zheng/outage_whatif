"""Per-case Markdown report (investigator architecture).

Keeps the mandatory conditionality block, the per-object verdict table,
unverified assumptions, policy constants, and the budget/agent ledgers;
adds the demand-closure statement (residual bound) and the round-by-round
briefing history (replacing the old board/dependency-table sections)."""

from __future__ import annotations

import dataclasses

DECLARED_BOUNDARY = (
    "Declared boundary: handover misconfiguration, transport bottlenecks, "
    "and all other factors absent from the inputs are outside every "
    "conclusion this system can draw.")

P_MIN_DISCLOSURE = (
    "Raster settlements under P_min are never offered as candidate pins "
    "and were not individually verified; their demand is covered only "
    "through the cell localization book (residual bound).")


def render_report(runner, verdict, result) -> str:
    cfg = runner.cfg
    pol = cfg.policy
    lines = []
    a = lines.append

    a(f"# What-if outage report — case {runner.spec.name}, "
      f"target {runner.target}")
    a("")
    a(f"*Outage window:* {runner.spec.window.start.isoformat()} to "
      f"{runner.spec.window.end.isoformat()} "
      f"({runner.spec.calendar_flags(cfg)['weekday']}, "
      f"{runner.spec.calendar_flags(cfg)['day_type']})")
    a("")
    h = runner.analysis_hour
    a("## Conditionality of this verdict")
    a(f"**This run assessed analysis hour {h:02d}:00.** "
      f"The verdict holds for that hour only. Other hours of the ticket "
      f"window ({runner.spec.window.start.isoformat()} to "
      f"{runner.spec.window.end.isoformat()}) were not verified in this "
      f"run.")
    rule = runner.spec.analysis_hour_rule
    if rule.startswith("[POLICY]"):
        a(f"- **[POLICY] applied** — analysis_hour was not specified by the "
          f"ticket; selected by the default rule: "
          f"{rule.removeprefix('[POLICY] default rule: ')}.")
    else:
        a(f"- analysis_hour selection: {rule}.")
    a(f"- Capacity evidence basis: k={pol.comparable_days_k} matched "
      f"occurrences of this hour on comparable days "
      f"(same clock-hour and weekday / holiday class; known outages "
      f"excluded).")
    a("")
    a("## Overall verdict")
    a(f"**{verdict.overall}**")
    a("")
    a(f"Stop reason: {result.stop_reason} after {result.rounds} rounds; "
      f"spend {result.spent} of budget {result.budget}.")
    a("")

    # ---- demand closure
    rb = runner.book.residual_bound(runner.registry, runner.raster, cfg)
    a("## Demand closure")
    if rb is None:
        a(f"- Residual bound: **unknown** — the demand ledger (cell-level "
          f"busy-window KPI for the target) was never completed; full "
          f"absorption is not declarable.")
    else:
        ok = rb <= pol.rho_residual
        a(f"- Residual bound: **{rb}** of the target's busy-window traffic "
          f"is not accounted for by registered demand objects "
          f"({'within' if ok else 'ABOVE'} rho_residual="
          f"{pol.rho_residual}).")
    rm = runner.book.residual_map(runner.registry, runner.raster, cfg)
    for cell, row in sorted(rm.items()):
        a(f"  - {cell}: T={row['T']} status={row['status']} "
          f"units={row['n_units']} unmapped_points="
          f"{len(row['unmapped_points'])}")
    a("- Objects: " + "; ".join(
        f"{o.id} ({o.state}; {'+'.join(o.provenance)})"
        for o in sorted(runner.registry.all(), key=lambda o: o.id)))
    a("")

    a("## Per-object verdicts and deciding claims")
    a("")
    a("| object | pop | tier | severity | bottleneck | deciding evidence |")
    a("|---|---|---|---|---|---|")
    pops = runner._populations()
    for sid, sv in sorted(verdict.per_subregion.items()):
        deciding = []
        for prefix in ("COV", "ROB"):
            cid = f"{prefix}:{sid}"
            if cid in runner.claims:
                c = runner.claims.get(cid)
                iv = c.detail.get("interval")
                deciding.append(f"{cid}:{c.state}"
                                + (f" {iv}" if iv else ""))
        for c in runner.claims.by_type("capacity"):
            if c.parent is None and sid in c.detail.get("serves", []):
                pos = (f" mean={c.detail.get('hourly_mean')}"
                       if c.detail.get("hourly_mean") is not None else "")
                pos += (f" spike_frac={c.detail.get('spike_frac')}"
                        if c.detail.get("spike_frac") is not None else "")
                deciding.append(f"{c.cid}:{c.state}{pos}")
        bt, bs = sv.bottleneck_type, sv.bottleneck_subject
        a(f"| {sid} | {round(pops.get(sid, 0))} | {sv.tier} | {sv.severe} | "
          f"{(bt or '-') + (' (' + bs + ')' if bs else '')} | "
          f"{'; '.join(deciding) or '-'} |")
    a("")

    if result.unverified_assumptions:
        a("## Unverified assumptions (conservative defaults at budget "
          "exhaustion)")
        for u in result.unverified_assumptions:
            a(f"- `unverified_assumption` — {u}")
        a("")

    a("## Policy rules in force ([POLICY] — advisor sign-off required)")
    for f in dataclasses.fields(pol):
        a(f"- {f.name} = {getattr(pol, f.name)}")
    a(f"- calibration support-zone edge = {runner.support_edge} "
      f"(hourly tier {'may' if runner.support_edge is not None else 'may NOT'}"
      f" declare support)")
    a("")

    a("## Disclosures")
    a(f"- {P_MIN_DISCLOSURE}")
    a(f"- {DECLARED_BOUNDARY}")
    tgt = getattr(runner, "target_rrc", None)
    a(f"- Target baseline RRC (reporting/validation only): "
      f"{('mean ' + str(round(sum(tgt) / len(tgt), 1)) + ' conn/h') if tgt else 'not purchased (budget)'}.")
    a("")

    a("## Budget ledger")
    a("")
    a("| round | action | kind | price | purpose | target |")
    a("|---|---|---|---|---|---|")
    for e in result.ledger_entries:
        a(f"| {e['round']} | {e['aid']} | {e['kind']} | {e['price']} | "
          f"{e['purpose']} | {e['claim'] or '-'} |")
    a(f"\n**Total spent: {result.spent} / {result.budget}**")
    a("")

    a("## Investigator ledger")
    s = result.agent_summary
    a(f"- hit rate per grade: {s['hit_rate_per_grade']}")
    a(f"- consecutive misses: {s['consecutive_misses']}")
    a(f"- selection bias: {s['selection_bias_note']}")
    if result.incidents:
        a("")
        a(f"## Protocol incidents ({len(result.incidents)})")
        for i in result.incidents:
            a(f"- R{i['round']}: {i['incident']}")
    a("")
    a("## Event log")
    for e in result.events:
        a(f"- {e}")
    a("")

    a("## Briefing history")
    briefings = [t for t in runner.trace if t.get("node") == "briefing"]
    for t in briefings:
        a("")
        a("```")
        a(t.get("briefing", ""))
        a("```")
    return "\n".join(lines)
