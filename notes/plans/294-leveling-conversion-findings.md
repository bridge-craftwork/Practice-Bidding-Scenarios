# Issue #294: converting the ladder to generated leveling — findings

Branch `feat/294-handtypes`, on top of `feat/level-operation` (PR #329).
Written 2026-09-11 by Claude Code for Rick. Nothing here is pushed.

## Summary

Every `.btn` that used the spot-card ladder (`#include "script/Leveling"`, or a
pasted copy): **100**.

| | count | where |
|---|---|---|
| converted mechanically, leveled | **47** | [Converted scenarios](#converted-scenarios) |
| fixed by hand, then leveled — **please review** | **21** | [Fixes applied — review](#fixes-applied--review) |
| ladder removed, dealing exactly what it dealt before | **12** | [Ladders that leveled nothing](#ladders-that-leveled-nothing-removed) |
| left untouched for you | **20** | [Needs Rick](#needs-rick) |

So 80 of the 100 are off the ladder. The 20 still include `script/Leveling`,
so that file stays.

The converter is `py/convert_leveling.py`: the issue's `pbs-to-handtypes.py`
rewritten to work on `btn/`, where the ladder is an `#include` rather than
pasted text. It also reads verdicts written `(name and keepNN)`, and has two
modes that keep the set of deals unchanged: `--narrow`, dealer3's gap fix,
and `--unlevel`, which takes out a ladder that levels nothing.
`python3 py/convert_leveling.py --all --json` re-runs the screen.

## One pipeline change you should look at first

**`level` was measuring on a few dozen deals for about half the corpus.**
`level.py` passed no `-g`, so dealer3's default generate limit of 10,000,000
ended the measuring long before its 2,000-sighting goal. `1N_5M_and_6m`
stopped after 86 qualifying deals, its rarest type seen 21 times: keeps known
to ±19%, and wrong for good. dealer3 warns but exits 0. The guide says `-g`
doesn't bound characterizing, but in the CLI it does.

I added `LEVEL_GENERATE = 2,000,000,000` to `config.py` and `-g` to the
`level` command (commit "Add py/convert_leveling.py; level measures with -g
..."). A generate limit stops on the same deal every run, so rebuilds stay
byte-identical.

A related false alarm: `level.py` decides "measuring stopped on the clock" by
looking for `--level-timeout` in dealer3's report. dealer3's thin-measurement
warning also names that switch ("Raise --level-measure or --level-timeout"), so
the clock warning can fire when the clock had nothing to do with it. I didn't
change that.

**`--level-budget` doesn't make `level` faster.** Measuring stops when the
rarest type has been seen 2,000 times, whatever the budget. A budget changes
only the keeps, and so the cost of *dealing* afterwards (`pbn`, the 10,000-deal
check, a BBO table). So a scenario whose measuring is slow can't be rescued
with a budget. It needs fewer or wider types, or a longer clock.

## Converted scenarios

Mix and dealt shares are percentages, in the order of the types column.
"Natural" is what the scenario deals without leveling; "mix" what the keeps
aim for; "dealt" what `level`'s own 10,000-deal check produced. "Cost" is
dealer3's figure, deals dealt per deal kept, which includes the base
condition's own rarity; "×" is the part leveling adds (1 / acceptance).
"Filter match" is the share of the 500 BBA-bid boards the `auction-filter`
keeps, before → after.

| scenario | types | natural | mix | dealt | cost | x | filter match |
|---|---|---|---|---|---|---|---|
| `1N` | Min, Avg, Max | 43 / 33 / 24 | 33 / 33 / 33 | 33.5 / 32.8 / 33.8 | 25 | 1.39 | 86.4% → 86.6% |
| `1N_5M_and_6m` | Min, Avg, Max | 39 / 37 / 23 | 33 / 33 / 33 | 33.4 / 32.6 / 34.0 | 188647 | 1.44 | 85.0% → 86.6% |
| `2N_and_1_Minor` | Slam, Game | 29 / 71 | 50 / 50 | 49.4 / 50.6 | 5614 | 1.70 | 55.6% → 60.2% |
| `2N_and_MSS` | Game, Slam | 72 / 28 | 50 / 50 | 49.1 / 50.9 | 46319 | 1.81 | 41.0% → 40.0% |
| `3N_over_LHO_3x` | 1, 2, 3 | 89 / 5 / 6 | 33 / 33 / 33 | 34.8 / 32.6 / 32.6 | 135220 | 6.63 | 25.6% → 22.8% |
| `3N_over_RHO_3x` | 1, 2, 3 | 81 / 9 / 10 | 33 / 33 / 33 | 33.9 / 33.1 / 33.0 | 27445 | 3.84 | 25.4% → 24.4% |
| `After_2_Passes` | Shaded, Full | 34 / 66 | 50 / 50 | 50.3 / 49.7 | 29 | 1.45 | 70.6% → 69.2% |
| `After_3_Passes` | 14, 15 | 38 / 62 | 50 / 50 | 49.5 / 50.5 | 654 | 1.32 | 75.8% → 75.2% |
| `After_Partner_Takeout_Double` | S, H, D, C | 38 / 36 / 14 / 13 | 25 / 25 / 25 / 25 | 25.4 / 24.8 / 25.2 / 24.6 | 23142 | 1.97 | 80.6% → 81.0% |
| `Balancing` | nOC1, nOC2, nTOX, nOCN, nJOC, nTSO, nTS, n2NT | 15 / 15 / 49 / 6 / 3 / 11 / 1 / 1 | 12 / 12 / 12 / 12 / 12 / 12 / 12 / 12 | 12.8 / 12.4 / 12.4 / 12.4 / 12.7 / 11.7 / 12.7 / 12.7 | 24132 | 16.26 | 97.4% → 96.0% |
| `Basic_Responses` | F1, F2, F3, F4, F5 | 5 / 62 / 12 / 4 / 18 | 25 / 25 / 25 / 12 / 12 | 25.3 / 24.6 / 24.8 / 12.3 / 13.0 | 988 | 4.88 | 99.2% → 99.6% |
| `Basic_What_To_Open` | 1C, 1D, 1H, 1S, 1N, 2N | 22 / 28 / 17 / 18 / 13 / 1 | 17 / 17 / 17 / 17 / 17 / 17 | 16.4 / 16.7 / 16.4 / 17.5 / 16.4 / 16.6 | 37 | 12.03 | 100.0% → 100.0% |
| `Bergen_Raises` | C, D, oM, M, N | 39 / 21 / 25 / 12 / 2 | 20 / 20 / 20 / 20 / 20 | 19.6 / 19.9 / 20.2 / 20.1 / 20.3 | 2368 | 8.12 | 26.4% → 24.6% |
| `Better_Minor_Lebensohl` | Weak, Invite, Force | 21 / 51 / 29 | 33 / 33 / 33 | 33.6 / 33.2 / 33.2 | 28703 | 1.61 | 92.6% → 91.4% |
| `DONT` | X, C, D, H, S | 77 / 2 / 2 / 2 / 17 | 20 / 20 / 20 / 20 / 20 | 20.1 / 20.2 / 20.1 / 20.3 / 19.4 | 20120 | 10.72 | -% → -% |
| `Drury` | Low, Mid, High | 32 / 50 / 18 | 35 / 60 / 5 | 35.0 / 60.1 / 4.9 | 4829 | 1.20 | 93.6% → 93.6% |
| `Exclusion_After_Sta_Jac` | case1, case2 | 62 / 38 | 50 / 50 | 49.6 / 50.4 | 30154 | 1.30 | 48.6% → 47.8% |
| `Gazzilli` | 2x, 3x, 2C, 2N | 40 / 4 / 38 / 18 | 25 / 25 / 25 / 25 | 25.2 / 25.2 / 24.5 / 25.1 | 3259 | 6.09 | 87.8% → 84.2% |
| `Jacoby_2N_4x_void_Leveled` | x4, x3, M3, N3, M4 | 8 / 47 / 5 / 14 / 26 | 20 / 20 / 20 / 20 / 20 | 19.7 / 20.2 / 20.0 / 19.6 / 20.4 | 2968 | 4.25 | 80.4% → 81.8% |
| `Jacoby_2N_Leveled` | x4, x3, M3, N3, M4 | 9 / 44 / 5 / 15 / 27 | 20 / 20 / 20 / 20 / 20 | 19.8 / 20.4 / 20.0 / 19.6 / 20.2 | 2968 | 3.97 | 76.4% → 80.6% |
| `Lebensohl` | 1Suit, 2Suit | 97 / 3 | 50 / 50 | 50.6 / 49.4 | 153898 | 17.73 | 50.0% → 51.2% |
| `Major_Suit_Fit` | 1, 2, 3, 4, 5 | 26 / 43 / 22 / 7 / 2 | 20 / 20 / 20 / 20 / 20 | 20.7 / 19.7 / 19.8 / 19.9 / 20.0 | 828 | 9.41 | 48.6% → 54.8% |
| `Maximal_After_Overcall` | wMaxH, wMaxD | 82 / 18 | 50 / 50 | 50.1 / 49.9 | 57502 | 2.74 | 28.8% → 30.0% |
| `McCabe_After_Weak_2` | Rule17, Rule15, LeadAsk, Raise, mySuit, Pass | 2 / 5 / 11 / 21 / 2 / 59 | 17 / 17 / 17 / 17 / 17 / 17 | 16.5 / 17.3 / 15.7 / 16.4 / 17.9 / 16.2 | 77694 | 10.76 | 91.2% → 87.8% |
| `Minor_Suit_Opener_Resp_Structure` | wkb, gib, gfb, wkr, gir, gfr | 30 / 23 / 46 / 0 / 0 / 1 | 17 / 17 / 17 / 17 / 17 / 17 | 15.8 / 15.7 / 18.6 / 16.5 / 16.9 / 16.4 | 8517 | 54.64 | 72.6% → 59.2% |
| `Misfit` | Min, Mid, Max | 22 / 24 / 54 | 33 / 33 / 33 | 33.4 / 33.4 / 33.2 | 440 | 1.50 | 99.8% → 100.0% |
| `Ned_3-Level_Resp_to_1N` | Min, Avg, Max | 53 / 31 / 16 | 33 / 33 / 33 | 33.6 / 33.5 / 32.9 | 19375 | 2.10 | 78.8% → 83.4% |
| `NT_Ladder` | 12_14, 15_17, 18_19, 20_21, 22_24 | 58 / 29 / 8 / 3 / 1 | 20 / 20 / 20 / 20 / 20 | 20.2 / 19.8 / 20.0 / 20.0 / 20.0 | 95 | 15.82 | 100.0% → 100.0% |
| `OBAR_BIDS` | X, 5, 6 | 45 / 27 / 28 | 33 / 33 / 33 | 32.9 / 32.8 / 34.3 | 8971 | 1.21 | 42.0% → 40.4% |
| `OBAR_BIDS11` | X, 5, 6 | 27 / 39 / 34 | 33 / 33 / 33 | 33.5 / 33.3 / 33.2 | 3718 | 1.21 | 55.4% → 53.2% |
| `Ogust` | 3C, 3D, 3H, 3S, 3N | 7 / 24 / 12 / 55 / 2 | 20 / 20 / 20 / 20 / 20 | 20.5 / 19.8 / 19.4 / 19.8 / 20.5 | 217273 | 8.20 | 67.6% → 63.6% |
| `Open_and_Rebid` | N5c4d, N65mM, N55m, T5d4c, Tbal, E6c4d, E5c4dM | 4 / 1 / 1 / 4 / 88 / 1 / 1 | 17 / 17 / 17 / 12 / 12 / 12 / 12 | 16.9 / 16.3 / 16.6 / 12.2 / 13.1 / 12.5 / 12.3 | 11750 | 18.80 | 99.4% → 99.6% |
| `Open_In_Fourth_Seat` | 13, 14, 15, 16 | 15 / 22 / 29 / 34 | 25 / 25 / 25 / 25 | 24.6 / 25.0 / 25.6 / 24.9 | 224 | 1.64 | 64.4% → 64.8% |
| `Opps_Double_Stayman` | 5, More | 25 / 75 | 50 / 50 | 50.4 / 49.6 | 29545 | 1.98 | 85.8% → 84.8% |
| `Reverse_Flannery` | 2H, 2S | 36 / 64 | 50 / 50 | 49.5 / 50.5 | 24304 | 1.38 | 99.4% → 99.4% |
| `Rosenkranz_Double` | With, Without | 52 / 48 | 50 / 50 | 50.7 / 49.3 | 158 | 1.05 | -% → -% |
| `Spear` | 2C, 2D, 2H, 2S, X | 10 / 22 / 6 / 6 / 56 | 20 / 20 / 20 / 20 / 20 | 19.2 / 19.5 / 20.2 / 20.3 / 20.7 | 52574 | 3.36 | 73.6% → 74.4% |
| `Splinters` | 1, 2, 3, 4 | 30 / 39 / 21 / 10 | 25 / 25 / 25 / 25 | 24.8 / 24.6 / 25.4 / 25.2 | 6696 | 2.40 | 33.2% → 37.4% |
| `Transfer_Advances` | C, D, H, S | 47 / 35 / 12 / 5 | 25 / 25 / 25 / 25 | 24.8 / 25.0 / 25.2 / 25.0 | 1922 | 4.57 | -% → -% |
| `Trap_Pass_Maybe` | Weak, Trap | 92 / 8 | 50 / 50 | 50.0 / 50.0 | 15834 | 6.15 | 26.6% → 25.0% |
| `Trap_Pass_Opener` | 1, 2 | 83 / 17 | 50 / 50 | 49.6 / 50.4 | 130222 | 2.93 | 57.4% → 58.4% |
| `Trap_Pass_Opener_Maybe` | 1t, 1n, 2t, 2n | 20 / 61 / 4 / 15 | 25 / 25 / 25 / 25 | 24.9 / 24.7 / 25.3 / 25.1 | 65111 | 6.06 | 62.0% → 60.4% |
| `Two-Way_New_Minor_Forcing_aka_xyNT` | Partscore, Invite, Game, Slam | 20 / 24 / 47 / 8 | 25 / 25 / 25 / 25 | 24.9 / 25.4 / 24.7 / 25.0 | 514 | 3.08 | 42.4% → 48.0% |
| `Vics_2C_Relay` | type_1, type_2, type_3 | 36 / 21 / 42 | 33 / 33 / 33 | 33.5 / 33.7 / 32.8 | 1018 | 1.57 | 96.8% → 95.8% |
| `Vics_Bal_Resp_to_1m` | 1N, 2H, 2N, 3N | 52 / 22 / 21 / 6 | 25 / 25 / 25 / 25 | 25.1 / 25.0 / 24.9 / 24.9 | 605 | 4.36 | 23.8% → 23.6% |
| `Weak_Jump_Shift` | Force1, Force2, Rebid, NewSuit, Other | 5 / 1 / 5 / 10 / 79 | 12 / 12 / 25 / 25 / 25 | 12.4 / 12.5 / 25.3 / 24.2 / 25.6 | 20168 | 9.65 | 75.8% → 73.0% |
| `Weak_NT_11-16` | 1113, 1416 | 64 / 36 | 50 / 50 | 49.7 / 50.3 | 7 | 1.39 | -% → -% |

### Chat and share changes in these (where I interpreted the intended mix)

| scenario | what the scenario said | what I did |
|---|---|---|
| `Drury` | chat: "Leveled Partscore 35%, game 60%, slam 5%." The ladder delivered about 80/6/13 | shares `Low 7, Mid 12, High 1`; chat reads `{{level-mix:Low}}` etc. Low/Mid/High (North under 15, 15-18, 19+) taken as partscore/game/slam, as the comment beside them says |
| `Weak_Jump_Shift` | chat: "Opener's Force, Rebid, New Suit, (Pass or Raise) occur at about the same frequency." Five types | shares `Force1 1, Force2 1, Rebid 2, NewSuit 2, Other 2`: the chat's "Force" is `force1` and `force2` together |
| `Open_and_Rebid` | comment: "Level toward ~50/25/25"; groups headed "(~half)", "(~quarter)", "(~quarter)" | shares 4,4,4 (non-standard) / 3,3 (standard) / 3,3 (edge) |
| `Basic_Responses` | comment: "the 10+ families are the minority tier", no number | shares 2,2,2,1,1: minimum families 75%, 10+ families 25% (the ladder gave about 79/21). **Least sure of this one**; delete the `_Share` lines for even |
| `NT_Ladder`, `Jacoby_2N_Leveled`, `Jacoby_2N_4x_void_Leveled` | hand-written per-type percentages | `{{level-mix:TYPE}}`; they read 20% each. The 4x_void chat said "Use the (Leveled) script to even that out" although it *is* the leveled script; now reads "...using this leveled script" |
| `Trap_Pass_Maybe` | "About 50% of South's passes are trap passes" | "About `{{level-mix:Trap}}` …", still 50% |
| `Ogust` | comment: "bring 3D and 3S down toward 3H" — a partial leveling | leveled evenly; say if you wanted only the first half |
| `Rosenkranz_Double` | comment "Level to ~50% top honor, ~50% no top honor", but both keeps were `keep` | leveled evenly: natural 52/48 becomes 50/50 |

Everything else says "about the same frequency", "leveled", or nothing, and is leveled evenly.

## Fixes applied — review

Each is its own commit, or a small commit of like cases. The evidence I used is
given in each case: the chat, the button text, the filter, or BBA's own
bidding. Results, from `level`'s check:

| scenario | types | natural | mix | dealt | cost | x | filter match |
|---|---|---|---|---|---|---|---|
| `Puppet_Stayman_1N` | Game, SlamInv, SlamForce | 93 / 6 / 1 | 33 / 33 / 33 | 33.4 / 33.3 / 33.3 | 7575 | 46.73 | 97.4% → 98.6% |
| `Puppet_Stayman_2N` | Game, SlamInv, SlamForce | 84 / 13 / 2 | 33 / 33 / 33 | 33.7 / 33.4 / 32.8 | 9147 | 13.33 | 99.4% → 99.0% |
| `Weak_2_Bids_Leveled` | case1, case2, case3, case4 | 59 / 27 / 8 / 6 | 25 / 25 / 25 / 25 | 24.4 / 25.1 / 25.2 / 25.3 | 401 | 4.51 | 89.8% → 92.2% |
| `Grand_Slam_Invite` | 1214, 1517, 1819, 2021, 2224, 2527, 28 | 13 / 24 / 20 / 18 / 17 / 6 / 1 | 14 / 14 / 14 / 14 / 14 / 14 / 14 | 14.3 / 14.7 / 14.3 / 14.1 / 14.1 / 14.1 / 14.4 | 74597 | 9.65 | 100.0% → 100.0% |
| `Minor_Suit_Opener_Balanced_Response` | 06_10, 11_12, 13_15, 16_17, 18_19 | 31 / 24 / 30 / 11 / 4 | 20 / 20 / 20 / 20 / 20 | 20.1 / 20.1 / 19.9 / 19.9 / 20.0 | 653 | 4.45 | 90.4% → 90.8% |
| `Rule_of_16` | 14, 15, 16, 17, 18 | 20 / 29 / 31 / 15 / 5 | 20 / 20 / 20 / 20 / 20 | 20.5 / 19.4 / 20.3 / 19.8 / 20.0 | 12429 | 4.28 | 98.2% → 98.2% |
| `Splinters_after_Minor` | 2, 3, 4 | 90 / 10 / 0 | 76 / 16 / 8 | 77.0 / 15.5 / 7.5 | 400000 | 33.22 | 20.8% → 18.2% |
| `Basic_Openers_Rebid` | F1, F2min, F2inv, F3min, F3inv, F4 | 27 / 17 / 16 / 18 / 15 / 9 | 17 / 17 / 17 / 17 / 17 / 17 | 16.6 / 17.0 / 16.8 / 16.6 / 16.5 / 16.5 | 1621 | 1.95 | 84.6% → 77.8% |
| `Benjamin_2D` | s2C2S, s2C1S, s2CB, s2DU, s2DB | 4 / 37 / 44 / 3 / 12 | 20 / 20 / 20 / 20 / 20 | 19.9 / 20.2 / 20.2 / 19.9 / 19.9 | 1937 | 6.71 | 83.6% → 85.0% |
| `Multi_Landy` | C, D, H, S, N, M4m5, m6, M5, Bal19 | 12 / 10 / 9 / 9 / 2 / 23 / 15 / 18 / 1 | 11 / 11 / 11 / 11 / 11 / 11 / 11 / 11 / 11 | 11.3 / 11.8 / 10.7 / 11.3 / 11.2 / 11.1 / 10.7 / 10.7 / 11.3 | 1723 | 9.55 | 48.6% → 34.6% |
| `Meckwell` | X, C, D, H, S, N | 57 / 3 / 3 / 17 / 17 / 2 | 17 / 17 / 17 / 17 / 17 / 17 | 16.6 / 16.8 / 16.4 / 16.8 / 16.8 / 16.6 | 6085 | 7.09 | 64.4% → 60.4% |
| `GIB_1N-P-2C-BID` | X, 2B, 3B, 4B | 64 / 18 / 13 / 4 | 25 / 25 / 25 / 25 | 25.5 / 24.8 / 25.0 / 24.7 | 52363 | 5.64 | 85.2% → 82.4% |
| `2N_and_3C_Response` | Game, Slam | 89 / 11 | 50 / 50 | 49.0 / 51.0 | 2617 | 4.75 | 84.8% → 84.6% |
| `2N_and_Balanced` | Game, Slam | 90 / 10 | 50 / 50 | 48.9 / 51.1 | 2476 | 4.98 | 86.4% → 86.0% |
| `Weak_2_Bids_Lax` | case1, case2, case3, case4 | 59 / 27 / 9 / 6 | 25 / 25 / 25 / 25 | 24.6 / 25.1 / 25.2 / 25.1 | 312 | 4.54 | 84.4% → 85.0% |
| `Weak_2_Bids_Lax_Leveled` | case1, case2, case3, case4 | 59 / 27 / 9 / 6 | 25 / 25 / 25 / 25 | 24.6 / 25.1 / 25.2 / 25.1 | 312 | 4.54 | 82.4% → 82.8% |
| `1m-2x` | n3m, n2S, n2m, n2H, n2NT, n3NT | 13 / 19 / 14 / 30 / 15 / 9 | 17 / 17 / 17 / 17 / 17 / 17 | 16.7 / 16.5 / 17.0 / 16.5 / 16.7 / 16.6 | 217 | 1.81 | -% → -% |
| `DOPI_ROPI` | preemptPath, overcallPath | 1 / 99 | 50 / 50 | 50.7 / 49.3 | 449141 | 37.74 | 1.0% → 2.0% |
| `Stayman` | nWeak, nNormal | 19 / 81 | 15 / 85 | 14.8 / 85.2 | 549 | 1.04 | 95.4% → 95.4% |
| `After_Partner_Overcalls` | Raise, Cue, Suit, NT, Punts | 16 / 18 / 27 / 3 / 37 | 20 / 20 / 20 / 20 / 20 | 20.3 / 19.4 / 19.7 / 20.0 / 20.6 | 29544 | 7.50 | 97.8% → 98.2% |
| `2N_and_Transfers` | JacobyGame, JacobySlam, TexasGame, TexasSlam | 55 / 10 / 27 / 8 | 25 / 25 / 25 / 25 | 24.9 / 25.2 / 24.8 / 25.1 | 2004 | 3.15 | 87.8% → 85.0% |

### Gaps: condition narrowed to the types (6)

dealer3: *"Error: N of M deals matched no hand type … narrow the condition to
the deals they cover: `and (HandType_a or …)`"*. The old verdict was `levA or
levB or …`, so a deal outside every type was never dealt. Adding the line
(`convert_leveling.py --narrow`) **keeps exactly the set of deals the scenario
produced**. The ladder was filtering as well as leveling, and now the
condition says so.

| scenario | unmatched before | the gap |
|---|---|---|
| `Puppet_Stayman_1N`, `Puppet_Stayman_2N` | 67% | types are North 10-15 / 16-18 / 19+; the condition let North under 10 in |
| `Weak_2_Bids_Leveled` | 6% | North 15-16 without a fit is in neither `rPass` (under 15) nor `rForce` (over 16) |
| `Grand_Slam_Invite` | 6% | `nt1517` needs `p < 18`, which adds a point for a five-card major, so a 17-count 5332 with five of a major is in no band |
| `Minor_Suit_Opener_Balanced_Response` | 1.7% | North 20+; the condition has no top. Its chat's hand-written `21.6%`, `20.0%` … are now `{{level-mix}}` tokens |
| `Rule_of_16` | 0.9% | `r16` outside 14-18 |

If any of those gap hands *should* be practised (North 15-16 without a fit in a
weak-two scenario, say), widen the types instead.

### A type that never occurs, and a budget: `Splinters_after_Minor`

dealer3: *"Error: never seen in 778 deals: `1`."* Type `1` was `part`
(combined TP under 26), which North's splinter makes impossible. I dropped it.
The remaining three are natural game 90 / slam 10 / grand 0.25%. Even leveling
costs about 1.6 million deals per deal kept. At that cost `pbn` can't deal 500
boards within its 300M-deal limit, and a BBO table would stall. The chat says
nothing about a mix, and the ladder dealt close to natural (keeps 1 / 0.70 / 1 /
1). A budget caps the cost, and the cost is set by how far the rarest type is
stretched, so the ceiling here is what `pbn` can deal: 500 boards inside its
300,000,000-deal limit, about 600,000 deals per board. I set
**`# level-budget: 400000`**, just under that: exactness 0.239, a mix of
76.2 / 15.6 / 8.1, which takes grand slams from 0.25% of boards to about 8%.
(At 30,000, which is what the 10,000-deal check would need to run in full,
exactness is 0.011 and the mix is 89.0 / 10.3 / 0.6 — near enough to no
leveling at all.) Options if you disagree: a **higher** budget, closer to even
and dearer to deal; a lower one, closer to natural; or fold `grand` into
`slam` and level two types. Note a BBO table deals this live, at 400,000 deals
a board.

### Overlaps: one type given precedence (5)

dealer3: *"Error: a deal is both `HandType_A` and `HandType_B`."* A precedence
changes only which type a deal is **tagged** as. The set of deals is the same.

- **`Basic_Openers_Rebid`** — `F3min` (rebid a six-card minor) and `F4` (open
  1D, rebid 1S over 1H). South `K986.3.AQ9652.AQ`. The chat says "A second
  four-card suit you can show at the ONE level: bid it", and **BBA rebids 1S on
  all four such deals** in `bba/Basic_Openers_Rebid.pbn`. So
  `HandType_F3min = f3min and not f4`.
- **`Benjamin_2D`** — `s2C1S`/`s2C2S` (2C, up to 24) and `s2DU` (2D, 24+
  unbalanced). South `AKQJT7.A6.AK6.K7`, 24 HCP. The chat: "2D shows 23+
  unbalanced", so 24 unbalanced is 2D: `HandType_s2C2S = s2C2S and not s2DU`,
  and the same for `s2C1S`. (The chat's 2D starts at 23 and the code's at 24; I
  left the ranges alone.)
- **`GIB_1N-P-2C-BID`** — `X` and `3B`. East `53.K74.8.AKJ9653`. `eX` already
  excludes 8- and 9-card suits and 7-4/7-5/7-6, but not 7-3-2-1, which looks
  like an oversight: `HandType_X = eX and not e3B`. A 7-card suit with 3-level
  values bids it.
- **`Meckwell`** — three overlaps, each settled by the chat:
  - `X`/`N`: South `T.96.AKT73.KJT62` (5-5 minors). `oneSuit` counts a 5-5 hand
    as one-suited (it excludes 76/75/65 but not 55), which made it an X via
    `oneMinor`. The chat: "2N = 5-5 or better in C & D". `HandType_X = cX and
    not c2N`. (`oneSuit` itself is probably a bug; I left it.)
  - `H`/`S`: South `KQJ.KQT9854.T.74`. `sGH`/`sGS` are suit *quality*, not
    length, so good three-card spades set `spadeSuit`. The chat's 2H/2S show 5+:
    the longer suit bids.
  - `D`/`N`: South `KQT4..KJT75.KQT6`. `bothMinors` accepts 5-4; the chat's 2N
    is 5-5+, and 2D is "D and a major". `HandType_N = c2N and not (c2C or c2D)`.
- **`Multi_Landy`** — three overlaps, each settled by the chat:
  - `N`/`m6`: South `8.A.KQ8762.KJ952`. 6-5 in the minors is 2N ("5-5 or
    better"), not the X hand with a 6+ minor.
  - `C`/`D`: South `KT9764.AQJT72..A`. 6-6 in the majors is 2C (both majors),
    not 2D (one major).
  - `D`/`m6`: South `7.AKJT87.AKT854.`. 2D is a six-card major "w/o a side
    suit"; six-six with a minor is the X hand.
  - `M5`/`Bal19`: a balanced 19+ with a five-card major. Both are X, so this only
    decides which X subtype it's counted as: `Bal19`.

### Converted by hand (9)

The ladder was there, but not in the shape the converter reads. I rewrote it
into `levelTheDeal = …` first, keeping what it filtered, then converted.

- **`2N_and_3C_Response`, `2N_and_Balanced`** — the condition said `(levGame or
  levSlam)`; now `levelTheDeal = levGame or levSlam`, narrowed.
- **`Weak_2_Bids_Lax`, `Weak_2_Bids_Lax_Leveled`** — the condition said `and
  (case1 or … case4)`; the same, narrowed. The two are identical scripts.
- **`1m-2x`** — the keeps were inline in the condition: `((n3m and keep70) or …
  or n3NT)`. Moved into `levelTheDeal`, narrowed.
- **`DOPI_ROPI`** — `slamZone and (preemptPath or (overcallPath and keep03))`.
  The comment explains the keep: without it "dealer fills the 500-hand cap
  entirely with overcall hands and finds 0 preempts". Leveled evenly, 50/50.
  Preempt hands are 1.3% natural, so this is expensive too (see the table).
- **`Stayman`** — `leveledNorth = (nWeak and keep33) or (nNormal and keep30)`.
  Its comment: "Weak (< 8 HCP) should be about 15% of results". Shares `nWeak
  3, nNormal 17`.
- **`After_Partner_Overcalls`** — **a bug fix.** The keeps `levelRaise … keep67`
  and `levelSuit … keep25` were defined but never applied, because the verdict
  named `nRaises` and `nNewSuit` instead. Now all five types are leveled.
- **`2N_and_Transfers`** — `(levJacoby or levTexas) and (levGame or levSlam)`, two
  lists multiplied. The chat: "leveled to make Jacoby or Texas Transfer AND game
  or slam at about the same frequency". Four product types (JacobyGame,
  JacobySlam, TexasGame, TexasSlam), leveled evenly, deliver exactly that: each
  half 50/50.

## Ladders that leveled nothing, removed

`convert_leveling.py --unlevel` takes out a ladder that changes nothing. I
checked every one by dealing 200 deals with the same seed from the old dlr and
the new: **identical** in all 12.

| scenario | why it did nothing |
|---|---|
| `Mixed_Raise_In_Comp`, `Exclusion_After_1M`, `Lebensohl_vs_Opps_W2_Bal` | every keep is `keep` (keep all) |
| `Jacoby_2N`, `Jacoby_2N_4x_void`, `Preempt_X_XX`, `Weak_2_Bids` | the condition's `and levelTheDeal` is commented out; two have `_Leveled` siblings |
| `Open_In_Fourth_13`, `_14`, `_15`, `_16` | `keep0` on all but one `r15` value — a filter, not leveling |
| `Double_Showing_2_Suits` | `keep0` on North's bids (its comment says why) |

`Mixed_Raise_In_Comp`'s two lists (shortness, support length) overlapped, and
neither was leveled. If you want it leveled, it's the same product question as
the We_X scenarios below. `Exclusion_After_1M` and `Lebensohl_vs_Opps_W2_Bal`
stay at their natural mix (Inv 8.5%, Force 15%). Converting them instead would
level them.

## Needs Rick

Left untouched. Each has the refusal, the evidence, and options.

### What the scenario means is genuinely open

- **`Serious`** — chat: "leveled so that game and slam occur with about the
  same frequency". Three types, Game / Slam / Grand, natural 95.8 / 4.1 / 0.09%.
  The ladder delivers about 60 / 38 / 2, near what the chat says. Options:
  (a) shares 2,1,1 → 50/25/25, with grand a quarter of the boards and the
  dearest (1 deal in 1,100); (b) 10,9,1 → 50/45/5, near today's; (c) fold grand
  into slam.
- **`CRASH`** — overlap: *"a deal is both `HandType_c1H` and `HandType_c1S`"*.
  South `AKT75.AK642.5.Q4` is a rank two-suiter (majors) and has five good
  spades. The script already treats spades specially: `c1D` excludes a black
  two-suiter with good spades, but `c1S` then excludes all color pairs, so that
  hand is in neither. I can't tell which way it wants to go. Options: (a)
  two-suiters first (`c1S = sS1 and not (colorPair or rankPair or shapePair)`);
  (b) good spades first (`c1H`, `c1N` exclude `sS1`, and `c1S` takes the black
  pair back); (c) spades first for the rank pair only.
- **`After_1x_1N`** — overlap: *"a deal is both `HandType_1m2D` and
  `HandType_Bid`"*. North `KQJT7653.K9.4.92`. The 19 types are two lists: the
  specific 2-level call (`om2C` … `oS2D`, no HCP limit) and North's action class
  (`nDoubles`, `nBids`, `nRaises`, `nPasses`), where `nBids` is the union of the
  calls at 5-9 HCP. The calls also overlap each other (`oM2D` and `oS2C` are
  both `sM` with clubs and hearts). Options: (a) drop `levBid`, give each call a
  5-9 range and untangle the call definitions; (b) level only North's four
  action classes; (c) the calls as `HandType_` and the classes as `LevelType_`.
- **`We_X_Opps_Weak_2`, `We_X_Opps_Preempt`** — overlap: *"a deal is both
  `HandType_Invite` and `HandType_SX1`"*. The verdict OR-ed two lists: North's
  strength (weak / invite / force) and South's double (12-15 short / 16-18 /
  19+). Every deal is in two types. **I tried** the obvious fix on Weak_2: tag by
  North's strength, `LevelType_` on the 3×3 cells. It levels, but costs
  **194,723 deals per deal kept**. North 12+ opposite a 19+ doubler is 0.75% of
  qualifying deals, seen 161 times in 60 seconds, which is about 7 of `level`'s
  10 minutes at 2 billion. So I reverted it. Options: (a) level North's strength
  only (cheap; South's double stays natural); (b) level South's double only;
  (c) the 3×3 product with a `# level-budget`.

### Two lists multiplied

Like `2N_and_Transfers`, which I did convert, but bigger, and none of these
chats says what mix is wanted:
**`2N`** (convention × strength, 8×3), **`Forcing_NT`** (`levelResponse and
levelRebid`), **`Gerber_By_Responder`** (7 HCP bands × 3 slam types),
**`Slam_after_Stayman_or_Jacoby_w30plus`** and **`_w31plus`** (fit type × NT
strength), **`BART`** (opening suit × type, via `levelOpening`). The converter
refuses them: *"ladder name keep… used outside the level lines"*, or *"verdict
term is not a name or (name and keep)"*. Options for each: (a) product types
leveled evenly, as in 2N_and_Transfers, which gets dear fast: the rarest cell
sets the cost; (b) one list as `HandType_` and the product as `LevelType_`;
(c) level one list only.

### Too expensive to level as written

Converted by hand and tried, then reverted. A budget doesn't help, because
measuring is what's slow:

| scenario | rarest type | natural | measured in 60s | cost per deal kept |
|---|---|---|---|---|
| `Maximal_Double` | X (responds to a double) | 0.074% | seen 6 times | 10.9 million |
| `McCabe_after_WJO` | Rule17 | 0.19% | seen 20 times | 1.9 million |
| `Play_Top_Tricks_NT` | 2N (exactly 8 top tricks) | 3.5%, but its condition deals only 1.4M deals a second | seen 207 times | 135,000 |

And one that is beyond what the `roll` can express:

- **`1N_Balanced_Raise`** — seven zones from Pass (4-7 HCP) to 7NT (21+), which
  its comment asks to flatten ("keep few of the very common pass/invite/game
  hands and all of the rare slam hands"). I converted it and `level` **failed its
  own check**: Pass was dealt 21.7% against a 14.3% mix, 7.4 points off (allowed
  2). The reason is arithmetic, not sampling. An even seventh for 7NT (0.021% of
  qualifying deals) needs keeps of 0.0005 for the common zones, and `roll` has
  1,000 steps, so 0.0005 becomes 1/1000 — twice what was asked. dealer3 measured
  fine (7N seen 423 times, ±4.9%, after its 2,000,000-deal measure cap).
  Options: (a) shares that ask less of 5NT/7NT — say Pass/Invite/Game 1 each and
  the four slam rungs 2 each; (b) merge 5NT and 7NT into one "grand slam zone";
  (c) level the first four zones only and let the slam rungs fall where they may.
  Its `.btn` is back as it was.

Options for the three above: (a) weights that ask less of the rare type;
(b) widen or merge the rare type; (c) a longer `LEVEL_TIMEOUT` for these. `McCabe_after_WJO` also needs
`keep06 and not c3` read as `keep045`, which it is. `Play_Top_Tricks_NT` keeps
its keeps inside the type definitions, and its `nsMarker` spot-card code for the
play trainer is separate from the ladder.

### Other

- **`Lebensohl2`** — two ladders: `script/Leveling` pasted in for West's hand
  type, and a second, home-made one from South's low cards for North's eight
  branches (`nk75`, `nk32` …), multiplied in the condition. Its comment explains
  why the second exists. Options: (a) West's type as `HandType_`, the 3×8
  product as `LevelType_`; (b) level North's branches only; (c) leave both.
- **`Opps_Preempt_4M`** — `ePreempts and (keep44 or not eight)` thins deals with
  an eight-card fit to 44%. There's no second type to level against. Options:
  (a) two types, `eight` and `not eight`, with shares that reproduce today's
  mix; (b) keep a plain thinning written with a safe `roll`; (c) drop the
  thinning.
- **`Spiral_Raises_Wolpert`, `Spiral_Raises_Weinstein`** — the pattern is clear
  (three teaching hands, keeps in `fourCardLeveled` etc.), but these feed
  `py/spiral_auction.py` and their curated coaching. Re-dealing them would
  invalidate that work. Convert when you next re-curate them.
- **`TEST`** — *"Error: names are used but never defined: west2C, west2D,
  west2H, west2S, west2N."* A scratch scenario. Leave or delete.

## Blocked on cost or budget

Nothing converted was abandoned for cost alone, and only one scenario needed a
budget. `LEVEL_TIMEOUT` is 600s and no committed scenario came within 3 minutes
of it.

**The one budget**: `Splinters_after_Minor`, `# level-budget: 400000` (above).

**Measured on fewer than 2,000 sightings**, so the keeps are known less
precisely than the usual ±2.2%:

| scenario | rarest type seen | precision | why it stopped |
|---|---|---|---|
| `Splinters_after_Minor` | 407 | ±5.0% | the 2,000,000,000-deal generate limit |
| `Ogust` | 1,841 | ±2.3% | the same |

Both still rebuild byte-identically, because a generate limit stops on the same
deal every run. Raising `LEVEL_GENERATE` would sharpen them, at minutes per run.

**The dearest to deal** (deals dealt per kept deal, from the tables above).
This is what a BBO table pays live, and what `pbn` pays for its 500 boards:

| scenario | cost | scenario | cost |
|---|---|---|---|
| `DOPI_ROPI` | 449,141 | `Splinters_after_Minor` | 400,000 |
| `Ogust` | 217,273 | `1N_5M_and_6m` | 188,647 |
| `Lebensohl` | 153,898 | `3N_over_LHO_3x` | 135,220 |
| `Trap_Pass_Opener` | 130,222 | `McCabe_After_Weak_2` | 77,694 |
| `Grand_Slam_Invite` | 74,597 | `Trap_Pass_Opener_Maybe` | 65,111 |
| `Maximal_After_Overcall` | 57,502 | `Spear` | 52,574 |
| `GIB_1N-P-2C-BID` | 52,363 | `2N_and_MSS` | 46,319 |

Most of that is the base condition's own rarity, not the leveling: the `×`
column in the tables is what leveling adds, and it is under 10 for all but
`Minor_Suit_Opener_Resp_Structure` (55), `DOPI_ROPI` (38), `Lebensohl` (18),
`Open_and_Rebid` (19), `Balancing` (16), `NT_Ladder` (16) and
`Basic_What_To_Open` (12). **I have not tried any of these on a BBO table**;
that's `bbo-demo`, which the brief excluded.

**The slowest `level` runs** (the measuring pass, which a budget does not
shorten): `Splinters_after_Minor` 6m47, `McCabe_After_Weak_2` 4m6, `Spear`
4m1, `Trap_Pass_Opener_Maybe` 3m52, `Weak_Jump_Shift` 2m34, `DOPI_ROPI` 2m21,
`Grand_Slam_Invite` 1m58, `1N_5M_and_6m` 1m58. A full rebuild of all 69
leveled scenarios takes about 75 minutes.

**Escalated for cost** rather than converted: `Maximal_Double`,
`McCabe_after_WJO`, `Play_Top_Tricks_NT`, both `We_X_Opps_*`, and
`1N_Balanced_Raise` (see [Needs Rick](#needs-rick)).

## Things that surprised me

- **The measuring limit** (above): the biggest finding, and not a script problem.
- **Many ladders did nothing**: 12 removed without changing a deal, plus
  `Rosenkranz_Double` (all `keep`), and `After_Partner_Overcalls`, whose verdict
  skipped two of its own keeps.
- **Meckwell's `oneSuit`** calls a 5-5 hand one-suited; **GIB's `eX`** lets a
  7-3-2-1 hand double.
- **The gap refusals change nothing** when fixed dealer3's way: the ladders were
  filtering as well as leveling. The overlaps were the real questions, and most
  were settled by the scenario's own chat.
- **Filter match rates barely moved.** Leveling changes which hands come up, not
  how well BBA's auctions fit the filter (table above).
- The issue's screen and mine differ in bookkeeping, not substance: it worked
  on `dlr/` with the ladder pasted, I worked on `btn/`. Rule_of_16 and
  Splinters_after_Minor are new refusals. CRASH and Maximal_After_Overcall
  convert here because the converter reads `(name and keepNN)` verdicts. The
  issue listed Weak_2_Bids as a gap, but in `btn/` its leveling is switched off.

## What I could not verify

- **Nothing was tried on BBO.** `bbo-demo`, `gib` and `release` were excluded by
  the brief, so I don't know whether BBO's own dealer will deal the expensive
  scripts live — `DOPI_ROPI` at 449,141 deals a board, `Splinters_after_Minor`
  at 400,000, `Ogust` at 217,273. That is the one thing I'd check before
  releasing any of them.
- **Only `dlr,level,pbn,rotate,bba,filter,filterStats` were run.** `quiz`,
  `biddingSheet` and `package` were not, so those artifacts are stale for every
  scenario I touched. `manifest/` is built by CI on push, and the chat in it
  will change for the scenarios whose chat now carries `{{level-mix}}`.
- **Curated and coaching artifacts.** Some converted scenarios carry
  `# curate: kind=bidding` (`Drury`, `Stayman`, `Basic_Openers_Rebid`,
  `Basic_Responses`), and their `bba/` pools are now different deals. I did not
  look at `bba-curated/` or `coaching/` to see what that invalidates. The
  `Spiral_Raises_*` pair was left alone for the same reason.
- **`GIB/` captures** are from the old scripts. `gibReport` was not re-run.
- **Basic_Openers_Rebid's precedence** rests on BBA rebidding 1S on all four
  6-4 deals in its own `bba/` file, which is evidence about BBA, not about what
  the lesson wants to teach.
- **`Splinters_after_Minor`'s mix** is measured on 407 sightings of the rarest
  type (±5%), so the delivered grand-slam share could be a point or so off the
  8.1% the file claims.
- **`Weak_2_Bids_Lax` and `Weak_2_Bids_Lax_Leveled` are the same script** (same
  types, same natural rates, same cost). I converted both rather than decide
  whether one should go.
- **The VS Code extension** was not built or run; I changed no TypeScript.
- Nothing is pushed, and no PR was opened.
