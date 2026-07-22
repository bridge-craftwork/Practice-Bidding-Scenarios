"""
Release layout operation: Copy button layout from beta to release and commit/push.

This operation is intentionally NOT included in OPERATIONS_ORDER,
so it won't run with "*" or "op+" wildcards. It must be invoked explicitly.
"""
import filecmp
import os
import shutil
import subprocess
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FOLDERS, PROJECT_ROOT


def run_release_layout(scenario: str = None, verbose: bool = True) -> bool:
    """
    Release the button layout by copying beta to release and committing.

    btn/-button-layout-beta.txt -> btn/-button-layout-release.txt
    Then commits and pushes the release file.
    The beta file is left intact.

    Args:
        scenario: Ignored (for API compatibility with other operations)
        verbose: Whether to print progress

    Returns:
        True if successful, False otherwise
    """
    if verbose:
        print(f"--------- Releasing button layout")

    btn_dir = FOLDERS["btn"]
    beta_path = os.path.join(btn_dir, "-button-layout-beta.txt")
    release_path = os.path.join(btn_dir, "-button-layout-release.txt")

    # Check that beta file exists
    if not os.path.exists(beta_path):
        print(f"Error: release-layout: No beta file found: {beta_path}")
        return False

    # Check if beta and release are already identical
    if os.path.exists(release_path) and filecmp.cmp(beta_path, release_path, shallow=False):
        print(f"  Beta is the same as Release")
        return True

    try:
        # Copy beta to release (overwriting if exists)
        if verbose:
            print(f"  Copying: {beta_path}")
            print(f"       to: {release_path}")

        shutil.copy2(beta_path, release_path)

        if verbose:
            print(f"  Copied successfully")

        # Git add, commit, and push
        if verbose:
            print(f"  Committing and pushing...")

        # Change to project root for git commands
        original_dir = os.getcwd()
        os.chdir(PROJECT_ROOT)

        try:
            # Git add the release file
            subprocess.run(
                ["git", "add", release_path],
                check=True,
                capture_output=True,
                text=True
            )

            # Commit
            commit_msg = "Release button layout to production"
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
        print(f"Error: release-layout: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print(f"Testing release-layout operation\n")
    success = run_release_layout()
    print(f"\nResult: {'Success' if success else 'Failed'}")
