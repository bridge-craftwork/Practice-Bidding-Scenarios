#!/usr/bin/env python3
"""Repeated-finesse detector (lesson 3b).

Structure hunted: ONE missing honor finessed against MORE THAN ONCE — the
lesson lives on entries to the leading side. In a South-declared game/slam
(3N or 4+) that makes EXACTLY:
  vsK — tenace hand holds Q+J (no K anywhere in NS, A somewhere in NS):
        finesse the J, cross back, finesse the Q.
  vsQ — tenace hand holds J+T (no Q in NS, A and K somewhere in NS):
        finesse the T, cross back, finesse the J.
The top honors may sit in either NS hand (A2 opposite KJT9 repeats fine).
Tenace's partner needs 2+ cards (two leads toward), and the missing honor must
sit in FRONT of the tenace (onside) — offside there is nothing to repeat.

Gate = DD-LINE ACID under a passive lead: the suit is led from the partner
side toward the tenace at least TWICE, the tenace wins each such trick with a
card below the missing honor, and the missing honor NEVER wins a trick.
Two-plus leads-toward in the DD line also PROVES the entries exist.
See finesse-family-plan.md §9.

Usage: repeated_detect.py bba/Pool_A.pbn [...] > scan.json
"""
import sys, json, re
from endplay.dds import calc_dd_table, solve_board
from endplay.types import Deal, Denom, Player, Card

SEATS = ["N","E","S","W"]
RANKS = "AKQJT98765432"
DENOM = {"C": Denom.clubs, "D": Denom.diamonds, "H": Denom.hearts,
         "S": Denom.spades, "N": Denom.nt}
PLAYER = {"N": Player.north, "E": Player.east, "S": Player.south, "W": Player.west}
SEAT_OF = {Player.north:"N", Player.east:"E", Player.south:"S", Player.west:"W"}
PL = {"N":"north","E":"east","S":"south","W":"west"}
LEADER_OF = {"N":"E","E":"S","S":"W","W":"N"}

def parse(ds):
    first, rest = ds.split(":"); hands = rest.split()
    order = [first] + [SEATS[(SEATS.index(first)+i)%4] for i in range(1,4)]
    return {s: dict(zip("SHDC", h.split("."))) for s, h in zip(order, hands)}

def tricks(ds, declarer, strain):
    return calc_dd_table(Deal(ds))[DENOM[strain], PLAYER[declarer]]

def sl(c): return c.suit.name[0].upper()
def rk(c): return c.rank.name[1:]

def winner(trick, trumpL):
    ts = None if trumpL == "N" else trumpL
    bs, bc = trick[0]
    for s, c in trick[1:]:
        if ts and sl(c) == ts and sl(bc) != ts: bs, bc = s, c
        elif sl(c) == sl(bc) and c.rank.value > bc.rank.value: bs, bc = s, c
    return bs

def dd_line(ds, contract, declarer, lead):
    d = Deal(ds); d.trump = DENOM[contract[1]]
    d.first = getattr(Player, PL[LEADER_OF[declarer]])
    chrono = []
    for i in range(52):
        s = SEAT_OF[d.curplayer]
        c = Card(lead) if i == 0 else max(solve_board(d), key=lambda kv: kv[1])[0]
        chrono.append((s, c)); d.play(c)
    return chrono

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from harvest_common import book_lead, line_tricks

def passive_lead(hands, leader, *rest):
    """Book lead (harvest_common) — trump letter is the LAST argument; any
    avoid-suit argument from older call sites is intentionally ignored: the
    acid must run on the REAL lead, even when it hits the taught suit."""
    return book_lead(hands, leader, rest[-1])

def compact_auction(b):
    am = re.search(r'\[Auction "[NESW]"\]\s*\n(.*?)(?=\n\[|\n\{|\Z)', b, re.S)
    if not am: return ""
    return " ".join(tok for ln in am.group(1).strip().splitlines() for tok in ln.split())

def acid(chrono, trumpL, fin_suit, tenace_hand, partner, missing, declarer):
    """>=2 leads toward the tenace, tenace wins EACH with a sub-honor card,
    and the missing honor never wins a trick."""
    decl_side = {declarer, {"N":"S","S":"N"}[declarer]}
    hv = RANKS.index(missing)
    finessed = 0
    for t in range(13):
        trick = chrono[t*4:t*4+4]
        led_seat, led_card = trick[0]
        w = winner(trick, trumpL)
        wc = next(c for s, c in trick if s == w)
        # missing honor ever wins -> not a clean repeated pickup
        if sl(wc) == fin_suit and rk(wc) == missing:
            return None
        if led_seat != partner or sl(led_card) != fin_suit:
            continue
        if w == tenace_hand and sl(wc) == fin_suit and RANKS.index(rk(wc)) > hv:
            finessed += 1
    if finessed >= 2:
        return {"finessed": finessed}
    return None

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
        cands = []
        for tenace_hand, partner in (("N","S"), ("S","N")):
            # onside = the defender who plays BEFORE the tenace hand on a lead
            # from partner: lead S -> W -> N (tenace N: onside is West);
            # lead N -> E -> S (tenace S: onside is East).
            front = "W" if tenace_hand == "N" else "E"
            for suit in "SHDC":
                if suit == strain: continue
                h, p = hands[tenace_hand][suit], hands[partner][suit]
                if len(h) < 2 or len(p) < 2: continue
                s = set(h); comb = s | set(p)
                if {"Q","J"} <= s and "K" not in comb and "A" in comb:
                    missing = "K"
                elif {"J","T"} <= s and "Q" not in comb and {"A","K"} <= comb:
                    missing = "Q"
                else:
                    continue
                holder = next((x for x in SEATS if missing in hands[x][suit]), None)
                if holder != front: continue     # must be onside to repeat
                cands.append((suit, tenace_hand, partner, missing, holder, h, p))
        if not cands:
            continue
        need = 6 + level
        try:
            if tricks(mdeal.group(1), "S", strain) != need:
                continue
        except Exception:
            continue
        for suit, tenace_hand, partner, missing, holder, h, p in cands:
            lead = passive_lead(hands, "W", suit, strain)
            try:
                chrono = dd_line(mdeal.group(1), f"{level}{strain}", "S", lead)
            except Exception:
                continue
        if line_tricks(chrono, strain, "S") != need:
            continue
            a = acid(chrono, strain, suit, tenace_hand, partner, missing, "S")
            if a is None:
                continue
            out.append({"board": int(mb.group(1)), "contract": f"{level}{strain}",
                        "deal": mdeal.group(1), "auction": compact_auction(b),
                        "suit": suit, "missing": missing, "tenace_hand": tenace_hand,
                        "tenace": h, "partner_holding": p, "holder": holder,
                        "lead": lead, "acid": a})
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
