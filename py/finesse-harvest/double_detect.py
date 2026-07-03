#!/usr/bin/env python3
"""Double-finesse detector (lesson 1c).

Structure hunted: ONE suit missing TWO honors, tenace concentrated in one NS
hand, in a South-declared game/slam (3N or 4+) that makes EXACTLY:
  AQT missing K+J  — finesse the T (or Q) first, then repeat: ~76% for one of two.
  AJT missing K+Q  — run the J/T twice.
Both missing honors must be with the DEFENDERS, and the tenace's partner needs
2+ cards to lead toward it twice.

Gate = DD-LINE ACID under a passive lead: the suit is led from the partner
side toward the tenace at least TWICE, and the tenace hand wins at least one
of those tricks with a card BELOW both missing honors. `first_lost` marks the
teaching-gold shape (first finesse loses, second wins — the 76% justification
made visible). See finesse-family-plan.md §9.

Usage: double_detect.py bba/Pool_A.pbn [...] > scan.json
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

def passive_lead(hands, leader, fin_suit, trumpL):
    cand = [s for s in "SHDC" if s != fin_suit and s != trumpL and hands[leader][s]]
    if not cand: cand = [s for s in "SHDC" if hands[leader][s]]
    best = max(cand, key=lambda s: len(hands[leader][s]))
    low = [r for r in RANKS if r in hands[leader][best]][-1]
    return best + low

def compact_auction(b):
    am = re.search(r'\[Auction "[NESW]"\]\s*\n(.*?)(?=\n\[|\n\{|\Z)', b, re.S)
    if not am: return ""
    return " ".join(tok for ln in am.group(1).strip().splitlines() for tok in ln.split())

def acid(chrono, trumpL, fin_suit, tenace_hand, partner, missing, declarer):
    """>=2 leads toward the tenace; tenace wins >=1 with a sub-honor card;
    classify whether the FIRST finesse lost (teaching gold)."""
    decl_side = {declarer, {"N":"S","S":"N"}[declarer]}
    hi = min(RANKS.index(h) for h in missing)     # higher missing honor
    leads_toward = 0; sub_wins = 0; results = []
    for t in range(13):
        trick = chrono[t*4:t*4+4]
        led_seat, led_card = trick[0]
        if led_seat != partner or sl(led_card) != fin_suit:
            continue
        w = winner(trick, trumpL)
        wc = next(c for s, c in trick if s == w)
        leads_toward += 1
        won = w in decl_side and sl(wc) == fin_suit and RANKS.index(rk(wc)) > hi
        if won: sub_wins += 1
        results.append("win" if w in decl_side else "lose")
    if leads_toward >= 2 and sub_wins >= 1:
        return {"leads_toward": leads_toward, "sub_wins": sub_wins,
                "sequence": results, "first_lost": results[0] == "lose"}
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
            for suit in "SHDC":
                if suit == strain: continue
                h, p = hands[tenace_hand][suit], hands[partner][suit]
                if len(h) < 3 or len(p) < 2: continue
                s = set(h); comb = s | set(p)
                for ten, mis in (({"A","Q","T"}, ("K","J")), ({"A","J","T"}, ("K","Q"))):
                    if ten <= s and not (set(mis) & comb):
                        holders = [next((x for x in SEATS if m in hands[x][suit]), None) for m in mis]
                        if all(hh in ("E","W") for hh in holders):
                            cands.append((suit, tenace_hand, partner, mis, holders, h, p))
                        break
        if not cands:
            continue
        need = 6 + level
        try:
            if tricks(mdeal.group(1), "S", strain) != need:
                continue
        except Exception:
            continue
        for suit, tenace_hand, partner, mis, holders, h, p in cands:
            lead = passive_lead(hands, "W", suit, strain)
            try:
                chrono = dd_line(mdeal.group(1), f"{level}{strain}", "S", lead)
            except Exception:
                continue
            a = acid(chrono, strain, suit, tenace_hand, partner, mis, "S")
            if a is None:
                continue
            out.append({"board": int(mb.group(1)), "contract": f"{level}{strain}",
                        "deal": mdeal.group(1), "auction": compact_auction(b),
                        "suit": suit, "missing": "".join(mis),
                        "tenace_hand": tenace_hand, "tenace": h, "partner_len": len(p),
                        "holders": holders, "lead": lead, "acid": a})
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
