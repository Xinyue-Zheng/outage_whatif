# PROJECT.md — canonical system description

Describes the system AS IMPLEMENTED after the migration to the
investigator architecture (specified in `outage_whatif_design_final.md`;
see drift note 1 — that document is not present in this repository, and
the migration brief served as the working spec).  Where older text and the
code disagree, the code wins; known disagreements are in §8.

## 1. Problem & question

A target eNodeB in a rural sparse network will be switched off during a
ticketed outage window (possibly many hours). One run answers one
conditional question: **if the outage's effect is assessed at a selected
`analysis_hour` within the ticket window, can the neighboring sites
absorb the target's users?** One run = one (case, analysis_hour) pair.

The answer is qualitative — per demand object and overall:
`fully absorbable` / `locally degraded` / `severe hole exists` /
`undecided/qualified`. The system verifies **necessary conditions** for
absorption as three-valued claims — coverage, capacity, robustness — and
never predicts how traffic would actually redistribute.

Every data item is priced against a finite per-case budget B, so this is
a budget-constrained sequential query-decision problem: each round one
investigator agent decides what the next unit of budget buys, and a
deterministic gate decides whether that spend is admissible.

## 2. Design principles

- Claims are three-valued (supported / refuted / undecided); *undecided*
  is a purchasing decision — spend to resolve it, or stop and disclose.
- Everything enumerable is deterministic code: adjudication, arithmetic,
  pricing, the verdict, the flip test, the audit, the gate.
- Exactly one judgment is delegated to the agent: the prior likelihood of
  a query's outcome (predicted bucket + confidence grade).
- Exactly ONE LLM call site exists: the investigator seat. There is no
  second seat, no rule baseline in a seat, and no fallback seat — a
  non-compliant round is skipped and logged.
- Demand is a set of explicit OBJECTS (hypotheses), not the raster: the
  population raster only generates candidate pins. Demand the raster
  misses is caught by the cell localization book (residual mechanism).
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
| `adjudicate_lifecycle` | object confirmations; re-adjudicate all claims; CAP claim spawn/kill |
| `assess` | flip-test tickets; verdict; audit (gap list) — no menu, no dependency table |
| `stop_check` | stop rules (see §4); idle-round guard |
| `briefing` | render the agent's opening view (stable labels, ~1.5k tokens) |
| `investigator` **(LLM seat)** | JSON tool loop: read-only tools, then ONE committing action |
| `gate` | the generalized spend gate; denial feeds back for a single retry |
| `execute` | pay, store data, update the demand layer, re-adjudicate |
| `reconcile` | predicted vs actual outcome bucket; hit-rate ledger |

There is **no initial sampling phase**: the round-zero audit (demand
ledger absent, every object hypothesized) is what makes exploration
fundable. The ~8 suggested random probe locations are generated at setup
and surfaced by the audit as a suggested remedy — never auto-executed.

**Demand layer** (`demand/`): `ObjectRegistry` holds `DemandObject`s
(area geometry now; line/point reserved — the only sanctioned extension
stub, `geometry/evidence.py::units_of_geometry`). Candidate pins: every
`segment_raster` settlement intersecting the candidate zone (closer to
the target than to its second-nearest site, + `candidate_margin_m`).
State transitions are code: *confirmed* when a purchased point inside the
object shows the target above `tau_acc` (confirmation auto-opens one COV
+ one ROB claim); *dismissed* only through an instrument-verified
DismissRequest (≥ `dismiss_min_units` sampled units inside, none showing
the target). The `CellLocalizationBook` tracks per target cell: T[c]
(busy-window traffic once cell-level KPI is owned), status ∈ {accounted,
unaccounted, unknown}, empirical direction of served points, and derives
`residual_bound`, `importance_bound(obj)`, `residual_map` — sums and set
intersections only, traffic is never split.

**Investigator protocol** (`agents/investigator.py`): plain JSON on top
of `LLMClient` (Ollama tool-calling is unreliable). Each response is
exactly one JSON object — `{"tool": name, "args": {...}}` (max
`max_tool_calls_per_round`, default 8) or `{"commit": <action>}`.
Committing actions: Purchase / RegisterObject / DismissRequest /
SplitObject / DrillDown / AcceptDefault / DeclareDone. Tools (read-only):
get_object, get_claim, list_claims, list_gaps, price, flip,
outcome_space, residual_map, footprint, history_profile,
run_adjudication_dry, notebook_read, notebook_write. Protocol rules: at
least one notebook_write before a commit; malformed → one re-prompt with
the validator error → round skipped with a logged incident (NO fallback
seat). The demo/CLI transport is `agents/demo_client.py` (a MockLLM-style
deterministic policy); `--llm ollama` uses the real server.

**Gate** (`loop/gate.py`): checks in order — schema; price ≤ remaining
budget; target exists and open; claim targets must hold a flip ticket;
predicted bucket ∈ outcome space (probe: target_present/target_absent/
mixed; PM: zone buckets; densify: interval_above/interval_below/
still_straddling); citation resolves **verbatim** against the briefing +
this turn's tool outputs; price ≤ {low: 0.02, mid: 0.10, high: 1.0} ×
B_initial. Denial returns the exact failing check as text.

## 4. Key mechanisms

**Flip test & tickets.** Every open claim is flipped to supported and to
refuted; if the verdict differs, the claim holds a ticket. Only ticketed
claims justify claim-directed spending — the gate re-checks this at
purchase time (there is no rendered dependency table).

**Audit (gap list).** Deterministic, every round: demand ledger absent;
target cell unknown/unaccounted with T[c] ≥ T_material (or T unknown);
object hypothesized; object above importance_floor with an open claim;
residual_bound > rho_residual and uninvestigated. Gap-directed spending
is how exploration is funded.

**Ledger reconciliation.** Every purchase's actual outcome bucket is
reconciled against the prediction immediately; per-grade hit rates are
shown back in the briefing. Bookkeeping only — nothing routes decisions
away from the agent (the old fuse is gone). Known selection bias
(documented): only chosen rows reconcile.

**Stopping.** Verdict stable `stable_rounds_to_stop` rounds with all
tickets resolved; or no ticket and no gap; or budget below every open
item's cheapest remedy; or DeclareDone (gate-checked: audit empty); or
`max_rounds`; or >4 consecutive rounds without an executed commit; the
CLI `--rounds N` caps regardless (demo mode). Close-out applies
conservative defaults (undecided tier → degraded, severity-undecided
hole → severe), each flagged `unverified_assumption`, and buys the
target's own RRC baseline last (reporting only).

## 5. Current parameter decisions

| parameter | value | [POLICY] | meaning |
|---|---|---|---|
| `analysis_hour` | per run | — | must lie inside the ticket window (validated at runner init) |
| `analysis_hour_default_rule` | busiest-profile else midpoint | yes | fires when the ticket omits the hour; the report flags it |
| `comparable_days_k` | 4 | yes | capacity evidence = k matched occurrences of the analysis hour |
| `theta` / `pi_hi` / `kappa` / `sigma` | 0.90 / 0.85 / 0.60 / 0.20 | yes | coverage pass share / no-headroom PRB / owner concentration / major-exit share |
| `P_min` | 50 | yes | pin granularity only — settlements below it are never offered as candidates (severity no longer uses population) |
| `candidate_margin_m` | 500 | yes | candidate-zone buffer |
| `T_material` / `T_severe` / `importance_floor` | 50 / 200 / 30 | yes | traffic thresholds for audit gaps and hole severity (illustrative values pending advisor sign-off — DESIGN-GAP) |
| `rho_residual` | 0.12 | yes | max unaccounted traffic share compatible with "fully absorbable" |
| `cap15_refute_frac` / `calib_false_pass_max` | 0.10 / 0.05 | yes | 15-min tier / calibration edge |
| `price_low_frac` / `price_mid_frac` | 0.02 / 0.10 | no | gate confidence caps (high = 1.0) |
| `max_tool_calls_per_round` | 8 | no | investigator tool budget |
| `n_min_units_per_cell` / `dismiss_min_units` / `min_dir_samples` | 3 / 4 / 3 | no | localization/dismissal evidence-unit minima |
| `suggested_random_probes` | 8 | no | exploration probes generated at setup (suggested, never auto-run) |
| `capacity_drilldown` | True | no (Config) | False: site-level analysis; DrillDown commits are refused |

## 6. Data & evaluation

All paid data flows through the `DataProvider` interface
(`provider/interface.py`): `topology`, `population_raster`,
`query_coverage`, `query_pm` (+ `query_pm_matched` default that
concatenates the k matched hours), `buy_profile`, `quote`. Site-level vs
cell-level PM is real: entities may be sites or cells (pricing scales by
entity count), and the target's demand ledger is a cell-level `rrc_conn`
purchase over the matched hours. The simulator (`provider/simulator.py`)
implements the seam today; a real-platform `FileProvider` implements the
same seam later (COPILOT_PROMPT.md). The simulator's "ghost" village
(present in reality, absent from the raster) is the canonical residual
test: it surfaces as an unaccounted heavy cell whose residual_map points
at it, registrable via RegisterObject(provenance="residual"). The
sub-P_min "tiny" village is the importance-floor test.

Prices come from one encapsulated function (`provider/pricing.py`);
"cheap"/"expensive" exist only relative to the budget caps — quartiles
died with the menu. The hourly-capacity calibration table
(`planning/calibration.py`, artifact `cases/calibration_table.json`) is
kept — it is an instrument, not evaluation.

There is **no evaluation harness in this repository**: `eval/`
(arms, oracle, metrics, ground truth, divergence logging) was deleted
with the migration. Each run writes `runs/<case>/`: `trace.jsonl` (every
node decision and every queried datum), `ledger.json`, `notebook.md`
(the agent's own log), `events.log`, `report.md` (with the mandatory
conditionality block, the demand-closure statement with the residual
bound, and the briefing history).

Demo: `python -m outage_whatif.run_case cases/case03.yaml --rounds 8
[--pause]` — 8 rounds end-to-end on the simulator with the deterministic
demo transport (no Ollama needed), printing each round's briefing, tool
calls, commit, gate result, and state deltas.

## 7. Status & extension points

Implemented and tested (72 tests, no LLM server required): geometry and
segmentation, demand objects/localization/audit, claims/adjudication,
verdict + flip tests, calibration (matched-hour, `calib-v2`), the
investigator round loop with gate and briefing, run tracing, the CLI.

Not implemented / never run:
- a real-LLM run (`--llm ollama`) has never executed (no Ollama server on
  the dev host);
- `FileProvider` (real-data adapter) is not written — task spec in
  COPILOT_PROMPT.md;
- line/point demand-object geometries: reserved stub
  `geometry/evidence.py::units_of_geometry` (the only sanctioned
  extension point).

`# DESIGN-GAP` markers (verbatim inventory): `config.py` illustrative
holiday calendar and illustrative `T_material`/`T_severe`/
`importance_floor` values; `claims/adjudicate.py` 30% footprint-share
unaffected rule; `provider/pricing.py` requested points proxy
area×density.

## 8. Drift notes (spec text vs code — code wins)

1. **The design document is not in this repository.**
   `outage_whatif_design_final.md` could not be located; the migration
   was executed against the migration brief as the authoritative spec
   (owner-approved). Consequences: the investigator system prompt
   (`agents/investigator.py::SYSTEM_PROMPT`) is a reconstruction of
   Part V from the brief — replace it verbatim when the document is
   available; the §4.1 cell-status semantics are implemented as:
   *unknown* = fewer than `n_min_units_per_cell` sampled units served by
   the cell; *accounted* = every sampled unit served by the cell lies in
   a registered non-dismissed object; *unaccounted* otherwise.
2. **Split / drill-down triggers.** The old automatic round-count
   triggers were removed: SplitObject and DrillDown are agent-committed
   actions, instrument-checked by the gate (clustered pass/fail cells;
   capacity claim stuck in the hourly middle zone). The splitting
   machinery itself is unchanged (`claims/lifecycle.py`).
3. **Hole severity.** Implemented as: severe iff the object is the sole
   non-dismissed explanation of a cell with T[c] ≥ T_severe; *severity
   undecided* when a sole-explained cell's T is unknown, or the object
   shares all its cells with intact objects; not severe otherwise. The
   "T unknown on a sole cell" branch is a code decision the design may
   refine.
4. **Deleted under the minimality directive** (ambiguous keep-vs-delete
   calls resolved toward deletion): the boundary/integrity machinery and
   static-square mode; the pre-enumerated action menu and price
   quartiles; the dependency table; both rule seats and all
   divergence-vs-baseline logging; the fuse; the eval harness with
   ground truth and metrics; old `runs/` artifacts; per-settlement
   startup claims; `arm` naming (runs are now `runs/<case>/`).
   `RuleSeat1ZoneDistance`'s zone-distance grading heuristic died with
   the baselines — if a scripted comparison agent is ever needed again,
   `agents/demo_client.py` is the place it would live.
5. **Case files renamed** `caseNN.yaml` (the `_blind`/`_calibration`
   filename suffixes were eval-arm naming); the `kind:` field inside is
   kept because calibration-table building selects on it.
6. **`straddler` village.** With no boundary, the simulator's forced
   near-edge village is just a normal pin; the name is historical.
7. **Profiles.** `buy_profile` purchases survive as the
   `profile` purchase kind and the read-only `history_profile` tool
   (owned profiles + quotes). The old judgment-firming scoring
   (grade-moved-next-round) died with the two-seat design; profile
   purchases reconcile on anchor_confirms/anchor_shifts like any other.
