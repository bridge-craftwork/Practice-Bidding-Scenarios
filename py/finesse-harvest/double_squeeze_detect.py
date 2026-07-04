#!/usr/bin/env python3
"""Double-squeeze detector — the WIDENED acid (see squeeze-endplay-plan.md log 07-04).

The first hunt (squeeze_family_detect's "double" class) demanded TWO promoted
winners with distinct victims — but a textbook double squeeze scores exactly
ONE extra trick: the common (third) suit's menace, which BOTH defenders had to
abandon because each was busy guarding his own side suit. The side menaces
threaten; they don't score. So the corpus looked empty when the acid was
simply wrong-shaped.

Widened signature, one DD line per qualifying board (book lead, line == need):

  both_pitch — a late led-suit trick won by a declarer-side card although the
      defense ORIGINALLY held beaters, every beater is gone, and the pitched
      beaters came from BOTH defenders (each pitched at least one on other
      suits' leads). This covers the length menace too: a low winning card
      counts every outstanding card of the suit as a beater, so "both
      defenders threw the suit away and the deuce ran" is caught by rank.

  two_menace — the old two-promoted-winners / two-victims shape, kept for
      completeness (a progressive/double where a side menace also cashes).

For each hit we record what each defender still guarded elsewhere at the
moment of the promoted trick (their busy suits) to speed the dump-read.

Usage: double_squeeze_detect.py bba/Pool_A.pbn [...] > scan.json
"""
import sys, json, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harvest_common import (SEATS, RANKS, parse, tricks, sl, rk,
                            winner, dd_line, book_lead, compact_auction, line_tricks)


def analyze(chrono, hands, trumpL):
    """One pass over the line -> promoted-winner events with per-defender
    pitch attribution and busy-suit snapshots."""
    pitches = {s: {su: [] for su in "SHDC"} for s in ("E", "W")}
    remaining = {s: {su: set(hands[s][su]) for su in "SHDC"} for s in SEATS}
    events = []
    for t in range(13):
        trick = chrono[t*4:t*4+4]
        led = sl(trick[0][1])
        w, wc = winner(trick, trumpL)
        suit = sl(wc)
        if w in ("N", "S") and suit != trumpL and led == suit and t >= 5:
            wi = RANKS.index(rk(wc))
            orig = {d: [r for r in hands[d][suit] if RANKS.index(r) < wi]
                    for d in ("E", "W")}
            live = [r for d in ("E", "W") for r in remaining[d][suit]
                    if RANKS.index(r) < wi]
            pitched = {d: [r for r in orig[d]
                           if any(pr == r for _, pr in pitches[d][suit])]
                       for d in ("E", "W")}
            if (orig["E"] or orig["W"]) and not live and (pitched["E"] or pitched["W"]):
                # busy-suit snapshot: what each defender still holds elsewhere
                busy = {}
                for d in ("E", "W"):
                    keep = {}
                    for su in "SHDC":
                        if su in (suit, trumpL):
                            continue
                        if remaining[d][su]:
                            keep[su] = "".join(r for r in RANKS
                                               if r in remaining[d][su])
                    busy[d] = keep
                events.append({"trick": t+1, "suit": suit, "card": rk(wc),
                               "pitched_E": pitched["E"], "pitched_W": pitched["W"],
                               "orig_E": orig["E"], "orig_W": orig["W"],
                               "busy": busy})
        for s, c in trick[1:]:
            if s in ("E", "W") and sl(c) != led and (trumpL == "N" or sl(c) != trumpL):
                pitches[s][sl(c)].append((t+1, rk(c)))
        for s, c in trick:
            remaining[s][sl(c)].discard(rk(c))
    return events


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
        events = analyze(chrono, hands, strain)
        hits = []
        for ev in events:
            if ev["pitched_E"] and ev["pitched_W"]:
                hits.append({"class": "both_pitch", **ev})
        victims = {("E" if ev["pitched_E"] else "W") for ev in events
                   if bool(ev["pitched_E"]) != bool(ev["pitched_W"])}
        if len(victims) == 2:
            hits.append({"class": "two_menace",
                         "menaces": [{k: ev[k] for k in
                                      ("trick", "suit", "card",
                                       "pitched_E", "pitched_W")}
                                     for ev in events][:3]})
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
