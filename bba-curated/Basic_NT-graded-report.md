# Layer B pilot — Basic_NT grading report

500 boards from `bba/Basic_NT.pbn` graded against the rubric in
notes/plans/pbn-curation-plan.md. Verdicts: `bba-curated/Basic_NT-graded.json`;
annotated pool: `bba-curated/Basic_NT.pbn`.

**Re-graded 2026-06-05** after raising the responder HCP cap to `<20` and
re-running the full pipeline (so the brief's "6NT = 18+" row can occur).
493 of the 500 deals are byte-identical to the previous pool (matched by
`deal_hash`) and carry their verdicts over unchanged; **7 new 18-19 HCP /
6NT boards were graded fresh** (see below). 7 old tail deals fell off the
500-board cut.

## Tier counts

| discipline | textbook | standard | judgment | reject |
|---|--:|--:|--:|--:|
| bidding | 304 | 116 | 57 | 23 |
| declarer | 10 | 279 | 3 | 208 |
| defense | 4 | 254 | 17 | 225 |

Auction classes: {'intended': 478, 'interference': 21, 'continuation': 1}
Difficulty: {1: 87, 2: 204, 3: 199, 4: 10}
Declarer themes: {'count-winners': 177, 'finesse-basic': 70, 'establish-long-suit': 39, 'hold-up': 2, 'danger-hand': 2, 'timing': 2}
Defense themes: {'opening-lead-nt': 243, 'passive-defense': 16, 'hold-up-ace': 5, 'opening-lead-suit': 5, 'count-declarers-tricks': 3, 'duck-to-keep-communication': 1, 'lead-partners-suit': 1, 'cash-out': 1, 'return-partners-suit': 1}

## The 7 new 6NT boards (responder 18-19 HCP)

With the cap at `<20`, North can now hold 18-19 and — with Gerber removed
from the Basic-Bridge card — BBA raises 1NT straight to 6NT (`1N P 6N`),
exactly the brief's slam row. All seven are `class: intended`,
`matched_intended_auction: true`, difficulty 2.

| board | N/S HCP (comb) | 6N DD | bidding | declarer | defense |
|--:|---|---|---|---|---|
| 66  | 18/16 (34) | makes 12 (exact) | **textbook** | standard count-winners | reject |
| 80  | 18/15 (33) | makes 13 | **textbook** | standard count-winners | reject |
| 251 | 18/17 (35) | makes 13 | **standard** — cold grand, unreachable naturally | standard count-winners | reject |
| 273 | 18/17 (35) | makes 13 | **standard** — cold grand, unreachable naturally | standard count-winners | reject |
| 291 | 18/15 (33) | makes 12 (exact) | **textbook** | standard count-winners | reject |
| 381 | 18/15 (33) | down 1 (11) | **standard** — correct 18+ call, sour DD result | reject | reject |
| 441 | 19/16 (35) | makes 12 (exact) | **textbook** | standard count-winners | reject |

Grading logic: a direct 6NT with 18+ opposite 15-17 is the brief's
prescribed call, so the bidding is sound on all seven (`intended`).
Textbook where 6NT is the clean, uncompeted answer and makes; **standard**
where a wrinkle deserves a coaching sentence — boards 251/273 because a
35-count's cold grand can't be reached with natural-only methods (a useful
note on the method's ceiling), and board 381 because the percentage 6NT
happens to fail double-dummy on a flat layout (correct bid, unlucky
result). Declarer is graded on the slam's own merits (count-winners for the
makers, reject for the down-one); defense is reject throughout — a making
slam offers no defensive decision, and 381 drifts off on count with nothing
for the defenders to find.

## Carried-over spot-check sample (still current — these deals are unchanged)

The boards below were the original David-review sample; their deals and
verdicts are unchanged by this regen. Board 430 already caught a grader
error (wrong opening leader) which hardened the rubric.

### Board 1 — intended, dd ok, difficulty 1
- bidding: **textbook** — Clean 17 balanced, N's 7-count pass matches the table exactly.
- declarer: **reject** — 9 tricks in 1N, two overtricks regardless — nothing to teach.
- defense: **reject** — Declarer has comfortable overtricks whatever defense does.

### Board 112 — intended, dd ok, difficulty 3
- bidding: **judgment** also_ok=['3N'] — S passed the 2N invite with a prime 16 (AQ5 AK7) and 9 tricks were there — accepting with a good 16 is at least as defensible.
- declarer: **standard** themes=['count-winners'] — 9 tricks dd in 2N; one-trick cushion, straightforward development.
- defense: **reject** — 2N always makes; only an overtrick at stake.

### Board 137 — intended, dd ok, difficulty 3
- bidding: **judgment** also_ok=['2N'] — N bid 3N with 9 HCP — table says 2N invite; AQT6 with tens makes the upgrade arguable, and it makes exactly.
- declarer: **standard** themes=['finesse-basic'] — Exactly 9 dd; the club finesse through W is a key trick.
- defense: **standard** themes=['opening-lead-nt'] — E's red-suit honors over declarer hold the total to 9.

(Earlier sampled boards 430/249/81/389/319/23/417 were drawn from the old
pool numbering; the deals persist but their board numbers may have shifted
in the re-cut. Re-sample from the annotated PBN if reviewing by number.)
