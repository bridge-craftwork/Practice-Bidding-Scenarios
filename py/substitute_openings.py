#!/usr/bin/env python3
"""substitute_openings.py — fix Open_and_Rebid's answer-key openings.

Open_and_Rebid teaches opening the suit that buys a comfortable rebid, which is
often NOT your longest suit. BBA/EPBot always opens the longest suit, so its raw
auction is the anti-lesson. This tool re-bids the non-standard boards with the
CORRECT opening forced (`bba-cli --auction-prefix`), letting EPBot resume natural
bidding — so the rebid, response, and contract all come out right.

Standard/edge-natural boards (5d-4c, balanced 12-14, 6c-4d) keep BBA's own auction.

Run AFTER the `bba` pipeline op and BEFORE `filter`:
    python3.12 py/substitute_openings.py Open_and_Rebid
It overwrites bba/<scn>.pbn in place (board order and numbers preserved).

Forced-opening rules (mirror btn/Open_and_Rebid.btn families):
    5c-4d, 5c-4d+4M, 5-5 minors -> 1D
    6-minor + 5H                -> 1H
    6-minor + 5S                -> 1S
"""
import re, subprocess, sys, os, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BBACLI = "/Applications/Bridge Utilities/bba-cli"
CARD = os.path.join(ROOT, "bbsa", "Basic-Bridge.bbsa")


def hand_of(deal, seat):
    return dict(zip('NESW', deal.split(':', 1)[1].split()))[seat]
def shape(h):
    return [len(x) if x != '-' else 0 for x in h.split('.')]  # S H D C
def deal_of(b):
    return re.search(r'\[Deal "([^"]+)"\]', b).group(1)
def bd_num(b):
    return re.search(r'\[Board "([^"]+)"\]', b).group(1)


def forced_opening(S):
    s, h, d, c = S
    if c == 5 and d == 4 and s < 4 and h < 4:    return '1D'   # 5c-4d
    if c == 5 and d == 5:                        return '1D'   # 5-5 minors
    if (c == 6 or d == 6) and h == 5:            return '1H'   # 6-minor + 5H
    if (c == 6 or d == 6) and s == 5:            return '1S'   # 6-minor + 5S
    if c == 5 and d == 4 and (s == 4 or h == 4): return '1D'   # 5c-4d + 4-card major
    return None


def substitute(scn):
    path = os.path.join(ROOT, "bba", f"{scn}.pbn")
    parts = re.split(r'(?=\[Board )', open(path).read())
    preamble = parts[0] if parts and not parts[0].startswith('[Board') else ''
    boards = [b for b in parts if b.startswith('[Board')]

    groups = {'1D': [], '1H': [], '1S': []}
    for b in boards:
        op = forced_opening(shape(hand_of(deal_of(b), 'S')))
        if op:
            head = (b[:b.find('[Auction')] if '[Auction' in b else b).rstrip() + '\n\n'
            groups[op].append(head)

    corrected = {}
    with tempfile.TemporaryDirectory() as td:
        for op, heads in groups.items():
            if not heads:
                continue
            inp, out = os.path.join(td, f"{op}.pbn"), os.path.join(td, f"{op}_out.pbn")
            open(inp, 'w').write(''.join(heads))
            subprocess.run([BBACLI, '--input', inp, '--output', out,
                            '--ns-conventions', CARD, '--ew-conventions', CARD,
                            '--auction-prefix', op, '--single-dummy',
                            '--event', scn], check=True, capture_output=True)
            for cb in re.split(r'(?=\[Board )', open(out).read()):
                if cb.startswith('[Board'):
                    corrected[deal_of(cb)] = cb

    merged, n = [preamble] if preamble else [], 0
    for b in boards:
        d = deal_of(b)
        if d in corrected:
            cb = re.sub(r'\[Board "[^"]+"\]', f'[Board "{bd_num(b)}"]', corrected[d], count=1)
            merged.append(cb); n += 1
        else:
            merged.append(b)
    open(path, 'w').write(''.join(merged))
    print(f"{scn}: substituted {n}/{len(boards)} openings "
          f"(1D:{len(groups['1D'])} 1H:{len(groups['1H'])} 1S:{len(groups['1S'])}) -> {path}")


if __name__ == "__main__":
    for scn in (sys.argv[1:] or ["Open_and_Rebid"]):
        substitute(scn)
