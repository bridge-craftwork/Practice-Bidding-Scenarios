# Coaching Board Curation — Proposal

**Author:** David Bailey · **Date:** 2026-06-02 · **Audience:** Rick Wilson

## Summary

Each Play-of-the-Hand coaching scenario teaches one technique (a hold-up, a safe finesse, a suit promotion) on **30 hand-picked boards**, drawn from the much larger on-pattern pool that the pipeline's `filter` step produces (`bba-filtered/*.pbn`, ~150–500 boards per scenario). Today that pick-of-30 is essentially "the first 30," with no quality check. A short, automated **curation step** — sitting between `filter` and the coaching-authoring stage — would score every candidate board and select the best 30.

I prototyped it and measured the payoff. The headline: a cheap **double-dummy quality gate** removes real defects (9% of current play boards present a contract that best defense beats, or that is declared from the wrong seat), and for "by-force" lessons it also positively selects good boards. A second, more expensive phase (single-dummy simulation) is needed to positively select the *avoidance* lessons — and the prototype proved **why** that phase can't be done with a double-dummy solver.

## The problem this solves

Two distinct defects show up in the current 30-board sets, both detectable with a double-dummy solver (DDS):

1. **Best defense beats the contract.** The board is taught as "you make 3NT," but on perfect defense declarer is held a trick short. Weak teaching example.
2. **Wrong-sided.** The contract makes — but only from the partner's seat, not the student's (South). The student is set up to fail through no fault of the line.

### Defect inventory (current curated sets, scored by DDS)

| Scenario | boards | sound | wrong-sided | down both sides | defect % |
|---|--:|--:|--:|--:|--:|
| Suit_Promotion | 30 | 22 | 1 | 7 | **27%** |
| Hold_Up_3N | 30 | 24 | 2 | 4 | **20%** |
| Two_Way_Finesse | 30 | 26 | 0 | 4 | 13% |
| Finesse_Simple | 30 | 26 | 0 | 4 | 13% |
| Endplay_3rd_Round_Strip | 30 | 27 | 0 | 3 | 10% |
| To_Finesse_Or_Not | 30 | 28 | 0 | 2 | 7% |
| Side_Suit_Ruff_Before_Trump | 30 | 28 | 0 | 2 | 7% |
| Play_Top_Tricks_NT | 30 | 28 | 0 | 2 | 7% |
| Play_Top_Tricks_Suit | 29 | 28 | 0 | 1 | 3% |
| Choice_Of_Finesses | 30 | 30 | 0 | 0 | 0% |
| Rabbis_Rule | 30 | 30 | 0 | 0 | 0% |
| Play_Top_Tricks | 30 | 30 | 0 | 0 | 0% |
| **Total** | **359** | | | | **9% (32 boards)** |

There is also a subtler defect a DD gate **cannot** see — a board that is a perfectly sound contract but doesn't actually feature the lesson's technique (e.g., a "Choice of Finesses" board where there's no real finesse choice). Choice_Of_Finesses scores 0% on soundness yet is known to feature the clean avoidance on only ~6 of its 30 boards. That class needs a different tool (see Phase 2).

### Concrete example — Suit_Promotion board 4

```
South (student) declares 3NT:
  N  ♠63    ♥AJT96  ♦8      ♣AJT97
  S  ♠AKQ75 ♥K7     ♦T73    ♣KQ5
DDS result: 3NT makes only 8 tricks from either North or South.
```

Best defense holds this to 8 — yet it is taught as a make. A clean by-force replacement already sitting in the pool:

```
  N  ♠876 ♥AQJT9 ♦T93 ♣Q7
  S  ♠AKQ  ♥8643 ♦J76 ♣AK6
DDS result: 3NT makes 9 on best defense, and still makes after swapping the
East/West hands (honors flipped) — i.e. it does not depend on a lucky finesse.
```

## How the curation step would work

Insert one operation, `curate`, between `filter` and coaching authoring:

```
btn → dlr → pbs → pbn → rotate → bba → filter (→ bba-filtered) → [CURATE] → author coaching → package
```

It scores every board in `bba-filtered/<scenario>.pbn` and emits the 30-board set the authoring stage consumes. Two layers:

### Phase 1 — Double-dummy quality gate (cheap, ready)

For each candidate board, run DDS and keep only boards where the target game is **makeable on best defense from the student's seat**. Auto-**rotate** wrong-sided boards (same deal, re-seated so the strong hand is South — salvages them instead of discarding). Optionally drop runaway "no decision" boards.

- **Validated** on the trio. It cleanly identifies all 8 Suit_Promotion and 6 Hold_Up defects above.
- For **by-force** lessons (Suit_Promotion, Play_Top_Tricks, Rabbis) it also *positively* selects good boards via an "honor-swap" robustness test — makeable even when the defenders' honors are flipped, so the contract is made by force, not by a lucky finesse. This validated at 16/18 of the sound Suit_Promotion boards.
- The replacement pool is abundant: e.g. Suit_Promotion has **249** by-force candidates in the pool; Hold_Up has **417** South-makeable boards. Scarcity is not the constraint.

### Phase 2 — Single-dummy simulation (expensive, avoidance lessons only)

The *avoidance/safety* lessons — Hold_Up, Choice_Of_Finesses, Two_Way_Finesse, To_Finesse_Or_Not — cannot be positively selected by a double-dummy solver, and the prototype proved it:

> A double-dummy solver sees all four hands and always plays the winning line. On 29 of 30 Choice_Of_Finesses boards it makes the contract with **1–4 overtricks** — the "pick the safe finesse" decision simply doesn't exist when you can see the cards. I also tried a committal test (force declarer to make the *wrong* play, then re-solve): it still fails, because double-dummy declarer recovers perfectly afterward, exactly as it skips the hold-up. Only 6 of 24 genuine hold-up boards register as "hold-up required" under any DD-based test.

The hold-up and the safe finesse are **single-dummy** safety plays — they only matter when declarer *can't* see the defenders' cards. Selecting boards where the technique is genuinely required means **Monte-Carlo single-dummy**: randomize the hidden hands consistent with the deal, play a *fixed* line, and measure the make-rate of the wrong line versus the technique line. `endplay`/DDS is double-dummy only, so this is a real engineering build, not a config change.

## Costs

| | Phase 1 (DD gate) | Phase 2 (single-dummy MC) |
|---|---|---|
| Compute | Trivial — DDS is ~ms/board | Heavier — many playouts/board |
| Engineering | Small — wrap DDS, add a `curate` op | Substantial — build a single-dummy playout/MC engine |
| Scope | All scenarios | Avoidance lessons only |
| Status | Prototyped & validated | Designed, not built |

**The dominant cost is shared and easy to overlook:** changing *which* 30 boards a scenario uses throws away the hand-authored coaching prose for the boards swapped out, which must be re-authored. So curation pays off most (a) before authoring a *new* scenario, and (b) on the ~32 already-defective boards we'd want to re-author anyway. Like the existing "regenerate `pbn+` after a card change" rule, curation must re-run when upstream deals change.

## Benefits

- Removes the 32 defective boards (9% of play content) that present unmakeable or wrong-sided contracts — and prevents new ones via a CI-style "0 defective boards" check.
- **Deterministic, auditable, reproducible** selection, versus today's ad-hoc first-30.
- For by-force lessons, *positively* upgrades board quality (clean made-by-force examples), not just defect removal.
- Rotation salvage recovers wrong-sided boards cheaply (re-seat, no new deal).
- Scales to every current and future scenario from one gate.

## Recommendation

Phased:

1. **Build Phase 1 now.** Cheap, broad, automatable, and it fixes real, measured defects across all scenarios. Start by re-curating the worst offenders (Suit_Promotion 27%, Hold_Up 20%).
2. **Scope Phase 2 separately**, limited to the four avoidance scenarios, only if the single-dummy build is judged worth it. Choice_Of_Finesses is the pure case: 0 soundness defects, so *only* single-dummy simulation can improve it.

### A question for you, Rick

`curate` sits directly downstream of `bba-cli`'s filter output. Two things would make it cleaner: (a) could `bba-cli` optionally emit the DDS table (or par result) per board, so the gate doesn't recompute it; and (b) is there appetite to fold a basic soundness gate into the filter itself? Happy to share the prototype (`endplay`-based, ~150 lines).

---

*Methodology: double-dummy results via the DDS solver (Bo Haglund) through the Python `endplay` wrapper. "Sound" = target game makeable on best defense from the student's declaring seat. "By-force" = makeable on best defense both as dealt and after swapping the East/West hands. Numbers above are from the current `coaching/*.pbn` and `bba-filtered/*.pbn` as of 2026-06-02.*
