# Build / Coach pipeline split + progressive-hash staleness — design note  ·  DRAFT

> **DRAFT — thinking out loud, not a commitment.** A record of a design conversation,
> speculative, may never be built. No action implied by its presence in the repo.

Captured 2026-06-24 from a design conversation (David + Claude); related to the
2026-06-06 content-fingerprint proposal drafted to Rick. Nothing here is implemented.

## Why this came up

The original "just run the pipe" habit (full `*` on any `.btn` change) used to be safe:
everything downstream was machine-generated, deterministic, and disposable. The
**coaching tier** broke that assumption. Coaching prose (`coaching-curated/*.pbn`) is
hand/LLM-authored — expensive and **non-deterministic** — and the served artifacts are
curated against *specific deals*. A blind full re-run now:

- wastes (and can orphan) curation/coaching work — regenerating `pbn` shifts the board
  pool out from under curation keyed to particular deals; and
- is triggered far too often, because staleness is judged by **file modification time**,
  which flips on any save — even a no-op save or a whitespace-only edit.

Two independent ideas address this. They compose.

## Idea 1 — Two pipelines: `build` and `coach`

Keep the current pipeline as **`build`** and add a separate **`coach`**.

- **`build`** (today): `btn → dlr → pbs → pbn → rotate → bba → filter → … → sheets / release`.
  Source of truth = `btn`. Deterministic, disposable, re-runnable any time.
- **`coach`** (new): `coaching-curated → {validate, suit_quality, check_fit_claims} →
  nonrotate → bridge_classroom → promote`. Source of truth = `coaching-curated`.

**Why separate rather than one unified pipeline:** the split makes the protective
boundary **structural, not a rule you have to remember**. A `build` run physically
cannot touch lessons; a `coach` run physically cannot regenerate hands. They genuinely
have two different sources of truth (`btn` vs `coaching-curated`), so they are two
pipelines, not one with a long tail.

**The line *inside* `coach`:** it orchestrates only the **deterministic tail** (the gates
+ `nonrotate` + `bridge_classroom` + `promote`). The **LLM authoring** (`coach.py` writing
prose, grading/curation) is *not* a pipeline stage — it is authoring, and it stays a
conscious step. `coaching-curated` is a **protected source**, like `btn`; no `*` run may
regenerate it.

**The seam between the two (the dangerous spot):** coaching is *curated from* `build`'s
output (the `bba` / `bba-filtered` hand pool). That bridging step
(`curate` / `select` / `spiral_auction` / `annotate`) belongs to **neither routine
pipeline**. Make it a conscious, gated, occasional operation, run on purpose when you want
to bring new hands into a lesson. And **pin coaching to deal *identity* — the PBN deal
strings — not to "re-run build."** Then a `build` re-run cannot silently pull the ground
out from under coaching, because coaching is anchored to the deals themselves, not to
whatever the pool happens to contain after the latest run.
(See the existing caution: `bba-filtered/` is *renumbered*; curate/coach tooling keys to
`bba/` board numbers — never join by board number across that boundary.)

What you "lose" with separation is automatic cross-seam staleness — but you don't want
that automated. Re-basing lessons onto a fresh pool should be a decision, not a side
effect. (Idea 2 gives the safe version: a *warning*, not an auto-rebuild.)

## Idea 2 — Progressive (per-stage) hash staleness, instead of dates

Replace mtime comparison with a **content fingerprint** at every stage. A fingerprint is a
checksum of a file's contents: same contents → same fingerprint; any change → a completely
different one.

**The chain rule:** each stage judges staleness against its **immediate predecessor's
*output* fingerprint** — not the original `btn`, and not the clock. Store the fingerprints
in a **gitignored `.build-cache/`** ledger (no file churn, no merge conflicts; a fresh
clone just rebuilds once).

The key behaviour that makes this powerful: **a stage may rebuild and produce an identical
output.** When it does, its fingerprint doesn't move, so its successors **skip**. The
cascade dies at the first stage whose output is unchanged.

**Worked example — editing a comment in a `.btn`:**
1. `btn` changed → `dlr` is stale vs `btn` → rebuild `dlr` (cheap — just extraction).
2. The comment is dropped during extraction, so the new `dlr` is **byte-identical** → its
   fingerprint doesn't move.
3. `pbn` checks its predecessor (`dlr`), sees the same fingerprint → **skips**. So do
   `bba`, `lin`, the sheets — every expensive stage.
4. Net cost: one cheap `dlr` rebuild. Nothing else runs.

**Make `dlr` the normalization firewall:** strip comments and collapse insignificant
whitespace at the `dlr` stage, and fingerprint *that* normalized output. Then *any*
cosmetic `.btn` edit (a comment, or spaces inside the dealer code) costs one cheap `dlr`
rebuild and stops cold — `pbn`/`bba`/sheets never run. (If a cosmetic change rode through
into `dlr` unchanged, the firewall would slide downstream to the expensive dealer run — so
normalize *at* `dlr`.) This is simpler and more robust than trying to hash the raw `.btn`
cleverly: the pipeline's own extraction step is already the normalizer.

**Enabler:** the dealer seed is deterministic per scenario (`md5(scenario:offset)` in
`config.py` `dealer_seed()`), so the same dealer code yields byte-identical hands. Output
only changes when the real input changes — which is exactly what makes fingerprint-skip
reliable.

**Escape hatches:** keep a `--force` flag so every op stays manually re-runnable; use
"write-if-changed" outputs (safe given the deterministic seed).

## How they compose

`coach` consumes a *frozen snapshot* of the hand pool (pinned by deal identity). With
fingerprints, `coach` can **warn** — "the `bba` pool you curated from has drifted" —
**without rebuilding anything**. You get safety across the seam without coupling the two
pipelines.

A concrete witness to the value: building today's coaching batch meant hand-running
`edit curated → validate → suit_quality → nonrotate → bridge_classroom` across ~25
scenarios, in order, remembering to run each gate. A single `coach <scenario>` op with
fingerprint-skip would have done exactly that, correctly, rebuilding only what changed.

## Precedents already in the tree

- The artifact→source dependency DAG already exists (the VS Code extension's `ARTIFACTS`
  table).
- The `pbs` op already does a content-aware "nothing to commit if unchanged" check.
- `promote.py` is already "gated, not a blind copy."

## Timing note

The *authoring/curation* half is still actively evolving. If any of this is ever built,
formalize the **stable deterministic tail** first (the gates + nonrotate + bridge_classroom
+ promote) and leave the authoring/curation scripts loose until they settle — no sense
ossifying a part still changing shape.
