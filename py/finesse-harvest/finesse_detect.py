#!/usr/bin/env python3
"""Finesse-family harvest detector.

Scans a bba/<pool>.pbn pool for boards where SOUTH declares a game/slam that
makes EXACTLY, and classifies the finesse structure via a swing test (move a
missing honor to the other defender, re-solve, see if South's trick count moves).

Emits JSON candidates keyed by pool name. Swing sign: delta > 0 = the honor is
onside and NEEDED (rung 2, demand-evidence); delta < 0 = offside / needless
(rung 1, decline). See finesse-family-plan.md §9 — a swing only flags
honor-location SENSITIVITY; the downstream filters (finesse_taken.py,
verify_play.py) decide whether the finesse is genuinely takeable/taken.
"""
import sys, json, re
from endplay.dds import calc_dd_table
from endplay.types import Deal, Denom, Player

RANKS = "AKQJT98765432"
HONORS = ["K", "Q", "J"]
DENOM = {"C": Denom.clubs, "D": Denom.diamonds, "H": Denom.hearts,
         "S": Denom.spades, "N": Denom.nt}
PLAYER = {"N": Player.north, "E": Player.east, "S": Player.south, "W": Player.west}
SEATS = ["N", "E", "S", "W"]

def parse_deal(deal_str):
    # "N:holdN holdE holdS holdW" -> dict seat -> [4 suit-strings SHDC]
    first, rest = deal_str.split(":")
    hands = rest.strip().split()
    order = [first, *[SEATS[(SEATS.index(first)+i) % 4] for i in range(1,4)]]
    d = {}
    for seat, h in zip(order, hands):
        d[seat] = h.split(".")   # [S,H,D,C]
    return d

def build_deal_str(d):
    return "N:" + " ".join(".".join(d[s]) for s in ["N","E","S","W"])

def tricks(deal_str, declarer, strain):
    t = calc_dd_table(Deal(deal_str))
    return t[DENOM[strain], PLAYER[declarer]]

SUIT_POS = {"S":0,"H":1,"D":2,"C":3}

def move_honor(d, suit, honor, to_seat):
    """Return new deal dict with `honor` of `suit` moved to `to_seat`,
       swapping a low card back. None if honor not movable or already there."""
    si = SUIT_POS[suit]
    holder = None
    for s in SEATS:
        if honor in d[s][si]:
            holder = s; break
    if holder is None or holder == to_seat:
        return None
    # need a low card in to_seat's same suit to swap back (keep 13 each)
    tgt = d[to_seat][si]
    low = None
    for r in reversed(RANKS):
        if r in tgt:
            low = r; break
    if low is None:
        return None  # to_seat void in suit; swap would change suit count -> skip
    nd = {s: list(d[s]) for s in SEATS}
    nd[holder][si] = "".join(r for r in RANKS if r in nd[holder][si] and r != honor)
    nd[to_seat][si] = "".join(r for r in RANKS if r in nd[to_seat][si] and r != low)
    nd[holder][si] = "".join(sorted(nd[holder][si] + low, key=RANKS.index))
    nd[to_seat][si] = "".join(sorted(nd[to_seat][si] + honor, key=RANKS.index))
    return nd

def missing_honors(d, suit):
    """Honors NOT held by NS (declaring side), highest first."""
    si = SUIT_POS[suit]
    ns = d["N"][si] + d["S"][si]
    return [h for h in HONORS if h not in ns]

def analyze_board(deal_str, declarer, level, strain):
    d = parse_deal(deal_str)
    need = 6 + level
    base = tricks(deal_str, declarer, strain)
    if base != need:
        return None  # only makes-EXACTLY boards
    defenders = ["E","W"] if declarer in ("N","S") else ["N","S"]
    swings = []
    for suit in ["S","H","D","C"]:
        for honor in missing_honors(d, suit):
            # find actual holder
            si = SUIT_POS[suit]
            holder = next((s for s in SEATS if honor in d[s][si]), None)
            if holder not in defenders:
                continue
            other = defenders[1] if holder == defenders[0] else defenders[0]
            nd = move_honor(d, suit, honor, other)
            if nd is None:
                continue
            t2 = tricks(build_deal_str(nd), declarer, strain)
            if t2 != base:
                swings.append({
                    "suit": suit, "honor": honor,
                    "held_by": holder, "delta": base - t2,
                    # delta>0: moving honor away LOSES tricks => finesse thru holder NEEDED/onside
                })
    if not swings:
        return None
    return {"base": base, "need": need, "swings": swings}

def compact_auction(lines):
    calls = []
    for ln in lines:
        for tok in ln.split():
            calls.append(tok)
    return " ".join(calls)

def seat_calls(auction_calls, dealer):
    """Return dict seat -> list of non-Pass calls that seat made."""
    out = {s: [] for s in SEATS}
    seat = dealer
    for tok in auction_calls:
        if tok.startswith("="):     # note ref attaches to prev call, skip cursor
            continue
        if tok not in ("Pass", "AP"):
            out[seat].append(tok)
        seat = SEATS[(SEATS.index(seat) + 1) % 4]
    return out

def is_game_or_slam(level, strain):
    if level >= 4:
        return True
    if level == 3 and strain == "N":
        return True
    return False

def scan_pool(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    boards = re.split(r'(?=^\[Board )', txt, flags=re.M)
    out = []
    for b in boards:
        m_board = re.search(r'\[Board "(\d+)"\]', b)
        m_deal = re.search(r'\[Deal "([^"]+)"\]', b)
        m_decl = re.search(r'\[Declarer "([NESW])"\]', b)
        m_ctr = re.search(r'\[Contract "(\d)([CDHSN][T]?)', b)
        m_dlr = re.search(r'\[Dealer "([NESW])"\]', b)
        if not (m_board and m_deal and m_decl and m_ctr and m_dlr):
            continue
        decl = m_decl.group(1)
        if decl != "S":
            continue
        level = int(m_ctr.group(1))
        strain = m_ctr.group(2)[0]
        if not is_game_or_slam(level, strain):
            continue
        # auction
        am = re.search(r'\[Auction "[NESW]"\]\s*\n(.*?)(?=\n\[|\n\{|\Z)', b, re.S)
        calls = compact_auction(am.group(1).strip().splitlines()) if am else ""
        try:
            res = analyze_board(m_deal.group(1), decl, level, strain)
        except Exception:
            continue
        if res is None:
            continue
        sc = seat_calls(calls.split(), m_dlr.group(1))
        opp_calls = sorted(set(sc["E"] + sc["W"]))
        # annotate each swing: did the honor-holder bid?
        for sw in res["swings"]:
            sw["holder_bid"] = bool(sc[sw["held_by"]])
            sw["rung"] = 2 if sw["delta"] > 0 else 1
        out.append({
            "board": int(m_board.group(1)),
            "contract": f"{level}{strain}",
            "deal": m_deal.group(1),
            "auction": calls,
            "opp_bid": bool(opp_calls),
            "opp_calls": opp_calls,
            "e_calls": sc["E"], "w_calls": sc["W"],
            **res,
        })
    return out

if __name__ == "__main__":
    pools = sys.argv[1:]
    results = {}
    for p in pools:
        name = re.sub(r'.*/', '', p).replace(".pbn","")
        try:
            results[name] = scan_pool(p)
            sys.stderr.write(f"{name}: {len(results[name])} candidates\n")
        except Exception as e:
            sys.stderr.write(f"{name}: ERROR {e}\n")
    print(json.dumps(results, indent=1))
