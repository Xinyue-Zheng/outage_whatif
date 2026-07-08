# outage_whatif — budget-constrained, agent-driven what-if analysis of cell-site outages

A target eNodeB will be switched off during a known window. Per populated
subregion and overall, the system decides **qualitatively** whether the
neighboring sites can absorb the target's users. Every piece of data costs
money from a finite budget B; each round decides what the next unit of budget
buys. The system verifies **necessary conditions** for absorption as
three-valued claims (supported / refuted / undecided):

- **coverage** — footprint evidence cells have a qualifying best alternative
  (Wilson interval vs θ; exact census once every cell is sampled),
- **capacity** — "no capacity obstacle found" per genuine exit neighbor
  (two-tier: calibrated hourly support zone, definitive 15-minute tier),
- **robustness** — best alternatives not concentrated in one owner (vs κ),
- **integrity** — the ring outside the analysis boundary holds essentially no
  footprint points (refutation forces boundary expansion).

Everything enumerable is deterministic code. Exactly one judgment is
delegated to LLM agents: **the prior likelihood of what a query will return
before it is run** (Agent 1 grades ticketed items; Agent 2 predicts outcome
buckets when selecting an action). Both seats can be swapped for rule
baselines — whether the agents earn their keep is an experimental question.

## Layout

```
outage_whatif/
  config.py        # single source of truth; [POLICY] block clearly isolated
  geometry/        # rasters, 8-connected clustering, 300 m evidence cells,
                   # Wilson machinery, boundary sectors/ring, footprint rules
  claims/          # claim model, deterministic adjudication, lifecycle
                   # (spawn / kill / split / drill-down)
  verdict/         # verdict function, flip test, dependency table
  planning/        # Track-1/Track-2 sampling, action menu + price quartiles,
                   # calibration table (support-zone edge, <=5% false pass)
  agents/          # LLM seats + schemas + validators, rule baselines,
                   # purchase & per-agent ledgers, two-miss fuse
  provider/        # DataProvider interface, price function, simulator
  loop/            # round loop, guardrail, mechanical checks, stop
                   # conditions, Markdown report
  eval/            # swap harness, oracle, metrics, divergence log, summary
  cases/           # 10 scenario files (2 calibration, 8 blind)
                   # + calibration_table.json (versioned artifact)
  runs/            # per-run artifacts: report.md, ledger.json,
                   # divergence.json, events.log, summary.md, metrics.json
  tests/           # 61 tests; all run without any API key
```

## Setup & run

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt

.venv/bin/python -m pytest outage_whatif/tests -q      # 61 tests, no LLM needed
.venv/bin/python -m outage_whatif.eval.calibrate       # build calibration artifact
.venv/bin/python -m outage_whatif.eval.harness         # run experiment arms
```

The harness runs `rule/rule` and the `zonedist/rule` ablation on all 10
cases plus an unlimited-budget oracle, and writes `outage_whatif/runs/summary.md`.
If an Ollama server with the configured model (`Config.llm_model`, default
`llama3.1`) is reachable — `$OLLAMA_HOST` or `http://localhost:11434` — it
also runs `llm/llm` (via LangChain's `langchain-ollama`, strict JSON via
Ollama's `format` = JSON schema) on all 10 cases and the mixed ablations
(`llm/rule`, `rule/llm`) on the 2 calibration cases.
A single arm: `.venv/bin/python -m outage_whatif.eval.harness llm/llm`.

## The round loop (one round)

1. Code produces the agents' entire (closed-book) world: **claim board**,
   **dependency table**, **anchor digest**.
2. Stop check: all tickets resolved + verdict stable 2 rounds; budget
   exhausted; or no (guardrail-compliant) affordable action can flip
   anything. On stop: buy the target's own baseline RRC last, apply
   conservative defaults (direction: degrade, flagged
   `unverified_assumption`), emit the report.
3. Refuted integrity blocks the run: forced deterministic boundary
   expansion + ring resampling; newly covered settlements get claims.
4. **Agent 1** grades every ticketed dependency row and direct resolution
   (verbatim citations verified; anchor-followed declarations required).
   **Code computes the ordering** — a theorem of the stated grades.
5. **Agent 2** picks an action among leader + 2 runners-up with predicted
   bucket, worst-case decisiveness arithmetic (re-verified by code),
   contingency line for every bucket, optional judgment-firming profile
   purchase, veto with mandatory dependency-row citation.
6. Guardrail (code): top-quartile price requires a high grade unless a
   prerequisite was resolved cheaply. Mechanical checks replace the omitted
   critic: duplicate-query, citation verification, contradiction lookup.
   One retry, then the round falls back to the rule baseline (that seat only).
7. Execute via `DataProvider`, pay, re-adjudicate, run lifecycle, recompute
   flip tests; reconcile ledgers (Agent 2 buckets immediately, Agent 1 grades
   when the lever's query executes); two-consecutive-miss fuse routes a
   single seat to its baseline next round. Divergences from baseline are
   logged first-class.

## Results snapshot (rule/rule, no API key)

Overall-verdict accuracy 10/10 vs simulator ground truth; mean per-village
tier accuracy ≈ 0.83 on blind cases at ≈ 45% of budget. See
`outage_whatif/runs/summary.md`.

## DESIGN-GAP list (where the spec was silent, simplest option chosen)

All marked `# DESIGN-GAP:` in code:

- `provider/pricing.py` — coverage's "super-linear in area × density" is
  realized as `base · n_points^1.15` (points proxy area×density).
- `planning/sampling.py` — "allocation proportional to population" is one
  evidence cell per P0/8 of population (min 4; ≥P0 gets the computed
  decide-in-one-round count, 35 at θ=0.9, z=1.96).
- `claims/adjudicate.py` — a subregion is "unaffected" when <30% of its
  sampled cells are footprint (same rule as the simulator's ground truth);
  once the census is complete the exact proportion decides against θ/κ
  (Wilson governs only partial sampling).
- `claims/lifecycle.py` — the capacity drill-down trigger is "stuck
  undecided in the hourly middle zone ≥2 rounds"; the design names the
  mechanism but not the trigger.
- `loop/tables.py` — integrity claims carry a constant P0 stake in the
  ordering (no stake was specified for them).
- `agents/ledger.py` — a tripped fuse routes that seat to its baseline for
  one round, then resets (penalty duration unspecified).
- `config.py` — small illustrative holiday calendar.
- `provider/simulator.py` — ground truth uses the same necessary-condition
  semantics as the claim system with perfect information (dense census over
  the same 300 m evidence cells), i.e. it measures whether sequential
  querying recovered the truth, not the physical outcome of an outage.
- Verdict ordering (documented in `verdict/verdict.py`): a refuted
  major-exit capacity is terminal for a subregion (degraded) — required for
  the design's worked dependency example; refuted robustness likewise pins
  the tier so open capacity claims lose their tickets when they can no
  longer change it.
- Known limitation: the never-zero Track-2 background stream means a
  background region whose true pass share sits exactly at θ can stay
  undecided indefinitely; the oracle run caps at 300 rounds and reports
  "undecided" honestly in that case (observed once, case03 oracle).

## Boundary declaration (verbatim in every report)

Handover misconfiguration, transport bottlenecks, and all other factors
absent from the inputs are outside every conclusion this system can draw.
