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

v2 (2026-07-13) — the 07-04 dump-reads killed 11 of 14 candidates; their
mirage catalog is now encoded as per-hit acid flags (`acid` object) and a
`tight` verdict, so the next hunt starts where the last dump-read ended:

  spare      — False if the declarer side discards a master anywhere in the
               line (the b45/b5 "spare winners at the death" class), with
               the jettison/unblock exempted (other declarer hand covers).
  guard_E/W  — ROUND-AWARE length guard (the common suit's guard is joint,
               so the simple-squeeze top-beater model is wrong here — b153's
               West guards the deuce's third round with 6-5-3): defender's
               original length >= the fruit's round number AND his top card
               beats the fruit card. Kills b220's Qx crash class without
               killing spot-card length guards.
  live_E/W   — the same, at the moment of his first critical pitch: cards
               remaining >= rounds still to come before the fruit, top still
               beating the fruit card (kills dead-wood pitches — the guard
               already extracted by force or geometry: the b237/b126 class).
  busy_E/W   — at his first critical pitch the defender alone guards a live
               declarer card in a side suit (a real menace aimed at him).
  three_suit — E's and W's busy suits differ: the textbook three-suit
               geometry (two side menaces + the common suit).
  choice_E/W — the pitch lands on a declarer-won trick while the defender
               holds >= 2 non-led suits: a decision, not a forced parting
               (finesse-dressed endings and end-position collisions fail).

tight = spare and all six per-defender flags and three_suit.

Usage: double_squeeze_detect.py bba/Pool_A.pbn [...] > scan.json
"""
import sys, json, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harvest_common import (SEATS, RANKS, parse, tricks, sl, rk,
                            winner, dd_line, book_lead, compact_auction,
                            line_tricks, busy_suits)


def analyze(chrono, hands, trumpL):
    """One pass over the line -> (promoted-winner events with per-defender
    pitch attribution and busy-suit snapshots, master-discard log,
    before-trick snapshots for the v2 pitch-moment acids)."""
    pitches = {s: {su: [] for su in "SHDC"} for s in ("E", "W")}
    remaining = {s: {su: set(hands[s][su]) for su in "SHDC"} for s in SEATS}
    events, master_discards, snaps = [], [], []
    for t in range(13):
        snaps.append({s: {su: set(remaining[s][su]) for su in "SHDC"}
                      for s in SEATS})
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
            pitch_trick = {d: min((pt for pt, pr in pitches[d][suit]
                                   if pr in orig[d]), default=None)
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
                               "pitch_trick_E": pitch_trick["E"],
                               "pitch_trick_W": pitch_trick["W"],
                               "busy": busy})
        # declarer-side master discard (spare-winner tell), jettison exempt
        for s, c in trick[1:]:
            if s in ("N", "S") and sl(c) != led and (trumpL == "N" or sl(c) != trumpL):
                su = sl(c)
                ci = RANKS.index(rk(c))
                def_higher = any(RANKS.index(r) < ci
                                 for d in ("E", "W") for r in remaining[d][su])
                if not def_higher:
                    other = "N" if s == "S" else "S"
                    covered = any(
                        not any(RANKS.index(r) < RANKS.index(oc)
                                for d in ("E", "W") for r in remaining[d][su])
                        for oc in remaining[other][su])
                    if not covered:
                        master_discards.append({"trick": t+1, "card": su + rk(c)})
        for s, c in trick[1:]:
            if s in ("E", "W") and sl(c) != led and (trumpL == "N" or sl(c) != trumpL):
                pitches[s][sl(c)].append((t+1, rk(c)))
        for s, c in trick:
            remaining[s][sl(c)].discard(rk(c))
    return events, master_discards, snaps


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
        events, master_discards, snaps = analyze(chrono, hands, strain)
        hits = []
        for ev in events:
            if ev["pitched_E"] and ev["pitched_W"]:
                suit = ev["suit"]
                fi = RANKS.index(ev["card"])
                # round number of each trick in the fruit suit
                lead_tricks = [t+1 for t in range(13)
                               if sl(chrono[t*4][1]) == suit]
                fruit_round = lead_tricks.index(ev["trick"]) + 1
                acid = {"spare": not master_discards}
                if master_discards:
                    acid["spare_cards"] = [m["card"] for m in master_discards]
                for d in ("E", "W"):
                    # round-aware length guard (joint-guard model)
                    L = len(hands[d][suit])
                    top = min(hands[d][suit], key=RANKS.index)
                    acid[f"guard_{d}"] = (L >= fruit_round
                                          and RANKS.index(top) < fi)
                    p = ev[f"pitch_trick_{d}"]
                    snap = snaps[p - 1]
                    # live guard at release: rounds still to come vs cards left
                    rounds_before = sum(1 for lt in lead_tricks if lt < p)
                    now = snap[d][suit]
                    if now:
                        top_now = min(now, key=RANKS.index)
                        acid[f"live_{d}"] = (
                            len(now) >= fruit_round - rounds_before
                            and RANKS.index(top_now) < fi)
                    else:
                        acid[f"live_{d}"] = False
                    # busy in a side suit + the pitch was a choice
                    bz = busy_suits(snap, d, suit, strain)
                    acid[f"busy_{d}"] = sorted(bz)
                    ptrick = chrono[(p-1)*4:(p-1)*4+4]
                    pw, _ = winner(ptrick, strain)
                    led = sl(ptrick[0][1])
                    held = [su for su in "SHDC" if su != led and snap[d][su]]
                    acid[f"choice_{d}"] = pw in ("N", "S") and len(held) >= 2
                acid["three_suit"] = any(
                    e != w for e in acid["busy_E"] for w in acid["busy_W"])
                tight = (acid["spare"]
                         and acid["guard_E"] and acid["guard_W"]
                         and acid["live_E"] and acid["live_W"]
                         and bool(acid["busy_E"]) and bool(acid["busy_W"])
                         and acid["choice_E"] and acid["choice_W"]
                         and acid["three_suit"])
                hits.append({"class": "both_pitch", "tight": tight,
                             "acid": acid, **ev})
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
            nt = sum(1 for c in results[name]
                     for h in c["hits"] if h.get("tight"))
            sys.stderr.write(f"{name}: {len(results[name])} candidates,"
                             f" {nt} tight\n")
        except Exception as e:
            sys.stderr.write(f"{name}: ERROR {e}\n")
    print(json.dumps(results, indent=1))
