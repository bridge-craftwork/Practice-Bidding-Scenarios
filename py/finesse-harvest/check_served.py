#!/usr/bin/env python3
"""Parse served coaching-non-rotated [Play] sections and count declarer tricks.

Usage: check_served.py coaching-non-rotated/<Scn>.pbn [...]

Post-serve verification for declarer-play lessons: replays every recorded
[Play] line (fixed-direction columns per the PBN standard, winner leads next)
and reports declarer's tricks vs the contract. FAILS-CONTRACT means the served
line does not make — a board that must not ship.
"""
import os, re, sys
from endplay.types import Card
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verify_play import trick_winner
LN={'W':['W','N','E','S'],'N':['N','E','S','W'],'E':['E','S','W','N'],'S':['S','W','N','E']}
for path in sys.argv[1:]:
    txt=open(path).read()
    scn=path.rsplit("/",1)[-1].replace(".pbn","")
    for b in re.split(r'(?=^\[Board )',txt,flags=re.M):
        mb=re.search(r'\[Board "(\d+)"\]',b); mc=re.search(r'\[Contract "(\d)([CDHSN])',b)
        md=re.search(r'\[Declarer "([NESW])"\]',b)
        mp=re.search(r'\[Play "([NESW])"\]\s*\n(.*?)(?=\n\[|\n\{|\Z)',b,re.S)
        if not(mb and mc and mp and md): continue
        lvl=int(mc.group(1)); strain=mc.group(2); need=6+lvl; decl=md.group(1)
        ds={decl,{'N':'S','S':'N','E':'W','W':'E'}[decl]}
        cols=LN[mp.group(1)]; rows=[r.split() for r in mp.group(2).strip().splitlines() if r.strip()]
        dtr=0; leader=mp.group(1)
        for row in rows:
            sc={cols[i]:Card(row[i]) for i in range(4)}
            trick=[(s,sc[s]) for s in LN[leader]]
            w=trick_winner(trick,strain)
            if w in ds: dtr+=1
            leader=w
        flag='OK' if dtr>=need else 'FAILS-CONTRACT'
        exact='(exact)' if dtr==need else f'(+{dtr-need})'
        print(f"{scn:16} b{mb.group(1):<2} {lvl}{strain} decl {decl} -> {dtr}/{need} {flag} {exact}")
