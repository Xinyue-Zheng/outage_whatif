"""Per-case Markdown report (Section 11 of the design)."""

from __future__ import annotations

import dataclasses

DECLARED_BOUNDARY = (
    "Declared boundary: handover misconfiguration, transport bottlenecks, "
    "and all other factors absent from the inputs are outside every "
    "conclusion this system can draw.")

P_MIN_DISCLOSURE = "Settlements under P_min were not individually verified."


def render_report(runner, verdict, result) -> str:
    cfg = runner.cfg
    pol = cfg.policy
    lines = []
    a = lines.append

    a(f"# What-if outage report — case {runner.spec.name}, "
      f"target {runner.target}")
    a("")
    a(f"*Arm:* `{result.arm}` — *outage window:* "
      f"{runner.spec.window.start.isoformat()} to "
      f"{runner.spec.window.end.isoformat()} "
      f"({runner.spec.calendar_flags(cfg)['weekday']}, "
      f"{runner.spec.calendar_flags(cfg)['day_type']})")
    a("")
    h = runner.analysis_hour
    a(f"## Conditionality of this verdict")
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
    a(f"- Capacity evidence basis: k={cfg.policy.comparable_days_k} matched "
      f"occurrences of this hour on comparable days "
      f"(same clock-hour and weekday / holiday class; known outages "
      f"excluded).")
    a("")
    a("## Overall verdict")
    a(f"**{verdict.overall}**"
      + (" — RUN BLOCKED" if verdict.blocked else ""))
    a("")
    a(f"Stop reason: {result.stop_reason} after {result.rounds} rounds; "
      f"spend {result.spent} of budget {result.budget}.")
    a("")

    a("## Per-subregion verdicts and deciding claims")
    a("")
    a("| subregion | pop | tier | severe | bottleneck | deciding evidence |")
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
        a(f"| {sid} | {round(pops.get(sid, 0))} | {sv.tier} | "
          f"{'yes' if sv.severe else 'no'} | "
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
    a(f"- {P_MIN_DISCLOSURE} "
      f"({runner.background.absorbed_small_settlements} settlement(s), "
      f"{round(runner.background.absorbed_small_population)} people absorbed "
      f"into the background region, which the background grid still covers.)")
    a(f"- {DECLARED_BOUNDARY}")
    a(f"- Boundary expansions performed: {result.boundary_expansions}.")
    tgt = getattr(runner, "target_rrc", None)
    a(f"- Target baseline RRC (reporting/validation only): "
      f"{('mean ' + str(round(sum(tgt) / len(tgt), 1)) + ' conn/h') if tgt else 'not purchased (budget)'}.")
    a("")

    a("## Budget ledger")
    a("")
    a("| round | action | kind | price | purpose | claim served |")
    a("|---|---|---|---|---|---|")
    for e in result.ledger_entries:
        a(f"| {e['round']} | {e['aid']} | {e['kind']} | {e['price']} | "
          f"{e['purpose']} | {e['claim'] or '-'} |")
    a(f"\n**Total spent: {result.spent} / {result.budget}**")
    a("")

    a("## Agent ledgers")
    for name, s in result.agent_summaries.items():
        a(f"### {name}")
        a(f"- hit rate per grade: {s['hit_rate_per_grade']}")
        a(f"- consecutive misses: {s['consecutive_misses']}; "
          f"fuse trips: {s['fuse_trips']}")
        a(f"- selection bias: {s['selection_bias_note']}")
    if result.divergence_log:
        a("")
        a(f"## Divergence log ({len(result.divergence_log)} departures from "
          f"baseline)")
        for d in result.divergence_log:
            a(f"- R{d['round']} {d['seat']}: chose {d['llm_choice']} over "
              f"baseline {d['baseline_choice']} (grade={d.get('grade')}) — "
              f"{d.get('rationale', '')}")
    a("")
    a("## Event log")
    for e in result.events:
        a(f"- {e}")
    return "\n".join(lines)
