"""Shared git helpers for pipeline operations."""

import subprocess


def push_with_rebase_retry(verbose: bool = True, retries: int = 3) -> bool:
    """Run ``git push``; if it is rejected because ``origin/main`` moved under us,
    ``git pull --rebase --autostash origin main`` and retry.

    This handles the manifest-bot race: a GitHub Action rebuilds ``manifest/`` and
    commits+pushes to ``main`` after every push touching ``btn/``, ``pbs-*/``, etc.,
    so a subsequent bare push (as the ``release`` / ``release-layout`` ops and the
    ``pbs`` auto-commit do) fails as a non-fast-forward. Rebasing onto the bot's
    commit and re-pushing recovers automatically. ``--autostash`` keeps it safe when
    the working tree has other uncommitted changes (e.g. mid-pipeline artifacts).

    The caller must have already committed and be inside the repo working tree.
    Returns True on a successful push, False otherwise.
    """
    for attempt in range(retries + 1):
        result = subprocess.run(["git", "push"], capture_output=True, text=True)
        if result.returncode == 0:
            if verbose:
                print("  Pushed successfully")
            return True

        combined = (result.stderr or "") + (result.stdout or "")
        rejected = any(
            token in combined
            for token in ("fast-forward", "rejected", "fetch first", "[rejected]")
        )
        if attempt < retries and rejected:
            if verbose:
                print(
                    "  Push rejected (remote moved, likely the manifest bot); "
                    "rebasing onto origin/main and retrying..."
                )
            pull = subprocess.run(
                ["git", "pull", "--rebase", "--autostash", "origin", "main"],
                capture_output=True,
                text=True,
            )
            if pull.returncode != 0:
                print(f"  Rebase failed: {pull.stderr.strip()}")
                # Don't leave the tree mid-rebase.
                subprocess.run(
                    ["git", "rebase", "--abort"], capture_output=True, text=True
                )
                return False
            continue

        # Out of retries, or a failure that a rebase won't fix.
        print(f"  Git push failed: {result.stderr.strip()}")
        print("  (You may need to pull first)")
        return False

    return False
