#!/usr/bin/env python3
"""Simple-squeeze detector (Squeezes & Endplays shelf).

Line signature: a declarer-side card WINS a plain-suit trick late in the hand
although the defenders originally held higher cards in that suit — and every
one of those higher cards was DISCARDED on other suits' leads (never played to
a trick in the suit). Under double-dummy defense a guard is only thrown when
every alternative is as bad: that is the squeeze. The makes-EXACTLY gate keeps
idle-pitch false positives rare; the dump-read remains the human gate.

Records the squeezed defender, the promoted winner, the pitch tricks, and
whether the same defender was also stripped in a second suit declarer scored
(the two-menace signature of the classic simple squeeze).

Usage: squeeze_detect.py bba/Pool_A.pbn [...] > scan.json
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

def book_lead(hands, leader, trumpL):
    """Deterministic approximation of West's book lead — the lesson of the
    day, learned repeatedly: the acid MUST run on a realistic line, not a
    synthetic passive one. Priority: singleton (suit contracts) > top of
    touching honors in the longest such suit > fourth-best of longest >
    top of nothing. Vs suit contracts, prefer the A over underleading it."""
    h = hands[leader]
    plain = [s for s in "SHDC" if s != trumpL and h[s]]
    if trumpL != "N":
        singles = [s for s in plain if len(h[s]) == 1]
        if singles:
            s = singles[0]
            return s + h[s]
    # touching-honor sequence headed T or better
    best = None
    for s in plain:
        cards = h[s]
        for i in range(4):                       # A,K,Q,J as seq tops
            r1, r2 = RANKS[i], RANKS[i+1]
            if r1 in cards and r2 in cards:
                key = (len(cards), -i)
                if best is None or key > best[0]:
                    best = (key, s, r1)
                break
    if best:
        return best[1] + best[2]
    long = max(plain, key=lambda s: (len(h[s]), max(14-RANKS.index(r) for r in h[s])))
    cards = [r for r in RANKS if r in h[long]]
    if trumpL != "N" and cards[0] == "A":
        return long + "A"                        # don't underlead an ace vs a suit
    if len(cards) >= 4:
        return long + cards[3]                   # fourth-best
    if all(RANKS.index(r) > 4 for r in cards):
        return long + cards[0]                   # top of nothing
    return long + cards[-1]

passive_lead = book_lead

def compact_auction(b):
    am = re.search(r'\[Auction "[NESW]"\]\s*\n(.*?)(?=\n\[|\n\{|\Z)', b, re.S)
    if not am: return ""
    return " ".join(tok for ln in am.group(1).strip().splitlines() for tok in ln.split())

def find_squeeze(chrono, hands, trumpL):
    """Return squeeze hits: a declarer card wins a late plain-suit trick as the
    NEW master — the defense originally held higher cards, none remain, and at
    least one of them was PITCHED on another suit's lead (the squeezed guard;
    beaters that fell to earlier rounds of the suit are normal play)."""
    pitches = {s: {su: [] for su in "SHDC"} for s in ("E","W")}
    remaining = {s: {su: set(hands[s][su]) for su in "SHDC"} for s in SEATS}
    hits = []
    for t in range(13):
        trick = chrono[t*4:t*4+4]
        led = sl(trick[0][1])
        w, wc = winner(trick, trumpL)
        suit = sl(wc)
        if w in ("N","S") and suit != trumpL and led == suit and t >= 6:
            wi = RANKS.index(rk(wc))
            orig = [(d, r) for d in ("E","W") for r in hands[d][suit]
                    if RANKS.index(r) < wi]
            live = [(d, r) for d in ("E","W") for r in remaining[d][suit]
                    if RANKS.index(r) < wi]
            pitched = [(d, r) for d, r in orig
                       if any(pr == r for _, pr in pitches[d][suit])]
            if orig and not live and pitched:
                sq_def = pitched[-1][0]
                other = [su for su in "SHDC" if su != suit and pitches[sq_def][su]]
                hits.append({"trick": t+1, "suit": suit, "card": rk(wc),
                             "squeezed": sq_def,
                             "beaters_pitched": [r for _, r in pitched],
                             "pitch_tricks": [pt for pt, pr in pitches[sq_def][suit]
                                              if any(pr == r for _, r in pitched)],
                             "also_pitched_suits": other})
        for s, c in trick[1:]:
            if s in ("E","W") and sl(c) != led and (trumpL == "N" or sl(c) != trumpL):
                pitches[s][sl(c)].append((t+1, rk(c)))
        for s, c in trick:
            remaining[s][sl(c)].discard(rk(c))
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
        # pre-filter: a runnable long suit (6+ combined w/ A+K, or 7+) exists
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
        lead = passive_lead(hands, "W", strain)
        try:
            chrono = dd_line(mdeal.group(1), f"{level}{strain}", "S", lead)
        except Exception:
            continue
        hits = find_squeeze(chrono, hands, strain)
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
