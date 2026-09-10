# Bridge Classroom — Changes (completed & proposed)

Running log of changes to the **Bridge Classroom app/engine** (the fork at
`~/Bridge-Classroom`). Scope here is the **engine/app**. Coaching **content** —
PBS decks, prose, board selection — is tracked in PBS git history, **not** here.
Keep it straight: **engine = the BC fork**; **content = PBS**.

**David's directive (2026-06-27): keep BC engine changes MINIMAL for now.** Work
within what BC already does. New engine ideas accumulate in the parking lot below
to weigh later instead of being built now.

> **Rick-facing version:** the precise, cold-readable change requests for Rick live in
> [`bridge-classroom-requests-for-rick.md`](../bridge-classroom-requests-for-rick.md)
> (Part A = built-on-fork → merge; Part B = build/fix). Keep the two in sync.

---

## Completed (built on David's fork — NOT yet merged upstream)

*Verified 2026-06-27 against `~/Bridge-Classroom`: all on `main`, **18 commits ahead of
Rick's `origin/main`**, and pushed to David's `fork/main`. "Built" = committed/pushed to
**David's fork only** — not in Rick's upstream, not in any prod Rick runs. Fork-only
until/unless PR'd to Rick.*

- **`[ACCEPT]` judgment-call scoring.** *(Added 2026-06-28. On its own branch
  `accept-and-lesson-sync` off `fork/main` — **local, NOT pushed**, 2 commits ahead:
  `6259eb0` impl, `f0aee3c` test.)* A judgment board can mark a second defensible call
  as also-correct with an inline `[ACCEPT <call>]`. Before, BC scored the alternate
  wrong and leaked the tag as raw text. Now `pbnParser.js` extracts it into the bid
  step's `acceptedBids` (and strips the marker) and `useDealPractice.js` `makeBid`
  scores correct on the recorded call OR any accepted call; the auction still advances
  on the recorded call. Additive — lessons without `[ACCEPT]` are byte-identical. 10
  vitest cases (incl. a real folded board); full suite shows no new failures vs
  `fork/main`. Pairs with the PBS-side change that lets the marker reach BC (PBS content,
  tracked in PBS git — see `feedback_accept_marker_works_in_bc`).
- **Report-a-Problem button.** `ReportProblemModal.vue` + `useReportProblem.js`; endpoint
  configurable via `VITE_REPORT_URL`. Has a real **Rust API route**
  (`bridge-classroom-api/src/routes/reports.rs`) *and* works against the local report-relay
  (the relay + `.env.local` are the gitignored, local-only pieces). Button sits beside the
  bidding box; popup is draggable. Issues land as `classroom-feedback` in PBS → `/issue` flow.
  **Now opt-in per collection** (`07b618a`, branch `accept-and-lesson-sync`): shown only for a
  collection with `report: true` (David Bailey on; Baker Bridge off), since a report files an
  issue in that collection's content repo. Keeps Baker-Bridge problems out of David's repo.
- **Scenario @chat popup.** `ScenarioChatPopup.vue` — sizable, movable popup showing the
  scenario's chat/teaching blurb; shown in Bidding Practice **and** coaching lessons; reopen
  button labeled "Description".
- **Coaching-feedback fade (BIDS).** Three-mode bid feedback: correct call → brief *varied*
  affirmation + the partner/opponent follow; wrong call → full explanation; reads the `⟦ ⟧`
  the generator wraps around the student's justification. Adds a **board-level cheer**
  (Bravo!/Perfect!) when every call on a board was right. *This is the bid analog of proposed
  item 1; the per-CARD (lead/play) version is still open.*
- **Coaching layout.** Left-align the table during practice with the chat open on the right;
  re-center on close; cap coaching-text height to the window so the bid box stays in view.
- **Local-run launcher.** *(Local dev convenience, not a fork commit.)* Desktop
  `Bridge Classroom.command` → Vite dev server + report-relay, opens to the David Bailey
  Scenarios page.

---

## Proposed / parking lot (not scheduled — nothing here is built until David moves it out)

1. **Per-card wrong feedback (3-tier).** Today a wrong lead says the same thing no matter
   which card you picked. Respond to the *actual* choice — correct (terse nod) / reasonable
   ("good thought, but…") / wrong (full why) — with length fading by correctness.
   *Raised 2026-06-27 reviewing Major-LHO. See `project_coaching_feedback_fade`.*
   **Note:** the **bid** version of this fade is already built on the fork (see Completed →
   Coaching-feedback fade). This item is the still-open **per-card (lead/play)** analog.

2. **Full defender play-out with revert-and-correct.** Let the student defend the WHOLE
   hand card-by-card (not just the opening lead); a mis-play is reverted and the correct
   card substituted, then play continues — the declarer-play model applied to a defender
   (South). *Cowork produced a build-ready handoff spec on branch
   `defender-playout-investigation` in `~/Bridge-Classroom` — ready to build when chosen.*

3. **Revisit state (NOT a bug).** Returning to a completed deal RESETS it to the start —
   your hand shown, ready to lead again: a clean re-try. Reasonable as-is. FUTURE nicety:
   optionally *remember* the previous lead + result instead of resetting. *Confirmed
   behavior 2026-06-27 (David).*

4. **Cosmetic affirmation verb.** On a lead lesson BC says "Beautifully bid!" — should read
   "Well led!" (correct verb per lesson type).

5. **`[showcards]` multi-seat parser bug.** *(Found 2026-06-27.)* A tag naming two seats —
   `[showcards N:C4, E:CT]`, or the documented `E:S7,S:S5` form — is mis-parsed: the seat
   regex in `src/utils/pbnParser.js` (the `([NESW]):([^,\s]+(?:,[^,\s]+)*)` pattern, ~line
   342) greedily swallows `,E:CT` as a *second card of North*, so the second seat is lost.
   **Worked around in content** by putting a **space after the comma** (`N:C4, E:CT`), which
   breaks the greedy match. A proper one-line regex fix would make the documented multi-seat
   format work without the space. *Surfaced while making dummy "play" its card in the
   third-hand RHO defense sets.*

6. **Header title/greeting overlap (CSS).** *(Found 2026-06-27.)* On a long collection title
   (e.g. "…Bailey Scenarios - Third Hand vs Notrump") the title overprints the
   "Welcome back, David" greeting — the two render on top of each other. The title doesn't
   truncate or wrap before the greeting. Cosmetic only; fix with ellipsis-truncation or
   allowing the title to wrap. Affects any long title.

### From the 2026-06-29 classroom-feedback batch (logged, NOT filed with Rick per David)

7. **Multi-pass auctions surface only one student Pass.** *(Reports #142 Basic_Takeout_Double
   D5, #133 Basic_What_To_Open D12.)* When the scripted auction has the student (South) pass
   **more than once** — e.g. pass over an opponent's bid early, then pass again to end it —
   BC surfaces only the one authored `[BID Pass]`, and the reviewer reports "no chance to bid
   the 2nd pass." Content side: passes are deliberately not all anchored (the validate gate
   requires `[BID]` anchors only on **non-pass** calls). So either BC should let the student
   confirm every one of their turns in a scripted auction, or auto-completion should be
   visibly clear. Engine behavior call — parked.

8. **Bidding lessons don't reveal all four hands at the end.** *(Report #138 Basic_Overcall
   D8: "why do the Overcalls not show all four hands at the conclusion?")* Bidding reflections
   use `[show NS]` — bid-meaning only, no opponent/partner hands — **by design** (the
   partner-hand-exposure gate forbids reciting partner's cards in a reflection). Showing all
   four hands at auction-end would be a deliberate philosophy change for bidding lessons (play
   lessons already use `[show NESW]`). Design call for David — parked, not a bug.

9. **Declarer-play decks aren't playable card-by-card.** *(Report #141 Play_Top_Tricks D3:
   "How does one play the hand?")* Play_Top_Tricks teaches the **play**, but BC supports
   bidding + opening lead, not full declarer card-play, so the student sees the coaching but
   can't play it out. Same root as parking-lot **item 2** (full play-out). Known engine
   limitation — parked.

10. **`[ACCEPT]` over-credits the alternative — now a precise engine request (B7).** *(Report
    #140 Basic_Weak_2 D6.)* The board records **Pass** as correct over the opponents' 4♥; the
    reviewer bid **4♠** and was scored wrong. Two wrong turns before landing it:
    (a) the original triage claimed `[ACCEPT]` can't attach to a `[BID Pass]` host — **false**
    (`pbnParser.js` ~227 attaches `acceptedBids` with no host condition; `useDealPractice.js`
    `makeBid` ~497 scores `expectedBid OR any acceptedBid`, no Pass casing). So `[ACCEPT 4S]`
    *did* score 4♠ correct.
    (b) but that exposed the real problem: `[ACCEPT]` is **binary** — it scores the alternative
    fully correct, **hides** the student's actual call behind the recorded one, and fires the
    "Beautifully bid!" cheer. David: that's wrong; a non-recorded call must be **reverted**
    (you can't know it ends the auction — an opponent could bid over it), shown as an **orange**
    strike-out "acceptable alternative" (red stays wrong), never standing in the auction.
    **Resolution:** `[ACCEPT 4S]` was **reverted**, the board's reflection softened to commit to
    Pass (so a wrong 4♠ isn't called "defensible" in the interim), and the orange-tier behavior
    is filed as **B7** in `bridge-classroom-requests-for-rick.md` for Rick. #140 stays open until
    B7 ships.

---

## How to use this file

Add new BC engine changes here — **Completed** when shipped, **Proposed** when raised.
Nothing in the parking lot gets built until David explicitly moves it out.
