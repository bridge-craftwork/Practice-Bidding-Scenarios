#!/usr/bin/env python3
"""Deep-finesse detector (Deep_Finesse lesson).

Hunts boards where the DD line wins a trick CHEAPLY ON PURPOSE with an
intermediate — a T/9/8 wins a led-toward trick while at least TWO higher
cards of the suit are still out with the defenders, and the winning hand
still held a higher card it chose not to play. That is the deep finesse:
the nine and ten are finesse cards too.

Gates: South declares a game/slam (3N or 4+) that makes EXACTLY; DD line
generated under a passive lead (real-lead re-verify is still on the human).
Emits JSON rows with the deep trick's details for dump-reading.

Usage: deep_detect.py bba/Pool_A.pbn [...] > scan.json
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

def passive_lead(hands, leader, trumpL):
    cand = [s for s in "SHDC" if s != trumpL and hands[leader][s]]
    if not cand: cand = [s for s in "SHDC" if hands[leader][s]]
    best = max(cand, key=lambda s: len(hands[leader][s]))
    low = [r for r in RANKS if r in hands[leader][best]][-1]
    return best + low

def compact_auction(b):
    am = re.search(r'\[Auction "[NESW]"\]\s*\n(.*?)(?=\n\[|\n\{|\Z)', b, re.S)
    if not am: return ""
    return " ".join(tok for ln in am.group(1).strip().splitlines() for tok in ln.split())

def deep_tricks(chrono, hands, trumpL, declarer):
    """Yield deep-finesse tricks: declarer side wins with T/9/8 in a non-trump
    suit on a led-toward trick, >=2 higher cards still with defenders, and the
    winning hand still held a higher card in the suit."""
    decl_side = {declarer, {"N":"S","S":"N"}[declarer]}
    played = {s: {su: set() for su in "SHDC"} for s in SEATS}
    out = []
    for t in range(13):
        trick = chrono[t*4:t*4+4]
        led_seat, led_card = trick[0]
        w, wc = winner(trick, trumpL)
        suit = sl(wc)
        if (w in decl_side and suit != trumpL and rk(wc) in ("T","9","8")
                and sl(led_card) == suit and led_seat != w):
            wi = RANKS.index(rk(wc))
            defs = [s for s in SEATS if s not in decl_side]
            higher_out = sum(1 for s in defs for r in hands[s][suit]
                             if r not in played[s][suit] and RANKS.index(r) < wi)
            had_higher = any(r not in played[w][suit] and RANKS.index(r) < wi
                             for r in hands[w][suit])
            # exclude cards already played to THIS trick when counting
            this_trick = {(s, rk(c)) for s, c in trick}
            higher_out = sum(1 for s in defs for r in hands[s][suit]
                             if r not in played[s][suit] and (s, r) not in this_trick
                             and RANKS.index(r) < wi)
            if higher_out >= 2 and had_higher:
                out.append({"trick": t+1, "suit": suit, "card": rk(wc),
                            "winner": w, "higher_out": higher_out})
        for s, c in trick:
            played[s][sl(c)].add(rk(c))
    return out

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
        # Structural pre-filter (the 52-solve DD line is expensive — only pay
        # for boards that CAN hold a deep finesse): some non-trump suit where
        # one NS hand carries an intermediate tenace (>=2 of QJT9 including
        # the T or 9), NS miss >=2 of AKQJ there, and partner can lead toward.
        def has_deep_shape():
            for su in "SHDC":
                if su == strain: continue
                comb = hands["N"][su] + hands["S"][su]
                missing_top = sum(1 for h in "AKQJ" if h not in comb)
                if missing_top < 2: continue
                for hand, mate in (("N","S"), ("S","N")):
                    h = set(hands[hand][su])
                    inter = h & set("QJT9")
                    if len(inter) >= 2 and (inter & {"T","9"}) and len(hands[mate][su]) >= 2:
                        return True
            return False
        if not has_deep_shape():
            continue
        need = 6 + level
        try:
            if tricks(mdeal.group(1), "S", strain) != need:
                continue
        except Exception:
            continue
        lead = passive_lead(hands, "W", strain)
        try:
            chrono = dd_line(mdeal.group(1), f"{level}{strain}", "S", lead)
        except Exception:
            continue
        deeps = deep_tricks(chrono, hands, strain, "S")
        if not deeps:
            continue
        out.append({"board": int(mb.group(1)), "contract": f"{level}{strain}",
                    "deal": mdeal.group(1), "auction": compact_auction(b),
                    "lead": lead, "deep": deeps})
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
