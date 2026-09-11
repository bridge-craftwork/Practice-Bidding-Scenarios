"""
Package operation: Copy scenario artifacts into a hierarchical folder
structure matching the BBOAlert button layout.

This operation is intentionally NOT included in OPERATIONS_ORDER,
so it won't run with "*" or "op+" wildcards. It must be invoked explicitly.

Output structure:
    Bidding Scenarios/
        Minor Suit Sequences/
            scenario.dlr
            scenario.pbn
            scenario.pdf
            scenario bidding sheets.pdf
            scenario quizzes.pdf
        Notrump Sequences/
            ...
"""
import os
import shutil
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FOLDERS, PROJECT_ROOT
from utils.leveling import leveled_or_original

# Module-level cache for the parsed layout
_layout_cache = None


def _parse_button_layout():
    """
    Parse btn/-button-layout-release.txt and return a dict mapping
    scenario names to lists of section folder paths.

    Returns:
        dict: {scenario_name: [section_path, ...]}
        where section_path is relative to the top-level output folder
        (e.g., "Minor Suit Sequences")
    """
    global _layout_cache
    if _layout_cache is not None:
        return _layout_cache

    layout_path = os.path.join(FOLDERS["btn"], "-button-layout-release.txt")
    if not os.path.exists(layout_path):
        print(f"Error: Button layout file not found: {layout_path}")
        return {}

    scenario_sections = {}  # {scenario_name: [section_folder_name, ...]}
    current_section = None
    section_counter = 0

    with open(layout_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            stripped = line.strip()

            # Skip comments and empty lines
            if not stripped or stripped.startswith('#'):
                continue

            # Skip [Major] lines — we use one top-level folder
            if stripped.startswith('[Major]'):
                continue

            # Skip [Action] lines
            if stripped.startswith('[Action]'):
                continue

            # Parse [Section] lines — number-prefixed for layout order
            if stripped.startswith('[Section]'):
                section_counter += 1
                section_name = stripped[len('[Section]'):].strip()
                # Replace / with - to avoid path separator issues
                section_name = section_name.replace('/', '-')
                current_section = f"{section_counter:02d} {section_name}"
                continue

            # Content lines: scenario names
            if current_section is None:
                continue

            # Split on commas to get individual entries
            entries = stripped.split(',')
            for entry in entries:
                name = entry.strip()

                # Strip grouping parens
                name = name.strip('(').strip(')')

                # Strip color and width suffixes (e.g., ":blue:12%", ":38%")
                if ':' in name:
                    name = name.split(':')[0]

                # Skip separators and empty
                name = name.strip()
                if not name or name == '---':
                    continue

                # Add to mapping
                if name not in scenario_sections:
                    scenario_sections[name] = []
                if current_section not in scenario_sections[name]:
                    scenario_sections[name].append(current_section)

    _layout_cache = scenario_sections
    return scenario_sections


# Files to copy: (source_folder_key, source_pattern, dest_suffix)
# source_pattern uses {scenario} placeholder
# dest_suffix is appended to scenario name for the destination filename
_FILE_SPECS = [
    # DLR file
    ("dlr", "{scenario}.dlr", ".dlr"),
    # BBA-filtered PBN (with fallback to pbn/)
    ("bba_filtered", "{scenario}.pbn", ".pbn"),
    # BBA-filtered PDF
    ("bba_filtered", "{scenario}.pdf", ".pdf"),
    # Bidding sheets PDF
    ("bidding_sheets", "{scenario} Bidding Sheets.pdf", " bidding sheets.pdf"),
    # Quiz PDF
    ("quiz", "{scenario}.pdf", " quizzes.pdf"),
]


def run_package(scenario: str, verbose: bool = True) -> bool:
    """
    Package a scenario by copying its artifacts into the hierarchical
    Bidding Scenarios folder structure.

    Args:
        scenario: Scenario name (e.g., "Smolen")
        verbose: Whether to print progress

    Returns:
        True if successful, False otherwise
    """
    if verbose:
        print(f"--------- Packaging {scenario}")

    layout = _parse_button_layout()
    if not layout:
        print(f"Error: Could not parse button layout")
        return False

    sections = layout.get(scenario)
    if not sections:
        if verbose:
            print(f"  {scenario}: Not found in button layout — skipping")
        return True  # Not an error; scenario just isn't in the release layout

    output_root = os.path.join(PROJECT_ROOT, "Bidding Scenarios")
    copied_any = False

    for section in sections:
        dest_dir = os.path.join(output_root, section, scenario)
        os.makedirs(dest_dir, exist_ok=True)

        for folder_key, src_pattern, dest_suffix in _FILE_SPECS:
            src_name = src_pattern.format(scenario=scenario)
            src_path = os.path.join(FOLDERS[folder_key], src_name)

            # A leveled scenario ships its leveled script (issue #322)
            if folder_key == "dlr":
                src_path = leveled_or_original(scenario, "dlr")

            # Fallback: if bba_filtered PBN doesn't exist, try pbn/ (pbn-leveled/ when leveled)
            if not os.path.exists(src_path) and folder_key == "bba_filtered" and dest_suffix == ".pbn":
                src_path = leveled_or_original(scenario, "pbn")

            if not os.path.exists(src_path):
                continue

            dest_name = f"{scenario}{dest_suffix}"
            dest_path = os.path.join(dest_dir, dest_name)

            shutil.copy2(src_path, dest_path)
            copied_any = True
            if verbose:
                # Show path relative to project root
                rel = os.path.relpath(dest_path, PROJECT_ROOT)
                print(f"  → {rel}")

    if not copied_any and verbose:
        print(f"  No artifacts found for {scenario}")

    return True


if __name__ == "__main__":
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
    else:
        print("Usage: python package.py <scenario>")
        print("Example: python package.py Smolen")
        sys.exit(1)

    print(f"Testing package operation with scenario: {scenario}\n")
    success = run_package(scenario)
    print(f"\nResult: {'Success' if success else 'Failed'}")
