# Evaluation summary

> **Note:** `ANTHROPIC_API_KEY` was not set, so the llm/llm arm (and mixed ablations) were skipped. Set the key and run `python -m outage_whatif.eval.harness llm/llm` to add them.

## Per-case results

| case | kind | arm | GT overall | system overall | hit | tier acc | attr acc | spend | rounds | divergences |
|---|---|---|---|---|---|---|---|---|---|---|
| case01 | calibration | rule/rule | locally degraded | locally degraded | Y | 1.0 | 1.0 | 310.5 | 39 | 0 |
| case02 | calibration | rule/rule | locally degraded | locally degraded | Y | 0.667 | 0.5 | 178.57 | 24 | 0 |
| case03 | blind | rule/rule | locally degraded | locally degraded | Y | 0.8 | 0.8 | 415.11 | 48 | 0 |
| case04 | blind | rule/rule | locally degraded | locally degraded | Y | 0.5 | 0.5 | 220.9 | 32 | 0 |
| case05 | blind | rule/rule | severe hole exists | severe hole exists | Y | 0.5 | 0.5 | 200.49 | 24 | 0 |
| case06 | blind | rule/rule | locally degraded | locally degraded | Y | 1.0 | 1.0 | 115.78 | 17 | 0 |
| case07 | blind | rule/rule | locally degraded | locally degraded | Y | 1.0 | 1.0 | 100.68 | 15 | 0 |
| case08 | blind | rule/rule | severe hole exists | severe hole exists | Y | 0.8 | 0.8 | 123.56 | 21 | 0 |
| case09 | blind | rule/rule | severe hole exists | severe hole exists | Y | 1.0 | 1.0 | 121.03 | 14 | 0 |
| case10 | blind | rule/rule | locally degraded | locally degraded | Y | 1.0 | 0.25 | 230.7 | 39 | 0 |
| case01 | calibration | zonedist/rule | locally degraded | locally degraded | Y | 1.0 | 1.0 | 300.04 | 39 | 0 |
| case02 | calibration | zonedist/rule | locally degraded | locally degraded | Y | 0.667 | 0.5 | 178.57 | 24 | 0 |
| case03 | blind | zonedist/rule | locally degraded | locally degraded | Y | 0.8 | 0.8 | 415.11 | 48 | 0 |
| case04 | blind | zonedist/rule | locally degraded | locally degraded | Y | 0.5 | 0.5 | 220.9 | 32 | 0 |
| case05 | blind | zonedist/rule | severe hole exists | severe hole exists | Y | 0.5 | 0.5 | 200.49 | 24 | 0 |
| case06 | blind | zonedist/rule | locally degraded | locally degraded | Y | 1.0 | 1.0 | 115.78 | 17 | 0 |
| case07 | blind | zonedist/rule | locally degraded | locally degraded | Y | 1.0 | 0.857 | 362.08 | 33 | 0 |
| case08 | blind | zonedist/rule | severe hole exists | severe hole exists | Y | 0.8 | 0.8 | 123.56 | 21 | 0 |
| case09 | blind | zonedist/rule | severe hole exists | severe hole exists | Y | 1.0 | 1.0 | 121.03 | 14 | 0 |
| case10 | blind | zonedist/rule | locally degraded | locally degraded | Y | 1.0 | 0.25 | 230.7 | 39 | 0 |
| case01 | calibration | oracle | locally degraded | locally degraded | Y | 1.0 | 1.0 | 310.5 | 39 | 0 |
| case02 | calibration | oracle | locally degraded | locally degraded | Y | 0.667 | 0.5 | 178.57 | 24 | 0 |
| case03 | blind | oracle | locally degraded | undecided | N | 0.8 | 0.8 | 2896.98 | 301 | 0 |
| case04 | blind | oracle | locally degraded | locally degraded | Y | 0.5 | 0.5 | 220.9 | 32 | 0 |
| case05 | blind | oracle | severe hole exists | severe hole exists | Y | 0.5 | 0.5 | 200.49 | 24 | 0 |
| case06 | blind | oracle | locally degraded | locally degraded | Y | 1.0 | 1.0 | 115.78 | 17 | 0 |
| case07 | blind | oracle | locally degraded | locally degraded | Y | 1.0 | 1.0 | 100.68 | 15 | 0 |
| case08 | blind | oracle | severe hole exists | severe hole exists | Y | 0.8 | 0.8 | 123.56 | 21 | 0 |
| case09 | blind | oracle | severe hole exists | severe hole exists | Y | 1.0 | 1.0 | 121.03 | 14 | 0 |
| case10 | blind | oracle | locally degraded | locally degraded | Y | 1.0 | 0.25 | 230.7 | 39 | 0 |

## Arm aggregates (blind cases)

| arm | overall acc | mean tier acc | mean attr acc | mean spend | mean rounds |
|---|---|---|---|---|---|
| oracle | 0.9 | 0.827 | 0.735 | 449.919 | 52.6 |
| rule/rule | 1.0 | 0.825 | 0.731 | 191.031 | 26.25 |
| zonedist/rule | 1.0 | 0.825 | 0.713 | 223.706 | 28.5 |

Divergence logs (per LLM-seat run) are first-class outputs in `runs/<case>_<arm>/divergence.json`.