# What-if outage report — case case05, target S5

*Arm:* `rule/rule` — *outage window:* 2026-07-04T10:00:00 to 2026-07-04T18:00:00 (Saturday, holiday)

## Overall verdict
**severe hole exists**

Stop reason: all tickets resolved; verdict unchanged for 2 rounds after 24 rounds; spend 200.49 of budget 420.0.

## Per-subregion verdicts and deciding claims

| subregion | pop | tier | severe | bottleneck | deciding evidence |
|---|---|---|---|---|---|
| BG | 32 | degraded | no | capacity (S11) | COV:BG:undecided (0.301, 0.954); ROB:BG:undecided (0.046, 0.699); CAP:S11:refuted mean=0.583; CAP:S2:supported mean=0.337; CAP:S6:refuted mean=0.657; CAP:S8:undecided |
| V1 | 349 | hole | yes | coverage | COV:V1:refuted (0.118, 0.769); ROB:V1:supported (0.231, 0.882); CAP:S2:supported mean=0.337; CAP:S4:supported mean=0.383 |
| V2 | 213 | absorbable | no | - | COV:V2:supported; ROB:V2:supported |
| V3 | 150 | degraded | no | capacity (S6) | COV:V3:refuted (0.0, 0.562); ROB:V3:refuted (0.208, 0.939); CAP:S6:refuted mean=0.657; CAP:S9:undecided mean=0.658 |
| V4 | 111 | degraded | no | capacity (S11) | COV:V4:refuted (0.046, 0.699); ROB:V4:refuted (0.301, 0.954); CAP:S11:refuted mean=0.583; CAP:S6:refuted mean=0.657 |
| V5 | 96 | degraded | no | capacity (S6) | COV:V5:supported (0.51, 1.0); ROB:V5:refuted (0.51, 1.0); CAP:S6:refuted mean=0.657 |
| V6 | 91 | degraded | no | robustness (S2) | COV:V6:supported (0.51, 1.0); ROB:V6:refuted (0.51, 1.0); CAP:S2:supported mean=0.337 |
| V7 | 57 | degraded | no | capacity (S6) | COV:V7:supported (0.342, 1.0); ROB:V7:refuted (0.342, 1.0); CAP:S6:refuted mean=0.657 |

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
- Settlements under P_min were not individually verified. (0 settlement(s), 0 people absorbed into the background region, which the background grid still covers.)
- Declared boundary: handover misconfiguration, transport bottlenecks, and all other factors absent from the inputs are outside every conclusion this system can draw.
- Boundary expansions performed: 1.
- Target baseline RRC (reporting/validation only): mean 406.4 conn/h.

## Budget ledger

| round | action | kind | price | purpose | claim served |
|---|---|---|---|---|---|
| 0 | init:Track-1 initial sampling | coverage | 6.37 | Track-1 initial sampling | COV:V1 |
| 0 | init:Track-1 initial sampling | coverage | 6.37 | Track-1 initial sampling | COV:V2 |
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V3 |
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V4 |
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V5 |
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V6 |
| 0 | init:Track-1 initial sampling | coverage | 2.22 | Track-1 initial sampling | COV:V7 |
| 0 | init:Track-2 fuse grid | coverage | 6.37 | Track-2 fuse grid | COV:BG |
| 1 | R1:ring_sample:INT:0 | ring_sample | 4.92 | resolve INT:0 | INT:0 |
| 2 | R2:ring_sample:INT:1 | ring_sample | 4.92 | resolve INT:1 | INT:1 |
| 3 | R3:ring_sample:INT:2 | ring_sample | 4.92 | resolve INT:2 | INT:2 |
| 4 | R4:expand:2 | coverage | 4.92 | boundary expansion resampling | INT:2 |
| 5 | R5:pm_hourly:S6 | pm_hourly | 6.4 | resolve CAP:S6 | CAP:S6 |
| 6 | R6:pm_hourly:S6_c0 | pm_hourly | 6.4 | resolve CAP:S6:S6_c0 | CAP:S6:S6_c0 |
| 7 | R7:pm_hourly:S6_c1 | pm_hourly | 6.4 | resolve CAP:S6:S6_c1 | CAP:S6:S6_c1 |
| 8 | R8:pm_hourly:S6_c2 | pm_hourly | 6.4 | resolve CAP:S6:S6_c2 | CAP:S6:S6_c2 |
| 9 | R9:pm_hourly:S2 | pm_hourly | 6.4 | resolve CAP:S2 | CAP:S2 |
| 10 | R10:ring_sample:INT:3 | ring_sample | 4.92 | resolve INT:3 | INT:3 |
| 11 | R11:ring_sample:INT:4 | ring_sample | 4.92 | resolve INT:4 | INT:4 |
| 12 | R12:pm_hourly:S11 | pm_hourly | 6.4 | resolve CAP:S11 | CAP:S11 |
| 13 | R13:pm_hourly:S11_c0 | pm_hourly | 6.4 | resolve CAP:S11:S11_c0 | CAP:S11:S11_c0 |
| 14 | R14:pm_hourly:S11_c1 | pm_hourly | 6.4 | resolve CAP:S11:S11_c1 | CAP:S11:S11_c1 |
| 15 | R15:pm_hourly:S9 | pm_hourly | 6.4 | resolve CAP:S9 | CAP:S9 |
| 16 | R16:pm_hourly:S9_c0 | pm_hourly | 6.4 | resolve CAP:S9:S9_c0 | CAP:S9:S9_c0 |
| 17 | R17:pm_hourly:S9_c1 | pm_hourly | 6.4 | resolve CAP:S9:S9_c1 | CAP:S9:S9_c1 |
| 18 | R18:pm_hourly:S9_c2 | pm_hourly | 6.4 | resolve CAP:S9:S9_c2 | CAP:S9:S9_c2 |
| 19 | R19:pm_15min:S6_c0 | pm_15min | 25.6 | resolve CAP:S6:S6_c0 | CAP:S6:S6_c0 |
| 20 | R20:ring_sample:INT:5 | ring_sample | 4.92 | resolve INT:5 | INT:5 |
| 21 | R21:ring_sample:INT:6 | ring_sample | 4.92 | resolve INT:6 | INT:6 |
| 22 | R22:pm_hourly:S4 | pm_hourly | 6.4 | resolve CAP:S4 | CAP:S4 |
| 23 | R23:ring_sample:INT:7 | ring_sample | 4.92 | resolve INT:7 | INT:7 |
| 24 | final:target_rrc | pm_hourly | 6.4 | target baseline RRC (reporting/validation only) | - |

**Total spent: 200.49 / 420.0**

## Agent ledgers
### agent1
- hit rate per grade: {'high': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 705, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}}
- consecutive misses: 0; fuse trips: 0
- selection bias: only chosen rows get tested
### agent2
- hit rate per grade: {'high': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 9, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 13, 'scored': 13, 'hits': 5, 'rate': 0.385}}
- consecutive misses: 0; fuse trips: 3
- selection bias: only chosen rows get tested

## Event log
- [R1] spawned CAP:S11 (major exit for BG, V4)
- [R1] spawned CAP:S2 (major exit for BG, V1, V6)
- [R1] spawned CAP:S4 (major exit for V1)
- [R1] spawned CAP:S6 (major exit for BG, V3, V4, V5, V7)
- [R1] spawned CAP:S9 (major exit for V3)
- [R1] executed R1:ring_sample:INT:0 (sample 4 ring points in sector 0) price=4.92; predicted=clean actual=clean
- [R2] executed R2:ring_sample:INT:1 (sample 4 ring points in sector 1) price=4.92; predicted=clean actual=clean
- [R3] executed R3:ring_sample:INT:2 (sample 4 ring points in sector 2) price=4.92; predicted=clean actual=contaminated
- [R4] boundary expansion forced in sector 2 (integrity refuted)
- [R5] spawned CAP:S8 (major exit for BG)
- [R5] executed R5:pm_hourly:S6 (hourly PRB for S6 over the outage-matched window) price=6.4; predicted=middle_zone actual=middle_zone
- [R6] drilled down CAP:S6 -> 3 per-cell children
- [R6] executed R6:pm_hourly:S6_c0 (hourly PRB for S6_c0 over the outage-matched window) price=6.4; predicted=middle_zone actual=middle_zone
- [R7] agent2 fuse active: routed to baseline this round
- [R7] executed R7:pm_hourly:S6_c1 (hourly PRB for S6_c1 over the outage-matched window) price=6.4; predicted=middle_zone actual=middle_zone
- [R8] executed R8:pm_hourly:S6_c2 (hourly PRB for S6_c2 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R9] executed R9:pm_hourly:S2 (hourly PRB for S2 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R10] executed R10:ring_sample:INT:3 (sample 4 ring points in sector 3) price=4.92; predicted=clean actual=clean
- [R11] executed R11:ring_sample:INT:4 (sample 4 ring points in sector 4) price=4.92; predicted=clean actual=clean
- [R12] executed R12:pm_hourly:S11 (hourly PRB for S11 over the outage-matched window) price=6.4; predicted=middle_zone actual=middle_zone
- [R13] drilled down CAP:S11 -> 3 per-cell children
- [R13] executed R13:pm_hourly:S11_c0 (hourly PRB for S11_c0 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R14] executed R14:pm_hourly:S11_c1 (hourly PRB for S11_c1 over the outage-matched window) price=6.4; predicted=middle_zone actual=refute_zone
- [R15] executed R15:pm_hourly:S9 (hourly PRB for S9 over the outage-matched window) price=6.4; predicted=middle_zone actual=middle_zone
- [R16] drilled down CAP:S9 -> 3 per-cell children
- [R16] executed R16:pm_hourly:S9_c0 (hourly PRB for S9_c0 over the outage-matched window) price=6.4; predicted=middle_zone actual=middle_zone
- [R17] agent2 fuse active: routed to baseline this round
- [R17] executed R17:pm_hourly:S9_c1 (hourly PRB for S9_c1 over the outage-matched window) price=6.4; predicted=middle_zone actual=middle_zone
- [R18] executed R18:pm_hourly:S9_c2 (hourly PRB for S9_c2 over the outage-matched window) price=6.4; predicted=middle_zone actual=middle_zone
- [R19] agent2 fuse active: routed to baseline this round
- [R19] executed R19:pm_15min:S6_c0 (15min PRB for S6_c0 over the outage-matched window) price=25.6; predicted=refute actual=refute
- [R20] executed R20:ring_sample:INT:5 (sample 4 ring points in sector 5) price=4.92; predicted=clean actual=clean
- [R21] executed R21:ring_sample:INT:6 (sample 4 ring points in sector 6) price=4.92; predicted=clean actual=clean
- [R22] executed R22:pm_hourly:S4 (hourly PRB for S4 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R23] executed R23:ring_sample:INT:7 (sample 4 ring points in sector 7) price=4.92; predicted=clean actual=clean