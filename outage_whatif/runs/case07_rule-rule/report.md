# What-if outage report — case case07, target S5

*Arm:* `rule/rule` — *outage window:* 2026-07-25T09:00:00 to 2026-07-25T21:00:00 (Saturday, sat)

## Overall verdict
**locally degraded**

Stop reason: all tickets resolved; verdict unchanged for 2 rounds after 15 rounds; spend 100.68 of budget 500.0.

## Per-subregion verdicts and deciding claims

| subregion | pop | tier | severe | bottleneck | deciding evidence |
|---|---|---|---|---|---|
| BG | 36 | absorbable | no | - | COV:BG:supported; ROB:BG:undecided (0.095, 0.905); CAP:S2:undecided; CAP:S8:undecided |
| V1 | 525 | degraded | no | robustness (S4) | COV:V1:supported (0.438, 1.0); ROB:V1:refuted (0.438, 1.0); CAP:S4:undecided |
| V2 | 355 | degraded | no | robustness (S8) | COV:V2:supported (0.438, 1.0); ROB:V2:refuted (0.208, 0.939); CAP:S6:undecided; CAP:S8:undecided |
| V3 | 274 | degraded | no | robustness (S1) | COV:V3:supported (0.438, 1.0); ROB:V3:refuted (0.208, 0.939); CAP:S1:undecided; CAP:S4:undecided |
| V4 | 200 | degraded | no | robustness (S4) | COV:V4:supported (0.51, 1.0); ROB:V4:refuted (0.51, 1.0); CAP:S4:undecided |
| V5 | 136 | degraded | no | robustness (S8) | COV:V5:supported (0.676, 1.0); ROB:V5:refuted (0.676, 1.0); CAP:S8:undecided |
| V6 | 72 | degraded | no | robustness (S8) | COV:V6:supported (0.342, 1.0); ROB:V6:refuted (0.342, 1.0); CAP:S8:undecided |

## Policy rules in force ([POLICY] — advisor sign-off required)
- theta = 0.9
- pi_hi = 0.85
- kappa = 0.6
- P_min = 50
- P0 = 200
- sigma = 0.2
- cap15_refute_frac = 0.1
- calib_false_pass_max = 0.05
- calibration support-zone edge = 0.5 (hourly tier may declare support)

## Disclosures
- Settlements under P_min were not individually verified. (1 settlement(s), 36 people absorbed into the background region, which the background grid still covers.)
- Declared boundary: handover misconfiguration, transport bottlenecks, and all other factors absent from the inputs are outside every conclusion this system can draw.
- Boundary expansions performed: 2.
- Target baseline RRC (reporting/validation only): mean 284.4 conn/h.

## Budget ledger

| round | action | kind | price | purpose | claim served |
|---|---|---|---|---|---|
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V1 |
| 0 | init:Track-1 initial sampling | coverage | 3.54 | Track-1 initial sampling | COV:V2 |
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V3 |
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V4 |
| 0 | init:Track-1 initial sampling | coverage | 7.85 | Track-1 initial sampling | COV:V5 |
| 0 | init:Track-1 initial sampling | coverage | 2.22 | Track-1 initial sampling | COV:V6 |
| 0 | init:Track-2 fuse grid | coverage | 6.37 | Track-2 fuse grid | COV:BG |
| 1 | R1:expand:2 | coverage | 4.92 | boundary expansion resampling | INT:2 |
| 2 | R2:ring_sample:INT:0 | ring_sample | 4.92 | resolve INT:0 | INT:0 |
| 3 | R3:ring_sample:INT:1 | ring_sample | 4.92 | resolve INT:1 | INT:1 |
| 4 | R4:expand:1 | coverage | 4.92 | boundary expansion resampling | INT:1 |
| 5 | R5:coverage_densify:COV:V5 | coverage_densify | 2.22 | resolve COV:V5 | COV:V5 |
| 6 | R6:ring_sample:INT:3 | ring_sample | 4.92 | resolve INT:3 | INT:3 |
| 7 | R7:ring_sample:INT:4 | ring_sample | 4.92 | resolve INT:4 | INT:4 |
| 8 | R8:ring_sample:INT:5 | ring_sample | 4.92 | resolve INT:5 | INT:5 |
| 9 | R9:ring_sample:INT:5 | ring_sample | 4.92 | resolve INT:5 | INT:5 |
| 10 | R10:ring_sample:INT:6 | ring_sample | 4.92 | resolve INT:6 | INT:6 |
| 11 | R11:ring_sample:INT:7 | ring_sample | 4.92 | resolve INT:7 | INT:7 |
| 12 | R12:ring_sample:INT:7 | ring_sample | 4.92 | resolve INT:7 | INT:7 |
| 15 | final:target_rrc | pm_hourly | 9.6 | target baseline RRC (reporting/validation only) | - |

**Total spent: 100.68 / 500.0**

## Agent ledgers
### agent1
- hit rate per grade: {'high': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 141, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}}
- consecutive misses: 0; fuse trips: 0
- selection bias: only chosen rows get tested
### agent2
- hit rate per grade: {'high': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 10, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}}
- consecutive misses: 0; fuse trips: 0
- selection bias: only chosen rows get tested

## Event log
- [R1] spawned CAP:S1 (major exit for V3)
- [R1] spawned CAP:S2 (major exit for BG)
- [R1] spawned CAP:S4 (major exit for V1, V3, V4)
- [R1] spawned CAP:S6 (major exit for V2)
- [R1] spawned CAP:S8 (major exit for V2, V5, V6)
- [R1] boundary expansion forced in sector 2 (integrity refuted)
- [R2] executed R2:ring_sample:INT:0 (sample 4 ring points in sector 0) price=4.92; predicted=clean actual=clean
- [R3] executed R3:ring_sample:INT:1 (sample 4 ring points in sector 1) price=4.92; predicted=clean actual=contaminated
- [R4] boundary expansion forced in sector 1 (integrity refuted)
- [R5] executed R5:coverage_densify:COV:V5 (densify 2 unsampled evidence cells in V5) price=2.22; predicted=clears_theta actual=clears_theta
- [R6] executed R6:ring_sample:INT:3 (sample 4 ring points in sector 3) price=4.92; predicted=clean actual=clean
- [R7] executed R7:ring_sample:INT:4 (sample 4 ring points in sector 4) price=4.92; predicted=clean actual=clean
- [R8] executed R8:ring_sample:INT:5 (sample 4 ring points in sector 5) price=4.92; predicted=clean actual=still_undecided
- [R9] executed R9:ring_sample:INT:5 (sample 4 ring points in sector 5) price=4.92; predicted=clean actual=clean
- [R10] executed R10:ring_sample:INT:6 (sample 4 ring points in sector 6) price=4.92; predicted=clean actual=clean
- [R11] executed R11:ring_sample:INT:7 (sample 4 ring points in sector 7) price=4.92; predicted=clean actual=still_undecided
- [R12] executed R12:ring_sample:INT:7 (sample 4 ring points in sector 7) price=4.92; predicted=clean actual=clean
- [R13] no ticketed claims; idle round (stability check)
- [R14] no ticketed claims; idle round (stability check)