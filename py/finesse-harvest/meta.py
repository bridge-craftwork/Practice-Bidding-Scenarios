#!/usr/bin/env python3
"""Compute {Shape}/{HCP}/{Losers} lines for a deal, order N E S W.

Usage: meta.py "<deal>"     (a PBN [Deal] value, any first seat)

Paste the three lines into an authored coaching-curated board. The `%`
fingerprint line is NOT computed here — copy it from the bba/ source board
(it is BBA's own fingerprint, not a sha1 of the deal string).
"""
import sys
SEATS=["N","E","S","W"]
HCPV={"A":4,"K":3,"Q":2,"J":1}
def parse(ds):
    first,rest=ds.split(":"); hands=rest.split()
    order=[first]+[SEATS[(SEATS.index(first)+i)%4] for i in range(1,4)]
    return {s:h.split(".") for s,h in zip(order,hands)}   # [S,H,D,C]
def hcp(suits): return sum(HCPV.get(c,0) for suit in suits for c in suit)
def shape(suits): return "".join(str(len(x)) for x in suits)
def ltc(suits):
    # standard Losing Trick Count: per suit, losers among missing A/K/Q, capped by length
    tot=0
    for s in suits:
        n=len(s)
        if n==0: continue
        cap=min(3,n)
        miss=0
        for h in "AKQ"[:cap]:
            if h not in s: miss+=1
        tot+=miss
    return tot
def main():
    ds=sys.argv[1]; d=parse(ds)
    sh=" ".join(shape(d[s]) for s in SEATS)
    hp=" ".join(str(hcp(d[s])) for s in SEATS)
    lo=" ".join(str(ltc(d[s])) for s in SEATS)
    print("{Shape "+sh+"}")
    print("{HCP "+hp+"}")
    print("{Losers "+lo+"}")
if __name__=="__main__": main()
