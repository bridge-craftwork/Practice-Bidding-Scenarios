"""
SSH command executor for running Windows commands from Mac.
Uses native ssh command via subprocess.
"""
import subprocess
import shlex
from typing import Optional, Tuple
from config import WINDOWS_SSH_HOST, WINDOWS_SSH_USER, PROJECT_ROOT, get_drive_mappings


def get_drive_mapping_commands() -> str:
    """
    Generate Windows commands to map network drives.
    SSH sessions don't inherit user's mapped drives, so we need to map them.
    """
    commands = []
    for mac_base, (drive_letter, unc_path) in get_drive_mappings().items():
        # Use net use to map the drive (ignore errors if already mapped)
        commands.append(f"net use {drive_letter} {unc_path} >nul 2>&1")
    return " & ".join(commands)


def mac_to_windows_path(mac_path: str) -> str:
    """
    Convert a Mac path to a Windows path using drive mappings.

    Example:
        /Volumes/Express2T/Development/GitHub/Practice-Bidding-Scenarios/pbn/Smolen.pbn
        -> P:\\pbn\\Smolen.pbn
    """
    # Normalize the path
    mac_path = mac_path.replace("\\", "/")

    # Find the matching drive mapping (sort by path length descending to match most specific first)
    for mac_base, (windows_drive, unc_path) in sorted(get_drive_mappings().items(), key=lambda x: len(x[0]), reverse=True):
        if mac_path.startswith(mac_base):
            # Replace Mac base with Windows drive and convert slashes
            relative_path = mac_path[len(mac_base):]
            windows_path = windows_drive + relative_path.replace("/", "\\")
            return windows_path

    # No mapping found, return as-is (will likely fail on Windows)
    print(f"Warning: No drive mapping found for {mac_path}")
    return mac_path


def windows_to_mac_path(windows_path: str) -> str:
    """
    Convert a Windows path to a Mac path using drive mappings.

    Example:
        P:\\pbn\\Smolen.pbn
        -> /Volumes/Express2T/Development/GitHub/Practice-Bidding-Scenarios/pbn/Smolen.pbn
    """
    # Normalize the path
    windows_path = windows_path.replace("/", "\\")

    # Find the matching drive mapping
    for mac_base, (windows_drive, unc_path) in get_drive_mappings().items():
        if windows_path.upper().startswith(windows_drive.upper()):
            # Replace Windows drive with Mac base and convert slashes
            relative_path = windows_path[len(windows_drive):]
            mac_path = mac_base + relative_path.replace("\\", "/")
            return mac_path

    # No mapping found, return as-is
    print(f"Warning: No drive mapping found for {windows_path}")
    return windows_path


def run_windows_command(
    command: str,
    capture_output: bool = True,
    check: bool = True,
    timeout: Optional[int] = 300,
    verbose: bool = True,
    map_drives: bool = True,
) -> Tuple[int, str, str]:
    """
    Run a command on the Windows VM via SSH.

    Args:
        command: The Windows command to run
        capture_output: Whether to capture stdout/stderr
        check: Whether to raise exception on non-zero exit
        timeout: Command timeout in seconds (None for no timeout)
        verbose: Whether to print command being executed
        map_drives: Whether to map network drives before running command

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    # Build SSH command
    ssh_target = f"{WINDOWS_SSH_USER}@{WINDOWS_SSH_HOST}"

    # Prepend drive mapping commands if needed
    if map_drives:
        drive_cmds = get_drive_mapping_commands()
        full_command = f"{drive_cmds} & {command}"
    else:
        full_command = command

    # Use ssh with the command
    # The -o options help with reliability
    ssh_cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ConnectTimeout=10",
        ssh_target,
        full_command,
    ]

    if verbose:
        print(f"  [SSH] {command}")

    try:
        result = subprocess.run(
            ssh_cmd,
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            check=False,  # We handle the check ourselves
        )

        stdout = result.stdout if capture_output else ""
        stderr = result.stderr if capture_output else ""

        if check and result.returncode != 0:
            error_msg = f"Windows command failed (exit code {result.returncode})"
            if stderr:
                error_msg += f": {stderr}"
            raise subprocess.CalledProcessError(
                result.returncode, command, stdout, stderr
            )

        return result.returncode, stdout, stderr

    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Command timed out after {timeout} seconds: {command}")


def test_ssh_connection() -> bool:
    """
    Test that SSH connection to Windows VM is working.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        returncode, stdout, stderr = run_windows_command(
            "echo SSH connection successful",
            check=False,
            verbose=False,
        )
        return returncode == 0 and "successful" in stdout
    except Exception as e:
        print(f"SSH connection test failed: {e}")
        return False


if __name__ == "__main__":
    # Test the SSH connection
    print("Testing SSH connection to Windows VM...")
    print(f"  Host: {WINDOWS_SSH_USER}@{WINDOWS_SSH_HOST}")

    if test_ssh_connection():
        print("  Connection successful!")

        # Test path conversion
        test_path = f"{PROJECT_ROOT}/pbn/Smolen.pbn"
        windows_path = mac_to_windows_path(test_path)
        print(f"\nPath conversion test:")
        print(f"  Mac:     {test_path}")
        print(f"  Windows: {windows_path}")

        # Show drive mapping commands
        print(f"\nDrive mapping commands:")
        print(f"  {get_drive_mapping_commands()}")

        # Test a simple Windows command with drive mapping
        print("\nTesting Windows command execution (with drive mapping)...")
        try:
            returncode, stdout, stderr = run_windows_command("dir P:\\", check=False)
            if returncode == 0:
                print("  Directory listing successful!")
                # Print first few lines
                lines = stdout.strip().split("\n")[:5]
                for line in lines:
                    print(f"    {line}")
            else:
                print(f"  Command failed with exit code {returncode}")
                if stderr:
                    print(f"  Error: {stderr}")
        except Exception as e:
            print(f"  Error: {e}")
    else:
        print("  Connection failed!")
        print("\nTroubleshooting:")
        print("  1. Ensure OpenSSH Server is enabled on Windows")
        print("  2. Check that you can manually SSH: ssh rick@10.211.55.5")
        print("  3. Ensure SSH keys are set up (or password auth is enabled)")
