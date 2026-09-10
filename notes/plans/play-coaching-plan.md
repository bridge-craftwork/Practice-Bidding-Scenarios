# Rough Plan — Coaching Play

*Draft, 2026-06-25. Synthesized from a design discussion; not yet built.*

**Goal:** extend play coaching beyond declarer to all three playable seats, picking the
right deals per seat instead of forcing one deal to teach everything.

## Principles

1. **Topics attach to seats.** Opening Lead, Declarer Play, Signaling, Counting Cards,
   Counting Points, Inferences from the Bidding — each maps to the seat(s) where it
   applies. (Signaling: defenders emit and read; declarer reads *and* disrupts via
   falsecards.)
2. **Four seats, named from declarer's frame** (clockwise: Declarer → LHO → Dummy → RHO).
   Three carry lessons — **Declarer** (declarer play), **LHO** (opening lead, then
   defense), **RHO** (third-hand defense). **Dummy** has no decisions, so no deck. LHO/RHO
   names the two defenders precisely (LHO leads then defends; RHO is third hand). NB: the
   on-disk marker still reads `[ROLE leader]` (≡ LHO) and `[ROLE declarer]`; renaming the
   marker string touches the trainer parser (Rick's side) — adopt LHO/RHO only in our
   vocabulary + deck/file names for now.
3. **Switch roles → switch deals.** A deal earns coaching per seat, on that seat's own
   merits. Bias to drop.
4. **Select-then-grade.** Scenario selection gets the role cheaply; one double-dummy
   solve read three ways finds the actual decision and drops the flat hands.
5. **Use LHO/RHO directly** in student-facing prose, beginners included (David's call,
   2026-06-25 — happy with LHO/RHO now). The terminology *fade* (Leader → Left Hand
   Opponent (LHO) → LHO) is possible but **not** required — add it only if Rick judges
   beginners need the gentler ramp. Prose only either way; the `[ROLE]` markers are
   untouched regardless.

## Where we stand (verified 2026-06-25)

- 12 play sets, 349 boards, **100% declarer.** `[ROLE defender]` count = 0; no E/W
  declarer on any curated play board. Opening-lead and defender decks do not exist —
  the `[ROLE leader]` markers are the opponents' auto-played opening lead, not the
  student leading.
- ~13 boards put the student in the dummy seat (partner declares) — a defect the grade
  should catch and drop.
- Corpus: `bba/` has 345 scenarios / 171,446 deals. N/S declares 80%, defends 20%.

## Sources (no new generation needed for defense)

**Rotation is the key.** A 90°/270° spin swaps the N/S↔E/W axis, seating the student in a
defender's chair. So the ENTIRE library — not just deals where the opponents already
declare — becomes a defender/lead source. (Rotate dealer + vulnerability tags too; the
4-player rotate tooling already does this.) Three streams:

- **Defending CONSTRUCTIVE auctions (rotate the whole library)** → take any of the ~137k
  N/S-declares deals and rotate 90°; the student defends a normal auction (Stayman 3NT,
  Jacoby game, slam). Largest, most realistic defensive pool.
- **Defending COMPETITIVE auctions (no rotation)** → the 49 defense-heavy scenarios where
  N/S already defends (Lead_Directing_Double, Responsive_Double, the overcall/double
  families). Advanced — not for beginners.
- **BEGINNER defense = rotate beginner-level CONSTRUCTIVE scenarios**, selected by bidding
  *content/level*, NOT the "Basic" filename. The beginner then defends the very auctions he
  just learned to bid — no new bidding concept. The pool is far larger than the `Basic_*`
  family: e.g. Major_Opener (79% declares), Major_Suit_Fit (89%), Minor_Suit_Opener,
  alongside Basic_NT/Major/Minor. **Basic_NT rotated is the prime opening-lead source**
  (lead/defense vs 1NT–3NT, the canonical beginner lead lesson), richest because it was
  ~97% declarer and thus useless as defense until rotated. Criterion = *constructive AND
  uses only bidding the student knows.* EXCLUDE for true beginners: competitive auctions
  (Basic_Overcall/Takeout — a takeout double is itself a concept) and convention-laden
  constructive ones (Jacoby_2N, Bergen, Splinters, Gavin_*) until the student has met that
  convention.

- **Declarer decks** → as today (no rotation).
- **Auction-independent technique lessons** → purpose-built `.btn` (full deal + pinned
  spot cards). Later.

**Selection (all rotated sources).** Rotation multiplies SEATS, not LESSONS — the
defenders' hands and spot cards were unconstrained, so most rotated hands are flat. The
per-seat grade gates; bias to drop. The grade's difficulty score is a **band-pass, not a
sort key**: beginner decks take the LOW band, advanced decks the HIGH band. So for a
beginner the grade does two jobs — clears the "is there a decision worth teaching" bar AND
**caps difficulty so the hand stays simple**: a clear rule-based action (textbook lead —
top of a sequence, fourth-best, partner's suit; an obvious defensive plan), normal shape
(no freaks), one teaching point, no advanced technique (no required count, trump promotion,
endplay, squeeze). Advanced decks want the opposite end — the hard hands are the good ones.

## Packaging

Up to three files per **theme** (at a difficulty level), one per **seat**
(LHO/RHO/Declarer), pre-rotated, single track each — **theme-based, NOT
scenario-based**: a deal is *pulled* from a scenario, but the deck is keyed to its
teaching theme + level, never to one scenario. All
content-side; reuses the existing pipeline. (The "one file, three grades + three tracks"
data model is prettier but deferred — it needs present-time rotation + track selection in
the engine.)

## Coaching modes

- **Full coaching** — author prose → gate → promote.
- **Un-coached play** — engine toggle: play a curated deal with prose off. For defense the
  engine must play the other seats adaptively and score against double-dummy par. (Engine
  work, Rick's side; small.)
- **Difficulty ladder** — cold → reveal coaching → graduate to no coaching.

## Shortest path

1. Build the per-seat play grade (DD-based; pass/fail + difficulty). Also flags the
   dummy-defect boards.
2. Pilot one **beginner opening-lead (LHO) deck by rotating Basic_NT** (lead/defense vs
   1NT–3NT): select → grade → author.
3. Add one **defender deck** from a defense-heavy scenario.
4. Enable **un-coached play** so every curated deal is also playable cold.

## Open decisions

- Beginner vs. advanced split for the new decks.
- Whether to keep a rare "same deal, three chairs" multi-perspective format.
- Role-file naming: `Scenario_Declarer` / `Scenario_LHO` / `Scenario_RHO` (underscores
  only — hyphens break the BBO/classroom regex).
- *(Resolved)* Terminology: LHO/RHO used directly, beginners included; fade deferred unless Rick wants it.

---

## 2026-06-25 — Defense build plan (design-session decisions)

**Scope.** Three "Basic" **DEFENSE** sets — **NT, Major, Minor** — 30 deals each,
student = South **defends**. The defending mirror of the `Basic_*` (declaring)
family.

**Lesson identity — THEME-based + LEVEL-based + ROLE-based, NOT scenario-based.**
Bidding lessons ≡ scenario names (1:1 with a `.btn`). Play lessons are the
opposite: each is a **theme** (Leads, Signals, Trump threats, Counting,
Inferences, …) at a **difficulty level** (beginner / intermediate / advanced),
for one **role/seat** (LHO / RHO / Declarer — see Seat axis), curated from
**many** scenarios. The level sets the **bidding complexity** — a *beginner* deck
pulls deals with beginner-level (natural, no-convention) bidding. A deal is
*pulled* from a scenario, but the deck is keyed to its theme + level + role,
**never to one scenario** — decoupled from `-PBS.txt`; each deal carries source
**provenance** (`[OriginalSource …]`). So source from *any* scenario whose
bidding fits the level, then select by theme.

**Seat axis.** Play lessons span three student seats: **LHO** (lead + defense),
**RHO** (third-hand defense), **Declarer**. Dummy has no decisions → no deck.
Taxonomy: **theme × difficulty-level × role/seat** (LHO/RHO/Declarer; contract type — NT/Major/Minor — is
context within a theme); seat goes in the filename
(`Scenario_LHO`/`_RHO`/`_Declarer`). Engine asymmetry: **LHO** needs a new
*graded-lead* anchor (the student leads); **RHO** rides the existing
`[ROLE leader]` auto-play (partner leads), then plays third-hand.

**Contract level (game vs partscore — distinct from the *difficulty* level
above).** *Not* a deck axis — the core job (count declarer's tricks, set up +
cash yours, try to set it) is the same whether they're in game or a partscore, so
a deck can mix 1N/2N/3N. (The MP partscore-overtrick nuance — passive vs a
partscore, all-out vs a game — is advanced, deferred.)

**Folders (target, from-scratch).** `bid/` and `play/`, **both non-rotated**. The
current `coaching-curated → coaching → coaching-non-rotated` chain exists *only*
to feed the Play Trainer's **runtime** rotation (what the `@`-tokens serve); with
Bridge Classroom (a non-rotated dumb renderer) as the home, that dimension
collapses. Defense lives in `play/` (all seats), **not** a defense-specific
folder. `play/` is greenfield → adopt the clean model now; existing **bid**
lessons migrate later, on Rick's timeline. **Interim (now, per David):** leave the
existing **bid** lessons — and the existing declarer-play lessons — in
`coaching-non-rotated/`, untouched; only the **new** play/defense content goes in
the new `play/` folder. The `bid/` folder and the migration are deferred.

**Fork shortcut (David's idea).** To run the fork in the *target* `bid/` + `play/`
shape *now* without waiting on migration, **mirror** `coaching-non-rotated/` into
the fork's folders — bidding lessons → `bid/`, the existing declarer-play sets →
`play/` (joining the new defense). Make it a **regeneratable copy** (gitignored;
re-run a one-line copy whenever `coaching-non-rotated/` changes), so the single
source of truth stays `coaching-non-rotated/` and the two never drift. Rick's
production still reads `coaching-non-rotated/`, untouched. The fork then runs
exactly like the eventual merged Classroom.

**Anchors / fade.** No `@`-tokens (rotation-only; these sets are pre-rotated /
fixed-South — write 2nd person). Reuse the `⟦ ⟧` fade (verbose-on-wrong,
nod-on-right, partner always shown). **Missing:** a graded opening-**lead** anchor
(the lead counterpart of `[BID]`/`[ACCEPT]`). Defender `[PLAY]` parked.

**Don't break Rick's live BC.** Classroom reads the **existing** layout off raw
GitHub main. All changes **additive + backward-compatible**; nothing reaches BC
until commit + push (and no breaking pushes).

**Build strategy — David's BC fork.** Build the **whole vertical** — PBS content
*plus* the BC engine work (defender seating, reveals, graded-lead anchor,
defender `[PLAY]`) — in **David's fork** of Bridge Classroom. Rick's production
stays untouched **and** we stop waiting on his parser. **Downside-resilient:** the
PBS content is renderer-agnostic and survives even if Rick passes; the
proof+design de-risk his version; only the fork engine code is throwaway. Then
offer Rick a working, tested merge.

**Status.** Pilot board drafted: `Basic_NT` b13 rotated → an **NT-LHO** lesson in
`coaching-curated/Basic_NT_Defense.pbn` (mis-homed — moves to `play/`). ⚠️ BC
handling defense deals is **unverified** — test one deal in a local BC run before
assuming it renders (every BC lesson so far has the student on the *declaring*
side).

**Play selection (menu).** BC's "Pick a Scenario" is built from
`btn/-button-layout-release.txt` (`[Section]` + rows of **scenario** names →
load a `.btn`). Theme-named play lessons have no `.btn`, so they can't be buttons
there. Fix: a **parallel play menu** — a play-layout file (the play counterpart
of `-button-layout`, *same* `[Section]`/rows format, **seat-aware**: e.g.
`[Section] Notrump Defense` → `Basic_NT_LHO`, `Basic_NT_RHO`) read by a **play
picker** in the fork ("Pick a Play Lesson" / a Play tab) that loads from `play/`.
Reuses BC's existing menu renderer (new bits = which file it reads + a click that
loads a play lesson, not a scenario). Additive — Rick's scenario selector
untouched. The 12 existing declarer-play sets are currently scenario-buttons in
`-button-layout`; in the fork-mirror world they graduate into the play menu with
the defense (leave them in both for now, move at cutover).

**Open.** Folder name; split "Basic NT Defense" into `_LHO`/`_RHO`; the
provenance tag; the graded-lead anchor shape; play-menu layout-file location/name;
heads-up note to Rick (drafted).

---

## 2026-06-26 — Opening-lead answer key, grading, and the auction-context decks (build spec)

**Status going in:** `Basic_NT_Defense_LHO` (30 boards, opp opened 1NT, student=South
on lead) is built + verified rendering/grading in the BC fork using the binary
`[choose-card]` primitive (zero fork code). This spec covers (a) a better, three-tier
answer key and (b) three new auction-context decks David asked for.

### Scope — four LHO opening-lead decks vs an NT contract (student = South, on lead)

The deal is rotated so **declarer = East** (South is then the opening leader). Decks by
how the opponents reached NT:
1. **after opp's 1NT** — built (`Basic_NT_Defense_LHO`).
2. **after opp's suit opening** — opp opens a suit (we silent) → NT.
3. **after we opened** — *our* side (the defenders) opened/acted first; opp still buys NT.
4. **after a competitive auction** — both sides bid; opp declares NT.
Detect the category from the rotated auction (first non-pass seat; did N/S bid). Corpus
availability (rotated, South-on-lead, NT contract): ~6k / 12k / 4k / 17k respectively —
not pool-limited.

### The answer key (resolved) — principle grades, SD only breaks ties

The "correct" card is the **principled lead**, and grading is **three-tier**:
- **correct (atta-boy)** = the principled card (top of sequence / fourth-best / partner's
  real suit). "Yes! / Well done."
- **reasonable** = right *suit* or right *idea* but imperfect card (another honor in a
  sequence → "lead the top"; a low card in the right suit; a genuinely defensible
  alternative). "I understand your thinking, but…"
- **wrong** = principle-violating (off-suit abandoning your long suit, a doubleton,
  leading into their bid suit). Explain why.

**Grade the tiers by PRINCIPLE, not by SD result-insensitivity.** A scan of 217 Basic_NT
candidates showed a pure "drop boards where no lead is double-dummy worse" rule cuts **60%
(131/217) — including the verified pilot #13** — because on most 3NT deals declarer makes
regardless of the lead. Result-insensitive ≠ no teaching value. (See
[[feedback_teach_good_leads_not_results]].)

**Single-dummy (SD) is used surgically, two places only:**
1. as the **tiebreaker** on the genuine judgment boards (decks 3–4: partner's suit vs your
   own), where principle alone can't pick the suit;
2. as a **QA spot-check** on principle-vs-SD suit disagreements (46/217 in the scan — some
   judgment, some classifier bugs to fix).
Not used to score the whole pool (too slow — see compute below) and never as the primary
key (it's result-based; conflicts with teaching technique).

### The lead principle (incl. David's auction-aware refinements)

vs NT, attack your longest/strongest suit; exact card = top of sequence / broken sequence /
fourth-best. For decks 3–4 the auction adds:
- **Is partner's suit *real*?** Overcall or a major opening = real → lead it. **1♣/1♦
  opening is often not a real suit** (balanced / short) → don't default to it.
- **Position.** NT bidder *behind* partner's suit (bid NT after partner) = stopper sits
  over partner → **less appealing**; partner *over* the NT bidder = **more** appealing.
  Read it from auction order.
- **Your own holding** (a sequence / long suit) competes with partner's suit.
- **The right lead is NOT always partner's suit** — that judgment *is* the lesson. Include
  boards where the answer is your own suit; the "reasonable" tier carries the trade-off.

### SD method + bidding-style knob

Monte-Carlo single-dummy: hold South's 13 cards, deal the hidden 39 many times **consistent
with the auction's implied point ranges**, double-dummy-solve each, average each candidate
lead's defensive tricks → a 0-100 score per card. (Standard MC-with-DD-per-layout; defenders
play DD after the lead, so absolute counts run slightly optimistic but the *ranking* is
robust.) SD picks the **suit**; principle picks the **card** (touching honors tie in DD).
- The point-ranges are a **bidding-style parameter** (conservative ↔ less conservative), and
  depend on the **auction type**, not a fixed 1NT=15-17. Default a notch **lighter than
  textbook** — that's how the robot and real opponents bid. Lighter declaring → defense
  should attack more → SD-best lead shifts aggressive. (Bidding soundness is itself a
  teachable "read the auction" variable.)
- **Coherence:** the SD style must match the style the board's auction was bid in (these
  deals: EPBot 2/1 GF, fairly sound). For genuinely less-conservative auctions, widen the
  source scenarios rather than just loosening the SD assumption.

### Feedback prose = generated per board AND per card

The tier+reason structure is the feedback generator. For the card the student actually
leads, the text is a function of its relationship to the correct lead: correct → atta-boy +
principle; same suit/other honor → "right suit, lead the top"; defensible off-suit → "fair
alternative, but your long suit develops more"; clearly wrong → "that abandons your best
tricks." Auto-generates a strong **first draft** (David's voice on top); flag, don't fake,
where the "why" can't be stated ([[feedback_intuition_axis_hard_to_discern]]).

**Result-aware affirmation (David, 2026-06-26) — the correct lead is correct even
when it loses.** Split the atta-boy by what actually happened on *this* deal: DD-solve
the **actual** layout for the principled card. If it beat the contract → *"Yes! — and
it set them."* If it didn't → *"That's the lead I'd have made too; it just didn't work
this time — the cards lay badly / declarer had it. Right lead, wrong day."* This is the
ONE place we touch the real result, and only to PHRASE the outcome honestly — never to
grade the lead (principle does that). Mirror case: a *wrong* lead that happens to come
in gets *"that worked this time, but it's not the percentage lead"* — never reward luck.

**Composition: deliberately seed a FEW "right lead, wrong day" boards (David,
2026-06-26).** A deck where the correct lead always triumphs quietly teaches
result=correctness — the opposite of the point. So intentionally include a handful
(~3-5 of 30) where, DD on the actual layout, even the principled card can't set the
contract (cheap single DD solve per board flags them; the pilot #13 already is one).
Keep the majority right-lead-works so success is the norm and the honest losses land as
the exception that proves the rule. Tag each board `right_lead_sets` during selection.

### Lead variety needed (David, 2026-06-26)

v1 covers only THREE lead types — solid 3-card sequence, broken sequence, fourth-best —
and is honor-heavy (18/30 lead an honor). `defense_lead_select.classify_lead` *drops* the
other real NT-lead situations, which is why variety is thin. Promote them to proper tiers
(each with its own principled card + prose), don't drop:
- **Interior sequence** — AJT, KJT, AQJ, QT9 → lead the top of the interior run (the J
  from AJTxx, the T from QT9xx). Currently killed by the interior-seq guard; make it a type.
- **Top of nothing** — longest suit has no honor → lead high to deny an honor (or a passive
  card). Currently dropped because fourth-best requires an honor.
- **Two-card sequence / honor doubleton** at the head of the long suit.
- **Passive lead vs a strong auction / slam** — include a few **6NT** boards (Basic_NT has
  ~18): vs a notrump slam you lead passively and don't give a trick. A distinct decision.
- (partner's suit / lead-through-dummy belong to the auction-context decks.)
Also vary the ORDER — not ten sequence boards in a row. Variety needs the larger pool +
these added types, not the current strict-drop classifier.

**Lead-type canon, sorted by SEAT (David, 2026-06-26).** Keep each principle on the deck
where it actually applies, or we mis-teach it.
- **NT opening leads (LHO deck):** (1) top of a solid sequence (KQJ/QJT/JT9), (2) top of a
  broken sequence (KQT/QJ9), (3) top of an interior sequence (AJT/KJT/AQJ/QT9 → the top of
  the touching run), (4) fourth-best, (5) top of nothing (no honor → high spot to deny one),
  (6) partner's real suit (card by holding), (7) passive vs a slam/strong auction,
  (8) lead-directing-double's suit (competitive deck).
- **Suit-contract opening leads (Major/Minor defense decks, NOT this one):** singleton for a
  ruff, trump lead to cut ruffs, top of a doubleton, K-from-AK, don't underlead an ace.
- **Later-trick / 3rd-hand principles (RHO / defense-play decks, NOT opening leads):**
  **"lead through strength, up to weakness"**, return partner's suit, third hand high, cover
  an honor with an honor, second hand low. These need the dummy in view — they are NOT
  trick-1 leads; the auction only hints. Map to the RHO/defense seat.

### Include hands without a clear-cut lead (David, 2026-06-26)

A deck of only obvious leads teaches recognition, not judgment — and choosing when nothing
is clear is the real skill. So composition gets a third deliberate quota (alongside the few
"right lead, wrong day" boards): **a meaningful minority of no-clear-cut-lead hands** —
competing suits, no sequence, your-suit-vs-partner's, attack-vs-passive.

**Critical distinction (don't confuse these):**
- **No clear-cut lead** = several *plausible* leads cluster near the top, but inferior leads
  still lose — a real choice *with stakes*. → **KEEP.** This is where "reasonable" + the SD
  tiebreak live.
- **Lead doesn't matter** (board 24) = even bad leads score the same; contract's fate fixed.
  → **DROP.**
The "no wrong tier → drop" rule already separates them: a judgment board still has *wrong*
leads to catch; that's what makes it gradable.

**Grading a judgment board:** top cluster = reasonable (the genuine choice); the SD/principle
favorite = atta-boy — or on a true coin-flip, accept several (no single winner) and let the
feedback say so ("close one — ♦ or ♥ both fine; I'd lean ♦ because…"); inferior = wrong.
The feedback teaches the trade-off, which is the lesson.

### Feedback verbosity — fade by tier (David, 2026-06-26)

Response length scales INVERSELY with correctness (the lead counterpart of the bidding `⟦⟧`
fade, but three levels):
- **correct → terse.** A short nod only ("♠Q — yes"); don't re-explain what they got right.
- **reasonable → pros/cons.** The trade-off for the card they actually chose: why it's
  defensible AND why the atta-boy edges it. The SD comparison supplies the substance (their
  lead's score vs the best); principle frames it.
- **wrong → full.** The complete explanation: the right lead and why theirs misses.
Fork-render behavior (the engine picks verbosity from the grade); the content provides all
three levels per board/card. Extends today's binary `⟦⟧` fade (nod / full) with the middle
pros/cons rung.

### Deck program — the full defense curriculum (David, 2026-06-26)

David is enumerating the whole vertical. Two student SEATS, several LHO contexts:

**LHO — opening leads** (student on lead; deal rotated so declarer = East):
- **vs NT** (opp opened 1NT) — **BUILT**, 5 lead types, verified in fork.
- **vs a Major** (after a major raise 1M-2M/3M/4M) — scouted (`Basic_Major`, 102 candidates; suit-contract leads).
- **vs a Minor** (after a minor auction) — to build.
- **after WE opened** — to build (auction-read).
- **after a COMPETITIVE auction** — scouted (~93k boards, 71k suit / 22k NT; partner bid a suit 53%, doubled 6% → **auction-dominated**: lead partner's suit / the doubled suit).
- (after a plain suit opening — to build.)

**RHO — third-hand play** (partner leads — the existing `[ROLE leader]` auto-play fits — dummy
shown, student plays third):
- canon: third hand high; cover an honor (with the *lower* of touching honors to finesse dummy);
  return partner's suit; unblock. NEW seat. "Hands suitable for third-hand play" = boards where
  third hand has a real decision.
- ENGINE: likely a `[choose-card]` at the third seat (partner-lead auto-played + dummy revealed,
  then student plays). CONFIRM the fork renders RHO play before scaling.

**Shared foundations — build once, apply across decks:**
- Lead canon: NT done; the **SUIT/COMPETITIVE canon = (A) David's priority call** — OPEN, and now
  gating Major + Minor + competitive + we-opened.
- **(B) Auction-reading classifier** (mine to build): parse the auction → partner's bid suit /
  lead-directing double → apply real-suit (overcall/major = real; 1♣/1♦ ≠ real) + position. The
  dominant lead on competitive / we-opened.
- Third-hand: **(C) the third-hand-play canon = David's call** — OPEN; plus a 3rd-hand selector.

**Two gating inputs from David:** (A) suit/competitive lead priorities; (C) third-hand priorities.
Everything else is tooling. **Build order:** lock (A)+(C) → build (B) + 3rd-hand selector + confirm
RHO render → mass-generate decks → SD-grade + David voice-pass → verify in fork → stage (no push
without David). Don't let the deck list sprawl ahead of the canons.

### Larger pool

Source **cross-corpus** (all `bba/` scenarios), not just Basic_NT, with a **natural-auction
filter** (exclude convention scenarios — Spiral_Raises, Lebensohl, NT_Splinter,
Minor_Suit_Stayman, GIB_*…). Dedup. Principle-grade the bulk cheaply; **bias to drop**.

### Compute reality

SD is ~2 s/board (the 217-board scan took 8 min at K=80, dominated by rejection sampling).
A multi-thousand pool can't be fully SD-scored — which is *why* SD is surgical: principle
grades everything for free; SD runs only on the judgment boards + the QA disagreements.

### Fork engine work (these decks are NOT zero-fork, unlike the 1NT deck)

The three-tier, per-card responsive feedback needs a fork change — today's `[choose-card]`
is binary (right/wrong only). Needs a marker/format carrying correct + reasonable[] +
per-tier text, and the renderer to show it. Build in David's BC fork. The existing
opp-1NT deck stays on the binary primitive (already shipped-ready).

### Tooling

- `py/defense_lead_select.py` — rotate-to-East + principled opening-lead classifier
  (sequence / broken / fourth-best; drops ace-headed seqs, AK-4th, interior seqs,
  voids/7+); `--emit` writes a balanced deck. Sources Basic_NT today.
- `py/sd_lead.py` — SD Monte-Carlo scorer + three-tier grader (`grade()` floors same-suit
  at "reasonable"; `droppable()` = no-wrong-tier) + `--pool` scan. Run with `python3 -P`
  (append-to-path trick avoids the stdlib `select` shadow).

### Next (in order)

1. Generalize sourcing to the cross-corpus natural-auction pool + dedup.
2. Per-auction SD point-ranges + the bidding-style knob; partner's-suit "real + position"
   logic in the principled classifier for decks 3–4.
3. Fix/triage the 46 principle-vs-SD disagreements.
4. Three-tier marker contract + fork renderer; per-card feedback generator.
5. Generate decks 2–4; David voice-pass; verify in fork; stage (don't push without David).

---

## FROSTING — mixed 16-board "graduation round" (David, 2026-06-26; do AFTER the themed decks)

A capstone practice set for once a student has the basic lessons. **Deferred** — "frosting, for
when the cake is done."

- **16 boards**, standard **duplicate rotation**: dealer N-E-S-W by board number, and the standard
  16-board **vulnerability** cycle (1 None, 2 NS, 3 EW, 4 Both, 5 NS, 6 EW, 7 Both, 8 None, 9 EW,
  10 Both, 11 None, 12 NS, 13 Both, 14 None, 15 NS, 16 EW — verify when building).
- Student is **always the actor** (fixed South = whoever has the action), but the **lesson type is a
  random mix** — bid / opening lead / third-hand / declarer — and the student is *not told which*.
  Recognising the situation is the whole point.
- **Construction rule: select, don't stamp, don't pad.** Vulnerability is meaningful (BBA bids by
  vul), so it must stay consistent with the shown auction. And a Pass *denies an opening hand* — you
  can't pad passes to reseat the dealer (a passed hand can't then bid strongly; that auction does
  not exist). So dealer AND vul come from **real boards** that already match the slot. Build = an
  **assignment problem**: each of 16 slots wants (dealer, vul, lesson-type); fill from the 80k pool
  with a board whose genuine rotated dealer+vul match. Nothing faked — auction, dealer, vul, and
  answer all stay exactly as BBA dealt/bid them.
- **Vul becomes a live exam variable** — the same competitive decision red vs white, which a themed
  single-colour deck can't probe.
- **Mostly assemblable from the existing decks, ~no new engine** — per-board markers (`[BID]` →
  bidding box, `[choose-card]` → card prompt) already drive the right widget per board.
- OPEN: the mix (how many of each type); **fixed vetted exam vs endless generator** (fixed =
  reviewable/reportable; generator = endless, regenerates each session). Build check: run a board
  through BBA at both vuls to confirm the auction actually moves (how hard the vul constraint bites).

---

## COMPLETE PROGRAM MATRIX (David, 2026-06-26) — three seats

The full play-coaching program now spans all three playable seats. **Asymmetric by design**
(David's call "a"): the **defender seats are cut by contract-context**, the **declarer seat by
technique** (because declarer skills span contracts — a finesse or top-tricks board occurs in NT,
hearts, or spades alike). Declarer reuses the existing 12 decks as-is (per-trick prose, already in
the "Play of the Hand" toc categories); LHO/RHO are the new single-`[choose-card]` decks built this
session.

**DECLARER (existing 12, technique-themed):**
- NT-leaning: `Play_Top_Tricks_NT`, `Hold_Up_3N`, `Choice_Of_Finesses`
- Suit-leaning: `Play_Top_Tricks_Suit`, `Play_Top_Tricks`, `Rabbis_Rule`, `Side_Suit_Ruff_Before_Trump`,
  `Endplay_3rd_Round_Strip`
- Technique-spanning (NT + suit boards): `Finesse_Simple`, `Two_Way_Finesse`,
  `To_Finesse_Or_Not_To_Finesse`, `Suit_Promotion`

**LHO — opening leads (new, by context, 30 each):** `Basic_NT_Defense_LHO`,
`Basic_Major_Defense_LHO`, `Basic_Minor_Defense_LHO`, `Competitive_Defense_LHO`

**RHO — third-hand (new, by context):** `Basic_NT_Defense_RHO` (30), `Basic_Major_Defense_RHO` (30),
`Basic_Minor_Defense_RHO` (23 — pool limit), `Competitive_Defense_RHO` (30)

All LHO/RHO decks staged (coaching-curated), **unpushed**. Declarer decks already live. Remaining
beyond the matrix (optional): LHO suit-opening→3NT, LHO we-opened, RHO cover-an-honor tier; and the
declarer-in-single-decision-quiz-format road (option "b") if ever wanted.
