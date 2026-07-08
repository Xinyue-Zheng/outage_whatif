# PROJECT.md — background and alignment document

This file is the shared context for everyone (and every AI assistant)
working on this project across its two workspaces. Read it before making
changes; update it when the picture changes.

## 1. What this project is

**outage_whatif** answers a telecom planning question: a target eNodeB
(cell site) will be switched off during a known outage window — *can the
neighboring sites absorb the target's users?* The answer is qualitative,
per populated settlement and overall: `fully absorbable`, `locally
degraded`, or `severe hole exists`.

Two things make it interesting:

1. **Every piece of data costs money.** Coverage probes, KPI (PM counter)
   series, and historical profiles are bought from a data platform against
   a finite per-case budget B. The system must decide, round by round,
   what the next unit of budget buys — sequential decision-making under a
   budget, not batch analysis.
2. **It is an experiment about LLM agents.** Everything enumerable is
   deterministic code. Exactly ONE judgment is delegated to agents: the
   prior likelihood of what a query will return before it is run. Two
   agent "seats" exist (see §3), and each can be filled by an LLM or by a
   rule baseline. The headline question: does the LLM earn its keep vs
   `rule/rule` under identical code and identical budget?

## 2. The question is conditional on one hour

The ticket keeps its full multi-hour outage window, but **one run = one
(case, analysis_hour) pair**: "IF the outage's effect is evaluated at
`analysis_hour` (a clock-hour inside the window), can neighbors absorb?"

- `analysis_hour` must lie inside the ticket window (validated at init;
  invalid → case rejected). If omitted, a [POLICY] default rule picks it
  (busiest window hour per a held target profile, else the window
  midpoint) and the report flags that the default fired.
- Capacity evidence = the k=4 matched occurrences of that hour on
  comparable days (same clock-hour + same weekday, most recent k weeks;
  holiday outages match holiday-class days; known-outage dates excluded).
  The hourly tier adjudicates the MEAN of the k values; the 15-minute
  tier the spike fraction over the 4k=16 bins (≥2 spiking bins refute).
- Coverage/robustness/integrity are hour-invariant (radio geometry).
- Run IDs carry the hour: `case01_h17_rule-rule`. Reports state the
  conditionality verbatim near the top.

## 3. How it works (one round)

The system's state is a board of falsifiable **claims**, three-valued
(supported / refuted / undecided):
- **coverage** — settlement S keeps service from neighbors (Wilson
  interval over 300 m evidence cells vs θ),
- **capacity** — exit neighbor N has headroom (two tiers, see §2),
- **robustness** — alternatives not concentrated in one owner (vs κ),
- **integrity** — the analysis boundary is drawn correctly.

Each round (a LangGraph StateGraph, `loop/graph.py` — topology LOCKED by
`tests/test_graph_topology.py`):

1. re-adjudicate claims, run claim lifecycle (spawn/kill/split);
2. build the action menu with prices; flip-test which claims could still
   change the verdict (those hold "tickets");
3. stop checks (verdict stable / budget gone / nothing can flip);
4. render the agents' entire closed-book world: claim board, dependency
   table, anchor digest;
5. **Seat 1 (prioritizer)** grades every ticketed item {high,mid,low};
   code computes the ranking FROM the grades (a theorem, not a choice);
6. **Seat 2 (action chooser)** picks one purchase with a predicted
   outcome bucket; a code guardrail + mechanical contradiction checks can
   reject it (one retry → rule fallback → cheapest compliant sweep);
7. execute, pay, reconcile both agents' prediction ledgers (two
   consecutive misses trip a "fuse" routing that seat to its baseline).

"Seat" = a role that either an LLM or a rule can occupy. Arms are named
`seat1/seat2`: `rule/rule`, `zonedist/rule`, `llm/llm`, plus mixed
ablations. LLM transport is LangChain → Ollama (`agents/llm.py`,
`Config.llm_model`, default `llama3.1`; `$OLLAMA_HOST` or
localhost:11434). There is deliberately NO Anthropic/OpenAI dependency.

Every run directory gets `report.md`, `ledger.json`, `trace.jsonl` (every
node decision + every queried datum, labeled by round and purpose — this
is the file to build visualizations from), and `round_graph.mmd`.

## 4. The two workspaces

| | Workspace A (origin) | Workspace B (adaptation) |
|---|---|---|
| Assistant | Claude Code | GitHub Copilot |
| Data | synthetic simulator (`provider/simulator.py`) | real files |
| Cases | 10 YAML scenarios in `cases/` | tickets CSV (enodeb, start, end) |
| KPI | simulated on demand | user's query script — ONE run returns ALL metrics; batch + cache |
| Coverage | simulated on demand | ~900 JSON tiles (1 km each, 10 m cubes) over a 30×30 km area |
| Population | simulated raster | user's population read script |
| Boundary | adaptive circle (default) | `static_area_km: 30` (fixed square) |

Workspace B's task list lives in **COPILOT_PROMPT.md** (fill in the
blanks, paste to Copilot). The key adapter to build there is
`provider/platform.py::FileProvider` implementing the `DataProvider`
interface (`provider/interface.py`) — the deliberate seam between
analysis logic and data source. Everything above that seam is shared and
should only change in workspace A, then flow to B via git.

**Boundary note (supersedes older specs):** with `static_area_km > 0` the
start area is an exact fixed square centered on the target; there is no
integrity ring, no integrity claims, and no boundary expansion. The
"R0 = 0.75 × median 6-NN distance" circle in any older document refers to
the default (`static_area_km = 0`) mode only. Do not restore the circle.

## 5. Current state (2026-07-08)

Done: milestones M1–M8 (geometry, provider, claims/verdict, planning,
loop, LLM seats, eval harness, per-hour analysis); LangGraph round loop;
Ollama/LangChain transport; static-square mode; decision/query tracing;
71 tests green.

Not done / pending:
- the `llm/llm` arm has NEVER run (no Ollama server was available on the
  workspace-A host) — rule/rule and zonedist/rule results in `runs/`;
- `FileProvider` (workspace B) not yet written;
- the "sweep all hours of the window" loop — deliberately NOT
  implemented; a marked EXTENSION POINT sits in `eval/harness.py`.

## 6. Conventions and guardrails

- Python 3.11 venv at repo root; recreate with
  `uv venv --python 3.11 .venv && uv pip install -r requirements.txt`;
  always run from the repo root (`python -m outage_whatif...`).
- Tests: `python -m pytest outage_whatif/tests -q` (all pass without any
  LLM server). Experiments: `python -m outage_whatif.eval.harness`.
- **[POLICY]** constants (`config.py` Policy block) encode discretionary
  judgment and require advisor sign-off to change. **DESIGN-GAP** markers
  flag places where the spec was silent and the simplest option was
  chosen (inventory in README.md).
- The orchestration graph's topology is locked by
  `tests/test_graph_topology.py`; change requests that say "the graph
  must not change" are proven by running it before and after.
- The verdict function, agent JSON schemas, and graph wiring are the
  most protected areas — treat changes there as scope changes needing
  explicit sign-off.
- Config overrides go in an optional `outage_whatif/config.yaml`
  (never edit defaults casually); LLM model/host live there too.
