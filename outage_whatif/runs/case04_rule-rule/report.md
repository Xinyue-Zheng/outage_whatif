# What-if outage report — case case04, target S5

*Arm:* `rule/rule` — *outage window:* 2026-07-22T17:00:00 to 2026-07-22T23:00:00 (Wednesday, weekday)

## Overall verdict
**locally degraded**

Stop reason: all tickets resolved; verdict unchanged for 2 rounds after 32 rounds; spend 220.9 of budget 420.0.

## Per-subregion verdicts and deciding claims

| subregion | pop | tier | severe | bottleneck | deciding evidence |
|---|---|---|---|---|---|
| BG | 140 | degraded | no | capacity (S10) | COV:BG:undecided (0.529, 0.978); ROB:BG:undecided (0.137, 0.694); CAP:S10:refuted mean=0.679; CAP:S2:undecided mean=0.536; CAP:S6:refuted mean=0.657 |
| V1 | 686 | degraded | no | robustness (S2) | COV:V1:supported (0.51, 1.0); ROB:V1:refuted (0.51, 1.0); CAP:S2:undecided mean=0.536 |
| V2 | 172 | absorbable | no | - | COV:V2:supported; ROB:V2:refuted (0.207, 1.0); CAP:S4:undecided mean=0.53 |
| V3 | 164 | degraded | no | capacity (S6) | COV:V3:refuted (0.061, 0.792); ROB:V3:refuted (0.438, 1.0); CAP:S6:refuted mean=0.657 |
| V4 | 110 | absorbable | no | - | COV:V4:supported; ROB:V4:supported |
| V5 | 61 | degraded | no | robustness (S4) | COV:V5:supported (0.207, 1.0); ROB:V5:refuted (0.207, 1.0); CAP:S4:undecided mean=0.53 |

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
- Settlements under P_min were not individually verified. (1 settlement(s), 25 people absorbed into the background region, which the background grid still covers.)
- Declared boundary: handover misconfiguration, transport bottlenecks, and all other factors absent from the inputs are outside every conclusion this system can draw.
- Boundary expansions performed: 3.
- Target baseline RRC (reporting/validation only): mean 387.2 conn/h.

## Budget ledger

| round | action | kind | price | purpose | claim served |
|---|---|---|---|---|---|
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V1 |
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V2 |
| 0 | init:Track-1 initial sampling | coverage | 3.54 | Track-1 initial sampling | COV:V3 |
| 0 | init:Track-1 initial sampling | coverage | 6.37 | Track-1 initial sampling | COV:V4 |
| 0 | init:Track-1 initial sampling | coverage | 2.22 | Track-1 initial sampling | COV:V5 |
| 0 | init:Track-2 fuse grid | coverage | 9.37 | Track-2 fuse grid | COV:BG |
| 1 | R1:ring_sample:INT:0 | ring_sample | 4.92 | resolve INT:0 | INT:0 |
| 2 | R2:expand:0 | coverage | 4.92 | boundary expansion resampling | INT:0 |
| 3 | R3:pm_hourly:S2 | pm_hourly | 4.8 | resolve CAP:S2 | CAP:S2 |
| 4 | R4:pm_hourly:S6 | pm_hourly | 4.8 | resolve CAP:S6 | CAP:S6 |
| 5 | R5:pm_hourly:S6_c0 | pm_hourly | 4.8 | resolve CAP:S6:S6_c0 | CAP:S6:S6_c0 |
| 6 | R6:pm_hourly:S6_c1 | pm_hourly | 4.8 | resolve CAP:S6:S6_c1 | CAP:S6:S6_c1 |
| 7 | R7:pm_hourly:S6_c2 | pm_hourly | 4.8 | resolve CAP:S6:S6_c2 | CAP:S6:S6_c2 |
| 8 | R8:ring_sample:INT:0 | ring_sample | 4.92 | resolve INT:0 | INT:0 |
| 9 | R9:pm_hourly:S4 | pm_hourly | 4.8 | resolve CAP:S4 | CAP:S4 |
| 10 | R10:profile:S2:same_weekday | profile | 5.0 | judgment firming | CAP:S2 |
| 11 | R11:profile:S4:same_weekday | profile | 5.0 | judgment firming | CAP:S4 |
| 12 | R12:profile:S6:same_weekday | profile | 5.0 | judgment firming | CAP:S6 |
| 13 | R13:pm_hourly:S10 | pm_hourly | 4.8 | resolve CAP:S10 | CAP:S10 |
| 14 | R14:pm_hourly:S10_c0 | pm_hourly | 4.8 | resolve CAP:S10:S10_c0 | CAP:S10:S10_c0 |
| 15 | R15:profile:S10:same_weekday | profile | 5.0 | judgment firming | CAP:S10 |
| 16 | R16:pm_hourly:S10_c1 | pm_hourly | 4.8 | resolve CAP:S10:S10_c1 | CAP:S10:S10_c1 |
| 17 | R17:ring_sample:INT:1 | ring_sample | 4.92 | resolve INT:1 | INT:1 |
| 18 | R18:ring_sample:INT:1 | ring_sample | 4.92 | resolve INT:1 | INT:1 |
| 19 | R19:ring_sample:INT:2 | ring_sample | 4.92 | resolve INT:2 | INT:2 |
| 20 | R20:ring_sample:INT:3 | ring_sample | 4.92 | resolve INT:3 | INT:3 |
| 21 | R21:expand:3 | coverage | 4.92 | boundary expansion resampling | INT:3 |
| 22 | R22:ring_sample:INT:4 | ring_sample | 4.92 | resolve INT:4 | INT:4 |
| 23 | R23:ring_sample:INT:5 | ring_sample | 4.92 | resolve INT:5 | INT:5 |
| 24 | R24:pm_15min:S6_c0 | pm_15min | 19.2 | resolve CAP:S6:S6_c0 | CAP:S6:S6_c0 |
| 25 | R25:ring_sample:INT:6 | ring_sample | 4.92 | resolve INT:6 | INT:6 |
| 26 | R26:pm_15min:S6_c1 | pm_15min | 19.2 | resolve CAP:S6:S6_c1 | CAP:S6:S6_c1 |
| 27 | R27:ring_sample:INT:7 | ring_sample | 4.92 | resolve INT:7 | INT:7 |
| 28 | R28:expand:7 | coverage | 4.92 | boundary expansion resampling | INT:7 |
| 29 | R29:pm_15min:S6_c2 | pm_15min | 19.2 | resolve CAP:S6:S6_c2 | CAP:S6:S6_c2 |
| 32 | final:target_rrc | pm_hourly | 4.8 | target baseline RRC (reporting/validation only) | - |

**Total spent: 220.9 / 420.0**

## Agent ledgers
### agent1
- hit rate per grade: {'high': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 1104, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}}
- consecutive misses: 0; fuse trips: 0
- selection bias: only chosen rows get tested
### agent2
- hit rate per grade: {'high': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 17, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 9, 'scored': 9, 'hits': 1, 'rate': 0.111}}
- consecutive misses: 0; fuse trips: 4
- selection bias: only chosen rows get tested

## Event log
- [R1] spawned CAP:S10 (major exit for BG)
- [R1] spawned CAP:S2 (major exit for BG, V1)
- [R1] spawned CAP:S4 (major exit for BG, V2, V5)
- [R1] spawned CAP:S6 (major exit for V3)
- [R1] executed R1:ring_sample:INT:0 (sample 4 ring points in sector 0) price=4.92; predicted=clean actual=contaminated
- [R2] boundary expansion forced in sector 0 (integrity refuted)
- [R3] executed R3:pm_hourly:S2 (hourly PRB for S2 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R4] drilled down CAP:S2 -> 3 per-cell children
- [R4] executed R4:pm_hourly:S6 (hourly PRB for S6 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R5] drilled down CAP:S6 -> 3 per-cell children
- [R5] agent2 fuse active: routed to baseline this round
- [R5] executed R5:pm_hourly:S6_c0 (hourly PRB for S6_c0 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R6] executed R6:pm_hourly:S6_c1 (hourly PRB for S6_c1 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R7] agent2 fuse active: routed to baseline this round
- [R7] executed R7:pm_hourly:S6_c2 (hourly PRB for S6_c2 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R8] executed R8:ring_sample:INT:0 (sample 4 ring points in sector 0) price=4.92; predicted=clean actual=clean
- [R9] executed R9:pm_hourly:S4 (hourly PRB for S4 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R10] drilled down CAP:S4 -> 3 per-cell children
- [R10] agent2 fuse active: routed to baseline this round
- [R10] executed R10:profile:S2:same_weekday (historical profile (same_weekday) for S2 — judgment-firming, changes no claim directly) price=5.0; predicted=anchor_confirms actual=anchor_confirms
- [R11] executed R11:profile:S4:same_weekday (historical profile (same_weekday) for S4 — judgment-firming, changes no claim directly) price=5.0; predicted=anchor_confirms actual=anchor_confirms
- [R12] executed R12:profile:S6:same_weekday (historical profile (same_weekday) for S6 — judgment-firming, changes no claim directly) price=5.0; predicted=anchor_confirms actual=anchor_confirms
- [R13] executed R13:pm_hourly:S10 (hourly PRB for S10 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R14] drilled down CAP:S10 -> 3 per-cell children
- [R14] executed R14:pm_hourly:S10_c0 (hourly PRB for S10_c0 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R15] agent2 fuse active: routed to baseline this round
- [R15] executed R15:profile:S10:same_weekday (historical profile (same_weekday) for S10 — judgment-firming, changes no claim directly) price=5.0; predicted=anchor_confirms actual=anchor_confirms
- [R16] executed R16:pm_hourly:S10_c1 (hourly PRB for S10_c1 over the outage-matched window) price=4.8; predicted=middle_zone actual=refute_zone
- [R17] executed R17:ring_sample:INT:1 (sample 4 ring points in sector 1) price=4.92; predicted=clean actual=still_undecided
- [R18] executed R18:ring_sample:INT:1 (sample 4 ring points in sector 1) price=4.92; predicted=clean actual=clean
- [R19] executed R19:ring_sample:INT:2 (sample 4 ring points in sector 2) price=4.92; predicted=clean actual=clean
- [R20] executed R20:ring_sample:INT:3 (sample 4 ring points in sector 3) price=4.92; predicted=clean actual=contaminated
- [R21] boundary expansion forced in sector 3 (integrity refuted)
- [R22] executed R22:ring_sample:INT:4 (sample 4 ring points in sector 4) price=4.92; predicted=clean actual=clean
- [R23] executed R23:ring_sample:INT:5 (sample 4 ring points in sector 5) price=4.92; predicted=clean actual=clean
- [R24] executed R24:pm_15min:S6_c0 (15min PRB for S6_c0 over the outage-matched window) price=19.2; predicted=support actual=support
- [R25] executed R25:ring_sample:INT:6 (sample 4 ring points in sector 6) price=4.92; predicted=clean actual=clean
- [R26] executed R26:pm_15min:S6_c1 (15min PRB for S6_c1 over the outage-matched window) price=19.2; predicted=support actual=support
- [R27] executed R27:ring_sample:INT:7 (sample 4 ring points in sector 7) price=4.92; predicted=clean actual=contaminated
- [R28] boundary expansion forced in sector 7 (integrity refuted)
- [R29] executed R29:pm_15min:S6_c2 (15min PRB for S6_c2 over the outage-matched window) price=19.2; predicted=support actual=refute
- [R30] no ticketed claims; idle round (stability check)
- [R31] no ticketed claims; idle round (stability check)