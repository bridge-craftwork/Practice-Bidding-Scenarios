# Finesse-family lesson plan

Design + working plan for reworking the **declarer-play finesse lessons** as a
coherent family. Started 2026-07-03 (David + Claude). Companion to
[pbn-curation-plan.md](pbn-curation-plan.md).

**Status:** design settled; method unproven (see §9). First change shipped:
Finesse_Simple board 1 re-curated (commit `7888e8565`).

---

## 1. The family — who owns what (learning-progression order)

All `[ROLE declarer]` play lessons (student = South = declarer). The set grows from 5 to 8.
They form a **progression**: each lesson may assume the earlier ones and must not re-teach them.

| # | Lesson | Owns the skill | New? |
|---|---|---|---|
| 1 | **Finesse_Simple** | Take a single finesse — the mechanic (lead toward the honor) | live |
| 1b | **Ruffing_Finesse** | The trump-contract finesse: run an honor, ruff it if covered, pitch if not | NEW |
| 1c | **Double_Finesse** | Two missing honors in one suit — finesse twice | NEW |
| 2 | **To_Finesse_Or_Not** | *Whether* at all — restraint + evidence; a safe line vs. a losing finesse | live (rebuild) |
| 3 | **Two_Way_Finesse** | *Which direction* — finesse either opponent, resolved by the count/bidding | live (verify) |
| 3b | **Repeated_Finesse** | Finesse the same suit several times — lives on entries | NEW |
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

## 9. Method — TO BE VALIDATED (fill in after Choice proves it)

Intended: one **structural DDS detector** classifying a deal by finesse shape (single clean / one-suit
two-way / two takeable finesses / safe-line-vs-losing-finesse / short-honor-drop-with-a-reason), run
**intent-prioritized** over the dense pools, harvest per rung, DDS-verify, author, serve. Detector
specifics + per-pool yields + board slates recorded here once Choice validates the pipeline.

_Detector notes (early scans):_ full-table DDS on ~425 boards exceeds a 2-min foreground call — run
scans in the background to JSON. A holding-agnostic **swing test** (move a missing K/Q to the other
defender, re-solve, see if the count moves) detects finesses regardless of card shape, but over-flags
notrump-stopper and stiff-honor positions — the detector must distinguish a *takeable finesse* (lead
toward a tenace) from mere honor-location sensitivity.

---

## 10. Progress log

- **2026-07-03** — Finesse_Simple board 1 re-curated (pool board 70), committed `7888e8565`. Family
  design, sourcing/architecture/organization, and this plan drafted. Next: build Choice_Of_Finesses.
