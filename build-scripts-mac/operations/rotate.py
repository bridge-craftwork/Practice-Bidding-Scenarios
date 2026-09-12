"""
Rotate operation: Create rotated PBN and LIN files for 4-player practice.
Uses bridge-wrangler rotate-deals and to-lin commands.
"""
import os
import shutil
import subprocess
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FOLDERS, MAC_TOOLS, PROJECT_ROOT
from utils.leveling import leveled_or_original


def run_rotate(scenario: str, verbose: bool = True) -> bool:
    """
    Create rotated PBN and LIN files for 4-player practice.

    pbn/{scenario}.pbn -> pbn-rotated-for-4-players/{scenario}.pbn
                       -> lin-rotated-for-4-players/{scenario}.lin

    Reads pbn-leveled/{scenario}.pbn instead when the scenario is leveled.

    Args:
        scenario: Scenario name (e.g., "Smolen")
        verbose: Whether to print progress

    Returns:
        True if successful, False otherwise
    """
    pbn_path = leveled_or_original(scenario, "pbn")
    if verbose:
        print(f"--------- bridge-wrangler: Creating rotated files for {scenario} "
              f"from {os.path.relpath(pbn_path, PROJECT_ROOT)}")

    # Check that PBN file exists
    if not os.path.exists(pbn_path):
        print(f"Error: rotate: PBN file not found: {pbn_path}")
        return False

    bridge_wrangler = MAC_TOOLS["bridge_wrangler"]

    # Step 1: Create rotated PBN (NESW rotation)
    # bridge-wrangler rotate-deals -i input.pbn -p NESW -o output.pbn
    dest_pbn = os.path.join(FOLDERS["pbn_rotated"], f"{scenario}.pbn")

    cmd1 = [
        bridge_wrangler, "rotate-deals",
        "-i", pbn_path,
        "-p", "NESW",
        "-o", dest_pbn
    ]

    if verbose:
        print(f"  Rotating PBN to NESW...")

    try:
        result = subprocess.run(cmd1, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: rotate: bridge-wrangler rotate-deals failed")
            if result.stderr:
                print(f"  {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"Error: rotate: bridge-wrangler rotate-deals: {e}")
        return False

    if verbose:
        print(f"  Created: {dest_pbn}")

    # Step 2: Create rotated LIN from the rotated PBN
    # bridge-wrangler to-lin -i input.pbn -o output.lin
    dest_lin = os.path.join(FOLDERS["lin_rotated"], f"{scenario}.lin")

    cmd2 = [
        bridge_wrangler, "to-lin",
        "-i", dest_pbn,
        "-o", dest_lin
    ]

    if verbose:
        print(f"  Converting to LIN...")

    try:
        result = subprocess.run(cmd2, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: rotate: bridge-wrangler to-lin failed")
            if result.stderr:
                print(f"  {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"Error: rotate: bridge-wrangler to-lin: {e}")
        return False

    if verbose:
        print(f"  Created: {dest_lin}")

    return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
    else:
        scenario = "Smolen"

    print(f"Testing rotate operation with scenario: {scenario}\n")
    success = run_rotate(scenario)
    print(f"\nResult: {'Success' if success else 'Failed'}")
