"""
Release operation: Move scenario from pbs-test to pbs-release and commit/push.

This operation is intentionally NOT included in OPERATIONS_ORDER,
so it won't run with "*" or "op+" wildcards. It must be invoked explicitly.
"""
import os
import shutil
import subprocess
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FOLDERS, PROJECT_ROOT


def run_release(scenario: str, verbose: bool = True) -> bool:
    """
    Release a scenario by moving it from pbs-test to pbs-release and committing.

    pbs-test/{scenario}.pbs -> pbs-release/{scenario}.pbs
    Then commits and pushes the pbs-release file.

    Args:
        scenario: Scenario name (e.g., "Smolen")
        verbose: Whether to print progress

    Returns:
        True if successful, False otherwise
    """
    if verbose:
        print(f"--------- Releasing {scenario}")

    pbs_test_path = os.path.join(FOLDERS["pbs_test"], f"{scenario}.pbs")
    pbs_release_path = os.path.join(FOLDERS["pbs_release"], f"{scenario}.pbs")

    # Check that pbs-test file exists
    if not os.path.exists(pbs_test_path):
        # No pbs-test file — verify whether current DLR matches the released PBS
        if os.path.exists(pbs_release_path):
            from operations.pbs_from_dlr import generate_pbs
            dlr_path = os.path.join(FOLDERS["dlr"], f"{scenario}.dlr")
            if os.path.exists(dlr_path):
                with open(dlr_path, 'r', encoding='utf-8') as f:
                    dlr_content = f.read()
                with open(pbs_release_path, 'r', encoding='utf-8') as f:
                    release_content = f.read()
                generated = generate_pbs(dlr_content, scenario)
                if generated == release_content:
                    print(f"  {scenario}: Already up to date (matches released version)")
                    return True
        print(f"Error: release: No pbs-test file found: {pbs_test_path}")
        return False

    try:
        # Move file from pbs-test to pbs-release
        if verbose:
            print(f"  Moving: {pbs_test_path}")
            print(f"      to: {pbs_release_path}")

        # Ensure pbs-release folder exists
        os.makedirs(FOLDERS["pbs_release"], exist_ok=True)

        # Copy then remove (safer than move across filesystems)
        shutil.copy2(pbs_test_path, pbs_release_path)
        os.remove(pbs_test_path)

        if verbose:
            print(f"  Moved successfully")

        # Git add, commit, and push
        if verbose:
            print(f"  Committing and pushing...")

        # Change to project root for git commands
        original_dir = os.getcwd()
        os.chdir(PROJECT_ROOT)

        try:
            # Git add the release file
            subprocess.run(
                ["git", "add", pbs_release_path],
                check=True,
                capture_output=True,
                text=True
            )

            # Stage the pbs-test removal only if git was tracking it
            tracked = subprocess.run(
                ["git", "ls-files", "--error-unmatch", pbs_test_path],
                capture_output=True,
                text=True
            )
            if tracked.returncode == 0:
                subprocess.run(
                    ["git", "add", pbs_test_path],
                    check=True,
                    capture_output=True,
                    text=True
                )

            # Commit
            commit_msg = f"Release {scenario} to pbs-release"
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
                    print(f"  Nothing to commit (file unchanged)")
                else:
                    print(f"  Git commit failed: {result.stderr}")
                    return False
            else:
                if verbose:
                    print(f"  Committed: {commit_msg}")

            # Push (rebase-and-retry on the manifest-bot race)
            from git_utils import push_with_rebase_retry
            if not push_with_rebase_retry(verbose):
                return False

        finally:
            os.chdir(original_dir)

        return True

    except Exception as e:
        print(f"Error: release: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
    else:
        print("Usage: python release.py <scenario>")
        print("Example: python release.py Smolen")
        sys.exit(1)

    print(f"Testing release operation with scenario: {scenario}\n")
    success = run_release(scenario)
    print(f"\nResult: {'Success' if success else 'Failed'}")
