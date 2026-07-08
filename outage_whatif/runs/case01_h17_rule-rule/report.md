# What-if outage report — case case01, target S5

*Arm:* `rule/rule` — *outage window:* 2026-07-20T10:00:00 to 2026-07-20T18:00:00 (Monday, weekday)

## Conditionality of this verdict
**This run assessed analysis hour 17:00.** The verdict holds for that hour only. Other hours of the ticket window (2026-07-20T10:00:00 to 2026-07-20T18:00:00) were not verified in this run.
- analysis_hour selection: explicit (deliverable d: busy hour).
- Capacity evidence basis: k=4 matched occurrences of this hour on comparable days (same clock-hour and weekday / holiday class; known outages excluded).

## Overall verdict
**locally degraded**

Stop reason: all tickets resolved; verdict unchanged for 2 rounds after 39 rounds; spend 288.49 of budget 420.0.

## Per-subregion verdicts and deciding claims

| subregion | pop | tier | severe | bottleneck | deciding evidence |
|---|---|---|---|---|---|
| BG | 46 | hole | no | coverage | COV:BG:refuted (0.641, 0.9); ROB:BG:supported (0.232, 0.537); CAP:S2:supported mean=0.298; CAP:S4:supported mean=0.254; CAP:S8:supported mean=0.195 |
| V1 | 374 | absorbable | no | - | COV:V1:supported; ROB:V1:supported |
| V2 | 309 | degraded | no | robustness (S2) | COV:V2:supported (0.438, 1.0); ROB:V2:refuted (0.438, 1.0); CAP:S2:supported mean=0.298 |
| V3 | 196 | absorbable | no | - | COV:V3:supported; ROB:V3:supported |
| V4 | 133 | degraded | no | robustness (S2) | COV:V4:supported (0.342, 1.0); ROB:V4:refuted (0.342, 1.0); CAP:S2:supported mean=0.298 |
| V5 | 88 | degraded | no | robustness (S6) | COV:V5:supported (0.566, 1.0); ROB:V5:refuted (0.566, 1.0); CAP:S6:undecided |
| V6 | 71 | degraded | no | robustness (S6) | COV:V6:supported (0.342, 1.0); ROB:V6:refuted (0.342, 1.0); CAP:S6:undecided |

## Policy rules in force ([POLICY] — advisor sign-off required)
- theta = 0.9
- pi_hi = 0.85
- kappa = 0.6
- P_min = 50
- P0 = 200
- sigma = 0.2
- cap15_refute_frac = 0.1
- calib_false_pass_max = 0.05
- comparable_days_k = 4
- analysis_hour_default_rule = busiest_profile_else_midpoint
- calibration support-zone edge = 0.5 (hourly tier may declare support)

## Disclosures
- Settlements under P_min were not individually verified. (1 settlement(s), 38 people absorbed into the background region, which the background grid still covers.)
- Declared boundary: handover misconfiguration, transport bottlenecks, and all other factors absent from the inputs are outside every conclusion this system can draw.
- Boundary expansions performed: 1.
- Target baseline RRC (reporting/validation only): mean 109.9 conn/h.

## Budget ledger

| round | action | kind | price | purpose | claim served |
|---|---|---|---|---|---|
| 0 | init:Track-1 initial sampling | coverage | 3.54 | Track-1 initial sampling | COV:V1 |
| 0 | init:Track-1 initial sampling | coverage | 3.54 | Track-1 initial sampling | COV:V2 |
| 0 | init:Track-1 initial sampling | coverage | 3.54 | Track-1 initial sampling | COV:V3 |
| 0 | init:Track-1 initial sampling | coverage | 2.22 | Track-1 initial sampling | COV:V4 |
| 0 | init:Track-1 initial sampling | coverage | 4.92 | Track-1 initial sampling | COV:V5 |
| 0 | init:Track-1 initial sampling | coverage | 2.22 | Track-1 initial sampling | COV:V6 |
| 0 | init:Track-2 fuse grid | coverage | 6.37 | Track-2 fuse grid | COV:BG |
| 1 | R1:ring_sample:INT:0 | ring_sample | 4.92 | resolve INT:0 | INT:0 |
| 2 | R2:ring_sample:INT:0 | ring_sample | 4.92 | resolve INT:0 | INT:0 |
| 3 | R3:ring_sample:INT:1 | ring_sample | 4.92 | resolve INT:1 | INT:1 |
| 4 | R4:expand:1 | coverage | 4.92 | boundary expansion resampling | INT:1 |
| 5 | R5:pm_hourly:S3 | pm_hourly | 3.2 | resolve CAP:S3 | CAP:S3 |
| 6 | R6:ring_sample:INT:2 | ring_sample | 4.92 | resolve INT:2 | INT:2 |
| 7 | R7:pm_hourly:S4 | pm_hourly | 3.2 | resolve CAP:S4 | CAP:S4 |
| 8 | R8:ring_sample:INT:3 | ring_sample | 4.92 | resolve INT:3 | INT:3 |
| 9 | R9:pm_hourly:S8 | pm_hourly | 3.2 | resolve CAP:S8 | CAP:S8 |
| 10 | R10:ring_sample:INT:4 | ring_sample | 4.92 | resolve INT:4 | INT:4 |
| 11 | R11:pm_hourly:S9 | pm_hourly | 3.2 | resolve CAP:S9 | CAP:S9 |
| 12 | R12:ring_sample:INT:5 | ring_sample | 4.92 | resolve INT:5 | INT:5 |
| 13 | R13:ring_sample:INT:5 | ring_sample | 4.92 | resolve INT:5 | INT:5 |
| 14 | R14:coverage_densify:COV:V5 | coverage_densify | 1.0 | resolve COV:V5 | COV:V5 |
| 15 | R15:ring_sample:INT:6 | ring_sample | 4.92 | resolve INT:6 | INT:6 |
| 16 | R16:ring_sample:INT:6 | ring_sample | 4.92 | resolve INT:6 | INT:6 |
| 17 | R17:ring_sample:INT:7 | ring_sample | 4.92 | resolve INT:7 | INT:7 |
| 18 | R18:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 19 | R19:bg_sweep:COV:BG | bg_sweep | 7.85 | resolve COV:BG | COV:BG |
| 20 | R20:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 21 | R21:bg_sweep:COV:BG | bg_sweep | 9.37 | resolve COV:BG | COV:BG |
| 22 | R22:bg_sweep:COV:BG | bg_sweep | 9.37 | resolve COV:BG | COV:BG |
| 23 | R23:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 24 | R24:bg_sweep:COV:BG | bg_sweep | 9.37 | resolve COV:BG | COV:BG |
| 25 | R25:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 26 | R26:bg_sweep:COV:BG | bg_sweep | 7.85 | resolve COV:BG | COV:BG |
| 27 | R27:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 28 | R28:bg_sweep:COV:BG | bg_sweep | 7.85 | resolve COV:BG | COV:BG |
| 29 | R29:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 30 | R30:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 31 | R31:bg_sweep:COV:BG | bg_sweep | 9.37 | resolve COV:BG | COV:BG |
| 32 | R32:pm_hourly:S2 | pm_hourly | 3.2 | resolve CAP:S2 | CAP:S2 |
| 33 | R33:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 34 | R34:bg_sweep:COV:BG | bg_sweep | 9.37 | resolve COV:BG | COV:BG |
| 35 | R35:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 36 | R36:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 39 | final:target_rrc | pm_hourly | 6.4 | target baseline RRC (reporting/validation only) | - |

**Total spent: 288.49 / 420.0**

## Agent ledgers
### agent1
- hit rate per grade: {'high': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 468, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}}
- consecutive misses: 0; fuse trips: 0
- selection bias: only chosen rows get tested
### agent2
- hit rate per grade: {'high': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 30, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 5, 'scored': 5, 'hits': 5, 'rate': 1.0}}
- consecutive misses: 0; fuse trips: 0
- selection bias: only chosen rows get tested

## Event log
- [R1] spawned CAP:S2 (major exit for V2, V4)
- [R1] spawned CAP:S3 (major exit for BG)
- [R1] spawned CAP:S4 (major exit for BG)
- [R1] spawned CAP:S6 (major exit for V5, V6)
- [R1] spawned CAP:S8 (major exit for BG)
- [R1] executed R1:ring_sample:INT:0 (sample 4 ring points in sector 0) price=4.92; predicted=clean actual=still_undecided
- [R2] executed R2:ring_sample:INT:0 (sample 4 ring points in sector 0) price=4.92; predicted=clean actual=clean
- [R3] executed R3:ring_sample:INT:1 (sample 4 ring points in sector 1) price=4.92; predicted=clean actual=contaminated
- [R4] boundary expansion forced in sector 1 (integrity refuted)
- [R5] spawned CAP:S9 (major exit for BG)
- [R5] executed R5:pm_hourly:S3 (hourly PRB for S3 at the analysis hour (17:00) over 4 matched comparable days) price=3.2; predicted=middle_zone actual=support_zone
- [R6] executed R6:ring_sample:INT:2 (sample 4 ring points in sector 2) price=4.92; predicted=clean actual=clean
- [R7] executed R7:pm_hourly:S4 (hourly PRB for S4 at the analysis hour (17:00) over 4 matched comparable days) price=3.2; predicted=middle_zone actual=support_zone
- [R8] executed R8:ring_sample:INT:3 (sample 4 ring points in sector 3) price=4.92; predicted=clean actual=clean
- [R9] executed R9:pm_hourly:S8 (hourly PRB for S8 at the analysis hour (17:00) over 4 matched comparable days) price=3.2; predicted=middle_zone actual=support_zone
- [R10] executed R10:ring_sample:INT:4 (sample 4 ring points in sector 4) price=4.92; predicted=clean actual=clean
- [R11] executed R11:pm_hourly:S9 (hourly PRB for S9 at the analysis hour (17:00) over 4 matched comparable days) price=3.2; predicted=middle_zone actual=support_zone
- [R12] executed R12:ring_sample:INT:5 (sample 4 ring points in sector 5) price=4.92; predicted=clean actual=still_undecided
- [R13] executed R13:ring_sample:INT:5 (sample 4 ring points in sector 5) price=4.92; predicted=clean actual=clean
- [R14] executed R14:coverage_densify:COV:V5 (densify 1 unsampled evidence cells in V5) price=1.0; predicted=clears_theta actual=clears_theta
- [R15] executed R15:ring_sample:INT:6 (sample 4 ring points in sector 6) price=4.92; predicted=clean actual=still_undecided
- [R16] executed R16:ring_sample:INT:6 (sample 4 ring points in sector 6) price=4.92; predicted=clean actual=clean
- [R17] executed R17:ring_sample:INT:7 (sample 4 ring points in sector 7) price=4.92; predicted=clean actual=clean
- [R18] executed R18:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=falls_below_theta actual=still_straddling
- [R19] killed CAP:S3 (no longer anyone's best alternative)
- [R19] executed R19:bg_sweep:COV:BG (background-grid sweep, 6 points) price=7.85; predicted=still_straddling actual=still_straddling
- [R20] executed R20:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=still_straddling actual=still_straddling
- [R21] killed CAP:S9 (no longer anyone's best alternative)
- [R21] executed R21:bg_sweep:COV:BG (background-grid sweep, 7 points) price=9.37; predicted=still_straddling actual=still_straddling
- [R22] executed R22:bg_sweep:COV:BG (background-grid sweep, 7 points) price=9.37; predicted=still_straddling actual=still_straddling
- [R23] executed R23:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=still_straddling actual=still_straddling
- [R24] executed R24:bg_sweep:COV:BG (background-grid sweep, 7 points) price=9.37; predicted=still_straddling actual=still_straddling
- [R25] executed R25:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=still_straddling actual=still_straddling
- [R26] executed R26:bg_sweep:COV:BG (background-grid sweep, 6 points) price=7.85; predicted=still_straddling actual=still_straddling
- [R27] executed R27:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=still_straddling actual=still_straddling
- [R28] executed R28:bg_sweep:COV:BG (background-grid sweep, 6 points) price=7.85; predicted=still_straddling actual=still_straddling
- [R29] executed R29:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=still_straddling actual=still_straddling
- [R30] executed R30:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=still_straddling actual=still_straddling
- [R31] executed R31:bg_sweep:COV:BG (background-grid sweep, 7 points) price=9.37; predicted=still_straddling actual=still_straddling
- [R32] executed R32:pm_hourly:S2 (hourly PRB for S2 at the analysis hour (17:00) over 4 matched comparable days) price=3.2; predicted=middle_zone actual=support_zone
- [R33] executed R33:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=still_straddling actual=still_straddling
- [R34] executed R34:bg_sweep:COV:BG (background-grid sweep, 7 points) price=9.37; predicted=still_straddling actual=still_straddling
- [R35] executed R35:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=still_straddling actual=still_straddling
- [R36] executed R36:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=still_straddling actual=falls_below_theta
- [R37] no ticketed claims; idle round (stability check)
- [R38] no ticketed claims; idle round (stability check)