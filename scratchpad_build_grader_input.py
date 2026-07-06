import json, re, sys, os

ROOT = "/Users/adavidbailey/Practice-Bidding-Scenarios"
scn = "Open_and_Rebid"

# --- Layer A features by board ---
la = json.load(open(f"{ROOT}/bba-curated/{scn}.json"))
feat = {b["board"]: b for b in la["pool"]}

# --- parse bba-filtered for deal + auction per board ---
txt = open(f"{ROOT}/bba-filtered/{scn}.pbn").read()
blocks = re.split(r'(?=\[Board )', txt)

def tagval(block, tag):
    m = re.search(r'\[' + tag + r' "([^"]*)"\]', block)
    return m.group(1) if m else None

records = []
for b in blocks:
    bd = tagval(b, "Board")
    if not bd:
        continue
    dealer = tagval(b, "Dealer")
    deal = tagval(b, "Deal")
    contract = tagval(b, "Contract")
    result = tagval(b, "Result")
    decl = tagval(b, "Declarer")
    # auction lines (between [Auction ...] and next [ or {)
    am = re.search(r'\[Auction "[^"]*"\]\n(.*?)(?=\n\[|\n\{|\Z)', b, re.S)
    calls = []
    if am:
        for line in am.group(1).splitlines():
            for tok in line.split():
                if tok.startswith('=') or tok.startswith('%'):
                    continue
                calls.append(tok)
    f = feat.get(bd, {})
    # map calls to seats starting from dealer
    order = ['N', 'E', 'S', 'W']
    start = order.index(dealer) if dealer in order else 0
    seatcalls = []
    for i, c in enumerate(calls):
        seatcalls.append((order[(start + i) % 4], c))
    # South's calls (non-pass, non-note)
    south_calls = [c for (s, c) in seatcalls if s == 'S' and c not in ('Pass', 'AP')]
    # South is dealer here (dealer south), so south_calls[0]=opening, [1]=rebid...
    rebid = south_calls[1] if len(south_calls) > 1 else None
    def cat(r):
        if r is None: return "no-rebid"
        if r == "1NT" or r == "1N": return "rebid-1NT"
        if r == "2NT" or r == "2N": return "rebid-2NT"
        if r in ("2C","2D","2H","2S","3C","3D","3H","3S"): return "rebid-suit"
        return "rebid-other"
    records.append({
        "board": bd,
        "deal_hash": f.get("deal_hash"),
        "dealer": dealer,
        "deal": deal,
        "auction": " ".join(calls),
        "seat_auction": " ".join(f"{s}:{c}" for s, c in seatcalls),
        "south_calls": south_calls,
        "rebid_cat": cat(rebid),
        "contract": contract,
        "declarer": decl,
        "result": result,
        "hcp": f.get("hcp"),
        "flags": f.get("flags"),
        "matched_intended_auction": f.get("matched_intended_auction"),
        "dd_class": f.get("dd_class"),
        "dd_declarer_tricks": f.get("dd_declarer_tricks"),
    })

json.dump(records, open(f"/private/tmp/claude-501/-Users-adavidbailey-Practice-Bidding-Scenarios/dfe200c8-a8fd-43da-9601-b45e75f03320/scratchpad/grader_input_all.json", "w"), indent=1)

# distribution
from collections import Counter
c = Counter(r["rebid_cat"] for r in records)
print("total boards:", len(records))
print("rebid categories:", dict(c))
