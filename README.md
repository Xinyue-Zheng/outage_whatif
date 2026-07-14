# outage_whatif — budget-constrained investigator for cell-site outage what-ifs

> **PROJECT.md** is the canonical as-implemented description (architecture,
> parameters, drift notes). **COPILOT_PROMPT.md** is the fill-in task prompt
> for the real-data adaptation (FileProvider).

A target eNodeB will be switched off during a ticketed window. Assessed at
one `analysis_hour` inside that window, can the neighboring sites absorb the
target's users? The answer — per demand object and overall — is qualitative:
`fully absorbable` / `locally degraded` / `severe hole exists` /
`undecided/qualified`. The system verifies **necessary conditions** as
three-valued claims (supported / refuted / undecided):

- **coverage** — footprint evidence cells have a qualifying best alternative
  (Wilson interval vs θ; exact census once every cell is sampled),
- **capacity** — "no capacity obstacle found" per genuine exit neighbor
  (two-tier: calibrated hourly support zone, definitive 15-minute tier),
- **robustness** — best alternatives not concentrated in one owner (vs κ).

**Per-hour analysis.** One run = one (case, analysis_hour) pair; capacity
evidence is the k=4 matched occurrences of that hour on comparable days
(same clock-hour + weekday, holiday-class matching, known outages excluded).
An omitted `analysis_hour` triggers the [POLICY] default rule and the report
flags it.

Every data item is priced against a finite budget B. One **investigator**
agent (a single LLM seat) decides each round what to buy; deterministic code
does everything else — adjudication, pricing, the flip test, the audit, the
verdict, and the **spend gate**.

## The round

```
advance -> adjudicate_lifecycle -> assess -> stop_check -> briefing
       -> investigator (JSON tool loop) -> gate -> execute -> reconcile
```

- **Demand objects.** The population raster only *pins candidates*: raster
  settlements intersecting the candidate zone (closer to the target than to
  its second-nearest site, + margin) start as *hypothesized* objects.
  Confirmation is code (a purchased point inside shows the target above
  τ_acc) and auto-opens one COV + one ROB claim; dismissal is
  instrument-verified (≥ `dismiss_min_units` sampled units inside, none
  showing the target). Demand the raster misses is caught by the **cell
  localization book**: per target cell, busy-window traffic T[c], status
  (accounted / unaccounted / unknown), empirical direction, and a residual
  map pointing at sampled-but-unmapped demand — registrable via
  `RegisterObject(provenance="residual")`. Sums and set intersections only;
  traffic is never split.
- **Audit.** A deterministic gap list (demand ledger absent, heavy
  unlocalized cells, hypothesized objects, open claims above the importance
  floor, uninvestigated residual). Round zero is naturally non-empty — that
  is what makes exploration fundable. There is no initial-sampling phase;
  the ~8 suggested random probes are a purchase, never auto-executed.
- **Investigator.** Plain-JSON protocol over `LLMClient` (Ollama
  tool-calling is unreliable): each response is exactly one JSON object,
  either a read-only tool call (max 8/round) or a **committing action**
  (Purchase / RegisterObject / DismissRequest / SplitObject / DrillDown /
  AcceptDefault / DeclareDone). At least one `notebook_write` must precede
  a commit; a malformed response gets one re-prompt, then the round is
  skipped with a logged incident — there is **no fallback seat**.
- **Gate.** Ordered checks: schema; price ≤ remaining budget; target exists
  and open; claim targets must hold a **flip ticket**; predicted bucket in
  the kind's outcome space; citation **verbatim** in the briefing + this
  turn's tool outputs; price within the confidence cap (low 2% / mid 10% /
  high 100% of the initial budget). Denials return the exact failing check
  and feed the single retry.
- **Reconciliation.** Predicted vs actual outcome bucket, per-grade hit
  rates shown back in the briefing (bookkeeping only — nothing routes
  decisions away from the agent).

## Setup & run

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt

.venv/bin/python -m pytest outage_whatif/tests -q          # 72 tests, no LLM needed
.venv/bin/python -m outage_whatif.planning.calibration     # calibration artifact
.venv/bin/python -m outage_whatif.run_case cases/case03.yaml --rounds 8 --pause
```

The demo command runs eight investigation rounds end-to-end on the
simulator with the deterministic demo transport (no Ollama needed),
printing each round's briefing, tool calls, committing action, gate result,
and state deltas; `--pause` waits for Enter between rounds. `--llm ollama`
uses the real model (`Config.llm_model`, default `llama3.1`, via
LangChain's `langchain-ollama`, strict JSON via Ollama's `format`).
Artifacts land in `outage_whatif/runs/<case>/`: `trace.jsonl`,
`ledger.json`, `notebook.md`, `events.log`, `report.md` (conditionality
block, demand-closure statement with the residual bound, briefing history).

## Layout

```
outage_whatif/
  config.py        # single source of truth; [POLICY] block clearly isolated
  geometry/        # rasters, 8-connected clustering, 300 m evidence cells,
                   # Wilson machinery, footprint rules (line/point geometry:
                   # reserved extension stub in evidence.py)
  demand/          # demand objects + registry, cell localization book
  claims/          # claim model, deterministic adjudication, lifecycle
  verdict/         # verdict function, flip test
  planning/        # comparable-day matching, calibration table,
                   # point-placement helpers, suggested random probes
  agents/          # investigator seat + protocol validators, LLM transports
                   # (Ollama / MockLLM / demo client), ledgers
  provider/        # DataProvider interface, price function, simulator
  loop/            # engine, round graph, briefing, spend gate, audit, report
  run_case.py      # the round-by-round demo CLI
  cases/           # 10 scenario files + calibration_table.json
  tests/           # 72 tests; all run without any LLM server
scripts/
  tickets_from_csv.py   # outage-ticket CSV -> case YAMLs
```

## DESIGN-GAP list (where the spec was silent, simplest option chosen)

All marked `# DESIGN-GAP:` in code:

- `provider/pricing.py` — coverage's "super-linear in area × density" is
  realized as `base · n_points^1.15` (points proxy area×density).
- `claims/adjudicate.py` — an object is "unaffected" when <30% of its
  sampled cells are footprint; once the census is complete the exact
  proportion decides against θ/κ (Wilson governs only partial sampling).
- `config.py` — small illustrative holiday calendar; illustrative
  `T_material` / `T_severe` / `importance_floor` values pending advisor
  sign-off.
- Verdict ordering (documented in `verdict/verdict.py`): a refuted
  major-exit capacity is terminal for an object (degraded); refuted
  robustness likewise pins the tier so open capacity claims lose their
  tickets when they can no longer change it.

See PROJECT.md §8 for the migration drift notes (missing design document,
agent-committed split/drill-down, severity semantics, deletions).

## Boundary declaration (verbatim in every report)

Handover misconfiguration, transport bottlenecks, and all other factors
absent from the inputs are outside every conclusion this system can draw.
