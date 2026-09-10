# bba-curated/ — graded deal pools with embedded {Curate} blocks

This folder holds the output of the **curate** pipeline stage (see
[pbn-curation-plan.md](../notes/plans/pbn-curation-plan.md)). For each coaching
scenario, `<scenario>.pbn` contains the **full** `bba/` pool (typically 500
boards) with one `{Curate ...}` comment block embedded per board. Lesson
sets are cut from these files with `py/select.py`; nothing here is
hand-edited.

## The {Curate} block

Placed immediately **before** the board's `[Auction]` tag, alongside the
existing `{Shape}`/`{HCP}`/`{Losers}` comment blocks. Standard PBN
consumers ignore comment blocks (verified: `endplay` parses these files
unchanged). Written by `py/annotate.py`; parsed by `py/select.py`.

```
{Curate
class: intended
difficulty: 2
bidding: judgment
also-ok: 3N
bidding-note: S declined the invite with a chunky 16 — accepting wins.
declarer: reject
declarer-note: 10 tricks in 2N, two overtricks — play is uninstructive.
defense: reject
defense-note: Overtricks regardless of defense.
}
```

One `key: value` per line. Fields:

| key | values | meaning |
|---|---|---|
| `class` | `intended` `interference` `continuation` `bba-disagreed` `regex-strict` | How the auction relates to the scenario's intent. `intended` = the convention on display as the `.btn` brief describes. The rest classify why not: opponents competed; the late auction went off-scheme; the robot judged the key call differently; the auction is fine but the old regex was too narrow. |
| `difficulty` | `1`–`5` | 1 = any beginner, 3 = average club player, 5 = expert. Independent of tier. |
| `bidding` | tier | Suitability as a **bidding** lesson example. |
| `also-ok` | calls, space-separated (e.g. `3N`, `1S 2C`) | Defensible alternative calls on judgment boards. The trainer's quiz should score these "defensible" (amber), not wrong. Omitted when empty. |
| `declarer` | tier + themes | Suitability as a **declarer-play** example, followed by its theme tag(s) from the controlled vocabulary, e.g. `standard count-winners`. |
| `defense` | tier + themes | Same for **defense**, e.g. `judgment hold-up-ace`. |
| `*-note` | free text | One-line reviewer note (for humans scanning; not student prose). Braces are converted to parentheses so a note can never terminate the block early. |

### Tiers

| tier | meaning |
|---|---|
| `textbook` | The rule/principle applies cleanly; nothing competes for attention. First exposure to a concept. |
| `standard` | Applies with minor wrinkles worth a sentence of coaching. |
| `judgment` | A genuinely close call; strong players could disagree. Must be coached *as* a close decision (see `also-ok`). |
| `reject` | Unusable for this discipline; the note says why. A board can be `reject` for one discipline and `textbook` for another. |

### Theme vocabulary (controlled — extend the list, don't improvise)

- **declarer:** `count-winners` `count-losers` `establish-long-suit`
  `hold-up` `finesse-basic` `finesse-safe-hand` `ruff-in-dummy`
  `draw-trumps-first` `delay-trumps` `entry-management` `safety-play`
  `danger-hand` `crossruff` `discard-losers` `timing` `endplay`
- **defense:** `opening-lead-suit` `opening-lead-nt` `lead-partners-suit`
  `third-hand-high` `second-hand-low` `return-partners-suit`
  `duck-to-keep-communication` `hold-up-ace` `cover-an-honor`
  `passive-defense` `count-declarers-tricks` `cash-out`

## Selecting lessons

```
python3 py/select.py Basic_NT "bidding=textbook" -n 30 -o lesson.pbn
python3 py/select.py Basic_NT "declarer=hold-up,danger-hand"
python3 py/select.py Basic_NT "bidding=judgment" "diff<=2"
python3 py/select.py Basic_NT "class=interference"
```

Terms are ANDed; commas within a value mean OR; values match whole words in
the field (so `declarer=hold-up` matches tier-plus-theme lines). `diff<=N`,
`diff>=N`, `diff=N` compare difficulty. `-n` caps the count, `-o` writes a
lesson PBN (`--strip` removes the Curate blocks from the output).

## Other files here

- `<scenario>.json` / `<scenario>-graded.json` — machine-readable Layer A
  features / Layer B verdicts (derived; the annotated PBN is the source of
  record).
- `<scenario>-report.md` — Layer A defect report per scenario.
- `Basic_NT-graded-report.md` — Layer B pilot report incl. spot-check
  sample.
- `-overnight-summary.md`, `-layerA-summary.json` — run summaries.
- `.progress/` — resumable-run checkpoints (gitignored, disposable).
