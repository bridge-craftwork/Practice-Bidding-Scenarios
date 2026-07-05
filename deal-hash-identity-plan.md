# Plan: migrate Bridge Classroom mastery from position-based deal IDs to content-hash IDs

## Context

Bridge Classroom (BC) tracks per-student mastery of individual boards (spaced
repetition: yellow → orange → green → silver → gold → "mastered in the wild").
Today BC's database identifies a board by **position** — `(Lesson Collection,
Lesson Name, board number 1..n)` — confirmed by Rick ("The database identifies
specific deals by Lesson Collection, Lesson Name, and board ID (1..n)", 2026-07-02).

Position keying is fragile the moment a set is curated: dropping a bad board and
backfilling another **re-points every student's record for that slot at a deal
they never practiced**, and any renumber shifts the whole tail. This is not
hypothetical — the **Report-a-Problem button guarantees it**: reports will retire
bad deals and pull in replacements as a routine event. Under position keying,
every such action risks corrupting earned mastery.

The fix is to make board identity **intrinsic to the deal**: key records on
`deal_hash(served [Deal])` instead of board position. Then drop / backfill /
reorder are all safe by construction — a record follows the deal's *content*, so
a dropped deal's history goes dormant, a backfilled deal starts clean, and the
served order is free to change.

**The unlock for Rick:** we do **not** discard existing records. Because his
tracked sets are **static** (frozen since students began — David's read, Rick to
confirm), position N of a lesson is the same deal for every student across all
time, so we can remap the entire existing mastery table **losslessly** in one
pass. Mastery is per-student, so the remap covers the whole cross-student history
table — but the student id, timestamps, and star levels ride along untouched;
only the board-identity component of the key changes.

Goal: (1) migrate the currently-live, static sets from position IDs to hash IDs
without losing any student history, and (2) make hash-based identity the standing
scheme so all future curation is non-destructive.

## Ownership seam (who does what)

- **PBS (David — executable now):** agree/normalize the one canonical `deal_hash`;
  stamp it on every served board going forward; run the one-time remap for David's
  own collection (`pbs-coaching` / David Bailey Scenarios).
- **BC (Rick — needs his OK; under the BC freeze):** everything touching the BC
  database and engine — add the hash column, run the remap over **Baker Bridge**
  (his content, his served files, his DB), and switch record keying + reads from
  position to hash. **Nothing lands in BC without Rick's approval.** Baker Bridge
  content is not in the PBS repo, so its remap runs on Rick's side.

The shared artifact between us is **one agreed hash function**, not a data file:
each collection owner runs the same remap logic against the served version they
actually deploy. Running it *in place* against deployed files means the map is
automatically pinned to the version students practiced — no cross-repo version
drift to reconcile.

## The canonical hash (decision)

Use the function that already exists and that the entire PBS pipeline already keys
on internally: `deal_hash = sha1(seated [Deal] string)[:16]`, lowercase
([`py/curate.py:102`](py/curate.py:102)). It is computed on the **served**
`[Deal]` — i.e. after rotation is baked into the file (rotation happens in the
files, never at the table), so there is exactly one deal string per board and its
hash is deterministic per load.

Normalize the three fingerprint variants that exist today so "the hash" means one
thing everywhere:
- [`py/curate.py:102`](py/curate.py:102) — `sha1[:16]` lower  ← **canonical, keep**
- [`py/rotate180.py:46`](py/rotate180.py:46) — `sha1[:28]` upper (the `%` line)
- BBA's own 28-char `%` fingerprint on originals (not a sha1 of the deal string)

The `%` comment line stays as BBA/rotate provenance; it is **not** the identity.
Identity is the canonical `deal_hash`.

## Phase 1 — agree + stamp going forward (PBS, David)

1. Lock `deal_hash` (above) as the canonical board id. One shared definition Rick
   can reproduce byte-for-byte on his side.
2. Stamp it on every served board at the **final, post-rotation** stage
   ([`py/bridge_classroom.py`](py/bridge_classroom.py) `_renumber`, which already
   makes the last in-place pass over `coaching-non-rotated/`). Write an explicit
   **`[DealHash "<16hex>"]`** tag per board — parser-visible so BC reads the id
   directly instead of recomputing, greppable, and it does not collide with the
   `%` provenance line or `rotate180`'s `%` regex. (Alternative considered:
   overload the `%` line — rejected; it changes BBA's provenance semantics and
   format.)
3. Make stamping **idempotent** (only add if absent) and cover the sets that
   currently bypass stamping entirely — the `cp`-synced `Basic_*` defense sets and
   any raw boards (today ~16% of `coaching-non-rotated/` boards carry no fingerprint
   at all). Stamping is additive metadata: the `[Deal]` bytes do not change, so no
   board identity moves under either key.
4. Do the same for `coaching/` (the trainer-served copy) for consistency.

## Phase 2 — one-time lossless remap of live records (each collection owner)

Run *in place* against the currently-deployed served files, so the version is
automatically the one students practiced.

For each existing mastery record keyed `(collection, lesson, board N)`:
1. Open the served file for `(collection, lesson)`, read the `[Deal]` at board N.
2. Compute `deal_hash`.
3. Write it into the record's new `deal_hash` key; **student id, timestamps, and
   star/mastery state are copied verbatim** — only the board-identity component
   changes.

The `(collection, lesson, N) → deal_hash` lookup is **student-independent** (a
static lesson serves the same board N to everyone), so one derivation remaps all
of a slot's rows across the entire student body.

- **Baker Bridge:** Rick runs this over his served files + DB.
- **pbs-coaching:** David runs the identical logic over the deployed PBS served
  files once BC is ready to consume the hash.

## Phase 3 — flip BC keying to the hash (Rick, needs OK)

BC-side engine change, sequenced so it is verifiable and reversible:
1. Add a `deal_hash` column to the records/exercises tables (nullable at first).
2. **Backfill** via Phase 2 while BC is still keying on position (dual state —
   both keys present, nothing switched yet).
3. **Verify** (below) that every existing record now carries a hash and counts
   reconcile.
4. **Flip** the record key + all reads
   (`useStudentProgress.js` / `useLearningProgress.js` / `useBoardMastery.js`,
   which today key on `${deal_subfolder}|${deal_number}`) from position to
   `deal_hash`.
5. `board_number` survives only as **display/order**, no longer as identity. The
   loader reads the stamped `[DealHash]` from the served file.

Rick's call, not ours: whether the record key is `deal_hash` alone (which makes
"mastered in the wild" — the same deal recognized out of context — fall out for
free, since the same deal is the same key in any lesson or random set) or a
composite `(collection, deal_hash)`.

## Phase 4 — report-driven curation is now safe (outcome)

With identity on the hash, `/issue` triage acting on a Report-a-Problem report can
drop a bad deal and backfill from the pool, and reorder freely:
- dropped deal's hash → its student records go dormant (never mis-bound);
- backfilled deal's hash → starts with a clean record;
- reorder → irrelevant to records.

The freeze discipline still governs *how often* (a dropped board a student already
gold-starred is a real loss of their investment even though nothing is corrupted),
but correctness is guaranteed.

## Verification

- **Backfill completeness:** after Phase 3.2, every position-keyed record resolves
  to a non-null `deal_hash`. Any record whose `(collection, lesson, N)` has no
  current-file match (deal since removed/changed) is **flagged, never dropped** —
  Rick decides its disposition.
- **No intra-lesson collisions:** each board's `deal_hash` is unique within a
  lesson (the duplicate detector in [`py/curate.py`](py/curate.py) already exists;
  reuse it as a pre-flight over every served lesson).
- **Row-count parity:** student × board × visit row counts identical before and
  after the remap.
- **Stamp coverage (Phase 1):** every board in `coaching-non-rotated/` and
  `coaching/` carries a `[DealHash]`; re-run and diff to confirm idempotence and
  zero gaps (close the current ~16% hole).
- **Round-trip:** BC-parsed `dealString` hashed on the fly == the stamped
  `[DealHash]` == the internal pipeline's `deal_hash`, for a sample of boards.

## Risks / prerequisites

- **Static-set assumption.** Lossless only for lessons unedited since the first
  student record. David's read: Rick's tracked sets are static; Rick confirms per
  lesson from his edit history. Any mid-history-edited lesson can't be
  disentangled after the fact (position keying already merged old/new occupants of
  the slot) — bind to the current deal or leave it position-keyed, Rick's call.
- **Version pinning** is handled by running the remap *in place* on deployed files.
- **BC freeze / Baker Bridge.** All Phase 3 work and the Baker Bridge remap are
  Rick's; this plan is a proposal to him. Don't break Baker Bridge.

## Immediate next step (PBS-side, no BC dependency)

Send Rick the coordination email (drafted, awaiting David's OK): his stability /
mastery frame first → the one yes/no (key records on `deal_hash`, or stay on
position?) → the two safety points (stamping doesn't change deals; the hash makes
error-fixes non-destructive) → the closer (existing student history is **preserved
via a one-time lossless remap** of the static sets, not discarded). Phase 1
stamping is independently executable on the PBS side whenever David wants to start.
