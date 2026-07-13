#!/usr/bin/env python3
"""harvest_common.py — shared core for the py/finesse-harvest detectors.

Single source of truth for the pieces every detector was copy-pasting —
above all book_lead(), the fix that ended the passive-lead false-positive
plague (scans whose candidates evaporate when re-dumped under West's real
lead). Every detector's acid should run on THIS lead from the start.

Import pattern (the sub-directory keeps py/'s stdlib shadows off sys.path):

    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from harvest_common import (SEATS, RANKS, parse, tricks, sl, rk,
                                winner, dd_line, book_lead, compact_auction)
"""
import re
from endplay.dds import calc_dd_table, solve_board
from endplay.types import Deal, Denom, Player, Card

SEATS = ["N", "E", "S", "W"]
RANKS = "AKQJT98765432"
DENOM = {"C": Denom.clubs, "D": Denom.diamonds, "H": Denom.hearts,
         "S": Denom.spades, "N": Denom.nt}
PLAYER = {"N": Player.north, "E": Player.east, "S": Player.south, "W": Player.west}
SEAT_OF = {Player.north: "N", Player.east: "E", Player.south: "S", Player.west: "W"}
PL = {"N": "north", "E": "east", "S": "south", "W": "west"}
LEADER_OF = {"N": "E", "E": "S", "S": "W", "W": "N"}


def parse(deal_str):
    """PBN [Deal] value -> {seat: {suit-letter: holding-string}}."""
    first, rest = deal_str.split(":")
    hands = rest.split()
    order = [first] + [SEATS[(SEATS.index(first) + i) % 4] for i in range(1, 4)]
    return {s: dict(zip("SHDC", h.split("."))) for s, h in zip(order, hands)}


def tricks(deal_str, declarer, strain):
    """Double-dummy trick count for declarer in the strain."""
    return calc_dd_table(Deal(deal_str))[DENOM[strain], PLAYER[declarer]]


def sl(card):
    return card.suit.name[0].upper()


def rk(card):
    return card.rank.name[1:]


def winner(trick, trump_letter):
    """trick = [(seat, Card) x4] in play order -> (winning seat, winning Card)."""
    ts = None if trump_letter == "N" else trump_letter
    bs, bc = trick[0]
    for s, c in trick[1:]:
        if ts and sl(c) == ts and sl(bc) != ts:
            bs, bc = s, c
        elif sl(c) == sl(bc) and c.rank.value > bc.rank.value:
            bs, bc = s, c
    return bs, bc


def dd_line(deal_str, contract, declarer, lead_code):
    """Force the opening lead, then DD-optimal play-out. -> [(seat, Card) x52]."""
    d = Deal(deal_str)
    d.trump = DENOM[contract[1]]
    d.first = getattr(Player, PL[LEADER_OF[declarer]])
    chrono = []
    for i in range(52):
        s = SEAT_OF[d.curplayer]
        c = Card(lead_code) if i == 0 else max(solve_board(d), key=lambda kv: kv[1])[0]
        chrono.append((s, c))
        d.play(c)
    return chrono


def book_lead(hands, leader, trumpL):
    """Deterministic approximation of the leader's book lead. Priority:
    singleton (suit contracts) > top of touching honors in the longest such
    suit > fourth-best of longest > top of nothing; vs suit contracts prefer
    cashing an ace over underleading it."""
    h = hands[leader]
    plain = [s for s in "SHDC" if s != trumpL and h[s]]
    if trumpL != "N":
        singles = [s for s in plain if len(h[s]) == 1]
        if singles:
            s = singles[0]
            return s + h[s]
    best = None
    for s in plain:
        cards = h[s]
        for i in range(4):                      # A,K,Q,J as sequence tops
            r1, r2 = RANKS[i], RANKS[i + 1]
            if r1 in cards and r2 in cards:
                key = (len(cards), -i)
                if best is None or key > best[0]:
                    best = (key, s, r1)
                break
    if best:
        return best[1] + best[2]
    long = max(plain, key=lambda s: (len(h[s]),
                                     max(14 - RANKS.index(r) for r in h[s])))
    cards = [r for r in RANKS if r in h[long]]
    if trumpL != "N" and cards[0] == "A":
        return long + "A"
    if len(cards) >= 4:
        return long + cards[3]
    if all(RANKS.index(r) > 4 for r in cards):
        return long + cards[0]
    return long + cards[-1]


def compact_auction(board_text):
    """Flatten a board's [Auction] block into one token string."""
    am = re.search(r'\[Auction "[NESW]"\]\s*\n(.*?)(?=\n\[|\n\{|\Z)',
                   board_text, re.S)
    if not am:
        return ""
    return " ".join(tok for ln in am.group(1).strip().splitlines()
                    for tok in ln.split())


def line_tricks(chrono, trump_letter, declarer):
    """Declarer-side trick count of a played-out line. Scans MUST gate on
    this, not (only) the DD table: a gifted book lead makes the line one
    trick richer than the table, and the technique stops being the swing."""
    decl_side = {declarer, {"N": "S", "S": "N", "E": "W", "W": "E"}[declarer]}
    n = 0
    for t in range(13):
        w, _ = winner(chrono[t*4:t*4+4], trump_letter)
        if w in decl_side:
            n += 1
    return n

def busy_suits(snap, victim, fruit_suit, trumpL):
    """Suits (≠ fruit, ≠ trump) where the victim alone guards a live
    declarer-side card: he holds a card beating some live N/S card d, no
    card above d is held by his partner, AND his holding is long enough to
    survive declarer's tops (a guard the tops would fell anyway isn't busy —
    the same always-crashing logic as the fruit-suit rung)."""
    partner = "W" if victim == "E" else "E"
    out = {}
    for su in "SHDC":
        if su in (fruit_suit, trumpL):
            continue
        vict = snap[victim][su]
        if not vict:
            continue
        top_v = min(vict, key=RANKS.index)
        decl = snap["N"][su] | snap["S"][su]
        tops_over = sum(1 for r in decl if RANKS.index(r) < RANKS.index(top_v))
        if len(vict) <= tops_over:
            continue
        for d in decl:
            di = RANKS.index(d)
            if (any(RANKS.index(v) < di for v in vict)
                    and not any(RANKS.index(p) < di for p in snap[partner][su])):
                out[su] = "".join(r for r in RANKS if r in vict)
                break
    return out
