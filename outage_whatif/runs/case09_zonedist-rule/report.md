# What-if outage report — case case09, target S5

*Arm:* `zonedist/rule` — *outage window:* 2026-07-20T10:00:00 to 2026-07-20T18:00:00 (Monday, weekday)

## Overall verdict
**severe hole exists**

Stop reason: all tickets resolved; verdict unchanged for 2 rounds after 14 rounds; spend 121.03 of budget 420.0.

## Per-subregion verdicts and deciding claims

| subregion | pop | tier | severe | bottleneck | deciding evidence |
|---|---|---|---|---|---|
| BG | 29 | absorbable | no | - | COV:BG:supported; ROB:BG:undecided (0.207, 1.0); CAP:S6:supported mean=0.198 |
| V1 | 588 | hole | yes | coverage | COV:V1:refuted (0.0, 0.39); ROB:V1:supported (0.188, 0.812); CAP:S11:supported mean=0.373; CAP:S6:supported mean=0.198 |
| V2 | 178 | absorbable | no | - | COV:V2:supported (0.342, 1.0); ROB:V2:supported (0.095, 0.905); CAP:S11:supported mean=0.373; CAP:S8:supported mean=0.407 |
| V3 | 150 | degraded | no | robustness (S8) | COV:V3:supported (0.51, 1.0); ROB:V3:refuted (0.51, 1.0); CAP:S8:supported mean=0.407 |
| V4 | 140 | degraded | no | robustness (S2) | COV:V4:supported (0.51, 1.0); ROB:V4:refuted (0.51, 1.0); CAP:S2:supported mean=0.213 |
| V5 | 110 | hole | no | coverage | COV:V5:refuted (0.0, 0.49); ROB:V5:refuted (0.301, 0.954); CAP:S2:supported mean=0.213; CAP:S6:supported mean=0.198 |
| V6 | 60 | degraded | no | robustness (S2) | COV:V6:supported (0.51, 1.0); ROB:V6:refuted (0.51, 1.0); CAP:S2:supported mean=0.213 |

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
- Boundary expansions performed: 0.
- Target baseline RRC (reporting/validation only): mean 234.9 conn/h.

## Budget ledger

| round | action | kind | price | purpose | claim served |
|---|---|---|---|---|---|
| 0 | init:Track-1 initial sampling | coverage | 7.85 | Track-1 initial sampling | COV:V1 |
| 0 | init:Track-1 initial sampling | coverage | 7.85 | Track-1 initial sampling | COV:V2 |
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V3 |
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V4 |
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V5 |
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V6 |
| 0 | init:Track-2 fuse grid | coverage | 9.37 | Track-2 fuse grid | COV:BG |
| 1 | R1:ring_sample:INT:0 | ring_sample | 4.92 | resolve INT:0 | INT:0 |
| 2 | R2:ring_sample:INT:1 | ring_sample | 4.92 | resolve INT:1 | INT:1 |
| 3 | R3:ring_sample:INT:2 | ring_sample | 4.92 | resolve INT:2 | INT:2 |
| 4 | R4:pm_hourly:S6 | pm_hourly | 6.4 | resolve CAP:S6 | CAP:S6 |
| 5 | R5:ring_sample:INT:4 | ring_sample | 4.92 | resolve INT:4 | INT:4 |
| 6 | R6:ring_sample:INT:5 | ring_sample | 4.92 | resolve INT:5 | INT:5 |
| 7 | R7:pm_hourly:S11 | pm_hourly | 6.4 | resolve CAP:S11 | CAP:S11 |
| 8 | R8:ring_sample:INT:5 | ring_sample | 4.92 | resolve INT:5 | INT:5 |
| 9 | R9:ring_sample:INT:6 | ring_sample | 4.92 | resolve INT:6 | INT:6 |
| 10 | R10:pm_hourly:S8 | pm_hourly | 6.4 | resolve CAP:S8 | CAP:S8 |
| 11 | R11:ring_sample:INT:7 | ring_sample | 4.92 | resolve INT:7 | INT:7 |
| 12 | R12:ring_sample:INT:7 | ring_sample | 4.92 | resolve INT:7 | INT:7 |
| 13 | R13:pm_hourly:S2 | pm_hourly | 6.4 | resolve CAP:S2 | CAP:S2 |
| 14 | final:target_rrc | pm_hourly | 6.4 | target baseline RRC (reporting/validation only) | - |

**Total spent: 121.03 / 420.0**

## Agent ledgers
### agent1
- hit rate per grade: {'high': {'graded': 18, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 222, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 9, 'scored': 0, 'hits': 0, 'rate': None}}
- consecutive misses: 0; fuse trips: 0
- selection bias: only chosen rows get tested
### agent2
- hit rate per grade: {'high': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 9, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 4, 'scored': 4, 'hits': 4, 'rate': 1.0}}
- consecutive misses: 0; fuse trips: 0
- selection bias: only chosen rows get tested

## Event log
- [R1] spawned CAP:S11 (major exit for V1, V2)
- [R1] spawned CAP:S2 (major exit for V4, V5, V6)
- [R1] spawned CAP:S6 (major exit for BG, V1, V5)
- [R1] spawned CAP:S8 (major exit for V2, V3)
- [R1] executed R1:ring_sample:INT:0 (sample 4 ring points in sector 0) price=4.92; predicted=clean actual=clean
- [R2] executed R2:ring_sample:INT:1 (sample 4 ring points in sector 1) price=4.92; predicted=clean actual=clean
- [R3] executed R3:ring_sample:INT:2 (sample 4 ring points in sector 2) price=4.92; predicted=clean actual=clean
- [R4] executed R4:pm_hourly:S6 (hourly PRB for S6 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R5] executed R5:ring_sample:INT:4 (sample 4 ring points in sector 4) price=4.92; predicted=clean actual=clean
- [R6] agent2 rejected: top-quartile price requires a high-confidence grade (or a cheaply resolved prerequisite); got grade=low; re-prompting once
- [R6] agent2 still non-compliant (top-quartile price requires a high-confidence grade (or a cheaply resolved prerequisite); got grade=low); routing this round to the fallback rule
- [R6] executed R6:ring_sample:INT:5 (sample 4 ring points in sector 5) price=4.92; predicted=clean actual=still_undecided
- [R7] executed R7:pm_hourly:S11 (hourly PRB for S11 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R8] executed R8:ring_sample:INT:5 (sample 4 ring points in sector 5) price=4.92; predicted=clean actual=clean
- [R9] executed R9:ring_sample:INT:6 (sample 4 ring points in sector 6) price=4.92; predicted=clean actual=clean
- [R10] executed R10:pm_hourly:S8 (hourly PRB for S8 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R11] agent2 rejected: top-quartile price requires a high-confidence grade (or a cheaply resolved prerequisite); got grade=low; re-prompting once
- [R11] agent2 still non-compliant (top-quartile price requires a high-confidence grade (or a cheaply resolved prerequisite); got grade=low); routing this round to the fallback rule
- [R11] executed R11:ring_sample:INT:7 (sample 4 ring points in sector 7) price=4.92; predicted=clean actual=still_undecided
- [R12] agent2 rejected: top-quartile price requires a high-confidence grade (or a cheaply resolved prerequisite); got grade=low; re-prompting once
- [R12] agent2 still non-compliant (top-quartile price requires a high-confidence grade (or a cheaply resolved prerequisite); got grade=low); routing this round to the fallback rule
- [R12] executed R12:ring_sample:INT:7 (sample 4 ring points in sector 7) price=4.92; predicted=clean actual=clean
- [R13] executed R13:pm_hourly:S2 (hourly PRB for S2 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone