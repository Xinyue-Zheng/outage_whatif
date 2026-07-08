# What-if outage report — case case08, target S5

*Arm:* `rule/rule` — *outage window:* 2026-07-26T10:00:00 to 2026-07-26T16:00:00 (Sunday, sun)

## Overall verdict
**severe hole exists**

Stop reason: all tickets resolved; verdict unchanged for 2 rounds after 21 rounds; spend 123.56 of budget 420.0.

## Per-subregion verdicts and deciding claims

| subregion | pop | tier | severe | bottleneck | deciding evidence |
|---|---|---|---|---|---|
| BG | 29 | hole | no | coverage | COV:BG:refuted (0.354, 0.879); ROB:BG:undecided (0.267, 0.811); CAP:S2:supported mean=0.177; CAP:S6:supported mean=0.164 |
| V1 | 478 | hole | yes | coverage | COV:V1:refuted (0.0, 0.49); ROB:V1:refuted (0.301, 0.954); CAP:S7:supported mean=0.164; CAP:S8:supported mean=0.185 |
| V2 | 124 | degraded | no | robustness (S6) | COV:V2:supported (0.51, 1.0); ROB:V2:refuted (0.51, 1.0); CAP:S6:supported mean=0.164 |
| V3 | 98 | degraded | no | robustness (S6) | COV:V3:supported (0.51, 1.0); ROB:V3:refuted (0.51, 1.0); CAP:S6:supported mean=0.164 |
| V4 | 83 | degraded | no | robustness (S2) | COV:V4:supported (0.438, 1.0); ROB:V4:refuted (0.438, 1.0); CAP:S2:supported mean=0.177 |

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
- Settlements under P_min were not individually verified. (1 settlement(s), 29 people absorbed into the background region, which the background grid still covers.)
- Declared boundary: handover misconfiguration, transport bottlenecks, and all other factors absent from the inputs are outside every conclusion this system can draw.
- Boundary expansions performed: 3.
- Target baseline RRC (reporting/validation only): mean 147.6 conn/h.

## Budget ledger

| round | action | kind | price | purpose | claim served |
|---|---|---|---|---|---|
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V1 |
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V2 |
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V3 |
| 0 | init:Track-1 initial sampling | coverage | 3.54 | Track-1 initial sampling | COV:V4 |
| 0 | init:Track-2 fuse grid | coverage | 6.37 | Track-2 fuse grid | COV:BG |
| 1 | R1:expand:0 | coverage | 4.92 | boundary expansion resampling | INT:0 |
| 2 | R2:ring_sample:INT:1 | ring_sample | 4.92 | resolve INT:1 | INT:1 |
| 3 | R3:ring_sample:INT:2 | ring_sample | 4.92 | resolve INT:2 | INT:2 |
| 4 | R4:ring_sample:INT:3 | ring_sample | 4.92 | resolve INT:3 | INT:3 |
| 5 | R5:pm_hourly:S8 | pm_hourly | 4.8 | resolve CAP:S8 | CAP:S8 |
| 6 | R6:ring_sample:INT:4 | ring_sample | 4.92 | resolve INT:4 | INT:4 |
| 7 | R7:ring_sample:INT:5 | ring_sample | 4.92 | resolve INT:5 | INT:5 |
| 8 | R8:expand:5 | coverage | 4.92 | boundary expansion resampling | INT:5 |
| 9 | R9:ring_sample:INT:5 | ring_sample | 4.92 | resolve INT:5 | INT:5 |
| 10 | R10:pm_hourly:S7 | pm_hourly | 4.8 | resolve CAP:S7 | CAP:S7 |
| 11 | R11:ring_sample:INT:6 | ring_sample | 4.92 | resolve INT:6 | INT:6 |
| 12 | R12:ring_sample:INT:6 | ring_sample | 4.92 | resolve INT:6 | INT:6 |
| 13 | R13:ring_sample:INT:7 | ring_sample | 4.92 | resolve INT:7 | INT:7 |
| 14 | R14:expand:7 | coverage | 4.92 | boundary expansion resampling | INT:7 |
| 15 | R15:pm_hourly:S6 | pm_hourly | 4.8 | resolve CAP:S6 | CAP:S6 |
| 16 | R16:pm_hourly:S2 | pm_hourly | 4.8 | resolve CAP:S2 | CAP:S2 |
| 17 | R17:ring_sample:INT:7 | ring_sample | 4.92 | resolve INT:7 | INT:7 |
| 18 | R18:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 21 | final:target_rrc | pm_hourly | 4.8 | target baseline RRC (reporting/validation only) | - |

**Total spent: 123.56 / 420.0**

## Agent ledgers
### agent1
- hit rate per grade: {'high': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 216, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}}
- consecutive misses: 0; fuse trips: 0
- selection bias: only chosen rows get tested
### agent2
- hit rate per grade: {'high': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 11, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 4, 'scored': 4, 'hits': 4, 'rate': 1.0}}
- consecutive misses: 0; fuse trips: 0
- selection bias: only chosen rows get tested

## Event log
- [R1] spawned CAP:S2 (major exit for BG, V4)
- [R1] spawned CAP:S6 (major exit for V2, V3)
- [R1] spawned CAP:S7 (major exit for V1)
- [R1] spawned CAP:S8 (major exit for BG, V1)
- [R1] boundary expansion forced in sector 0 (integrity refuted)
- [R2] executed R2:ring_sample:INT:1 (sample 4 ring points in sector 1) price=4.92; predicted=clean actual=clean
- [R3] executed R3:ring_sample:INT:2 (sample 4 ring points in sector 2) price=4.92; predicted=clean actual=clean
- [R4] executed R4:ring_sample:INT:3 (sample 4 ring points in sector 3) price=4.92; predicted=clean actual=clean
- [R5] executed R5:pm_hourly:S8 (hourly PRB for S8 over the outage-matched window) price=4.8; predicted=middle_zone actual=support_zone
- [R6] executed R6:ring_sample:INT:4 (sample 4 ring points in sector 4) price=4.92; predicted=clean actual=clean
- [R7] executed R7:ring_sample:INT:5 (sample 4 ring points in sector 5) price=4.92; predicted=clean actual=contaminated
- [R8] boundary expansion forced in sector 5 (integrity refuted)
- [R9] executed R9:ring_sample:INT:5 (sample 4 ring points in sector 5) price=4.92; predicted=clean actual=clean
- [R10] executed R10:pm_hourly:S7 (hourly PRB for S7 over the outage-matched window) price=4.8; predicted=middle_zone actual=support_zone
- [R11] executed R11:ring_sample:INT:6 (sample 4 ring points in sector 6) price=4.92; predicted=clean actual=still_undecided
- [R12] executed R12:ring_sample:INT:6 (sample 4 ring points in sector 6) price=4.92; predicted=clean actual=clean
- [R13] executed R13:ring_sample:INT:7 (sample 4 ring points in sector 7) price=4.92; predicted=clean actual=contaminated
- [R14] boundary expansion forced in sector 7 (integrity refuted)
- [R15] executed R15:pm_hourly:S6 (hourly PRB for S6 over the outage-matched window) price=4.8; predicted=middle_zone actual=support_zone
- [R16] executed R16:pm_hourly:S2 (hourly PRB for S2 over the outage-matched window) price=4.8; predicted=middle_zone actual=support_zone
- [R17] executed R17:ring_sample:INT:7 (sample 4 ring points in sector 7) price=4.92; predicted=clean actual=clean
- [R18] executed R18:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=falls_below_theta actual=falls_below_theta
- [R19] no ticketed claims; idle round (stability check)
- [R20] no ticketed claims; idle round (stability check)