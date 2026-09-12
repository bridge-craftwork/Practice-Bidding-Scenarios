# Merge report: converting the leveling ladder (#294), on the `level` pipeline (#322)

What this merge changes, scenario by scenario: what each one dealt before, what
it deals now, and why. Written for review before merge.

Branches: `feat/294-handtypes` (this work) on top of `feat/level-operation`
(PR #329, the pipeline side). The detailed working notes are in
[294-leveling-conversion-findings.md](294-leveling-conversion-findings.md); this
report is the summary a reviewer should read first.

## What is in the merge

100 `.btn` files used the spot-card ladder (`#include "script/Leveling"`, keeps
built from where the ♣2 and friends landed).

| | count |
|---|---|
| converted to `HandType_` + generated leveling | 47 |
| converted after a fix that needs review | 21 |
| ladder removed because it leveled nothing — deals unchanged | 12 |
| left on the old ladder, tracked in #331 | 20 |

The 20 left behind keep `#include "script/Leveling"`, declare no `HandType_`
variables, and so are skipped by `level` and ignored by the `check-leveled` CI
gate. They deal exactly what they deal today. `script/Leveling` stays for them.
David wrote these scenarios and the remaining decisions are his; #331 lists each
one with its refusal, the evidence, and the options.

## The rule used where a scenario stated no intended mix

Some scripts say what mix they want, in the `@chat` a student reads or in a
comment. Those are honoured, and where the chat stated percentages they are now
`{{level-mix:TYPE}}` tokens, so the text and the keeps come from one calculation
and cannot drift apart again.

Where a script said nothing, **the old ladder's behaviour was not treated as the
specification.** Those ladders thinned with crude `keep25`-style steps, so what
they delivered was incidental rather than chosen — matching it now would only
freeze an accident. The types are leveled evenly (or on the plainest reading of
whatever comment exists), and the before/after is recorded here.

## How to read the table

- **natural** — what the scenario deals with no leveling at all.
- **BEFORE** — what the **old ladder** delivered, measured by pasting the new
  hand-type definitions into the old script and dealing it (seed 1, 2,000
  boards, capped at 300M deals). Both columns are therefore counted by the same
  definitions, so they compare directly.
- **target mix** — what the new keeps aim for, from the shares the script
  declares.
- **AFTER** — what `level`'s own 10,000-deal check dealt from the generated file.
- **cost** — deals dealt per deal kept, dealer3's figure. It includes the base
  condition's own rarity; the leveling's own share of it is the `×` column in
  the findings doc.
- **filter match** — the share of the 500 BBA-bid boards the `auction-filter`
  keeps, before → after. These barely move: leveling changes which hands come
  up, not how well BBA's auctions fit the filter.

Percentages are in the order of the types column.

How BEFORE was measured, since it matters: each old script was taken from the
base commit and the new hand-type definitions pasted in **after its condition**
(a condition can span lines, and splitting one silently breaks it), with every
name the old script defines differently resolved through the new `.btn`'s own
definitions (otherwise an alias like `lev2x` picks up the old
`lev2x = s2x and keep06` and measures the keep-filtered subset instead of the
category). Checked two ways: the shares sum to 100% for all 68, and the tagged
script deals the same boards as the untagged one. `After_3_Passes` comes out
49.6 / 50.3, which is what its old `keep94` / `keep56` predict.

| scenario | types | natural | BEFORE (old ladder) | target mix | AFTER (dealt) | cost | filter match |
|---|---|---|---|---|---|---|---|
| `1N` | Min, Avg, Max | 43 / 33 / 24 | 29.9 / 36.7 / 33.4 | 33 / 33 / 33 | 33.5 / 32.8 / 33.8 | 25 | 86.4% → 86.6% |
| `1N_5M_and_6m` | Min, Avg, Max | 39 / 37 / 23 | 29.9 / 30.9 / 39.1 | 33 / 33 / 33 | 33.4 / 32.6 / 34.0 | 188647 | 85.0% → 86.6% |
| `1m-2x` | n3m, n2S, n2m, n2H, n2NT, n3NT | 13 / 19 / 14 / 30 / 15 / 9 | 15.8 / 19.4 / 15.3 / 16.4 / 17.5 / 15.6 | 17 / 17 / 17 / 17 / 17 / 17 | 16.7 / 16.5 / 17.0 / 16.5 / 16.7 / 16.6 | 217 | -% → -% |
| `2N_and_1_Minor` | Slam, Game | 29 / 71 | 44.7 / 55.3 | 50 / 50 | 49.4 / 50.6 | 5614 | 55.6% → 60.2% |
| `2N_and_3C_Response` | Game, Slam | 89 / 11 | 55.0 / 45.0 | 50 / 50 | 49.0 / 51.0 | 2617 | 84.8% → 84.6% |
| `2N_and_Balanced` | Game, Slam | 90 / 10 | 51.2 / 48.8 | 50 / 50 | 48.9 / 51.1 | 2476 | 86.4% → 86.0% |
| `2N_and_MSS` | Game, Slam | 72 / 28 | 49.1 / 50.8 | 50 / 50 | 49.1 / 50.9 | 46319 | 41.0% → 40.0% |
| `2N_and_Transfers` | JacobyGame, JacobySlam, TexasGame, TexasSlam | 55 / 10 / 27 / 8 | 23.1 / 20.5 / 23.4 / 33.0 | 25 / 25 / 25 / 25 | 24.9 / 25.2 / 24.8 / 25.1 | 2004 | 87.8% → 85.0% |
| `3N_over_LHO_3x` | 1, 2, 3 | 89 / 5 / 6 | 38.6 / 27.6 / 33.8 | 33 / 33 / 33 | 34.8 / 32.6 / 32.6 | 135220 | 25.6% → 22.8% |
| `3N_over_RHO_3x` | 1, 2, 3 | 81 / 9 / 10 | 30.8 / 35.6 / 33.7 | 33 / 33 / 33 | 33.9 / 33.1 / 33.0 | 27445 | 25.4% → 24.4% |
| `After_2_Passes` | Shaded, Full | 34 / 66 | 50.9 / 49.1 | 50 / 50 | 50.3 / 49.7 | 29 | 70.6% → 69.2% |
| `After_3_Passes` | 14, 15 | 38 / 62 | 49.6 / 50.3 | 50 / 50 | 49.5 / 50.5 | 654 | 75.8% → 75.2% |
| `After_Partner_Overcalls` | Raise, Cue, Suit, NT, Punts | 16 / 18 / 27 / 3 / 37 | 21.1 / 25.3 / 35.0 / 4.0 / 14.6 | 20 / 20 / 20 / 20 / 20 | 20.3 / 19.4 / 19.7 / 20.0 / 20.6 | 29544 | 97.8% → 98.2% |
| `After_Partner_Takeout_Double` | S, H, D, C | 38 / 36 / 14 / 13 | 23.8 / 23.8 / 28.1 / 24.2 | 25 / 25 / 25 / 25 | 25.4 / 24.8 / 25.2 / 24.6 | 23142 | 80.6% → 81.0% |
| `Balancing` | nOC1, nOC2, nTOX, nOCN, nJOC, nTSO, nTS, n2NT | 15 / 15 / 49 / 6 / 3 / 11 / 1 / 1 | 9.2 / 10.0 / 16.5 / 13.3 / 14.3 / 11.1 / 13.0 / 12.6 | 12 / 12 / 12 / 12 / 12 / 12 / 12 / 12 | 12.8 / 12.4 / 12.4 / 12.4 / 12.7 / 11.7 / 12.7 / 12.7 | 24132 | 97.4% → 96.0% |
| `Basic_Openers_Rebid` | F1, F2min, F2inv, F3min, F3inv, F4 | 27 / 17 / 16 / 18 / 15 / 9 | 26.3 / 20.4 / 11.1 / 22.6 / 8.6 / 11.1 | 17 / 17 / 17 / 17 / 17 / 17 | 16.6 / 17.0 / 16.8 / 16.6 / 16.5 / 16.5 | 1621 | 84.6% → 77.8% |
| `Basic_Responses` | F1, F2, F3, F4, F5 | 5 / 62 / 12 / 4 / 18 | 12.2 / 38.0 / 27.8 / 9.8 / 12.2 | 25 / 25 / 25 / 12 / 12 | 25.3 / 24.6 / 24.8 / 12.3 / 13.0 | 988 | 99.2% → 99.6% |
| `Basic_What_To_Open` | 1C, 1D, 1H, 1S, 1N, 2N | 22 / 28 / 17 / 18 / 13 / 1 | 15.8 / 20.2 / 19.6 / 18.1 / 21.2 / 5.1 | 17 / 17 / 17 / 17 / 17 / 17 | 16.4 / 16.7 / 16.4 / 17.5 / 16.4 / 16.6 | 37 | 100.0% → 100.0% |
| `Benjamin_2D` | s2C2S, s2C1S, s2CB, s2DU, s2DB | 4 / 37 / 44 / 3 / 12 | 20.4 / 24.2 / 29.5 / 14.1 / 11.8 | 20 / 20 / 20 / 20 / 20 | 19.9 / 20.2 / 20.2 / 19.9 / 19.9 | 1937 | 83.6% → 85.0% |
| `Bergen_Raises` | C, D, oM, M, N | 39 / 21 / 25 / 12 / 2 | 18.9 / 24.7 / 20.0 / 17.1 / 19.2 | 20 / 20 / 20 / 20 / 20 | 19.6 / 19.9 / 20.2 / 20.1 / 20.3 | 2368 | 26.4% → 24.6% |
| `Better_Minor_Lebensohl` | Weak, Invite, Force | 21 / 51 / 29 | 33.4 / 34.9 / 31.8 | 33 / 33 / 33 | 33.6 / 33.2 / 33.2 | 28703 | 92.6% → 91.4% |
| `DONT` | X, C, D, H, S | 77 / 2 / 2 / 2 / 17 | 39.6 / 7.2 / 15.1 / 30.0 / 8.1 | 20 / 20 / 20 / 20 / 20 | 20.1 / 20.2 / 20.1 / 20.3 / 19.4 | 20120 | -% → -% |
| `DOPI_ROPI` | preemptPath, overcallPath | 1 / 99 | 40.2 / 59.8 | 50 / 50 | 50.7 / 49.3 | 449141 | 1.0% → 2.0% |
| `Drury` | Low, Mid, High | 32 / 50 / 18 | 80.0 / 5.2 / 14.8 | 35 / 60 / 5 | 35.0 / 60.1 / 4.9 | 4829 | 93.6% → 93.6% |
| `Exclusion_After_Sta_Jac` | case1, case2 | 62 / 38 | 49.3 / 50.7 | 50 / 50 | 49.6 / 50.4 | 30154 | 48.6% → 47.8% |
| `GIB_1N-P-2C-BID` | X, 2B, 3B, 4B | 64 / 18 / 13 / 4 | 24.8 / 33.5 / 24.8 / 17.0 | 25 / 25 / 25 / 25 | 25.5 / 24.8 / 25.0 / 24.7 | 52363 | 85.2% → 82.4% |
| `Gazzilli` | 2x, 3x, 2C, 2N | 40 / 4 / 38 / 18 | 14.8 / 20.0 / 53.9 / 11.3 | 25 / 25 / 25 / 25 | 25.2 / 25.2 / 24.5 / 25.1 | 3259 | 87.8% → 84.2% |
| `Grand_Slam_Invite` | 1214, 1517, 1819, 2021, 2224, 2527, 28 | 13 / 24 / 20 / 18 / 17 / 6 / 1 | 17.6 / 22.2 / 15.2 / 17.0 / 16.4 / 9.6 / 2.0 | 14 / 14 / 14 / 14 / 14 / 14 / 14 | 14.3 / 14.7 / 14.3 / 14.1 / 14.1 / 14.1 / 14.4 | 74597 | 100.0% → 100.0% |
| `Jacoby_2N_4x_void_Leveled` | x4, x3, M3, N3, M4 | 8 / 47 / 5 / 14 / 26 | 18.0 / 24.0 / 23.0 / 22.2 / 12.8 | 20 / 20 / 20 / 20 / 20 | 19.7 / 20.2 / 20.0 / 19.6 / 20.4 | 2968 | 80.4% → 81.8% |
| `Jacoby_2N_Leveled` | x4, x3, M3, N3, M4 | 9 / 44 / 5 / 15 / 27 | 22.8 / 16.2 / 33.0 / 17.2 / 10.8 | 20 / 20 / 20 / 20 / 20 | 19.8 / 20.4 / 20.0 / 19.6 / 20.2 | 2968 | 76.4% → 80.6% |
| `Lebensohl` | 1Suit, 2Suit | 97 / 3 | 49.8 / 50.2 | 50 / 50 | 50.6 / 49.4 | 153898 | 50.0% → 51.2% |
| `Major_Suit_Fit` | 1, 2, 3, 4, 5 | 26 / 43 / 22 / 7 / 2 | 23.8 / 19.9 / 22.5 / 24.9 / 8.9 | 20 / 20 / 20 / 20 / 20 | 20.7 / 19.7 / 19.8 / 19.9 / 20.0 | 828 | 48.6% → 54.8% |
| `Maximal_After_Overcall` | wMaxH, wMaxD | 82 / 18 | 52.9 / 47.0 | 50 / 50 | 50.1 / 49.9 | 57502 | 28.8% → 30.0% |
| `McCabe_After_Weak_2` | Rule17, Rule15, LeadAsk, Raise, mySuit, Pass | 2 / 5 / 11 / 21 / 2 / 59 | 20.0 / 15.4 / 17.9 / 15.3 / 17.9 / 13.5 | 17 / 17 / 17 / 17 / 17 / 17 | 16.5 / 17.3 / 15.7 / 16.4 / 17.9 / 16.2 | 77694 | 91.2% → 87.8% |
| `Meckwell` | X, C, D, H, S, N | 57 / 3 / 3 / 17 / 17 / 2 | 10.6 / 18.6 / 18.2 / 17.6 / 17.8 / 17.1 | 17 / 17 / 17 / 17 / 17 / 17 | 16.6 / 16.8 / 16.4 / 16.8 / 16.8 / 16.6 | 6085 | 64.4% → 60.4% |
| `Minor_Suit_Opener_Balanced_Response` | 06_10, 11_12, 13_15, 16_17, 18_19 | 31 / 24 / 30 / 11 / 4 | 17.4 / 20.0 / 24.8 / 16.4 / 21.5 | 20 / 20 / 20 / 20 / 20 | 20.1 / 20.1 / 19.9 / 19.9 / 20.0 | 653 | 90.4% → 90.8% |
| `Minor_Suit_Opener_Resp_Structure` | wkb, gib, gfb, wkr, gir, gfr | 30 / 23 / 46 / 0 / 0 / 1 | 18.1 / 30.0 / 20.2 / 6.5 / 8.2 / 16.9 | 17 / 17 / 17 / 17 / 17 / 17 | 15.8 / 15.7 / 18.6 / 16.5 / 16.9 / 16.4 | 8517 | 72.6% → 59.2% |
| `Misfit` | Min, Mid, Max | 22 / 24 / 54 | 17.6 / 30.4 / 52.0 | 33 / 33 / 33 | 33.4 / 33.4 / 33.2 | 440 | 99.8% → 100.0% |
| `Multi_Landy` | C, D, H, S, N, M4m5, m6, M5, Bal19 | 12 / 10 / 9 / 9 / 2 / 23 / 15 / 18 / 1 | 13.6 / 12.3 / 13.5 / 14.4 / 3.6 / 12.3 / 14.6 / 14.1 / 1.6 | 11 / 11 / 11 / 11 / 11 / 11 / 11 / 11 / 11 | 11.3 / 11.8 / 10.7 / 11.3 / 11.2 / 11.1 / 10.7 / 10.7 / 11.3 | 1723 | 48.6% → 34.6% |
| `NT_Ladder` | 12_14, 15_17, 18_19, 20_21, 22_24 | 58 / 29 / 8 / 3 / 1 | 18.6 / 18.6 / 21.9 / 22.2 / 18.6 | 20 / 20 / 20 / 20 / 20 | 20.2 / 19.8 / 20.0 / 20.0 / 20.0 | 95 | 100.0% → 100.0% |
| `Ned_3-Level_Resp_to_1N` | Min, Avg, Max | 53 / 31 / 16 | 36.6 / 34.7 / 28.6 | 33 / 33 / 33 | 33.6 / 33.5 / 32.9 | 19375 | 78.8% → 83.4% |
| `OBAR_BIDS` | X, 5, 6 | 45 / 27 / 28 | 33.7 / 35.0 / 31.3 | 33 / 33 / 33 | 32.9 / 32.8 / 34.3 | 8971 | 42.0% → 40.4% |
| `OBAR_BIDS11` | X, 5, 6 | 27 / 39 / 34 | 31.8 / 37.0 / 31.1 | 33 / 33 / 33 | 33.5 / 33.3 / 33.2 | 3718 | 55.4% → 53.2% |
| `Ogust` | 3C, 3D, 3H, 3S, 3N | 7 / 24 / 12 / 55 / 2 | 14.0 / 24.3 / 23.5 / 32.9 / 5.3 | 20 / 20 / 20 / 20 / 20 | 20.5 / 19.8 / 19.4 / 19.8 / 20.5 | 217273 | 67.6% → 63.6% |
| `Open_In_Fourth_Seat` | 13, 14, 15, 16 | 15 / 22 / 29 / 34 | 26.4 / 23.8 / 21.8 / 28.0 | 25 / 25 / 25 / 25 | 24.6 / 25.0 / 25.6 / 24.9 | 224 | 64.4% → 64.8% |
| `Open_and_Rebid` | N5c4d, N65mM, N55m, T5d4c, Tbal, E6c4d, E5c4dM | 4 / 1 / 1 / 4 / 88 / 1 / 1 | 35.6 / 9.4 / 11.1 / 18.7 / 11.5 / 8.0 / 5.8 | 17 / 17 / 17 / 12 / 12 / 12 / 12 | 16.9 / 16.3 / 16.6 / 12.2 / 13.1 / 12.5 / 12.3 | 11750 | 99.4% → 99.6% |
| `Opps_Double_Stayman` | 5, More | 25 / 75 | 51.2 / 48.8 | 50 / 50 | 50.4 / 49.6 | 29545 | 85.8% → 84.8% |
| `Puppet_Stayman_1N` | Game, SlamInv, SlamForce | 93 / 6 / 1 | 83.4 / 15.2 / 1.4 | 33 / 33 / 33 | 33.4 / 33.3 / 33.3 | 7575 | 97.4% → 98.6% |
| `Puppet_Stayman_2N` | Game, SlamInv, SlamForce | 84 / 13 / 2 | 65.1 / 29.4 / 5.5 | 33 / 33 / 33 | 33.7 / 33.4 / 32.8 | 9147 | 99.4% → 99.0% |
| `Reverse_Flannery` | 2H, 2S | 36 / 64 | 46.5 / 53.5 | 50 / 50 | 49.5 / 50.5 | 24304 | 99.4% → 99.4% |
| `Rosenkranz_Double` | With, Without | 52 / 48 | 52.4 / 47.5 | 50 / 50 | 50.7 / 49.3 | 158 | -% → -% |
| `Rule_of_16` | 14, 15, 16, 17, 18 | 20 / 29 / 31 / 15 / 5 | 25.1 / 26.2 / 23.7 / 19.4 / 5.7 | 20 / 20 / 20 / 20 / 20 | 20.5 / 19.4 / 20.3 / 19.8 / 20.0 | 12429 | 98.2% → 98.2% |
| `Spear` | 2C, 2D, 2H, 2S, X | 10 / 22 / 6 / 6 / 56 | 28.5 / 36.9 / 10.3 / 10.2 / 14.1 | 20 / 20 / 20 / 20 / 20 | 19.2 / 19.5 / 20.2 / 20.3 / 20.7 | 52574 | 73.6% → 74.4% |
| `Splinters` | 1, 2, 3, 4 | 30 / 39 / 21 / 10 | 26.3 / 24.1 / 24.8 / 24.8 | 25 / 25 / 25 / 25 | 24.8 / 24.6 / 25.4 / 25.2 | 6696 | 33.2% → 37.4% |
| `Splinters_after_Minor` | 2, 3, 4 | 90 / 10 / 0 | 86.4 / 13.3 / 0.4 | 76 / 16 / 8 | 77.0 / 15.5 / 7.5 | 400000 | 20.8% → 18.2% |
| `Stayman` | nWeak, nNormal | 19 / 81 | 18.9 / 81.2 | 15 / 85 | 14.8 / 85.2 | 549 | 95.4% → 95.4% |
| `Transfer_Advances` | C, D, H, S | 47 / 35 / 12 / 5 | 24.0 / 25.2 / 20.8 / 29.9 | 25 / 25 / 25 / 25 | 24.8 / 25.0 / 25.2 / 25.0 | 1922 | -% → -% |
| `Trap_Pass_Maybe` | Weak, Trap | 92 / 8 | 48.0 / 52.0 | 50 / 50 | 50.0 / 50.0 | 15834 | 26.6% → 25.0% |
| `Trap_Pass_Opener` | 1, 2 | 83 / 17 | 51.0 / 48.9 | 50 / 50 | 49.6 / 50.4 | 130222 | 57.4% → 58.4% |
| `Trap_Pass_Opener_Maybe` | 1t, 1n, 2t, 2n | 20 / 61 / 4 / 15 | 32.3 / 18.5 / 22.2 / 27.0 | 25 / 25 / 25 / 25 | 24.9 / 24.7 / 25.3 / 25.1 | 65111 | 62.0% → 60.4% |
| `Two-Way_New_Minor_Forcing_aka_xyNT` | Partscore, Invite, Game, Slam | 20 / 24 / 47 / 8 | 15.7 / 23.8 / 28.7 / 31.8 | 25 / 25 / 25 / 25 | 24.9 / 25.4 / 24.7 / 25.0 | 514 | 42.4% → 48.0% |
| `Vics_2C_Relay` | type_1, type_2, type_3 | 36 / 21 / 42 | 15.2 / 42.5 / 42.3 | 33 / 33 / 33 | 33.5 / 33.7 / 32.8 | 1018 | 96.8% → 95.8% |
| `Vics_Bal_Resp_to_1m` | 1N, 2H, 2N, 3N | 52 / 22 / 21 / 6 | 29.9 / 24.9 / 26.6 / 18.6 | 25 / 25 / 25 / 25 | 25.1 / 25.0 / 24.9 / 24.9 | 605 | 23.8% → 23.6% |
| `Weak_2_Bids_Lax` | case1, case2, case3, case4 | 59 / 27 / 9 / 6 | 28.0 / 22.9 / 24.9 / 24.1 | 25 / 25 / 25 / 25 | 24.6 / 25.1 / 25.2 / 25.1 | 312 | 84.4% → 85.0% |
| `Weak_2_Bids_Lax_Leveled` | case1, case2, case3, case4 | 59 / 27 / 9 / 6 | 28.0 / 22.9 / 24.9 / 24.1 | 25 / 25 / 25 / 25 | 24.6 / 25.1 / 25.2 / 25.1 | 312 | 82.4% → 82.8% |
| `Weak_2_Bids_Leveled` | case1, case2, case3, case4 | 59 / 27 / 8 / 6 | 29.5 / 22.3 / 20.8 / 27.3 | 25 / 25 / 25 / 25 | 24.4 / 25.1 / 25.2 / 25.3 | 401 | 89.8% → 92.2% |
| `Weak_Jump_Shift` | Force1, Force2, Rebid, NewSuit, Other | 5 / 1 / 5 / 10 / 79 | 17.6 / 6.2 / 25.8 / 26.7 / 23.8 | 12 / 12 / 25 / 25 / 25 | 12.4 / 12.5 / 25.3 / 24.2 / 25.6 | 20168 | 75.8% → 73.0% |
| `Weak_NT_11-16` | 1113, 1416 | 64 / 36 | 48.0 / 52.0 | 50 / 50 | 49.7 / 50.3 | 7 | -% → -% |

## A bug this turned up in the pipeline (#322)

`level` passed no `-g`, so dealer3's default generate limit of 10,000,000 ended
the measuring pass long before its 2,000-sighting goal, and it exits 0 either
way. Measured on `1N_5M_and_6m`:

| | deals measured | rarest type seen | keeps known to |
|---|---|---|---|
| without `-g` (PR #329 as first written) | 86 | 21 times | ±19% |
| with `-g 2,000,000,000` | 8,631 | 2,000 times | ±2.0% |

The two generated files differ, so this was affecting real output, and the error
is systematic: producing more deals afterwards converges on the wrong keeps
rather than averaging out. `LEVEL_GENERATE` in `config.py` and `-g` on the
`level` command fix it. A generate limit stops on the same deal every run, so
files still rebuild byte-identically — verified: two fresh runs match each other
and match the committed file.

Two related notes, neither fixed:

- `level` decides "measuring stopped on the clock" by looking for
  `--level-timeout` in dealer3's report, but dealer3's thin-measurement warning
  also names that switch, so the warning can fire when the clock was not the
  limit.
- `--level-budget` does **not** make `level` faster. Measuring stops when the
  rarest type has been seen 2,000 times whatever the budget; a budget changes
  only the keeps, and so the cost of dealing afterwards. A scenario whose
  measuring is slow needs fewer or wider types, not a budget.

## Where an intended mix had to be interpreted

These are the judgment calls in the merge. Each changes what a student meets.

| scenario | what the script said | what was done |
|---|---|---|
| `Drury` | chat: "Leveled Partscore 35%, game 60%, slam 5%" — it delivered about 80 / 6 / 13 | shares 7 / 12 / 1, so it now delivers what it always claimed. Chat carries `{{level-mix}}` tokens |
| `Basic_Responses` | comment: "the 10+ families are the minority tier", no number | shares 2:2:2:1:1 — see below |
| `Weak_Jump_Shift` | chat: "Opener's Force, Rebid, New Suit, (Pass or Raise) occur at about the same frequency", but five types | shares 1,1,2,2,2: the chat's one "Force" is two types in the script |
| `Open_and_Rebid` | comment "Level toward ~50/25/25", groups headed "(~half)", "(~quarter)" | shares 4,4,4 / 3,3 / 3,3 |
| `Stayman` | comment: "Weak (< 8 HCP) should be about 15% of results" | shares 3 / 17 → 15 / 85 |
| `Ogust` | comment: "bring 3D and 3S down toward 3H" — a partial leveling | leveled evenly. Say if only the first half was wanted |
| `Rosenkranz_Double` | comment "Level to ~50% / ~50%", but both keeps were keep-everything | leveled evenly: 52 / 48 → 50 / 50 |
| `Trap_Pass_Maybe` | "About 50% of South's passes are trap passes" | `{{level-mix:Trap}}`, still 50% |
| `NT_Ladder`, `Jacoby_2N_Leveled`, `Jacoby_2N_4x_void_Leveled` | hand-written per-type percentages | `{{level-mix:TYPE}}`; they read 20% each |

### `Basic_Responses`, the one with the least to go on

Its five families are F1 single raise, F2 new suit at the 1 level, F3 1NT,
F4 jump raise, F5 new suit at the 2 level.

| | F1 | F2 | F3 | F4 | F5 | minimum tier F1-F3 | 10+ tier F4-F5 |
|---|---|---|---|---|---|---|---|
| natural | 5 | 62 | 12 | 4 | 18 | 79 | 22 |
| old ladder, measured | 12.0 | 38.5 | 27.7 | 9.7 | 12.1 | 78.2 | 21.8 |
| now, shares 2:2:2:1:1 | 25.3 | 24.6 | 24.8 | 12.3 | 13.0 | 75 | 25 |

The script's only statement is "the 10+ families are the minority tier", with no
number, and its keeps were `keep25` on F2 and F5 with keep-everything on the
other three. So the old 38.5 / 27.7 / 12 split inside the minimum tier was not a
chosen mix — it is what thinning the two commonest families happened to produce.
The tier split is kept at roughly what it was (21.8% → 25%) and the three
minimum families are leveled evenly, which is the plainest reading of the one
comment. The visible change is that single raises roughly double (12% → 25%) and
new-suit-at-the-one-level falls (38.5% → 25%).

## Overlaps: which type a deal counts as (5)

dealer3 refuses two types matching one deal. A precedence changes only which
type a deal is **tagged** as; the set of deals is unchanged. Each was settled
from the scenario's own chat, except where noted.

- **`Basic_Openers_Rebid`** — six diamonds and four spades is both "rebid the
  long minor" and "show spades at the one level". The chat says to bid a second
  four-card suit at the one level, and BBA rebids 1S on all four such deals in
  the scenario's own `bba/` file. Spades win. **This rests on evidence about
  BBA, not about what the lesson intends** — worth a look.
- **`Benjamin_2D`** — 24 HCP unbalanced is both 2C and 2D. The chat says 2D
  shows 23+ unbalanced, so 2D wins. (The chat says 23 and the code 24; the
  ranges were left alone.)
- **`GIB_1N-P-2C-BID`** — a 7-3-2-1 hand fell into both the double and the
  3-level bid; the double's definition excludes other 7-card shapes, which looks
  like an oversight. The 3-level bid wins.
- **`Meckwell`** — three overlaps, all from the chat (2N is 5-5+ in the minors;
  2H/2S show five; 2D is a diamond suit with a major).
- **`Multi_Landy`** — three overlaps, all from the chat (6-5 minors is 2N; 6-6
  majors is 2C; a six-card major with a side minor is the double).

Two incidental bugs were found and **left alone**: `Meckwell`'s `oneSuit` counts
a 5-5 hand as one-suited, and `GIB_1N-P-2C-BID`'s double lets a 7-3-2-1 hand in.

## Gaps: the condition now says what it always dealt (6)

`Puppet_Stayman_1N`, `Puppet_Stayman_2N`, `Weak_2_Bids_Leveled`,
`Grand_Slam_Invite`, `Minor_Suit_Opener_Balanced_Response`, `Rule_of_16`.

dealer3 refuses hand types that leave deals uncovered. In each case the old
verdict was an `or` of the same types, so a deal outside every type was never
dealt anyway — the ladder was filtering as well as leveling. Adding
`and (HandType_a or HandType_b …)` to the condition **keeps exactly the set of
deals the scenario produced** and makes the filtering explicit. If any of those
excluded hands should be practised (North 15-16 without a fit in a weak-two
scenario, say), the types should be widened instead.

## Ladders that leveled nothing, removed (12)

`Mixed_Raise_In_Comp`, `Exclusion_After_1M`, `Lebensohl_vs_Opps_W2_Bal` (every
keep kept everything); `Jacoby_2N`, `Jacoby_2N_4x_void`, `Preempt_X_XX`,
`Weak_2_Bids` (the `and levelTheDeal` was commented out); `Open_In_Fourth_13`
/`_14`/`_15`/`_16`, `Double_Showing_2_Suits` (`keep0` — a filter, not leveling).

All 12 were checked by dealing 200 boards from the old and new scripts with the
same seed: identical. Two were re-verified independently for this report
(`Jacoby_2N`, `Open_In_Fourth_14`).

## The one budget: `Splinters_after_Minor`

Its grand-slam type is 0.25% of qualifying deals, and even leveling would cost
about 1.6 million deals per board — more than `pbn` can deal for 500 boards, and
a BBO table would stall. `# level-budget: 400000` gives 76 / 16 / 8, which takes
grand slams from 0.25% of boards to about 8%. Its keeps rest on 407 sightings of
the rarest type (±5%), so the 8% could be a point out. A dead type (`part`,
impossible opposite a splinter) was dropped. **A BBO table would deal this live
at 400,000 deals a board, which has not been tried.**

## What has not been verified

- **Nothing was tried on BBO.** The dearest scripts to deal are `DOPI_ROPI`
  (449,141 deals a board), `Splinters_after_Minor` (400,000) and `Ogust`
  (217,273). Whether BBO's own dealer copes is the thing to check with
  `bbo-demo` before releasing any of them.
- **Only `dlr,level,pbn,rotate,bba,filter,filterStats` were run.** `quiz`,
  `biddingSheet` and `package` are stale for every scenario touched, and the
  `GIB/` captures are from the old scripts.
- The manifest is rebuilt by CI on push; the chat in it changes for the
  scenarios whose chat now carries `{{level-mix}}` tokens.
- `Weak_2_Bids_Lax` and `Weak_2_Bids_Lax_Leveled` are the same script; both were
  converted rather than deciding whether one should go.
- The VS Code extension was not rebuilt here; no TypeScript changed in this
  branch.

Regenerating a scenario's `bba/` pool does **not** invalidate its
`bba-curated/` deals or its coaching prose, so the four converted scenarios
carrying `# curate: kind=bidding` (`Drury`, `Stayman`, `Basic_Openers_Rebid`,
`Basic_Responses`) need nothing re-curated. `Spiral_Raises_*` is left for #331
because those feed `py/spiral_auction.py`.

## Reviewer's checklist

1. The interpreted mixes above, `Basic_Responses` first.
2. The five overlap precedences — they are bidding judgments.
3. `Splinters_after_Minor`'s budget, and whether an 8% grand-slam share is what
   that lesson wants.
4. The six narrowed conditions: no deal changes, but they now exclude those
   hands in writing.
5. Whether the `-g` fix should be folded into PR #329 or ride along with this
   branch.
