#!/usr/bin/env python3
"""Rectify / simple-squeeze detector (Squeezes & Endplays shelf) — the TIGHT acid.

Supersedes the `rectify` class of squeeze_family_detect.py, which paired ANY
early declarer duck with ANY late promoted winner and so also matched
establishment lines, forced-out guards, always-crashing honors, and spare-
winner garnish (the classes the 07-04 double-squeeze dump-reads catalogued).
This detector keys on the whole simple-squeeze story and demands each link:

Structure hunted: South declares a game/slam (3N or 4+) making EXACTLY; the
book-lead DD line contains a visible RECTIFICATION (an early duck that was a
choice), then a squeeze against ONE defender who guarded two suits, ending in
a promoted declarer winner the defense originally beat.

The acid, over the book-lead DD line:
  1. line makes EXACTLY (line_tricks == need) — the technique is load-bearing.
  2. RECTIFY (splits the output into two classes): within the first six
     tricks the defense wins a trick while a declarer-side hand ducks BY
     CHOICE — follows (or under-ruffs) below the winning card while holding
     a beater, or discards holding a trump that could ruff. A qualifying
     duck before the fruit → class "rectify" (Rectify_The_Count wants it);
     none → class "simple" (the count rectified by force — fine for
     Simple_Squeeze, whose story is the two-suit guard, not the duck).
  3. FRUIT: a late trick (7+) in a plain suit, led in that suit and won by a
     declarer-side card the defense ORIGINALLY beat; every original beater is
     gone and at least one was pitched as a DISCARD on another suit's lead.
  4. ONE VICTIM: every pitched beater came from the SAME defender — two
     victims is the double squeeze's shape, not this lesson's.
  5. GENUINE GUARD (kills the always-crashing Qx of the mirage catalog): the
     victim's original length in the fruit suit exceeds the number of
     declarer-side cards above his top beater — his guard would have SURVIVED
     the tops; only the squeeze extracts it. r-of-length-drops excluded.
  6. BUSY ELSEWHERE (the two-suit story): at the moment of his first critical
     pitch the victim still held, in a second plain suit, the ONLY defensive
     card(s) beating a live declarer card — a real second menace aimed at him
     alone. Guards "extracted by force" (nothing else to hold) fail here.
  7. CHOICE, NOT COLLISION: the critical pitch happens on a declarer-won
     trick (the run) while the victim still holds at least two suits besides
     the one led — he CHOSE which guard to abandon.
  8. LIVE GUARD AT RELEASE (kills the dead-wood class, found on shipped
     b233's dump: East's club spots were dead under dummy's A-T after the
     trick-five duck-finesse, so his late club pitch was housekeeping, not a
     squeeze concession): at the pitch moment the victim's fruit-suit
     holding must still outlast declarer's remaining tops.
  9. NO SPARE WINNER (kills the b45/b5 garnish class): the declarer side
     never discards a master — a card no defender can beat — anywhere in
     the line, EXCEPT the jettison/unblock (the other declarer hand still
     holds a live master in the suit — shipped b185 pitches the spade ACE
     at trick ten to unblock, and the club fruit is still load-bearing).

`fruit_rank` (the promoted card, lower = more spectacular), `duck_trick`, and
`fruit_trick` are recorded for authoring: Rectify_The_Count wants the duck
early and visible (the shipped arc is tricks one, two, five); Simple_Squeeze
wants the two-suit guard story legible. See squeeze-endplay-plan.md §5 and
finesse-family-plan.md §9.

Usage: rectify_detect.py bba/Pool_A.pbn [...] > scan.json
"""
import sys, json, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harvest_common import (SEATS, RANKS, parse, tricks, sl, rk,
                            winner, dd_line, book_lead, compact_auction,
                            line_tricks, busy_suits)

DEF = {"E", "W"}
DECL = {"N", "S"}


def analyze(chrono, hands, trumpL):
    """One pass -> (ducks, fruits, pitch log, master-discard log, snapshots).

    snapshots[t] = per-seat remaining holdings BEFORE trick t+1 is played,
    so pitch-moment busy/choice checks read the position the defender saw."""
    pitches = {s: {su: [] for su in "SHDC"} for s in DEF}
    remaining = {s: {su: set(hands[s][su]) for su in "SHDC"} for s in SEATS}
    ducks, fruits, master_discards, snaps = [], [], [], []
    for t in range(13):
        snaps.append({s: {su: set(remaining[s][su]) for su in "SHDC"}
                      for s in SEATS})
        trick = chrono[t*4:t*4+4]
        led = sl(trick[0][1])
        w, wc = winner(trick, trumpL)
        suit = sl(wc)
        # rectification: defense wins while a declarer hand ducked by choice
        if w in DEF and t <= 5:
            wi = RANKS.index(rk(wc))
            for s, c in trick:
                if s not in DECL:
                    continue
                if (sl(c) == suit and RANKS.index(rk(c)) > wi
                        and any(RANKS.index(r) < wi
                                for r in remaining[s][suit] - {rk(c)})):
                    ducks.append({"trick": t+1, "suit": suit, "by": s,
                                  "held": "".join(r for r in RANKS
                                                  if r in remaining[s][suit])})
                    break
                if (trumpL != "N" and suit != trumpL and sl(c) != led
                        and sl(c) != trumpL and remaining[s][trumpL]):
                    ducks.append({"trick": t+1, "suit": suit, "by": s,
                                  "held": "ruff-declined"})
                    break
        # fruit: promoted declarer winner in a plain suit
        if w in DECL and suit != trumpL and led == suit and t >= 6:
            wi = RANKS.index(rk(wc))
            orig = {d: [r for r in hands[d][suit] if RANKS.index(r) < wi]
                    for d in DEF}
            live = [r for d in DEF for r in remaining[d][suit]
                    if RANKS.index(r) < wi]
            pitched = {d: [(pt, r) for pt, r in pitches[d][suit]
                           if r in orig[d]] for d in DEF}
            if (orig["E"] or orig["W"]) and not live \
                    and (pitched["E"] or pitched["W"]):
                fruits.append({"trick": t+1, "suit": suit, "card": rk(wc),
                               "orig": orig, "pitched": pitched})
        # declarer-side master discard (spare-winner tell). Exempt the
        # jettison/unblock: if the OTHER declarer hand still holds a live
        # master in the suit, the pitch keeps the suit runnable from there.
        for s, c in trick[1:]:
            if s in DECL and sl(c) != led and (trumpL == "N" or sl(c) != trumpL):
                su = sl(c)
                ci = RANKS.index(rk(c))
                def_higher = any(RANKS.index(r) < ci
                                 for d in DEF for r in remaining[d][su])
                if not def_higher:
                    other = "N" if s == "S" else "S"
                    covered = any(
                        not any(RANKS.index(r) < RANKS.index(oc)
                                for d in DEF for r in remaining[d][su])
                        for oc in remaining[other][su])
                    if not covered:
                        master_discards.append({"trick": t+1, "card": su + rk(c)})
        for s, c in trick[1:]:
            if s in DEF and sl(c) != led and (trumpL == "N" or sl(c) != trumpL):
                pitches[s][sl(c)].append((t+1, rk(c)))
        for s, c in trick:
            remaining[s][sl(c)].discard(rk(c))
    return ducks, fruits, master_discards, snaps




def scan(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    out = []
    for b in re.split(r'(?=^\[Board )', txt, flags=re.M):
        mb = re.search(r'\[Board "(\d+)"\]', b)
        mc = re.search(r'\[Contract "(\d)([CDHSN])', b)
        md = re.search(r'\[Deal "([^"]+)"\]', b)
        if not (mb and mc and md and re.search(r'\[Declarer "S"\]', b)):
            continue
        level, trumpL = int(mc.group(1)), mc.group(2)
        if not (level >= 4 or (level == 3 and trumpL == "N")):
            continue
        hands = parse(md.group(1))
        deal = md.group(1)
        # pre-filter: a runnable long suit exists (the squeeze needs a run)
        def has_run():
            for su in "SHDC":
                comb = hands["N"][su] + hands["S"][su]
                if len(comb) >= 7: return True
                if len(comb) >= 5 and "A" in comb and "K" in comb: return True
            return False
        if not has_run():
            continue
        need = 6 + level
        try:
            if tricks(deal, "S", trumpL) != need:
                continue
        except Exception:
            continue
        lead = book_lead(hands, "W", trumpL)
        try:
            chrono = dd_line(deal, f"{level}{trumpL}", "S", lead)
        except Exception:
            continue
        if line_tricks(chrono, trumpL, "S") != need:
            continue
        ducks, fruits, master_discards, snaps = analyze(chrono, hands, trumpL)
        if master_discards:
            continue
        hit = None
        for fr in fruits:
            # rung 4: one victim
            victims = [d for d in DEF if fr["pitched"][d]]
            if len(victims) != 1:
                continue
            victim = victims[0]
            # rung 5: genuine guard
            suit = fr["suit"]
            L = len(hands[victim][suit])
            top = min(fr["orig"][victim], key=RANKS.index)
            ti = RANKS.index(top)
            C = sum(1 for r in hands["N"][suit] + hands["S"][suit]
                    if RANKS.index(r) < ti)
            if L <= C:
                continue
            # rungs 6+7 at the first critical pitch
            p_trick = min(pt for pt, _ in fr["pitched"][victim])
            snap = snaps[p_trick - 1]
            ptrick = chrono[(p_trick-1)*4:(p_trick-1)*4+4]
            pw, _ = winner(ptrick, trumpL)
            if pw not in DECL:
                continue
            led = sl(ptrick[0][1])
            suits_held = [su for su in "SHDC"
                          if su != led and snap[victim][su]]
            if len(suits_held) < 2:
                continue
            # live guard at the moment of release (kills dead-wood pitches:
            # a "beater" already dead under declarer's remaining tops was
            # picked by finesse geometry or force earlier, not by squeeze)
            vict_now = snap[victim][suit]
            if not vict_now:
                continue
            top_now = min(vict_now, key=RANKS.index)
            decl_now = snap["N"][suit] | snap["S"][suit]
            tops_now = sum(1 for r in decl_now
                           if RANKS.index(r) < RANKS.index(top_now))
            if len(vict_now) <= tops_now:
                continue
            busy = busy_suits(snap, victim, suit, trumpL)
            if not busy:
                continue
            hit = {"fruit_trick": fr["trick"], "fruit_suit": suit,
                   "fruit_rank": fr["card"], "victim": victim,
                   "pitched": [r for _, r in fr["pitched"][victim]],
                   "pitch_trick": p_trick, "busy": busy,
                   "guard_len": L, "tops_over": C,
                   "victim_holding": hands[victim][suit],
                   "ns_holding": "".join(sorted(
                       hands["N"][suit] + hands["S"][suit], key=RANKS.index))}
            break
        if not hit:
            continue
        pre = [d for d in ducks if d["trick"] < hit["fruit_trick"]]
        out.append({"board": int(mb.group(1)), "contract": f"{level}{trumpL}",
                    "deal": deal, "auction": compact_auction(b), "lead": lead,
                    "class": "rectify" if pre else "simple",
                    "duck_trick": pre[0]["trick"] if pre else None,
                    "ducks": pre, **hit})
    return out


if __name__ == "__main__":
    results = {}
    for path in sys.argv[1:]:
        name = re.sub(r'.*/', '', path).replace(".pbn", "")
        try:
            results[name] = scan(path)
            sys.stderr.write(f"{name}: {len(results[name])} candidates\n")
        except Exception as e:
            sys.stderr.write(f"{name}: ERROR {e}\n")
    print(json.dumps(results, indent=1))
