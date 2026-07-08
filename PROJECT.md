# PROJECT.md — canonical system description

Describes the system AS IMPLEMENTED. Where older spec text and the code
disagree, the code wins; known disagreements are listed in §8 (drift
notes), not silently resolved. Every claim here is checkable against the
code.

## 1. Problem & question

A target eNodeB in a rural sparse network will be switched off during a
ticketed outage window (possibly many hours). One run answers one
conditional question: **if the outage's effect is assessed at a selected
`analysis_hour` within the ticket window, can the neighboring sites
absorb the target's users?** One run = one (case, analysis_hour) pair.

The answer is qualitative — per populated settlement and overall:
`fully absorbable` / `locally degraded` / `severe hole exists`. The
system verifies **necessary conditions** for absorption as three-valued
claims — coverage, capacity, robustness, integrity — and never predicts
how traffic would actually redistribute; a violated necessary condition
refutes absorption, verified conditions support it.

Every data item is priced (coverage probes, PM/KPI series, historical
profiles) against a finite per-case budget B, so this is a
budget-constrained sequential query-decision problem: each round decides
what the next unit of budget buys.

## 2. Design principles

- Claims are three-valued (supported / refuted / undecided); *undecided*
  is a purchasing decision — spend to resolve it, or stop and disclose.
- Everything enumerable is deterministic code: adjudication, ordering,
  arithmetic, pricing, verdict.
- Exactly one judgment is delegated to agents: the prior likelihood of a
  query's outcome before it is run.
- Exactly two LLM call sites exist (seat 1, seat 2) — nowhere else.
- Rule baselines are swappable into either seat; agent value is an
  experimental hypothesis (`rule/rule` vs `llm/llm`), not a premise.
- Definitional rules and [POLICY] rules are kept separate; [POLICY]
  constants (`config.py` Policy block) require advisor sign-off.
- Declared boundary: handover misconfiguration, transport bottlenecks,
  and everything else invisible to the inputs is outside every
  conclusion (stated verbatim in every report).

## 3. Current architecture

Orchestration is a LangGraph StateGraph (`loop/graph.py`); one round =
one graph invocation (`CaseRunner.step()`); `run()` loops rounds. The
topology is locked by `tests/test_graph_topology.py`. Nodes:

| node | responsibility |
|---|---|
| `advance` | round counter, max-round safety stop, seeded RNG |
| `adjudicate_lifecycle` | re-adjudicate all claims from evidence; claim spawn/kill/split |
| `assess` | build priced action menu; flip-test tickets; verdict; dependency table; route blocked runs |
| `expand_boundary` | forced deterministic boundary expansion + resampling (no agents; unreachable in static-square mode) |
| `stop_check` | stop rules: verdict stable, budget exhausted, nothing can flip; idle-round limit |
| `build_tables` | render the agents' entire world: claim board, dependency table, anchor digest |
| `seat1` **(LLM seat)** | Agent 1 grades every ticketed item; code derives the ordering; divergence vs baseline logged |
| `seat2` **(LLM seat)** | Agent 2 picks one purchase; guardrail + mechanical checks; retry → rule fallback → cheapest compliant sweep |
| `execute` | pay, store returned data, re-adjudicate, reconcile prediction ledgers |

Graph state (`RoundState`) carries intra-round intermediates only: `rng`,
`view`, `menu`, `price_map`, `deps`, `affordable`/`affordable_ticketed`,
`board`, `digest`, `out1`, `candidates`, `menu2`, `out2`, `stop`, `goto`.
Cross-round state lives on `CaseRunner` (claims, ledgers, boundary,
budget, matched windows).

Closed-book rule: seat 1 sees exactly the claim board, dependency table,
and anchor digest; seat 2 sees the candidate ordering, the menu filtered
to it, the digest, zone constants, and the dependency table. Nothing
else.

Validation/retry/fallback: every LLM response is mechanically validated
(schema completeness, verbatim citations, re-verified arithmetic) — one
retry with the reason, then that seat falls back to its rule baseline for
the round. The code guardrail runs after Agent 2 only (top-quartile price
requires grade=high unless a prerequisite resolved cheaply). Each agent
has a two-consecutive-miss fuse that routes it to its baseline for one
round. There is NO critic LLM: duplicate/contradiction checks are code
table-lookups, and the off-menu directed-probe channel is closed
(`engine.py`, MECHANICAL-CHECKS EXTENSION POINT).

## 4. Key mechanisms

**Flip test & tickets.** After each adjudication pass, every open claim
is flipped to supported and to refuted; if the verdict differs, the claim
holds a ticket. Only ticketed claims justify spending — budget on an
unticketed claim cannot change the answer.

**Dependency table.** For each ticketed outcome, the savings unlocked if
it lands that way (queries that stop being necessary). Priced from the
cheapest resolving action per claim; recomputed every round.

**Agent 1 (prioritization).** Emits one grade in {high, mid, low} per
ticketed item with a verbatim citation from the tables (fabricated
citations are rejected) and an optional one-step clue adjustment
(named clues include holiday flags, matched_hour_spread, busy_hour_flag).
Code computes the ordering from the grades — per claim: grade-weighted
population stake plus grade-weighted dependency savings, divided by the
cheapest resolving price; the ordering is a theorem of the stated grades.

**Agent 2 (action choice).** Predicts an outcome bucket + grade for the
candidates, with worst-case escalation arithmetic (effective cost =
sticker + follow-up forced by the predicted bucket; re-verified by code)
required to pick any non-cheapest action, an optional judgment-firming
profile purchase, and a mandatory contingency line for every bucket in
the chosen action's outcome space.

**Ledger reconciliation.** Every purchase's actual outcome bucket is
reconciled against Agent 2's prediction immediately (profiles: scored
next round on whether the relevant grade moved). Agent 1's grades are
reconciled when the lever's query executes. Per-grade hit rates and the
fuse state are shown back to the agents in the digest. Known selection
bias (documented): only chosen rows reconcile.

## 5. Current parameter decisions

| parameter | value | [POLICY] | meaning |
|---|---|---|---|
| `static_area_km` | 0 default; **30 for real-data runs** | no (Config) | >0: start area is a fixed square (exact containment), centered on the target; no integrity ring/claims, no expansion. 0: adaptive circle R0 = 0.75 × median 6-NN distance with integrity correction loop |
| `analysis_hour` | per run | — | must lie inside the ticket window (validated at runner init; invalid → case rejected); stamped into run ID (`case01_h17_...`) and report |
| `analysis_hour_default_rule` | busiest-profile else midpoint | yes | fires when the ticket omits the hour; the report flags which rule fired |
| `comparable_days_k` | 4 | yes | capacity evidence = k matched occurrences of the analysis hour: same clock-hour + weekday, most recent k weeks; holiday outages match holiday-class days; `known_outage_dates` excluded. Hourly tier = mean of k; 15-min tier = spike fraction over 4k=16 bins (≥2 spiking bins refute) |
| `theta` | 0.90 | yes | coverage pass proportion (Wilson-tested; exact census decides when complete) |
| `pi_hi` | 0.85 | yes | PRB utilisation treated as "no headroom" |
| `kappa` | 0.60 | yes | max top-owner share of best alternatives (robustness) |
| `sigma` | 0.20 | yes | major-exit share: neighbor is a genuine exit iff best alternative for ≥ σ of footprint cells |
| `P_min` | 50 | yes | settlements below this population get no individual claims (absorbed into background; disclosed) |
| `P0` | 200 | yes | severe-hole population line |
| `cap15_refute_frac` | 0.10 | yes | 15-min tier refute threshold |
| `calib_false_pass_max` | 0.05 | yes | max false-pass rate for the calibrated hourly support edge |
| `z` | 1.96 | no | Wilson score |
| `evidence_cell_m` | 300 | no | effective-evidence cells; all coverage/robustness statistics count cells, never raw points |
| `escalation_mode` | `worst_case` | no (Config) | `weighted` is reserved, not implemented |

## 6. Data & evaluation

All paid data flows through the `DataProvider` interface
(`provider/interface.py`): `topology`, `population_raster`,
`query_coverage`, `query_pm` (+ `query_pm_matched` default that
concatenates the k matched hours), `buy_profile(site, kind, hour=None)`,
`quote`. The simulator (`provider/simulator.py`) implements it today; a
real-platform `FileProvider` implements the same seam later
(COPILOT_PROMPT.md). The LLM transport is LangChain → Ollama
(`agents/llm.py`; model/host in config; tests use `MockLLM`, no server
needed).

Prices come from one encapsulated function (`provider/pricing.py`);
"cheap"/"expensive" exist only as quartiles within a round's menu, never
as data-type properties. PM is priced over the k matched hours.

Evaluation: 10 simulated cases (2 calibration + 8 blind; case files pin
2 busy-hour and 2 off-peak analysis selections, the harness defaults the
rest to the window's busiest diurnal hour). The swap harness runs arms on
identical code and budget: headline `rule/rule` vs `llm/llm` on the blind
cases; mixed ablations on the calibration cases; an unlimited-budget
oracle run per case gives the ceiling. Departures of an LLM seat from its
baseline are logged first-class (divergence log). Ground truth is
computed from the simulator's hidden parameters with perfect information
at the matched analysis hours, using the same necessary-condition
semantics as the claim system (see drift note 3). Each run writes
`report.md` (with a mandatory conditionality block naming the assessed
hour), `ledger.json`, `trace.jsonl` (every node decision and every
queried datum, labeled by round and purpose), and `round_graph.mmd`.

## 7. Status & extension points

Implemented and tested (71 tests, no LLM server required): geometry and
segmentation, claims/adjudication/lifecycle, verdict + flip tests,
planning/menu/calibration (matched-hour, `calib-v2`), the LangGraph round
loop, rule baselines, LLM seats with validators, swap harness + metrics,
per-hour analysis, static-square mode, run tracing.

Not implemented / never run:
- the `llm/llm` arm has never executed (no Ollama server on the dev
  host); `runs/` holds `rule/rule` and `zonedist/rule` results;
- `FileProvider` (real-data adapter) is not written — task spec in
  COPILOT_PROMPT.md;
- hour-sweep runner: marked `EXTENSION POINT (hour sweep)` in
  `eval/harness.py::run_case` — iterate (case, analysis_hour) pairs;
- critic reinstatement: marked `MECHANICAL-CHECKS EXTENSION POINT` in
  `loop/engine.py::_mechanical_checks`;
- weighted escalation mode: reserved in config (`worst_case | weighted`).

`# DESIGN-GAP` markers (verbatim inventory, README has details):
`config.py` illustrative holiday calendar; `planning/sampling.py`
population-proportional allocation realised as one cell per P0/8;
`loop/tables.py` integrity claims carry a constant P0 stake;
`claims/lifecycle.py` capacity drill-down trigger = stuck in the hourly
middle zone ≥ 2 rounds; `claims/adjudicate.py` 30% footprint-share
unaffected rule; `provider/pricing.py` requested points proxy
area×density; `agents/ledger.py` one-round fuse penalty duration;
`provider/simulator.py` ground truth measures recovery of truth, not the
physical outcome of an outage.

## 8. Drift notes (spec text vs code — code wins)

1. **Start area.** Older notes call the 30 km × 30 km square "the" start
   area and "a [POLICY] constant". In code, `static_area_km` is a plain
   Config field (not in the Policy block) defaulting to **0**, i.e. the
   adaptive R0 circle; the square activates only when a run sets it
   (intended for real-data runs). The simulator cases still run on the
   circle.
2. **Default-hour rule.** The [POLICY] rule says "busiest hour per the
   target's historical profile if already held, else midpoint". At runner
   init no profile is ever held, so in-run defaulting always lands on the
   midpoint; the busiest branch is reachable only by passing a profile
   explicitly. Eval-side busiest-hour selection lives in the harness
   (`select_eval_hour`), not in this rule.
3. **"Ground truth from RRC-delta."** Not what the code does: ground
   truth uses PRB-based necessary-condition semantics (coverage pass
   share; 15-minute PRB spike fraction at the matched hours). The
   target's RRC baseline is purchased at stop for reporting/validation
   only.
4. **"Scout-model rule promotion" extension point.** No such marker or
   mechanism exists in the code.
