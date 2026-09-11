# Plan: curating + coaching conventions BBA doesn't bid

**Status:** proposed 2026-06-14. First instance: `Spiral_Raises_Wolpert`.
Extends the `curate` stage (see [pbn-curation-plan.md](pbn-curation-plan.md)) to
scenarios whose teaching auction BBA cannot produce.

## Problem

Every coached scenario so far teaches a situation BBA bids natively (1NT openings,
weak twos, takeout doubles). For those, BBA's auction in `bba/<scn>.pbn` **is** the
teaching auction, and the trainer uses the PBN `[Auction]` as its quiz answer key.

`Spiral_Raises_Wolpert` is the first scenario that teaches a **convention BBA does
not play.** The deals are constructed (via Dealer constraints) so the spiral-raise
decision arises, but BBA bids them with `21GF-DEFAULT`, which has no Spiral Raises —
so its auctions are natural 2/1 (`1C 1H 1N 2N`, `1D 1S 2S P`, …) and the spiral
ask/answer ladder never appears. Coaching the convention against those auctions
would be inconsistent: the prose would teach the spiral while the answer key
expected BBA's natural call.

This generalizes: any relay or convention continuation BBA's convention cards don't
know (the other Spiral variants, Bergen, Jacoby 2NT continuations, …) hits the same
wall.

## Approach: generate the convention auction, substitute it in

For these scenarios the teaching auction is **authored deterministically from the
hands**, then substituted into the curated pool so the rest of the pipeline (and the
trainer) treat it as the answer key.

Key facts that make this safe (traced in the code):

- `annotate.py` copies `bba/`'s `[Auction]` verbatim into `bba-curated/<scn>.pbn`,
  adding only a `{Curate}` comment block; `coach.py packets`/`splice` carry the
  auction through unchanged. **Nothing downstream re-derives or cross-checks the
  auction against `bba/`.** So rewriting `[Auction]` in `bba-curated/` is sufficient.
- `deal_hash` hashes only `[Deal]`, so a sidecar keyed by `deal_hash` joins cleanly
  across every step even after auctions are rewritten.
- A generated auction round-trips through `endplay.parsers.pbn` — the exact loader
  the trainer uses — so "endplay parses it" ≡ "the trainer can load it."

### New code

`py/spiral_auction.py` (the convention engine for this scenario). Per board:

- read N/S hands (`curate.hands()`); reuse BBA's natural opening + 1-level response
  (the first two N/S calls);
- classify opener's decision — 4-card raise / suitable 3-card raise (a ruffing
  value) / unsuitable decline — using the `.btn`'s own "unguarded shortness" rule;
- on raises, classify South's hand to exactly one rung of the spiral ladder and
  render the coded answer (one **parameterized** renderer covers all four
  opening×major cases — not four hand-typed tables);
- apply responder placement (combined 23-27 → mostly game-zone; fit + values → 4M,
  balanced 5-3 → 3NT, both-minimum → sign-off);
- emit a legal ascending auction and **self-verify** that South maps to exactly one
  rung (independent per-rung predicates flag any board matching ≠1 rung — this is
  the spec-gap detector);
- compute `calc_dd_table` makeability of the placed contract (reuse `curate.dd()`);
- write a `deal_hash`-keyed sidecar + a `--report`, and a `--substitute` mode that
  surgically rewrites only the `[Auction]…calls` block (and
  `[Contract]/[Declarer]/[Result]/[Score]`) in `bba-curated/<scn>.pbn`, leaving the
  `{Curate}`/`{Shape}`/`{HCP}`/`{Losers}` blocks intact. Decline boards keep BBA's
  natural auction (it is already correct).

DD only **tiers** the result (makes → textbook; borderline → judgment + `also-ok`);
it never picks the bid, per the curation plan's "DD for soundness, never pedagogy."

### Where it plugs into the pipeline

```
btn → dlr → pbn → rotate → bba → annotate ──▶ [spiral_auction --substitute] ──▶ select → coach → promote
                                   (natural auction)      (convention auction)
```

`curate.py` (Layer A features) and a Layer-B grading subagent run as usual, except
the grader is fed the **spiral** sidecar auctions (grade-only — it never re-proposes
calls). The substitution runs *after* `annotate.py`, because `annotate` rebuilds
`bba-curated/` from `bba/` (the natural auction).

## The convention (Spiral_Raises_Wolpert)

Opener (South) opens a minor and may raise responder's (North's) major to 2M on 3-
or 4-card support; responder asks with the cheapest step, and opener "spirals" out
support length, strength, and shortness. The `.btn` `/*@chat */` gives the full
answer ladder verbatim for the `1♦-1♥-2♥`/`2♠`-ask case; the 1♠-response cases
("shift up one step") and 1♣ openings ("minors swapped") are derived by rule.

**Open item — Gate 1 (before authoring):** the derived 1♠-response ladder puts coded
meanings on the trump suit (3♠) and 3NT and pushes the 3-card-balanced hands high;
this and the min/max HCP cutoff within 12-14 are being confirmed against a per-rung
distribution report before any coaching prose is written.

## Coaching + the practice table

Coaching is authored rotation-compatible (`@S`/`@v(base|third)` tokens) so it renders
for a single user in the bottom seat, a pair in both seats, or random-rotate. The
voice is a warm at-the-table partner walking through each call's meaning by
agreement (which is exactly what coded answers are).

**Selector location.** Runtime, user-facing selection (pick tier / difficulty /
sub-drill — raise-decision vs ladder vs placement) belongs in the **practice table**,
filtering the served pool on its `{Curate}` metadata. PBS emits the curated+coached
pool with that metadata retained; build-time `select.py` stays an authoring/QA tool.
This build is made forward-compatible (metadata retained, sub-drills tagged); it does
not build the table selector itself.

## Lesson scope

The three-way contrast is the lesson (coaching only spiral boards would train
"always raise on 3"): a 30-board default of 12 spiral boards spanning the ladder +
6 four-card raises + 8 unsuitable declines + 4 judgment/buffer.
