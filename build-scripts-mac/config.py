"""
Configuration for the Mac build pipeline.
"""
import os

# Project root directory (parent of build-scripts-mac)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Version stamped into generated artifacts that carry provenance (currently the
# quiz/v1 JSON emitted by the quiz operation). Bump when a pipeline change alters
# the content of those artifacts, so consumers can detect stale snapshots.
PIPELINE_VERSION = "1.0.0"

# Windows VM SSH configuration
# Set these environment variables in your ~/.zshrc:
#   export WINDOWS_HOST="your-windows-ip"
#   export WINDOWS_USER="your-windows-username"
#   export PBS_UNC_PREFIX="\\Mac\Home"  (for Parallels) or your VM's UNC prefix
#   export PBS_BCSCRIPT_PATH="~/Documents/BCScript/2024-11-13"  (path to BCScript folder)
WINDOWS_SSH_HOST = os.environ.get("WINDOWS_HOST")
WINDOWS_SSH_USER = os.environ.get("WINDOWS_USER")
UNC_PREFIX = os.environ.get("PBS_UNC_PREFIX")
BCSCRIPT_PATH = os.environ.get("PBS_BCSCRIPT_PATH")

def require_windows_config():
    """Validate that Windows VM environment variables are set.
    Call this before operations that need Windows connectivity."""
    _missing = []
    if not WINDOWS_SSH_HOST:
        _missing.append('WINDOWS_HOST')
    if not WINDOWS_SSH_USER:
        _missing.append('WINDOWS_USER')
    if not UNC_PREFIX:
        _missing.append('PBS_UNC_PREFIX')
    if not BCSCRIPT_PATH:
        _missing.append('PBS_BCSCRIPT_PATH')
    if _missing:
        import sys
        print(f"Error: Missing required environment variables: {', '.join(_missing)}")
        print("Add these to your ~/.zshrc:")
        print('  export WINDOWS_HOST="your-windows-ip"')
        print('  export WINDOWS_USER="your-windows-username"')
        print('  export PBS_UNC_PREFIX="\\\\Mac\\Home"  # For Parallels; adjust for your VM')
        print('  export PBS_BCSCRIPT_PATH="~/Documents/BCScript/2024-11-13"')
        print("Then run: source ~/.zshrc")
        sys.exit(1)

# Helper to convert Mac path to UNC path
def _mac_to_unc(mac_path: str) -> str:
    """Convert a Mac path to a UNC path using the configured prefix."""
    expanded = os.path.expanduser(mac_path)
    # Remove leading ~ expansion to get path relative to home
    home = os.path.expanduser("~")
    if expanded.startswith(home):
        relative = expanded[len(home):]
        return UNC_PREFIX + relative.replace("/", "\\")
    return expanded.replace("/", "\\")

# Drive mappings are built lazily since they require Windows config
_DRIVE_MAPPINGS = None

def get_drive_mappings():
    """Get drive mappings, building them on first access. Requires Windows config."""
    global _DRIVE_MAPPINGS
    if _DRIVE_MAPPINGS is None:
        require_windows_config()
        _bcscript_expanded = os.path.expanduser(BCSCRIPT_PATH)
        _DRIVE_MAPPINGS = {
            # G: drive maps to GitHub folder (one level above project)
            os.path.dirname(PROJECT_ROOT): ("G:", _mac_to_unc(os.path.dirname(PROJECT_ROOT))),
            # P: drive maps to the project root
            PROJECT_ROOT: ("P:", _mac_to_unc(PROJECT_ROOT)),
            # S: drive maps to BridgeComposer scripts folder
            _bcscript_expanded: ("S:", _mac_to_unc(_bcscript_expanded)),
        }
    return _DRIVE_MAPPINGS

# For backward compatibility
DRIVE_MAPPINGS = None  # Use get_drive_mappings() instead

# Folder structure within the project
FOLDERS = {
    "btn": os.path.join(PROJECT_ROOT, "btn"),
    "pbs": os.path.join(PROJECT_ROOT, "PBS"),
    "pbs_test": os.path.join(PROJECT_ROOT, "pbs-test"),
    "pbs_release": os.path.join(PROJECT_ROOT, "pbs-release"),
    "dlr": os.path.join(PROJECT_ROOT, "dlr"),
    "pbn": os.path.join(PROJECT_ROOT, "pbn"),
    "pbn_rotated": os.path.join(PROJECT_ROOT, "pbn-rotated-for-4-players"),
    "lin_rotated": os.path.join(PROJECT_ROOT, "lin-rotated-for-4-players"),
    "bba": os.path.join(PROJECT_ROOT, "bba"),
    "bba_summary": os.path.join(PROJECT_ROOT, "bba-summary"),
    "bba_filtered": os.path.join(PROJECT_ROOT, "bba-filtered"),
    "bba_filtered_out": os.path.join(PROJECT_ROOT, "bba-filtered-out"),
    "bidding_sheets": os.path.join(PROJECT_ROOT, "bidding-sheets"),
    "quiz": os.path.join(PROJECT_ROOT, "quiz"),
    "bbsa": os.path.join(PROJECT_ROOT, "bbsa"),
    "py": os.path.join(PROJECT_ROOT, "py"),
}

# Windows tool paths (as seen from Windows)
WINDOWS_TOOLS = {
    "dealer": "P:\\dealer.exe",
    "bba": "BBA.exe",  # Assumes BBA.exe is in Windows PATH
    "cscript": "cscript",
    "filter_js": "S:\\Filter.js",
    "set_dealer_multi_js": "S:\\SetDealerMulti.js",
    "bidding_sheets_wsf": "S:\\BiddingSheets.wsf",
    "wkhtmltopdf": "wkhtmltopdf",  # Assumes wkhtmltopdf is in Windows PATH
}

# Mac tool paths
#
# bba_cli: the Rust-based bba-cli from BBA-Tools — same engine as the
# bba-server on the droplet, so auctions match the production server
# byte-for-byte. Installed from the signed/notarized .dmg release;
# libEPBot.dylib lives next to it and is auto-discovered via the binary's
# embedded rpath, so no DYLD_LIBRARY_PATH dance is needed.
#
# To run against a dev build instead, point at
# ~/Development/GitHub/BBA-Tools/bba-cli/target/release/bba-cli AND copy
# epbot-libs/macos/arm64/libEPBot.dylib next to it (rpath looks for it
# in @executable_path).
MAC_TOOLS = {
    "python": "python3",
    "wkhtmltopdf": "/opt/homebrew/bin/wkhtmltopdf",  # Adjust if installed elsewhere
    "dealer": "/Applications/Bridge Utilities/dealer3",  # Mac version of dealer
    "bridge_wrangler": "/Applications/Bridge Utilities/bridge-wrangler",
    "bba_cli": "/Applications/Bridge Utilities/bba-cli",
}

# Where to run dealer: "mac" (default) or "windows"
DEALER_PLATFORM = os.environ.get("PBS_DEALER_PLATFORM", "mac").lower()

# Default convention cards
DEFAULT_CC1 = "21GF-DEFAULT"
DEFAULT_CC2 = "21GF-GIB"

# Dealer parameters
SEED_OFFSET = 1          # Increment to regenerate all scenarios with fresh deals
DEALER_GENERATE = 300000000
DEALER_PRODUCE = 500

# Bidding sheet parameters
BIDDING_SHEET_MAX_BOARDS = 50  # Max boards to include in bidding sheets PDF


def dealer_seed(scenario: str) -> int:
    """Compute a deterministic seed from scenario name and offset. Range: 1-1,000,000."""
    import hashlib
    h = hashlib.md5(f"{scenario}:{SEED_OFFSET}".encode()).hexdigest()
    return (int(h, 16) % 1_000_000) + 1

# Pipeline operations in order
OPERATIONS_ORDER = [
    "dlr",      # Generate DLR from BTN
    "pbs",      # Generate PBS from DLR
    "pbn",
    "rotate",
    "bba",
    "filter",
    "filterStats",
    "biddingSheet",
    "quiz",     # Generate quiz PBN/PDF from filtered BBA
    "package",  # Copy artifacts into Bidding Scenarios hierarchy
]
