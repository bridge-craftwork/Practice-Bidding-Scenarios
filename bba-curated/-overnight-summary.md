# Layer A overnight run — 2026-06-04/05

First full run of the generalized `curate` script (`py/curate.py`) over all
19 coaching scenarios (7 bidding, 12 play): the current 30-board coaching
sets **and** the full 500-board `bba/` pools — ~10,000 boards, DD-classified
in the Cowork sandbox (endplay installed there fine, contrary to the earlier
note). Per-scenario verdicts: `bba-curated/<scenario>.json` + `-report.md`.
Nothing is committed — review first.

## Headlines

1. **The Proposal's numbers re-validated exactly.** Suit_Promotion: 22 ok /
   1 wrong-sided / 7 down-both; Hold_Up_3N: 24/2/4 — identical to the June 2
   measurements. The generalized script agrees with the prototype.

2. **New finding: the Basic bidding coaching sets have *higher* DD-defect
   rates than the play sets** — 5–10 of 30 boards each (avg ~19%) where the
   taught contract fails on best defense or only makes from partner's seat.
   Caveat: for a *bidding* lesson a failing contract isn't automatically a
   defect (you can bid perfectly and go down) — but a beginner lesson that
   ends "and 3NT went two down" is poor reinforcement. This is exactly the
   judgment call Layer B grades; the DD class rides along as evidence.

3. **The hold-up oracle found 57 pool boards where the hold-up is genuinely
   required** (vs 6 of 30 in the current coaching set). That's a positively
   selected replacement pool for Hold_Up_3N — the single-dummy idea works as
   a selector, not just a defect detector.

4. **Choice_Of_Finesses confirms the Phase-2 gap.** The structural shape
   filter matched 500/500 pool boards (the Dealer constraints already force
   the shape), so it doesn't discriminate. Positive selection there still
   needs single-dummy Monte-Carlo. Two_Way_Finesse (138/500) and
   To_Finesse_Or_Not (199/500) do discriminate structurally.

5. **By-force pools are huge**: 342–424 of 500 per Play_Top_Tricks-family
   scenario survive the honor-swap test. Selection can afford to be picky.

6. **Regex feature validated**: applying each `.btn` `# auction-filter`
   regex in Python reproduced `bba-filtered/` membership with **zero
   disagreements** across all ~9,500 pool boards. The regex is now safely a
   feature (`matched_intended_auction`), per the plan.

## Per-scenario table

| Scenario | kind | coach defects /30 | pool DD-ok /500 | regex-matched | extra |
|---|---|---|---|---|---|
| Basic_Major | bidding | 8 | 373 | 294 | |
| Basic_Minor | bidding | 8 | 366 | 317 | |
| Basic_NT | bidding | 5 | 392 | 460 | |
| Basic_Overcall | bidding | 8 | 309 | 295 | |
| Basic_Takeout_Double | bidding | 10 | 316 | 448 | |
| Basic_Weak_2 | bidding | 10 | 364 | 360 | |
| Basic_What_To_Open | bidding | 8 | 344 | 500 | |
| Play_Top_Tricks | byforce | 0 | 424 | 156 | by-force 399 |
| Play_Top_Tricks_NT | byforce | 2 | 443 | 500 | by-force 424 |
| Play_Top_Tricks_Suit | byforce | 2 | 368 | 142 | by-force 342 |
| Rabbis_Rule | byforce | 0 | 422 | 110 | by-force 394 |
| Suit_Promotion | byforce | 8 | 405 | 500 | by-force 377 |
| Finesse_Simple | soundness | 4 | 389 | 500 | |
| Endplay_3rd_Round_Strip | soundness | 3 | 428 | 376 | |
| Side_Suit_Ruff_Before_Trump | soundness | 2 | 422 | 335 | |
| Hold_Up_3N | avoidance | 6 | 423 | 500 | hold-up required 57 |
| Choice_Of_Finesses | avoidance | 0 | 483 | 500 | shaped 500 (no signal) |
| Two_Way_Finesse | avoidance | 4 | 423 | 500 | shaped 138 |
| To_Finesse_Or_Not_To_Finesse | avoidance | 2 | 485 | 160 | shaped 199 |

"Coach defects" = wrong-sided + down-both vs the board's own contract.
Defective boards are listed in each `<scenario>-report.md`.

## Notes & caveats

- Scenario kinds and oracles are configured in `CONFIG` at the top of
  `py/curate.py` — review my kind assignments (e.g. Finesse_Simple as
  `soundness` rather than `avoidance`). Moving these into a `# curate:`
  directive in the `.btn` files is the planned next step, left for review
  rather than editing 19 masters overnight.
- The sandbox kills long processes, so the script is time-budgeted and
  resumable (`CURATE_BUDGET` env var, checkpoints in
  `bba-curated/.progress/*.jsonl`). On your Mac it can simply run to
  completion in one go.
- `down_both` for bidding scenarios is evidence, not a verdict (see #2).
- New/changed files (all uncommitted): `py/curate.py`,
  `notes/plans/pbn-curation-plan.md`, `bba-curated/*` (19 JSON + 19 reports + this
  summary + `.progress/`). The `.progress/` directory is disposable cache —
  candidates for `.gitignore`.

## Suggested next steps (in order)

1. Review this summary + spot-check one report (`Suit_Promotion-report.md`
   lists the 8 defective boards with trick counts).
2. Approve/adjust the `CONFIG` kind assignments; decide on the `# curate:`
   btn directive.
3. Layer B pilot on Basic_NT (grading + the regex-reject yield analysis).
