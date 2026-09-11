"""
Title operation: Set title metadata in PBN files from the PBS Button text.
Sets both %HRTitleEvent header comment (for pbn-to-pdf) and [Event] tags.
Runs after PBN generation to ensure proper titles in output files.
"""
import os
import re
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FOLDERS, dealer_seed, SEED_OFFSET


def get_title_from_pbs(scenario: str) -> str:
    """
    Extract the title from a PBS file's Button line.

    The Button line format is: Button,title,chat_text

    Args:
        scenario: Scenario name (e.g., "Smolen")

    Returns:
        Title from PBS file, or scenario name if not found
    """
    pbs_path = os.path.join(FOLDERS["pbs"], scenario)

    if not os.path.exists(pbs_path):
        return scenario

    try:
        with open(pbs_path, "r") as f:
            for line in f:
                if line.startswith("Button,"):
                    # Extract the title (second field after "Button,")
                    parts = line.split(",", 2)
                    if len(parts) >= 2:
                        return parts[1].strip()
    except Exception as e:
        print(f"Warning: Error reading PBS file: {e}")

    return scenario


def run_title(scenario: str, verbose: bool = True, pbn_path: str = None) -> bool:
    """
    Update title metadata in the PBN file with the title from PBS.

    Sets:
    - %HRTitleEvent header comment (used by pbn-to-pdf for PDF title)
    - [Event "..."] tags on each board

    pbn/{scenario}.pbn -> pbn/{scenario}.pbn (updated)

    Args:
        scenario: Scenario name (e.g., "Smolen")
        verbose: Whether to print progress
        pbn_path: The file to update, if not pbn/{scenario}.pbn

    Returns:
        True if successful, False otherwise
    """
    if verbose:
        print(f"--------- Setting title for {scenario}")

    # Get title from PBS file
    title = get_title_from_pbs(scenario)

    if verbose:
        print(f"  Title: {title}")

    # Update PBN file
    pbn_path = pbn_path or os.path.join(FOLDERS["pbn"], f"{scenario}.pbn")

    if not os.path.exists(pbn_path):
        print(f"Error: PBN file not found: {pbn_path}")
        return False

    try:
        with open(pbn_path, "r") as f:
            lines = f.readlines()

        # Update or add %HRTitleEvent in header
        hr_title_line = f'%HRTitleEvent "{title}"\n'
        hr_pattern = re.compile(r'^%HRTitleEvent\s')
        found_hr_title = False
        insert_pos = 0

        for i, line in enumerate(lines):
            if hr_pattern.match(line):
                # Replace existing %HRTitleEvent
                lines[i] = hr_title_line
                found_hr_title = True
                break
            elif line.startswith('%'):
                # Track last header comment position
                insert_pos = i + 1
            elif line.startswith('['):
                # Reached first board, stop looking
                break

        if not found_hr_title:
            # Insert %HRTitleEvent after other header comments
            lines.insert(insert_pos, hr_title_line)

        # Add or update %HRSeed comment after %HRTitleEvent
        seed = dealer_seed(scenario)
        hr_seed_line = f'%HRSeed {seed} (offset {SEED_OFFSET})\n'
        hr_seed_pattern = re.compile(r'^%HRSeed\s')
        found_hr_seed = False

        for i, line in enumerate(lines):
            if hr_seed_pattern.match(line):
                lines[i] = hr_seed_line
                found_hr_seed = True
                break

        if not found_hr_seed:
            # Insert after %HRTitleEvent
            for i, line in enumerate(lines):
                if line.startswith('%HRTitleEvent'):
                    lines.insert(i + 1, hr_seed_line)
                    break

        # Join lines back to content
        content = ''.join(lines)

        # Replace all [Event "..."] tags with the new title
        pattern = r'\[Event "[^"]*"\]'
        replacement = f'[Event "{title}"]'
        updated_content = re.sub(pattern, replacement, content)

        # Remove all [Date "..."] lines
        updated_content = re.sub(r'\[Date "[^"]*"\]\n?', '', updated_content)

        with open(pbn_path, "w") as f:
            f.write(updated_content)

        if verbose:
            count = len(re.findall(pattern, content))
            print(f"  Updated {count} Event tags in {pbn_path}")

        return True

    except Exception as e:
        print(f"Error updating PBN file: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
    else:
        scenario = "Smolen"

    print(f"Testing title operation with scenario: {scenario}\n")
    success = run_title(scenario)
    print(f"\nResult: {'Success' if success else 'Failed'}")
