# Basic Bidding & Play Scenarios — Status

Beginner-facing scenarios in two groups: **Basic Bidding** (`Bidding Scenarios/01 Beginners Bidding/`) and **Play technique** (`Bidding Scenarios/18-20 Notrump Play / Suit Contract Play/`).

## Basic Bidding (7 scenarios)

| Scenario | Purpose | Status |
|---|---|---|
| Basic_What_To_Open | Opening choice (1m/1M/1NT/Pass) | Stable |
| Basic_Major | 1H / 1S opening + standard responses | Stable |
| Basic_Minor | 1C / 1D opening + responses | Stable |
| Basic_NT | 1NT opening + Stayman / transfers | Stable |
| Basic_Overcall | Simple overcall after opp's 1-of-suit | Stable |
| Basic_Takeout_Double | Takeout double after opp's opening | Stable |
| Basic_Weak_2 | Weak 2 openings + 2NT inquiry (feature) | Stable; 2D added in commit `68e94c93` |

No active work on these in this session. They use `Basic-Bridge.bbsa` as the convention card.

## Play Technique (5 scenarios)

| Scenario | Final Contract | Teaching Point | Status |
|---|---|---|---|
| Play_Top_Tricks | 2-level partial (suit or NT) | Count tricks before playing | Older; superseded by NT/Suit split |
| [Play_Top_Tricks_NT](../btn/Play_Top_Tricks_NT.btn) | 3NT | Quick tricks in NT (chain × length) | Stable. 3 paths (Pass / 2NT / 3NT) balanced via Leveling; topTricksNS enforced per path |
| [Play_Top_Tricks_Suit](btn/Play_Top_Tricks_Suit.btn) | 2X / 3X / 4M | Trump-suit length + side-suit ruffs | **Active — see session work below** |
| [Side_Suit_Ruff_Before_Trump](../btn/Side_Suit_Ruff_Before_Trump.btn) | 4S | Ruff dummy's singleton before drawing trumps | Stable |
| [Endplay_3rd_Round_Strip](../btn/Endplay_3rd_Round_Strip.btn) | 4S | Strip-and-endplay (throw E in with hearts) | Stable |

Both `Play_Top_Tricks_NT` and `Play_Top_Tricks_Suit` use a shared concept of `topTricksNS` (count of sure winners) but with **different formulas** — one tuned for NT play, the other for suit play. The scripts are:
- `script/topTricksNS` — NT version: chain × longer-hand length, requires all 4 aces
- `script/topTricksSuitNS` — Suit version: first-round stops + trump-suit length + side-suit ruff bonus

## What we did this session (Play_Top_Tricks_Suit)

1. **Created `script/topTricksSuitNS`** — reusable suit-contract top-trick calculator. Extracted from the btn.
2. **Side-suit voids count as first-round stops** — a void in NS hand ruffs the first round of that suit (equivalent to holding the ace).
3. **Second-round ruff bonus** — a side-suit void in a hand that still holds 4+ trumps takes a second ruff before running out of trumps.
4. **Continuous trump-tricks formula** — `trumpTricks = chain ≥ opps ? nsTrumpLen : (nsTrumpLen - opps + chain)`. Closes the gap between chain mode (0-5) and length mode (8+) that the original formula had.
5. **Multi-path scenario design** — three responder paths predicting the final contract level:
   - **2X simple raise** (1X-P-2X) → opener=12, tpNorth 6-9, fit → 8 top tricks
   - **3X passed limit** (1X-P-3X) → opener=12, tpNorth 10-12, fit → 9 top tricks
   - **4M accepted limit** (1M-P-3M-P-4M) → opener=14, tpNorth 10-12, major fit → 10+ top tricks
6. **Leveling** (`keep25`, `keep03`) to balance natural path frequencies after constraints.
7. **`tpNorth` instead of `hcp(north)`** — shape-aware classification matching BBA's evaluation. Shapely 6-9 HCP hands have tp 10-12 and naturally fall into the limit-raise bucket.
8. **Simplified `Basic-Bridge.bbsa`** (user-edited via the BBA UI) — disabled Jacoby 2NT, Inverted Minors, Bergen, Unusual 2NT to reduce auction noise in beginner scenarios.

## Where we stand (Play_Top_Tricks_Suit)

Latest run (commit `ef9b0a719`):

| Level | N hands | avg topTricks | target | gap |
|---|---|---|---|---|
| 2 | 30 | 8.63 | 8 | +0.63 |
| 3 | 42 | 8.93 | 9 | -0.07 ✓ |
| 4 | 68 | 9.51 | 10 | -0.49 |

- 141 filtered hands from 500 produced (~28%)
- Levels 2 and 3 close to target; level 4 still has ~50% of hands that go down 1 trick
- The remaining bleed: BBA's shape-based limit-raise acceptance still fires at opener=12

## What we need to do

### Play_Top_Tricks_Suit (open items)

1. **Apply `tpSouth` to opener** — would let BBA's opener evaluation align with our path categorization. Should further reduce level-4 bleed.
2. **Add 1-of-suit path** (`1X-P-P-P`) — pass-out scenario. Responder very weak (0-5), no fit. Target 7 top tricks.
3. **Add 5-of-minor path** — challenging because BBA prefers 3NT over 5m with balanced hands. Need shapely responder + no NT stoppers. Target 11 top tricks.
4. **Verify per-board topTricks** matches actual play results — current model under-counts vs BBA single-dummy in some cases.

### Cross-scenario work

5. **Audit other beginner scenarios for consistency** — confirm `Basic-Bridge.bbsa` changes (Jacoby/Bergen/Inverted/Unusual off) haven't broken any of the 7 `Basic_*` scenarios.
6. **Consider the older `Play_Top_Tricks`** — is it obsolete now that NT and Suit are split? Could be deleted.
7. **Top-tricks teaching pages** — consider adding `@chat` content that walks players through counting before playing.

### Architecture / shared

8. **Cross-platform topTricks for the play trainer** — the web Play Trainer (see `[[project_play_trainer_status.md]]`) could reuse the same topTricks formulas to grade declarer play. Worth porting `topTricksSuitNS` logic to TypeScript when wiring Claude grading.
9. **Tooling**: `/tmp/top_tricks_per_board.py` (used in this session to verify alignment) is reusable — could move it into `py/` as `verify_top_tricks.py` if we plan to run regression on these stats.
