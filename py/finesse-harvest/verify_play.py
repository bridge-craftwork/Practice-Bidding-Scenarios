#!/usr/bin/env python3
"""Force an opening lead, play DD-optimal, count declarer-side tricks.

Usage:
    verify_play.py "<deal>" <contract> <declarer> <lead1> [lead2 ...]
    verify_play.py "<deal>" <contract> <declarer> --show <lead>

The first form prints declarer's trick count under each forced lead (use it to
confirm a candidate makes EXACTLY under every realistic lead). The --show form
dumps the full 13-trick DD line so you can see HOW it makes — the acid test
that the taught finesse is genuinely taken (see finesse-family-plan.md §9).
Also imported by check_served.py for its trick_winner().
"""
import sys
from endplay.types import Deal, Player, Denom, Card
from endplay.dds import solve_board

SEAT = {Player.north:"N", Player.east:"E", Player.south:"S", Player.west:"W"}
STRAIN = {"C":Denom.clubs,"D":Denom.diamonds,"H":Denom.hearts,"S":Denom.spades,"N":Denom.nt}
LEADER_OF = {"N":"E","E":"S","S":"W","W":"N"}

def sl(card):           # suit letter of a Card
    return card.suit.name[0].upper()

def trick_winner(cards_in_order, trump_letter):
    # cards_in_order: list of (seat, Card) in play order (len 4)
    tsuit = None if trump_letter == "N" else trump_letter
    best_seat, best_card = cards_in_order[0]
    for seat, c in cards_in_order[1:]:
        if tsuit is not None and sl(c) == tsuit and sl(best_card) != tsuit:
            best_seat, best_card = seat, c
        elif sl(c) == sl(best_card) and c.rank.value > best_card.rank.value:
            best_seat, best_card = seat, c
    return best_seat

def run(deal_str, contract, declarer, lead_code):
    strain = STRAIN[contract[1]]
    d = Deal(deal_str); d.trump = strain
    leader = LEADER_OF[declarer]
    d.first = getattr(Player, {"N":"north","E":"east","S":"south","W":"west"}[leader])
    forced = Card(lead_code)
    chrono = []
    for i in range(52):
        seat = SEAT[d.curplayer]
        card = forced if i == 0 else max(solve_board(d), key=lambda kv: kv[1])[0]
        chrono.append((seat, card)); d.play(card)
    # count declarer-side tricks
    decl_side = {declarer, {"N":"S","S":"N","E":"W","W":"E"}[declarer]}
    dtr = 0
    for t in range(13):
        trick = chrono[t*4:t*4+4]
        w = trick_winner(trick, contract[1])
        if w in decl_side: dtr += 1
    return dtr

def show(deal_str, contract, declarer, lead_code):
    strain = STRAIN[contract[1]]
    d = Deal(deal_str); d.trump = strain
    leader = LEADER_OF[declarer]
    d.first = getattr(Player, {"N":"north","E":"east","S":"south","W":"west"}[leader])
    forced = Card(lead_code); chrono=[]
    for i in range(52):
        seat = SEAT[d.curplayer]
        card = forced if i == 0 else max(solve_board(d), key=lambda kv: kv[1])[0]
        chrono.append((seat, card)); d.play(card)
    def cc(c): return sl(c)+c.rank.name[1:]
    for t in range(13):
        trick = chrono[t*4:t*4+4]
        w = trick_winner(trick, contract[1])
        print(f"  T{t+1}: " + "  ".join(f"{s}:{cc(c)}" for s,c in trick) + f"   -> {w}")

if __name__ == "__main__":
    deal, contract, declarer = sys.argv[1], sys.argv[2], sys.argv[3]
    need = 6 + int(contract[0])
    if sys.argv[4] == "--show":
        show(deal, contract, declarer, sys.argv[5])
    else:
        for lead in sys.argv[4:]:
            dtr = run(deal, contract, declarer, lead)
            print(f"  lead {lead}: declarer {dtr} tricks  ({'MAKES-EXACT' if dtr==need else 'down' if dtr<need else f'+{dtr-need}'}) [need {need}]")
