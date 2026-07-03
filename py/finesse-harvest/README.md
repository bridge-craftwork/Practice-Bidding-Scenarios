# finesse-harvest — DDS harvest toolkit for the finesse-family play lessons

Promoted from the session scratchpad 2026-07-03 after building
To_Finesse_Or_Not with it. The conceptual spec — what each filter means, why
each exists, and the failure modes they catch — is **finesse-family-plan.md
§9**; read that first. Requires the `endplay` package (DDS).

Typical run, from the repo root:

```bash
# 1. Scan pools for South-declared, makes-EXACTLY games/slams with honor swings.
#    ~1-2 min per 500-board pool; background a multi-pool run.
python3 -P py/finesse-harvest/finesse_detect.py bba/Pool_A.pbn bba/Pool_B.pbn \
    > scan.json 2> per-pool-counts.txt

# 2. Eyeball candidates by rung (2 = needed/demand-evidence, 1 = decline).
python3 -P py/finesse-harvest/rank.py scan.json --rung 2

# 3. THE big filter: keep only boards whose DD line GENUINELY takes the
#    marked finesse (sub-honor wins a trick; marked honor never scores).
python3 -P py/finesse-harvest/finesse_taken.py scan.json

# 4. Per finalist: force West's realistic lead(s), count declarer tricks,
#    then dump the DD line and eyeball HOW it makes.
python3 -P py/finesse-harvest/verify_play.py "<deal>" 4S S HK C5
python3 -P py/finesse-harvest/verify_play.py "<deal>" 4S S --show HK

# 5. Metadata lines for the authored coaching-curated board.
python3 -P py/finesse-harvest/meta.py "<deal>"

# 6. After the serve chain: every [Play] line in a lesson makes its contract.
python3 -P py/finesse-harvest/check_served.py coaching-non-rotated/<Scn>.pbn
```

Deal strings are PBN `[Deal]` values (`"N:... ... ... ..."`, any first seat).
Card codes are suit-then-rank with `T` for ten (`HK`, `ST`). The `%`
fingerprint in an authored board is **copied from the bba/ source board**, not
recomputed. Serve chain after authoring: `coach.py validate` + `suit_quality.py`
→ `nonrotate.py` → `bridge_classroom.py` (injects `[Play]`) → `promote.py`.
