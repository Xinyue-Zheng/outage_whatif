# What-if outage report — case case03, target S5

*Arm:* `zonedist/rule` — *outage window:* 2026-07-20T10:00:00 to 2026-07-20T18:00:00 (Monday, weekday)

## Overall verdict
**locally degraded**

Stop reason: budget exhausted (no affordable action) after 48 rounds; spend 415.11 of budget 420.0.

## Per-subregion verdicts and deciding claims

| subregion | pop | tier | severe | bottleneck | deciding evidence |
|---|---|---|---|---|---|
| BG | 73 | degraded | no | coverage | COV:BG:undecided (0.76, 0.95); ROB:BG:supported (0.2, 0.466); CAP:S2:supported mean=0.158 |
| V1 | 347 | degraded | no | robustness (S2) | COV:V1:supported (0.438, 1.0); ROB:V1:refuted (0.438, 1.0); CAP:S2:supported mean=0.158 |
| V2 | 345 | degraded | no | robustness (S8) | COV:V2:supported (0.566, 1.0); ROB:V2:refuted (0.566, 1.0); CAP:S8:supported mean=0.177 |
| V3 | 191 | absorbable | no | - | COV:V3:supported (0.51, 1.0); ROB:V3:supported (0.15, 0.85); CAP:S12:supported mean=0.307; CAP:S8:supported mean=0.177 |
| V4 | 59 | degraded | no | robustness (S2) | COV:V4:supported (0.342, 1.0); ROB:V4:refuted (0.342, 1.0); CAP:S2:supported mean=0.158 |
| V5 | 53 | absorbable | no | - | COV:V5:supported; ROB:V5:supported |

## Unverified assumptions (conservative defaults at budget exhaustion)
- `unverified_assumption` — BG: tier undecided at stop (budget exhausted (no affordable action); open coverage claim); conservatively reported as degraded

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
- Settlements under P_min were not individually verified. (1 settlement(s), 38 people absorbed into the background region, which the background grid still covers.)
- Declared boundary: handover misconfiguration, transport bottlenecks, and all other factors absent from the inputs are outside every conclusion this system can draw.
- Boundary expansions performed: 2.
- Target baseline RRC (reporting/validation only): not purchased (budget).

## Budget ledger

| round | action | kind | price | purpose | claim served |
|---|---|---|---|---|---|
| 0 | init:Track-1 initial sampling | coverage | 3.54 | Track-1 initial sampling | COV:V1 |
| 0 | init:Track-1 initial sampling | coverage | 6.37 | Track-1 initial sampling | COV:V2 |
| 0 | init:Track-1 initial sampling | coverage | 6.37 | Track-1 initial sampling | COV:V3 |
| 0 | init:Track-1 initial sampling | coverage | 2.22 | Track-1 initial sampling | COV:V4 |
| 0 | init:Track-1 initial sampling | coverage | 2.22 | Track-1 initial sampling | COV:V5 |
| 0 | init:Track-2 fuse grid | coverage | 4.92 | Track-2 fuse grid | COV:BG |
| 1 | R1:expand:2 | coverage | 4.92 | boundary expansion resampling | INT:2 |
| 2 | R2:ring_sample:INT:0 | ring_sample | 4.92 | resolve INT:0 | INT:0 |
| 3 | R3:ring_sample:INT:1 | ring_sample | 4.92 | resolve INT:1 | INT:1 |
| 4 | R4:ring_sample:INT:2 | ring_sample | 4.92 | resolve INT:2 | INT:2 |
| 5 | R5:ring_sample:INT:3 | ring_sample | 4.92 | resolve INT:3 | INT:3 |
| 6 | R6:pm_hourly:S2 | pm_hourly | 6.4 | resolve CAP:S2 | CAP:S2 |
| 7 | R7:ring_sample:INT:4 | ring_sample | 4.92 | resolve INT:4 | INT:4 |
| 8 | R8:pm_hourly:S8 | pm_hourly | 6.4 | resolve CAP:S8 | CAP:S8 |
| 9 | R9:ring_sample:INT:5 | ring_sample | 4.92 | resolve INT:5 | INT:5 |
| 10 | R10:expand:5 | coverage | 4.92 | boundary expansion resampling | INT:5 |
| 11 | R11:ring_sample:INT:6 | ring_sample | 4.92 | resolve INT:6 | INT:6 |
| 12 | R12:pm_hourly:S10 | pm_hourly | 6.4 | resolve CAP:S10 | CAP:S10 |
| 13 | R13:ring_sample:INT:6 | ring_sample | 4.92 | resolve INT:6 | INT:6 |
| 14 | R14:pm_hourly:S12 | pm_hourly | 6.4 | resolve CAP:S12 | CAP:S12 |
| 15 | R15:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 16 | R16:bg_sweep:COV:BG | bg_sweep | 9.37 | resolve COV:BG | COV:BG |
| 17 | R17:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 18 | R18:bg_sweep:COV:BG | bg_sweep | 9.37 | resolve COV:BG | COV:BG |
| 19 | R19:pm_hourly:S4 | pm_hourly | 6.4 | resolve CAP:S4 | CAP:S4 |
| 20 | R20:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 21 | R21:bg_sweep:COV:BG | bg_sweep | 9.37 | resolve COV:BG | COV:BG |
| 22 | R22:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 23 | R23:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 24 | R24:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 25 | R25:bg_sweep:COV:BG | bg_sweep | 7.85 | resolve COV:BG | COV:BG |
| 26 | R26:bg_sweep:COV:BG | bg_sweep | 9.37 | resolve COV:BG | COV:BG |
| 27 | R27:bg_sweep:COV:BG | bg_sweep | 9.37 | resolve COV:BG | COV:BG |
| 28 | R28:bg_sweep:COV:BG | bg_sweep | 6.37 | resolve COV:BG | COV:BG |
| 29 | R29:bg_sweep:COV:BG | bg_sweep | 9.37 | resolve COV:BG | COV:BG |
| 30 | R30:bg_sweep:COV:BG | bg_sweep | 9.37 | resolve COV:BG | COV:BG |
| 31 | R31:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 32 | R32:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 33 | R33:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 34 | R34:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 35 | R35:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 36 | R36:bg_sweep:COV:BG | bg_sweep | 7.85 | resolve COV:BG | COV:BG |
| 37 | R37:bg_sweep:COV:BG | bg_sweep | 7.85 | resolve COV:BG | COV:BG |
| 38 | R38:bg_sweep:COV:BG | bg_sweep | 7.85 | resolve COV:BG | COV:BG |
| 39 | R39:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 40 | R40:bg_sweep:COV:BG | bg_sweep | 9.37 | resolve COV:BG | COV:BG |
| 41 | R41:bg_sweep:COV:BG | bg_sweep | 7.85 | resolve COV:BG | COV:BG |
| 42 | R42:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 43 | R43:bg_sweep:COV:BG | bg_sweep | 9.37 | resolve COV:BG | COV:BG |
| 44 | R44:bg_sweep:COV:BG | bg_sweep | 9.37 | resolve COV:BG | COV:BG |
| 45 | R45:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 46 | R46:bg_sweep:COV:BG | bg_sweep | 10.93 | resolve COV:BG | COV:BG |
| 47 | R47:profile:S12:same_weekday | profile | 5.0 | judgment firming | CAP:S12 |

**Total spent: 415.11 / 420.0**

## Agent ledgers
### agent1
- hit rate per grade: {'high': {'graded': 42, 'scored': 21, 'hits': 0, 'rate': 0.0}, 'mid': {'graded': 309, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 21, 'scored': 0, 'hits': 0, 'rate': None}}
- consecutive misses: 1; fuse trips: 10
- selection bias: only chosen rows get tested
### agent2
- hit rate per grade: {'high': {'graded': 0, 'scored': 0, 'hits': 0, 'rate': None}, 'mid': {'graded': 40, 'scored': 0, 'hits': 0, 'rate': None}, 'low': {'graded': 5, 'scored': 5, 'hits': 5, 'rate': 1.0}}
- consecutive misses: 0; fuse trips: 0
- selection bias: only chosen rows get tested

## Event log
- [R1] spawned CAP:S10 (major exit for BG)
- [R1] spawned CAP:S12 (major exit for V3)
- [R1] spawned CAP:S2 (major exit for BG, V1, V4)
- [R1] spawned CAP:S8 (major exit for V2, V3)
- [R1] boundary expansion forced in sector 2 (integrity refuted)
- [R2] executed R2:ring_sample:INT:0 (sample 4 ring points in sector 0) price=4.92; predicted=clean actual=clean
- [R3] executed R3:ring_sample:INT:1 (sample 4 ring points in sector 1) price=4.92; predicted=clean actual=clean
- [R4] executed R4:ring_sample:INT:2 (sample 4 ring points in sector 2) price=4.92; predicted=clean actual=clean
- [R5] executed R5:ring_sample:INT:3 (sample 4 ring points in sector 3) price=4.92; predicted=clean actual=clean
- [R6] executed R6:pm_hourly:S2 (hourly PRB for S2 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R7] executed R7:ring_sample:INT:4 (sample 4 ring points in sector 4) price=4.92; predicted=clean actual=clean
- [R8] executed R8:pm_hourly:S8 (hourly PRB for S8 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R9] executed R9:ring_sample:INT:5 (sample 4 ring points in sector 5) price=4.92; predicted=clean actual=contaminated
- [R10] boundary expansion forced in sector 5 (integrity refuted)
- [R11] executed R11:ring_sample:INT:6 (sample 4 ring points in sector 6) price=4.92; predicted=clean actual=still_undecided
- [R12] executed R12:pm_hourly:S10 (hourly PRB for S10 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R13] executed R13:ring_sample:INT:6 (sample 4 ring points in sector 6) price=4.92; predicted=clean actual=clean
- [R14] executed R14:pm_hourly:S12 (hourly PRB for S12 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R15] executed R15:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=falls_below_theta actual=still_straddling
- [R16] agent1 fuse active: routed to baseline this round
- [R16] executed R16:bg_sweep:COV:BG (background-grid sweep, 7 points) price=9.37; predicted=falls_below_theta actual=still_straddling
- [R17] executed R17:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=still_straddling actual=still_straddling
- [R18] executed R18:bg_sweep:COV:BG (background-grid sweep, 7 points) price=9.37; predicted=falls_below_theta actual=still_straddling
- [R19] spawned CAP:S4 (major exit for BG)
- [R19] agent1 fuse active: routed to baseline this round
- [R19] executed R19:pm_hourly:S4 (hourly PRB for S4 over the outage-matched window) price=6.4; predicted=middle_zone actual=support_zone
- [R20] executed R20:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=falls_below_theta actual=still_straddling
- [R21] killed CAP:S10 (no longer anyone's best alternative)
- [R21] executed R21:bg_sweep:COV:BG (background-grid sweep, 7 points) price=9.37; predicted=falls_below_theta actual=still_straddling
- [R22] agent1 fuse active: routed to baseline this round
- [R22] executed R22:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=falls_below_theta actual=still_straddling
- [R23] executed R23:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=falls_below_theta actual=still_straddling
- [R24] executed R24:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=falls_below_theta actual=still_straddling
- [R25] agent1 fuse active: routed to baseline this round
- [R25] executed R25:bg_sweep:COV:BG (background-grid sweep, 6 points) price=7.85; predicted=still_straddling actual=still_straddling
- [R26] executed R26:bg_sweep:COV:BG (background-grid sweep, 7 points) price=9.37; predicted=still_straddling actual=still_straddling
- [R27] killed CAP:S4 (no longer anyone's best alternative)
- [R27] executed R27:bg_sweep:COV:BG (background-grid sweep, 7 points) price=9.37; predicted=still_straddling actual=still_straddling
- [R28] executed R28:bg_sweep:COV:BG (background-grid sweep, 5 points) price=6.37; predicted=still_straddling actual=still_straddling
- [R29] executed R29:bg_sweep:COV:BG (background-grid sweep, 7 points) price=9.37; predicted=still_straddling actual=still_straddling
- [R30] executed R30:bg_sweep:COV:BG (background-grid sweep, 7 points) price=9.37; predicted=still_straddling actual=still_straddling
- [R31] executed R31:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=falls_below_theta actual=still_straddling
- [R32] executed R32:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=falls_below_theta actual=still_straddling
- [R33] agent1 fuse active: routed to baseline this round
- [R33] executed R33:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=falls_below_theta actual=still_straddling
- [R34] executed R34:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=falls_below_theta actual=still_straddling
- [R35] executed R35:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=still_straddling actual=still_straddling
- [R36] executed R36:bg_sweep:COV:BG (background-grid sweep, 6 points) price=7.85; predicted=still_straddling actual=still_straddling
- [R37] executed R37:bg_sweep:COV:BG (background-grid sweep, 6 points) price=7.85; predicted=still_straddling actual=still_straddling
- [R38] executed R38:bg_sweep:COV:BG (background-grid sweep, 6 points) price=7.85; predicted=still_straddling actual=still_straddling
- [R39] executed R39:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=still_straddling actual=still_straddling
- [R40] executed R40:bg_sweep:COV:BG (background-grid sweep, 7 points) price=9.37; predicted=still_straddling actual=still_straddling
- [R41] executed R41:bg_sweep:COV:BG (background-grid sweep, 6 points) price=7.85; predicted=still_straddling actual=still_straddling
- [R42] executed R42:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=still_straddling actual=still_straddling
- [R43] executed R43:bg_sweep:COV:BG (background-grid sweep, 7 points) price=9.37; predicted=still_straddling actual=still_straddling
- [R44] executed R44:bg_sweep:COV:BG (background-grid sweep, 7 points) price=9.37; predicted=still_straddling actual=still_straddling
- [R45] executed R45:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=still_straddling actual=still_straddling
- [R46] executed R46:bg_sweep:COV:BG (background-grid sweep, 8 points) price=10.93; predicted=still_straddling actual=still_straddling
- [R47] executed R47:profile:S12:same_weekday (historical profile (same_weekday) for S12 — judgment-firming, changes no claim directly) price=5.0; predicted=anchor_confirms actual=anchor_confirms
- [R48] target baseline RRC unaffordable at stop