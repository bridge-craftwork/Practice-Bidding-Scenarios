import json, os, glob, sys
from collections import Counter

ROOT = "/Users/adavidbailey/Practice-Bidding-Scenarios"
SP = "/private/tmp/claude-501/-Users-adavidbailey-Practice-Bidding-Scenarios/dfe200c8-a8fd-43da-9601-b45e75f03320/scratchpad"
scn = "Open_and_Rebid"

sys.path.append(os.path.join(ROOT, "py"))
from curate import deal_hash  # canonical, same fn annotate.py uses

# board -> correct deal string (from bba-filtered, correctly paired in grader_input)
recs = json.load(open(f"{SP}/grader_input_all.json"))
deal_by_board = {str(r["board"]): r["deal"] for r in recs}
hash_by_board = {b: deal_hash(d) for b, d in deal_by_board.items()}

# sanity: are these hashes present in bba/<scn>.pbn?  (annotate matches there)
bba_txt = open(f"{ROOT}/bba/{scn}.pbn").read()
import re
bba_hashes = set()
for m in re.finditer(r'\[Deal "([^"]+)"\]', bba_txt):
    bba_hashes.add(deal_hash(m.group(1)))

verdicts = []
seen = set()
missing_in_bba = 0
for f in sorted(glob.glob(f"{SP}/grade/verdicts_*.json")):
    for v in json.load(open(f)):
        b = str(v["board"])
        if b in seen:
            continue
        seen.add(b)
        # OVERWRITE deal_hash with the correct hash of the graded deal
        h = hash_by_board.get(b)
        if h is None:
            continue
        if h not in bba_hashes:
            missing_in_bba += 1
        v["deal_hash"] = h
        verdicts.append(v)

verdicts.sort(key=lambda v: int(v["board"]))
tiers = Counter(v["bidding"]["tier"] for v in verdicts)
out = {
    "scenario": scn,
    "graded": len(verdicts),
    "aggregates": {"bidding_tiers": dict(tiers)},
    "verdicts": verdicts,
}
json.dump(out, open(f"{ROOT}/bba-curated/{scn}-graded.json", "w"), indent=1)
print("merged verdicts:", len(verdicts))
print("bidding tiers:", dict(tiers))
print("hashes NOT found in bba/ (should be 0):", missing_in_bba)
pool = [v for v in verdicts if v["bidding"]["tier"] in ("textbook", "judgment") and v.get("difficulty", 9) <= 3]
print("coaching-eligible (textbook/judgment, diff<=3):", len(pool))
# per rebid-cat of eligible
cat_by_board = {str(r["board"]): r["rebid_cat"] for r in recs}
print("eligible by rebid-cat:", dict(Counter(cat_by_board.get(str(v["board"])) for v in pool)))
