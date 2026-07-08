# What-if outage report — case case10, target S5

*Arm:* `rule/rule` — *outage window:* 2026-07-23T18:00:00 to 2026-07-24T00:00:00 (Thursday, weekday)

## Overall verdict
**locally degraded**

Stop reason: all tickets resolved; verdict unchanged for 2 rounds after 39 rounds; spend 230.7 of budget 360.0.

## Per-subregion verdicts and deciding claims

| subregion | pop | tier | severe | bottleneck | deciding evidence |
|---|---|---|---|---|---|
| BG | 0 | degraded | no | capacity (S2) | COV:BG:undecided (0.646, 1.0); ROB:BG:undecided (0.082, 0.641); CAP:S2:refuted mean=0.618 |
| V1 | 1024 | degraded | no | capacity (S2) | COV:V1:supported (0.596, 0.982); ROB:V1:refuted (0.397, 0.892); CAP:S2:refuted mean=0.618; CAP:S4:undecided mean=0.66 |
| V2 | 432 | degraded | no | robustness (S4) | COV:V2:supported (0.566, 1.0); ROB:V2:refuted (0.566, 1.0); CAP:S4:undecided mean=0.66 |
| V3 | 173 | absorbable | no | - | COV:V3:supported; ROB:V3:refuted (0.207, 1.0); CAP:S12:undecided |

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
- Boundary expansions performed: 3.
- Target baseline RRC (reporting/validation only): mean 433.5 conn/h.

## Budget ledger

| round | action | kind | price | purpose | claim served |
|---|---|---|---|---|---|
| 0 | init:Track-1 initial sampling | coverage | 15.76 | Track-1 initial sampling | COV:V1 |
| 0 | init:Track-1 initial sampling | coverage | 6.37 | Track-1 initial sampling | COV:V2 |
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V3 |
| 0 | init:Track-2 fuse grid | coverage | 4.92 | Track-2 fuse grid | COV:BG |
| 1 | R1:pm_hourly:S4 | pm_hourly | 4.8 | resolve CAP:S4 | CAP:S4 |
| 2 | R2:ring_sample:INT:0 | ring_sample | 4.92 | resolve INT:0 | INT:0 |
| 3 | R3:ring_sample:INT:1 | ring_sample | 4.92 | resolve INT:1 | INT:1 |
| 4 | R4:expand:1 | coverage | 4.92 | boundary expansion resampling | INT:1 |
| 5 | R5:pm_hourly:S10 | pm_hourly | 4.8 | resolve CAP:S10 | CAP:S10 |
| 6 | R6:pm_hourly:S4_c0 | pm_hourly | 4.8 | resolve CAP:S4:S4_c0 | CAP:S4:S4_c0 |
| 7 | R7:pm_hourly:S10_c0 | pm_hourly | 4.8 | resolve CAP:S10:S10_c0 | CAP:S10:S10_c0 |
| 8 | R8:pm_hourly:S10_c1 | pm_hourly | 4.8 | resolve CAP:S10:S10_c1 | CAP:S10:S10_c1 |
| 9 | R9:pm_hourly:S10_c2 | pm_hourly | 4.8 | resolve CAP:S10:S10_c2 | CAP:S10:S10_c2 |
| 10 | R10:pm_hourly:S4_c1 | pm_hourly | 4.8 | resolve CAP:S4:S4_c1 | CAP:S4:S4_c1 |
| 11 | R11:pm_hourly:S4_c2 | pm_hourly | 4.8 | resolve CAP:S4:S4_c2 | CAP:S4:S4_c2 |
| 12 | R12:pm_hourly:S6 | pm_hourly | 4.8 | resolve CAP:S6 | CAP:S6 |
| 13 | R13:profile:S10:same_weekday | profile | 5.0 | judgment firming | CAP:S10 |
| 14 | R14:profile:S4:same_weekday | profile | 5.0 | judgment firming | CAP:S4 |
| 15 | R15:profile:S6:same_weekday | profile | 5.0 | judgment firming | CAP:S6 |
| 16 | R16:pm_hourly:S6_c0 | pm_hourly | 4.8 | resolve CAP:S6:S6_c0 | CAP:S6:S6_c0 |
| 17 | R17:pm_hourly:S6_c1 | pm_hourly | 4.8 | resolve CAP:S6:S6_c1 | CAP:S6:S6_c1 |
| 18 | R18:pm_hourly:S6_c2 | pm_hourly | 4.8 | resolve CAP:S6:S6_c2 | CAP:S6:S6_c2 |
| 19 | R19:pm_hourly:S8 | pm_hourly | 4.8 | resolve CAP:S8 | CAP:S8 |
| 20 | R20:pm_hourly:S8_c0 | pm_hourly | 4.8 | resolve CAP:S8:S8_c0 | CAP:S8:S8_c0 |
| 21 | R21:ring_sample:INT:2 | ring_sample | 4.92 | resolve INT:2 | INT:2 |
| 22 | R22:ring_sample:INT:3 | ring_sample | 4.92 | resolve INT:3 | INT:3 |
| 23 | R23:ring_sample:INT:4 | ring_sample | 4.92 | resolve INT:4 | INT:4 |
| 24 | R24:ring_sample:INT:4 | ring_sample | 4.92 | resolve INT:4 | INT:4 |
| 25 | R25:ring_sample:INT:5 | ring_sample | 4.92 | resolve INT:5 | INT:5 |
| 26 | R26:ring_sample:INT:6 | ring_sample | 4.92 | resolve INT:6 | INT:6 |
| 27 | R27:ring_sample:INT:6 | ring_sample | 4.92 | resolve INT:6 | INT:6 |
| 28 | R28:expand:6 | coverage | 4.92 | boundary expansion resampling | INT:6 |
| 29 | R29:ring_sample:INT:7 | ring_sample | 4.92 | resolve INT:7 | INT:7 |
| 30 | R30:expand:7 | coverage | 4.92 | boundary expansion resampling | INT:7 |
| 31 | R31:bg_sweep:COV:BG | bg_sweep | 9.37 | resolve COV:BG | COV:BG |
| 32 | R32:pm_hourly:S2 | pm_hourly | 4.8 | resolve CAP:S2 | CAP:S2 |
| 33 | R33:pm_hourly:S2_c0 | pm_hourly | 4.8 | resolve CAP:S2:S2_c0 | CAP:S2:S2_c0 |
| 34 | R34:pm_hourly:S2_c1 | pm_hourly | 4.8 | resolve CAP:S2:S2_c1 | CAP:S2:S2_c1 |
| 35 | R35:pm_hourly:S2_c2 | pm_hourly | 4.8 | resolve CAP:S2:S2_c2 | CAP:S2:S2_c2 |
| 36 | R36:pm_15min:S2_c0 | pm_15min | 19.2 | resolve CAP:S2:S2_c0 | CAP:S2:S2_c0 |
| 39 | final:target_rrc | pm_hourly | 4.8 | target baseline RRC (reporting/validation only) | - |

**Total spent: 230.7 / 360.0**

## Agent ledgers
### agent1
- hit rate per grade: {'high': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 1083, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}}
- consecutive misses: 0; fuse trips: 0
- selection bias: only chosen rows get tested
### agent2
- hit rate per grade: {'high': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 15, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 18, 'scored': 18, 'hits': 4, 'rate': 0.222}}
- consecutive misses: 1; fuse trips: 5
- selection bias: only chosen rows get tested

## Event log
- [R1] spawned CAP:S12 (major exit for V3)
- [R1] spawned CAP:S2 (major exit for V1)
- [R1] spawned CAP:S4 (major exit for BG, V1, V2)
- [R1] spawned CAP:S6 (major exit for BG)
- [R1] executed R1:pm_hourly:S4 (hourly PRB for S4 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R2] executed R2:ring_sample:INT:0 (sample 4 ring points in sector 0) price=4.92; predicted=clean actual=clean
- [R3] drilled down CAP:S4 -> 3 per-cell children
- [R3] executed R3:ring_sample:INT:1 (sample 4 ring points in sector 1) price=4.92; predicted=clean actual=contaminated
- [R4] boundary expansion forced in sector 1 (integrity refuted)
- [R5] spawned CAP:S10 (major exit for BG)
- [R5] spawned CAP:S8 (major exit for BG)
- [R5] executed R5:pm_hourly:S10 (hourly PRB for S10 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R6] agent2 fuse active: routed to baseline this round
- [R6] executed R6:pm_hourly:S4_c0 (hourly PRB for S4_c0 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R7] drilled down CAP:S10 -> 3 per-cell children
- [R7] executed R7:pm_hourly:S10_c0 (hourly PRB for S10_c0 over the outage-matched window) price=4.8; predicted=middle_zone actual=support_zone
- [R8] executed R8:pm_hourly:S10_c1 (hourly PRB for S10_c1 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R9] executed R9:pm_hourly:S10_c2 (hourly PRB for S10_c2 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R10] agent2 fuse active: routed to baseline this round
- [R10] executed R10:pm_hourly:S4_c1 (hourly PRB for S4_c1 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R11] executed R11:pm_hourly:S4_c2 (hourly PRB for S4_c2 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R12] agent2 fuse active: routed to baseline this round
- [R12] executed R12:pm_hourly:S6 (hourly PRB for S6 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R13] drilled down CAP:S6 -> 3 per-cell children
- [R13] executed R13:profile:S10:same_weekday (historical profile (same_weekday) for S10 — judgment-firming, changes no claim directly) price=5.0; predicted=anchor_confirms actual=anchor_shifts
- [R14] executed R14:profile:S4:same_weekday (historical profile (same_weekday) for S4 — judgment-firming, changes no claim directly) price=5.0; predicted=anchor_confirms actual=anchor_shifts
- [R15] executed R15:profile:S6:same_weekday (historical profile (same_weekday) for S6 — judgment-firming, changes no claim directly) price=5.0; predicted=anchor_confirms actual=anchor_shifts
- [R16] executed R16:pm_hourly:S6_c0 (hourly PRB for S6_c0 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R17] agent2 fuse active: routed to baseline this round
- [R17] executed R17:pm_hourly:S6_c1 (hourly PRB for S6_c1 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R18] executed R18:pm_hourly:S6_c2 (hourly PRB for S6_c2 over the outage-matched window) price=4.8; predicted=middle_zone actual=support_zone
- [R19] executed R19:pm_hourly:S8 (hourly PRB for S8 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R20] drilled down CAP:S8 -> 3 per-cell children
- [R20] executed R20:pm_hourly:S8_c0 (hourly PRB for S8_c0 over the outage-matched window) price=4.8; predicted=middle_zone actual=refute_zone
- [R21] executed R21:ring_sample:INT:2 (sample 4 ring points in sector 2) price=4.92; predicted=clean actual=clean
- [R22] executed R22:ring_sample:INT:3 (sample 4 ring points in sector 3) price=4.92; predicted=clean actual=clean
- [R23] executed R23:ring_sample:INT:4 (sample 4 ring points in sector 4) price=4.92; predicted=clean actual=still_undecided
- [R24] executed R24:ring_sample:INT:4 (sample 4 ring points in sector 4) price=4.92; predicted=clean actual=clean
- [R25] executed R25:ring_sample:INT:5 (sample 4 ring points in sector 5) price=4.92; predicted=clean actual=clean
- [R26] executed R26:ring_sample:INT:6 (sample 4 ring points in sector 6) price=4.92; predicted=clean actual=still_undecided
- [R27] executed R27:ring_sample:INT:6 (sample 4 ring points in sector 6) price=4.92; predicted=clean actual=contaminated
- [R28] boundary expansion forced in sector 6 (integrity refuted)
- [R29] executed R29:ring_sample:INT:7 (sample 4 ring points in sector 7) price=4.92; predicted=clean actual=contaminated
- [R30] boundary expansion forced in sector 7 (integrity refuted)
- [R31] killed CAP:S6 (no longer anyone's best alternative)
- [R31] killed CAP:S10 (no longer anyone's best alternative)
- [R31] killed CAP:S8 (no longer anyone's best alternative)
- [R31] executed R31:bg_sweep:COV:BG (background-grid sweep, 7 points) price=9.37; predicted=clears_theta actual=still_straddling
- [R32] executed R32:pm_hourly:S2 (hourly PRB for S2 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R33] drilled down CAP:S2 -> 3 per-cell children
- [R33] executed R33:pm_hourly:S2_c0 (hourly PRB for S2_c0 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R34] agent2 fuse active: routed to baseline this round
- [R34] executed R34:pm_hourly:S2_c1 (hourly PRB for S2_c1 over the outage-matched window) price=4.8; predicted=middle_zone actual=support_zone
- [R35] executed R35:pm_hourly:S2_c2 (hourly PRB for S2_c2 over the outage-matched window) price=4.8; predicted=middle_zone actual=middle_zone
- [R36] executed R36:pm_15min:S2_c0 (15min PRB for S2_c0 over the outage-matched window) price=19.2; predicted=support actual=refute
- [R37] no ticketed claims; idle round (stability check)
- [R38] no ticketed claims; idle round (stability check)