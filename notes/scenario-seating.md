# Scenario seating — where to put the student

Design rule for which seat the student occupies in a bidding scenario, so the
trainer quizzes the *interesting* decisions. From Rick Wilson (who deploys the
trainer), 2026-06-06, confirming + refining the Basic_NT_Response pilot.

## How the quiz works (Rick)

The quiz hands the first set of questions to **the first seat that has a real
choice**, then alternates between the two partners, bouncing back and forth as
the auction develops. For a 1NT auction it skips the (forced) opening and
starts at the response.

## The rule (simplified 2026-06-06)

**Use rotation, not new scenarios.** "Randomly Rotate" (the ↕ toggle in the
PBS extension, BBO's checkbox, the uploader's R2) seats the student in both
the opener and responder seats across the deals, and the quiz starts at the
**first seat with a real choice** — so the student is quizzed on the
interesting decision regardless of which way the deal rotated. This holds for
both short auctions (1NT + a response) and longer ones (1-major/minor with
rebids). No mirrored or alternating-opener scenarios are needed.

This supersedes the earlier idea of building per-seat mirror scenarios
(`Basic_NT_Response`) and dealer-code alternation (`Basic_Major_Both`) — both
retired, because rotation does the job from the existing single scenario and
reuses its curated deals.

**The only opener-seated exceptions** are scenarios where the *opening itself*
is the lesson and rotation would defeat the point:
- `Basic_What_To_Open` — choosing the opening bid is the decision under test.
- `Basic_Weak_2` — deciding whether/what to preempt is itself a judgment call.

## Two ways to get "both seats" — and which to use

There are two mechanisms for putting the student in both seats:

1. **Rotation at play/upload time (preferred for longer auctions).** A 180°
   rotation spins the whole deal so the student (always South) holds what was
   North's hand on the rotated copy — i.e. opener on one copy, responder on
   the other. This is a checkbox/setting, not new content:
   - BBO Practice Table: **"Randomly Rotate"** checkbox.
   - PBS VS Code extension: the **↕ (double-headed arrow) toggle** in the
     button grid, next to Start Bidding Table / Start Teaching Table /
     Auction Compare.
   - pbs-deal-archive-uploader: the rotation radio (**2** = 180°, 4 = 90°).
   - AI-Bridge-Play-Trainer: rotates internally; coaching is stored in real
     compass and mapped by `rotation_shift`, so coached prose follows the
     rotation correctly.
   Rotation reuses the existing curated/coached deals — no new pipeline run.

2. **Dealer-code alternation (only when you need it baked into one PBN).**
   A disjunction over which side holds the opener (below) produces a single
   pool whose *boards* already mix the seating. Use this only when the deals
   must travel as one static file with mixed seats and you can't rely on the
   play environment's rotation. (Pilot: `Basic_Major_Both.btn`.)

**Rule of thumb:** keep the single scenario and turn on rotation
(mechanism 1) for both short and longer auctions — the quiz starts at the
first seat with a real choice, so the student always lands on the interesting
decision. Dealer-code alternation (mechanism 2) is a rarely-needed fallback,
only when deals must travel as one static file and you can't rely on the play
environment's rotation. (Earlier worry that rotation wastes short-auction
boards on the forced opening was wrong — the quiz skips the forced call.)

## Implementing "alternate opener" in dealer code (fallback)

Make the deal condition a disjunction over which side holds the opener shape:

```
# opener-shape / responder-shape predicates for each seat
sOpen = <opener constraints on south>
nOpen = <opener constraints on north>
sResp = <responder constraints on south>
nResp = <responder constraints on north>

# either South opens (North responds) or North opens (South responds)
(sOpen and nResp) or (nOpen and sResp)
```

Roughly half the produced deals seat the opener on each side, so the student
sees both. BBA bids from the hands, so the auctions come out correct either
way. (Keep E/W weak as before so the auction stays uncontested unless the
scenario is about competition.)

## Status of the current bidding scenarios

| Scenario | auction length | seating to use |
|---|---|---|
| Basic_NT | short | single scenario + **rotation** (Basic_NT_Response retired) |
| Basic_Weak_2 | opening IS a judgment call | student = opener (correct) |
| Basic_What_To_Open | the *opening* IS the decision | student = opener (correct) |
| Basic_Major | longer (rebids) | single scenario + **rotation** |
| Basic_Minor | longer (rebids) | single scenario + **rotation** |
| Basic_Overcall | competitive | single scenario + **rotation** |
| Basic_Takeout_Double | competitive | single scenario + **rotation** |

Both pilots retired 2026-06-06: `Basic_NT_Response.btn` (short-auction mirror)
and `Basic_Major_Both.btn` (dealer-code alternation) — rotation covers both
cases from the existing single scenarios and reuses their curated deals. The
dealer-code disjunction recipe is kept above only as a documented fallback.

`Basic_What_To_Open` is the exception that proves the rule: when the decision
under test is the opening bid itself, the student belongs in the opener's seat
and no re-seating is wanted.

## Note

The play scenarios (declarer/defense) already sit the student where the stream
of decisions is (declaring South), so this rule is a bidding-scenario concern
only.
