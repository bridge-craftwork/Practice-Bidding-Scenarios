"""
Solve operation: add a double-dummy table to every deal (issue #341).
Uses bridge-wrangler analyze, which writes the PBN 2.1 [OptimumResultTable]
section and leaves every other byte of the file as it was.

The table is written into the deal file itself, so everything downstream sees
it: rotate carries it around the table with the hands, and bba-cli keeps it
beside the auction it generates (BBA-Tools#26). A table depends only on the
deal, so it stays valid until pbn deals new hands -- which rewrites the file
and takes the tables with it, making a re-solve necessary and obvious.
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
TABLE_RE = re.compile(r'^\[OptimumResultTable "', re.MULTILINE)


def count_deals_and_tables(pbn_path: str) -> tuple:
    """Return (deals, tables) counted in a PBN file."""
    with open(pbn_path, encoding="utf-8", errors="replace") as f:
        content = f.read()
    return len(DEAL_RE.findall(content)), len(TABLE_RE.findall(content))


def run_solve(scenario: str, verbose: bool = True) -> bool:
    """
    Add a double-dummy table to every deal of a scenario, in place.

    pbn/{scenario}.pbn -> pbn/{scenario}.pbn, with [OptimumResultTable] added

    Reads and writes pbn-leveled/{scenario}.pbn instead when the scenario is
    leveled, since that is the file the rest of the pipeline reads.

    A file whose every deal already carries a table is left alone, so re-running
    the pipeline does not pay for the solving again.

    Args:
        scenario: Scenario name (e.g., "Smolen")
        verbose: Whether to print progress

    Returns:
        True if successful, False otherwise
    """
    pbn_path = leveled_or_original(scenario, "pbn")
    if verbose:
        print(f"--------- bridge-wrangler analyze: Solving "
              f"{os.path.relpath(pbn_path, PROJECT_ROOT)}")

    if not os.path.exists(pbn_path):
        print(f"Error: solve: PBN file not found: {pbn_path}")
        return False

    deals, tables = count_deals_and_tables(pbn_path)
    if deals == 0:
        print(f"Error: solve: no deals in {pbn_path}")
        return False

    if tables >= deals:
        if verbose:
            print(f"  Up to date: {tables} tables for {deals} deals")
        return True

    if verbose and tables:
        print(f"  {tables} of {deals} deals already solved; solving the file again")

    bridge_wrangler = MAC_TOOLS["bridge_wrangler"]

    # Solve into a temporary file and move it into place, so an interrupted run
    # cannot leave a half-written deal file behind.
    fd, temp_path = tempfile.mkstemp(suffix=".pbn", dir=os.path.dirname(pbn_path))
    os.close(fd)

    cmd = [bridge_wrangler, "analyze", "-i", pbn_path, "-o", temp_path]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: solve: bridge-wrangler analyze failed")
            if result.stderr:
                print(f"  {result.stderr.strip()}")
            return False

        solved_deals, solved_tables = count_deals_and_tables(temp_path)
        if solved_tables < solved_deals:
            print(f"Error: solve: only {solved_tables} of {solved_deals} deals "
                  f"were solved; leaving {os.path.basename(pbn_path)} alone")
            return False

        shutil.move(temp_path, pbn_path)
    except Exception as e:
        print(f"Error: solve: bridge-wrangler analyze: {e}")
        return False
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    if verbose:
        print(f"  Solved {deals} deals")

    return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
    else:
        scenario = "Smolen"

    print(f"Testing solve operation with scenario: {scenario}\n")
    success = run_solve(scenario)
    print(f"\nResult: {'Success' if success else 'Failed'}")
