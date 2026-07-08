# What-if outage report — case case07, target S5

*Arm:* `zonedist/rule` — *outage window:* 2026-07-25T09:00:00 to 2026-07-25T21:00:00 (Saturday, sat)

## Overall verdict
**locally degraded**

Stop reason: all tickets resolved; verdict unchanged for 2 rounds after 33 rounds; spend 362.08 of budget 500.0.

## Per-subregion verdicts and deciding claims

| subregion | pop | tier | severe | bottleneck | deciding evidence |
|---|---|---|---|---|---|
| BG | 36 | degraded | no | capacity (S6) | COV:BG:undecided (0.686, 0.971); ROB:BG:supported (0.118, 0.488); CAP:S4:supported mean=0.41; CAP:S6:refuted mean=0.555; CAP:S8:supported mean=0.513 |
| V1 | 525 | degraded | no | robustness (S4) | COV:V1:supported (0.438, 1.0); ROB:V1:refuted (0.438, 1.0); CAP:S4:supported mean=0.41 |
| V2 | 355 | degraded | no | capacity (S6) | COV:V2:supported (0.438, 1.0); ROB:V2:refuted (0.208, 0.939); CAP:S6:refuted mean=0.555; CAP:S8:supported mean=0.513 |
| V3 | 274 | degraded | no | robustness (S1) | COV:V3:supported (0.438, 1.0); ROB:V3:refuted (0.208, 0.939); CAP:S1:undecided; CAP:S4:supported mean=0.41 |
| V4 | 200 | degraded | no | robustness (S4) | COV:V4:supported (0.51, 1.0); ROB:V4:refuted (0.51, 1.0); CAP:S4:supported mean=0.41 |
| V5 | 136 | degraded | no | robustness (S8) | COV:V5:supported (0.676, 1.0); ROB:V5:refuted (0.676, 1.0); CAP:S8:supported mean=0.513 |
| V6 | 72 | degraded | no | robustness (S8) | COV:V6:supported (0.342, 1.0); ROB:V6:refuted (0.342, 1.0); CAP:S8:supported mean=0.513 |

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
- Boundary expansions performed: 3.
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
| 2 | R2:coverage_densify:COV:V5 | coverage_densify | 2.22 | resolve COV:V5 | COV:V5 |
| 3 | R3:ring_sample:INT:0 | ring_sample | 4.92 | resolve INT:0 | INT:0 |
| 4 | R4:expand:0 | coverage | 4.92 | boundary expansion resampling | INT:0 |
| 5 | R5:ring_sample:INT:1 | ring_sample | 4.92 | resolve INT:1 | INT:1 |
| 6 | R6:expand:1 | coverage | 4.92 | boundary expansion resampling | INT:1 |
| 7 | R7:ring_sample:INT:3 | ring_sample | 4.92 | resolve INT:3 | INT:3 |
| 8 | R8:pm_hourly:S8 | pm_hourly | 9.6 | resolve CAP:S8 | CAP:S8 |
| 9 | R9:pm_hourly:S12 | pm_hourly | 9.6 | resolve CAP:S12 | CAP:S12 |
| 10 | R10:pm_hourly:S2 | pm_hourly | 9.6 | resolve CAP:S2 | CAP:S2 |
| 11 | R11:ring_sample:INT:4 | ring_sample | 4.92 | resolve INT:4 | INT:4 |
| 12 | R12:ring_sample:INT:5 | ring_sample | 4.92 | resolve INT:5 | INT:5 |
| 13 | R13:pm_hourly:S8_c0 | pm_hourly | 9.6 | resolve CAP:S8:S8_c0 | CAP:S8:S8_c0 |
| 14 | R14:pm_hourly:S8_c1 | pm_hourly | 9.6 | resolve CAP:S8:S8_c1 | CAP:S8:S8_c1 |
| 15 | R15:pm_hourly:S8_c2 | pm_hourly | 9.6 | resolve CAP:S8:S8_c2 | CAP:S8:S8_c2 |
| 16 | R16:ring_sample:INT:6 | ring_sample | 4.92 | resolve INT:6 | INT:6 |
| 17 | R17:ring_sample:INT:7 | ring_sample | 4.92 | resolve INT:7 | INT:7 |
| 18 | R18:ring_sample:INT:7 | ring_sample | 4.92 | resolve INT:7 | INT:7 |
| 19 | R19:pm_15min:S8_c1 | pm_15min | 38.4 | resolve CAP:S8:S8_c1 | CAP:S8:S8_c1 |
| 20 | R20:pm_15min:S8_c2 | pm_15min | 38.4 | resolve CAP:S8:S8_c2 | CAP:S8:S8_c2 |
| 21 | R21:bg_sweep:COV:BG | bg_sweep | 9.37 | resolve COV:BG | COV:BG |
| 22 | R22:pm_hourly:S4 | pm_hourly | 9.6 | resolve CAP:S4 | CAP:S4 |
| 23 | R23:bg_sweep:COV:BG | bg_sweep | 9.37 | resolve COV:BG | COV:BG |
| 24 | R24:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 25 | R25:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 26 | R26:pm_hourly:S6 | pm_hourly | 9.6 | resolve CAP:S6 | CAP:S6 |
| 27 | R27:pm_hourly:S6_c0 | pm_hourly | 9.6 | resolve CAP:S6:S6_c0 | CAP:S6:S6_c0 |
| 28 | R28:pm_hourly:S6_c1 | pm_hourly | 9.6 | resolve CAP:S6:S6_c1 | CAP:S6:S6_c1 |
| 29 | R29:pm_hourly:S6_c2 | pm_hourly | 9.6 | resolve CAP:S6:S6_c2 | CAP:S6:S6_c2 |
| 30 | R30:pm_15min:S6_c0 | pm_15min | 38.4 | resolve CAP:S6:S6_c0 | CAP:S6:S6_c0 |
| 33 | final:target_rrc | pm_hourly | 9.6 | target baseline RRC (reporting/validation only) | - |

**Total spent: 362.08 / 500.0**

## Agent ledgers
### agent1
- hit rate per grade: {'high': {'graded': 36, 'scored': 19, 'hits': 2, 'rate': 0.105}, 'mid': {'graded': 389, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 25, 'scored': 6, 'hits': 1, 'rate': 0.167}}
- consecutive misses: 0; fuse trips: 11
- selection bias: only chosen rows get tested
### agent2
- hit rate per grade: {'high': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 16, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 11, 'scored': 11, 'hits': 5, 'rate': 0.455}}
- consecutive misses: 0; fuse trips: 2
- selection bias: only chosen rows get tested

## Event log
- [R1] spawned CAP:S1 (major exit for V3)
- [R1] spawned CAP:S2 (major exit for BG)
- [R1] spawned CAP:S4 (major exit for V1, V3, V4)
- [R1] spawned CAP:S6 (major exit for V2)
- [R1] spawned CAP:S8 (major exit for V2, V5, V6)
- [R1] boundary expansion forced in sector 2 (integrity refuted)
- [R2] executed R2:coverage_densify:COV:V5 (densify 2 unsampled evidence cells in V5) price=2.22; predicted=clears_theta actual=clears_theta
- [R3] executed R3:ring_sample:INT:0 (sample 4 ring points in sector 0) price=4.92; predicted=clean actual=contaminated
- [R4] boundary expansion forced in sector 0 (integrity refuted)
- [R5] spawned CAP:S12 (major exit for BG)
- [R5] executed R5:ring_sample:INT:1 (sample 4 ring points in sector 1) price=4.92; predicted=clean actual=contaminated
- [R6] boundary expansion forced in sector 1 (integrity refuted)
- [R7] executed R7:ring_sample:INT:3 (sample 4 ring points in sector 3) price=4.92; predicted=clean actual=clean
- [R8] executed R8:pm_hourly:S8 (hourly PRB for S8 over the outage-matched window) price=9.6; predicted=middle_zone actual=middle_zone
- [R9] drilled down CAP:S8 -> 3 per-cell children
- [R9] executed R9:pm_hourly:S12 (hourly PRB for S12 over the outage-matched window) price=9.6; predicted=middle_zone actual=support_zone
- [R10] executed R10:pm_hourly:S2 (hourly PRB for S2 over the outage-matched window) price=9.6; predicted=middle_zone actual=support_zone
- [R11] executed R11:ring_sample:INT:4 (sample 4 ring points in sector 4) price=4.92; predicted=clean actual=clean
- [R12] executed R12:ring_sample:INT:5 (sample 4 ring points in sector 5) price=4.92; predicted=clean actual=clean
- [R13] executed R13:pm_hourly:S8_c0 (hourly PRB for S8_c0 over the outage-matched window) price=9.6; predicted=middle_zone actual=support_zone
- [R14] executed R14:pm_hourly:S8_c1 (hourly PRB for S8_c1 over the outage-matched window) price=9.6; predicted=middle_zone actual=middle_zone
- [R15] executed R15:pm_hourly:S8_c2 (hourly PRB for S8_c2 over the outage-matched window) price=9.6; predicted=middle_zone actual=middle_zone
- [R16] agent2 fuse active: routed to baseline this round
- [R16] executed R16:ring_sample:INT:6 (sample 4 ring points in sector 6) price=4.92; predicted=clean actual=clean
- [R17] executed R17:ring_sample:INT:7 (sample 4 ring points in sector 7) price=4.92; predicted=clean actual=still_undecided
- [R18] executed R18:ring_sample:INT:7 (sample 4 ring points in sector 7) price=4.92; predicted=clean actual=clean
- [R19] executed R19:pm_15min:S8_c1 (15min PRB for S8_c1 over the outage-matched window) price=38.4; predicted=support actual=support
- [R20] agent1 fuse active: routed to baseline this round
- [R20] executed R20:pm_15min:S8_c2 (15min PRB for S8_c2 over the outage-matched window) price=38.4; predicted=support actual=support
- [R21] executed R21:bg_sweep:COV:BG (background-grid sweep, 7 points) price=9.37; predicted=clears_theta actual=still_straddling
- [R22] killed CAP:S2 (no longer anyone's best alternative)
- [R22] agent1 fuse active: routed to baseline this round
- [R22] executed R22:pm_hourly:S4 (hourly PRB for S4 over the outage-matched window) price=9.6; predicted=middle_zone actual=support_zone
- [R23] executed R23:bg_sweep:COV:BG (background-grid sweep, 7 points) price=9.37; predicted=clears_theta actual=still_straddling
- [R24] agent1 fuse active: routed to baseline this round
- [R24] executed R24:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=still_straddling actual=still_straddling
- [R25] killed CAP:S12 (no longer anyone's best alternative)
- [R25] executed R25:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=still_straddling actual=still_straddling
- [R26] executed R26:pm_hourly:S6 (hourly PRB for S6 over the outage-matched window) price=9.6; predicted=middle_zone actual=middle_zone
- [R27] drilled down CAP:S6 -> 3 per-cell children
- [R27] executed R27:pm_hourly:S6_c0 (hourly PRB for S6_c0 over the outage-matched window) price=9.6; predicted=middle_zone actual=middle_zone
- [R28] agent2 fuse active: routed to baseline this round
- [R28] executed R28:pm_hourly:S6_c1 (hourly PRB for S6_c1 over the outage-matched window) price=9.6; predicted=middle_zone actual=middle_zone
- [R29] executed R29:pm_hourly:S6_c2 (hourly PRB for S6_c2 over the outage-matched window) price=9.6; predicted=middle_zone actual=support_zone
- [R30] executed R30:pm_15min:S6_c0 (15min PRB for S6_c0 over the outage-matched window) price=38.4; predicted=support actual=refute
- [R31] no ticketed claims; idle round (stability check)
- [R32] no ticketed claims; idle round (stability check)