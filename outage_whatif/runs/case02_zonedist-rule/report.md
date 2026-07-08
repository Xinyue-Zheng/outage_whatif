# What-if outage report — case case02, target S5

*Arm:* `zonedist/rule` — *outage window:* 2026-07-21T10:00:00 to 2026-07-21T18:00:00 (Tuesday, weekday)

## Overall verdict
**locally degraded**

Stop reason: all tickets resolved; verdict unchanged for 2 rounds after 24 rounds; spend 178.57 of budget 420.0.

## Per-subregion verdicts and deciding claims

| subregion | pop | tier | severe | bottleneck | deciding evidence |
|---|---|---|---|---|---|
| BG | 37 | degraded | no | capacity (S8) | COV:BG:undecided (0.51, 1.0); ROB:BG:undecided (0.15, 0.85); CAP:S6:supported mean=0.424; CAP:S7:supported mean=0.436; CAP:S8:refuted mean=0.53 |
| V1 | 465 | degraded | no | robustness (S2) | COV:V1:supported (0.438, 1.0); ROB:V1:refuted (0.208, 0.939); CAP:S2:supported mean=0.425; CAP:S6:supported mean=0.424 |
| V2 | 316 | absorbable | no | - | COV:V2:supported (0.61, 1.0); ROB:V2:supported (0.188, 0.812); CAP:S2:supported mean=0.425; CAP:S3:supported mean=0.433 |
| V3 | 154 | degraded | no | robustness (S4) | COV:V3:supported (0.566, 1.0); ROB:V3:refuted (0.566, 1.0); CAP:S4:undecided |
| V4 | 114 | degraded | no | capacity (S8) | COV:V4:supported (0.51, 1.0); ROB:V4:refuted (0.51, 1.0); CAP:S8:refuted mean=0.53 |
| V5 | 71 | degraded | no | robustness (S6) | COV:V5:supported (0.438, 1.0); ROB:V5:refuted (0.438, 1.0); CAP:S6:supported mean=0.424 |
| V6 | 53 | degraded | no | robustness (S6) | COV:V6:supported (0.207, 1.0); ROB:V6:refuted (0.207, 1.0); CAP:S6:supported mean=0.424 |

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
- Settlements under P_min were not individually verified. (1 settlement(s), 31 people absorbed into the background region, which the background grid still covers.)
- Declared boundary: handover misconfiguration, transport bottlenecks, and all other factors absent from the inputs are outside every conclusion this system can draw.
- Boundary expansions performed: 2.
- Target baseline RRC (reporting/validation only): mean 295.6 conn/h.

## Budget ledger

| round | action | kind | price | purpose | claim served |
|---|---|---|---|---|---|
| 0 | init:Track-1 initial sampling | coverage | 3.54 | Track-1 initial sampling | COV:V1 |
| 0 | init:Track-1 initial sampling | coverage | 9.37 | Track-1 initial sampling | COV:V2 |
| 0 | init:Track-1 initial sampling | coverage | 6.37 | Track-1 initial sampling | COV:V3 |
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V4 |
| 0 | init:Track-1 initial sampling | coverage | 3.54 | Track-1 initial sampling | COV:V5 |
| 0 | init:Track-1 initial sampling | coverage | 2.22 | Track-1 initial sampling | COV:V6 |
| 0 | init:Track-2 fuse grid | coverage | 6.37 | Track-2 fuse grid | COV:BG |
| 1 | R1:expand:6 | coverage | 4.92 | boundary expansion resampling | INT:6 |
| 2 | R2:ring_sample:INT:0 | ring_sample | 4.92 | resolve INT:0 | INT:0 |
| 3 | R3:ring_sample:INT:0 | ring_sample | 4.92 | resolve INT:0 | INT:0 |
| 4 | R4:expand:0 | coverage | 4.92 | boundary expansion resampling | INT:0 |
| 5 | R5:ring_sample:INT:1 | ring_sample | 4.92 | resolve INT:1 | INT:1 |
| 6 | R6:pm_hourly:S6 | pm_hourly | 6.4 | resolve CAP:S6 | CAP:S6 |
| 7 | R7:ring_sample:INT:2 | ring_sample | 4.92 | resolve INT:2 | INT:2 |
| 8 | R8:pm_hourly:S2 | pm_hourly | 6.4 | resolve CAP:S2 | CAP:S2 |
| 9 | R9:ring_sample:INT:3 | ring_sample | 4.92 | resolve INT:3 | INT:3 |
| 10 | R10:pm_hourly:S8 | pm_hourly | 6.4 | resolve CAP:S8 | CAP:S8 |
| 11 | R11:pm_hourly:S7 | pm_hourly | 6.4 | resolve CAP:S7 | CAP:S7 |
| 12 | R12:pm_hourly:S8_c0 | pm_hourly | 6.4 | resolve CAP:S8:S8_c0 | CAP:S8:S8_c0 |
| 13 | R13:ring_sample:INT:4 | ring_sample | 4.92 | resolve INT:4 | INT:4 |
| 14 | R14:pm_hourly:S8_c1 | pm_hourly | 6.4 | resolve CAP:S8:S8_c1 | CAP:S8:S8_c1 |
| 15 | R15:pm_hourly:S8_c2 | pm_hourly | 6.4 | resolve CAP:S8:S8_c2 | CAP:S8:S8_c2 |
| 16 | R16:ring_sample:INT:5 | ring_sample | 4.92 | resolve INT:5 | INT:5 |
| 17 | R17:ring_sample:INT:5 | ring_sample | 4.92 | resolve INT:5 | INT:5 |
| 18 | R18:pm_15min:S8_c1 | pm_15min | 25.6 | resolve CAP:S8:S8_c1 | CAP:S8:S8_c1 |
| 19 | R19:pm_hourly:S3 | pm_hourly | 6.4 | resolve CAP:S3 | CAP:S3 |
| 20 | R20:ring_sample:INT:7 | ring_sample | 4.92 | resolve INT:7 | INT:7 |
| 21 | R21:ring_sample:INT:7 | ring_sample | 4.92 | resolve INT:7 | INT:7 |
| 24 | final:target_rrc | pm_hourly | 6.4 | target baseline RRC (reporting/validation only) | - |

**Total spent: 178.57 / 420.0**

## Agent ledgers
### agent1
- hit rate per grade: {'high': {'graded': 32, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 383, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 20, 'scored': 4, 'hits': 0, 'rate': 0.0}}
- consecutive misses: 0; fuse trips: 2
- selection bias: only chosen rows get tested
### agent2
- hit rate per grade: {'high': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 11, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 8, 'scored': 8, 'hits': 5, 'rate': 0.625}}
- consecutive misses: 0; fuse trips: 1
- selection bias: only chosen rows get tested

## Event log
- [R1] spawned CAP:S2 (major exit for V1, V2)
- [R1] spawned CAP:S3 (major exit for V2)
- [R1] spawned CAP:S4 (major exit for V3)
- [R1] spawned CAP:S6 (major exit for V1, V5, V6)
- [R1] spawned CAP:S7 (major exit for BG)
- [R1] spawned CAP:S8 (major exit for V4)
- [R1] boundary expansion forced in sector 6 (integrity refuted)
- [R2] executed R2:ring_sample:INT:0 (sample 4 ring points in sector 0) price=4.92; predicted=clean actual=still_undecided
- [R3] executed R3:ring_sample:INT:0 (sample 4 ring points in sector 0) price=4.92; predicted=clean actual=contaminated
- [R4] boundary expansion forced in sector 0 (integrity refuted)
- [R5] executed R5:ring_sample:INT:1 (sample 4 ring points in sector 1) price=4.92; predicted=clean actual=clean
- [R6] executed R6:pm_hourly:S6 (hourly PRB for S6 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R7] executed R7:ring_sample:INT:2 (sample 4 ring points in sector 2) price=4.92; predicted=clean actual=clean
- [R8] executed R8:pm_hourly:S2 (hourly PRB for S2 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R9] executed R9:ring_sample:INT:3 (sample 4 ring points in sector 3) price=4.92; predicted=clean actual=clean
- [R10] executed R10:pm_hourly:S8 (hourly PRB for S8 over the outage-matched window) price=6.4; predicted=middle_zone actual=middle_zone
- [R11] drilled down CAP:S8 -> 3 per-cell children
- [R11] executed R11:pm_hourly:S7 (hourly PRB for S7 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R12] executed R12:pm_hourly:S8_c0 (hourly PRB for S8_c0 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R13] executed R13:ring_sample:INT:4 (sample 4 ring points in sector 4) price=4.92; predicted=clean actual=clean
- [R14] executed R14:pm_hourly:S8_c1 (hourly PRB for S8_c1 over the outage-matched window) price=6.4; predicted=middle_zone actual=middle_zone
- [R15] executed R15:pm_hourly:S8_c2 (hourly PRB for S8_c2 over the outage-matched window) price=6.4; predicted=middle_zone actual=middle_zone
- [R16] agent2 fuse active: routed to baseline this round
- [R16] executed R16:ring_sample:INT:5 (sample 4 ring points in sector 5) price=4.92; predicted=clean actual=still_undecided
- [R17] executed R17:ring_sample:INT:5 (sample 4 ring points in sector 5) price=4.92; predicted=clean actual=clean
- [R18] executed R18:pm_15min:S8_c1 (15min PRB for S8_c1 over the outage-matched window) price=25.6; predicted=support actual=refute
- [R19] agent1 fuse active: routed to baseline this round
- [R19] executed R19:pm_hourly:S3 (hourly PRB for S3 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R20] executed R20:ring_sample:INT:7 (sample 4 ring points in sector 7) price=4.92; predicted=clean actual=still_undecided
- [R21] executed R21:ring_sample:INT:7 (sample 4 ring points in sector 7) price=4.92; predicted=clean actual=clean
- [R22] no ticketed claims; idle round (stability check)
- [R23] no ticketed claims; idle round (stability check)