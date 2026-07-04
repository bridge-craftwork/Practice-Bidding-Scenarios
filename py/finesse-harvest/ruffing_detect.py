#!/usr/bin/env python3
"""Ruffing-finesse detector (lesson 1b).

Structure hunted: a SIDE suit where one NS hand holds a broken sequence
missing its top honor and partner is short (0-1 cards), in a South-declared
suit game/slam that makes EXACTLY:
  vsK — hand has A+Q+J, no K: cash the A, run the Q; ruff the K or pitch.
  vsA — hand has K+Q+J, no A: run the K through the ace.
The missing honor must be with a DEFENDER (a partner stiff K opposite AQJ is
nothing to finesse — the pre-scan trap). `front` marks the can't-lose layout:
the honor sits with the defender who plays BETWEEN the sequence hand and the
short hand (seq N/short S -> East; seq S/short N -> West).

Swing tests can't find these (a true ruffing finesse barely moves the DD count
wherever the honor sits), so the gate is the DD-LINE ACID: under a passive
lead, the line must contain a trick where a sequence honor below the missing
one is LED from the sequence hand and the short hand either RUFFS the cover or
PITCHES (loser-on-loser). Emits JSON rows for eyeballing with verify_play.py
--show. See finesse-family-plan.md §9.

Usage: ruffing_detect.py bba/Pool_A.pbn [...] > scan.json
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
from harvest_common import book_lead

def passive_lead(hands, leader, *rest):
    """Book lead (harvest_common) — trump letter is the LAST argument; any
    avoid-suit argument from older call sites is intentionally ignored: the
    acid must run on the REAL lead, even when it hits the taught suit."""
    return book_lead(hands, leader, rest[-1])

def compact_auction(b):
    am = re.search(r'\[Auction "[NESW]"\]\s*\n(.*?)(?=\n\[|\n\{|\Z)', b, re.S)
    if not am: return ""
    return " ".join(tok for ln in am.group(1).strip().splitlines() for tok in ln.split())

def acid(chrono, trumpL, fin_suit, seq, short, missing, declarer):
    """Find the ruffing-finesse trick: seq hand leads a fin-suit honor below the
    missing one; short hand (void by then) ruffs or pitches."""
    decl_side = {declarer, {"N":"S","S":"N"}[declarer]}
    hv = RANKS.index(missing)
    leader = chrono[0][0]
    for t in range(13):
        trick = chrono[t*4:t*4+4]
        led_seat, led_card = trick[0]
        w = winner(trick, trumpL)
        li = RANKS.index(rk(led_card))
        # led card = a sequence honor just below the missing one (Q/J/T under a
        # missing K; K/Q/J under a missing A)
        if led_seat == seq and sl(led_card) == fin_suit and hv < li <= hv + 3:
            sc = next((c for s, c in trick if s == short), None)
            if sc is None or sl(sc) == fin_suit:
                continue                      # short hand still following
            covered = any(sl(c) == fin_suit and rk(c) == missing for s, c in trick)
            kind = "ruff" if sl(sc) == trumpL else "pitch"
            return {"trick": t+1, "kind": kind, "covered": covered,
                    "won_by_decl": w in decl_side}
    return None

def scan(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    out = []
    for b in re.split(r'(?=^\[Board )', txt, flags=re.M):
        mb = re.search(r'\[Board "(\d+)"\]', b)
        mc = re.search(r'\[Contract "(\d)([CDHS])', b)
        mdeal = re.search(r'\[Deal "([^"]+)"\]', b)
        if not (mb and mc and mdeal and re.search(r'\[Declarer "S"\]', b)):
            continue
        level, trumpL = int(mc.group(1)), mc.group(2)
        if level < 4:
            continue
        hands = parse(mdeal.group(1))
        cands = []
        for seq, short in (("N","S"), ("S","N")):
            for suit in "SHDC":
                if suit == trumpL: continue
                h, p = hands[seq][suit], hands[short][suit]
                if len(p) > 1 or len(h) < 3: continue
                s = set(h)
                if {"A","Q","J"} <= s and "K" not in s: flavor, missing = "vsK", "K"
                elif {"K","Q","J"} <= s and "A" not in s: flavor, missing = "vsA", "A"
                else: continue
                holder = next((x for x in SEATS if missing in hands[x][suit]), None)
                if holder not in ("E","W"): continue      # partner-stiff trap
                front = "E" if seq == "N" else "W"
                cands.append((suit, flavor, missing, seq, short, holder, holder == front, h, p))
        if not cands:
            continue
        need = 6 + level
        try:
            if tricks(mdeal.group(1), "S", trumpL) != need:
                continue
        except Exception:
            continue
        for suit, flavor, missing, seq, short, holder, front, h, p in cands:
            lead = passive_lead(hands, "W", suit, trumpL)
            try:
                chrono = dd_line(mdeal.group(1), f"{level}{trumpL}", "S", lead)
            except Exception:
                continue
            a = acid(chrono, trumpL, suit, seq, short, missing, "S")
            if a is None:
                continue
            out.append({"board": int(mb.group(1)), "contract": f"{level}{trumpL}",
                        "deal": mdeal.group(1), "auction": compact_auction(b),
                        "suit": suit, "flavor": flavor, "missing": missing,
                        "seq": seq, "short": short, "holder": holder, "front": front,
                        "seq_holding": h, "short_holding": p or "-",
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
