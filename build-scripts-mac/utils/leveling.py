"""
Leveling (issue #322): which dealer script, and which PBN, a scenario's
downstream stages read.

A scenario levels when its script declares hand types: variables named
HandType_* (see docs/leveling-guide.md in the dealer3 repo). The level
operation writes its leveled copy:

    dlr/<name>.dlr  --[level]-->  dlr-leveled/<name>.dlr

and from then on the leveled version wins wherever it exists. pbn deals the
leveled script into pbn-leveled/<name>.pbn and keeps pbn/<name>.pbn as the
natural mix, which is how you see what leveling changed. rotate, bba, gib and
package read the leveled files. They all ask leveled_or_original() rather
than deciding for themselves.

A leveled file's first line records the dlr it was made from:

    # leveled-from: dlr/<name>.dlr sha256:<hex>

so a stale one is caught instead of used. (dealer3 stamps no source hash of
its own.)

Stdlib only, so CI can run the check without dealer3:

    python3 build-scripts-mac/utils/leveling.py --check
"""
import hashlib
import os
import re
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FOLDERS

# dealer3 reads the prefix in any case: handtype_x declares the type x too
HAND_TYPE_RE = re.compile(r"^\s*handtype_\w+\s*=", re.IGNORECASE | re.MULTILINE)
STAMP_RE = re.compile(r"^# leveled-from: \S+ sha256:([0-9a-f]{64})\s*$")

UNLEVELED = "unleveled"   # no dlr-leveled file
CURRENT = "current"       # made from the dlr as it stands
STALE = "stale"           # made from some other dlr, or its dlr is gone


def dlr_path(scenario: str) -> str:
    return os.path.join(FOLDERS["dlr"], f"{scenario}.dlr")


def leveled_dlr_path(scenario: str) -> str:
    return os.path.join(FOLDERS["dlr_leveled"], f"{scenario}.dlr")


def pbn_path(scenario: str) -> str:
    return os.path.join(FOLDERS["pbn"], f"{scenario}.pbn")


def leveled_pbn_path(scenario: str) -> str:
    return os.path.join(FOLDERS["pbn_leveled"], f"{scenario}.pbn")


def declares_hand_types(dlr_file: str) -> bool:
    """True if the script names at least one HandType_ variable."""
    try:
        with open(dlr_file, encoding="utf-8") as f:
            return bool(HAND_TYPE_RE.search(f.read()))
    except OSError:
        return False


def source_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def stamp_line(scenario: str) -> str:
    """The first line of dlr-leveled/<name>.dlr, naming the dlr it came from."""
    return f"# leveled-from: dlr/{scenario}.dlr sha256:{source_hash(dlr_path(scenario))}"


def leveled_status(scenario: str) -> str:
    """UNLEVELED, CURRENT or STALE."""
    leveled = leveled_dlr_path(scenario)
    if not os.path.exists(leveled):
        return UNLEVELED
    with open(leveled, encoding="utf-8") as f:
        m = STAMP_RE.match(f.readline())
    source = dlr_path(scenario)
    if m and os.path.exists(source) and m.group(1) == source_hash(source):
        return CURRENT
    return STALE


def is_leveled(scenario: str) -> bool:
    return os.path.exists(leveled_dlr_path(scenario))


def leveled_or_original(scenario: str, kind: str) -> str:
    """The file a stage should read. kind is "dlr" or "pbn"."""
    leveled = is_leveled(scenario)
    if kind == "dlr":
        return leveled_dlr_path(scenario) if leveled else dlr_path(scenario)
    if kind == "pbn":
        return leveled_pbn_path(scenario) if leveled else pbn_path(scenario)
    raise ValueError(f"leveled_or_original: unknown kind {kind!r}")


def check_all() -> list:
    """Every leveled file that doesn't match its dlr, and every scenario that
    declares hand types but has no leveled file. One line each."""
    names = set()
    for key in ("dlr", "dlr_leveled"):
        if os.path.isdir(FOLDERS[key]):
            names |= {f[:-4] for f in os.listdir(FOLDERS[key]) if f.endswith(".dlr")}

    problems = []
    for name in sorted(names):
        status = leveled_status(name)
        if status == STALE and not os.path.exists(dlr_path(name)):
            problems.append(f"dlr-leveled/{name}.dlr has no dlr/{name}.dlr")
        elif status == STALE:
            problems.append(f"dlr-leveled/{name}.dlr was not made from the current "
                            f"dlr/{name}.dlr; run level")
        elif status == UNLEVELED and declares_hand_types(dlr_path(name)):
            problems.append(f"dlr/{name}.dlr declares hand types but has no "
                            f"dlr-leveled/{name}.dlr; run level")
    return problems


if __name__ == "__main__":
    if sys.argv[1:] != ["--check"]:
        print("Usage: python3 build-scripts-mac/utils/leveling.py --check")
        sys.exit(2)
    problems = check_all()
    for problem in problems:
        print(problem)
    print(f"{len(problems)} problem(s)" if problems else "Leveled scripts match their sources")
    sys.exit(1 if problems else 0)
