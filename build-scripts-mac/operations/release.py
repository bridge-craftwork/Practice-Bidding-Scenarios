"""
Release operation: publish a scenario by committing its .btn and .dlr and
pushing main.

The BBO extension and Bridge Classroom load dlr/<name>.dlr from main, so a push
to main is the release (issue #321). Which buttons each channel shows is still
set by btn/-button-layout-{release,beta}.txt; see release-layout.

The .dlr is regenerated from the .btn first, so what ships always matches the
master file. Only those two files are committed; anything else staged or
modified in the tree is left alone.

This operation is intentionally NOT included in OPERATIONS_ORDER,
so it won't run with "*" or "op+" wildcards. It must be invoked explicitly.
"""
import os
import subprocess
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FOLDERS, PROJECT_ROOT
from operations.dlr_from_btn import run_dlr


def _git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=PROJECT_ROOT)


def run_release(scenario: str, verbose: bool = True) -> bool:
    """
    Release a scenario: regenerate its .dlr, commit btn/{scenario}.btn and
    dlr/{scenario}.dlr, and push main.

    Args:
        scenario: Scenario name (e.g., "Smolen")
        verbose: Whether to print progress

    Returns:
        True if successful, False otherwise
    """
    if verbose:
        print(f"--------- Releasing {scenario}")

    # A push from any other branch would not reach users
    branch = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if branch != "main":
        print(f"Error: release: on branch '{branch}'; release pushes main")
        return False

    if not run_dlr(scenario, verbose):
        return False

    paths = [
        os.path.relpath(os.path.join(FOLDERS["btn"], f"{scenario}.btn"), PROJECT_ROOT),
        os.path.relpath(os.path.join(FOLDERS["dlr"], f"{scenario}.dlr"), PROJECT_ROOT),
    ]

    original_dir = os.getcwd()
    os.chdir(PROJECT_ROOT)
    try:
        result = _git("add", "--", *paths)
        if result.returncode != 0:
            print(f"  Git add failed: {result.stderr.strip()}")
            return False

        # Commit only these two paths, even if other changes are staged
        if _git("diff", "--cached", "--quiet", "--", *paths).returncode != 0:
            commit_msg = f"Release {scenario}"
            result = _git("commit", "-m", commit_msg, "--", *paths)
            if result.returncode != 0:
                print(f"  Git commit failed: {result.stderr.strip()}")
                return False
            if verbose:
                print(f"  Committed: {commit_msg}")
        elif verbose:
            print(f"  {' and '.join(paths)} unchanged since the last commit")

        # Push if main is ahead of origin: this commit, or earlier unpushed ones
        _git("fetch", "--quiet", "origin", "main")
        ahead = _git("rev-list", "--count", "origin/main..HEAD").stdout.strip()
        if ahead == "0":
            if verbose:
                print(f"  {scenario}: already released (main matches origin/main)")
            return True

        if verbose:
            print(f"  Pushing {ahead} commit(s) to origin/main...")
        # Rebase-and-retry on the manifest-bot race
        from git_utils import push_with_rebase_retry
        return push_with_rebase_retry(verbose)

    except Exception as e:
        print(f"Error: release: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        os.chdir(original_dir)


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
