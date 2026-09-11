# Bridge Classroom Integration Plan

> **STATUS — SHIPPED 2026-06-28 (header added 2026-06-29).** This doc is now a historical
> record; the plan is executed and waiting on Rick.
> - **Track A (deliverable): DONE.** `[ACCEPT]` parse+score+per-collection scoping implemented
>   on the `fork` branch `accept-and-lesson-sync`; 46 lessons + full toc live on PBS main;
>   email sent to Rick 2026-06-28. Awaiting his pull.
> - **Track B (token sweep): DONE.** The "19 still tokenized" list below is **OBSOLETE** —
>   verified 2026-06-29 that **zero** rotation tokens remain in `coaching-non-rotated/` (all 46)
>   or `coaching-curated/`.
> - **Still on Rick's side:** Drury reconcile, id→skillPath mapping, Baker Bridge non-disruption
>   verify, the separate `[showcards]` parser bug. Optional possessive collection rename lives in
>   `bridge-classroom-requests-for-rick.md`, not here.

**Goal:** get our PBS coaching lessons (and the one engine change they need) working
**on David's BC fork**, verify Rick's existing app is unaffected, then have Rick **pull
everything** into his repo. Drafted 2026-06-28 to seed a clean implementation session +
the email to Rick.

**Flow:** everything working here → Rick tests & verifies (his live use unaffected) →
Rick pulls.

---

## Repos & mechanics (no action needed from David)

- **PBS** (`~/Practice-Bidding-Scenarios`, `ADavidBailey/Practice-Bidding-Scenarios`) —
  our content + pipeline. Source of truth for lessons.
- **BC engine** (`~/Bridge-Classroom`): two remotes —
  - `origin` = `Rick-Wilson/Bridge-Classroom` — Rick's repo, **push-disabled for us**
    (we literally cannot disrupt it).
  - `fork` = `ADavidBailey/Bridge-Classroom` — David's fork; **all our changes ride
    here**, on a branch. Prior work (Part A, report button / fades) already lives here.
- Hand-off = Rick **pulls our fork upstream** when he's satisfied. We never push to his repo.
- BC **bundles its own lesson data** (`public/data` + `bridge-classroom-api/seed_data` →
  built into `dist/data`); it does NOT live-read PBS. So integration is a **content copy**,
  not a runtime pointer.

## What BC has today

- Only **5 bundled lessons** (Cue-bid, Establishment, OLead, Squeeze, Drury) — mostly card-play.
- `public/data/skillPaths.json` already **names most of our conventions as planned slots**
  (blackwood, jacoby_2nt_splinters, new_minor_forcing, fourth_suit_forcing, reverse_bids,
  roman_keycard, ogust, preempts, …) — structure defined, **content missing**. Our 46
  lessons largely *fill* these slots → integration is mostly **additive**, not conflicting.
- His lessons are **token-free** (matches our retired-token format) and use markers
  `[show]`, `[showcards]`, `[BID]`, `[choose-card]`, `[NEXT]` — **all of which our lessons
  use and his parser already handles.**

## The ONE engine gap: `[ACCEPT]`

`[ACCEPT]` is **not implemented** — only a comment in `src/views/MainLayout.vue`:
*"Judgement boards ([ACCEPT]) are a later slice."* Bid scoring is single-answer.

- **Impact:** our **textbook/mechanical** bidding boards (one correct call) drop in clean.
  Our **judgment** boards (a defensible alternative marked also-correct) would score the
  alternative WRONG until `[ACCEPT]` exists. Also, since `[ACCEPT]` isn't a recognized tag,
  it currently leaks into displayed text.
- **Fix (additive, non-disruptive — lessons without `[ACCEPT]` behave identically):**
  1. **Parse** — `src/utils/pbnParser.js`, `parseUnifiedSteps` (~line 164-228): recognize
     `[ACCEPT <call>]`, extract the call(s) from the bid chunk's prompt+explanation into
     `acceptedBids: [...]` on the `type:'bid'` step, and **strip** the marker from the
     displayed text.
  2. **Score** — `src/composables/useDealPractice.js`, `makeBid` (~line 493): change
     `isCorrect` from `normalizeBid(bid) === normalizeBid(expectedBid)` to ALSO accept when
     `bid` is in the step's `acceptedBids`. (Auction still advances on the canonical
     recorded call.)
  3. **Test** — add a vitest case in `src/utils/__tests__/pbnParser.test.js` (parse) and a
     scoring case; a lesson WITH `[ACCEPT]` scores both calls correct, one WITHOUT is
     unchanged.

## Work plan — ONE clean session, unhurried (no Cowork needed)

**Timing (revised 2026-06-28):** Rick is at a bridge tournament and will NOT start tonight,
so there is **no tonight deadline**. Do the work at a measured pace in a **single clean
session**; Cowork/parallelism was only justified by the (now-gone) deadline. The two tracks
below are independent (different repos, zero shared files), so order is flexible — do Track A
(the real deliverable) first, then Track B. Have everything **working + verified and waiting**;
email Rick **after his tournament**, when he's free.

**Key fact:** the BC integration does NOT depend on the PBS sweep. BC reads
`coaching-non-rotated/`, already token-free for all 46 lessons; the sweep only cleans
`curated/`+`served/`, which BC never reads.

### Track A — BC fork (the deliverable)
Work in `~/Bridge-Classroom` on a **new branch off the fork**. **Never push `origin`** (Rick's).
1. **Implement `[ACCEPT]`** — the parse + score edits in §"The ONE engine gap" + vitest tests.
2. **Content-sync** — copy all 46 `coaching-non-rotated/*.pbn` into BC's data dir; write a
   **one-way sync script** (PBS `coaching-non-rotated/` → BC data + `skillPaths` entries) so
   PBS stays source of truth and Rick rebuilds from it.
3. **Index mapping** — our `toc.json` ids → his `skillPaths.json` slots; list his slots we
   don't cover and our lessons with no slot.
4. **Reconcile Drury** — his bundled Drury differs from ours; pick one (likely ours; Rick's call).
5. **Verify NON-DISRUPTION (gate — all must pass before David emails Rick):**
   - his **vitest suite** green; his **5 existing lessons** render unchanged;
   - **Baker Bridge** (Rick's own lesson series; PBNs on his github) renders identically
     before & after our changes;
   - our lessons render AND score (incl. an `[ACCEPT]` judgment board).
6. **Signal David** "working + verified" → he sends Rick the actionable email **after the
   tournament** (no tonight rush).

### Track B — PBS (parallel hygiene; does NOT gate Rick)
**Finish the token-free sweep** — 19 lessons still tokenized (3N_Rebid_by_Opener, Basic_* ×6,
Fourth_Suit_Forcing, Negative_Double, New_Minor_Forcing, Responsive_Double, Reverse_By_Opener,
Slam_after_Stayman_or_Jacoby_w30plus, Smolen, Spiral_Raises_×2, Stayman, Texas_Transfer).
Method: **regenerate-then-collapse** (refresh each `coaching-non-rotated/` from current curated,
then copy over curated+served) so nothing reverts to a stale version. (7 already done: Gerber +
6 keycard lessons, commit 27c9f5c1d.) Coordinate with any active PBS Cowork session.

## Open items / decisions

- **Baker Bridge** — Rick's OWN lesson series (his analog to "David Bailey's"); PBN files
  live on Rick's github (exact repo/path TBD — the verifying session can also just exercise
  whatever BC presents in its UI). Non-disruption check: render the Baker Bridge lessons
  before & after our changes, confirm identical. Expected safe by construction (`[ACCEPT]`
  only affects boards using it; content-sync only adds our files).
- **id→skillPath mapping** — exact table (step 4).
- **Drury** — his vs ours (step 5).
- Whether the sync script also handles the defense/play sets (they're already token-free,
  byte-identical curated==non-rotated).
- Known `[showcards]` parser bug (separate from `[ACCEPT]`) — affects play/defense sets;
  track for Rick.

## For the clean session — one session, Track A then Track B

Start a single clean session from this doc; do Track A (BC fork) first, then Track B (PBS
sweep). No tonight rush — Rick is at a tournament. Paste-able opening prompt:

> Execute `bridge-classroom-integration-plan.md` (in ~/Practice-Bidding-Scenarios). Do Track A
> first: work in ~/Bridge-Classroom on a new branch off the `fork` remote — NEVER push
> `origin` (Rick's repo). Implement `[ACCEPT]` (parse in src/utils/pbnParser.js, score in
> src/composables/useDealPractice.js makeBid ~L493) + vitest tests; run the full vitest suite
> and confirm his 5 bundled lessons + Baker Bridge [David will give you what this is] still
> work. Then content-sync all 46 coaching-non-rotated/*.pbn into BC's data, map them into
> skillPaths.json, reconcile Drury. Then do Track B, the PBS token sweep. No tonight rush —
> Rick is at a tournament; stop and report when Track A is working + verified.
