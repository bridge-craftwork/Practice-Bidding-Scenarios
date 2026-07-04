#!/usr/bin/env python3
"""Squeeze-family detector — the shelf's next three rungs, one pass.

Thin over harvest_common (book leads throughout). South declares a game/slam
(3N or 4+) making EXACTLY; one DD line per qualifying board, three acids:

  rectify — the Simple_Squeeze story with the RECTIFICATION visible: within
      the first five tricks declarer-side DUCKS (plays low holding a higher
      card in the led suit while the defense wins the trick), and later a
      promoted winner scores (the squeeze acid). The duck is the lesson.

  showup — the show-up squeeze: a defender's GUARDED honor (K or Q behind a
      declarer tenace) is never finessed — his guards evaporate on earlier
      discards and the honor falls SINGLETON under a top card late in the
      hand. The count made the "finesse" a certainty, so no finesse was taken.

  double — two promoted winners in DIFFERENT suits whose pitched beaters came
      from DIFFERENT defenders: both opponents squeezed on the same run.

Usage: squeeze_family_detect.py bba/Pool_A.pbn [...] > scan.json
"""
import sys, json, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harvest_common import (SEATS, RANKS, parse, tricks, sl, rk,
                            winner, dd_line, book_lead, compact_auction, line_tricks)


def analyze(chrono, hands, trumpL):
    """One pass over the line collecting ducks, pitches, promoted winners,
    and show-up drops."""
    pitches = {s: {su: [] for su in "SHDC"} for s in ("E", "W")}
    remaining = {s: {su: set(hands[s][su]) for su in "SHDC"} for s in SEATS}
    ducks, promoted, showups = [], [], []
    for t in range(13):
        trick = chrono[t*4:t*4+4]
        led = sl(trick[0][1])
        w, wc = winner(trick, trumpL)
        suit = sl(wc)
        # duck: defense wins while a declarer hand followed low holding a beater
        if w in ("E", "W") and t <= 4:
            wi = RANKS.index(rk(wc))
            for s, c in trick:
                if s in ("N", "S") and sl(c) == suit and RANKS.index(rk(c)) > wi:
                    if any(RANKS.index(r) < wi for r in remaining[s][suit] - {rk(c)}):
                        ducks.append({"trick": t+1, "suit": suit, "by": s})
                        break
        # promoted winner (squeeze fruit)
        if w in ("N", "S") and suit != trumpL and led == suit and t >= 6:
            wi = RANKS.index(rk(wc))
            orig = [(d, r) for d in ("E", "W") for r in hands[d][suit]
                    if RANKS.index(r) < wi]
            live = [(d, r) for d in ("E", "W") for r in remaining[d][suit]
                    if RANKS.index(r) < wi]
            pitched = [(d, r) for d, r in orig
                       if any(pr == r for _, pr in pitches[d][suit])]
            if orig and not live and pitched:
                promoted.append({"trick": t+1, "suit": suit, "card": rk(wc),
                                 "victim": pitched[-1][0],
                                 "pitched": [r for _, r in pitched]})
        # show-up drop: guarded K/Q falls simple under a winning top card
        if w in ("N", "S") and suit != trumpL and t >= 6:
            for s, c in trick:
                if s in ("E", "W") and sl(c) == suit and rk(c) in ("K", "Q"):
                    guards0 = len(hands[s][suit]) - 1
                    pitched_here = len(pitches[s][suit])
                    if (guards0 >= 2 and pitched_here >= 1
                            and rk(wc) in ("A", "K")
                            and RANKS.index(rk(wc)) < RANKS.index(rk(c))):
                        showups.append({"trick": t+1, "suit": suit,
                                        "honor": rk(c), "holder": s,
                                        "orig_len": guards0 + 1})
        for s, c in trick[1:]:
            if s in ("E", "W") and sl(c) != led and (trumpL == "N" or sl(c) != trumpL):
                pitches[s][sl(c)].append((t+1, rk(c)))
        for s, c in trick:
            remaining[s][sl(c)].discard(rk(c))
    return ducks, promoted, showups


def scan(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    out = []
    for b in re.split(r'(?=^\[Board )', txt, flags=re.M):
        mb = re.search(r'\[Board "(\d+)"\]', b)
        mc = re.search(r'\[Contract "(\d)([CDHSN])', b)
        mdeal = re.search(r'\[Deal "([^"]+)"\]', b)
        if not (mb and mc and mdeal and re.search(r'\[Declarer "S"\]', b)):
            continue
        level, strain = int(mc.group(1)), mc.group(2)
        if not (level >= 4 or (level == 3 and strain == "N")):
            continue
        hands = parse(mdeal.group(1))
        # pre-filter: a runnable long suit exists (as squeeze_detect)
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
            if tricks(mdeal.group(1), "S", strain) != need:
                continue
        except Exception:
            continue
        lead = book_lead(hands, "W", strain)
        try:
            chrono = dd_line(mdeal.group(1), f"{level}{strain}", "S", lead)
        except Exception:
            continue
        if line_tricks(chrono, strain, "S") != need:
            continue
        ducks, promoted, showups = analyze(chrono, hands, strain)
        hits = []
        if ducks and promoted:
            hits.append({"class": "rectify", "duck": ducks[0],
                         "promoted": promoted[0]})
        if showups:
            hits.append({"class": "showup", **showups[0]})
        victims = {p["victim"] for p in promoted}
        if len(victims) == 2:
            hits.append({"class": "double",
                         "menaces": [{k: p[k] for k in ("trick","suit","card","victim")}
                                     for p in promoted[:2]]})
        if not hits:
            continue
        out.append({"board": int(mb.group(1)), "contract": f"{level}{strain}",
                    "deal": mdeal.group(1), "auction": compact_auction(b),
                    "lead": lead, "hits": hits})
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
