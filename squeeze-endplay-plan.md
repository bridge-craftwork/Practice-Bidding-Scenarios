# Squeezes & Endplays — family plan

Design + working plan for the **second play-technique family**, following the pattern proven by
[finesse-family-plan.md](finesse-family-plan.md). Started 2026-07-03 (David + Claude). The shelf is
David's call ("Squeezes & Endplays shelf"); the faceted-section design comes from the finesse plan §6.

**Status: SHELF LIVE — first two lessons shipped 2026-07-03.** `Strip_And_Endplay` (3 boards,
`414d27952`) and `Simple_Squeeze` (3 boards). Toc section `Play of the Hand: Squeezes & Endplays`
live in both toc files. Next rungs (Rectify / Show-Up / Double squeeze) await fresh wells.

---

## 1. The family — planned progression

| # | Lesson | Owns the skill | Status |
|---|---|---|---|
| 1 | **Strip_And_Endplay** | Strip the side suits, throw a defender in, force the lead you wanted — the 50% finesse becomes 100% | live |
| 2 | **Simple_Squeeze** | One defender guards two suits: rectify, run the long suit, watch the discards | live |
| 3 | Rectify_The_Count | Losing your losers EARLY as its own skill (the squeeze's ignition) | later |
| 4 | Show_Up_Squeeze | The run bares the honor — the "finesse" at the end is no longer a guess (bridges back to the finesse family) | later |
| 5 | Double_Squeeze | Both defenders, three suits — the capstone | later |

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
