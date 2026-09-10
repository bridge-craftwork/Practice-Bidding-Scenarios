# `coaching-non-rotated/` — coached PBNs (South=student), bridge-classroom-compatible

This directory holds **non-rotated** coached scenario PBNs: the same boards as
[`coaching/`](../coaching/), but with the rotation pronoun tokens (`@S`, `@v(...)`, `@Your`)
already resolved with **South as the student**, so each file reads correctly from a fixed
seat. Each file is a normal PBN whose boards carry a Baker-Bridge–style `{...}` tutorial
block, written so the [Bridge Play Trainer](../notes/Bridge%20Play%20Trainer.md) can teach the
deal bid-by-bid and during the play.

## bridge-classroom compatibility (`py/bridge_classroom.py`)

These files are also rendered on **[bridge-classroom.com](https://bridge-classroom.com)**
(Rick Wilson's "dumb renderer" — it follows the PBN's coaching directives literally). To
keep them compatible, run the build step from the project root after editing:

```
python3 -P py/bridge_classroom.py            # all files (in place)
python3 -P py/bridge_classroom.py Basic_Major # one scenario
python3 -P py/bridge_classroom.py --check     # dry run, report only
```

It is idempotent and enforces four invariants on every board:

- **`[Board]` numbered 1..n** in file order; the source deck position is preserved in a
  separate **`[OriginalBoard "N"]`** tag (added once, then left alone).
- **No pre-auction `{...}` blocks** — the `{Shape}`/`{HCP}`/`{Losers}` stats and any
  `{Curate ...}` metadata (authoring aids the Trainer ignores) are stripped.
- **The coaching block opens with a `[show …]`** — `[show S]` is prepended unless the block
  already leads with one (e.g. play boards open `[show NS]`).
- **The student's auction-ending Pass is anchored.** bridge-classroom auto-plays any
  unanchored call, so without this the student never gets a turn to confirm the final
  contract — they just spectate after their last bid. When the student's *last* call is a
  Pass, a `[BID Pass]` chunk is inserted before the reflective `[show …]`, naming the final
  contract. Only on boards that already quiz bidding (have a `[BID]`) — play boards are left
  alone — and only when the student's last call is a Pass (skipped when the student declares).
  The fold step never strips a `[BID Pass]`, so this is idempotent.
- **Each anchor sits on its own line.** A linebreak is inserted before every chunk anchor
  (`[BID …]`, `[show …]`, `[POST-AUCTION]`, `[ROLE …][STAGE …]`) that is currently inline. The
  opening anchor stays glued to `{`; `[ACCEPT …]` (a mid-chunk modifier, not an anchor) stays
  inline; anchors already at line start keep their existing blank-line spacing untouched.
- **`[BID]` anchors only the student's own calls.** bridge-classroom's renderer assumes every
  `[BID]` step is a student call and auto-plays until a student-seat call matches the *next*
  `[BID]`'s value — so a `[BID]` on a partner/opponent call makes it skip past (auto-play) the
  student's own later calls. The build drops each non-student `[BID]` and folds its prose into
  the preceding student chunk (the Basic_Major board-1 model); partner/opponent calls are then
  auto-played and explained inline. `[BID]`→call mapping is value-based (walk the auction,
  consume the next matching call), so partially-anchored boards (e.g. an unanchored overcall)
  fold correctly. Boards where a `[BID]` matches no call, or a non-student `[BID]` precedes any
  student `[BID]`, are left untouched and FLAGGED for manual review.
- **The coaching block is a single balanced `{...}`** — a stray trailing `}` is dropped
  (one such defect, `}}`, exists in some `Negative_Double` boards and is also present
  upstream in `coaching/` / `coaching-curated/`; fix it there too when convenient).

The model board the transform mirrors is the first board of `Basic_Major.pbn`.

## How the trainer uses these files

- For a scenario, the trainer loads `coaching/<scenario>.pbn` if it exists, and falls
  back to `bba/<scenario>.pbn` (plain, no prose) otherwise.
- The trainer's **sidebar menu is restricted to scenarios that have a coaching file**, so
  in practice every user-pickable scenario is one that lives here.
- All prose is **precomputed** — the trainer makes no AI calls at runtime.

The authoritative parser is `parse_coaching` in the trainer repo's `server.py`
(`~/AI-Bridge-Play-Trainer`). When in doubt about behavior, that function is the source of
truth; this README documents its contract.

## ⚠️ Coaching depends on the convention card — regenerate after any card change

The coached **auctions are BBA's output under the scenario's `.bbsa` convention card**
(`convention-card-ns`/`-ew` in the `.btn`). If you edit a card, the `pbn/` / `bba/` /
`bba-filtered/` artifacts **and every coaching file built on them go stale** — they may
teach conventions the bots no longer bid (this bit us once: a "Basic Bridge" card had Bergen
and Jacoby 2NT turned off, but the coaching still described them). After any card edit:

1. Regenerate the pipeline from `pbn` onward: `python3 build-scripts-mac/pbs-pipeline-mac.py "<scenario>" "pbn+"`.
2. Rebuild the affected coaching files on the fresh auctions.

Deals are deterministic (fixed seed), so the **hands don't change — only the auctions and
contracts do**. To find stale files, diff each coached board's embedded auction against the
fresh `bba/` board for the same `[Deal]`.

## Play-of-the-hand scenarios (finesses, hold-ups, ruffs, endplays, top tricks)

These teach **declarer technique**, so the student is South/declarer and the bulk of each
block is the `[ROLE declarer][STAGE …]` play tips.

- **Curate the boards to the target contract.** Select ~30 boards where **South declares the
  intended contract** (filter the `bba-filtered/` source by `[Declarer "S"]` + the target
  `[Contract]`, e.g. Hold_Up_3N → `3N`, Side_Suit_Ruff → `4S`). The raw filter leaks slams,
  partscores, and boards where South isn't declarer — those don't show the lesson.
- **Analyze the actual deal**, not the idealized brief: where the key card sits, which
  defender is the danger hand, whether the finesse wins/loses on *this* layout. The prose
  must stay consistent with the board's `[Contract]`/`[Result]`/`[Score]`.
- **If a board doesn't fit the lesson, teach the real line and flag it** — never invent the
  textbook layout. (The dealer constraints often don't fully enforce the exact card
  placement, so a fraction of boards are off-pattern; tightening the `.btn` dealer code is
  the root fix.)
- Block layout mirrors `Play_Top_Tricks.pbn`: `[show S]` intro → `[BID]` per South call →
  `[POST-AUCTION]` (count winners/losers, name the technique, reveal partner via `[show NS]`
  as combined hands) → declarer/leader/defender `[ROLE][STAGE]` chunks, with praise only in
  `[STAGE post-play]`.

### Opening-lead advice (the `[ROLE leader][STAGE pre-lead]` chunk)

Make the leader's pre-lead tip follow standard practice (ref: https://kwbridge.com/leads.htm).
Pick the suit, then name the **specific card** and why:

- **Which suit — vs a suit contract** (safety): a singleton → partner's bid suit → a strong
  touching-honor sequence → your longest suit (low) → an unbid suit → dummy's → a trump (last
  resort). Don't lead unsupported/underled aces, underled broken honors (KJxx, Q10x) outside
  partner's suit, or declarer's suit.
- **Which suit — vs notrump** (attack length): **4th-best from your longest, strongest suit**,
  unless partner bid one (lead it), your long suit is theirs, or it holds 3+ touching honors
  (lead the honor).
- **Which card from the suit:** AK… → K; touching honors (KQ, QJ, J10, 109) → the top honor;
  interior sequence (the J in KJ10x, the 10 in Q10 9 7 4) → top of that sequence; 4+ with no
  sequence → 4th best; 3 small → lowest; doubleton → top.

Ground it in the actual hand and auction (e.g. "lead the ♦K, top of your ♦KQJ" / "4th-best
spade, the ♠5, your longest suit against their notrump").

**The declarer coaching should USE that lead.** The `[ROLE declarer][STAGE post-lead]` chunk
fires after the opening lead is on the table, so it should *start from the actual lead*, not
ignore it: name what was led, the **trick-1 decision** (win / duck / which card), and what the
lead reveals — a 4th-best lead gives a count (rule of 11); a top-of-sequence lead places the
honors below it with the leader; a singleton warns of a coming ruff; a lead into your tenace
may hand you a trick. *Then* proceed to the deal's technique. (Hold_Up_3N is the clearest case:
the hold-up duck *is* the response to the lead.) Example: "West leads the ♦K — top of a
sequence, so the ♦QJ sit with West and nothing's free for them. Win the ♦A, draw trumps, then
run the spade finesse…"

**But hedge the *interpretation* — from declarer's seat it's an inference, not a fact.** The
card led is certain; what it means is a read. Say the ♦2 **"looks like"** / **"appears to be"** a
fourth-best (**"suggesting"** about four), the ♦K **"looks like"** the top of a sequence (West
**"probably"** holds the QJ), a low card **"looks like"** a singleton (**"watch for"** a ruff).
Avoid the flat "the ♦2 *is* fourth-best, *marking* four" — defenders can lead top-of-nothing, a
short suit, or a safe exit. Hedge the read, then plan for the likely case.

**Defensive signals — keep them nuanced and optional.** The audience is beginner/casual, and
such players rarely give reliable attitude/count/suit-preference signals (ref:
https://www.acblunit390.org/Simon/signals-and-discards.htm). So never assert a signal as fact —
not as a defender obligation ("you *must* play the ♥9 to encourage") nor as a declarer inference
("East's high heart shows an even count"). If a signal is worth mentioning at all, **hedge it**:
"*if* your opponents are signaling, that high card *hints* at length — but don't count on it at
this level." Declarer can read defenders' cards too, but should lean on counting and the opening
lead, not on assumed signals. One light mention at most; prefer concrete card-reading (rule of
11, who showed out) over signal theory.

## File structure

Standard PBN. For each board you want coached, insert **one `{...}` block immediately
after the board's `[Auction "..."]` tag and its auction call lines** (before the next
`[Tag]`). Boards with no block just play normally. Only the curly block right after
`[Auction]` is read; any pre-auction `{Shape ...}`/`{HCP ...}`/`{Losers ...}` comments
from the `bba/` files are ignored.

The block body has up to three sections, **in this order**:

1. **Bidding tutorial** — an intro chunk plus one `[BID]`-anchored chunk per call.
2. **`[POST-AUCTION]`** — prose shown after the auction is fully revealed (contract summary
   etc.), before the Play hand-off.
3. **Card-play tips** — `[ROLE …][STAGE …]` chunks shown during play.

## Markers

| Marker | Meaning |
|---|---|
| `[show X]` | Reveal hand(s). `X` is one or more seat letters in **real compass** (`N E S W`) — e.g. `[show S]`, `[show NS]`. Reveals accumulate down the board. |
| `[BID xxx]` | Anchor the following prose to a call. `xxx` is PBN form: `1C 2D 3NT X XX`. Case-insensitive; `1N` and `1NT` are treated the same. Anchors to the next unconsumed matching call; when a call is ambiguous (e.g. several `Pass`es) the **student's own** call wins. Prose before the first `[BID]` is the intro chunk. |
| `[ACCEPT call …]` | Extra call(s) the bid-quiz should accept as correct alongside the one actually made — for judgment decisions with more than one defensible call (e.g. `[ACCEPT Pass]` after `1NT-2NT` with a middling hand). |
| `[POST-AUCTION]` | Begins the post-auction section (see above). |
| `[ROLE r][STAGE s]` | A card-play tip. `r` = `declarer` \| `leader` \| `defender`. `s` = `auction-end` \| `pre-lead` \| `post-lead` \| `post-play`. The trainer shows the chunk matching the student's role at that stage. |
| `\S \H \D \C` | Render as ♠ ♥ ♦ ♣. |

**Deferred reveals:** a `[show S]` (the student's own hand) is fine mid-auction, but any
`[show]` that exposes a hand the student can't yet see (partner/dummy, opponents) — and the
prose after it — is automatically held back and folded into the post-auction chunk, so a
hand is only described once it's visible. Author naturally; the parser handles the timing.

## Pronoun / verb tokens (`@S`, `@v(...)`, `@Your`)

Deals are played **with rotation**, so the student may sit in *either* N/S seat. A `[BID]`
chunk is authored once, in the **second person addressing its own actor**; at render time the
trainer rewrites it to second person ("you") when the student actually made that call, and to
third person ("your partner") when the *partner* made it. These inline tokens are what make
that flip work — so one file reads correctly from either seat. The authoritative substitution
is `fill_pronouns` in the trainer's `server.py`.

| Token | When the student made the call | When partner made it |
|---|---|---|
| `@S` | `You` | `Your partner` |
| `@s` | `you` | `your partner` |
| `@Your` | `Your` | `Their` |
| `@your` | `your` | `their` |
| `@v(base\|third)` | `base` (e.g. `have`, `open`, `raise`) | `third` (e.g. `has`, `opens`, `raises`) |

- **`@S`/`@s`** — the subject pronoun. `@v(base|third)` — **verb agreement**: the part before
  the `|` is used in the student (second-person) rendering, the part after for the
  partner (third-person) rendering. Common forms: `@v(have|has)`, `@v(open|opens)`,
  `@v(show|shows)`, `@v(bid|bids)`, `@v(raise|raises)`, `@v(respond|responds)`.
- **Parentheses, never braces.** Write `@v(open|opens)`, not `@v{open|opens}` — a `}` inside
  the token would collide with the coaching block's own `}` delimiter and truncate the block.
- **Use `@S` once per chunk** as the subject. Don't name the actor as the subject a second time
  (`@S … @s …`) — in third person that reads "Your partner … your partner …". After the first
  subject, continue with verbs joined by "and" (`@v(open|opens) … and @v(let|lets) …`) or start
  a fresh sentence about the *call* rather than the actor.
- Intro and reflective `[show NS]` chunks are authored **seat-neutral** (no tokens) and pass
  through unchanged.

Example — `[BID 1N] @S @v(have|has) 15-17 balanced, so @v(open|opens) 1NT.`
renders as *"You have 15-17 balanced, so open 1NT."* for the student who bid it, or
*"Your partner has 15-17 balanced, so opens 1NT."* when the partner bid it.

## Authoring rules

- Write from the **student's perspective**: "you" (S), "partner" (N), "LHO" (W), "RHO" (E).
  The student is normally South.
- **Voice: relaxed, warm, encouraging — like a friendly teacher at your shoulder, not a
  textbook.** The audience skews beginner/senior, so keep it conversational and supportive.
  Put **genuine praise in the reflective end-of-deal chunks** — the partner reveal,
  `[POST-AUCTION]`, and the `[ROLE …][STAGE post-play]` review — where a "nicely judged" or
  "that was the whole story — well played" lands naturally ("Twelve tricks, +650 — lovely
  result"). **Do NOT put praise ("Nice bid!") in a `[BID]` chunk:** those fire after *every*
  attempt, right or wrong, so praise there would also appear under a wrong answer. Per-bid,
  reactive praise is handled by the trainer app's own ✓/✗ quiz messages, not the prose. Stay
  warm and accurate — never sacrifice the bridge facts or the rules below for tone.
- Open the intro chunk with `[show S]` to reveal the student's hand; reveal partner/opponents
  later as the narrative needs (often `[show NS]` near the end).
- **The intro chunk poses the decision; it does not recite the hand or give the answer.** The
  student can see their own 13 cards, so don't list them (`You hold \S… \H… \D… \C…`), and
  don't name or hint the call. Frame it as: `You have <HCP> HCP and a <balanced |
  semi-balanced | unbalanced> hand[, with <a significant feature or two>]. What do you open?`
  (or `RHO opened 1X. What's your call?` in competitive scenarios). Vary the feature wording
  per hand — "a strong rebiddable six-card spade suit", "both majors", "5-5 in the minors",
  "no five-card major", "stoppers everywhere". Shape buckets: balanced = 4333/4432/5332;
  semi-balanced = 5422/6322; unbalanced = any singleton/void, 7+ suit, or two 5+ suits. The
  `[BID xxx]` chunks come *after* the call, so they freely explain the bid — that's where the
  teaching goes, not the intro.
- **1♦ opening rule (Basic-Bridge):** a 1♦ opener normally has 4+ diamonds. The only exception
  is when the distribution is exactly 4=4=3=2. With 3-2 in the minors, open the 3-card suit.
- Emit an anchored chunk for each **non-pass** call from the student's side. **Never anchor
  `[BID Pass]`.**
- **When you reveal partner with `[show NS]`, describe the *combined* hands — the fit, the
  combined strength, and the weakness — not partner's 13 cards.** Once revealed, partner's
  hand is on screen, so a card-by-card list (`Partner: \S… \H… \D… \C…`) is redundant.
  Name the trump/notrump fit and its combined length, where the partnership's power lives
  (controls, a running suit, ruffing values), and the soft spot (a leaky short suit, a
  missing stopper, thin trumps, a 4-3 fit, a misfit), then keep the contract/result takeaway.
  Reference a specific honor only when it makes a teaching point (a fitting honor, a control
  opposite shortness) — never to enumerate the hand.
- Keep each chunk to ~2–4 short, conversational, second-person sentences. Ground the prose in
  the scenario's `btn/<scenario>.btn` `@chat` brief; if it teaches a decision tree, walk the
  student through it for *this* hand.
- Every `[BID xxx]` must match a real call in the auction. If you can't find a clean match,
  **drop the marker** rather than invent one — an unmatched `[BID]` degrades to the previous
  anchored chunk.
- Seat letters in `[show]` are **real compass** (the actual `[Deal]` seats); the trainer
  rotates everything so the student sits South on screen. Don't pre-rotate.

## Bridge accuracy in the prose

Beyond the structural rules above, keep the bridge correct and the wording precise:

- **Balanced vs. unbalanced.** Balanced = 4-3-3-3, 4-4-3-2, 5-3-3-2 (no singleton or void, at
  most one doubleton). Semi-balanced = 5-4-2-2 or 6-3-2-2. **Any singleton or void makes a hand
  unbalanced, regardless of HCP** — never call a singleton-bearing hand "balanced" or
  "balanced-ish" (e.g. 1-4-5-3 is unbalanced).
- **Diagnose the real reason a bid is rejected.** If a hand is in the point range for a call but
  can't make it, the reason is usually *shape*, not strength. 15 HCP is plenty for 1NT (15-17) —
  if you're not bidding 1NT, say the hand is **unbalanced / unsuitable**, not "not strong enough."
- **Opening-suit algorithm (Basic-Bridge).** A biddable major is 5+, a biddable minor is 3+.
  Open the longer biddable suit; with equal length open the **higher-ranking**; with exactly
  **3-3 in the minors open 1♣ (the short club)**. A 1♦ opener normally has 4+ diamonds — the only
  exception is exactly 4=4=3=2 (open the 3-card diamond). With two 5-card suits, open the
  **higher-ranking** (5-5 spades-and-diamonds → 1♠).
- **Reverse, defined correctly.** A reverse is a new-suit rebid **higher-ranking than your first
  suit** that forces partner to the three-level to show preference; it promises extras (~17+) and
  is forcing for one round. A second suit **lower-ranking** than your first — so partner can give
  preference at the two-level — is **not** a reverse; it's a natural, wide-range rebid (~11-16
  HCP). For example **1♦-1♠-2♣ is natural** (4+♦, 4+♣, fewer than three spades), not a reverse.
- **Geometry words.** Partner sits **opposite** you, across the table — describe partner's holding
  as "♦KJT73 opposite your ♦AQ862," never "behind." "Behind" / "in front of" describe an
  *opponent's* positional relationship during the play, not partner.
- **Terminology.** Choose the **higher-ranking** suit (not just "the higher"); a misfit is a
  **lack of a fit** (not "no second suit between you").
- **No thinking-out-loud.** Finished prose states the conclusion. Don't leave "Wait —,"
  "actually," or visible self-corrections in the text.

## Example (one board)

```
[Auction "S"]
1D    Pass  1H    Pass
2H    Pass  Pass  Pass
{[show S]
You have 14 HCP and a semi-balanced hand with five diamonds, four good hearts, and no
five-card major. What do you open?
[BID 1D] You have 14 HCP and five diamonds. With no five-card major, open one diamond.
[BID 2H] Partner showed four+ hearts. You hold four to the ace-king — raise to two hearts
and let partner declare.
[POST-AUCTION]
Your side has 23 combined HCP and an eight-card heart fit. Two hearts needs eight tricks.
[ROLE declarer][STAGE auction-end]
Partner declares; your hand is dummy. With the \HAK and \CAK this dummy carries real power.
[ROLE leader][STAGE pre-lead]
Lead the \DA, top of your \DAK. Cash a winner first and look at dummy before continuing.
[ROLE declarer][STAGE post-play]
Drawing trumps and cashing your AKs was all you needed — no finesse to reach eight tricks.
}
```

## See also

- **Generation/authoring plan** (how these files get produced, including the subagent
  prompt template): `pbn-coaching-generator-plan.md` in the trainer repo
  (`~/AI-Bridge-Play-Trainer`).
- **Parser contract:** `parse_coaching` / `_strip_post_auction_blocks` in that repo's
  `server.py`.

> Note: `[hint]` / `[wrong xxx]` per-bid miss-prose are **proposed but not yet implemented**
> (see the generator plan's "Followups"). Don't author them yet — the parser ignores them.
</content>
