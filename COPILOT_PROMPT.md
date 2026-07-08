# Prompt for Copilot — adapt outage_whatif to real data (fill the blanks, then paste)

NOTE: the initial analysis boundary is now a fixed 30km x 30km square
centered on the target (already implemented) — this supersedes the
"R0 = 0.75 x median 6-NN distance" circle in any spec document. Do not
restore the circle. The square's size is `static_area_km` in config.
NOTE: per-hour analysis is already implemented — one run = one
(ticket, analysis_hour) pair; capacity PM is queried as k=4 matched
occurrences of the analysis hour via `DataProvider.query_pm_matched`
(default implementation loops `query_pm`, so FileProvider gets it free).

Repo root: `<ROOT>` — the python package is `<ROOT>/outage_whatif`.
Tickets CSV: `<CASES_CSV_PATH>` (columns: enodeb, start time, end time; exact names: `<COLUMN_NAMES>`)
KPI query script: `<KPI_SCRIPT_PATH>` — one run fetches ALL KPI metrics
together for the requested cells/window (CSV output). There are NO
pre-downloaded KPI files; every KPI read goes through this script.
Coverage JSONs dir: `<COVERAGE_JSON_DIR>` — whole area is a static 30km x 30km
grid sampled every 1km: each JSON file = one 1km x 1km tile holding its
10m x 10m cubes' coverage. Tile file naming: `<TILE_NAMING_RULE>`.
Population read script: `<POP_SCRIPT_PATH>`
Ollama server: `<OLLAMA_HOST>` , model: `<MODEL>`

Read before coding: `outage_whatif/provider/interface.py` (the `DataProvider`
contract + return dataclasses), `outage_whatif/loop/case.py` (case fields),
`outage_whatif/config.py`, `<KPI_SCRIPT_PATH>` (to learn its args and
output columns), and ONE coverage JSON to infer its schema. Do the 4
steps in order.

## 1. Tickets: CSV -> case files

Write `scripts/tickets_from_csv.py`: read `<CASES_CSV_PATH>`, emit one YAML
per row into `outage_whatif/cases/` with `name`, `kind: blind`, `seed`
(row index), `budget: <BUDGET>`, `outage_start`/`outage_end` (ISO),
`target_site` = enodeb, and optional `analysis_hour` (clock-hour inside
the window; omit to let the [POLICY] default rule pick it). No `sim:`
block (that is simulator-only). Delete the old synthetic caseNN yamls.

## 2. Static 30km x 30km start area

Already implemented: set `static_area_km: 30` (config.py / config.yaml)
for real runs. The boundary becomes the exact data square centered on the
target; integrity ring/claims and boundary expansion are disabled
automatically. No code change needed.

## 3. File-backed data provider

Create `outage_whatif/provider/platform.py`:
`class FileProvider(DataProvider)` reading the local files (types from
`interface.py`; every paid method returns `(data, charged_price)`; keep
`provider/pricing.py` as the pricebook so budget semantics survive):

- `topology()` -> `Topology(sites, roster, azimuths)` from `<TOPOLOGY_SOURCE>`
- `population_raster()` -> read `<POP_SCRIPT_PATH>` and reuse its data access/parsing; resample its output onto a `PopulationRaster` grid (see `geometry/raster.py` for the expected shape) covering the 30km square
- `query_coverage(points)` -> `([PointCoverage], price)`: for each (x, y) locate the 1km tile JSON, load it (cache loaded tiles in a dict), pick the nearest 10m cube, map its fields to `serving=(cell, rsrp)` + `backups=[(cell, rsrp)]`
- `query_pm(entities, metric, granularity, window)` -> `({entity: PMSeries}, price)`: wrap `<KPI_SCRIPT_PATH>`. The script returns EVERY metric in one query, so run it once per (entities, granularity, window), cache the full multi-metric result in a dict, and serve later calls for other metrics of the same key from the cache (no re-run; price each served call via `quote` as usual). Map script columns to rrc_conn|prb_util|throughput|volume; granularity hourly|15min
- `buy_profile(site, kind, hour=None)` -> `(Profile, price)`: 24-entry hourly mean/var from a historical window fetched via the same script (cached too); `kind="matched_hour"` profiles the given clock-hour over ~12 weeks (repeat its stat in all 24 slots, as SimProvider does)
- `quote(kind, **params)` -> price without buying

Wire into `outage_whatif/eval/harness.py::run_case` (currently hardcodes
`SimProvider`) behind a config flag; simulator runs must still work.

## 4. Check the Ollama endpoint

Set `llm_model=<MODEL>`, `ollama_host=<OLLAMA_HOST>` in `config.py` (or a
`config.yaml` next to it). Client: `outage_whatif/agents/llm.py::OllamaLLM`
(LangChain ChatOllama, strict JSON via `format`=schema). Verify
`GET <OLLAMA_HOST>/api/tags` lists `<MODEL>`, then smoke-test one
`OllamaLLM.complete_json()` call.

## Constraints

- Python 3.11 venv: `python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt`; always run from repo root (`python -m outage_whatif...`).
- Do NOT modify `geometry/`, `claims/`, `verdict/`, `planning/`, `loop/` logic.
- Every run already dumps all queried data, labeled by round and purpose, to `<run_dir>/trace.jsonl` (`node=="query"` records, written by `loop/engine.py::_trace_query`) — keep this path working for FileProvider data; do not build a second export.
- Done when `.venv/bin/python -m pytest outage_whatif/tests -q` passes (61 tests) and `.venv/bin/python -m outage_whatif.eval.harness llm/llm` runs one real ticket end-to-end with per-step query data present in its `runs/<case>_llm-llm/trace.jsonl`.
