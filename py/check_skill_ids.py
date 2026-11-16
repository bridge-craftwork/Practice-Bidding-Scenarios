#!/usr/bin/env python3
"""Check the IDs in btn/-scenario-skills.txt against bridge-common-conventions.

Every ID a scenario is tagged with must be defined in the published snapshot
of bridge-craftwork/bridge-common-conventions (its pack.json): a typo, or an
ID nobody defined, would otherwise go unnoticed and the scenario would be
offered to nobody.

    python3 py/check_skill_ids.py                # the published snapshot
    python3 py/check_skill_ids.py --pack FILE    # a pack.json on disk

Exit status 1 when an ID is not defined. The snapshot is fetched only by
this check; building the manifest needs no network.
"""

import argparse
import json
import os
import re
import sys

# py/ holds a select.py, which would stand in for the standard library's
# `select` (urllib needs it) while this folder is on the import path. So the
# folder comes off the path, and the reader below is a copy of
# build_manifest.py's, not an import of it.
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.curdir) != _HERE]

import urllib.request  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_PATH = os.path.join(ROOT, "btn", "-scenario-skills.txt")


def load_scenario_skills(path=SKILLS_PATH):
    """{scenario: [ID]} from btn/-scenario-skills.txt, as build_manifest.py reads it."""
    out = {}
    with open(path, encoding="utf-8") as fh:
        for n, raw in enumerate(fh, 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            name, sep, ids = line.partition(":")
            skills = [i.strip() for i in ids.split(",") if i.strip()]
            if not sep or not name.strip() or not skills:
                sys.exit(f"{os.path.relpath(path, ROOT)}:{n}: expected `Scenario: category/skill, ...`")
            bad = [i for i in skills if not re.fullmatch(r"[a-z0-9_]+/[a-z0-9_]+", i)]
            if bad:
                sys.exit(f"{os.path.relpath(path, ROOT)}:{n}: not a skill ID: {', '.join(bad)}")
            out[name.strip()] = skills
    return out


PACK_URL = "https://bridge-craftwork.github.io/bridge-common-conventions/pack.json"


def load_pack(path=None):
    if path:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    req = urllib.request.Request(PACK_URL, headers={"User-Agent": "pbs-check-skill-ids"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def check(skills, pack):
    """(unknown, kinds): {id: [scenario]} not defined, and a count by kind."""
    defs = pack.get("conventions", {})
    unknown, kinds = {}, {}
    for scenario in sorted(skills):
        for i in skills[scenario]:
            if i not in defs:
                unknown.setdefault(i, []).append(scenario)
    for i in {i for ids in skills.values() for i in ids if i in defs}:
        kind = defs[i].get("kind", "convention")
        kinds[kind] = kinds.get(kind, 0) + 1
    return unknown, kinds


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pack", help="a pack.json on disk, instead of the published one")
    args = ap.parse_args()

    skills = load_scenario_skills()
    try:
        pack = load_pack(args.pack)
    except (OSError, ValueError) as e:
        sys.exit(f"could not read the snapshot ({args.pack or PACK_URL}): {e}")
    if pack.get("schema") != "pack/v1" or not isinstance(pack.get("conventions"), dict):
        sys.exit("not a pack snapshot: `schema` is not \"pack/v1\"")

    unknown, kinds = check(skills, pack)
    rel = os.path.relpath(SKILLS_PATH, ROOT)
    ids = {i for v in skills.values() for i in v}
    by_kind = ", ".join(f"{n} {k}" for k, n in sorted(kinds.items(), key=lambda kv: -kv[1]))
    print(f"{rel}: {len(skills)} scenarios, {len(ids)} IDs ({by_kind})")
    for i in sorted(unknown):
        print(f"{rel}: `{i}` is not defined in bridge-common-conventions "
              f"(used by {', '.join(unknown[i])})", file=sys.stderr)
    if unknown:
        sys.exit(1)
    print("every ID is defined")


if __name__ == "__main__":
    main()
