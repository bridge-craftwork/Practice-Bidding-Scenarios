# Plan: PBS producer obligations for board identity + readiness (reconciled with BC ADR-0001)

## Status

**Superseded/reconciled 2026-07-05.** The original version of this doc proposed
re-keying Bridge Classroom mastery on a content hash plus a one-time
position→hash remap. Rick's response — **[ADR-0001 + spec, PR #52](https://github.com/bridge-craftwork/Bridge-Classroom/pull/52)** —
declined the re-key and the remap, on a code-grounded correction we accept, and
adopted the stamped hash in a different role. This doc is now the **PBS
(producer) side** of that reconciled design: what we stamp and emit so BC can do
its part. BC's side is owned by ADR-0001.

## Why the re-key/remap is gone (the correction we accept)

Our plan assumed position keying corrupts history when a board is edited or
replaced — i.e. that a record resolves its deal by looking it up at that position.
**Rick verified in the BC code that this is false.** BC observations are
**self-contained**: each embeds the full deal it was played on (four hands,
auction, contract, cardplay), and the teacher drill-down renders from that stored
record, never re-fetching by board number. So changing a board later cannot
corrupt existing history — the misbinding we guarded against can't occur. No
re-key, therefore no remap. Board identity stays **positional**, extended by BC to
`(collection_id, deal_subfolder, deal_number)`.

The one conceptual consequence to keep in mind: mastery is **topic/slot-level**,
not deal-level. Replacing a board (same id, similar difficulty) lets the aggregate
"board N is mastered" indicator carry to the new deal; the detailed per-play
history stays pinned to what was actually played. That is BC's model (ADR-0001);
our obligation is just to honor the **same-id, similar-difficulty, no-renumber**
contract when we swap a board.

## The PBN contract — tag names we emit (proposed to Rick)

> **⚠️ Superseded by the accepted contract (2026-07-06).** The tag *names* below
> were a proposal; the finalized
> [Collection Producer Contract](https://github.com/bridge-craftwork/Bridge-Classroom/blob/main/documentation/adr/collection-producer-contract.md)
> changed three of the four. The durable, authoritative producer rules now live in
> the folder-scoped [`coaching-non-rotated/CLAUDE.md`](coaching-non-rotated/CLAUDE.md).
> The mapping:
>
> | This doc proposed | Accepted contract |
> |---|---|
> | `[Collection "…"]` | **dropped** — collection id is BC-owned; do **not** put it in the PBN |
> | `[Ready "true\|false"]` | `%bridge-classroom-stable: true\|false` (file) + `[Stable "…"]` (board); absent ⇒ not stable |
> | `[SkillPath "…"]` | unchanged |
> | `[DealHash "<16-hex>"]` | `[BoardVersionToken "…"]` — and the algorithm changed (see the token note below) |
>
> The rest of this section is retained as the historical proposal record.

BC's frontend slice is gated on these. All fit PBN's `[Tag "value"]` grammar and
the existing custom-tag precedent (`[OriginalBoard]`, `[BidSystemNS]`). PBN
value-inheritance (a tag carries forward until re-declared) gives file-level
defaults with per-board override for free.

| Tag | Scope | Value | Purpose |
|---|---|---|---|
| `[Collection "practice-bidding-scenarios"]` | file (first board, inherits) | collection slug | the `collection_id` half of BC's identity key |
| `[Ready "true"\|"false"]` | file default + per-board override | readiness | absent/`false` ⇒ BC records plays as `prerelease` (kept for the student's own history, excluded from mastery/stats, not assignable); `true` ⇒ full |
| `[SkillPath "bidding/…"]` | per board | real skill path | retires `uncategorized`; BC requires a real path (C5) |
| `[DealHash "<16-hex>"]` | per board | rotation-independent deal fingerprint | opaque **board-version token**: BC records it + echoes it into "Report a Problem", never computes/verifies/compares it (C2) |

To BC the token is opaque, so its definition is entirely ours — Rick only needs
the tag name.

> **Token algorithm — superseded.** The accepted contract specifies a
> *rotation-**canonical*** hash (rotate deal **and auction** so the ♠A holder sits
> North), `sha256( canonical_deal + "|" + canonical_auction )`, **lowercase hex** —
> not the sort-invariant, deal-only `sha1[:16]` described immediately below. See
> [`coaching-non-rotated/CLAUDE.md`](coaching-non-rotated/CLAUDE.md) §R3.

## The rotation-independent token (our definition)

Repurposed from the original rotation-*sensitive* `deal_hash`. Now
**rotation-independent** so a report on any seat-variant of a deal lets us find and
fix that deal across every file/rotation it appears in (ADR §5.1).

- Canonicalize to a rotation-invariant form: sort the cards in each hand, then sort
  the four hands lexicographically among themselves, and join — invariant under any
  seat permutation (all rotations).
- `token = sha1(canonical_form)[:16]`, lowercase.
- Consequence (intended): a deal and all its rotated variants stamp the **same**
  token. It re-stamps only when the actual cards change → BC's passive
  change-over-time signal.

Distinct from `py/curate.py:102`'s existing `deal_hash` (which hashes the seated
`[Deal]` string and is rotation-*sensitive*) — that one stays for internal dedup;
the stamped token is the new canonical-form variant.

## Producer tasks (PBS)

1. **Stamp `[DealHash]`** (rotation-independent, above) on every served board at the
   final post-rotation stage ([`py/bridge_classroom.py`](py/bridge_classroom.py)),
   idempotent, closing the current gap (the `cp`-synced `Basic_*` sets — ~16% of
   `coaching-non-rotated/` boards carry no fingerprint today).
2. **Emit `[Ready]`** — file-level default `false`, per-board override; a set is beta
   until we promote it. (Safe default: a forgotten flag can never let beta content
   reach mastery.)
3. **Emit `[Collection "practice-bidding-scenarios"]`** at file level.
4. **Real skill-path taxonomy** — mint real `[SkillPath]` values for our content and
   retire `uncategorized` (C5). This is genuine new taxonomy work on our side.
5. **CI warn** when a `ready` board's content changes (so post-promotion edits are
   deliberate — ADR §7.1).
6. **Report-a-Problem payload** already carries the verbatim deal (the authoritative
   locator); BC adds the token echo on their side (C6).

## Explicitly not doing anymore

- No content-hash **keying** of records (declined).
- No position→hash **remap** (declined — self-contained observations).
- No change to BC's database or reads — the `collection_id`/`prerelease` schema work
  and the mastery/stat filters are all BC-side (ADR Phases 1–4).

## Verification

- **Stamp coverage:** every board in `coaching-non-rotated/` (and `coaching/`) carries
  `[DealHash]`, `[Ready]`, `[Collection]`, `[SkillPath]`; re-run + diff for idempotence
  and zero gaps.
- **Rotation-independence:** a deal and its 180°/4-seat rotations produce the **same**
  `[DealHash]` (test across a seat-alternation pair and the `pbn-rotated-for-4-players`
  variants).
- **Ready default:** a freshly generated set stamps `[Ready "false"]` until promoted.
- **Skill paths:** no board maps to `uncategorized`.

## Coordination / next steps

1. **Reply to Rick:** approve ADR-0001; propose the four tag names above (the one thing
   his frontend slice waits on). Confirm our collection slug = `practice-bidding-scenarios`
   and that the skill-path taxonomy is ours to define.
2. On agreement, implement the producer tasks (stamping is independently executable;
   skill-path taxonomy is the larger piece).

## Curation under the positional contract (the burden C3/C4/C5 put on us)

ADR-0001 moves the "history can't be corrupted" guarantee from a technical mechanism
(a content-keyed DB tolerant of churn) to a **behavioral contract curation must honor.**
BC never re-fetches or verifies, so it won't stop us breaking it — the discipline is
ours. It bites **only for promoted (`ready`) boards with student history**; pre-promotion
everything stays free (regenerate, reorder, drop). With no students yet and all content
`prerelease`, full freedom holds until the first promotion; the discipline switches on
per-set, at promotion.

### A. In-place replacement operation (the core new tool)

Fix a promoted board without disturbing its slot. Never drop-and-renumber a ready board.

1. **Locate the slot** — from the report's verbatim deal + token, find the board; read its
   board number, `[SkillPath]`, difficulty, student seat/role, served rotation.
2. **Pull a substitute from the pool** matching `{theme/skill-path, difficulty band,
   student seat}` via `{Curate}` / `py/select.py` over the theme-index tags — **select from
   the existing generated pool, no regeneration.**
3. **Rotate to match** the slot's served orientation (student in the same seat/role).
4. **Write into the same slot** — preserve board number, `[SkillPath]`, `[Ready "true"]`,
   `[Collection]`. **Renumber nothing else.**
5. **Re-stamp `[DealHash]`** (new deal family) and **author/port the coaching prose**; run
   the gates (`py/coach.py validate`, `py/suit_quality.py`).
6. **Replacement is itself `ready`** — re-reviewed, not dropped to beta (C3).

Invariants: same `(collection, subfolder, number)` · same difficulty band · same
seat/rotation · stays ready · no renumber. (Note: the token is rotation-*independent* — a
locator across files — while the served board is rotation-*pinned* to the slot; the
replacement must match the served rotation, which the token does not constrain.)

### B. Readiness model

- `[Ready]` file-level default `false`, per-board override; new content is beta until promoted.
- A **promote** step flips a reviewed set/board to `ready=true`.
- A replacement for a ready board must itself be ready.
- **CI warns** when a ready board's content changes, so post-promotion edits are deliberate.

### C. Skill-path taxonomy (the upfront work)

Define a real skill-path tree for PBS content and assign `[SkillPath]` per board, retiring
`uncategorized` (C5). The larger piece; needs David's input on how the content maps.

### D. `/issue` grows one branch

Report lands → **beta or ready?** Beta ⇒ free (drop / regenerate / reorder, today's
behavior). Ready ⇒ operation **A** only, never drop-and-renumber.

### Open decisions

1. **Skill-path tree** — mirror Rick's Baker Bridge taxonomy, or a parallel PBS tree?
2. **Where operation A lives** — extend `py/curate.py` / `py/select.py`, or a new `py/` script?
3. **Difficulty-match tolerance** — how tight a band? (theme-index carries difficulty weights.)
4. **Seat/theme tags** — confirm the theme-index carries student-seat + theme for the sets to
   be promoted; the replacement query depends on them.
