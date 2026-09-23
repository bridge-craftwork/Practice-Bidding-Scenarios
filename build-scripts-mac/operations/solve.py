"""
Solve operation: add double-dummy results to every deal (issue #341).

Uses the bridge-solver CLI, which owns double dummy: it reads and writes PBN
through the same byte-preserving document bridge-wrangler uses, solves across
every core, and gives identical bytes at any thread count. bridge-wrangler had
an `analyze` until its v0.11.0, solving one board at a time on one thread; it
was removed rather than kept as a slower second implementation.

Each board gains four tags: [OptimumResultTable] and [DoubleDummyTricks], which
are the same table in two encodings, and [OptimumScore] and [ParContract], the
par computed from that table at no extra solving cost.

The tags are written into the deal file itself, so everything downstream sees
them: rotate turns all four with the hands (bridge-wrangler#14), and bba-cli
keeps them beside the auction it generates (BBA-Tools#26). They depend only on
the deal, so they stay valid until pbn deals new hands -- which rewrites the
file without them, making the next solve necessary and obvious.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import MAC_TOOLS, PROJECT_ROOT
from utils.leveling import leveled_or_original

DEAL_RE = re.compile(r'^\[Deal "', re.MULTILINE)
# The tag bridge-solver itself treats as "this board is analysed", and the one
# the par tags come with, so counting it answers both questions at once.
SOLVED_RE = re.compile(r'^\[DoubleDummyTricks "', re.MULTILINE)

# Worker threads. Unset means every core, which is what the tool defaults to.
SOLVE_THREADS = os.environ.get("PBS_SOLVE_THREADS")


def count_deals_and_solved(pbn_path: str) -> tuple:
    """Return (deals, solved boards) counted in a PBN file."""
    with open(pbn_path, encoding="utf-8", errors="replace") as f:
        content = f.read()
    return len(DEAL_RE.findall(content)), len(SOLVED_RE.findall(content))


def run_solve(scenario: str, verbose: bool = True) -> bool:
    """
    Add double-dummy results to every deal of a scenario, in place.

    pbn/{scenario}.pbn -> pbn/{scenario}.pbn, with the four DD tags added

    Reads and writes pbn-leveled/{scenario}.pbn instead when the scenario is
    leveled, since that is the file the rest of the pipeline reads.

    A file whose every deal is already solved is left alone, and within a file
    bridge-solver leaves an analysed board as it found it, so neither the
    pipeline nor the tool pays for the same deal twice.

    Args:
        scenario: Scenario name (e.g., "Smolen")
        verbose: Whether to print progress

    Returns:
        True if successful, False otherwise
    """
    pbn_path = leveled_or_original(scenario, "pbn")
    if verbose:
        print(f"--------- bridge-solver: Solving "
              f"{os.path.relpath(pbn_path, PROJECT_ROOT)}")

    if not os.path.exists(pbn_path):
        print(f"Error: solve: PBN file not found: {pbn_path}")
        return False

    deals, solved = count_deals_and_solved(pbn_path)
    if deals == 0:
        print(f"Error: solve: no deals in {pbn_path}")
        return False

    if solved >= deals:
        if verbose:
            print(f"  Up to date: all {deals} deals solved")
        return True

    if verbose and solved:
        print(f"  {solved} of {deals} deals already solved; solving the rest")

    bridge_solver = MAC_TOOLS["bridge_solver"]
    if not os.path.exists(bridge_solver):
        print(f"Error: solve: bridge-solver not found at: {bridge_solver}")
        print(f"  Build and install it with "
              f"bridge-craftwork-platform/mac/scripts/rebuild-bridge-tools.sh")
        return False

    # Solve into a temporary file and move it into place, so an interrupted run
    # cannot leave a half-written deal file behind. It is written beside its
    # deal file, so the move is a rename rather than a copy, and named with a
    # leading dot so an interrupted run leaves nothing that looks like a
    # scenario's PBN.
    fd, temp_path = tempfile.mkstemp(prefix=f".{scenario}-solve-", suffix=".pbn",
                                     dir=os.path.dirname(pbn_path))
    os.close(fd)

    cmd = [bridge_solver, "-i", pbn_path, "-o", temp_path]
    if SOLVE_THREADS:
        cmd += ["-j", SOLVE_THREADS]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: solve: bridge-solver failed")
            if result.stderr:
                print(f"  {result.stderr.strip()}")
            return False

        solved_deals, now_solved = count_deals_and_solved(temp_path)
        if now_solved < solved_deals:
            print(f"Error: solve: only {now_solved} of {solved_deals} deals "
                  f"were solved; leaving {os.path.basename(pbn_path)} alone")
            return False

        shutil.move(temp_path, pbn_path)
    except Exception as e:
        print(f"Error: solve: bridge-solver: {e}")
        return False
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    if verbose:
        print(f"  Solved {deals - solved} deals")

    return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
    else:
        scenario = "Smolen"

    print(f"Testing solve operation with scenario: {scenario}\n")
    success = run_solve(scenario)
    print(f"\nResult: {'Success' if success else 'Failed'}")
