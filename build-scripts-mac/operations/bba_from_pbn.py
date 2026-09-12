"""
BBA operation: Generate BBA file from PBN using bba-cli natively on Mac.
Then run oneSummary.py locally to create summary.

After BBA completes, restores header comments and fixes Event tags
that BBA strips or overwrites.
"""
import os
import re
import subprocess
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FOLDERS, MAC_TOOLS, PROJECT_ROOT
from utils.properties import get_convention_card_ns, get_convention_card_ew
from operations.title import get_title_from_pbs
from utils.leveling import leveled_or_original

# Timeout for BBA completion
BBA_TIMEOUT = 300


def fix_event_tags(scenario: str, file_path: str, verbose: bool = True) -> bool:
    """
    Fix title metadata in a PBN file with the correct title from PBS.

    BBA overwrites Event tags with Windows paths like "P:\\bba\\scenario".
    This function:
    - Adds/updates %HRTitleEvent header comment (used by pbn-to-pdf)
    - Replaces all [Event "..."] tags with the proper title

    Args:
        scenario: Scenario name
        file_path: Path to the PBN file to fix
        verbose: Whether to print progress

    Returns:
        True if successful, False otherwise
    """
    title = get_title_from_pbs(scenario)

    try:
        with open(file_path, "r") as f:
            lines = f.readlines()

        # Update or add %HRTitleEvent in header
        hr_title_line = f'%HRTitleEvent "{title}"\n'
        hr_pattern = re.compile(r'^%HRTitleEvent\s')
        found_hr_title = False
        insert_pos = 0

        for i, line in enumerate(lines):
            if hr_pattern.match(line):
                lines[i] = hr_title_line
                found_hr_title = True
                break
            elif line.startswith('%'):
                insert_pos = i + 1
            elif line.startswith('['):
                break

        if not found_hr_title:
            lines.insert(insert_pos, hr_title_line)

        content = ''.join(lines)

        # Replace all [Event "..."] tags with the correct title
        pattern = r'\[Event "[^"]*"\]'
        replacement = f'[Event "{title}"]'
        updated_content = re.sub(pattern, replacement, content)

        # Remove all [Date "..."] lines to avoid spurious diffs
        updated_content = re.sub(r'\[Date "[^"]*"\]\n?', '', updated_content)

        with open(file_path, "w") as f:
            f.write(updated_content)

        if verbose:
            count = len(re.findall(pattern, content))
            print(f"  Fixed {count} Event tags with title: {title}")

        return True

    except Exception as e:
        print(f"Error fixing Event tags: {e}")
        return False


def run_bba(scenario: str, verbose: bool = True, output_dir: str = None) -> bool:
    """
    Generate BBA file from PBN file using bba-cli natively on Mac.

    pbn/{scenario}.pbn -> bba/{scenario}.pbn (or output_dir/{scenario}.pbn)

    Uses the Rust bba-cli built from the BBA-Tools repo, which links the same
    NativeAOT libEPBot.dylib that bba-server runs on the droplet. This keeps
    locally-generated bba-filtered output in sync with what users see from
    the production server.

    Args:
        scenario: Scenario name (e.g., "Smolen")
        verbose: Whether to print progress
        output_dir: Optional override for output directory (for comparison testing)

    Returns:
        True if successful, False otherwise
    """
    # pbn-leveled/ when the scenario is leveled (issue #322)
    pbn_path = leveled_or_original(scenario, "pbn")
    if verbose:
        print(f"--------- bba-cli: Creating bba/{scenario}.pbn from "
              f"{os.path.relpath(pbn_path, PROJECT_ROOT)}")

    bba_cli = MAC_TOOLS.get("bba_cli")
    if not bba_cli or not os.path.exists(bba_cli):
        print(f"Error: bba-cli not found at: {bba_cli}")
        print(f"  Install from https://github.com/Rick-Wilson/BBA-Tools/releases (.dmg)")
        return False

    if not os.path.exists(pbn_path):
        print(f"Error: PBN file not found: {pbn_path}")
        return False

    cc1 = get_convention_card_ns(scenario)
    cc2 = get_convention_card_ew(scenario)

    if verbose:
        print(f"  Convention cards: {cc1} vs {cc2}")

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        bba_output = os.path.join(output_dir, f"{scenario}.pbn")
    else:
        bba_output = os.path.join(FOLDERS["bba"], f"{scenario}.pbn")

    if os.path.exists(bba_output):
        os.remove(bba_output)

    cc1_file = os.path.join(FOLDERS["bbsa"], f"{cc1}.bbsa")
    cc2_file = os.path.join(FOLDERS["bbsa"], f"{cc2}.bbsa")

    cmd = [
        bba_cli,
        "--input", pbn_path,
        "--output", bba_output,
        "--ns-conventions", cc1_file,
        "--ew-conventions", cc2_file,
        "--event", scenario.replace("_", " "),
        # Emit [Result], [Score], [Scoring], and the BBA board-id hash —
        # restores the per-board fields the original BBA.exe output had
        # and that David's classroom UI expects. Costs ~0.22 ms per board.
        "--single-dummy",
    ]

    if verbose:
        print(f"  Running: {' '.join(cmd)}")

    try:
        start_time = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=BBA_TIMEOUT,
        )
        elapsed = time.time() - start_time

        if result.returncode != 0:
            print(f"Error: bba-cli failed with exit code {result.returncode}")
            if result.stderr:
                print(f"  {result.stderr}")
            return False

        if verbose:
            print(f"  BBA completed successfully in {int(elapsed)}s")
            if result.stdout:
                print(f"  {result.stdout.strip()}")

    except subprocess.TimeoutExpired:
        print(f"Error: bba-cli timed out after {BBA_TIMEOUT} seconds")
        return False
    except Exception as e:
        print(f"Error running bba-cli: {e}")
        return False

    if not os.path.exists(bba_output):
        print(f"Error: BBA output was not created: {bba_output}")
        return False

    fix_event_tags(scenario, bba_output, verbose)

    if not output_dir:
        return run_summary(scenario, verbose)

    return True


def run_summary(scenario: str, verbose: bool = True) -> bool:
    """
    Run oneSummary.py to create the summary file.
    """
    if verbose:
        print(f"--------- oneSummary.py: Creating bba-summary/{scenario}.txt")

    py_dir = FOLDERS["py"]
    summary_script = os.path.join(py_dir, "oneSummary.py")

    if not os.path.exists(summary_script):
        print(f"Error: oneSummary.py not found: {summary_script}")
        return False

    try:
        result = subprocess.run(
            [MAC_TOOLS["python"], summary_script, "--scenario", scenario],
            cwd=py_dir,
            capture_output=True,
            text=True,
            check=True,
        )

        if verbose and result.stdout:
            print(result.stdout)

    except subprocess.CalledProcessError as e:
        print(f"Error running oneSummary.py: {e}")
        if e.stderr:
            print(e.stderr)
        print("  (continuing despite summary error)")

    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run BBA analysis on a scenario")
    parser.add_argument("scenario", nargs="?", default="Smolen", help="Scenario name")
    parser.add_argument("--compare", action="store_true",
                        help="Run BBA to a temp directory and diff against existing bba/ output")
    args = parser.parse_args()

    scenario = args.scenario

    if args.compare:
        compare_dir = os.path.join(PROJECT_ROOT, "bba-mac-test")
        print(f"Running bba-cli on {scenario} (output to bba-mac-test/)...\n")
        success = run_bba(scenario, verbose=True, output_dir=compare_dir)
        if success:
            new_file = os.path.join(compare_dir, f"{scenario}.pbn")
            existing_file = os.path.join(FOLDERS["bba"], f"{scenario}.pbn")
            if os.path.exists(existing_file):
                print(f"\nComparing outputs...")
                print(f"  Existing: {existing_file}")
                print(f"  New:      {new_file}")
                pbn_diff = os.path.join(PROJECT_ROOT, "build-scripts-mac", "pbn-diff.py")
                if os.path.exists(pbn_diff):
                    result = subprocess.run(
                        [MAC_TOOLS["python"], pbn_diff, existing_file, new_file],
                        capture_output=True, text=True)
                    print(result.stdout)
                    if result.stderr:
                        print(result.stderr)
                else:
                    for label, path in [("Existing", existing_file), ("New", new_file)]:
                        with open(path) as f:
                            content = f.read()
                        boards = content.count('[Board "')
                        auctions = content.count('[Auction "')
                        print(f"  {label}: {boards} boards, {auctions} auctions")
            else:
                print(f"\n  No existing output at {existing_file} to compare against.")
        print(f"\nResult: {'Success' if success else 'Failed'}")
    else:
        print(f"Testing BBA operation with scenario: {scenario}\n")
        success = run_bba(scenario)
        print(f"\nResult: {'Success' if success else 'Failed'}")
