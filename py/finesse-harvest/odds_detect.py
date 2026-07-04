#!/usr/bin/env python3
"""Eight-ever / nine-never detector (Deep_Finesse lesson's poor-candidate rung).

Two classes, one scan, South declares a game/slam (3N or 4+) making EXACTLY:

  nine_never — NS hold 9+ cards in a suit with A, K and J but no Q; the Q sits
      with the defender BEHIND the jack (so the tempting hook would LOSE); the
      DD line cashes the top honors and the Q FALLS within two rounds and
      never wins a trick. The finesse was available, poor, and losing — the
      drop was right.

  eight_ever — same missing-Q shape but an 8-card fit, Q in FRONT of the jack,
      and the DD line genuinely HOOKS the jack (J wins a led-toward trick
      while the Q is live; Q never scores). With eight, finesse.

Usage: odds_detect.py bba/Pool_A.pbn [...] > scan.json
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
    return bs, bc

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

def suit_story(chrono, trumpL, suit):
    """Rounds of `suit`: (round#, winner_seat, winning_rank, q_played_this_round)."""
    rounds = []
    for t in range(13):
        trick = chrono[t*4:t*4+4]
        if sl(trick[0][1]) != suit:
            continue
        w, wc = winner(trick, trumpL)
        qhere = any(sl(c) == suit and rk(c) == "Q" for _, c in trick)
        rounds.append((t+1, w, rk(wc), qhere))
    return rounds

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
        for suit in "SHDC":
            n, s_ = hands["N"][suit], hands["S"][suit]
            comb = n + s_
            if "Q" in comb or "A" not in comb or "K" not in comb or "J" not in comb:
                continue
            qholder = next((x for x in ("E","W") if "Q" in hands[x][suit]), None)
            if qholder is None:
                continue
            jhand = "N" if "J" in n else "S"
            behind_j = "W" if jhand == "S" else "E"   # defender playing after the J-hand
            fit = len(comb)
            if fit >= 9 and qholder == behind_j:
                cands.append((suit, "nine_never", qholder, fit,
                              len(hands[qholder][suit])))
            elif fit == 8 and qholder != behind_j:
                cands.append((suit, "eight_ever", qholder, fit,
                              len(hands[qholder][suit])))
        if not cands:
            continue
        need = 6 + level
        try:
            if tricks(mdeal.group(1), "S", strain) != need:
                continue
        except Exception:
            continue
        for suit, cls, qholder, fit, qlen in cands:
            lead = passive_lead(hands, "W", suit, strain)
            try:
                chrono = dd_line(mdeal.group(1), f"{level}{strain}", "S", lead)
            except Exception:
                continue
            rounds = suit_story(chrono, strain, suit)
            decl_side = {"N","S"}
            q_won = any(w in ("E","W") and r == "Q" for _, w, r, _ in rounds)
            if q_won:
                continue                        # the Q scored — story broken
            if cls == "nine_never":
                # Q must fall under a top honor within the first two rounds
                early = rounds[:2]
                if not any(q and w in decl_side and r in ("A","K")
                           for _, w, r, q in early):
                    continue
            else:
                # eight_ever: the J must WIN a round while the Q is still out
                jwin = next((i for i, (_, w, r, _) in enumerate(rounds)
                             if w in decl_side and r == "J"), None)
                qseen = next((i for i, (_, _, _, q) in enumerate(rounds) if q),
                             len(rounds))
                if jwin is None or jwin > qseen:
                    continue
            out.append({"board": int(mb.group(1)), "contract": f"{level}{strain}",
                        "deal": mdeal.group(1), "auction": compact_auction(b),
                        "suit": suit, "class": cls, "fit": fit,
                        "qholder": qholder, "qlen": qlen, "lead": lead,
                        "rounds": rounds})
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
