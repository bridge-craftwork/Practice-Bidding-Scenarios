# Explain the Table — coaching auction-annotation plan

**Status:** design locked 2026-07-20 (David). Pilot: the 7 beginner bidding lessons.

## Goal
Every **bidding** coaching lesson should let the student read the *whole* auction. The
meaning of every **non-student call** — partner's *and* the opponents' — is explained, so
the student never has to guess what the other calls meant. The student still makes every
decision themselves.

## Principle — explain, don't direct
At every point the student must act on a **secondary** call, the prose says **only what the
other players' calls mean**. It never:
- tells the student their action ("you pass"),
- evaluates the student's own hand ("with a minimum opening"),
- announces the result ("2♥ is the final contract").

The student reads the auction and arrives at the call unaided.

## Scope of the principle
- Applies to **secondary calls only** — every call other than the student's **primary
  teaching bid**.
- The **primary teaching bid** (the lesson's whole point — the opening in *What Should I
  Open?*, the response in *How to Respond*, etc.) keeps its existing teaching prose; it may
  evaluate the hand and name the call, because that *is* the lesson. [decided 2026-07-20]

## Where the text lives — content only (no engine change)
Fold the explanation of secondary calls into the student decision step that follows them
(`[BID X]` / `[BID Pass]` markers), covering **every non-student call since the student's
previous turn**. This needs no Bridge Classroom engine change (Fork A).

## What each explanation says
- Describe the call's **standard meaning** (what it *shows*), never the actual hidden hand —
  e.g. "Partner's 2♥ is a simple raise — a heart fit and about 6–9 points."
- Cover partner's calls *and* opponents' calls (overcalls, doubles, runouts).
- Verify against the auction context + the board's `{Curate}` bidding-note + `[show NESW]`
  reflection before writing.

## Fade — per lesson, by thirds
Boards are ordered easy→hard. For a lesson of N boards, board i (1-based) is
`tier = floor(3·(i−1)/N)` → 0/1/2:
- **T1 (first third)** — full clause per secondary call.
- **T2 (middle third)** — terse clause per call.
- **T3 (last third)** — short **tag** only, and only for calls **not** already explained
  several times earlier in this lesson; routine repeats (e.g. the Nth simple raise) drop.
  This is a **terse floor, never a hard zero** — a genuinely new / competitive /
  first-in-lesson call still gets a tag even on the last board.
- The fade **resets per lesson** (each lesson re-teaches its own auctions).

### One step, three tiers (the 2♥-raise example)
| Tier | Reads |
|--|--|
| T1 | "Partner's 2♥ is a simple raise — a heart fit and about 6–9 points." |
| T2 | "Partner's 2♥ — a simple raise." |
| T3 | "2♥: raise."  (dropped if simple raises already shown several times earlier) |

## Execution
1. **Pilot — 7 beginner bidding lessons:** Basic_What_To_Open, Basic_Minor, Basic_Major,
   Basic_NT, Basic_Overcall, Basic_Takeout_Double, Basic_Weak_2. (Basic_Responses,
   Basic_Openers_Rebid, Open_and_Rebid, 1N_Balanced_Raise have no bare secondary pass-steps
   — check each for any intervening other-call glosses.)
2. Per lesson: author → `py/coach.py validate` + `py/suit_quality.py` → rebuild
   (`nonrotate.py`, `bridge_classroom.py`) → review diff → push (BC serves from main).
3. **Roll out** to the remaining bidding lessons (Notrump Sequences, Minor/Major Sequences,
   competitive sets, …) in batches.
