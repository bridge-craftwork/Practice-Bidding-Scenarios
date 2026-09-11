"""
Bidding sheet operation: Generate bidding sheets from filtered files.
Uses bridge-wrangler rotate-deals and to-pdf commands.
Limits boards to BIDDING_SHEET_MAX_BOARDS from config.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FOLDERS, MAC_TOOLS, BIDDING_SHEET_MAX_BOARDS


def _truncate_pbn(input_path: str, max_boards: int) -> str:
    """
    Create a temp file with only the first max_boards boards from a PBN file.
    Returns the temp file path. Caller is responsible for cleanup.

    Each board starts with [Event ...] preceded by a blank line.
    We track board boundaries at [Event lines and cut cleanly.
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    board_count = 0
    # Track where each board starts (the [Event line index)
    current_board_start = None

    for i, line in enumerate(lines):
        if re.match(r'^\[Event\s+"', line):
            board_count += 1
            if board_count > max_boards:
                # Cut just before this board's [Event line
                # Remove trailing blank lines
                end = i
                while end > 0 and lines[end - 1].strip() == '':
                    end -= 1
                output_lines = lines[:end]
                output_lines.append('')  # trailing newline
                break
    else:
        # Fewer boards than max — use entire file
        output_lines = lines

    fd, temp_path = tempfile.mkstemp(suffix='.pbn')
    os.close(fd)
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))

    return temp_path


def run_bidding_sheet(scenario: str, verbose: bool = True) -> bool:
    """
    Generate bidding sheets from filtered BBA file.

    bba-filtered/{scenario}.pbn -> bidding-sheets/{scenario}.pbn
                                -> bidding-sheets/{scenario} Bidding Sheets.pdf

    Only the first BIDDING_SHEET_MAX_BOARDS boards are included.

    Args:
        scenario: Scenario name (e.g., "Smolen")
        verbose: Whether to print progress

    Returns:
        True if successful, False otherwise
    """
    if verbose:
        print(f"--------- Bidding sheets for {scenario}")

    # Check that filtered file exists
    filtered_path = os.path.join(FOLDERS["bba_filtered"], f"{scenario}.pbn")
    if not os.path.exists(filtered_path):
        print(f"Error: biddingSheet: Filtered file not found: {filtered_path}")
        return False

    bridge_wrangler = MAC_TOOLS["bridge_wrangler"]

    # Count total boards in filtered file
    with open(filtered_path, 'r', encoding='utf-8') as f:
        total_boards = sum(1 for line in f if re.match(r'^\[Event\s+"', line))

    # Truncate to max boards if needed
    temp_path = None
    if total_boards > BIDDING_SHEET_MAX_BOARDS:
        temp_path = _truncate_pbn(filtered_path, BIDDING_SHEET_MAX_BOARDS)
        input_path = temp_path
        if verbose:
            print(f"  Using first {BIDDING_SHEET_MAX_BOARDS} of {total_boards} boards")
    else:
        input_path = filtered_path
        if verbose:
            print(f"  Using all {total_boards} boards")

    # Step 1: Rotate for N/S only
    # bridge-wrangler rotate-deals -i input.pbn -p NS -o output.pbn
    dest_pbn = os.path.join(FOLDERS["bidding_sheets"], f"{scenario}.pbn")

    if verbose:
        print(f"  Rotating for N/S...")

    cmd1 = [
        bridge_wrangler, "rotate-deals",
        "-i", input_path,
        "-p", "NS",
        "-o", dest_pbn
    ]

    try:
        result = subprocess.run(cmd1, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: biddingSheet: bridge-wrangler rotate-deals failed")
            if result.stderr:
                print(f"  {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"Error: biddingSheet: bridge-wrangler rotate-deals: {e}")
        return False
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    # Step 2: Generate PDF bidding sheets
    # bridge-wrangler to-pdf -i input.pbn -o output.pdf -l bidding-sheets
    if verbose:
        print(f"  Generating PDF bidding sheets...")

    pdf_path = os.path.join(FOLDERS["bidding_sheets"], f"{scenario} Bidding Sheets.pdf")

    cmd2 = [
        bridge_wrangler, "to-pdf",
        "-i", dest_pbn,
        "-o", pdf_path,
        "-l", "bidding-sheets",
        # The sheets carry their own banner; no page furniture from the PBN
        "--no-page-furniture",
    ]

    try:
        result = subprocess.run(cmd2, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: biddingSheet: bridge-wrangler to-pdf failed")
            if result.stderr:
                print(f"  {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"Error: biddingSheet: bridge-wrangler to-pdf: {e}")
        return False

    if verbose:
        print(f"  Created: {pdf_path}")

    # Clean up leftover .html file from old Windows build process
    html_path = os.path.join(FOLDERS["bidding_sheets"], f"{scenario} Bidding Sheets.html")
    if os.path.exists(html_path):
        os.remove(html_path)
        if verbose:
            print(f"  Removed leftover: {html_path}")

    return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
    else:
        scenario = "Smolen"

    print(f"Testing bidding sheet operation with scenario: {scenario}\n")
    success = run_bidding_sheet(scenario)
    print(f"\nResult: {'Success' if success else 'Failed'}")
