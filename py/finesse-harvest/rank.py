#!/usr/bin/env python3
"""Rank finesse_detect.py candidates for eyeballing, by rung.

Usage: rank.py scan.json [--rung 2|1]

Rung 2 = needed onside finesse (demand-evidence); rung 1 = offside/needless
(decline). Ranks auction-marked candidates first, then game contracts, then
fewer competing swings. parse_deal()/holding() are also import-handy for
ad-hoc filters over the scan JSON.
"""
import sys, json

SEATS = ["N","E","S","W"]

def parse_deal(ds):
    first, rest = ds.split(":")
    hands = rest.split()
    order = [first] + [SEATS[(SEATS.index(first)+i)%4] for i in range(1,4)]
    d = {}
    for seat,h in zip(order,hands):
        s = h.split(".")
        d[seat] = {"S":s[0],"H":s[1],"D":s[2],"C":s[3]}
    return d

def holding(d, seat, suit):
    return d[seat][suit] or "-"

def main():
    data = json.load(open(sys.argv[1]))
    want_rung = 2
    if "--rung" in sys.argv:
        want_rung = int(sys.argv[sys.argv.index("--rung")+1])
    rows = []
    for pool, cands in data.items():
        for c in cands:
            d = parse_deal(c["deal"])
            for sw in c["swings"]:
                if sw["rung"] != want_rung:
                    continue
                # for rung 2 want the honor-holder to have bid (auction marks it)
                marked = sw.get("holder_bid", False)
                suit = sw["suit"]; hld = sw["held_by"]
                ns = holding(d,"N",suit)+" / "+holding(d,"S",suit)
                ew = holding(d,"E",suit)+" / "+holding(d,"W",suit)
                rows.append({
                    "pool":pool,"board":c["board"],"ctr":c["contract"],
                    "suit":suit,"honor":sw["honor"],"held":hld,"delta":sw["delta"],
                    "marked":marked,
                    "ecalls":c["e_calls"],"wcalls":c["w_calls"],
                    "nsH":ns,"ewH":ew,"auction":c["auction"],"deal":c["deal"],
                    "nswings":len(c["swings"]),
                })
    # rank: marked first, then game contracts (3N/4M), then fewer competing swings
    def keyf(r):
        game_pref = {"3N":0,"4S":0,"4H":0}.get(r["ctr"],1)
        return (not r["marked"], game_pref, r["nswings"])
    rows.sort(key=keyf)
    print(f"# rung {want_rung}: {len(rows)} swing-rows\n")
    for r in rows[:40]:
        mk = "MARKED" if r["marked"] else "quiet "
        holder_calls = r["ecalls"] if r["held"]=="E" else r["wcalls"]
        print(f"{r['pool'][:22]:22} b{r['board']:<3} {r['ctr']} | "
              f"finesse {r['suit']}{r['honor']} in {r['held']} d{r['delta']:+d} {mk} "
              f"holder-bid:{holder_calls}")
        print(f"    {r['suit']}: NS[{r['nsH']}]  EW[{r['ewH']}]   swings:{r['nswings']}")
        print(f"    auc: {r['auction']}")
        print(f"    deal: {r['deal']}")
    return rows

if __name__ == "__main__":
    main()
