# Bridge Play Trainer

A self-paced web tool for practicing the **play** of bridge hands — declarer technique, defense, and reading the auction. The trainer reuses the scenario library from Practice-Bidding-Scenarios and adds an interactive play surface backed by [endplay](https://github.com/dominicprice/endplay) for legality checking and double-dummy resolution.

## Who it's for

There are lots of sites focused on bridge bidding. **This site is for those wanting to play their cards better.** The UI is plain, large, and forgiving — large fonts, no timed animations, gentle errors, generous click targets. Coaching is **built into the scenario files** as precomputed tutorial prose, so a new user gets a fully working, self-explaining trainer with no setup, no account, and no API key. There are **no outbound calls to any AI service at runtime.**

## Where the code lives

The trainer is a **separate repository** from Practice-Bidding-Scenarios:

- Code: `~/AI-Bridge-Play-Trainer` — [github.com/ADavidBailey/AI-Bridge-Play-Trainer](https://github.com/ADavidBailey/AI-Bridge-Play-Trainer). Ships code only.
- Data: *this* repo (Practice-Bidding-Scenarios) supplies the scenarios the trainer plays — the coaching PBNs in [coaching/](../coaching/) and the menu layout in [btn/-button-layout-release.txt](../btn/-button-layout-release.txt).

The server resolves its data location from `BRIDGE_DATA_ROOT`, defaulting to `/Users/adavidbailey/Practice-Bidding-Scenarios`.

## How to run

```bash
cd ~/AI-Bridge-Play-Trainer
python3 -m uvicorn server:app --reload --port 8765
```

Open <http://localhost:8765> in any modern browser. No build step, no test suite, no lint config. Override the data location with `BRIDGE_DATA_ROOT=/some/path` if the scenarios live elsewhere.

## How to use

1. **Pick a scenario** from the left sidebar. Sections collapse; a sticky search box filters. Only scenarios that ship with an embedded coaching file are user-pickable — the menu is restricted to those, so every selectable deal is fully coached.
2. **Pick a role**: Declarer (user controls declarer + dummy), Leader (the opening leader / defender on lead), or Defender (the leader's partner). The UI today is tuned for declarer; defender roles are functional but less polished.
3. **Optionally set a deal number** to jump to a specific board; otherwise it starts at the first.
4. **The auction animates bid-by-bid** in the center, interleaved with the scenario's tutorial prose (see below). Hands reveal progressively as the coaching calls for it. A **Play** action starts the card play once the auction is done — non-user seats (e.g. the opening lead) auto-play until it's your turn.
5. **Click cards in your hand** to play. Legal cards are highlighted; non-user seats (defenders, and dummy when you aren't declarer) are auto-played by the double-dummy solver.
6. **After each trick**, a brief freeze shows who won; the **trick-counter strip** below the table tracks our-side vs opponent tricks.
7. **Controls below the table**:
   - **Undo** — rewinds your last decision (and everything the auto-player did in response). Implemented by replaying the full move-log, because endplay's `unplay()` can't cross trick boundaries.
   - **Hint** — surfaces card-counting facts derived from the trick history so far.
   - **Review** — press-and-hold to re-show the auction (pointer capture keeps it up if your finger drifts off-button).
   - **Replay** — reset to the opening-lead state.
   - **Claim** — the solver plays out the remaining tricks.
   - **Next deal** — same scenario, next board.
8. **Coaching panel** (center, below the table): renders the bid-by-bid tutorial prose and the post-auction planning notes. Its title bar doubles as a **Scenarios picker** — click it to switch scenarios without leaving the play view.
9. **Result panel** appears when the deal completes (all 13 tricks or a claim): contract, made/down, and all four hands.
10. **Session IMPs** in the header keeps a running total vs double-dummy across the deals you play in this tab.

## Bridge table layout

The board is rotated so the **user always sits at the bottom (South in the display frame)**. Partner top, LHO left, RHO right. Everything — auction calls, contract banner, seat labels, hands, trick history, trick totals — relabels together, regardless of which seat the scenario actually dealt.

Under the hood the `Deal`, the DDS calls, and the dealer engine all use **real compass**; only the outgoing API payload is rotated (`_rotation_shift`, computed once per session). When debugging: a seat letter in the API `state` is in the display frame; a `Player` enum inside a `Session` is real compass.

## Embedded coaching (precomputed PBN tutorial prose)

Coaching is authored directly into the scenario PBNs as a Baker-Bridge–style tutorial block that follows the `[Auction]` tag. There is no AI at runtime — all prose is precomputed upstream.

```
[Auction "N"]
1H Pass 2D Pass 2NT Pass 3NT Pass Pass Pass
{[show S]
After North's 1\H opening South counts 12 HCP plus one length point for the
fifth \D. What do you bid?[BID 2D]
That is enough for a 2/1 response so South says 2\D. ...[BID 3NT]
South is happy to play in Notrump ...
[show NS]}
```

Recognised markers:
- `[show X]` — `X` is one or more seat letters (`N`, `EW`, `NSEW`, …) in **real** compass; reveals accumulate as the auction steps forward.
- `[BID xxx]` — anchors the chunk to the next unconsumed matching call in the auction (`1C`, `2D`, `3NT`, `X`, `XX`; case-insensitive). Prose before the first `[BID]` is the intro chunk. Unmatched `[BID]`s degrade to the previous successfully-anchored chunk.
- `\S \H \D \C` — substituted server-side to `♠ ♥ ♦ ♣`.

The parser only inspects the curly block immediately after `[Auction]`; pre-auction `{Shape ...}` / `{HCP ...}` / `{Losers ...}` blocks in the older `bba/*.pbn` files are ignored, and stripped before endplay parses the PBN. Coaching reveals are kept in the **author's real-compass frame** so the PBNs stay portable; the frontend maps them through `state.rotation_shift`. Scenarios without an embedded coaching block simply play normally (`state.coaching === null` skips the tutorial path).

The trainer prefers `coaching/<scenario>.pbn` and falls back to `bba/<scenario>.pbn`. Authoring conventions for these files — every marker, the section ordering, and the rules — are documented in [coaching/README.md](../coaching/README.md); the upstream generation plan (how the files are produced) lives in the trainer repo's `pbn-coaching-generator-plan.md`.

## Backend (FastAPI)

All backend logic lives in one file, `server.py` (in the trainer repo). A `Session` owns the full state of one in-progress deal; sessions are held in an in-memory dict keyed by an opaque token — no persistence, no auth, single-user local app. Non-user seats are auto-played by the double-dummy solver (`endplay.dds.solve_board`), and the deal's DD table is cached once per session for scoring. Scoring is reported as **IMPs vs double-dummy** from the student's perspective, undoubled (the trainer doesn't model doubles).

| Endpoint | Purpose |
|---|---|
| `GET /api/scenarios`, `GET /api/menu` | Scenario list + sidebar sections, restricted to scenarios that have embedded coaching. |
| `POST /api/session` | Start a session: scenario + deal number + role. Returns initial state. |
| `GET /api/session/{sid}` | Current state (auction, visible hands, trick history, coaching chunks, rotation shift). |
| `POST /api/session/{sid}/play` | Play one card. |
| `POST /api/session/{sid}/start-play` | User clicked Play in the auction overlay — auto-play non-user seats (e.g. the opening lead) until it's the user's turn. Idempotent. |
| `POST /api/session/{sid}/undo` | Rebuild the deal from the move-log up to the previous checkpoint. |
| `POST /api/session/{sid}/replay` | Reset to the opening-lead state. |
| `POST /api/session/{sid}/claim` | Solver plays out the remaining tricks. |
| `DELETE /api/session/{sid}` | End the session. |

## Frontend

Plain HTML/CSS/JS, no build step:
- `index.html` — markup for the table, sidebar, coaching panel (which doubles as a Scenarios picker), and result panel.
- `style.css` — layout (sidebar + table area), seat slots sized to prevent reflow during play.
- `app.js` — state, render, API calls, the bid-by-bid auction animation, and progressive `[show]`-based hand masking. Polls the session and re-renders.

## CLI prototypes (predecessors of the web MVP)

`pipe1.py` … `pipe5.py` in the trainer repo are standalone terminal walkers, in evolutionary order. They predate the web UI and are kept as references / scratch tools (run `python3 pipeN.py`; `pipe5` takes `--role declarer|defender_e|defender_w`). Useful for exercising deal/play logic in isolation.

## Roadmap

- **Defender polish**: bring the leader/defender roles up to the declarer experience.
- **End-of-session summary**: aggregate score across multiple deals (the header already tracks running session IMPs).
- **Wider coaching coverage**: author tutorial blocks for more of the scenario library so more scenarios become user-pickable.
- **Found-scenario integration**: surface the curated "Found_Endplay" / "Found_Rabbis_Rule" decks in the sidebar even though they were removed from the BBO button layout.
- **Cross-platform topTricks**: port `script/topTricksNS` / `script/topTricksSuitNS` so the trainer can grade "sure tricks" objectively.

## Status snapshot

See [Basic_Bidding_and_Play_Status.md](Basic_Bidding_and_Play_Status.md) for where the scenario library stands. The trainer consumes that library; improvements on either side compound.
</content>
</invoke>
