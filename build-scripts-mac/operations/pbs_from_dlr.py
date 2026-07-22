"""
PBS operation: Generate PBS file from DLR file.
Pipeline stage: DLR → PBS
  - Parses metadata and dealer code from DLR
  - Wraps in BBOalert Script/Button format
Button width and color are derived from the layout file.
"""
import os
import re
import subprocess
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FOLDERS, PROJECT_ROOT

# Cache for layout styles (loaded once)
_layout_styles = None


def load_layout_styles():
    """
    Parse the layout file and extract button width/color for each scenario.
    Returns dict mapping scenario name -> {'width': '12%', 'color': 'blue'}
    """
    global _layout_styles
    if _layout_styles is not None:
        return _layout_styles

    _layout_styles = {}
    layout_path = os.path.join(FOLDERS["btn"], "-layout.txt")

    if not os.path.exists(layout_path):
        return _layout_styles

    with open(layout_path, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or stripped.startswith('[') or stripped == '---':
                continue

            # Parse button row, handling groups
            buttons = parse_layout_buttons(stripped)
            for btn in buttons:
                name = btn['name']
                if btn.get('width') or btn.get('color'):
                    _layout_styles[name] = {
                        'width': btn.get('width'),
                        'color': btn.get('color'),
                    }

    return _layout_styles


def parse_layout_buttons(line):
    """Parse a button row line from layout file, handling groups."""
    buttons = []

    # Split by comma but respect parentheses
    parts = []
    current = ""
    paren_depth = 0

    for char in line:
        if char == '(':
            paren_depth += 1
            current += char
        elif char == ')':
            paren_depth -= 1
            current += char
        elif char == ',' and paren_depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current.strip())

    for part in parts:
        part = part.strip()
        if part.startswith('(') and part.endswith(')'):
            # Grouped buttons - they share 50% width
            group_content = part[1:-1]
            group_items = [s.strip() for s in group_content.split(',')]

            # Calculate width for each button in group
            total_width = 50
            n = len(group_items)
            base_width = total_width // n
            remainder = total_width % n

            for i, item in enumerate(group_items):
                item_parts = item.split(':')
                name = item_parts[0]
                color = None
                item_width = None
                for p in item_parts[1:]:
                    if p.endswith('%'):
                        item_width = p
                    else:
                        color = p
                # Use explicit width if provided, otherwise calculate
                if item_width is None:
                    item_width = f"{base_width + (1 if i >= n - remainder else 0)}%"
                buttons.append({'name': name, 'width': item_width, 'color': color, 'grouped': True})
        else:
            # Regular button - may have explicit width like file:blue:38%
            item_parts = part.split(':')
            name = item_parts[0]
            color = None
            width = None
            for p in item_parts[1:]:
                if p.endswith('%'):
                    width = p
                else:
                    color = p
            buttons.append({'name': name, 'width': width, 'color': color, 'grouped': False})

    # Calculate widths for non-grouped buttons
    non_grouped = [b for b in buttons if not b.get('grouped')]
    grouped = [b for b in buttons if b.get('grouped')]

    if len(non_grouped) == 1 and len(grouped) == 0:
        non_grouped[0]['width'] = '100%'
    elif len(non_grouped) == 2 and len(grouped) == 0:
        for b in non_grouped:
            b['width'] = '50%'
    elif len(non_grouped) == 1 and len(grouped) > 0:
        non_grouped[0]['width'] = '50%'
    elif len(non_grouped) == 2:
        for b in non_grouped:
            b['width'] = '50%'

    return buttons



def generate_logging_code(alias: str, scenario_filename: str) -> str:
    """
    Generate the scenario logging JavaScript code.
    """
    return f"""window.currentPBSScenario = '{alias}';
window.currentPBSScenarioFilename = '{scenario_filename}';
console.log('PBS: Logging scenario selection for {alias}');
fetch('https://bba.harmonicsystems.com/api/scenario/select', {{
    method: 'POST',
    headers: {{
        'Content-Type': 'application/json',
        'X-Client-Version': '1.0.0'
    }},
    body: JSON.stringify({{
        scenario: '{alias}',
        user: whoAmI() || 'anonymous'
    }})
}}).then(function(r){{ console.log('PBS: Server response', r.status); }}).catch(function(e){{ console.log('PBS: Fetch error', e); }});"""


def parse_dlr_file(dlr_content: str) -> dict:
    """
    Parse a DLR file's content and extract metadata, chat, and dealer code.

    Returns:
        dict with keys: alias, button_text, dealer_position, gib_works, bba_works,
                       auction_filter, convention_card_ns, convention_card_ew, chat, dealer_code
    """
    result = {
        'alias': None,
        'button_text': None,
        'dealer_position': 'S',
        'gib_works': True,
        'bba_works': True,
        'auction_filter': None,
        'convention_card_ns': None,
        'convention_card_ew': None,
        'quiz_control': None,
        'chat': None,
        'dealer_code': None,
    }

    # Parse single-line metadata: # key: value
    metadata_pattern = r'^#\s*(alias|button-text|scenario-title|gib-works|bba-works|auction-filter|convention-card-ns|convention-card-ew|quiz-control):\s*(.*)$'
    for match in re.finditer(metadata_pattern, dlr_content, re.MULTILINE):
        key = match.group(1).lower().replace('-', '_')
        value = match.group(2).strip()

        if key in ('gib_works', 'bba_works'):
            result[key] = value.lower() == 'true'
        else:
            result[key] = value

    # Extract dealer position from dealer statement (e.g., "dealer south")
    dealer_match = re.search(r'^\s*dealer\s+(south|north|east|west)', dlr_content, re.MULTILINE)
    if dealer_match:
        position_map = {'south': 'S', 'north': 'N', 'east': 'E', 'west': 'W'}
        result['dealer_position'] = position_map[dealer_match.group(1)]

    # Parse chat block: /*@chat ... @chat*/
    chat_match = re.search(r'/\*@chat\s*\n(.*?)@chat\*/', dlr_content, re.DOTALL)
    if chat_match:
        result['chat'] = chat_match.group(1).rstrip()

    # Extract dealer code: everything after metadata, chat block, and dealer statement
    lines = dlr_content.split('\n')
    dealer_lines = []
    in_chat_block = False
    past_header = False

    for line in lines:
        if '/*@chat' in line:
            in_chat_block = True
            continue
        if '@chat*/' in line:
            in_chat_block = False
            continue
        if in_chat_block:
            continue

        if not past_header:
            # Skip metadata lines
            if re.match(r'^#\s*(alias|button-text|scenario-title|gib-works|bba-works|auction-filter|convention-card-ns|convention-card-ew|quiz-control):', line):
                continue
            # Skip the dealer statement (PBS uses setDealerCode position arg instead)
            if re.match(r'^dealer\s+(south|north|east|west)', line.strip()):
                continue
            if line.strip() == '':
                continue
            past_header = True

        dealer_lines.append(line)

    result['dealer_code'] = '\n'.join(dealer_lines)

    return result


def generate_pbs(dlr_content: str, scenario_filename: str) -> str:
    """
    Generate PBS file content from DLR file content.
    Button width and color are derived from the layout file.
    """
    parsed = parse_dlr_file(dlr_content)

    alias = parsed['alias'] or 'Unknown'
    button_text = parsed['button_text'] or alias
    dealer_position = parsed['dealer_position'] or 'S'

    # Get layout styles for this scenario
    layout_styles = load_layout_styles()
    scenario_style = layout_styles.get(scenario_filename, {})

    # Dealer code is already expanded in the DLR (includes inlined)
    dealer_code = parsed['dealer_code']

    # Remove "action printpbn" line - not needed in PBS
    dealer_code = re.sub(r'\n*action\s+printpbn\s*\n*', '\n', dealer_code)

    # Build the PBS content
    lines = []

    # Script block with logging code
    lines.append(f"Script,{alias}")
    lines.append(generate_logging_code(alias, scenario_filename))
    lines.append("setDealerCode(`")

    # Add auction filter and convention cards if present (as block comment)
    has_metadata = parsed['auction_filter'] or parsed['convention_card_ns'] or parsed['convention_card_ew']
    if has_metadata:
        lines.append("")
        lines.append("/*")
        if parsed['convention_card_ns']:
            lines.append(f"convention-card-ns: {parsed['convention_card_ns']}")
        if parsed['convention_card_ew']:
            lines.append(f"convention-card-ew: {parsed['convention_card_ew']}")
        if parsed['auction_filter']:
            lines.append(f"auction-filter: {parsed['auction_filter']}")
        lines.append("*/")

    # Add dealer code
    lines.append(dealer_code.rstrip())

    # Close setDealerCode
    lines.append(f"`, \"{dealer_position}\", true)")
    lines.append("Script")

    # Button definition
    # Build style string from layout file (width and color)
    style_parts = []

    # Width from layout file
    if scenario_style.get('width'):
        style_parts.append(f"width={scenario_style['width']}")

    # Color: lightpink background if GIB doesn't work, else text color from layout
    if not parsed['gib_works']:
        style_parts.append("backgroundColor=lightpink")
    elif scenario_style.get('color'):
        style_parts.append(f"color={scenario_style['color']}")

    style_str = " ".join(style_parts)
    if style_str:
        style_str = "," + style_str

    if parsed['chat']:
        # Convert regular commas to wide commas in chat content
        # Replace ", " with "，" (wide comma absorbs the trailing space)
        chat_content = parsed['chat'].replace(', ', '，')
        # Format chat with line continuations
        chat_lines = chat_content.split('\n')
        chat_formatted = '\\n\\\n'.join(chat_lines)
        lines.append(f"Button,{button_text},\\n\\")
        lines.append(f"{chat_formatted}\\n\\")
        lines.append(f"%{alias}%{style_str}")
    else:
        lines.append(f"Button,{button_text},%{alias}%{style_str}")

    lines.append("")  # trailing newline

    return '\n'.join(lines)


def _git_commit_and_push(pbs_test_path: str, scenario: str, verbose: bool = True) -> None:
    """Commit and push a pbs-test file for online testing."""
    original_dir = os.getcwd()
    os.chdir(PROJECT_ROOT)

    try:
        # Git add the pbs-test file
        subprocess.run(
            ["git", "add", pbs_test_path],
            check=True,
            capture_output=True,
            text=True
        )

        # Commit
        commit_msg = f"Update pbs-test/{scenario}.pbs"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
                if verbose:
                    print(f"  Git: nothing to commit (file unchanged)")
                return
            else:
                print(f"  Git commit failed: {result.stderr}")
                return
        else:
            if verbose:
                print(f"  Committed: {commit_msg}")

        # Push (fire-and-forget: a failed push just leaves the commit local, to be
        # pushed later). Deliberately NOT rebase-and-retry — this runs mid-pipeline
        # (per scenario), where a git pull --rebase would autostash in-progress
        # artifacts and can stall. Rebase-retry is only for the terminal release ops.
        result = subprocess.run(
            ["git", "push"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"  Git push failed: {result.stderr}")
        else:
            if verbose:
                print(f"  Pushed successfully")

    except Exception as e:
        print(f"  Git error: {e}")
    finally:
        os.chdir(original_dir)


def run_pbs(scenario: str, verbose: bool = True) -> bool:
    """
    Generate PBS file from DLR file.

    dlr/{scenario}.dlr -> pbs-test/{scenario}.pbs

    Args:
        scenario: Scenario name (e.g., "Smolen")
        verbose: Whether to print progress

    Returns:
        True if successful, False otherwise
    """
    if verbose:
        print(f"--------- Generating PBS from DLR for {scenario}")

    # Check that DLR file exists
    dlr_path = os.path.join(FOLDERS["dlr"], f"{scenario}.dlr")
    if not os.path.exists(dlr_path):
        print(f"Error: pbs: DLR file not found: {dlr_path}")
        return False

    # Ensure output folder exists
    os.makedirs(FOLDERS["pbs_test"], exist_ok=True)

    try:
        if verbose:
            print(f"  Source: {dlr_path}")

        with open(dlr_path, 'r', encoding='utf-8') as f:
            dlr_content = f.read()

        pbs_content = generate_pbs(dlr_content, scenario)

        pbs_test_path = os.path.join(FOLDERS["pbs_test"], f"{scenario}.pbs")
        pbs_release_path = os.path.join(FOLDERS["pbs_release"], f"{scenario}.pbs")

        # Check if pbs-test file already exists (scenario was already modified)
        pbs_test_exists = os.path.exists(pbs_test_path)

        # Check if content differs from pbs-release
        content_differs = True  # Default to True if no release file exists
        if os.path.exists(pbs_release_path):
            with open(pbs_release_path, 'r', encoding='utf-8') as f:
                release_content = f.read()
            content_differs = (pbs_content != release_content)

        # Only write to pbs-test if:
        # - pbs-test file already exists (was already modified), OR
        # - Content differs from pbs-release
        if pbs_test_exists or content_differs:
            with open(pbs_test_path, 'w', encoding='utf-8') as f:
                f.write(pbs_content)
            if verbose:
                if not content_differs:
                    print(f"  Updated: {pbs_test_path} (unchanged from release)")
                else:
                    print(f"  Created: {pbs_test_path}")

            # Auto-commit and push pbs-test file for online testing
            _git_commit_and_push(pbs_test_path, scenario, verbose)
        else:
            if verbose:
                print(f"  Skipped: {pbs_test_path} (matches release)")

        return True

    except Exception as e:
        print(f"Error: pbs: {e}")
        import traceback
        traceback.print_exc()
        return False



if __name__ == "__main__":
    if len(sys.argv) > 1:
        scenario = sys.argv[1]
    else:
        scenario = "Smolen"

    print(f"Testing PBS operation with scenario: {scenario}\n")
    success = run_pbs(scenario)
    print(f"\nResult: {'Success' if success else 'Failed'}")
