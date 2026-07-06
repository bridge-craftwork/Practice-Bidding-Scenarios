# CLAUDE.md — `coaching-non-rotated/` (the Bridge-Classroom-served collection)

**Scope:** this file is *additive* to the root [`../CLAUDE.md`](../CLAUDE.md).
The root describes the whole PBS pipeline; this file adds the obligations that
apply specifically because Bridge Classroom serves the PBNs in **this folder** to
students. Read the root first; nothing here overrides it.

## What this folder is

`coaching-non-rotated/` is the **terminal, Bridge-Classroom-served collection**.
Bridge Classroom fetches these files at runtime from
`raw.githubusercontent.com/bridge-craftwork/Practice-Bidding-Scenarios/main/coaching-non-rotated/`
(BC's `COLLECTIONS[]` config, slug `pbs-coaching`). It is distinct from:

- `coaching-curated/` — the **staging/authoring** source (rotation-tokenized).
- `coaching/` — served to the **AI-Bridge-Play-Trainer**, not to Bridge Classroom.

These files are **generated, not hand-authored**. The pipeline is:

```
coaching-curated/<scn>.pbn   (author here; gates run here)
   │  py/nonrotate.py <scn>          resolve tokens → South=student, fold partner
   ▼
coaching-non-rotated/<scn>.pbn
   │  py/bridge_classroom.py <scn>   strip pre-auction blocks, renumber 1..n,
   ▼                                 add [OriginalBoard], add [show S]
coaching-non-rotated/<scn>.pbn   ← what BC fetches
```

Board-level PBN tags authored in `coaching-curated/` **flow through** both steps
into the served file (e.g. `[SkillPath]` already does). So author the release
tags upstream in staging; only the derived `[BoardVersionToken]` is stamped as a
build step over the final files here (see below).

## The producer contract (authoritative sources)

Bridge Classroom keys student mastery to a board's **position**, not its content.
The full obligations live in the Bridge-Classroom repo — these are normative and
win over any summary here:

- Producer contract: https://github.com/bridge-craftwork/Bridge-Classroom/blob/main/documentation/adr/collection-producer-contract.md
- Companion spec (contracts C1–C7): https://github.com/bridge-craftwork/Bridge-Classroom/blob/main/documentation/adr/board-identity-and-history-integrity.md
- ADR-0001 (the decision): https://github.com/bridge-craftwork/Bridge-Classroom/blob/main/documentation/adr/0001-positional-board-identity.md

Accepted 2026-07-06 (Rick + David). Changes require both sides' agreement.

## The four obligations (R1–R4)

### R1 — Declare release status with the `stable` flag

Two scopes, PBN carriers:

| Scope | Carrier | Meaning |
|---|---|---|
| **File** | `%bridge-classroom-stable: true` \| `false` — a `%` comment line at the **very top of the file**, above the first `[Event]` | default `stable` for every board in the file |
| **Board** | `[Stable "true"]` \| `[Stable "false"]` — a board tag | overrides the file default for that one board |

**Absent ⇒ not stable (prerelease).** This is the safe default: a prerelease
board is fully playable and kept in the student's *private* history, but is
**excluded from mastery/platform stats and cannot be assigned into an exercise**.
Forgetting the flag only ever *withholds* content — it never lets beta content
silently reach mastery. So only set `stable=true` on **vetted** boards.

### R2 — Once stable, freeze the position

Mastery is keyed to `(collection, subfolder/lesson, board number)`. Once a board
is `stable`:

- **Do not renumber it.** Board 5 stays board 5. Renumbering a *stable* lesson
  needs explicit coordination with Bridge Classroom first — it is not a routine
  edit. (Before promotion, prerelease sets may be reordered/regenerated freely.)
- **Editing in place is fine** — history survives revisions (observations are
  self-contained on BC's side; no edit of ours ever mutates student data).
- **A replacement must occupy the same position, be itself `stable=true`, and
  match difficulty.** Never swap a prerelease board into a promoted position —
  that would silently drop the student work recorded there. Lessons are ordered
  easy → hard, so a replacement should be about as hard as what it replaced.

### R3 — Stamp a board-version token on every board

`[BoardVersionToken "…"]`, derived by the build (never hand-maintained,
recomputed each build):

- **Value:** rotation-canonical content hash. Compute the rotation `k` that moves
  the **♠A holder to North**, apply it to **both the hands and the auction**
  (calls keep order; dealer and seat labels shift by `k`), then
  `sha256( normalize(canonical_deal) + "|" + normalize(canonical_auction) )`,
  **lowercase hex**, over the *extracted* values (not raw file bytes, so cosmetic
  reformatting doesn't churn it). Every deal has exactly one ♠A, so `k` is
  well-defined; every rotation of the same deal+auction maps to one token.
- **BC treats it as opaque** — it records the token and echoes it into "Report a
  Problem" but never computes, verifies, or compares it. There is exactly one
  implementation of the scheme (ours). It is *evidence, not enforcement*: the real
  guarantee is R2's freeze rule, not the token.
- The build should **warn** when a *stable* board's token changes, so
  post-promotion edits are deliberate.

> Not yet implemented. See the "Build step still to do" note below. Do **not**
> confuse the token with the existing `% <28-uppercase-hex>` provenance comment,
> which is a BBA fingerprint (`sha1[:28]`), unrelated to this contract.

### R4 — Every stable board carries a real skill path

`[SkillPath "…"]`. **`uncategorized` is allowed only while a board is
prerelease.** The requirement binds *at promotion*: assign a real path **before**
setting `stable=true` (skill path feeds only mastery, from which prerelease is
already excluded). Mint new paths as needed.

## Do NOT put these in the PBN (Bridge Classroom owns them)

- the **`collection` id** (`pbs-coaching`) — BC sources it from its own config;
- the **`report`-button flag** — a BC-side, collection-level switch;
- the **`prerelease`** column — BC's consumer-side inverse of your `stable` flag.

(An older repo doc, [`../deal-hash-identity-plan.md`](../deal-hash-identity-plan.md),
proposed a `[Collection]` tag and the names `[Ready]`/`[DealHash]`. Those are
superseded by this contract: no `[Collection]`; `[Ready]` → `%bridge-classroom-stable:`
+ `[Stable]`; `[DealHash]` → `[BoardVersionToken]`.)

## Promotion checklist (what "promote a board to `stable`" requires)

Before any board here is set `stable=true`, it **must** carry:

1. a real `[SkillPath "…"]` (no `uncategorized`), **and**
2. a stamped `[BoardVersionToken "…"]` from the build.

Then set `%bridge-classroom-stable: true` (or per-board `[Stable "true"]`), and
**from then on treat that position as frozen** (R2). Replacements are
same-position, `stable=true`, similar difficulty.

## Build step still to do (follow-up)

Token stamping (R3) and back-stamping the existing served files, plus wiring
`%bridge-classroom-stable:` / `[SkillPath]` defaults through the
`nonrotate.py` → `bridge_classroom.py` seam, is a **new build step** not yet
built. Until it lands, boards here remain **prerelease by default** (safe: they
are playable and kept in private history, excluded from mastery). Do not flip any
board to `stable=true` until R3 + R4 are satisfied for it.
