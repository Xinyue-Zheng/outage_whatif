# Prompt for Copilot — adapt outage_whatif to real data (fill the blanks, then paste)

Project background: see PROJECT.md (read it if unsure about intent; this
prompt is self-sufficient for the task).

NOTE: the codebase now runs the INVESTIGATOR architecture — one agent seat
(JSON tool loop over `agents/llm.py::LLMClient`), a spend gate, demand
objects with a cell localization book, and no analysis boundary of any
kind. There is no eval harness, no arms, and no rule seats. The demo entry
point is `python -m outage_whatif.run_case <case.yaml> --rounds N`.
NOTE: per-hour analysis is implemented — one run = one
(ticket, analysis_hour) pair; capacity PM is queried as k=4 matched
occurrences of the analysis hour via `DataProvider.query_pm_matched`
(default implementation loops `query_pm`, so FileProvider gets it free).
NOTE: the target's demand ledger is a CELL-LEVEL `rrc_conn` purchase over
the matched hours (`target_kpi`), so `query_pm` must accept cell entities
for the target even when neighbor analysis stays site-level.

Repo root: `<ROOT>` — the python package is `<ROOT>/outage_whatif`.
Tickets CSV: `<CASES_CSV_PATH>` (columns: enodeb, start time, end time; exact names: `<COLUMN_NAMES>`)
KPI query script: `<KPI_SCRIPT_PATH>` — one run fetches ALL KPI metrics
together for the requested cells/window (CSV output). There are NO
pre-downloaded KPI files; every KPI read goes through this script.
Coverage query script: `<COVERAGE_SCRIPT_PATH>` — there is NO local
coverage storage; each query downloads one JSON per requested tile. The
area is a static 30km x 30km grid sampled every 1km: one JSON = one
1km x 1km tile holding its 10m x 10m cubes' coverage. Tile
naming/addressing: `<TILE_NAMING_RULE>`.
Site CSV (topology): `<SITE_CSV_PATH>` — site id + location for every site in the area, nothing else
Population read script: `<POP_SCRIPT_PATH>`
Ollama server: `<OLLAMA_HOST>` , model: `<MODEL>`

Read before coding: `outage_whatif/provider/interface.py` (the `DataProvider`
contract + return dataclasses), `outage_whatif/loop/case.py` (case fields),
`outage_whatif/config.py`, `<KPI_SCRIPT_PATH>` (to learn its args and
output columns), and ONE coverage JSON to infer its schema. Do the 3
steps in order.

## 1. Tickets: CSV -> case files

`scripts/tickets_from_csv.py` already exists: read `<CASES_CSV_PATH>`, emit
one YAML per row into `outage_whatif/cases/` with `name`, `kind: blind`,
`seed` (row index), `budget: <BUDGET>`, `outage_start`/`outage_end` (ISO),
`target_site` = enodeb, and optional `analysis_hour` (clock-hour inside
the window; omit to let the [POLICY] default rule pick it). No `sim:`
block (that is simulator-only). Delete the old synthetic caseNN yamls.
Verify the column mapping against `<COLUMN_NAMES>` and run it.

## 2. File-backed data provider

Create `outage_whatif/provider/platform.py`:
`class FileProvider(DataProvider)` reading the local files (types from
`interface.py`; every paid method returns `(data, charged_price)`; keep
`provider/pricing.py` as the pricebook so budget semantics survive):

- `topology()` -> `Topology(sites, roster, azimuths)` from the site CSV `<SITE_CSV_PATH>` (site id + location only). Convert lat/lon to local meters on the 30km plane if needed. The roster must include the TARGET's cells (cell -> site) — the localization book keys on them; if coverage JSONs report cell IDs, derive cell->site by parsing the IDs; azimuths = {} (optional)
- `population_raster()` -> read `<POP_SCRIPT_PATH>` and reuse its data access/parsing; resample its output onto a `PopulationRaster` grid (see `geometry/raster.py` for the expected shape) covering the 30km square. The raster is only the candidate-pin generator; demand the raster misses is handled by the residual mechanism, no code change needed
- `query_coverage(points)` -> `([PointCoverage], price)`: for each (x, y) locate its 1km tile, download that tile's JSON via `<COVERAGE_SCRIPT_PATH>` ONLY if not already cached this run (cache downloaded tiles in a dict — never re-download), pick the nearest 10m cube, map its fields to `serving=(cell, rsrp)` + `backups=[(cell, rsrp)]`
- `query_pm(entities, metric, granularity, window)` -> `({entity: PMSeries}, price)`: wrap `<KPI_SCRIPT_PATH>`. The script returns EVERY metric in one query, so run it once per (entities, granularity, window), cache the full multi-metric result in a dict, and serve later calls for other metrics of the same key from the cache (no re-run; price each served call via `quote` as usual). Map script columns to rrc_conn|prb_util|throughput|volume; granularity hourly|15min. Entities may be sites or cells (target cells for the demand ledger)
- `buy_profile(site, kind, hour=None)` -> `(Profile, price)`: 24-entry hourly mean/var from a historical window fetched via the same script (cached too); `kind="matched_hour"` profiles the given clock-hour over ~12 weeks (repeat its stat in all 24 slots, as SimProvider does)
- `quote(kind, **params)` -> price without buying

Wire into `outage_whatif/run_case.py` (currently requires a `sim:` block
and hardcodes `SimProvider`) behind the absence of `sim:`; simulator runs
must still work.

## 3. Check the Ollama endpoint

Set `llm_model=<MODEL>`, `ollama_host=<OLLAMA_HOST>`, and
`capacity_drilldown: false` (site-level analysis — the KPI source has no
per-cell PM for neighbors; DrillDown commits are then refused by the gate)
in `config.py` (or a `config.yaml` next to it). Client:
`outage_whatif/agents/llm.py::OllamaLLM` (LangChain ChatOllama, strict
JSON via `format`=schema). Verify `GET <OLLAMA_HOST>/api/tags` lists
`<MODEL>`, then smoke-test one `OllamaLLM.complete_json()` call.

## Constraints

- Python 3.11 venv: `python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt`; always run from repo root (`python -m outage_whatif...`).
- Do NOT modify `geometry/`, `demand/`, `claims/`, `verdict/`, `planning/`, `loop/` logic.
- Every run already dumps all queried data, labeled by round and purpose, to `<run_dir>/trace.jsonl` (`node=="query"` records, written by `loop/engine.py::_trace_query`) — keep this path working for FileProvider data; do not build a second export.
- Done when `.venv/bin/python -m pytest outage_whatif/tests -q` passes (72 tests) and `.venv/bin/python -m outage_whatif.run_case cases/<real_case>.yaml --rounds 8 --llm ollama` runs one real ticket end-to-end with per-step query data present in `runs/<case>/trace.jsonl`.
