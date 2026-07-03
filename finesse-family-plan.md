# Finesse-family lesson plan

Design + working plan for reworking the **declarer-play finesse lessons** as a
coherent family. Started 2026-07-03 (David + Claude). Companion to
[pbn-curation-plan.md](pbn-curation-plan.md) (the curation pipeline) and
[Bridge Play Trainer.md](Bridge%20Play%20Trainer.md).

**Status:** design settled; method unproven (see "Method — TO BE VALIDATED").
First concrete change already shipped: Finesse_Simple board 1 re-curated to a
single winning make-or-break finesse (commit `7888e8565`).

---

## 1. The five-lesson family — who owns what

These are all `[ROLE declarer]` play lessons (student = South = declarer).

| Lesson | Owns the skill | Shape | curate kind |
|---|---|---|---|
| **Finesse_Simple** | Take a single finesse — the mechanic (lead toward the honor) | one suit, it's the way | soundness |
| **Two_Way_Finesse** | *Which direction* — finesse either opponent for the queen, resolved by the count/bidding | one suit, a guess | avoidance |
| **Choice_Of_Finesses** | *Which of several* + **combine chances** + order (entries / danger hand) | multi-suit | avoidance |
| **To_Finesse_Or_Not** | *Whether at all* — vs. a safe line; restraint + evidence | one decision | avoidance |
| **Rabbi's_Rule** | Finesse vs. the **drop** — play the ace for the stiff honor, *with a reason* | odds / safety | byforce |

**Boundary guards (to prevent overlap):**
- **Choice stays multi-suit / combining.** Single-suit direction-guessing belongs to Two_Way.
- **To_Finesse_Or_Not's alternative is a *non-drop* safe line** (establish a suit, duck for a
  certain trick, or count that you don't need the finesse). Finesse-vs-drop is Rabbi's turf —
  if To_Finesse leans on the drop it *becomes* Rabbi's Rule.
- **Avoidance (danger/safe hand) is a cross-cutting reason, not its own lesson.** It currently has
  no home of its own; it's folded into Choice as "the reason the order is forced." (Open question
  whether it eventually deserves a standalone lesson.)

---

## 2. The declarer's decision framework (the teaching backbone)

When declarer has a finesse decision, the reasoning runs in this order. Each stage is a natural
cluster of boards.

1. **Count first.** How many tricks, and how many finesses must actually work? Decides whether
   you're *combining* (need one of two) or *picking the best single one*, and whether you can
   afford to lose a finesse at all.
2. **Is it already *known*?** — **inference from the bidding.** An opponent who opened/overcalled
   holds the missing honors (finesse *through* them); a passed hand is capped (a shown-up honor
   *places* the rest); a preempt/long-suit bid marks shape → vacant spaces shift the odds; silence
   is a negative inference. Often converts a 50-50 into a certainty.
3. **Can I *discover* it?** — **inference from the play / gaining information.** Play your *other*
   suits first and **count** — who follows, who shows out — until the finesse suit is placed (often
   pick it up by **drop** instead). Test a suit on purpose (discovery play); cash the top of the
   finesse suit first (free stiff-honor chance + a look); strip toward an endplay. Prefer *free*
   discovery (winners you'd cash anyway, ordered to reveal count) to *paid* discovery.
4. **Still a mystery? Combine chances.** Take the finesse whose *loss still leaves the other* as a
   fallback — 50% → ~75%. Order is forced by **entries** (keep a route back), the **danger hand**
   (take the finesse that loses to the *safe* hand first), and **free chances first** (drop-then-finesse).
5. **Can only take one? Best odds.** Two-way guesses resolved by counting the hand; finesse-vs-drop
   ("8 ever, 9 never"); the line that also gains from a friendly break.
6. **Timing — *when* to commit.** As **late as you safely can**: the latest point at which you can
   still take the finesse *and* survive its loss. Cash the sure tricks and gather the count first;
   the deadline is set by **entries** (a route about to vanish) and **control/tempo** (must act while
   you still hold a stopper).

Through-line: **count first, guess last.** A finesse is a last resort; combining is the safety net
under it.

---

## 3. Per-lesson concept + difficulty arc

**Choice_Of_Finesses** (rebuild target). Spine = *count → known? → discover → combine → best odds*.
- Open: two plain finesses, take both (either order makes) — "you have two chances, use both."
- Middle: order forced by **entries** (must take one first to keep the route to the other).
- Harder: order forced by the **danger hand** (take the safe-loss finesse first — avoidance re-enters).
- Judgment: combining vs. a single better-odds finesse; or cash-for-the-drop-then-finesse.
- Default scope: mostly 3NT, a couple competitive auctions (to *place* an honor), tight ~10-board arc.

**To_Finesse_Or_Not** (build target). *Whether* at all; the finesse is a gamble that costs the hand.
- Flavor #1 — **decline the unnecessary finesse** (count; a safe line already makes; don't be greedy).
- Flavor #2 — **demand evidence before risking a needed one** (bidding/lead/count must support it).
- Signature board: *a safe line makes AND a tempting finesse loses* — the disciplined student makes,
  the greedy one goes down. (Alternative must be non-drop — see boundary guard.)
- **OPEN:** which flavor to center (#1, #2, or a walk from #1 into #2).

**Rabbi's_Rule** (re-curate toward good bridge). Naive "cash the ace and pray" is luck; it's *good
bridge* only with a **reason**:
1. **The count marks the king short** (a preempt/overcall/long-suit bid → he's short in the key suit).
2. **The drop is the safe line; the finesse is the unsafe one** (finesse loses to the danger hand).
3. **The ace is a free first chance** (cash it, keep the finesse in reserve — combining drop + finesse).
- Weed out the current luck-boards ("stiff K happened to drop"). Prefer #1 and #3.

**Two_Way_Finesse** and **Finesse_Simple**: already live and largely in-lane. Verify, light touch only.

---

## 4. Sourcing strategy

- **A hand is 52 cards, decoupled from the scenario that dealt it.** Once harvested, we own the
  auction and contract we wrap around it. Origin scenario is irrelevant to fitness.
- **All scenario pools are fair game** — not just the 5 finesse pools, not just the 12 play pools.
  ~339 btn scenarios; the curated ones each carry ~500-deal pools (`bba-curated/`, `bba/`, `pbn/`).
- **Intent prioritizes the search** (and makes ~170k deals tractable — mine the dense veins, skip the rest):

  | Target structure | Prioritize pools whose intent is… |
  |---|---|
  | Combining chances (two side-suit finesses, 3NT) | notrump: Basic_NT, Stayman, Smolen, 3N_Rebid_by_Opener, Slam_after_Stayman |
  | Good-bridge Rabbi's (a *marked* short king) | competitive/preempt: Basic_Overcall, Basic_Weak_2, Basic_Takeout_Double, Negative/Responsive_Double |
  | Two-way finesse (one-suit guess, count) | slam: Gerber, Jacoby_2N, Splinters, Slam_after_Stayman |
  | To_Finesse_Or_Not (safe line vs. losing finesse) | notrump + suit-fit pools |

- **Universal gate** for any play-lesson candidate: **South declares the target contract and the
  target line makes** — applied structurally (DDS), regardless of source pool.
- Generation from scratch is a **last resort** only if a rung has no good hand anywhere in the corpus.
  (Confirmed the generic pools were built from loose auction filters, so their boilerplate `{Curate}`
  annotation is not per-board analysis — e.g. Choice_Of_Finesses has one stock note on 406/500 boards.)

**How to identify play vs. bid scenarios:** the `# curate: kind=` header. `soundness`/`avoidance`/
`byforce` = play (12 scenarios); `bidding` = bid (28); *none* = legacy uncurated BBO scenarios (~299).
No explicit play/bid label exists; `curate:kind` is the proxy. (Could add a first-class
`# discipline: play|bid` line if we ever want it explicit — maps onto BC's BID/PLAY/DEFEND grouping.)

---

## 5. Engine-fidelity constraints (why board *selection* is constrained)

The lessons play interactively in Bridge Classroom via a **double-dummy** recorded `[Play]` line
(`py/play_line.py`) with a **replay bot** defending; the bot falls to legal-arbitrary cards once the
student diverges. Consequences for what we can teach:

- **Auction inferences: rock-solid** — the bidding is fixed and shown. Curate deals where an
  overcall/passed hand genuinely places the honor.
- **Count inferences (who shows out): solid** — determined by the actual deal, not the bot's skill.
  "Cash your winners, count, then finesse" renders faithfully. This is the most engine-friendly cluster.
- **Signal / discretionary-defense inferences: fragile** — the bot doesn't signal meaningfully.
  **Avoid boards that hinge on reading a defender's signal or optional play.**
- **"Combining chances" needs the fallback to be *visible*.** A DD declarer never combines (it knows
  the layout), so curate deals where **one finesse is offside and the other onside**: the student
  takes the safe/first finesse, it loses, the fallback wins — the principle actually happens on screen,
  and the correct line makes while the careless one fails.

**Serve chain (per lesson):** author `coaching-curated/<scn>.pbn` (South-fixed, token-free) →
`py/coach.py validate` + `py/suit_quality.py` → `py/nonrotate.py <scn>` → `py/bridge_classroom.py <scn>`
(injects the `[Play]` line) → `py/promote.py <scn>` (gated → `coaching/`). toc carries no board counts,
so same-count swaps need no toc edit. **Never hand-edit `coaching/` or `coaching-non-rotated/`.**

---

## 6. Open design questions

- **To_Finesse_Or_Not flavor**: #1 decline / #2 evidence / a walk. (Blocks its board search.)
- **Contract-type mixing**: let each lesson pull whatever contract fits its concept, or keep each to
  one contract family for consistency?
- **Set sizes**: full 30, or tight focused sets (~8–12) that nail the arc without near-clones?
- **Avoidance**: fold into Choice permanently, or eventually its own lesson?
- **Explicit `# discipline:` tag**: worth adding, or leave `curate:kind` as the proxy?

---

## 7. Method — TO BE VALIDATED (fill in after the first lesson proves it)

Intended: build one **structural DDS detector** that classifies a deal by finesse shape
(single clean finesse / one-suit two-way / two takeable finesses / safe-line-vs-losing-finesse /
short-honor-drop-with-a-reason), run it **intent-prioritized** over the dense pools, harvest per
rung, DDS-verify, author, serve. Detector specifics, per-pool yields, and board slates get recorded
here once the Choice_Of_Finesses build validates the pipeline.

_Notes for the detector (from early scans):_ full-table DDS on ~425 boards exceeds a 2-min foreground
call — run scans in the background to a JSON file. A holding-agnostic **swing test** (move a missing
K/Q to the other defender, re-solve, see if the trick count moves) detects finesses regardless of
card shape, but over-flags notrump-stopper and stiff-honor positions as "guesses" — the detector must
distinguish a *takeable finesse* (lead toward a tenace) from mere honor-location sensitivity.

---

## 8. Progress log

- **2026-07-03** — Finesse_Simple board 1 re-curated (pool board 70): single spade AQ9 finesse vs
  East K842, onside, make-or-break; replaces a board where both finesses were offside. Committed
  `7888e8565`. Family design + this plan drafted.
