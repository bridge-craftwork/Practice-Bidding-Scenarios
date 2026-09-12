"""
PBN operation: Generate PBN file from DLR using dealer (Mac or Windows).
Then run oneComment.py locally to add comments.
Finally, set correct Event tags using title from PBS file.

A leveled scenario (issue #322) gets two PBN files: pbn/{scenario}.pbn from
the natural mix, which is how you see what leveling changed, and
pbn-leveled/{scenario}.pbn from dlr-leveled/, which rotate and bba read.
"""
import os
import re
import subprocess
import sys
import threading

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FOLDERS, MAC_TOOLS, WINDOWS_TOOLS, PROJECT_ROOT, dealer_seed, DEALER_GENERATE, DEALER_PRODUCE, DEALER_PLATFORM
from ssh_runner import run_windows_command, mac_to_windows_path
from operations.title import run_title
from utils.leveling import STALE, UNLEVELED, leveled_dlr_path, leveled_pbn_path, leveled_status

# ANSI color codes
RED = '\033[91m'
RESET = '\033[0m'


def print_error(msg: str):
    """Print error message in red."""
    print(f"{RED}{msg}{RESET}")


def _validate_pbn_output(pbn_path: str, error_pattern: re.Pattern, verbose: bool = True) -> bool:
    """
    Validate that the PBN file contains valid output and not dealer errors.

    Mac dealer writes errors to stdout (into the pbn file) rather than stderr.
    This function checks the beginning of the file for error patterns.

    Returns:
        True if valid PBN, False if errors detected
    """
    if not os.path.exists(pbn_path):
        print_error(f"Error: PBN file was not created: {pbn_path}")
        return False

    try:
        with open(pbn_path, 'r') as f:
            # Read first few lines to check for errors
            first_lines = []
            for i, line in enumerate(f):
                first_lines.append(line)
                if i >= 10:  # Check first 10 lines
                    break

        if not first_lines:
            print_error(f"Error: PBN file is empty: {pbn_path}")
            os.remove(pbn_path)
            return False

        # Check for dealer error patterns in the output
        for line in first_lines:
            stripped = line.strip()
            if error_pattern.match(stripped) or \
               'unknown variable' in stripped.lower() or \
               'syntax error' in stripped.lower() or \
               'redefined variable' in stripped.lower() or \
               'parse error' in stripped.lower():
                print_error(f"Dealer error detected in output: {stripped}")
                os.remove(pbn_path)
                return False

        # Check that file starts with valid PBN header
        first_line = first_lines[0].strip()
        if not first_line.startswith('[Event'):
            print_error(f"Error: PBN file does not start with valid header: {first_line[:50]}")
            os.remove(pbn_path)
            return False

        return True

    except Exception as e:
        print_error(f"Error validating PBN file: {e}")
        if os.path.exists(pbn_path):
            os.remove(pbn_path)
        return False


def run_pbn(scenario: str, verbose: bool = True) -> bool:
    """
    Generate PBN file from DLR file using dealer.

    dlr/{scenario}.dlr -> pbn/{scenario}.pbn
    dlr-leveled/{scenario}.dlr -> pbn-leveled/{scenario}.pbn, when leveled

    Args:
        scenario: Scenario name (e.g., "Smolen")
        verbose: Whether to print progress

    Returns:
        True if successful, False otherwise
    """
    # Check that DLR file exists
    dlr_path = os.path.join(FOLDERS["dlr"], f"{scenario}.dlr")
    if not os.path.exists(dlr_path):
        print_error(f"Error: DLR file not found: {dlr_path}")
        return False

    pbn_path = os.path.join(FOLDERS["pbn"], f"{scenario}.pbn")
    if not _make_pbn(scenario, dlr_path, pbn_path, verbose):
        return False

    status = leveled_status(scenario)
    if status == UNLEVELED:
        return True
    if status == STALE:
        print_error(f"Error: dlr-leveled/{scenario}.dlr was made from an older "
                    f"dlr/{scenario}.dlr; run level first")
        return False

    os.makedirs(FOLDERS["pbn_leveled"], exist_ok=True)
    # Interleaved, so any run of boards from the top walks through the hand types
    return _make_pbn(scenario, leveled_dlr_path(scenario), leveled_pbn_path(scenario),
                     verbose, interleave=True)


def _make_pbn(scenario: str, dlr_path: str, pbn_path: str, verbose: bool,
              interleave: bool = False) -> bool:
    """Deal dlr_path into pbn_path, then add the comments and title."""
    dlr_rel = os.path.relpath(dlr_path, PROJECT_ROOT)
    pbn_rel = os.path.relpath(pbn_path, PROJECT_ROOT)

    if DEALER_PLATFORM == "mac":
        # Step 1: Run dealer locally on Mac
        # Note: dealer3 reads input from stdin, not as a file argument
        if verbose:
            print(f"--------- dealer (Mac): Creating {pbn_rel} from {dlr_rel}")

        seed = dealer_seed(scenario)
        dealer_cmd = [
            MAC_TOOLS["dealer"],
            "-s", str(seed),
            "-g", str(DEALER_GENERATE),
            "-p", str(DEALER_PRODUCE),
            "-f", "printpbn",
            "-v",
        ]
        if interleave:
            dealer_cmd.append("--interleave")

        if verbose:
            print(f"  [Local] {' '.join(dealer_cmd)} < {dlr_path}")

        # Dealer error pattern: "line N: error message"
        dealer_error_pattern = re.compile(r'^line \d+:', re.IGNORECASE)

        try:
            with open(dlr_path, 'r') as infile, open(pbn_path, 'w') as outfile:
                # Use Popen to monitor stderr for early error detection
                process = subprocess.Popen(
                    dealer_cmd,
                    stdin=infile,
                    stdout=outfile,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # Thread to read stderr and detect errors
                stderr_output = []
                error_detected = threading.Event()

                def read_stderr():
                    try:
                        for line in process.stderr:
                            stderr_output.append(line)
                            # Check for dealer error patterns
                            if dealer_error_pattern.match(line.strip()) or \
                               'unknown variable' in line.lower() or \
                               'syntax error' in line.lower():
                                error_detected.set()
                                print_error(f"Dealer error detected: {line.strip()}")
                                process.terminate()
                                return
                    except Exception:
                        pass

                stderr_thread = threading.Thread(target=read_stderr)
                stderr_thread.start()

                # Wait for process with timeout (300 seconds for large hand generation)
                try:
                    process.wait(timeout=300)
                except subprocess.TimeoutExpired:
                    print_error("Error: dealer timed out after 300 seconds")
                    process.kill()
                    stderr_thread.join(timeout=2)
                    if os.path.exists(pbn_path):
                        os.remove(pbn_path)
                    return False

                stderr_thread.join(timeout=5)
                stderr_text = ''.join(stderr_output)
                returncode = process.returncode

            if error_detected.is_set() or returncode != 0:
                print_error(f"Error: dealer failed with exit code {returncode}")
                if stderr_text:
                    print_error(stderr_text)
                # Clean up incomplete output file
                if os.path.exists(pbn_path):
                    os.remove(pbn_path)
                return False

        except Exception as e:
            print_error(f"Error running dealer: {e}")
            return False

        # Validate the output file (dealer may write errors to stdout)
        if not _validate_pbn_output(pbn_path, dealer_error_pattern, verbose):
            return False

    else:
        # Step 1: Run dealer.exe on Windows via SSH
        if verbose:
            print(f"--------- dealer.exe (Windows): Creating {pbn_rel} from {dlr_rel}")
            if interleave:
                print("  (dealer.exe has no --interleave; boards stay in the order dealt)")

        # Build Windows paths
        win_dlr = mac_to_windows_path(dlr_path)
        win_pbn = mac_to_windows_path(pbn_path)

        # Build dealer command
        seed = dealer_seed(scenario)
        dealer_cmd = (
            f'{WINDOWS_TOOLS["dealer"]} {win_dlr} '
            f'-s {seed} -g {DEALER_GENERATE} -p {DEALER_PRODUCE} -m '
            f'>{win_pbn}'
        )

        try:
            returncode, stdout, stderr = run_windows_command(dealer_cmd, verbose=verbose)

            if returncode != 0:
                print_error(f"Error: dealer.exe failed with exit code {returncode}")
                if stderr:
                    print_error(stderr)
                return False

        except Exception as e:
            print_error(f"Error running dealer.exe: {e}")
            return False

    # Step 2: Run oneComment.py locally to add comments
    if verbose:
        print(f"--------- oneComment.py: Adding comments to {pbn_rel}")

    py_dir = FOLDERS["py"]
    comment_script = os.path.join(py_dir, "oneComment.py")

    if not os.path.exists(comment_script):
        print_error(f"Error: oneComment.py not found: {comment_script}")
        return False

    try:
        result = subprocess.run(
            [MAC_TOOLS["python"], comment_script, "--scenario", scenario, "--pbn", pbn_path],
            cwd=py_dir,
            capture_output=True,
            text=True,
            check=True,
        )

        if verbose and result.stdout:
            print(result.stdout)

    except subprocess.CalledProcessError as e:
        print_error(f"Error running oneComment.py: {e}")
        if e.stderr:
            print_error(e.stderr)
        return False

    # Verify output was created
    if not os.path.exists(pbn_path):
        print_error(f"Error: PBN file was not created: {pbn_path}")
        return False

    # Step 3: Set correct Event tags from PBS file
    run_title(scenario, verbose, pbn_path)

    return True


if __name__ == "__main__":
    # Test with a scenario
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
    else:
        scenario = "Smolen"

    print(f"Testing PBN operation with scenario: {scenario}\n")
    success = run_pbn(scenario)
    print(f"\nResult: {'Success' if success else 'Failed'}")
