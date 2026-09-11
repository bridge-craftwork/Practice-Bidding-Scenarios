"""
Level operation (issue #322): generate the leveled copy of a scenario that
declares hand types.

    dlr/{scenario}.dlr -> dlr-leveled/{scenario}.dlr

dealer3 measures how often each HandType_ comes up, and writes a copy whose
condition keeps each type at the rate that evens out the mix (see
docs/leveling-guide.md in the dealer3 repo). From then on the leveled file
wins downstream; see utils/leveling.py.

- A scenario with no HandType_ variables is skipped, and any leveled files it
  left behind are removed, so they can't win over the script it has now.
- A leveled file already made from this dlr is left alone.
- No -p: dealer3 sizes the measurement itself, dealing until the rarest type
  has been seen 2,000 times. The seed is fixed and the clock set well past
  what that takes, so a rebuild is byte-identical.
- `# level-budget: N` in the .btn caps the cost at N deals dealt per deal kept,
  for scenarios too expensive to level exactly (e.g. Bergen_Raises).
- dealer3 fills in the {{level-mix:...}} tokens in the chat.

Then it checks the result: it deals 10,000 from the leveled file and compares
each type's share with the mix dealer3 said the keeps would deliver.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FOLDERS, MAC_TOOLS, PROJECT_ROOT, DEALER_GENERATE, LEVEL_SEED, LEVEL_TIMEOUT
from utils.leveling import (CURRENT, declares_hand_types, dlr_path, leveled_dlr_path,
                            leveled_pbn_path, leveled_status, stamp_line)
from utils.properties import get_btn_property

VERIFY_DEALS = 10000
# 10,000 deals land a share within about 1 point of its mix; allow 2 before
# calling the leveling wrong
VERIFY_TOLERANCE = 0.02

# A row of the summary dealer3 prints to stderr:
#   type     natural    target       mix     keep      seen
#   12_14    0.58301   0.20000   0.20000   0.0217     92304
MIX_ROW = re.compile(r"^\s+(\S+)\s+[\d.]+\s+[\d.]+\s+([\d.]+)\s+[\d.]+\s+\d+\s*$")


def _rel(path: str) -> str:
    return os.path.relpath(path, PROJECT_ROOT)


def _remove(path: str, verbose: bool):
    if os.path.exists(path):
        os.remove(path)
        if verbose:
            print(f"  Removed: {_rel(path)}")


def run_level(scenario: str, verbose: bool = True) -> bool:
    """
    Write dlr-leveled/{scenario}.dlr from dlr/{scenario}.dlr.

    Args:
        scenario: Scenario name (e.g., "NT_Ladder")
        verbose: Whether to print progress

    Returns:
        True if successful (including when there is nothing to level)
    """
    if verbose:
        print(f"--------- dealer3: Leveling dlr/{scenario}.dlr")

    source = dlr_path(scenario)
    if not os.path.exists(source):
        print(f"Error: level: DLR file not found: {source}")
        return False

    leveled = leveled_dlr_path(scenario)
    if not declares_hand_types(source):
        if verbose:
            print(f"  No HandType_ variables; {scenario} is not leveled")
        _remove(leveled, verbose)
        _remove(leveled_pbn_path(scenario), verbose)
        return True

    if leveled_status(scenario) == CURRENT:
        # Touch it, so a regenerated but unchanged dlr doesn't make it look stale
        os.utime(leveled)
        if verbose:
            print(f"  Up to date: {_rel(leveled)}")
        return True

    cmd = [MAC_TOOLS["dealer"], source, "-q",
           "-s", str(LEVEL_SEED),
           "--level-timeout", str(LEVEL_TIMEOUT)]
    budget = get_btn_property(scenario, "level-budget")
    if budget:
        cmd += ["--level-budget", budget]
    if verbose:
        print(f"  [Local] {' '.join(cmd)} --write-leveled {_rel(leveled)}")

    # Write beside the target and move it in, so a failed run leaves no half file
    os.makedirs(FOLDERS["dlr_leveled"], exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".", suffix=".dlr", dir=FOLDERS["dlr_leveled"])
    os.close(fd)
    try:
        result = subprocess.run(cmd + ["--write-leveled", tmp], capture_output=True,
                                text=True, timeout=LEVEL_TIMEOUT + 60)
        report = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            print(f"Error: level: dealer3 failed with exit code {result.returncode}")
            if report:
                print(report)
            return False
        with open(tmp, encoding="utf-8") as f:
            body = f.read()
        with open(leveled, "w", encoding="utf-8") as f:
            f.write(stamp_line(scenario) + "\n" + body)
    except subprocess.TimeoutExpired:
        print(f"Error: level: dealer3 still running after {LEVEL_TIMEOUT + 60} seconds")
        return False
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    if verbose:
        for line in report.splitlines():
            # dealer3's "wrote <file>" names the temporary file
            if not line.startswith("wrote "):
                print(f"  {line}")
        print(f"  Created: {_rel(leveled)}")

    # dealer3 names the switch when the clock, not the sightings, ended the
    # measuring. The file is still usable, but a rebuild won't reproduce it.
    if "--level-timeout" in report:
        print(f"  Warning: measuring {scenario} stopped on the clock, so a rebuild won't be "
              f"byte-identical. Raise LEVEL_TIMEOUT in config.py, or set # level-budget.")

    return _verify(leveled, report, verbose)


def _verify(leveled: str, report: str, verbose: bool) -> bool:
    """Deal VERIFY_DEALS from the leveled file and compare each hand type's
    share with the mix in dealer3's report."""
    mix = {}
    for line in report.splitlines():
        m = MIX_ROW.match(line)
        if m:
            mix[m.group(1)] = float(m.group(2))
    if not mix:
        print("Error: level: found no mix table in dealer3's report")
        return False

    cmd = [MAC_TOOLS["dealer"], leveled, "-q",
           "-s", str(LEVEL_SEED),
           "-g", str(DEALER_GENERATE),
           "-p", str(VERIFY_DEALS),
           "--stats-json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        shares = {t["name"]: t["share"] for t in json.loads(result.stdout)["hand_types"]}
    except subprocess.TimeoutExpired:
        print(f"Error: level: checking {_rel(leveled)} took over 600 seconds")
        return False
    except (ValueError, KeyError, TypeError):
        print(f"Error: level: couldn't read the check run's --stats-json (exit {result.returncode})")
        if result.stderr:
            print(result.stderr.strip())
        return False

    if verbose:
        print(f"  Check: {VERIFY_DEALS} deals from {_rel(leveled)}")
    worst = 0.0
    for name, want in mix.items():
        got = shares.get(name, 0.0)
        worst = max(worst, abs(got - want))
        if verbose:
            print(f"    {name:16} mix {want:6.1%}   dealt {got:6.1%}")

    if worst > VERIFY_TOLERANCE:
        print(f"Error: level: a hand type was dealt {worst:.1%} away from its mix "
              f"(allowed {VERIFY_TOLERANCE:.0%}); look at the keeps in {_rel(leveled)}")
        return False
    return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
    else:
        scenario = "NT_Ladder"

    print(f"Testing level operation with scenario: {scenario}\n")
    success = run_level(scenario)
    print(f"\nResult: {'Success' if success else 'Failed'}")
