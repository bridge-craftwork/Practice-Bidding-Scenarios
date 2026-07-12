#!/usr/bin/env python3
"""Show-up-squeeze detector (Squeezes & Endplays shelf) — the TIGHT acid.

Supersedes the `showup` class of squeeze_family_detect.py, which fires whenever
a guarded honor falls under a top card and so also matches plain length-drops,
ordinary finesses, and endplays (a ~0/10 hand-verified hit rate on its raw
output). This detector keys on the ONE thing that makes a show-up a squeeze
rather than luck: the missing honor is picked up EARLIER than length or a
finesse could manage, because the defender was forced to DISCARD a guard.

Structure hunted: a suit where NS holds the ACE and is missing a guarded honor
H in {K, Q} held by a SINGLE defender (the holder, guard length g >= 3), in a
South-declared game/slam (3N or 4+) that makes EXACTLY.

The acid, over the book-lead DD line:
  1. line makes EXACTLY (line_tricks == need) — the technique is load-bearing.
  2. H is the SOLE top missing honor: NS holds every rank above H (A for a
     missing K; A and K for a missing Q). A defender sitting with both K and Q
     is a double-guard, not a show-up.
  3. The suit is brought home WHOLE: the defense wins ZERO tricks in it. The
     shipped boards' own notes say "without losing one" / "never wins a
     diamond" — that is the show-up's whole point.
  4. H falls to the ACE: the trick where H is played is won by NS's ACE (H
     rises and the ace swallows it). A finesse leaves H sitting behind or
     captures it under a low honor NS led toward — the ace-drop is the tell.
  5. H falls on suit-lead round r with r < g (and r >= 2). Length alone strips
     a g-card guard only on round g; falling on an EARLIER round means the
     holder shed (g - r) cards of the suit as DISCARDS on other suits' leads —
     the squeeze. r == g is a pure length-drop; excluded.
  6. H never wins a trick anywhere (trapped throughout).

`hooks_first` records how many lower rounds NS won with a card below H before
the show-up (0 = pure count; 1-2 = the "finesse twice, then the count" shape of
the shipped boards). See squeeze-endplay-plan.md §5 and finesse-family-plan.md §9.

Usage: showup_detect.py bba/Pool_A.pbn [...] > scan.json
"""
import sys, json, re, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harvest_common import (SEATS, RANKS, parse, tricks, sl, rk,
                            winner, dd_line, book_lead, compact_auction, line_tricks)

DEF = {"E", "W"}
PARTNER = {"N": "S", "S": "N", "E": "W", "W": "E"}


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
        need = 6 + level
        deal = md.group(1)
        # candidate suits: NS holds the ace, a single defender holds a guarded K or Q
        cands = []
        for suit in "SHDC":
            if suit == trumpL:
                continue
            ns = hands["N"][suit] + hands["S"][suit]
            if "A" not in ns:
                continue
            for H in ("K", "Q"):
                if H in ns:
                    continue
                # H must be the SOLE top missing honor: NS holds every rank above it
                hv = RANKS.index(H)
                if not all(RANKS[i] in ns for i in range(hv)):
                    continue
                holders = [d for d in DEF if H in hands[d][suit]]
                if len(holders) != 1:
                    continue
                holder = holders[0]
                g = len(hands[holder][suit])
                if g < 3:
                    continue
                cands.append((suit, H, holder, g))
        if not cands:
            continue
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
        for suit, H, holder, g in cands:
            hv = RANKS.index(H)
            rounds = 0            # suit-lead rounds elapsed
            fell = None          # round on which H fell to the ace
            honor_wins = False
            def_wins = 0         # tricks the defense won in the suit
            hooks_first = 0      # NS-won rounds with a card BELOW H before H fell
            pitched = 0          # holder discards of the suit on non-suit leads
            for t in range(13):
                trick = chrono[t*4:t*4+4]
                led = sl(trick[0][1])
                ws, wc = winner(trick, trumpL)
                hc = next((c for s, c in trick if s == holder), None)
                if led == suit:
                    rounds += 1
                    if ws in DEF:
                        def_wins += 1
                    if fell is None and ws in ("N", "S") and RANKS.index(rk(wc)) > hv:
                        hooks_first += 1
                    if hc is not None and sl(hc) == suit and rk(hc) == H:
                        if (ws, wc) == (holder, hc):
                            honor_wins = True
                        elif rk(wc) == "A" and ws in ("N", "S") and fell is None:
                            fell = rounds      # H rose and the ace swallowed it
                else:
                    if hc is not None and sl(hc) == suit:
                        pitched += 1
            if honor_wins or def_wins or fell is None:
                continue
            r = fell
            if r < 2 or r >= g:
                continue
            if pitched < 1:
                continue
            out.append({"board": int(mb.group(1)), "contract": f"{level}{trumpL}",
                        "deal": deal, "auction": compact_auction(b),
                        "suit": suit, "honor": H, "holder": holder, "guard": g,
                        "fell_round": r, "hooks_first": hooks_first,
                        "pitched": pitched, "lead": lead,
                        "ns_holding": "".join(sorted(hands["N"][suit] + hands["S"][suit],
                                                     key=RANKS.index)),
                        "holder_holding": hands[holder][suit]})
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
