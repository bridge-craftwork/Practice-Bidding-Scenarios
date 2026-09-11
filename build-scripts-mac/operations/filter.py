"""
Filter operation: Filter BBA file based on auction patterns.
Uses bridge-wrangler filter command.
"""
import os
import subprocess
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FOLDERS, MAC_TOOLS
from utils.properties import get_auction_filter


def normalize_filter_for_bridge_wrangler(filter_expr: str) -> str:
    """
    Normalize filter expression for bridge-wrangler.

    - Adds (?s) flag to enable dotall mode (. matches newlines)
    - Converts escaped \\n sequences to actual newlines
    - Converts \\r?\\n to just newlines (bridge-wrangler handles line endings)
    - Converts single spaces to \\s+ to match variable whitespace in PBN files
    """
    result = filter_expr

    # Convert escaped newlines to actual newlines
    # Handle both \\n and \n patterns
    result = result.replace("\\r?\\n", "\n")
    result = result.replace("\\n", "\n")

    # Replace single spaces with \s+ to match variable whitespace in PBN files
    # (PBN auctions have multiple spaces between bids like "1D    Pass  1S")
    result = result.replace(" ", r"\s+")

    # Add (?s) flag at the beginning for dotall mode
    if not result.startswith("(?s)"):
        result = "(?s)" + result

    return result


def bridge_wrangler_filter(input_path: str, filter_expr: str, output_filtered: str,
                           output_inverse: str, verbose: bool = True) -> bool:
    """
    Split a PBN file by an auction-filter expression (as written in the .dlr)
    into matched and not-matched PBN files, with a PDF beside each.

    Shared by the filter operation (bba/) and the gibReport operation (GIB/).

    Returns:
        True if the filter ran; a PDF failure only warns
    """
    filter_expr = normalize_filter_for_bridge_wrangler(filter_expr)
    bridge_wrangler = MAC_TOOLS["bridge_wrangler"]
    for path in (output_filtered, output_inverse):
        os.makedirs(os.path.dirname(path), exist_ok=True)

    # Run filter with both matched and not-matched outputs
    # bridge-wrangler filter -i input.pbn -p "pattern" -m matched.pbn -n not-matched.pbn
    cmd = [
        bridge_wrangler, "filter",
        "-i", input_path,
        "-p", filter_expr,
        "-m", output_filtered,
        "-n", output_inverse
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error: bridge-wrangler filter failed")
            if result.stderr:
                print(result.stderr)
            return False
    except Exception as e:
        print(f"Error running bridge-wrangler filter: {e}")
        return False

    if verbose:
        print(f"  Created: {output_filtered}")
        print(f"  Created: {output_inverse}")

    # Generate PDFs for both filtered and filtered-out outputs
    for pbn_file in (output_filtered, output_inverse):
        output_pdf = os.path.splitext(pbn_file)[0] + ".pdf"
        # bridge-wrangler will not render an empty file, which would leave an
        # earlier run's PDF behind, showing boards that are no longer there.
        with open(pbn_file, encoding="utf-8", errors="replace") as f:
            if "[Board " not in f.read():
                if os.path.exists(output_pdf):
                    os.remove(output_pdf)
                continue
        pdf_cmd = [
            bridge_wrangler, "to-pdf",
            "-i", pbn_file,
            "-o", output_pdf
        ]

        try:
            result = subprocess.run(pdf_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  Warning: PDF generation failed for {pbn_file}")
                if result.stderr:
                    print(f"    {result.stderr}")
                # Don't fail the whole operation for PDF generation failure
            elif verbose:
                print(f"  Created: {output_pdf}")
        except Exception as e:
            print(f"  Warning: PDF generation failed: {e}")

    return True


def run_filter(scenario: str, verbose: bool = True) -> bool:
    """
    Filter BBA file based on auction patterns.

    bba/{scenario}.pbn -> bba-filtered/{scenario}.pbn
                       -> bba-filtered-out/{scenario}.pbn

    Args:
        scenario: Scenario name (e.g., "Smolen")
        verbose: Whether to print progress

    Returns:
        True if successful, False otherwise
    """
    if verbose:
        print(f"--------- bridge-wrangler filter: Filtering bba/{scenario}.pbn")

    # Check that BBA file exists
    bba_path = os.path.join(FOLDERS["bba"], f"{scenario}.pbn")
    if not os.path.exists(bba_path):
        print(f"Error: BBA file not found: {bba_path}")
        return False

    # Get auction filter from DLR properties
    filter_expr = get_auction_filter(scenario)

    if not filter_expr:
        print(f"  {scenario} doesn't have a filter expression, skipping")
        return True  # Not an error, just nothing to do

    if verbose:
        print(f"  Filter: {filter_expr}")

    output_filtered = os.path.join(FOLDERS["bba_filtered"], f"{scenario}.pbn")
    output_inverse = os.path.join(FOLDERS["bba_filtered_out"], f"{scenario}.pbn")
    return bridge_wrangler_filter(bba_path, filter_expr, output_filtered, output_inverse, verbose)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
    else:
        scenario = "Smolen"

    print(f"Testing filter operation with scenario: {scenario}\n")
    success = run_filter(scenario)
    print(f"\nResult: {'Success' if success else 'Failed'}")
