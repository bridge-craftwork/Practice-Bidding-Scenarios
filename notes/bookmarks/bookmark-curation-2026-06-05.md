# Bookmark — curation status (2026-06-05)

Session ended here. Current state and what's next.

## Where things stand

- **Plan of record:** `pbn-curation-plan.md`. Format reference:
  `bba-curated/README.md` ({Curate} comment block + `py/select.py` filter).
- **Layer A** (DD gate + features): run over all 19 coaching scenarios,
  refreshed after the Basic-Bridge cc fix. Tools: `py/curate.py`
  (resumable, reads the `# curate:` directive in each `.btn`),
  `py/annotate.py`, `py/select.py`, `py/auction_diff.py` (`--base <ref>`
  for diffing against a pre-change commit; run with `python3 -P` —
  select.py shadows stdlib select).
- **Layer B pilot (Basic_NT):** all 500 boards graded. **Re-graded
  2026-06-05 after the `<20` cap regen** (see item 2): 493 deals unchanged
  (deal_hash carry-over), 7 new 18-19 HCP / 6NT boards graded fresh.
  Current: 304 textbook / 116 standard / 57 judgment / 23 reject (bidding).
  Annotated PBN: `bba-curated/Basic_NT.pbn`. Report:
  `bba-curated/Basic_NT-graded-report.md`.
- **Basic-Bridge cc fixed** (Gerber-over-NT off etc.); all 21 dependent
  scenarios' bba/ regenerated and committed (eaa3abe9d by the Claude Code
  session). 83 boards changed; verdict reuse worked (only 22 re-graded).
- **Email to Rick**: draft in Gmail ("Curation step built — first
  results..."), recipient placeholder = David's own address. Links require
  push before sending.

## Open items (in order)

1. **DONE (2026-06-05) — spot-check complete, rubric calibrated.** David
   reviewed 10 boards. One mechanical bug found+fixed (430 wrong leader →
   leader now pre-computed). One calibration ruling: board 137 (South
   passes a 2NT invite on a flat 16) is **judgment + also_ok, not reject** —
   borderline-but-defensible bidding decisions are judgment; reserve reject
   for indefensible calls. Recorded in pbn-curation-plan.md grading criteria.
   The grader is trusted for the fan-out.
2. **DONE (2026-06-05) — Option 1 chosen.** Raised the responder cap to
   `hcp(north) < 20` (`1c1cc7b7d`), re-ran the full pipeline, and re-graded
   Layer B. The 6NT/18+ row now occurs (1.4% of deals; with Gerber off BBA
   raises 1NT straight to 6NT, `1N P 6N`). 7 new boards: 4 textbook /
   3 standard bidding, all `intended`. The 11 old 17-count→6N boards stay
   `reject` (brief wants 17 = 4NT quantitative). All pushed.
3. **DONE (2026-06-05) — fan-out complete: all 19 scenarios curated.**
   Layer B graded every scenario's 500-board pool (5 subagents each,
   leader pre-computed, board-137 calibration applied). Each has a
   `{Curate}`-annotated `bba-curated/<scn>.pbn` + `<scn>-graded.json`.
   `bba-curated/theme-index.json` aggregates declarer/defense themes across
   all scenarios (e.g. count-winners 345 textbook boards, finesse-safe-hand
   289, finesse-basic 157, establish-long-suit 133, hold-up 36, endplay 19)
   — this is what cross-scenario play lessons draw from. Vocabulary extended:
   added `endplay` to the declarer themes (README updated). A few boards per
   scenario carried through unannotated due to genuine duplicate deal_hashes
   in the pools (harmless).
   Scenario-design notes surfaced for later (not blocking): Rabbi's Rule —
   robots run Blackwood to slam on ~60% of boards, diluting the "you already
   have 10 tricks" point; Choice_Of_Finesses / Two_Way / To_Finesse — the
   constraints place the key honor favorably only ~20-35% of the time, so
   the genuine-decision boards are a minority of each pool (still plenty for
   a 30-board lesson). These are constraint-tightening opportunities in the
   `.btn` masters when convenient.
4. **DONE (2026-06-06) — Randomly Rotate + bidding coaching fan-out.**
   - Trainer (AI-Bridge-Play-Trainer): added "Randomly Rotate" — seats the
     student in either bidding seat per board; coaching uses pronoun tokens
     (@S/@s/@Your/@your/@v(base|third), parens not braces) rendered per seat
     by `fill_pronouns`. Only applies to rotation-ready (tokenized) coaching;
     non-tokenized scenarios stay on their authored seat. "Play as" greys out
     while rotation is on (mutually exclusive). Trainer now reads
     `coaching-curated/` first, then `coaching/`, then `bba/`. Also fixed:
     orphaned Continue button during play (post-auction reflection now
     passive).
   - Coaching generator productionized: `coaching-curated/GENERATOR.md` (spec
     incl. the "use @S once per chunk" repetition rule) + `py/coach.py`
     (`packets` / `splice`). Work files in `coaching-curated/.work/`
     (gitignored).
   - Fan-out: all 7 Beginners-Bidding scenarios now have tokenized both-seats
     lessons in `coaching-curated/*.pbn` (Basic_NT + the 6 others), 30 boards
     each, validated (no [BID Pass], no card recitation). The whole Beginners
     Bidding section is curated+coached and live in the trainer.

## Open items (in order)

0. **DONE (2026-06-06) — coaching architecture fix (Option A).** Two bugs
   found while testing: (a) the prose leaked partner's concrete holding
   during the auction ("partner has six spades"); (b) worse, on multi-round
   auctions the trainer's `parse_coaching` DEFERS any prose after a partner
   `[show N]` to the post-auction chunk, which renders first-person — so
   "You have 10 HCP" described partner. Root cause: my both-seats coaching
   used mid-auction `[show]`, which the trainer (built for single-student
   Baker-Bridge coaching) defers. Fix (Option A, David's call): NO `[show]`
   in `[BID]` chunks — only the closing `[show NS]`; describe what each call
   SHOWS by agreement, never the actor's concrete holding. Proven via the
   trainer's own `parse_coaching` (each call renders in the right person).
   All 7 bidding scenarios regenerated, validator-clean, endplay-parse,
   `[ACCEPT]` intact. `py/coach.py validate` now flags any mid-auction
   `[show]` and missing N/S `[BID]` anchors. GENERATOR.md is the Option A
   spec. (Trainer unchanged — no `server.py`/`app.js` edits needed.)

5. **Spot-check the fan-out in the trainer**, especially a competitive
   scenario (Basic_Takeout_Double / Basic_Overcall) with Randomly Rotate on —
   rotation + competitive auctions is the newest ground.
6. **Play-stage coaching for the 12 play scenarios** (Finesses, Notrump Play,
   Suit Contract Play). Needs the trainer's per-trick coaching markers
   ([ROLE]/[STAGE]/per-trick anchors) — a real build. This is the next
   frontier.
7. **`[ACCEPT]` / judgment-alternative support — PARTLY DONE (2026-06-06).**
   Finding: the trainer ALREADY supports `[ACCEPT <call>]` (parser
   `_extract_accept`, per-quizzed-call quiz scoring — picks the alternative →
   green "either X or Y is fine"). No trainer work needed. The gap was the
   generated coaching: (a) it didn't emit `[ACCEPT]`, and (b) ~45 boards
   narrate one N/S call without its own `[BID]` anchor (Basic_NT responses,
   Basic_Major openings), so rotation can't quiz that call and `[ACCEPT]`
   can't attach. Pass-judgments (declines) can't anchor at all — prose only.
   Done: `GENERATOR.md` now documents `[ACCEPT]` + the structure discipline
   (one `[BID]` per N/S non-pass call, framing-only intro); `py/coach.py`
   gained `validate` (gates `splice`); **Basic_NT regenerated clean** (0
   structure issues, `[ACCEPT]` on b13/b38/b46, endplay-parses).
   **DONE (2026-06-06):** all 7 bidding scenarios structure-tighten regen'd —
   `coach.py validate` reports 0 issues for every one, all endplay-parse, and
   `[ACCEPT]` markers are on the non-pass judgment boards (Basic_NT,
   Basic_Major, Basic_Weak_2). Pass-judgment declines stay prose-only (can't
   anchor `[BID Pass]`) — a known, acceptable limitation. Also removed a stray
   `coaching-curated/Basic_NT-input.pbn` (pilot leftover that the menu would
   have shown as a bogus scenario). The whole Beginners Bidding section is now
   curated + coached + rotation-ready + judgment-aware.
8. **Scenario-design follow-ups** (non-blocking): Rabbi's Rule Blackwood
   dilution; finesse scenarios' favorable-honor placement. Constraint
   tightening in the `.btn` masters when convenient.

## Session conventions

- Cowork sandbox: endplay installed via
  `pip install endplay --break-system-packages`; long runs must be
  time-budgeted (`CURATE_BUDGET`) — background processes don't survive
  between bash calls.
- Commits from Cowork: `git -c user.name="David Bailey"
  -c user.email="adavidbailey@gmail.com" commit ...`. **No push from
  Cowork** (no credentials, by David's choice) — David pushes from
  Terminal/Claude Code.

## Claude Code session note (2026-06-05, late)

- Regrade lists for **all 21** Basic-Bridge scenarios are pre-generated in
  `bba-curated/.progress/<scn>-regrade.json` (git-ignored), via
  `python3 -P py/auction_diff.py --base 89a22f775 <scns>` (baseline
  `89a22f775` = the pre-card-change parent). 83 boards changed total. The
  Layer B fan-out (open item 3) can read these directly — no need to
  re-diff. Details: `bba-curated/.progress/_README_baseline.md`.
- Working tree clean. **Pushed to `origin/main` (David approved)** —
  `fcc909014` + `77e499617` + the bookmark commit are now on origin; local
  and origin in sync. Rick-email links now resolve.

## Claude Code session note (2026-06-07) — Play-Trainer feedback

The trainer's new in-app feedback button (🚩 Report → GitHub issues in
AI-Bridge-Play-Trainer) surfaced two coaching items for **Basic_What_To_Open**:

- **Board 13 prose (issue #13) — DONE, committed + pushed (`2eb62ee19`).**
  The 4S `[BID]` chunk called North's `AKT65432` "a strong fit for partner's
  spades"; now "a self-sufficient spade suit" (a long, solid suit is its own
  trump source, not support for partner). Worth confirming GENERATOR.md's
  terminology rules keep this so a regen doesn't reintroduce "fit for partner".
- **Count-your-tricks request (issues #8/#9 — left OPEN as a tracker).** When
  a student plays a *bidding* scenario out as declarer, they want the
  "count your sure winners" prompt. Decision (David): do NOT hand-author a
  one-off tip — instead **fold Basic_What_To_Open (and likely the other
  bidding scenarios) into the play-coaching generator's scope** (open item 6 /
  `GENERATOR-PLAY.md`): run `play_splice` on it once the play generator lands,
  so declarers get the same analyzed `[ROLE declarer][STAGE auction-end]`
  count-the-winners directive as the 12 dedicated play scenarios.

Second round (issues #15/#16, board 15 of Basic_What_To_Open — South
`A762.QJT2.A965.A`, a 4-4-4-1 opening 1♦ into `1♦-2♣-2♥-2N-3N`):

- **Board 15 prose (#15) — DONE, committed (`68cd947fd`).** The intro
  mislabeled South's 4=4=4=1 as "a strong balanced opening, just shy of 1NT";
  reworded to a three-suiter (a singleton rules out 1NT). **Generator guard
  for GENERATOR.md:** never call a hand with a singleton/void "balanced"
  (the prose also reaches for "balanced-looking" elsewhere) — same spirit as
  the #13 terminology rule.
- **Board 15 re-curation candidate (#16 — left OPEN as tracker).** The 2♥
  rebid is reverse-*shaped* yet South has only 4 diamonds / 15 HCP. It's fine
  in 2/1 GF (2♣ already forced game, so 2♥ isn't a true reverse), but for a
  *Basic* "what to open" lesson the 2/1 sequence with a reverse-looking rebid
  is confusing. Decision (David): **flag board 15 for re-curation** — prefer
  replacing/dropping it over patching prose. A curation note for whoever
  reselects the 30 boards: avoid openings whose follow-up auction needs 2/1
  machinery to read correctly.

---

## 2026-06-07 — Hold_Up_3N scenario bug found via play-coaching pilot

Starting the **play-stage coaching** pilot (Hold_Up_3N, theme=hold-up) surfaced
a scenario-design bug, not a coaching bug.

**Symptom.** Of 12 pilot boards, the play-coaching subagents found only 1 that
was even arguably a hold-up on the *real* opening lead, and on inspection that
one (board 17, ♠AK opposite ♠QJ doubleton) isn't a true hold-up either — you
just cash both top spades.

**Root cause.** The old `Hold_Up_3N.btn` put the long heart suit in **East**
(`predeal east HKQ`, `hearts(east) > 4`). But South declares 3NT, so the
opening leader is **West**, who was short in hearts and led their *own* long
suit. The heart hold-up the scenario teaches almost never arose. Evidence: the
corrected lead-driven oracle over the full 500-board `bba/Hold_Up_3N.pbn` pool
found West leads a heart on only **22/500** boards and a DD-necessary hold-up on
only **4/500 (0.8%)**.

**Two fixes landed (PBS-side, uncommitted):**

1. `py/curate.py` `holdup_required` rewritten to be **lead-driven**: it now
   computes West's actual standard opening lead (4th-best of the longest,
   strongest suit; top of a 3-honor sequence) and tests whether *winning the
   first round of the led suit* costs the contract. Stopper-count agnostic
   (catches two-stopper "duck once to strand the short hand" as well as classic
   Axx). New helpers `opening_lead_vs_nt`, `_honor_sequence_top`.

2. `btn/Hold_Up_3N.btn` rewritten so **WEST** holds the long suit and leads it:
   `predeal west HKQ`, `hearts(west) > 4`, `hcp(west) < 8` (so no outside
   entry); South keeps one stopper (`predeal south HA`, `hearts(south) < 4`);
   East short hearts (`hearts(east) < 4`) and, as the stronger defender, holds
   the side entry to knock out. @chat prose updated to the corrected geometry
   (duck to exhaust **East**, the entry hand; West's length is stranded).

**Verification.** Monte-Carlo over deals matching the new constraints: **13% of
makeable boards are DD-necessary hold-ups** (vs 0.8% before, ~16x). A 500-board
run should yield 50+ clean hold-up boards.

**Open / next:**
- The pilot play-coach JSONs in `coaching-curated/.work/Hold_Up_3N-play-*` were
  generated off the BROKEN pool — discard; regenerate after the pipeline re-run.
- **David to re-run the pipeline for Hold_Up_3N** (bba needs the Windows VM):
  `dlr → pbn → rotate → bba → curate` (e.g. from build-scripts-mac:
  `python3 pbs-pipeline-mac.py Hold_Up_3N "dlr+"`). Then grade + play-coach.
- Same class of bug may affect the other **avoidance** play scenarios
  (Choice_Of_Finesses, Two_Way_Finesse, To_Finesse_Or_Not_To_Finesse): confirm
  the suit/entry that the lesson hinges on sits with the hand that the *real*
  opening lead and play actually route through. Worth an oracle/lead pass on
  each before generating their play coaching.

### Same-bug sweep of the avoidance/finesse play scenarios (2026-06-07)

Checked the other `oracle=shape` play scenarios for the same leader-seat bug
(danger suit in the wrong defender). West's opening-lead suit over each
500-board `bba/` pool:

- **Choice_Of_Finesses — SAME BUG, fixed.** West led a heart 0/500; East held
  the 5+ hearts on all 500. Rewrote `btn/Choice_Of_Finesses.btn`: long hearts
  + the SQ to **West** (so the SPADE finesse loses to the danger hand = fatal);
  CQ falls to East by elimination (so the CLUB finesse is safe); South keeps
  one heart stopper and ducks to exhaust East. Labels flipped vs the old prose
  (now: take clubs, avoid spades). MC verify: West leads a heart 59/60, 3NT
  makes DD 57/60. Needs the same pipeline re-run as Hold_Up_3N.
- **To_Finesse_Or_Not_To_Finesse — no seat bug, prose softened.** Suit contract
  (4S); the club finesse itself puts East on lead, so East-as-danger doesn't
  depend on the lead. But in a trump contract East cashes ≤1 heart before a
  ruff, so "East cashes a 5-card suit" oversold it. Reworded @chat to lead with
  count-your-tricks / no-upside; kept the heart danger as a footnote. No regen.
- **Two_Way_Finesse — structurally fine.** Pure two-way guess for the QD,
  hearts split evenly (W60/E66). Added a `# curate-note:` to the .btn: TIER by
  readability (prefer boards where an inference points one way), de-prioritise
  true 50/50s. (Parser-safe: `curate_directive` matches only `# curate:`.)

Net: two .btn redesigns (Hold_Up_3N, Choice_Of_Finesses) need David to re-run
`dlr+` through the pipeline (bba on the Windows VM); To_Finesse + Two_Way are
prose/curation-note only. All uncommitted.

### Hold_Up_3N play-coaching pilot + trick-map verification (2026-06-07)

Built the first play-stage coaching pilot on the redesigned Hold_Up_3N pool
(12 boards) and, in doing so, added a verification layer that the play
pipeline needs.

- **Layer A re-run** on the corrected pools (had to clear stale Jun-5
  `.progress` + JSON — resume is keyed by board ORDER, not deal hash): 63
  DD-necessary hold-ups / 500 (Hold_Up_3N), 500/500 avoidance-shaped (Choice).
- **Oracle-derived graded.json** for both (declarer discipline): holdup_required
  -> textbook hold-up; ok+avoidance_shaped -> textbook avoidance. Re-annotated
  bba-curated PBNs so deal_hashes match the new pool.
- **NEW `py/suit_tricks.py`** — exact single-suit double-dummy with known cards
  (seat-aware, positional finesses). `coach.py play-packets` now injects a
  verified `trick_map` (top / establishable per suit + development_suit) and the
  authoritative `opening_lead` into every packet, so the generating subagent
  NARRATES counts and the lead instead of computing them — that was the failure
  mode (board 1 first drafted "four spades" for a 3-trick suit and missed clubs
  as the real source). Fixed a `top_tricks` overcount on long 5-5 fits.
- **`play-splice` now cross-checks** the spliced pre-lead card against the
  computed standard NT lead (caught a HK-from-KQxxx slip; correct is 4th-best).
- Verified with the trainer's OWN `_strip_post_auction_blocks` + `parse_tips`
  (endplay parses, 4 tips per board, suit symbols render). All 12 boards
  reconcile to 9 tricks; all leads validated. `coaching-curated/Hold_Up_3N.pbn`.

Open: delete the now-shadowed hand-authored `coaching/Hold_Up_3N.pbn` (30
boards, broken under the redesign; trainer prefers coaching-curated/). Choice
play coaching not yet generated (graded.json ready). Other play scenarios
await fan-out through the same trick-map-grounded pipeline.

### Choice_Of_Finesses + Play_Top_Tricks_NT play coaching (2026-06-07, cont.)

- **Choice_Of_Finesses** (10 boards) — avoidance theme. Added a SAFE-LINE check
  (count only tricks whose forced loser goes to East, the safe hand); it doubles
  as the avoidance oracle and dropped boards 13/14 (safe line makes only 8 — they
  need the fatal spade finesse). Subagents told to develop the safe suit
  (clubs/diamonds into East), never the spade finesse, ignoring trick_map's
  DD-optimal development_suit when it points at spades.
- **Broken-sequence lead fix** (`curate.py _honor_sequence_top`): KQ10/QJ9 are
  leadable sequences — lead the top (K), not 4th-best. Was leading 4th-best and
  the prose contradicted itself ("top of sequence" over a 9). Fixed; regenerated
  Hold_Up_3N board 10 and Choice boards 1/2/10 (now lead \HK).
- **Play_Top_Tricks_NT** (11 boards) — count-winners. Filtered to top-sum >= 9
  (pure cash-out, per the .btn's "exactly 9 quick tricks" design); the
  count-winners grade also tags develop-one boards (those belong to
  establish-long-suit, not this lesson). Coaching: count first, cash unblocking
  high-from-short-hand, no finesse.
- All three verified via the trainer's own _strip_post_auction_blocks +
  parse_tips (4 tips/board, leads validated).

NEXT — the remaining 8 play scenarios are all SUIT contracts (4S/4H/6S):
Play_Top_Tricks, Play_Top_Tricks_Suit, Rabbis_Rule, Suit_Promotion,
Finesse_Simple, Endplay_3rd_Round_Strip, Side_Suit_Ruff_Before_Trump,
Two_Way_Finesse, To_Finesse_Or_Not. The NT trick_map (py/suit_tricks.py) is
WRONG for them (ignores trumps + ruffing). They need a trump-aware trick
analyzer before coaching — a real build. Their Jun-6 graded.json are still
valid (pools unchanged). Play_Top_Tricks_NT.pbn uncommitted.

---

## Claude Code session (2026-06-07, later) — defender_budget + issue triage

Picked up after the Cowork session above went idle (no repo writes for ~4.5h;
David closed the hung window). Coordinated by not touching Cowork's in-flight
files until confirmed idle. Everything below is committed + pushed to origin/main.

**Repo state at handoff — BOTH repos (Cowork straddles the content/engine split):**
- *Practice-Bidding-Scenarios* — working tree CLEAN, origin/main current; all of
  today's work below is committed + pushed.
- *AI-Bridge-Play-Trainer* — no uncommitted source work; last Cowork commit
  `715bbb1` (06-07 07:06, header/feedback UI). Only stray file is a stale May-23
  `activity-log.json` (harness session log, not work); no lock, no stranded work.

**defender_budget — new play-coaching ground truth (commit `0b458fca8`).**
- `py/defender_budget.py` — the HCP/shape counterpart of `suit_tricks.trick_map`:
  what declarer can KNOW (ns_hcp / defender_hcp = 40 − declarer+dummy) and INFER
  (per-defender split, silence from a passed-out auction, rule-of-11 on a
  4th-best NT lead) about the two hidden hands. Self-tested.
- Wired into `coach.py play_packets` (one field/packet) + documented in
  `GENERATOR-PLAY.md` ("Use the verified defender_budget", exact-fact-vs-hedged-
  inference discipline + difficulty gate).
- **Play_Top_Tricks_NT.pbn regenerated** with the "you hold N of 40, defence has
  M, nobody bid → count and cash" beat and COMMITTED (resolves the "uncommitted"
  note above). Hold_Up_3N + Choice_Of_Finesses can be re-spliced through the
  updated pipeline when convenient (composes with the trump-aware build: rule_of_11
  is NT-only / returns null for suit leads; ns_hcp/silent still apply).

**⚠ Reproducibility gap (matters for your suit-scenario work).** The curated
play-coaching selection is NOT reproducible from `coach.py play-packets` alone —
it only filters by tier+theme. Each scenario's extra filter lives only in this
bookmark's prose (e.g. Play_Top_Tricks_NT = count-winners + trick_map top-sum>=9).
Trust `.work/<scn>-play-boards.json` + the coach-JSON board numbers as the coached
set; **restore play-boards.json before any play_splice** or it splices nothing and
WIPES the tips. (Memory: reference_play_coaching_selection_filter.)

**Trainer-feedback issue triage (12 issues, all replied; 3 fixed+closed).**
Verified each claim before applying (issue authors are untrusted end users).
- Fixed+closed (commit `0a7b9a9ea`): #18 Hold_Up b1 (Rule of Seven → hold up
  once, was duck-twice), #21 BWTO b39 (semi-solid not solid), #23 BWTO b1 (2♠
  shows 5+ spades, not a raise; + show-NS seat fix).
- **Re-curation flags — YOUR domain (board bids the awkward call; replace, don't
  patch prose): #16 BWTO b15 (4-4-4-1 reverse-shaped), #22 BWTO b42 (opener
  passes 2NT invite with a max — confusing), #25 BMinor b6 (1♦-2♣ wrongly called
  a "reverse"; 17 + solid 6 wants 3♦), #26 BMinor b10 (jump-raise on a singleton
  ♣Q).** Mind the selection-filter gap when reselecting.
- UI (trainer repo, not coaching): #19, #20. Trackers: #8, #9 (count-your-tricks
  → fold bidding scenarios into the play generator).

**Also spotted:** Hold_Up_3N.pbn has 14 literal `—` (em-dashes play-splice
never decoded → render ugly). play-splice should decode JSON \u escapes.

### NEXT for Cowork
1. Your stated NEXT — the **trump-aware trick analyzer** for the 8 suit play
   scenarios — unchanged and still the big build.
2. The **4 re-curation flags** (#16/#22/#25/#26) — curation, watch the selection gap.
3. Optional: re-splice Hold_Up_3N + Choice_Of_Finesses through the
   defender_budget-aware pipeline.

---

## Cowork session (2026-06-07, later still) — trump-aware trick analyzer BUILT

Resumed after the restart, synced to `785addd88`. Picked up NEXT item 1 (the
big build). Committed under David's identity, NOT pushed (David pushes).

**`py/trump_tricks.py` (new) — the trump-aware counterpart of
`suit_tricks.trick_map`.** For suit contracts the NT map is wrong (winners get
ruffed; extra tricks come from ruffing, not only length). New
`trump_trick_map(hands, trumps, declarer, deal_str=None)` returns:
- **VERIFIED (exact DD):** `total` (declarer's double-dummy trick count in the
  trump strain, from endplay `calc_dd_table` — the hard cap), `dd_losers`
  (=13−total), per-side-suit `top`/`establishable` and the trump suit's
  `isolated_tricks` (all exact single-suit DD via `suit_tricks`, seat-aware so
  finesses are resolved), plus `missing_honors` per suit.
- **DERIVED planning aids (clamped consistent with `total`):**
  `ruffs_in_short_hand` (extra ruffs the short trump hand can make — the
  ruff-in-dummy headline), `side_top`/`safe_top` (winners cashable before a
  ruff), `sure_tricks` floor, `develop` (=total−sure_tricks).
- Assumes declarer's side is N/S (same as the NT map; every curated play board is
  seated South). `total` is still correct for an E/W declarer; only the
  decomposition is skipped there (`decomposition: None`).

**Verification.** Built-in `__main__` self-test over board 1 of all 9 suit
scenarios + a fan-out test of **270 suit-contract boards**: `total` matches
`calc_dd_table` on **every** board (0 mismatches), and invariants
(`sure_tricks ≤ total`, `establishable ≥ top`, `trump_iso ≤ trump_len`) hold
everywhere (0 breaches). NT and E/W-declared boards correctly route elsewhere.

**`py/curate.py` — new `opening_lead_vs_suit(leader_suits, trump_idx)`** (+
helper `_lead_card_from_holding`). The NT lead was being used for every contract;
suit contracts need their own standard lead: singleton → top of a touching-honour
sequence (incl. K from AK) → 4th-best from the longest side suit, **never
underleading a bare ace** (falls back to leading the ace itself, then a trump).
Tested on constructed holdings and real boards (e.g. Side_Suit_Ruff b1 leader
correctly leads `\D3`, skipping the bare ♣A).

**`py/coach.py` `play_packets` — now contract-aware.** Routes NT→`trick_map` +
`opening_lead_vs_nt`, suit→`trump_trick_map` + `opening_lead_vs_suit`, keyed off
the board's `[Contract]` strain. `play_splice`'s auto-lead cross-check is also
contract-aware now (it previously assumed an NT lead, which would have falsely
flagged every suit board). The packet field stays named `trick_map`; suit boards
carry the trump-aware shape (has a `trumps` key).

**`py/defender_budget.py`** — added an optional `strain` param; `rule_of_11` (an
NT-only tool) is suppressed for suit contracts. Backward compatible (NT pilot
self-tests unchanged, still pass).

GENERATOR-PLAY.md documents the new suit-contract `trick_map` shape + the
exact-vs-planning-aid discipline (ruff-in-dummy → `ruffs_in_short_hand`;
establish → largest `length_winners`; reconcile every narrative to `total`).

**NEXT (still for Cowork):**
- The build is done and wired; what remains is the **coaching fan-out** for the 8
  suit scenarios: run `coach.py play-packets <scn> <theme>`, subagent the prose
  per GENERATOR-PLAY.md, `play-splice`. Per-scenario selection FILTERS still live
  only in prose (the reproducibility gap) — decide each scenario's extra filter
  (e.g. Side_Suit_Ruff = ruff-in-dummy + `ruffs_in_short_hand ≥ 1`;
  Suit_Promotion = establish-long-suit + `length_winners ≥ 2`) and record it
  before `play-splice` (restore `.work/<scn>-play-boards.json` first).
- Then NEXT items 2 (the 4 re-curation flags) and 3 (re-splice Hold_Up/Choice).
- Note: the Cowork sandbox `.work/` mount refused `rm` (Operation not permitted)
  this session — stray test packets for Side_Suit_Ruff_Before_Trump remain in
  `.work/` (gitignored, overwritten by the next real `play-packets` run).

### First suit-contract play-coaching pilot — Side_Suit_Ruff_Before_Trump (12 boards)

Proved the trump-aware pipeline end-to-end through actual coached output (commit
follows). `coach.py play-packets Side_Suit_Ruff_Before_Trump ruff-in-dummy -n 12`
(boards 1,2,3,4,7,8,9,11,12,13,20,21 — all 4S by South, all make DD, all with
2-3 dummy heart-ruffs in `ruffs_in_short_hand`). Two subagents (one per packet)
authored the 4 `[ROLE]/[STAGE]` tips per GENERATOR-PLAY.md, grounded in the
trump-aware `trick_map` (count LOSERS, ruff hearts in the short hand BEFORE
drawing trumps) + `defender_budget` (exact HCP, hedged splits).
- `play-splice` clean (no lead/space/wrong-lead warnings).
- Verification: 12/12 coached, exactly 4 tips each, **0 em-dashes**, every
  pre-lead card matches `opening_lead_vs_suit`, all 500 deals still parse via
  endplay. The 9 multi-rank suit refs are all declarer's-own or leader's-own
  holdings (no hidden hand revealed). Spot-checked b1 + b12 (the tightest,
  exactly-making): principled ruff-in-dummy lines, correct singleton/4th-best
  leads, warm tone.
- **Selection filter (record for reproducibility):** declarer textbook/standard
  `ruff-in-dummy` + (implicitly) `ruffs_in_short_hand >= 2`, first 12. Board
  list in `.work/Side_Suit_Ruff_Before_Trump-play-boards.json` — restore it
  before any re-`play-splice`.
- Output is the 500-board pool with 12 coached (same convention as Hold_Up_3N /
  Choice / Play_Top_Tricks_NT). The old hand-authored
  `coaching/Side_Suit_Ruff_Before_Trump.pbn` (30 boards) is now SHADOWED by the
  curated file (trainer prefers `coaching-curated/`) — left in place for David to
  delete when convenient (same disposition as the Hold_Up shadow).

**UPDATE (same session): expanded to the full 30 boards** (added boards
24,25,29,32,33,35,38,40,41,42,43,51,54,56,62,64,65,66 via 2 more subagents).
All 30 validate: 4 tips/board, 0 em-dashes, every lead matches
`opening_lead_vs_suit`, no hidden-hand reveals, endplay parses. One board (40)
had `silent:false` and the subagent correctly dropped the "nobody bid" clause.

**NEXT:** fan out
the same trump-aware pipeline to the other 7 suit scenarios (Play_Top_Tricks,
Play_Top_Tricks_Suit, Rabbis_Rule, Suit_Promotion, Finesse_Simple,
Endplay_3rd_Round_Strip, To_Finesse_Or_Not / Two_Way_Finesse), each with its own
theme + selection filter. Then re-curation flags #16/#22/#25/#26.

---

## Claude Code session (2026-06-07, evening) — singleton-honor lead fix + Rabbis_Rule

Cowork flagged (then hung on) a real bug in `opening_lead_vs_suit`: it led ANY
non-ace singleton, INCLUDING a singleton honour — so e.g. all Rabbis_Rule boards
auto-led West's bare ♦K, exposing it at trick 1 and killing the cash-the-ace-to-
drop-the-K lesson. David confirmed the bridge call (you don't lead singleton
honours). After David killed the hung Cowork session, Claude Code did:

- **Fixed `opening_lead_vs_suit`** (`679e4dc26`): step 1 now leads only a SMALL
  (spot-card) singleton; a lone honour singleton (A/K/Q/J) falls through to the
  sequence / 4th-best logic. GENERATOR-PLAY.md lead rule updated to match.
- **Generated Rabbis_Rule play coaching** (theme `safety-play`, 30 boards,
  corrected leads) → NEW `coaching-curated/Rabbis_Rule.pbn` (supersedes the old
  hand-authored `coaching/Rabbis_Rule.pbn`). play_splice clean; 4 tips/board;
  every lead cross-checks; no singleton-honour leads (honour leads are all
  sequences, e.g. ♣Q from QJ9xx).
- **Re-coached + surgically spliced the 4 shipped stiff-honour boards** (only
  those blocks changed): Side_Suit_Ruff_Before_Trump b40 (now ♥4) & b42 (♣Q),
  Play_Top_Tricks_Suit b60 (♠J), Finesse_Simple b4 (♣5).
- Cowork's hung session was killed; its uncommitted sandbox work (Side_Suit_Ruff
  coach3/4 "18 boards", its Rabbis attempt) was discarded — regenerable, nothing
  lost in git. All of the above committed + pushed.

**Coached PLAY scenarios now (9):** Choice_Of_Finesses, Finesse_Simple,
Hold_Up_3N, Play_Top_Tricks, Play_Top_Tricks_NT, Play_Top_Tricks_Suit,
Rabbis_Rule, Side_Suit_Ruff_Before_Trump, Suit_Promotion.
**Remaining play scenarios:** Two_Way_Finesse, To_Finesse_Or_Not_To_Finesse,
Endplay_3rd_Round_Strip. Then re-curation flags #16/#22/#25/#26.

---

## Claude Code session (2026-06-07, late) — play-coaching fan-out COMPLETE

Generated the final 3 play scenarios with the corrected leads. Themes were read
from each scenario's `.btn` @chat (the authored lesson) — review if a different
lesson was intended:

- **Two_Way_Finesse** (theme `finesse-safe-hand`, 30 boards) — coach the two-way
  ♦Q-finesse DECISION via inferences (auction shape, opening lead, count, vacant
  places); defender_budget is the tool. (Genuine-clue boards are a minority of
  the pool per the earlier note, but the coaching teaches the reasoning either way.)
- **To_Finesse_Or_Not_To_Finesse** (theme `count-winners`, 30) — count first;
  the club finesse has no upside; decline it and claim.
- **Endplay_3rd_Round_Strip** (theme `endplay`, 19 — the entire qualifying set) —
  strip the side suits and throw East in instead of finessing.

play_splice clean for all three (every lead cross-checks), 4 tips/board. **ALL 12
PLAY SCENARIOS are now coached in coaching-curated/** (9 prior + these 3).

Remaining curation work: the re-curation flags #16/#22/#25/#26 (need David's ruling).

---

## Claude Code session (2026-06-08) — re-curation flags resolved (#16/#22/#25/#26)

David ruled: replace the 4 awkward boards. Swapped each for a clean,
textbook-graded board with a simple readable auction (David approved the picks):

- **Basic_What_To_Open**: b15 (4=4=4=1 into a 2/1 reverse-looking auction) →
  **b193** (open 1♥, six-card major); b42 (opener passes a 2NT invite with a
  max) → **b220** (open 1NT, 15-17).
- **Basic_Minor**: b6 (1♦-2♣ mislabeled a "reverse") → **b173** (1♦-1NT, open
  the longer minor); b10 (jump-raise on a stiff ♣Q) → **b225** (1♣-1NT).

New coaching generated per GENERATOR.md (rotation tokens, [BID] per call,
[show NS]); both files still 30 boards, `coach.py validate` = 0 issues, braces
balanced. GitHub issues #16/#22/#25/#26 to be closed.

---

## Cowork session (2026-06-08) — Rabbis_Rule slam-dilution + shape fix

Tackled open item 8 (Rabbi's Rule Blackwood dilution). Diagnosed from the
old 500-board pool: contracts were 246 6S (49%) / 165 4S (33%) / 58 5S /
20 3S — robots ran Blackwood on 343/500 and opened a strong 2C on 71.
Root cause is structural: the predealt honors South *needs* for the lesson
(♠AK + ♥A + ♦AQ) already total 17 HCP and three aces in a 6-card-suit hand,
so BBA correctly drives toward slam; South literally can't go below 17.
Slam rate scales with strength (S 17→38%, 18→44%, 19→59%; by combined:
23-24≈26%, 26≈55%, 27≈74%, 28≈94%).

Two edits to `btn/Rabbis_Rule.btn` (David's calls):
1. **`combinedHcp = hcp(north) + hcp(south) < 27`** — caps partnership
   strength to keep the auction in game.
2. **Shape caps** to lessen extreme distributions: West side suits <6 (no
   void / no 6+ suit with the stiff ♦K), East hearts 5-6 (not 7+) + no
   black-suit void + diamonds <6, North hearts/clubs <6, South no club void.

David ran the full pipe in VS Code and committed+pushed. **New distribution:
227 6S (45%) / 211 4S (42%) / 62 5S** — shape caps worked (freak 3S boards
gone, 4S pool grew 165→211), but `combined <27` only nudged slam 49%→45%
(most slams sit at combined 25-26, which the cap keeps). **OPEN:** if the
~45% slam rate still bugs David, tighten to `<26` (~36%) or `<25` (~26%) and
re-pipe — one-line change. Note: hand generation (dealer3) and bidding
analysis (bba-cli) are Mac-only and can't run in the Cowork sandbox; only
dlr/pbs regenerate there — David runs pbn+ in VS Code.

---

## Cowork session (2026-06-08, cont.) — coaching QA: voice bugs + suit-quality standard

Trainer spot-check of the competitive bidding scenarios surfaced a bug class
and a terminology standard. Learnings to carry forward:

- **Two coaching "voice" bug classes.** Coaching `[BID]` chunks use `@S` and
  the trainer's `fill_pronouns` renders it per-call as "You" or "Your
  partner" based on who actually made that call (server.py ~98-106, 1053-61).
  - **Partner-voice = NOT a bug.** `@S` on the *partner's* (other N/S seat)
    call renders correctly as "Your partner …" — e.g. Basic_Takeout_Double b46
    (North's 3♥ jump with the six-card suit) reads fine.
  - **Opponent-voice = REAL bug.** When the opponents (E/W) outbid and
    *declare*, an `[BID]` on their call is narrated in the student's voice —
    the trainer never remaps E/W, so it tells the student they made the
    opponents' bid. Found in **Basic_Takeout_Double b1/b2/b39/b47** (double
    got steamrolled, E/W declared). **RESOLVED (2026-06-09):** David chose
    replace. Swapped b1/b2/b39/b47 → b115 (1C-X-2S) / b201 (1D-X-2H) /
    b151 (1H-X-2S) / b378 (1S-X-2H) — textbook doubles, sound partner
    advances, opener silent, N/S declares, sensible final contracts; one of
    each opener. Fresh coaching authored per GENERATOR; `coach.py validate`
    and the anchor cross-check both 0; rendered correct from both seats via
    `fill_pronouns`. Committed c10faf523.
- **New validator check** in `py/coach.py validate`: flags any `[BID]` on an
  E/W call whose chunk carries a student token (`@S/@s/@Your/@your/@v(`).
  Calibrated — flags exactly the 4 above, Basic_Overcall clean. NOTE: `validate`
  is for BIDDING coaching only; running it on the 12 play scenarios prints
  "500 board(s)" noise (play files keep the full pool, ~30 coached, different
  format) — ignore that, or guard validate to skip play files (not yet done).
- **SUIT-QUALITY TERMINOLOGY** — adopt GIB's definitions (now recorded in
  `coaching-curated/GENERATOR.md`; source
  doc.bridgebase.com/lobbynews/gib_descriptions.html). Key trap: **"solid"
  requires AKQ** — solid 6-card = AKQTxx or AKQJxx. KQJxxx is "good"
  (rebiddable); AKQ9xx is "strong" (has AKQ, lacks T/J), still not solid.
  Fixed **Basic_Weak_2**: b9/b71 (♥KQJ) + b134 (♠KQJ943) "solid"→"good",
  b87 (♠AKQ952) "solid"→"strong"; left b37 "solid values" (HCP, not a suit).
- **Trainer feedback fix:** the "Report a problem" button needs `GITHUB_TOKEN`
  (fine-grained PAT, repo `ADavidBailey/AI-Bridge-Play-Trainer`, Issues RW).
  David had it in a gitignored `.env` but `server.py` never loaded `.env`;
  added a tiny built-in `.env` loader near the top of server.py (no
  python-dotenv dependency). Restart the server to pick it up.

Uncommitted at session end (two repos): `coaching-curated/Basic_Weak_2.pbn`,
`coaching-curated/GENERATOR.md`, `py/coach.py`, and trainer `server.py`.
(All committed + pushed by David shortly after.)

---

## Cowork session (2026-06-09) — play-coaching opponent inference: Hint engine + voice refit

David's goal: play coaching should lean on **inferences from the opponents'
bids / silence and speculate on their HCP & shape** — and update trick-to-trick.

**Two layers, both addressed:**

1. **Live Hint engine** (`AI-Bridge-Play-Trainer/static/app.js`, `computeHintLines`)
   — this is the trick-to-trick layer; it recomputes from the play on every
   Hint click. Enhanced it (commit 4fccf31) with, declarer-view, public-info-only,
   hedged, NO play advice:
   - per-defender **shape from show-outs** ("RHO void in ♥ → remaining cards lie
     in the other suits, where length/honours concentrate"),
   - **firm honour placement by void-deduction** ("♥K still out: RHO void in ♥,
     so it's now marked with LHO"),
   - **hedged vacant-spaces lean** once a void skews the shape ("…leans LHO's
     way — a tendency, not pinned"); no lean while symmetric (no misleading
     early reads). Rides on the existing HCP-complement / auction / rule-of-11
     reads. Tested offline with synthetic states. David: "ok for now."

2. **Static PBN play coaching** voice refit. Tightened `GENERATOR-PLAY.md`
   (commit 46d086943): the opponent read is now **mandatory on every board** —
   auction-end states the exact HCP complement + silence read; post-lead turns
   lead+auction+vacant-spaces into a **placement INFERENCE**. **Two David voice
   rules (load-bearing):** (a) STATE the inference, **WITHHOLD the conclusion** —
   give "the ♥K probably sits with West" and STOP; never append "so finesse West";
   (b) **HEDGE the length read** too ("the club length *probably* sits with
   West" — a 4th-best can be from four or five).
   - **Finesse_Simple pilot regenerated** to this voice (commit fe83381ac): 30
     boards via subagent fan-out (2 packets), reconciled to trick_map, validated
     — 0 banned-conclusion phrases in any tip, length hedged, HCP complement on
     all 30, endplay-parses, lead cards verified by play-splice.
   - **REMAINING:** the other 11 play scenarios are still in the old voice —
     fan them out the same way when ready. Inconsistency was worst on Hold_Up_3N
     / Choice_Of_Finesses / Finesse_Simple; Play_Top_Tricks_NT was already good.

**Standing interaction preferences (David, this session):**
- When a **push** is needed, DISPLAY the exact `git push` command(s) for copy/paste.
- When the **server** needs (re)starting, DISPLAY the start command for copy/paste.
- A **static-JS** change (app.js) needs only **Cmd-Shift-R** in the browser — no
  server restart; only `server.py` changes need a restart. Trainer reads the
  LOCAL `Practice-Bidding-Scenarios` folder (BRIDGE_DATA_ROOT), so testing needs
  no push — push is only to back up / share.
- Cowork commits, David pushes (no push from Cowork). Stale `.git/*.lock` files
  accrue from the sandbox's filesystem quirk — clear with `find .git -name '*.lock' -delete`.

**Open (pending David):** UX idea — render each new Hint at the TOP of the hint
window (newest-first) so changes are obvious; keep scroll-up for history.
→ DONE: Hint panel now renders hints newest-first at top, freshest highlighted
(trainer commit 7f0569a).

---

## Cowork session (2026-06-09, later) — trainer feedback issues #29–#32 processed

The in-app "Report a problem" button now works (GITHUB_TOKEN wired up) and files
issues into **ADavidBailey/AI-Bridge-Play-Trainer** (public repo, label
`user-feedback`). Read them via the GitHub API (no connector auth needed for a
public repo): `https://api.github.com/repos/ADavidBailey/AI-Bridge-Play-Trainer/issues?state=open&labels=user-feedback`.

- **#32 Choice_Of_Finesses b1 "You and dummy hold 0 HCP???"** — LATENT TRAINER
  BUG, now fixed (commit 622d86b). `handHcp` + `computeHintLines` read full-name
  suit keys (`hand["spades"]`) but the server's `hand_to_dict` emits **letter
  keys with arrays** (`{S:["A","K"],…}`). So HCP was ALWAYS 0 and the
  outstanding/rule-of-11/placement reads misfired on every board. Fixed to
  letter keys + array iteration; re-tested against the real format (28 HCP now).
  LESSON: trainer hand objects are `{S/H/D/C: [rank,…]}`, NOT full-name strings.
- **#29 Basic_Weak_2 "upgrade board shouldn't be board 1"** — fixed (a56301853):
  the trainer serves boards in FILE ORDER (`boards[board_index]`, default 0), so
  moved the 1♥-upgrade judgment board out of the first slot; a clean weak two
  leads now.
- **#30 Basic_Weak_2 b9 "not a solid suit"** — already fixed earlier (solid→good).
- **#31 Finesse_Simple b2 was an uncoached, opponent-declared deal** — root cause:
  play coaching-curated files kept all 500 pool boards (only ~30 coached), so the
  trainer served uncoached junk. David's call: **TRIM**. All 12 play files now
  contain ONLY their coached boards (commit 34ef8078f) — matches the bidding
  convention; the pool still lives in `bba/`/`bba-curated/`. Coached counts:
  Choice_Of_Finesses 10, Endplay 19, Hold_Up_3N 12, Play_Top_Tricks_NT 11, the
  rest 30.

Issues #29/#30/#32 are resolved and can be closed on GitHub (David closes, or
authenticate the github connector to close with commit refs). **Still old-voice:**
the 11 non-Finesse_Simple play scenarios need the inference-voice fan-out when ready.
