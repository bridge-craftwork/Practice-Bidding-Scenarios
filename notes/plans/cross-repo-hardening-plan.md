# Cross-Repo Workflow Hardening — Plan

> **STATUS: DRAFT for David + Rick.** This is a planning document. Nothing in it has
> been implemented. No code, parser, or guard described here exists yet. Adopt or edit
> first; then route the work to the two repo agents (see §3, "What David has to do").

**Author:** Cowork session, for David Bailey · **Date:** 2026-06-17
**Companion file:** `coordination/PROPOSED-charter.md` (the charter draft this plan
refers to).

---

## 1. Where things stand

The cross-repo workflow already works. PBS (content + pipeline) and Trainer
(engine + UI) collaborate through the file-based message pipe in `coordination/`,
with a one-way runtime dependency (Trainer reads PBS's `coaching/*.pbn` via
`BRIDGE_DATA_ROOT`, never writes back) and a single shared seam: the coaching markers
(`[show]`, `[BID]`, `[PLAY]`, `[STAGE]`, `[WHY]`, `\S\H\D\C`) authored in PBS and
parsed in Trainer's `server.py`. The PBS-6/7 ↔ TR-6 exchange shows the loop catching a
real defect the gate alone could not see.

The problem is **not** the design — it's that several load-bearing pieces are still
*conventions and proposals* rather than *committed artifacts and enforced checks*. This
plan converts them. Five gaps, in priority order.

---

## 2. The five gaps and how to close them

### Gap 1 — The charter and LOG exist only as a proposal *(highest value)*

The rules of engagement live in one agent's pitch (`PBS-proposal.md`), not in an
agreed document both agents read. There is no `coordination/README.md` and no
`LOG.md`, and Trainer never wrote its half.

**Fix.** Adopt `coordination/PROPOSED-charter.md` as `coordination/README.md`; create
`LOG.md`; have Trainer record agreement.
**Owner:** David adopts; both agents thereafter obey it.
**Effort:** minutes. **Risk if skipped:** the autonomy boundaries that protect you are
unenforceable because they aren't written where both agents look.

### Gap 2 — An unexplained writer has already touched a content file

`PBS-6` reported that a concurrent process reverted
`coaching-curated/Choice_Of_Finesses.pbn` between `git status` and `git add`; `TR-6`
ruled itself out; the culprit is unidentified. The file-pipe model enforces ownership
by **convention only** — there is no lock.

**Fix.** Codify the content-file ownership rule (charter §4): only PBS writes coaching
`.pbn`; Trainer writes neither `coaching/` nor `coaching-curated/`; every agent diffs
**staged-vs-working** before committing a content file and aborts on an unexpected
delta.
**Owner:** PBS agent adds the pre-commit staged-vs-working check; both agents adopt the
rule.
**Effort:** small. **Risk if skipped:** a silent reversion ships a served file with no
source behind it — directly threatens the no-wrong-coaching promise — and it gets worse
at the 300+ board scale-up.

### Gap 3 — No version handshake on the marker vocabulary

The real contract is whatever `server.py`'s parser accepts. `data-model.md` is
explicitly "design intent, not a contract," and there is no single authoritative marker
spec and no `formatVersion`. When PBS adds a new `[PLAY]` decision-type signal
(hold-up duck, ruff timing, drop-vs-finesse, promotion, endplay — all noted as
in-build), nothing makes Trainer **fail loudly** on a marker it doesn't yet understand.

**Fix.** (a) One authoritative `MARKERS.md` spec — the marker vocabulary, owned jointly,
the source of truth both the author and the parser follow. (b) Stamp each coaching
`.pbn` with a `formatVersion`. (c) Trainer's parser rejects an unknown `formatVersion`
**loudly** (clear error, scenario skipped) instead of silently mis-parsing.
**Owner:** marker spec — joint; version stamping — PBS; loud-reject parser — Trainer.
**Effort:** moderate. **Risk if skipped:** a format change silently degrades coaching in
production, where seniors won't report it.

### Gap 4 — The contract test is unnamed and lives across the line

`verify_play_coaching.py` is effectively the executable contract, but it sits in
Trainer while validating PBS content, and isn't formally designated as "the contract."

**Fix.** Name it explicitly in the charter/MARKERS spec as **the** contract test,
state that it is content-read-only, and decide its home of record (recommend: stays in
Trainer as the engine-side acceptance test, referenced from PBS). No behavior change —
this is about removing ambiguity over who owns "valid coaching."
**Owner:** David ratifies; documented by whichever agent edits MARKERS.
**Effort:** minutes (documentation). **Risk if skipped:** ongoing low-grade confusion
about ownership at the content↔engine line.

### Gap 5 — The no-keys guarantee has no regression guard

The "no outbound AI calls" promise is protected only by discipline and the completed
API→embedded-prose migration. One reintroduced call breaks the whole premise that your
users never need a key.

**Fix.** A trivial CI-style check that fails if `server.py` (or its imports) references
an AI client / outbound inference call. Run it on every Trainer change.
**Owner:** Trainer agent.
**Effort:** small. **Risk if skipped:** a future edit silently reintroduces a key
requirement and nobody notices until a user is asked to pay.

---

## 3. What David has to do

Because the two agents can't talk live, **you are the one who points both at the same
adopted rules and assigns each its half of the work.** The drafts make that routing
concrete. Concretely:

**Step 1 — Review & edit the two drafts.**
`coordination/PROPOSED-charter.md` (weigh in especially on §3 rules of engagement and
§6 autonomy level — those are yours to set) and this plan. Change anything you disagree
with.

**Step 2 — Get Rick's sign-off.**
The charter is shared and symmetric, so both humans should agree. Send Rick both files.

**Step 3 — Make the charter jointly owned.**
Have the **Trainer** agent record agreement — tell it "check coord, review
PROPOSED-charter, reply with your agreement or edits." It writes a `TR-*.md` saying so.

**Step 4 — Activate the charter.**
Rename `coordination/PROPOSED-charter.md` → `coordination/README.md`, create an empty
`LOG.md`, fill in the `CURRENT AUTONOMY LEVEL` line (start **TIGHT**), and commit. You
can do this yourself or tell the PBS agent "adopt the charter."

**Step 5 — Route the five fixes to the owning agent, via the pipe.**
You don't implement these; you assign them. Suggested messages:
- To **PBS**: "Add the pre-commit staged-vs-working check (Gap 2). Stamp `formatVersion`
  on coaching `.pbn` files (Gap 3b)."
- To **Trainer**: "Make the parser reject unknown `formatVersion` loudly (Gap 3c). Add
  the no-AI-calls guard (Gap 5)."
- To **both** (one drafts, the other ratifies via the pipe): "Write the joint
  `MARKERS.md` spec and name `verify_play_coaching.py` as the contract test (Gaps 3a, 4)."

**Step 6 — Run one supervised loop, then set autonomy.**
Watch one full request go through the pipe end-to-end. If the agents behaved, change the
charter's `CURRENT AUTONOMY LEVEL` to LOOSENED. Until then it stays TIGHT.

**Standing rule (already agreed):** no agent pushes to `main` without your say-so.

---

## 4. Suggested order

Gap 1 (adopt charter) and Gap 2 (ownership rule) first — they're cheap and they protect
content integrity immediately. Gap 5 (no-keys guard) next — also cheap, protects a
non-negotiable. Then Gap 3 (version handshake) as the one moderate build, timed to land
**before** the next new `[PLAY]` marker type ships. Gap 4 is documentation you can fold
into the Gap 3 spec work.
