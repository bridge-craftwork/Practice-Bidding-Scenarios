#!/usr/bin/env python3
"""For each single-swing rung-2 candidate in a finesse_detect.py scan, force a
PASSIVE neutral opening lead (West's longest side suit, low) and check the DD
line actually TAKES the marked finesse: declarer wins a trick in the finesse
suit with a card BELOW the missing honor, AND the marked honor NEVER wins a
trick (it is trapped). This is the filter that kills most swing candidates —
boards that "make exactly with the honor onside" but via side-suit
establishment, honor-forced establishment, a doubleton drop (Rabbi's turf), or
a defensive gift. See finesse-family-plan.md §9.

Usage: finesse_taken.py scan.json
"""
import json, sys
from endplay.types import Deal, Player, Denom, Card
from endplay.dds import solve_board

SEAT={Player.north:"N",Player.east:"E",Player.south:"S",Player.west:"W"}
STRAIN={"C":Denom.clubs,"D":Denom.diamonds,"H":Denom.hearts,"S":Denom.spades,"N":Denom.nt}
LEADER_OF={"N":"E","E":"S","S":"W","W":"N"}
PL={"N":"north","E":"east","S":"south","W":"west"}
RANKS="AKQJT98765432"
SEATS=["N","E","S","W"]

def parse(ds):
    first,rest=ds.split(":"); hands=rest.split()
    order=[first]+[SEATS[(SEATS.index(first)+i)%4] for i in range(1,4)]
    return {s:dict(zip("SHDC",h.split("."))) for s,h in zip(order,hands)}

def sl(c): return c.suit.name[0].upper()
def rk(c): return c.rank.name[1:]

def winner(trick, trumpL):
    ts=None if trumpL=="N" else trumpL
    bs,bc=trick[0]
    for s,c in trick[1:]:
        if ts and sl(c)==ts and sl(bc)!=ts: bs,bc=s,c
        elif sl(c)==sl(bc) and c.rank.value>bc.rank.value: bs,bc=s,c
    return bs

def play_line(ds, contract, declarer, lead):
    d=Deal(ds); d.trump=STRAIN[contract[1]]
    d.first=getattr(Player,PL[LEADER_OF[declarer]])
    chrono=[]
    for i in range(52):
        s=SEAT[d.curplayer]
        c=Card(lead) if i==0 else max(solve_board(d),key=lambda kv:kv[1])[0]
        chrono.append((s,c)); d.play(c)
    return chrono

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from harvest_common import book_lead

def passive_lead(hands, leader, *rest):
    """Book lead (harvest_common) — trump letter is the LAST argument; any
    avoid-suit argument from older call sites is intentionally ignored: the
    acid must run on the REAL lead, even when it hits the taught suit."""
    return book_lead(hands, leader, rest[-1])

def check(ds, contract, declarer, fin_suit, honor, marked):
    hands=parse(ds); trumpL=contract[1]
    leader=LEADER_OF[declarer]
    lead=passive_lead(hands, leader, fin_suit, trumpL)
    chrono=play_line(ds, contract, declarer, lead)
    need=6+int(contract[0])
    decl_side={declarer,{"N":"S","S":"N","E":"W","W":"E"}[declarer]}
    dtr=0; finesse_taken=False; honor_won=False
    hv=RANKS.index(honor)
    for t in range(13):
        trick=chrono[t*4:t*4+4]
        w=winner(trick,trumpL)
        wc=[c for s,c in trick if s==w][0]
        # did the MARKED honor card win this trick? (establishment, not finesse)
        if w==marked and sl(wc)==fin_suit and rk(wc)==honor:
            honor_won=True
        if w in decl_side:
            dtr+=1
            # declarer wins finesse suit with a card BELOW the missing honor
            if sl(wc)==fin_suit and RANKS.index(rk(wc))>hv:
                finesse_taken=True
    # genuine finesse: sub-honor wins AND the marked honor is trapped (never wins)
    return dtr, need, (finesse_taken and not honor_won), lead

def main():
    data=json.load(open(sys.argv[1]))
    hits=[]
    for pool,cands in data.items():
        for c in cands:
            s2=[s for s in c["swings"] if s["rung"]==2]
            if len(c["swings"])!=1 or len(s2)!=1: continue
            sw=s2[0]
            if not sw["holder_bid"]: continue
            try:
                dtr,need,taken,lead=check(c["deal"],c["contract"],"S",sw["suit"],sw["honor"],sw["held_by"])
            except Exception:
                continue
            if dtr==need and taken:
                hits.append((pool,c["board"],c["contract"],sw["suit"],sw["honor"],sw["held_by"],
                             c["e_calls"] if sw["held_by"]=="E" else c["w_calls"],lead,c["auction"],c["deal"]))
    print(f"CLEAN finesse-taken boards: {len(hits)}\n")
    for h in hits:
        print(f"{h[0][:20]:20} b{h[1]:<3} {h[2]} fin {h[3]}{h[4]}->{h[5]} holder:{h[6]} passlead:{h[7]}")
        print(f"    auc: {h[8]}")
        print(f"    deal: {h[9]}")

if __name__=="__main__": main()
