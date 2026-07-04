#!/usr/bin/env python3
"""
PBS to BTN conversion: Generate BTN files from existing PBS files.
This is the reverse of the btn_to_pbs operation.

Usage:
    python pbs_to_btn.py [scenario]     # Convert specific scenario
    python pbs_to_btn.py --all          # Convert all PBS files
"""
import os
import re
import sys

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import FOLDERS, PROJECT_ROOT

# GitHub base URL pattern for converting back to #include
GITHUB_SCRIPT_PATTERN = r'Import,https://github\.com/(?:bridge-craftwork|ADavidBailey)/Practice-Bidding-Scenarios/blob/main/(script/[^\s]+)'


def parse_pbs_file(pbs_path: str) -> dict:
    """
    Parse a PBS file and extract components for BTN generation.

    Returns:
        dict with keys: alias, button_text, dealer_position, auction_filter,
                       convention_card, chat, dealer_code
    """
    with open(pbs_path, 'r', encoding='utf-8') as f:
        content = f.read()

    result = {
        'alias': None,
        'button_text': None,
        'dealer_position': 'S',
        'auction_filter': None,
        'convention_card_ns': None,
        'convention_card_ew': None,
        'chat': None,
        'dealer_code': None,
    }

    # Extract alias from Script,{alias}
    alias_match = re.search(r'^Script,(\w+)', content, re.MULTILINE)
    if alias_match:
        result['alias'] = alias_match.group(1)

    # Extract dealer position from `, "{position}", true)`
    position_match = re.search(r'`,\s*"([NSEW])",\s*true\)', content)
    if position_match:
        result['dealer_position'] = position_match.group(1)

    # Extract auction-filter from comment block
    filter_match = re.search(r'auction-filter:\s*(.+?)(?:\n|\*/)', content)
    if filter_match:
        result['auction_filter'] = filter_match.group(1).strip()

    # Extract convention-card-ns and convention-card-ew from comment block
    cc_ns_match = re.search(r'convention-card-ns:\s*(.+?)(?:\n|\*/)', content)
    if cc_ns_match:
        result['convention_card_ns'] = cc_ns_match.group(1).strip()
    else:
        # Legacy fallback: read old "convention-card:" format as NS
        cc_match = re.search(r'convention-card:\s*(.+?)(?:\n|\*/)', content)
        if cc_match:
            result['convention_card_ns'] = cc_match.group(1).strip()
    cc_ew_match = re.search(r'convention-card-ew:\s*(.+?)(?:\n|\*/)', content)
    if cc_ew_match:
        result['convention_card_ew'] = cc_ew_match.group(1).strip()

    # Extract dealer code between setDealerCode(` and closing `)
    # Handles both formats: `,"S",true) and `)
    code_match = re.search(r'setDealerCode\(\s*`\s*(.*?)\s*`\s*(?:,\s*"|[)])', content, re.DOTALL)
    if code_match:
        dealer_code = code_match.group(1)

        # Remove the auction-filter/convention-card comment block from dealer code
        dealer_code = re.sub(r'/\*\s*\n(?:convention-card(?:-ns|-ew)?:.*?\n)*(?:auction-filter:.*?\n)?\*/', '', dealer_code)

        # Also remove # convention-card-ns/ew: and # auction-filter: comment lines
        dealer_code = re.sub(r'^#\s*convention-card(?:-ns|-ew)?:.*\n?', '', dealer_code, flags=re.MULTILINE)
        dealer_code = re.sub(r'^#\s*auction-filter:.*\n?', '', dealer_code, flags=re.MULTILINE)

        dealer_code = dealer_code.strip()

        result['dealer_code'] = dealer_code

    # Extract button text and chat from Button line(s)
    # Format: Button,{button_text},\n\
    #         {chat_line1}\n\
    #         {chat_line2}\n\
    #         %{alias}%
    # First find where Button starts and extract everything until %alias%
    alias = result['alias'] or ''
    button_pattern = rf'Button,([^,]+),(.*?)%{re.escape(alias)}%'
    button_match = re.search(button_pattern, content, re.DOTALL)
    if button_match:
        result['button_text'] = button_match.group(1)
        button_content = button_match.group(2)

        # The button content has \n\ at end of each line, followed by actual newline
        # Remove actual newlines and then split by \n\
        button_content = button_content.replace('\n', '')

        # Now split by \n\ to get chat lines
        if button_content.startswith('\\n\\'):
            button_content = button_content[3:]  # Remove leading \n\

        if button_content.endswith('\\n\\'):
            button_content = button_content[:-3]  # Remove trailing \n\

        chat_lines = button_content.split('\\n\\')
        # Convert wide commas back to regular commas
        chat_lines = [line.replace('，', ', ') for line in chat_lines]
        result['chat'] = '\n'.join(chat_lines)

    return result


def convert_imports_to_includes(dealer_code: str) -> str:
    """
    Convert Import,URL statements back to #include "path" directives.
    """
    def replace_import(match):
        path = match.group(1)
        return f'#include "{path}"'

    return re.sub(GITHUB_SCRIPT_PATTERN, replace_import, dealer_code)


def generate_btn(parsed: dict) -> str:
    """
    Generate BTN file content from parsed PBS data.
    """
    alias = parsed['alias'] or 'Unknown'
    button_text = parsed['button_text'] or alias
    dealer_position = parsed['dealer_position'] or 'S'

    # Map position initial to full name for dealer statement
    position_names = {'S': 'south', 'N': 'north', 'E': 'east', 'W': 'west'}

    lines = []

    # Metadata comments
    lines.append(f"# alias: {alias}")
    lines.append(f"# button-text: {button_text}")
    lines.append("# gib-works: true")
    lines.append("# bba-works: true")
    if parsed['auction_filter']:
        lines.append(f"# auction-filter: {parsed['auction_filter']}")
    if parsed['convention_card_ns']:
        lines.append(f"# convention-card-ns: {parsed['convention_card_ns']}")
    if parsed['convention_card_ew']:
        lines.append(f"# convention-card-ew: {parsed['convention_card_ew']}")

    lines.append("")

    # Chat block
    if parsed['chat']:
        lines.append("/*@chat")
        lines.append(parsed['chat'])
        lines.append("@chat*/")
        lines.append("")

    # Dealer statement
    lines.append(f"dealer {position_names.get(dealer_position, 'south')}")

    # Dealer code with #include directives
    dealer_code = parsed['dealer_code'] or ''
    dealer_code = convert_imports_to_includes(dealer_code)
    lines.append(dealer_code)

    lines.append("")

    return '\n'.join(lines)


def convert_pbs_to_btn(scenario: str, verbose: bool = True) -> bool:
    """
    Convert a PBS file to BTN format.

    PBS/{scenario} -> btn/{scenario}.btn

    Args:
        scenario: Scenario name (e.g., "Smolen")
        verbose: Whether to print progress

    Returns:
        True if successful, False otherwise
    """
    pbs_path = os.path.join(FOLDERS["pbs"], scenario)

    if not os.path.exists(pbs_path):
        print(f"Error: PBS file not found: {pbs_path}")
        return False

    if verbose:
        print(f"Converting: {scenario}")

    try:
        # Parse PBS file
        parsed = parse_pbs_file(pbs_path)

        # Generate BTN content
        btn_content = generate_btn(parsed)

        # Write BTN file
        os.makedirs(FOLDERS["btn"], exist_ok=True)
        btn_path = os.path.join(FOLDERS["btn"], f"{scenario}.btn")

        with open(btn_path, 'w', encoding='utf-8') as f:
            f.write(btn_content)

        if verbose:
            print(f"  Created: {btn_path}")

        return True

    except Exception as e:
        print(f"Error converting {scenario}: {e}")
        return False


def get_all_scenarios() -> list:
    """Get list of all PBS scenarios."""
    pbs_dir = FOLDERS["pbs"]
    scenarios = []
    for f in os.listdir(pbs_dir):
        # Skip hidden files and files with extensions
        if not f.startswith(".") and "." not in f:
            scenarios.append(f)
    return sorted(scenarios)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python pbs_to_btn.py <scenario>   # Convert specific scenario")
        print("  python pbs_to_btn.py --all        # Convert all PBS files")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--all":
        scenarios = get_all_scenarios()
        print(f"Converting {len(scenarios)} PBS files to BTN format...\n")

        success_count = 0
        fail_count = 0

        for scenario in scenarios:
            if convert_pbs_to_btn(scenario):
                success_count += 1
            else:
                fail_count += 1

        print(f"\nDone: {success_count} succeeded, {fail_count} failed")
    else:
        scenario = arg
        success = convert_pbs_to_btn(scenario)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
