# Finesse-family lesson plan

Design + working plan for reworking the **declarer-play finesse lessons** as a
coherent family. Started 2026-07-03 (David + Claude). Companion to
[pbn-curation-plan.md](pbn-curation-plan.md).

**Status: FAMILY COMPLETE — all 8 lessons live** (2026-07-03). Rebuilt: Finesse_Simple bd1
(`7888e8565`), Choice (`0af244bbc`), Rabbi's (`ed685535a`), To_Finesse_Or_Not (`9467a3361`,
5-board #1→#2 walk). NEW: Ruffing_Finesse (`8c8584352`, 4 bds), Double_Finesse (`0ff013766`, 3 bds),
Repeated_Finesse (4 bds). Two_Way + Finesse_Simple verified clean. Method §9 proven; toolkit
`py/finesse-harvest/`. Remaining (later): expand tight cuts as clean boards surface; §6 faceted
cross-listing + BC dup-id check; §8 opens.

---

## 1. The family — who owns what (learning-progression order)

All `[ROLE declarer]` play lessons (student = South = declarer). The set grows from 5 to 8.
They form a **progression**: each lesson may assume the earlier ones and must not re-teach them.

| # | Lesson | Owns the skill | New? |
|---|---|---|---|
| 1 | **Finesse_Simple** | Take a single finesse — the mechanic (lead toward the honor) | live |
| 1b | **Ruffing_Finesse** | The trump-contract finesse: run an honor, ruff it if covered, pitch if not | live |
| 1c | **Double_Finesse** | Two missing honors in one suit — finesse twice | live |
| 2 | **To_Finesse_Or_Not** | *Whether* at all — restraint + evidence; a safe line vs. a losing finesse | rebuilt |
| 3 | **Two_Way_Finesse** | *Which direction* — finesse either opponent, resolved by the count/bidding | live (verified) |
| 3b | **Repeated_Finesse** | Finesse the same suit several times — lives on entries | live |
| 4 | **Choice_Of_Finesses** | *Which of several* + **combine chances** + order (entries / danger hand) | live (rebuild) |
| 5 | **Rabbi's_Rule** | Finesse vs. the **drop** — play the ace for the stiff honor, *with a reason* | live (rebuild) |

**Progression payoff:** Choice can assume counting (from To_Finesse) and single-suit inference
(from Two_Way) — so it goes straight at combining/order. To_Finesse can assume the mechanic (from
Simple). Each lesson stays narrow because the earlier ones did their job. Difficulty rises across
the set.

**Boundary guards (prevent overlap):**
- Choice stays **multi-suit / combining**. Single-suit direction-guessing → Two_Way.
- To_Finesse's alternative is a **non-drop safe line** (establish, duck, count you don't need it).
  Finesse-vs-drop → Rabbi's.
- Avoidance (danger/safe hand) is a **cross-cutting reason, not its own lesson** — folded into
  Choice as "the reason the order is forced."

---

## 2. The declarer's decision framework (teaching backbone)

1. **Count first.** How many tricks, how many finesses must work? → combine (need one of two) or
   pick the best single one.
2. **Is it already *known*? (inference from the bidding.)** Opener/overcaller holds the honors
   (finesse *through*); a passed hand is capped (a shown honor *places* the rest); preempt/long-suit
   marks shape → vacant spaces; silence is a negative inference.
3. **Can I *discover* it? (inference from the play.)** Play the *other* suits first and **count**
   (who follows, who shows out) until the suit is placed — often pick it up by drop. Test a suit
   (discovery play); cash the top of the finesse suit first (free stiff-honor chance + a look);
   strip toward an endplay. Prefer *free* discovery to *paid*.
4. **Still a mystery? Combine chances.** Take the finesse whose *loss still leaves the other* — 50%
   → ~75%. Order forced by **entries**, the **danger hand** (lose to the safe hand first), and
   **free chances first**.
5. **Can only take one? Best odds.** Two-way (count the hand), finesse-vs-drop ("8 ever, 9 never").
6. **Timing — commit as late as you safely can.** Cash sure tricks and gather the count first;
   deadline set by entries (route about to vanish) and control/tempo (act while you hold a stopper).

Through-line: **count first, guess last.** A finesse is a last resort; combining is the safety net.

---

## 3. Per-lesson concept + arc

**Choice_Of_Finesses** (rebuild, FIRST — validates the method).
- Open: two plain finesses, take both (either order makes).
- Middle: order forced by **entries**.
- Harder: order forced by the **danger hand** (safe-loss finesse first — avoidance re-enters).
- Judgment: combining vs. a single better-odds finesse; cash-for-drop-then-finesse.
- Scope: mostly 3NT, a couple competitive auctions (to *place* an honor), tight ~10-board arc.

**To_Finesse_Or_Not** (rebuild). *Whether* — the finesse is a gamble that costs the hand.
- **Walk: #1 decline-the-unnecessary-finesse (count; a safe line makes) → #2 demand-evidence-before-
  risking-a-needed-one.** Weighted #1 up front (it comes early in the progression). *(SETTLED.)*
- Signature board: a safe line makes AND a tempting finesse loses. Non-drop alternative only.

**Rabbi's_Rule** (rebuild toward good bridge). Naive "cash and pray" is luck; good bridge needs a reason:
(1) the count marks the king short; (2) the drop is the safe line, the finesse the unsafe one;
(3) the ace is a free first chance (combine drop + finesse). Weed the luck-boards. Prefer #1 and #3.

**Ruffing_Finesse** (NEW, suit contracts). Sequence short opposite void/singleton: cash the ace,
run the queen through — ruff the king if covered, pitch a loser if not. A finesse you can't lose.
Sits by Finesse_Simple as "the same mechanic, with trumps."

**Double_Finesse** (NEW). AQ10 missing KJ, or AJ10 missing KQ: finesse twice in one suit; ~76% for
one of two. Extension of Simple.

**Repeated_Finesse** (NEW). AQJ / KJ10 finessed multiple times — lives on entries. Pairs with Choice.

**Two_Way_Finesse**, **Finesse_Simple**: largely in-lane; verify, light touch only.

---

## 4. Sourcing strategy

- **A hand is 52 cards, decoupled from the scenario that dealt it.** We own the auction/contract we
  wrap around a harvested deal. Origin scenario is irrelevant to fitness.
- **All ~339 scenario pools are fair game** — not just the finesse or play pools. Curated scenarios
  each carry ~500-deal pools (`bba-curated/`, `bba/`, `pbn/`).
- **Intent prioritizes the search** (makes ~170k deals tractable — mine the dense veins):

  | Target structure | Prioritize pools whose intent is… |
  |---|---|
  | Combining chances (two side-suit finesses, 3NT) | notrump: Basic_NT, Stayman, Smolen, 3N_Rebid_by_Opener, Slam_after_Stayman |
  | Good-bridge Rabbi's (a *marked* short king) | competitive/preempt: Basic_Overcall, Basic_Weak_2, Basic_Takeout_Double, Negative/Responsive_Double |
  | Two-way finesse (one-suit guess, count) | slam: Gerber, Jacoby_2N, Splinters, Slam_after_Stayman |
  | Ruffing finesse (suit contract) | Suit Contract Play pools; suit-fit/slam pools |
  | To_Finesse_Or_Not (safe line vs. losing finesse) | notrump + suit-fit pools |

- **Universal gate:** South declares the target contract and the target line makes (DDS), regardless
  of source pool.
- Generation from scratch is a **last resort** (the generic pools' boilerplate `{Curate}` annotation
  is not per-board analysis). Mac `dealer3` at `/Applications/Bridge Utilities/dealer3`; card token
  order is **rank+suit** (`hascard(south, AS)` = ace of spades) — wrong order silently no-ops.

**Identify play vs. bid scenarios:** the `# curate: kind=` btn header. `soundness`/`avoidance`/
`byforce` = play (12); `bidding` = bid (28); *none* = legacy uncurated (~299).

---

## 5. Architecture — two layers (source vs. lesson)

Harvesting splits one thing into two:
- **Source scenario** = a btn (dealer code → a ~500-deal pool). One per scenario. A deal *factory*.
- **Play lesson** = a curated *collection* of harvested deals + coaching. Assembled from *many*
  sources. Its home is `coaching-curated/<lesson>.pbn` + toc/layout entries — **not** a btn.
  (A lesson may keep a thin btn as a BBO-import/metadata shell; its dealer code is then vestigial.
  OPEN — see §8.)

**Metadata lives at the collection layer** (the lesson), not the factory (the btn). Facets/section
membership/coaching belong to the lesson.

**Provenance (what Rick wants: filename + original board number).** Each harvested board records:
- `[OriginalScenario "<source>"]` — the source pool it came from (NEW; needed once boards come from
  many pools — `[Event]` holds the *lesson*/destination, not the source).
- `[OriginalBoard N]` — its board number in that pool (existing).
This pair is the origin key. Simple, needed now, no canonicalization.

**Canonical deal-hash (trove key) — SEPARATE, LATER todo.** The existing `%` line is a SHA-1 of the
deal *string* (`py/rotate180.py`: `sha1(deal_str)[:28].upper()`), so it fingerprints the *written
form* (seat order, card order, orientation) — `rotate180` recomputes it after rotating. It is **not**
a rotation-stable / canonical identity and can't be the harvest key as-is. A canonical deal-hash
(normalize to a fixed orientation + sorted holdings, then hash) is a distinct future task, to be
settled *with* how BC keys its records (Rick's side) before freezing. Origin-tracking (above) does
not depend on it.

---

## 6. Curriculum organization — faceted (multi-membership)

"Play of the Hand" (a Major) currently has three Sections: **Finesses**, **Notrump Play**, **Suit
Contract Play** — a *mixed* taxonomy (Finesses = technique; the others = contract type), which is why
placing the ruffing finesse felt ambiguous.

**Resolution: don't pick technique-vs-contract — treat sections as *views over a tagged lesson*, and
let a lesson belong to more than one.** Multi-membership is already an established pattern on the
bidding side (Drury, Lebensohl, Minor_Suit_Stayman… appear in multiple `[Section]`s), and the toc
models membership as *group → lessons list*, so a lesson can appear in multiple groups.

- Keep **technique** sections (Finesses, Ruffing, Avoidance, Endplays, Planning) *and* **contract**
  sections (Notrump Play, Suit Contract Play) as overlapping views.
- Each lesson gets **one primary home** (for the progression + to avoid menu clutter) plus **curated
  cross-listings** where they aid discovery. A scalpel, not a firehose.
- Finesse family: primary home **Finesses**; cross-list by contract (Choice/To_Finesse → Notrump
  Play; Ruffing/Two_Way/Rabbi's → Suit Contract Play).

**To verify (not assume):** that BC's frontend renders a lesson appearing in two toc groups
gracefully (navigating by a repeated id). Editing toc.json is PBS content (clear of the BC freeze);
only a *fix* if BC chokes would touch the engine. BBO-side cross-listing works regardless.

**Deferred / phased** (separate from content, not blocking the builds): implement the faceted reorg
in layout/toc; optional facet-tags-generate-layout refactor (single source of truth); optional
explicit `# discipline: play|bid` tag.

---

## 7. Engine-fidelity constraints (why board *selection* is constrained)

Interactive via a **double-dummy** recorded `[Play]` line (`py/play_line.py`) + a **replay bot** that
falls to legal-arbitrary cards once the student diverges.
- **Auction inferences: rock-solid** (bidding is fixed/shown).
- **Count inferences (who shows out): solid** (fixed by the deal). "Cash, count, then finesse" renders.
- **Signal / discretionary-defense inferences: fragile** — avoid boards that hinge on reading a signal.
- **Combining needs the fallback *visible*:** a DD declarer never combines, so curate deals where
  **one finesse is offside, one onside** — the student takes the first, it loses, the fallback wins.

**Serve chain (per lesson):** author `coaching-curated/<scn>.pbn` (South-fixed, token-free) →
`coach.py validate` + `suit_quality.py` → `nonrotate.py` → `bridge_classroom.py` (injects `[Play]`) →
`promote.py` (gated → `coaching/`). Same-count swaps need no toc edit. Never hand-edit `coaching/`
or `coaching-non-rotated/`.

---

## 8. Open questions

- Does a harvested lesson keep a thin (vestigial-dealer) btn, or become a pure collection?
- Contract-type mixing within a lesson vs. one contract family per lesson.
- Set sizes: full 30 vs. tight ~8–12.
- BC duplicate-id-across-groups render check (§6).
- Avoidance: fold into Choice permanently, or its own lesson eventually?

---

## 9. Method — PROVEN (Choice, Rabbi's, To_Finesse #2)

**Detector** (`scratchpad/finesse_detect.py`). Scan `bba/<pool>.pbn` for boards where **South
declares** a game/slam that **makes EXACTLY** (DDS table, `endplay.dds.calc_dd_table`, index
`t[Denom, Player]`). For each missing honor (K/Q/J the NS side lacks) held by a defender, run the
**swing test**: move that honor to the *other* defender, re-solve, and read `delta = base − t2`:
- **`delta < 0`** → the honor is *offside/unneeded*; the safe line still makes → **decline rung (#1)**.
- **`delta > 0`** → the honor is *onside and needed*; making depends on it → **evidence rung (#2)**.
Annotate each swing with whether the honor-holder bid (`holder_bid`) and the E/W calls, so a
marking auction can be spotted. Run in the **background to JSON** (full-table DDS over ~15 pools
exceeds a 2-min foreground call). Filter to real games/slams (`level≥4` or `3N`).

**The swing test flags honor-location SENSITIVITY, which is NOT the same as a takeable finesse** —
and this is where nearly all candidates die. A `delta>0` board must survive three more filters, in
order of how many it kills:

1. **The DD `[Play]` line must actually TAKE the finesse** (`scratchpad/finesse_taken.py`). Generate
   the line, and require declarer to **win a finesse-suit trick with a card *below* the missing
   honor while the marked honor NEVER wins a trick** (it is captured/trapped). This one filter
   removes the majority. Failure modes it catches, all of which "make exactly" yet make by a
   *different* mechanism, so "finesse the marked King" would be a lie:
   - **side-suit establishment** (b445: makes on a long diamond, concedes the ♠K),
   - **honor-forced establishment** (b324: cash A, concede the K, the Q-J are now high — not a finesse),
   - **doubleton drop** (b332: KJ tight falls under AQ — that is Rabbi's, not a finesse),
   - **defensive gift** (b183 under the natural ♥A lead: the DD defender leads into the tenace).
2. **The forced opening lead must be West's genuinely principled lead** (top-of-sequence / longest
   suit) *and* the finesse must still be the making line under THAT lead. A board that only finesses
   under an unnatural passive lead is out (b183: finesses under an ace-underlead, but West's real
   lead is the ♥A → gift line). `verify_play.py` force-leads a card and counts declarer tricks.
3. **The marking must place the specific honor.** `holder_bid=True` is necessary, not sufficient: a
   1♣ opening does not mark a *heart* Q. Keep only where the holder **bid the finesse suit, bid NT,
   or made an opening/overcall whose values place the missing King** — i.e. a clean *"finesse into
   the bidder."* Trust the DDS `delta` for on/offside; hand-geometry ("who sits over the tenace") is
   error-prone in trump contracts with a missing ace — the sign already encodes it.

**Per-pool yield (competitive scan, 15 pools, makes-exact game/slam, South declares):** Basic_Overcall
11, Dealing_with_Overcalls_Strong 32, _Weak 24, After_Opp_Overcalls 23, Negative_Double 31,
Support_Double 8, Takeout_Double 8, Jump_Overcalls 5, Michaels 0, Unusual_2N 2, Opps_Overcall_1NT 2,
We_X_Opps_Weak_2 8, Opps_Preempt 14, Maximal 3, Game_Overcalls 36. Of **44** single-swing rung-2
`holder_bid` candidates, **18** survived filter #1 (finesse genuinely taken), and only a handful
survived filters #2–#3 with a clean principled lead → the tight cut the memory predicted. The dense
vein for *side-suit* finesses-into-the-opener was **Game_Overcalls** ("1X–4M" auctions: RHO opens,
South preempts to game); most of its boards are *trump* finesses (South's long suit) and only the
side-suit ones (e.g. b253) are in-lane.

**Serve chain (play lesson):** author `coaching-curated/<scn>.pbn` (South-fixed, `[ROLE]/[STAGE]`
blocks, `[show NESW]`, `{Shape}/{HCP}/{Losers}` + `%` fingerprint copied from the bba source, `[OriginalScenario]`+`[OriginalBoard]`) →
`py/coach.py validate` + `py/suit_quality.py` → `py/nonrotate.py` (folds; play boards pass through) →
`py/bridge_classroom.py` (strips metadata blocks, injects the `[Play]` line via `play_line.process`
for any `[ROLE declarer]` board) → `py/promote.py` (gated curated→served). `[Auction "E/N/W"]`
non-South dealers render fine (250+ served boards already do).

**Toolkit: `py/finesse-harvest/`** (promoted from the session scratchpad 2026-07-03; see its README
for invocations). `finesse_detect.py` (scan → JSON), `rank.py` (eyeball by rung), `finesse_taken.py`
(the genuinely-takes-the-finesse filter), `verify_play.py` (force a lead / `--show` the DD line),
`meta.py` ({Shape}/{HCP}/{Losers}), `check_served.py` (served `[Play]` makes contract). Kept in its
own subdirectory rather than flat `py/` so intra-toolkit imports never put `py/` on `sys.path`
(`py/select.py` shadows the stdlib module endplay needs — see the `-P` convention).

---

## 10. Progress log

- **2026-07-03** — Finesse_Simple board 1 re-curated (pool board 70), committed `7888e8565`. Family
  design, sourcing/architecture/organization, and this plan drafted. Next: build Choice_Of_Finesses.
- **2026-07-03** — Choice_Of_Finesses (`0af244bbc`) + Rabbi's_Rule (`ed685535a`) rebuilt.
- **2026-07-03** — **To_Finesse_Or_Not rebuilt** as a 5-board **#1→#2 walk**: three *decline* boards
  (4S / 6NT / 6C — count first, the finesse is needless) reused from the native pool, then two
  *demand-evidence* boards harvested from **Game_Overcalls** — b253 (4S, ♣ A-Q-J finesse into the 1♦
  opener) and b363 (6H slam, ♠ A-Q finesse into the 1♣ opener): *finesse into the bidder; the opening
  bid marks the King.* Both make exactly and the served `[Play]` genuinely takes the finesse (honor
  trapped). §9 Method backfilled & proven. Two_Way (29) + Finesse_Simple (30) served lines all make.
  Expansion candidates parked: overcaller-marked #2 boards (b292/b332-family) — need clean principled
  leads; most failed the "finesse actually taken" filter. NEXT: new Ruffing / Double / Repeated lessons.
- **2026-07-03** — Harvest toolkit **promoted to `py/finesse-harvest/`** (detect / rank / taken /
  verify_play / meta / check_served + README); all six smoke-tested against the session's known-good
  outputs from the new location.
- **2026-07-03** — **Ruffing_Finesse NEW lesson shipped** (`8c8584352`, 4 boards): 4♥ both branches
  (duck→pitch, cover→ruff, dummy's KQJ643 opposite a void), 4♠ AQJT9 signature after a splinter,
  4♠ loser-on-loser jack ride after Jacoby 2NT, 6♣ slam riding on the heart ruffing finesse. New
  `ruffing_detect.py` (structural scan — swing tests can't see a can't-lose finesse; DD-line acid =
  sequence honor led, short hand ruffs the cover or pitches). 174 raw → 85 front → 4 survivors; the
  real-lead re-dump killed b308 (DD pitches the suit away), b421 (defensive gift), b430/b466
  (overtricks / ambiguous lead). Finesses toc shelf reordered to the plan's progression.
- **2026-07-03** — **Double_Finesse NEW lesson shipped** (`0ff013766`, 3 boards): 3NT ♣AJT2 both
  hooks genuinely taken, 3NT after 2NT-Smolen (queen rises into the ace), 5♣ after Michaels —
  lose-win-win with the five-five bid marking the honors. New `double_detect.py`; acid refinement
  learned: the second sub-honor win must come **while a missing honor is still live** (b56's "second
  finesse" was a routine cash after the ace dropped a doubleton queen). 64 raw → 3 survivors; killed:
  doubleton drops (b56), DD drop-and-ruff lines (b29), A-K-cash-then-exit gift lines (b387),
  overtricks under the true lead (b455/b379/b90), lead-ambiguous (b381).
- **2026-07-03** — **Repeated_Finesse NEW lesson shipped** (4 boards; family COMPLETE at 8 lessons).
  Arc: 3NT ♠AQJ vs guarded K (dummy's two heart honors = exactly the two entries), 3NT ♣AQJ64 hooking
  twice through West's K987 (overtake the ♠Q for the re-entry — entry management on screen), 3NT
  ♦AKJT vs Q943 (the ten is the first finesse), 6NT ♦AQJ9 vs KT72 — deep repeat (hook the NINE, then
  the jack) where **EPBot's own playout went one down**; the repeat IS the slam. Detector bug found +
  fixed: the `front`/onside map was **inverted** (tenace in North → onside defender is WEST, who
  plays before dummy) — the first scan's 6 "hits" were all duck-dependent establishment, none real.
  Corrected full-corpus rescan: ~90 raw → 36 mainstream-auction → 4 survivors (b63/b38 overtricks
  under the true lead, exotic-system pools deprioritized).
