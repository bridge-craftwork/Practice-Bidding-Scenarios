#!/usr/bin/env python3
"""Strip-and-endplay detector (Squeezes & Endplays shelf).

Line signature: a defender WINS a trick (the throw-in) and on the very next
trick must LEAD a suit where either
  into_tenace — the declarer side wins with a card the LEADER could beat with
      a card still in his own hand (he led away from his guard into the
      tenace), or
  ruff_sluff — both declarer hands are void in the led suit and the trick is
      won by a trump while the other declarer hand sheds a loser.
Under double-dummy defense the defender only concedes like this when every
exit is as bad — i.e. he was genuinely stripped. Makes-EXACTLY gate as usual;
the dump-read remains the human gate.

Usage: endplay_detect.py bba/Pool_A.pbn [...] > scan.json
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

def find_endplay(chrono, hands, trumpL):
    """Throw-in tricks: defender wins t, leads t+1 into a tenace or gives a
    ruff-sluff. Tracks remaining cards to test 'leader still holds a beater'."""
    remaining = {s: {su: set(hands[s][su]) for su in "SHDC"} for s in SEATS}
    hits = []
    for t in range(12):
        trick = chrono[t*4:t*4+4]
        w, _ = winner(trick, trumpL)
        # update remaining after this trick
        for s, c in trick:
            remaining[s][sl(c)].discard(rk(c))
        if w not in ("E","W") or t + 1 >= 13:
            continue
        nxt = chrono[(t+1)*4:(t+1)*4+4]
        led_seat, led_card = nxt[0]
        if led_seat != w:
            continue
        s2 = sl(led_card)
        w2, wc2 = winner(nxt, trumpL)
        if w2 not in ("N","S"):
            continue
        # into_tenace: leader still holds (after t+1) a card beating the winner
        if sl(wc2) == s2:
            wi = RANKS.index(rk(wc2))
            leader_beats = any(RANKS.index(r) < wi
                               for r in remaining[w][s2] - {rk(led_card)})
            if leader_beats:
                hits.append({"class": "into_tenace", "throw_in": t+1,
                             "exit_suit": s2, "won_with": rk(wc2),
                             "endplayed": w})
        # ruff_sluff: both N,S void in led suit, won by trump
        if (trumpL != "N" and sl(wc2) == trumpL
                and not remaining["N"][s2] and not remaining["S"][s2]):
            hits.append({"class": "ruff_sluff", "throw_in": t+1,
                         "exit_suit": s2, "endplayed": w})
    return hits

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
        hits = find_endplay(chrono, hands, strain)
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
