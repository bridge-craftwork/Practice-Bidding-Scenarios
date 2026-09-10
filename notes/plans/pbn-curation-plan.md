# Plan: the `curate` pipeline operation

**Status:** merged plan, 2026-06-04. Combines
[Coaching-Board-Curation-Proposal.md](Coaching-Board-Curation-Proposal.md)
(the DD quality gate — prototyped and measured) with the grading-pass design
(tiers, themes, judgment boards) drafted in conversation. Supersedes
`bookmark-bba-curated-2026-06-03.md`; the Proposal stays as-is as the
Rick-facing document.

## Context

Pipeline position — one new op between `filter` and coaching authoring:

```
btn → dlr → pbs → pbn → rotate → bba → filter (→ bba-filtered) → [CURATE] → author coaching → package
```

Prior work this plan builds on:

- `coaching/` holds **20 hand-authored 30-board lesson sets** (7 Basic
  bidding + 13 play-of-the-hand). Boards were picked as "the first 30" with
  no quality check.
- `curation_trial.py` (scratch prototype, validated in the Proposal):
  a double-dummy gate found **9% of current play boards defective** — best
  defense beats the taught contract, or it only makes from partner's seat
  (Suit_Promotion 27%, Hold_Up_3N 20%). The honor-swap test positively
  selects "by-force" boards. Replacement pools are abundant (hundreds of
  clean candidates per scenario).
- **Proven negative result:** DD cannot positively select *avoidance*
  boards (hold-up, safe finesse) — seeing all four hands makes the
  technique unnecessary. Positive selection there needs single-dummy
  Monte-Carlo (**Phase 2 — designed, not built, out of scope here**). The
  prototype's single-dummy hold-up oracle (`holdup_required`) is the seed.
- The regex that today gates `bba-filtered/` lives in the `.btn` master,
  e.g. `btn/Basic_NT.btn` line 5:
  `# auction-filter: Auction.....\n1N +Pass +(Pass|2N|3N|4N|6N)`.
  **Status decision (2026-06-04): the regex is the one exception to ".btn
  is source of truth."** The `.btn` remains authoritative for scenario
  *intent* — Dealer constraints, the `@chat` brief, the `# curate:`
  directive — but board *selection* authority transfers to the curate op.
  For curated scenarios the regex is a legacy bootstrap: still computed as
  the `matched_intended_auction` feature (cheap, and needed for the
  bba-vs-bba-filtered comparison), never again a gate. For the ~324
  scenarios outside curation scope, `filter` keeps running unchanged — the
  uploader and bidding sheets depend on `bba-filtered/`.

**Scope (decided 2026-06-04):** the 20 scenarios in `coaching/` — every
play lesson plus the Beginners Bidding set — expanding as new lessons are
authored. Not all 344.

Guiding principles:

- **Tier, don't gate.** Borderline deals aren't rejects; edge cases are
  where judgment is taught. Every kept board gets a tier per discipline.
- **DD for soundness, never for pedagogy.** The DD gate removes objectively
  defective boards and certifies by-force boards. Teaching merit — does this
  board exhibit the technique, is the line findable by principle — is judged
  by the grading layer (and eventually Phase 2 simulation), not by DD.
- **Realistic play.** Lessons reward good bridge principles, not DD-perfect
  play. (Downstream consequence for the trainer's DDS-driven opponents —
  separate plan.)

## Architecture: one `curate` op, two layers

### Layer A — mechanical gate + features (generalize `curation_trial.py`)

Per board of `bba/<scenario>.pbn` — the full BBA-bid pool, since the regex
no longer decides what curation gets to see — pure computation:

- **DD soundness classify** (play lessons): `ok` / `wrong_sided` /
  `down_both` for the lesson's target contract from the student's seat.
  Wrong-sided boards are **rotate-salvaged** (re-seat so the strong hand is
  South) rather than discarded.
- **By-force test** (by-force lessons): still makes with the E/W hands
  swapped — made by force, not by a lucky finesse.
- **Technique oracles** (avoidance lessons, best-effort until Phase 2):
  the hold-up single-dummy oracle; structural shape filters (single stopper
  + tenace count) for finesse-choice lessons.
- **Features for the grader:** `matched_intended_auction` (the `.btn`
  `# auction-filter` regex, demoted from gate to feature), HCP/shape margin
  from the scenario constraints, combined values vs. contract, freak/
  interference flags, opening-lead clarity, duplicate detection
  (`deal_hash`).

Lesson kind and target drive which tests run. That config belongs in the
**`.btn` master** alongside the auction filter — one new directive:

```
# curate: kind=byforce contract=3N seat=S        (Suit_Promotion)
# curate: kind=avoidance contract=3N seat=S      (Hold_Up_3N)
# curate: kind=bidding                           (Basic_NT)
```

*Implemented 2026-06-05:* directives added to all 19 coaching `.btn`
masters (`kind=`, plus `oracle=` for avoidance lessons and
`contract=`/`seat=` where the lesson target is uniform); `py/curate.py`
reads the directive, keeping its internal table only as a fallback.

Note: `endplay`/DDS runs on the Mac (it is not in the Cowork sandbox);
`curate` is a local pipeline op like the rest.

### Layer B — Claude grading pass

Same fan-out architecture as the coaching generator (one subagent per
scenario, spawned in parallel). Input: scenario brief (`/*@chat */` from the
`.btn`), boards + Layer-A records, rubric. Output: per-board verdict.

Tiers, graded **independently per discipline** (bidding / declarer /
defense):

| Tier | Meaning |
|------|---------|
| `textbook` | Rule/principle applies cleanly; nothing competes for attention. First exposure. |
| `standard` | Applies with minor wrinkles worth a sentence of coaching. |
| `judgment` | Genuinely close; strong players could disagree. Coaching must present it as close and argue both sides. |
| `reject` | Unusable for this discipline (reason required; may be fine for another). |

**Calibration rule (David, 2026-06-05, Basic_NT board 137):** a borderline
but defensible bidding decision — declining an invitation with a maximum, or
any close accept/decline — is **`judgment` with an `also_ok`, not
`reject`.** Reserve bidding `reject` for auctions a teacher genuinely cannot
defend (a clear rule violation, an indefensible call), never for the losing
side of a close call. Edge cases are teaching material. (Confirmed against
the Basic_NT pilot: board 137, South passing a 2NT invite on a flat 16 →
judgment.)

Grading criteria:

- **Bidding** — *auction soundness is load-bearing* (the trainer's quiz
  treats the PBN auction as the answer key): every kept board's auction must
  be defensible, especially when `matched_intended_auction` is false. Then:
  margin from constraint boundaries (deep inside → textbook; on the line →
  judgment, not reject), sensible final contract, quiet opponents plausible,
  one teaching point. Judgment boards record defensible alternatives
  (`also_ok`) with one-line cases. Textbook bidding boards require the
  intended convention **on display** — `auction_class: intended` as judged
  by the grader (the regex feature bootstraps that judgment but doesn't
  decide it).
- **Declarer** — the play matters (principled line succeeds, plausible
  careless line fails — Layer A's gate and oracles supply the evidence);
  one nameable theme; clear standard opening lead; line findable by
  counting/reasoning, never DD-only.
- **Defense** — correct principled defense beats the contract (or saves the
  decisive trick); the key decision sits in the student's seat; findable by
  teachable rule + visible evidence; signals optional and hedged, never
  load-bearing.

Themes from a **controlled vocabulary** (extend by editing the list, not by
improvising): declarer `count-winners, count-losers, establish-long-suit,
hold-up, finesse-basic, finesse-safe-hand, ruff-in-dummy, draw-trumps-first,
delay-trumps, entry-management, safety-play, danger-hand, crossruff,
discard-losers, timing`; defense `opening-lead-suit, opening-lead-nt,
lead-partners-suit, third-hand-high, second-hand-low, return-partners-suit,
duck-to-keep-communication, hold-up-ace, cover-an-honor, passive-defense,
count-declarers-tricks, cash-out`; bidding uses the scenario name plus
`close-decision-<alt>` on judgment boards.

### Outputs

**Decided 2026-06-05: verdicts are embedded in the PBN itself** as one
`{Curate ...}` comment block per board, placed before `[Auction]` — the
same house style as the existing `{Shape}`/`{HCP}`/`{Losers}` blocks, and
ignored by all PBN consumers (verified: `endplay` parses annotated files
unchanged). The deal and its verdict can't get separated, the file is
readable in any editor, and selection becomes a simple deterministic
filter — the structured successor to the auction-filter regex. Implemented
in `py/annotate.py` (writes the block) and `py/select.py` (filters on it):

```
{Curate
class: intended
difficulty: 2
bidding: judgment
also-ok: 3N
bidding-note: S declined the invite with a chunky 16 — accepting was the winning call.
declarer: reject
declarer-note: 10 tricks in 2N, two overtricks — play is uninstructive.
defense: reject
defense-note: Overtricks regardless of defense.
}

python3 py/select.py Basic_NT "bidding=textbook" "diff<=2" -n 30 -o lesson.pbn
```

The notes are embedded in `bba-curated/<scenario>.pbn` (a derived,
versioned artifact) — never in `bba/`, which the pipeline regenerates.
The JSON below is now a derived convenience for tooling; the annotated
PBN is the source of record. All under `bba-curated/`:

- `bba-curated/<scenario>.pbn` (+ regenerated `.pdf`) — the selected best-N
  boards (N=30 default), deterministic sort key (tier, by-force/oracle
  flags, difficulty spread, `deal_hash` tiebreak). This is what coaching
  authoring consumes.
- `bba-curated/<scenario>.json` — full verdicts for **every** pool board
  (selected or not): tiers, themes, `also_ok`, notes, Layer-A results,
  `auction_class` (`intended` / `interference` / `continuation` /
  `bba-disagreed` / `regex-strict`).
- `bba-curated/theme-index.json` — aggregated theme → (scenario, board,
  tier, difficulty) lookup. This is what lets a future cross-scenario
  lesson ("Hold-up Plays") assemble boards generated by many different
  bidding scenarios.
- `bba-curated/<scenario>-report.md` — human review table (board, tiers,
  themes, notes) + a **diff against the current `coaching/<scenario>.pbn`**:
  boards kept vs. swapped. The dominant cost of re-curation is re-authoring
  prose for swapped boards, so the diff makes that cost visible and
  targeted.

## What the wider pool buys (measured in the pilot)

With the regex demoted, curation's pool is `bba/` by decision — the open
question is only what the extra boards *yield*, which sizes the grading
cost. Regex-rejected boards fail for unequal reasons; the `bba-disagreed`
class (BBA judged the key call differently than the Dealer constraints
intend) is prime judgment-tier material, discarded unseen today. The
**Basic_NT pilot** (500 boards vs 460 regex-matched) reports the
`auction_class` breakdown of regex-rejects and what fraction of each class
the grader rated usable. If rejects yield little, later scenarios may grade
regex-matches plus a capped sample of rejects purely as a cost optimization
— the authority stays with curation either way.

## Order of changes

1. **Layer A script.** Generalize `curation_trial.py` into the `curate` op
   (`build-scripts-mac/operations/`, registered in `OPERATIONS`): parse the
   `# curate:` directive, run gate + features over all 20 scenarios, emit
   the JSON + report (no PBN selection yet). Review the defect/pool numbers
   together — this re-validates the Proposal's measurements on today's
   files.
2. **Pilot Layer B** on `Basic_NT` (full `bba/` pool): one subagent →
   verdicts + review table + the reject-class comparison. David spot-checks
   ~10 boards; iterate the rubric until agreement is acceptable.
3. **Fan out** Layer B to the remaining 19 scenarios (parallel subagents).
   Build `theme-index.json`. Emit `bba-curated/*.pbn` selections.
4. **Re-point coaching authoring** at `bba-curated/` (the trainer repo's
   generator plan switches from "first 30" to the curated selection).
   Regenerate the worst offenders first — Suit_Promotion (27% defective),
   Hold_Up_3N (20%) — which also clears the open terminology-audit item.
5. **Trainer PR** (AI-Bridge-Play-Trainer): `[also-ok xxx]` coaching marker
   — quiz scores a defensible alternative as amber ("defensible — here's why
   we prefer …") instead of a red ✗; judgment-tier authoring rule in the
   generation prompt; later, a loader for reference-list lessons built from
   the theme index.
6. **Phase 2** (single-dummy Monte-Carlo for positive selection on avoidance
   lessons) — separate scope, per the Proposal. The Layer-A oracle slots are
   where it plugs in.

## Open questions

- **Rotate-salvage default** — re-seat wrong-sided boards automatically, or
  flag for review? (Rotation changes dealer/vul bookkeeping downstream.)
- **N per lesson** — 30 assumed; judgment-tier boards in the selection mix
  for beginner menus, or only in dedicated "Close Decisions" lessons?
- **Rick / bba-cli** — pending answers on emitting DD tables per board and
  folding a soundness gate into `filter` (Proposal's closing question).
  Either would simplify Layer A.
- **Regen policy** — `deal_hash` tells us which verdicts survive an upstream
  regen; auto-grade only new boards, or re-grade the scenario?
- **Defense seat policy** — curate defense boards for the leader's seat,
  partner's, or both? (Trainer supports `leader`/`defender` roles; UI
  focuses on declarer today.)

## Critical files

- `btn/<scenario>.btn` — source of truth: `# auction-filter:` regex (becomes
  the `matched_intended_auction` feature) + new `# curate:` directive.
- `bba/<scenario>.pbn` — the grading pool. (`bba-filtered/` continues for
  the non-curated scenarios, the uploader, and bidding sheets.)
- `coaching/<scenario>.pbn` — current hand-authored sets; diff target.
- `bba-curated/` — all curate output (new).
- `curation_trial.py` — prototype to generalize, then retire.
- `build-scripts-mac/operations/` + `config.py` — where `curate` registers.
- `AI-Bridge-Play-Trainer/server.py` (`parse_coaching`) and
  `pbn-coaching-generator-plan.md` — downstream consumers.
