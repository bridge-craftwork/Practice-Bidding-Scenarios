"""
The dealer script BBO receives, read out of a .dlr file.

Everything that hands a scenario to BBO strips the .dlr the same way:
  - the BBO extension's loader (dealerFromDlr in pbs-bbo-extension's
    runtime/pbsDynamicLayout.js, a JavaScript port of this file;
    tools/check-dlr-strip.mjs there compares the two);
  - py/gib_capture.py, which gives the script straight to setDealerCode;
  - py/build_manifest.py, which takes the button text and chat from the header.

This used to be the core of the `pbs` operation, which wrapped the result in a
.pbs file. That operation is gone (issue #321); the extension now fetches
dlr/<name>.dlr itself.

Pure stdlib, so py/build_manifest.py can import it in GitHub Actions.
"""
import re


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
            # Skip the dealer statement (the seat goes to setDealerCode separately)
            if re.match(r'^dealer\s+(south|north|east|west)', line.strip()):
                continue
            if line.strip() == '':
                continue
            past_header = True

        dealer_lines.append(line)

    result['dealer_code'] = '\n'.join(dealer_lines)

    return result


def bbo_dealer_code(dlr_content: str, parsed: dict = None) -> tuple:
    """
    The dealer script exactly as BBO's Deal Source box receives it, and the
    dealer seat to pass alongside it: the first two arguments of
    setDealerCode(code, seat, true).

    Returns:
        (dealer_code, dealer_position)
    """
    if parsed is None:
        parsed = parse_dlr_file(dlr_content)

    # Dealer code is already expanded in the DLR (includes inlined)
    dealer_code = parsed['dealer_code']

    # Remove "action printpbn" line - BBO doesn't want it
    dealer_code = re.sub(r'\n*action\s+printpbn\s*\n*', '\n', dealer_code)

    lines = []

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

    return '\n'.join(lines), parsed['dealer_position'] or 'S'
