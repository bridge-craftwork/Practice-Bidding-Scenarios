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

# The stamp a solved file carries in its header, as `% solved: 500/500 deals`.
# Solving writes its results into the deal file rather than a file of its own,
# so a solved file and an unsolved one are the same path: nothing about the file
# itself says which it is. The stamp says it in the first line, the way
# dlr-leveled/<name>.dlr records the .dlr it was made from, so a reader -- the
# VS Code panel, a person, a future check -- can tell without counting tags
# through a quarter of a megabyte. Dealing new hands rewrites the file without
# it, which is exactly when it should stop claiming to be solved.
STAMP_RE = re.compile(r'^% solved: .*$\n?', re.MULTILINE)

# Worker threads. Unset means every core, which is what the tool defaults to.
SOLVE_THREADS = os.environ.get("PBS_SOLVE_THREADS")


def count_deals_and_solved(pbn_path: str) -> tuple:
    """Return (deals, solved boards) counted in a PBN file."""
    with open(pbn_path, encoding="utf-8", errors="replace") as f:
        content = f.read()
    return len(DEAL_RE.findall(content)), len(SOLVED_RE.findall(content))


def read_stamp(pbn_path: str):
    """The (deals, solved) a file's stamp claims, or None if it carries none.

    Reads the header rather than the file: the stamp is in the first few lines,
    and this is the question asked most often and answered least expensively.
    """
    with open(pbn_path, encoding="utf-8", errors="replace") as f:
        head = f.read(4096)

    m = re.search(r'^% solved: (\d+)/(\d+) deals', head, re.MULTILINE)
    if not m:
        return None
    return int(m.group(2)), int(m.group(1))


def write_stamp(pbn_path: str, deals: int, solved: int, keep_mtime: bool = False):
    """Record in the file's header how much of it is solved.

    The stamp goes above the first tag, among the `%` lines PBN keeps for
    exactly this (2.1 section 2.3), and replaces any earlier one rather than
    stacking up. Every tool in this pipeline preserves those lines.

    keep_mtime restores the file's timestamp afterwards, for stamping a file
    that was already solved. The deals and their tables are untouched there, so
    letting the clock move would tell rotate, bba and everything after them to
    rebuild against content that has not changed.
    """
    before = os.stat(pbn_path)

    with open(pbn_path, encoding="utf-8", errors="replace") as f:
        content = f.read()

    content = STAMP_RE.sub("", content)
    stamp = f"% solved: {solved}/{deals} deals, bridge-solver\n"

    # After the header's other % lines, and always before the first tag.
    first_tag = content.find("[")
    head, rest = content[:first_tag], content[first_tag:]
    if head and not head.endswith("\n"):
        head += "\n"

    with open(pbn_path, "w", encoding="utf-8") as f:
        f.write(head + stamp + rest)

    if keep_mtime:
        os.utime(pbn_path, (before.st_atime, before.st_mtime))


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

    # The stamp answers this without reading the whole file; a file solved
    # before the stamp existed, or by bridge-solver directly, is counted
    # instead and then stamped, so it need not be solved again to gain one.
    stamped = read_stamp(pbn_path)
    deals, solved = stamped if stamped else count_deals_and_solved(pbn_path)
    if deals == 0:
        print(f"Error: solve: no deals in {pbn_path}")
        return False

    if solved >= deals:
        if not stamped:
            write_stamp(pbn_path, deals, solved, keep_mtime=True)
            if verbose:
                print(f"  Already solved; stamped {deals} deals")
            return True
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

        write_stamp(temp_path, solved_deals, now_solved)
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
