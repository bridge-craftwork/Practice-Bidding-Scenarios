# Bridge Classroom — Change plan for Rick

> **STATUS: UPDATED DRAFT 2026-06-29** — supersedes the version sent 2026-06-28. Pending
> David's review, then delivery to Rick. Nothing here is merged into Rick's upstream yet;
> "built" means committed/pushed to **David's fork only**.

*Self-contained: written to be read cold, without PBS-internal context.*

**What's new in this update.** We're proposing to deliver everything as **pull requests
from David's fork** (not a document of asks), and we've added a **folder migration** that
collapses the two coaching folders into one. The plan now has three parts:

- **Part M — Folder migration.** Collapse `coaching-non-rotated/` + `coaching/` (PBS repo)
  into a single `coaching/`. One four-line change in BC; the rest is PBS-side. *(New.)*
- **Part A — Built on David's fork.** Five features already implemented; we'll send these
  as PRs for review + upstream merge.
- **Part B — Fixes.** Small bugs we'll now **build ourselves and PR** (B1, B2, B5, B6);
  two larger engine enhancements left as **requests for Rick** (B3, B4).

Fork: `https://github.com/ADavidBailey/Bridge-Classroom`.
- A1–A4 are on branch `main` (**18 commits ahead** of `Rick-Wilson/Bridge-Classroom@main`).
- **A5 (`[ACCEPT]`) is on a separate branch `accept-and-lesson-sync`** (off `fork/main`,
  +2 commits) — **not yet pushed**; merges cleanly on top of `main`.

---

## Part M — Folder migration: collapse the two coaching folders into one

**The problem.** PBS currently has two near-identical coaching folders. `coaching/` is the
pipeline's served output; `coaching-non-rotated/` is what BC actually reads. They date from
a now-retired "rotation" scheme — every lesson is authored South-fixed, so the
"rotated/non-rotated" naming no longer means anything. Today `coaching-non-rotated/` is a
**superset**: it holds all of `coaching/`'s files plus 8 defense-set lessons, and it is the
**only** folder with `toc.json` (the index BC loads). The goal is one folder named
`coaching/`, with no "rotated" naming left.

**Why this approach (safe, no downtime).** BC reads PBS over the live internet from `main`.
A straight rename would break BC until Rick merges the repoint. Instead we stand up the new
folder *first* and delete the old one *last*, so the old path keeps serving BC the entire
time — Rick can review on his own schedule and BC is never broken.

**Phase 1 — PBS side (David), nothing breaks.** Bring `coaching/` to full parity with
`coaching-non-rotated/`: copy in the 8 defense-set files and `toc.json`, and retarget the
PBS maintenance scripts so `coaching/` stays current. Push to PBS `main`. Both folders now
exist and are identical; BC still reads `coaching-non-rotated/`, unchanged.

**Phase 2 — BC side (PR to Rick).** The entire BC footprint of the rename is four touch
points, all just swapping the path `coaching-non-rotated` → `coaching`:

| File | Line | Change |
|---|---|---|
| `src/composables/useAppConfig.js` | 134 | `tocUrl` → `…/main/coaching/toc.json` |
| `src/composables/useAppConfig.js` | 135 | `baseUrl` → `…/main/coaching` |
| `src/views/MainLayout.vue` | 1169 | regex `/\/coaching-non-rotated$/` → `/\/coaching$/` |
| `src/utils/__tests__/pbnParser.test.js` | 330 | comment only — update the cited path *(cosmetic)* |

During Rick's review BC works on **either** path, because both folders still exist on PBS
`main`.

**Phase 3 — cleanup (after merge).** Once Rick's repoint is merged and BC is confirmed
loading from `coaching/`, delete `coaching-non-rotated/` from PBS. Final layout:
`coaching-curated/` (staging) → `coaching/` (served + what BC reads). No "rotated" anywhere.

> Out of scope: the legacy `pbn-rotated-for-4-players/` and `lin-rotated-for-4-players/`
> dirs are a separate, older BBO-practice artifact, not read by BC — untouched here.

---

## Part A — Built on our fork; requesting review + upstream merge

Listed newest-feature-first. "Frontend-only" = safe to merge independently; the report
button also adds a **server (Rust) route**, so it needs coordination with the API.

### A5. `[ACCEPT]` judgment-call scoring  *(frontend only)*
A coaching board can mark a second defensible call as also-correct with an inline
`[ACCEPT <call>]` marker, for judgment decisions with more than one sound call. Before,
BC scored the alternate wrong and the unrecognized tag leaked into displayed text.
- **Behavior:** parser pulls `[ACCEPT …]` into the bid step's `acceptedBids` and strips
  the marker; `makeBid` scores correct on the recorded call **or** any accepted call. The
  auction still advances on the recorded call. Purely additive — boards without `[ACCEPT]`
  are byte-identical, so existing lessons (Baker Bridge, the 5 bundled) are unaffected.
- **Files:** `src/utils/pbnParser.js`, `src/composables/useDealPractice.js`; tests in
  `src/utils/__tests__/pbnParser.test.js`, `src/composables/__tests__/useDealPractice.test.js`.
- **Branch/commits:** `accept-and-lesson-sync` — `6259eb0` (impl), `f0aee3c` (test).
- **Note:** the marker is supplied by PBS coaching content (PBS side, separate repo); this
  is just the engine that consumes it.

### A1. "Report a Problem" button  *(frontend + API)*
Lets a student flag a problem on a coached lesson from inside the app. Button sits beside
the bidding box; popup is draggable; report endpoint is configurable.
- **Files:** `src/components/ReportProblemModal.vue`, `src/composables/useReportProblem.js`,
  `src/views/MainLayout.vue`, `vite.config.js`; **API:** `bridge-classroom-api/src/routes/reports.rs`
  (+ `config.rs`, `main.rs`, `routes/mod.rs`, `.env.example`).
- **Commits:** `18b48a2`, `ee1fc79`, `07bd31e`, `4a3927f` (merge `54dc1f8`).
- **Note:** endpoint set via `VITE_REPORT_URL`; our local setup points it at a small relay,
  but the Rust route is the real server path — this is the piece to align with Rick.
- **Now opt-in per collection** (commit `07b618a`, on branch `accept-and-lesson-sync`):
  a report files an issue in the *content* repo, so the button shows only for a collection
  that sets `report: true` and points the endpoint at its own repo. **On for David Bailey
  Scenarios, off for Baker Bridge** — a report on a Baker board is about your content, not
  David's, so it shouldn't open an issue in his repo. **Rick: if you want it on Baker
  Bridge, say so** — it's one flag (`report: true` on the collection) plus pointing
  `VITE_REPORT_URL` at your repo; happy to wire it up or leave it to you.

### A2. Scenario @chat popup  *(frontend only)*
Shows the scenario's chat/teaching blurb in a sizable, movable popup; appears in Bidding
Practice and in coaching lessons; reopen button labeled "Description".
- **Files:** `src/components/ScenarioChatPopup.vue`, `src/views/MainLayout.vue`,
  `src/views/BiddingPracticeView.vue`.
- **Commits:** `d3add23`, `22dc2eb`, `8ef20f5`, `7159985`, `c41db3c`, `18b3d0e` (merge `d7834a2`).

### A3. Coaching-feedback fade — bids  *(frontend only)*
Three-mode feedback on a bid: correct call → brief *varied* affirmation + the
partner/opponent follow; wrong call → full explanation. Renderer reads the `⟦ ⟧` the
content wraps around the student's own justification; un-bracketed legacy content is
unchanged. Adds a board-level cheer (Bravo!/Perfect!) when every call on a board was right.
- **Files:** `src/utils/pbnParser.js`, `src/composables/useDealPractice.js`, `src/views/MainLayout.vue`.
- **Commits:** `c8a9f60`, `c5dd047`, `065b44e` (merge `add4958`).

### A4. Coaching layout  *(frontend only)*
Left-align the table during practice with the chat open on the right; re-center when the
description closes; cap coaching-text height to the window so the bid box stays in view.
- **Files:** `src/views/MainLayout.vue`.
- **Commits:** `4e484c8`, `15bc887`.

---

## Part B — Fixes

**B1, B2, B5, B6 — after Rick approves, we'll build these on the fork and send PRs** (small,
low-risk; converting the old "please fix" asks into mergeable work so Rick just reviews).
**B3, B4, B7 stay as requests for Rick** — engine/behavior changes left for him to own (B7
refines A5's `[ACCEPT]` and carries a precise spec). Per David: no new BC code until Rick
signs off (see the Delivery plan).

Each item still ends with a **paste-ready Claude prompt** for reference. If Rick prefers to
do one himself, he can open Claude Code at the root of his `Bridge-Classroom` checkout and
paste the block — it'll read the repo and propose the change as a diff.

### B1. BUG — `[showcards]` multi-seat tag is mis-parsed  *(small; bug — **we'll PR**)*
A `[showcards …]` tag that names **two seats** is parsed wrong.
- **Where:** `src/utils/pbnParser.js`, the seat regex `/([NESW]):([^,\s]+(?:,[^,\s]+)*)/gi`
  (~line 342).
- **Repro:** `[showcards N:C4,E:CT]` parses to `{ N: ["C4", "E:CT"] }` — the regex swallows
  `,E:CT` as a *second card of North*, so East is lost. The documented `E:S7,S:S5` form fails
  the same way.
- **Current workaround (in our PBN content):** a **space after the comma** (`N:C4, E:CT`)
  breaks the greedy match and parses correctly. So existing files work, but the documented
  no-space format is broken.
- **Proposed fix** (verified against all cases below) — replace the regex loop with a split
  on "comma that precedes a seat token":
  ```js
  for (const part of showcardsValue.split(/,(?=\s*[NESW]:)/)) {
    const i = part.indexOf(':'); if (i < 0) continue
    const seat = part.slice(0, i).trim().toUpperCase()
    const cards = part.slice(i + 1).split(',').map(c => c.trim().toUpperCase())
    if (seat) showcards[seat] = cards
  }
  ```
- **Acceptance:** `N:C4,E:CT` and `E:S7,S:S5` → two seats; `E:S7,H3,S:S5` → E has two cards,
  S one; `N:C4,C7` → one seat, two cards; spaced variants (`N:C4, E:CT`) still parse the same.
- **Claude prompt:**
  ```
  In src/utils/pbnParser.js, fix the [showcards ...] parser so a tag naming two seats
  parses correctly. The seat regex near line 342, /([NESW]):([^,\s]+(?:,[^,\s]+)*)/gi,
  greedily swallows the next seat as a card, so [showcards N:C4,E:CT] becomes
  { N: ['C4','E:CT'] } and East is lost. Replace the matching loop with a split on a
  comma that precedes a seat token:
    for (const part of showcardsValue.split(/,(?=\s*[NESW]:)/)) {
      const i = part.indexOf(':'); if (i < 0) continue
      const seat = part.slice(0, i).trim().toUpperCase()
      const cards = part.slice(i + 1).split(',').map(c => c.trim().toUpperCase())
      if (seat) showcards[seat] = cards
    }
  Then add a vitest case. It must pass: N:C4,E:CT and E:S7,S:S5 -> two seats;
  E:S7,H3,S:S5 -> E has two cards and S one; N:C4,C7 -> one seat with two cards; and the
  spaced form N:C4, E:CT still parses the same.
  ```

### B2. BUG — header title overprints the greeting  *(small; cosmetic CSS — **we'll PR**)*
On a long collection/lesson title (e.g. "…Bailey Scenarios - Third Hand vs Notrump"), the
`<h1>` title and the "Welcome back, David" greeting render on top of each other.
- **Where:** `src/views/MainLayout.vue` — `<header class="app-header">` (h1 ~line 18,
  greeting span line 19). Cause: `.welcome-greeting` is `position: absolute; left: 50%`
  (centered, ~line 1366), drawn over the flex header; the h1 has no max-width/ellipsis, so a
  long title reaches the center and collides.
- **Requested:** title and greeting never overlap on any title length.
- **Options (Rick's call):** (a) take `.welcome-greeting` out of absolute positioning and let
  it sit in the flex flow; (b) truncate the h1 with `min-width:0; overflow:hidden;
  text-overflow:ellipsis; white-space:nowrap` and a max-width that stops before center;
  (c) hide the centered greeting on lesson views.
- **Claude prompt:**
  ```
  In src/views/MainLayout.vue, fix the app header so a long collection/lesson title never
  overlaps the "Welcome back, ..." greeting. The greeting span (.welcome-greeting, ~line
  1366) is position: absolute; left: 50%, drawn over the flex header, and the h1 title has
  no max-width or ellipsis, so a long title collides with it. Pick the cleanest fix: either
  move .welcome-greeting into the normal flex flow, or truncate the h1 (min-width:0;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap, plus a max-width that stops
  before center), or hide the centered greeting on lesson views. Verify with a long title
  like "David Bailey's Scenarios - Third Hand vs Notrump".
  ```

### B3. ENHANCEMENT — per-card (lead/play) 3-tier feedback  *(medium — **request for Rick**)*
The **bid** version is built (A3, on the fork). Requested: the same fade for **card**
decisions (opening leads and third-hand play). Today a wrong card shows the same text regardless of which card
was chosen. Respond to the *actual* choice — correct (terse nod) / reasonable ("good thought,
but…") / wrong (full why) — with length fading by correctness.
- **Claude prompt:**
  ```
  Extend Bridge Classroom's 3-tier feedback fade from bids to card plays. For bids it
  already works: a correct call shows a brief affirmation, a wrong call the full
  explanation, reading the brackets the content wraps around the student's own
  justification (see src/composables/useDealPractice.js makeBid and the parsing in
  src/utils/pbnParser.js). Do the same for card decisions (opening leads and third-hand
  play): respond to the actual card chosen -- correct (terse nod) / reasonable ("good
  thought, but...") / wrong (full why) -- with the explanation length fading by
  correctness. Today a wrong card shows the same text no matter which card was chosen.
  Propose the content markup and the engine changes before implementing.
  ```

### B4. ENHANCEMENT — full defender play-out with revert-and-correct  *(large — **request for Rick**)*
Let the student defend the **whole** hand card-by-card (not just the opening lead). A mis-play
is reverted and the correct card substituted, then play continues — the declarer-play model
applied to a defender (South).
- **Status:** prototype + build-ready handoff spec already on our fork, branch
  `defender-playout-investigation` (commits `d753cab`, `23be662`, `aa9c9a5`). Ready to build
  when chosen.
- **Claude prompt:**
  ```
  Build full defender play-out in Bridge Classroom: let the student (South) defend the whole
  hand card by card, not just the opening lead. A mis-played card is reverted and the correct
  card substituted, then play continues -- the declarer-play model applied to a defender. A
  prototype and a build-ready handoff spec already exist on the branch
  defender-playout-investigation (commits d753cab, 23be662, aa9c9a5). Check out that branch,
  read the spec, and integrate it into the main play flow.
  ```

### B5. NICETY — remember the previous attempt on revisit  *(small; optional — **we'll PR if David wants it**)*
Returning to a completed deal resets it to the start (a clean re-try) — fine as-is. Optional
improvement: remember the previous lead/play + result instead of fully resetting.
- **Claude prompt:**
  ```
  In Bridge Classroom, when a student revisits a completed deal it currently resets to the
  start for a clean re-try. Add an option to instead remember the previous lead/play and
  result and show it on revisit, while keeping the clean-retry behavior available. Find where
  a deal is reset on load (the play / deal-practice composables) and add the
  remembered-attempt path.
  ```

### B6. FIX — lead-lesson affirmations + board cheer borrow bid wording  *(tiny — **we'll PR**)*
On a lead/defense lesson, **both** success messages currently use bid wording. There are two
separate sets in `src/views/MainLayout.vue`, and both need a card-play variant:
1. **Per-call affirmation** (`AFFIRMATIONS`, ~line 372): the nod after a correct call. On a
   lead lesson it should read like a lead, not a bid. **Avoid "Well led!"** (too stiff).
   Preferred lead set: **"Good lead!", "Good", "Correct lead", "Nice lead".**
2. **Board-level cheer** (`CELEBRATIONS`, ~line 406 — `'Bravo!', 'Perfect!', 'Beautifully
   bid!', 'Flawless — every call!', 'Nailed the whole auction!'`): shown when every call on
   the board was right. The bid-flavored ones ("Beautifully bid!", "Nailed the whole
   auction!") read wrong on a card lesson. Needs a card-play set, e.g. **"Beautifully
   played!", "Perfect — every card!", "Flawless defense!", "Nailed it!"** (wording Rick's/
   ours to taste).

Both already vary per board (index `% set.length`); keep that mechanism, just branch the set
on lesson type (card-play vs bid).
- **Claude prompt:**
  ```
  In Bridge Classroom (src/views/MainLayout.vue), the success messages on a lead/defense
  (card-play) lesson borrow bid wording. There are TWO sets to fix: AFFIRMATIONS (~line 372,
  the per-call nod) and CELEBRATIONS (~line 406, the board-level cheer shown when every call
  was right, e.g. "Beautifully bid!"). When the lesson/step is a card play rather than a bid,
  use card-play variants instead: per-call from {"Good lead!", "Good", "Correct lead",
  "Nice lead"} (do NOT use "Well led!"), and the board cheer from {"Beautifully played!",
  "Perfect — every card!", "Flawless defense!", "Nailed it!"}. Keep the existing
  vary-per-board selection (index % set.length); just branch the chosen set on whether the
  current step / lesson is card-play or bidding. affirmationFor() and boardCelebration() are
  the two functions to touch.
  ```

### B7. ENHANCEMENT — `[ACCEPT]` should revert + flag the alternative (orange), not score it as fully correct  *(small/medium — **request for Rick**, refines A5)*
This is about the behavior of A5's `[ACCEPT]` marker, surfaced by report #140 (Basic_Weak_2
D6). Today `[ACCEPT]` is purely binary: an accepted call is scored **fully correct**, the
student's actual call is **hidden** behind the recorded call (`useDealPractice.js makeBid`
pushes the recorded call into the displayed auction; the header reads `recorded-call —
affirmation`), and the all-correct board cheer ("Beautifully bid!") fires. So a student who
deliberately picks the accepted *alternative* sees it praised as if it were the textbook
call, and never sees that they chose differently.

Desired behavior (David's spec):
- **Never let a non-recorded call stand** — there's no way to know a call ends the auction (an
  opponent could bid over it), so an accepted call must be **struck out and reverted to the
  recorded call**, exactly like a corrected wrong bid. The auction always advances on the
  recorded call (both mid-auction and final).
- **Distinguish by colour, not by faking correctness:**
  - textbook call → green/normal (as today);
  - **accepted alternative → ORANGE strike-out + the corrected call + an "acceptable
    alternative" note** (not a failure, not penalised, and it should NOT trigger the
    "Beautifully bid!" perfect-board cheer);
  - wrong call → RED strike-out + corrected call (as today).
- So `[ACCEPT]`'s only job becomes "don't penalise this call, revert it, and explain it as a
  reasonable alternative" — a third tier between right and wrong.
- **Claude prompt:**
  ```
  In Bridge Classroom, change how the [ACCEPT ...] marker behaves. Today an accepted call is
  scored fully correct and the student's actual call is hidden: useDealPractice.js makeBid
  pushes the recorded call into the auction and the header shows recorded-call + affirmation,
  and the all-correct board cheer fires. Instead: a call that is in the step's acceptedBids
  but is NOT the recorded call should be treated as a third tier between right and wrong --
  struck out and reverted to the recorded call (exactly like a wrong bid is corrected; the
  auction always advances on the recorded call), but drawn with an ORANGE strike-out (wrong
  stays RED) and shown as "an acceptable alternative" with its explanation, not penalised in
  the score and NOT counted toward the perfect-board "Beautifully bid!" cheer. acceptedBids
  is already parsed in pbnParser.js; flag the accepted-alternative case in makeBid and render
  the orange tier in the auction display + the feedback header in MainLayout.vue.
  ```

---

### B8. ENHANCEMENT — play-table controls: Review, Undo, Claim  *(medium — **request for Rick**)*
David's request (2026-07-03), now that the declarer-play lessons (finesse family + exam)
play out full hands interactively: the play table should carry the three standard controls.

- **Review** — step back through the tricks already played (read-only replay of the hand so
  far), so a student can re-examine what has fallen before committing to the next card.
- **Undo** — take back the student's last card. The audience is seniors on varied devices;
  misclicks happen, and today one stray tap plays a card irrevocably.
- **Claim** — claim the remaining tricks once the hand is proven (trumps drawn, suit
  established). Clicking out ten obvious winners one by one buries the lesson in busywork.

Notes: all three touch the play-state engine (trick state + the recorded-`[Play]` replay
bot), so this is squarely engine territory — **parked until Rick's explicit go-ahead**, per
the freeze. Undo must rewind the defenders' queued replay cards one step too; Claim needs an
acceptance rule (simplest: enable only when every remaining declarer-side card is high by
rank, else keep the button disabled).

---

## How the coaching content is authored  *(FYI — reusable if you want it)*

The lessons aren't written board by board. The `{...}` coaching prose is generated by
**Claude subagents following a fixed authoring spec**, then mechanically spliced into the
PBN — so the voice stays consistent and the volume is feasible. If you ever want to author
or extend lessons the same way (for Baker Bridge or anything else), the whole pipeline lives
in the PBS repo and is yours to reuse:

- **Authoring spec — bidding:** [`coaching-curated/GENERATOR.md`](https://github.com/ADavidBailey/Practice-Bidding-Scenarios/blob/main/coaching-curated/GENERATOR.md)
  — the rules a subagent follows: the token-free South-fixed format, the `⟦ ⟧` brackets the
  feedback fade reads, and the structure discipline that makes `[ACCEPT]` work.
- **Authoring spec — play:** [`coaching-curated/GENERATOR-PLAY.md`](https://github.com/ADavidBailey/Practice-Bidding-Scenarios/blob/main/coaching-curated/GENERATOR-PLAY.md)
  — the same, for card-play lessons.
- **Orchestration:** [`.claude/skills/coach-lesson/SKILL.md`](https://github.com/ADavidBailey/Practice-Bidding-Scenarios/blob/main/.claude/skills/coach-lesson/SKILL.md)
  — the `/coach-lesson <Scenario>` skill that runs the full pass (curate → author → gate → resolve).
- **Mechanical steps:** [`py/coach.py`](https://github.com/ADavidBailey/Practice-Bidding-Scenarios/blob/main/py/coach.py)
  — selects boards into per-chunk packets, splices the subagents' prose back into the PBN, validates.

The flow in one line: `coach.py packets` builds packets → one Claude subagent per packet writes
prose per GENERATOR.md → `coach.py splice` writes the curated PBN → it's gated and resolved into
the served files the app reads. The spec files ARE the prompts — point Claude at them.

---

## Delivery plan — approval first, then our changes, then Rick's pull

**Nothing proceeds on Bridge Classroom without Rick's approval first.** No new BC code is
written, and nothing is merged upstream, until Rick signs off on this plan. (Part A is
already built on the fork from earlier work, but it stays unmerged behind this same gate.)

The order is:

**Step 1 — Rick approves the plan.** He reviews this document and approves the approach: the
folder migration, the A-items to merge, the B-fixes we'll build, and the PR delivery.

**Step 2 — We make the changes.** Only after approval:
- PBS side: Phase 1 prep (bring `coaching/` to parity — `toc.json` + the 8 defense sets,
  retarget scripts), pushed to PBS `main`.
- BC side: open **PRs from `ADavidBailey/Bridge-Classroom`**, grouped by risk:
  1. **Folder repoint (Part M, alone)** — the four-line path change; depends on PBS Phase 1.
  2. **Part A built features** — promote A1–A5 to PRs (one per feature or sensible grouping).
  3. **Small Part B fixes** — B1, B2, B6 (and B5 if David wants it).
  4. **B3, B4** — requests only; no code from us.

**Step 3 — Rick pulls.** He reviews and merges the PRs into his upstream.

**Step 4 — Cleanup.** Once the repoint is merged and BC is confirmed loading from
`coaching/`, delete `coaching-non-rotated/` from PBS.

**Merge-order caution — `src/views/MainLayout.vue` is the hot file.** It is touched by the
repoint and by B2, B6, A1, A2, A3, and A4. Separate PRs will conflict there, so they need a
defined merge order (or some grouping). This is the main reason not to split too finely.

## How to use this draft
David reviews; once approved, deliver to Rick for **his** approval (Step 1). Our BC changes
(Step 2) begin only after Rick signs off.
