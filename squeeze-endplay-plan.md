# Squeezes & Endplays — family plan

Design + working plan for the **second play-technique family**, following the pattern proven by
[finesse-family-plan.md](finesse-family-plan.md). Started 2026-07-03 (David + Claude). The shelf is
David's call ("Squeezes & Endplays shelf"); the faceted-section design comes from the finesse plan §6.

**Status: SHELF COMPLETE — all five lessons + the exam live (capstone shipped 2026-07-04).**
`Strip_And_Endplay`, `Simple_Squeeze`, `Rectify_The_Count`, `Show_Up_Squeeze`, `Double_Squeeze`
(3 boards each) + `Squeeze_Endplay_Exam` (6 boards). Toc section
`Play of the Hand: Squeezes & Endplays` live in both toc files.

---

## 1. The family — planned progression

| # | Lesson | Owns the skill | Status |
|---|---|---|---|
| 1 | **Strip_And_Endplay** | Strip the side suits, throw a defender in, force the lead you wanted — the 50% finesse becomes 100% | live |
| 2 | **Simple_Squeeze** | One defender guards two suits: rectify, run the long suit, watch the discards | live |
| 3 | Rectify_The_Count | Losing your losers EARLY as its own skill (the squeeze's ignition) | live |
| 4 | Show_Up_Squeeze | The run bares the honor — the "finesse" at the end is no longer a guess (bridges back to the finesse family) | live |
| 5 | Double_Squeeze | Both defenders, three suits — the capstone | live |

Endplay before squeeze in the learning order: the throw-in is concrete (a defender physically on
lead, visibly stuck) while the squeeze is abstract (a card silently promoted). Both assume the whole
finesse family — especially counting and Deep_Finesse's odds discipline.

**Boundary guards:**
- The finesse family owns *which/whether/how* of finesses. This shelf owns **tricks won without
  a finesse** — by force of position (throw-in) or of discards (squeeze).
- Show_Up_Squeeze will straddle: primary home HERE, cross-listed to Finesses later per the faceted
  design (finesse plan §6).

## 2. Teaching backbone

1. **Count winners AND losers** — both techniques begin exactly where the finesse family ended.
2. **Rectify the count** (squeeze) / **strip the exits** (endplay): give away your unavoidable
   losers EARLY, while you still control what happens next.
3. **Identify the position**: two menaces + one busy defender (squeeze); a tenace + a defender with
   only losing exits (endplay).
4. **Execute mechanically**: run the long suit and *watch the discards*; or throw him in and let
   him play your suit for you.
5. Through-line: *"the defenders' cards are fixed — make them play against themselves."*

## 3. Engine fidelity

- Both techniques render **faithfully** in the recorded-`[Play]` + replay-bot engine: the teaching
  inferences are **fixed defender discards/exits**, not signals. DD lines *love* squeezes and
  endplays — the acid is confirming the story reads at single-dummy tempo, same as the finesse gates.
- The endgame click-out tedium is real here (squeeze hands win the last 4-5 tricks on promoted
  cards) — one more argument for the **B8 Claim button** parked with Rick.

## 4. Sourcing

- **Strip_And_Endplay**: two PURPOSE-BUILT pools already exist — `Found_Endplay` (500 boards
  hand-scanned by find_endplay_candidates.py: 4M by South, A-J tenace + strip suits, East to be
  thrown in) and `Endplay_3rd_Round_Strip` (4♠, kind=soundness). Harvest = line-acid over those.
- **Simple_Squeeze**: no dedicated pool — fresh `squeeze_detect.py` harvest over NT/slam pools.
- Universal gates as proven in the finesse plan §9: makes EXACTLY; **re-verify under West's REAL
  lead**; the DD line must genuinely execute the taught technique (dump-read every finalist).

## 5. Detectors (py/finesse-harvest/)

- `endplay_detect.py` — throw-in signature: a defender wins a trick and his forced return either
  runs **into a tenace** (declarer wins with a card the leader could still beat — he led away from
  his guard) or concedes a **ruff-and-sluff** (both declarer hands void, trump wins). DD defense
  only concedes like that when genuinely stripped.
- `squeeze_detect.py` — promoted-winner signature: a declarer card wins a late plain-suit trick
  although the defense started with higher cards, and **every beater was discarded** on other
  suits' leads (never played to the suit). Under DD a guard is pitched only when every alternative
  is as bad — that IS the squeeze. Two-menace hint recorded (same defender stripped elsewhere).

## 6. Progress log

- **2026-07-03** — Shelf green-lit by David. Detectors written; scans launched (both endplay pools;
  18 NT/slam pools for squeezes). Plan doc created.
- **2026-07-03** — **Strip_And_Endplay shipped** (3 boards from Found_Endplay: the textbook trump-Q
  throw-in with both punishments visible; the timing study where the trump K wins exactly when West
  is stripped; the manufactured throw-in that solves an unpickable guarded trump queen). 75 raw →
  22 late into-tenace → 3 survivors; trick-1 "throw-ins" are lead artifacts, and passive-line hits
  keep dying under real leads.
- **2026-07-03** — **THE structural fix, finally codified:** `book_lead()` (singleton → top of
  touching honors → fourth-best → don't-underlead-aces) now lives in `squeeze_detect.py` in place
  of the synthetic passive lead, so the acid runs on a realistic line FIRST-pass. First scan under
  passive leads: 80 candidates, first three dumps all evaporated (0-for-3). Rescan under book
  leads: 77 candidates whose dumps AGREE with the scan. Port `book_lead` into the other detectors
  before their next use.
- **2026-07-03** — **Simple_Squeeze shipped** (3 boards): 4♥ Stayman intro (East abandons the ♣Q on
  dummy's last spade; the jack wins trick 13), 6NT classic (rectify at trick THREE — visible! — run
  five spades, West breaks twice, dummy's ♣9 wins trick 13; **EPBot's playout went one down**, the
  third bot-rescue board of the day), 6♥ trump squeeze (the last trump forces East's ♠J; the EIGHT
  scores at the death). Squeeze funnel: 77 → 24 honor-pitch → 3 authored.
- **2026-07-04** — **THE TABLE-vs-LINE GATE BUG found and fixed.** The scans gated makes-exactly on
  the DD *table*, but a gifted book lead makes the *line* one trick richer — check_served caught
  four freshly-authored boards playing +1 against their Result tags, and the technique stops being
  load-bearing at need+1. Fix in two layers: `line_tricks()` in harvest_common with every
  line-scanning detector now gating `line == need` (finesse_taken was already line-based), and a
  `post_count.py` sweep re-filtering existing scan JSONs. Casualties re-slated: Rectify lost
  b118/b83, Show_Up lost b139/b62, the exam's pending Choice board b291 died too.
- **2026-07-04** — **Rectify_The_Count shipped** (3 boards, all 6NT, all line-exact): the arc is a
  duck-timing progression — duck at trick ONE (b428: the ♦9 wins trick 13), duck at trick TWO
  (b185: concede the diamond the suit owed anyway; the ♦8 at trick 13), duck at trick FIVE into
  the queen while holding A-T over her (b233: dummy's ♣5 wins trick 12).
- **2026-07-04** — **Show_Up_Squeeze shipped** (3 boards, line-exact): 3NT hook-hook-then-the-count
  (b237: West's 4-long ♠K rises into the ace), 3NT the un-pickable K-7-5-3 picked up anyway (b184:
  pressure first, finesses second, drop last), 6NT where East's own discard is the confession
  (b92: one hook, one cashed king, the ace drops the queen, the SEVEN scores). Shelf = 4 lessons.
- **2026-07-04** — **Double_Squeeze: the full-corpus hunt came back DRY.** All 344 pools, 1,734
  squeeze-family candidates, exactly ONE double hit (2N_Smolen 13, the ♦4/♣2 board) — and it fails
  the line gate: its line takes all THIRTEEN tricks, the defense never scores, so the double
  squeeze was overtrick garnish, not the make. A teaching double squeeze needs makes-exactly WITH
  the squeeze load-bearing, and that intersection appears empty in these pools. Paths if wanted
  later: widen the acid (length-menace doubles, where one menace scores by running rather than as
  a led-suit promoted winner), or last-resort dealer generation (finesse plan §4). The shelf's
  capstone slot stays honestly open.
- **2026-07-04** — **Squeeze_Endplay_Exam shipped** (6 boards, exam voice, all line-exact) — David
  asked "I can't find the squeeze exam" and the answer was to build it. Coverage: Simple Squeeze ×2
  (a 4♠ where the last trump squeezes out West's diamond jack, and the 6♠ crown jewel where West
  pitches the very KING the beginner would finesse for), Strip & Endplay ×2 (East thrown in with his
  spade king → forced diamond into A-Q-T-9; West given his diamond queen → forced club into J-T),
  Show-Up ×1 (the queen counted out of hiding), Rectify ×1 as the FINALE — duck trick one, and the
  FOUR of spades takes a trick ("the trick you surrender at trick one buys the endgame"). Endplay
  candidates' stored leads predated the book-lead port — recomputed and re-verified per board.
  Shelf = 4 lessons + exam; the two-shelf curriculum now mirrors: each ends in a no-labels test.
- **2026-07-04** — **Double_Squeeze SHIPPED (3 boards) — the widened acid found the well.** The
  diagnosis: the old "double" class demanded TWO promoted winners with distinct victims, but a
  textbook double squeeze scores exactly ONE extra trick — the common suit's menace, which BOTH
  defenders abandon; the side menaces threaten, they never cash. New `double_squeeze_detect.py`
  keys on one promoted winner whose pitched beaters came from both defenders (covers the length
  menace by rank: against a low winner, every outstanding card is a beater). Full 344-pool rescan:
  14 candidates, 15 both-pitch hits, 0 of the old two-menace shape. Dump-reads killed 11 — the
  mirage catalog: spare winners at the death (b45 pitches a high ♣A on the "fruit"; b5 dummy sheds
  a good ♣K), guards extracted by force rather than squeeze (b237, b126), Qx "guards" that were
  always crashing (b220), finesse-dressed endings (b423) — and confirmed 3, all line-exact under
  book leads: **b153/3N** (6NT canonical: rectify at six, run, and the ♠2 wins trick 13 — E guards
  ♣J vs the 7, W guards ♥J vs dummy's 8; makes 12 under EVERY tested lead), **b176/Smolen** (6NT
  split menaces: dummy's ♥8 vs W, declarer's ♦7 vs E, the club ace gathers BOTH honors, dummy's
  ♣3 at trick 13), **b444/Impossible_2S** (4♣ — a GAME-level double with both side menaces
  stacked in diamonds at two heights; the ♥3 wins trick 12; the spade lead is West's natural
  attack and the strict line — a diamond lead concedes 11, noted in Curate). b318/w30plus genuine
  but narratively tangled — left in the well. Served gates: 12/12, 12/12, 10/10 exact.
