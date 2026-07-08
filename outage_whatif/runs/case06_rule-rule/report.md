# What-if outage report — case case06, target S5

*Arm:* `rule/rule` — *outage window:* 2026-07-20T10:00:00 to 2026-07-20T18:00:00 (Monday, weekday)

## Overall verdict
**locally degraded**

Stop reason: all tickets resolved; verdict unchanged for 2 rounds after 17 rounds; spend 115.78 of budget 330.0.

## Per-subregion verdicts and deciding claims

| subregion | pop | tier | severe | bottleneck | deciding evidence |
|---|---|---|---|---|---|
| BG | 58 | hole | no | coverage | COV:BG:refuted (0.391, 0.862); ROB:BG:supported (0.089, 0.532); CAP:S7:supported mean=0.37 |
| V1 | 405 | degraded | no | robustness (S10) | COV:V1:supported (0.342, 1.0); ROB:V1:refuted (0.342, 1.0); CAP:S10:undecided |
| V2 | 300 | degraded | no | robustness (S8) | COV:V2:supported (0.566, 1.0); ROB:V2:refuted (0.566, 1.0); CAP:S8:undecided |
| V3 | 211 | degraded | no | robustness (S2) | COV:V3:supported (0.438, 1.0); ROB:V3:refuted (0.438, 1.0); CAP:S2:supported mean=0.346 |
| V4 | 95 | degraded | no | robustness (S8) | COV:V4:supported (0.342, 1.0); ROB:V4:refuted (0.342, 1.0); CAP:S8:undecided |
| V5 | 67 | degraded | no | robustness (S8) | COV:V5:supported (0.342, 1.0); ROB:V5:refuted (0.342, 1.0); CAP:S8:undecided |

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
- Settlements under P_min were not individually verified. (1 settlement(s), 37 people absorbed into the background region, which the background grid still covers.)
- Declared boundary: handover misconfiguration, transport bottlenecks, and all other factors absent from the inputs are outside every conclusion this system can draw.
- Boundary expansions performed: 3.
- Target baseline RRC (reporting/validation only): mean 208.5 conn/h.

## Budget ledger

| round | action | kind | price | purpose | claim served |
|---|---|---|---|---|---|
| 0 | init:Track-1 initial sampling | coverage | 7.85 | Track-1 initial sampling | COV:V1 |
| 0 | init:Track-1 initial sampling | coverage | 6.37 | Track-1 initial sampling | COV:V2 |
| 0 | init:Track-1 initial sampling | coverage | 3.54 | Track-1 initial sampling | COV:V3 |
| 0 | init:Track-1 initial sampling | coverage | 2.22 | Track-1 initial sampling | COV:V4 |
| 0 | init:Track-1 initial sampling | coverage | 2.22 | Track-1 initial sampling | COV:V5 |
| 0 | init:Track-2 fuse grid | coverage | 7.85 | Track-2 fuse grid | COV:BG |
| 1 | R1:expand:5 | coverage | 4.92 | boundary expansion resampling | INT:5 |
| 2 | R2:ring_sample:INT:1 | ring_sample | 4.92 | resolve INT:1 | INT:1 |
| 3 | R3:ring_sample:INT:2 | ring_sample | 4.92 | resolve INT:2 | INT:2 |
| 4 | R4:expand:2 | coverage | 4.92 | boundary expansion resampling | INT:2 |
| 5 | R5:ring_sample:INT:3 | ring_sample | 4.92 | resolve INT:3 | INT:3 |
| 6 | R6:ring_sample:INT:4 | ring_sample | 4.92 | resolve INT:4 | INT:4 |
| 7 | R7:pm_hourly:S2 | pm_hourly | 6.4 | resolve CAP:S2 | CAP:S2 |
| 8 | R8:ring_sample:INT:5 | ring_sample | 4.92 | resolve INT:5 | INT:5 |
| 9 | R9:ring_sample:INT:6 | ring_sample | 4.92 | resolve INT:6 | INT:6 |
| 10 | R10:pm_hourly:S7 | pm_hourly | 6.4 | resolve CAP:S7 | CAP:S7 |
| 11 | R11:ring_sample:INT:7 | ring_sample | 4.92 | resolve INT:7 | INT:7 |
| 12 | R12:expand:7 | coverage | 4.92 | boundary expansion resampling | INT:7 |
| 13 | R13:pm_hourly:S3 | pm_hourly | 6.4 | resolve CAP:S3 | CAP:S3 |
| 14 | R14:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 17 | final:target_rrc | pm_hourly | 6.4 | target baseline RRC (reporting/validation only) | - |

**Total spent: 115.78 / 330.0**

## Agent ledgers
### agent1
- hit rate per grade: {'high': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 177, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}}
- consecutive misses: 0; fuse trips: 0
- selection bias: only chosen rows get tested
### agent2
- hit rate per grade: {'high': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 8, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 3, 'scored': 3, 'hits': 3, 'rate': 1.0}}
- consecutive misses: 0; fuse trips: 0
- selection bias: only chosen rows get tested

## Event log
- [R1] spawned CAP:S10 (major exit for V1)
- [R1] spawned CAP:S2 (major exit for BG, V3)
- [R1] spawned CAP:S4 (major exit for BG)
- [R1] spawned CAP:S8 (major exit for BG, V2, V4, V5)
- [R1] boundary expansion forced in sector 5 (integrity refuted)
- [R2] executed R2:ring_sample:INT:1 (sample 4 ring points in sector 1) price=4.92; predicted=clean actual=clean
- [R3] executed R3:ring_sample:INT:2 (sample 4 ring points in sector 2) price=4.92; predicted=clean actual=contaminated
- [R4] boundary expansion forced in sector 2 (integrity refuted)
- [R5] spawned CAP:S7 (major exit for BG)
- [R5] killed CAP:S4 (no longer anyone's best alternative)
- [R5] executed R5:ring_sample:INT:3 (sample 4 ring points in sector 3) price=4.92; predicted=clean actual=clean
- [R6] executed R6:ring_sample:INT:4 (sample 4 ring points in sector 4) price=4.92; predicted=clean actual=clean
- [R7] executed R7:pm_hourly:S2 (hourly PRB for S2 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R8] executed R8:ring_sample:INT:5 (sample 4 ring points in sector 5) price=4.92; predicted=clean actual=clean
- [R9] executed R9:ring_sample:INT:6 (sample 4 ring points in sector 6) price=4.92; predicted=clean actual=clean
- [R10] executed R10:pm_hourly:S7 (hourly PRB for S7 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R11] executed R11:ring_sample:INT:7 (sample 4 ring points in sector 7) price=4.92; predicted=clean actual=contaminated
- [R12] boundary expansion forced in sector 7 (integrity refuted)
- [R13] spawned CAP:S3 (major exit for BG)
- [R13] executed R13:pm_hourly:S3 (hourly PRB for S3 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R14] executed R14:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=falls_below_theta actual=falls_below_theta
- [R15] killed CAP:S3 (no longer anyone's best alternative)
- [R15] no ticketed claims; idle round (stability check)
- [R16] no ticketed claims; idle round (stability check)