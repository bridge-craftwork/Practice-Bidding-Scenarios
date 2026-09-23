#!/usr/bin/env python3
"""Convert a PBN file to PDF with 5 hands per page, bidding, and double-dummy analysis."""

import re
import os
import sys
import subprocess
import tempfile

# Path to tools
BRIDGE_WRANGLER = "/Applications/Bridge Utilities/bridge-wrangler"
BRIDGE_SOLVER = "/Applications/Bridge Utilities/bridge-solver"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

SUIT_HTML = {
    'S': '<span class="s">&spades;</span>',
    'H': '<span class="h">&hearts;</span>',
    'D': '<span class="d">&diams;</span>',
    'C': '<span class="c">&clubs;</span>',
}


def parse_deal(deal_str):
    """Parse PBN deal string into dict of hands {N/E/S/W: [spades, hearts, diamonds, clubs]}."""
    # Format: "N:A64.9.QJT862.J87 QT3.J82.AK54.542 J9875.A7643.3.K9 K2.KQT5.97.AQT63"
    first_seat = deal_str[0]
    hands_str = deal_str[2:]
    hands_raw = hands_str.split()
    seat_order = ['N', 'E', 'S', 'W']
    start = seat_order.index(first_seat)
    hands = {}
    for i, raw in enumerate(hands_raw):
        seat = seat_order[(start + i) % 4]
        suits = raw.split('.')
        # Pad to 4 suits if needed
        while len(suits) < 4:
            suits.append('')
        hands[seat] = suits  # [spades, hearts, diamonds, clubs]
    return hands


def parse_optimum_table(block):
    """Read a board's double-dummy table as {seat: {strain: tricks}}.

    Two shapes are on disk, and both are read here.

    The conforming PBN 2.1 table section (5.7), which bridge-wrangler and
    Bridge Composer write, is a header naming the columns followed by one
    line per cell:

        [OptimumResultTable "Declarer;Denomination\\2R;Result\\1R"]
        N NT 10
        N  S  9

    Older bridge-wrangler builds packed the whole table into the tag value
    instead, with escaped newlines and tabs and the strains in a positional
    header row:

        [OptimumResultTable "NT\\tS\\tH\\tD\\tC\\nN\\t7\\t6\\t7\\t6\\t6\\n..."]

    Returns None when the board carries no table, or when one is there but
    no row could be read from it.
    """
    m = re.search(r'\[OptimumResultTable "([^"]*)"\]', block)
    if not m:
        return None

    header = m.group(1)
    # The legacy form carries the data in the tag value itself.
    if '\\n' in header or '\\t' in header:
        return parse_legacy_optimum_table(header)

    # The conforming form names its columns; find which one holds the seat,
    # the denomination and the trick count, rather than assuming an order.
    # Each column may carry a format specifier after a backslash ("Result\\2R").
    columns = [c.split('\\')[0].strip() for c in header.split(';')]
    try:
        seat_col = columns.index('Declarer')
        strain_col = columns.index('Denomination')
        tricks_col = columns.index('Result')
    except ValueError:
        return None

    result = {}
    # The rows are the lines after the tag's own line, up to the next tag or a
    # blank line.
    _, _, rest = block[m.end():].partition('\n')
    for line in rest.splitlines():
        if not line.strip():
            break
        if line.lstrip().startswith('['):
            break
        fields = line.split()
        if len(fields) <= max(seat_col, strain_col, tricks_col):
            continue
        result.setdefault(fields[seat_col], {})[fields[strain_col]] = fields[tricks_col]

    return result or None


def parse_legacy_optimum_table(table_str):
    """Read the pre-2026 table, packed into the tag value.

    The header row names the strains and each later row is a seat followed by
    its trick counts in that order. Tabs and newlines may be written as escape
    sequences or as the characters themselves, so both are normalized first.
    """
    text = table_str.replace('\\t', '\t').replace('\\n', '\n')
    lines = [line for line in text.split('\n') if line.strip()]
    if len(lines) < 2:
        return None

    strains = lines[0].split()
    result = {}
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < len(strains) + 1:
            continue
        seat = parts[0]
        result[seat] = {strain: parts[i + 1] for i, strain in enumerate(strains)}

    return result or None


def parse_auction(auction_text, dealer):
    """Parse auction text into list of bids, starting from dealer."""
    # Remove comments {}, alerts =...=
    text = re.sub(r'\{[^}]*\}', '', auction_text)
    text = re.sub(r'=[^=]*=', '', text)
    bids = text.split()
    # Filter out empty strings
    bids = [b for b in bids if b.strip()]
    return bids


def parse_pbn(content):
    """Parse PBN file content into list of board dicts."""
    boards = []
    # Split on blank-line-separated blocks that start with [Event
    blocks = re.split(r'\n\s*\n(?=\[Event )', content)

    for block in blocks:
        if '[Event' not in block:
            continue

        board = {}
        board_m = re.search(r'\[Board "([^"]+)"\]', block)
        board['number'] = board_m.group(1) if board_m else '?'

        dealer_m = re.search(r'\[Dealer "([^"]+)"\]', block)
        board['dealer'] = dealer_m.group(1) if dealer_m else '?'

        vul_m = re.search(r'\[Vulnerable "([^"]+)"\]', block)
        board['vul'] = vul_m.group(1) if vul_m else '?'

        deal_m = re.search(r'\[Deal "([^"]+)"\]', block)
        board['hands'] = parse_deal(deal_m.group(1)) if deal_m else {}

        contract_m = re.search(r'\[Contract "([^"]+)"\]', block)
        board['contract'] = contract_m.group(1) if contract_m else '?'

        declarer_m = re.search(r'\[Declarer "([^"]+)"\]', block)
        board['declarer'] = declarer_m.group(1) if declarer_m else '?'

        board['dd'] = parse_optimum_table(block)

        # Parse HCP from comment
        hcp_m = re.search(r'\{HCP\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\}', block)
        if hcp_m:
            board['hcp'] = {
                'N': hcp_m.group(1), 'E': hcp_m.group(2),
                'S': hcp_m.group(3), 'W': hcp_m.group(4)
            }
        else:
            board['hcp'] = {}

        # Parse auction
        auction_m = re.search(r'\[Auction "([^"]+)"\]\s*\n(.*?)(?=\n\s*\n|\n\[|\Z)', block, re.DOTALL)
        if auction_m:
            board['auction_dealer'] = auction_m.group(1)
            board['bids'] = parse_auction(auction_m.group(2), auction_m.group(1))
        else:
            board['auction_dealer'] = board['dealer']
            board['bids'] = []

        boards.append(board)

    return boards


def format_cards(cards):
    """Format a suit's cards, showing '-' for void."""
    return cards if cards else '&mdash;'


def suit_html(suit_idx):
    """Return HTML for a suit symbol by index (0=S, 1=H, 2=D, 3=C)."""
    return [SUIT_HTML['S'], SUIT_HTML['H'], SUIT_HTML['D'], SUIT_HTML['C']][suit_idx]


def format_bid(bid):
    """Format a bid with suit symbols."""
    if bid.upper() in ('PASS', 'P'):
        return 'Pass'
    if bid.upper() in ('X', 'DBL', 'DOUBLE'):
        return 'Dbl'
    if bid.upper() in ('XX', 'RDBL', 'REDOUBLE'):
        return 'Rdbl'
    if bid == 'AP':
        return 'AP'
    # Match digit + suit letter
    m = re.match(r'(\d)(NT|N|S|H|D|C)', bid, re.IGNORECASE)
    if m:
        level = m.group(1)
        strain = m.group(2).upper()
        if strain in ('NT', 'N'):
            return f'{level}NT'
        return f'{level}{SUIT_HTML[strain]}'
    return bid


def render_compass(hands):
    """Render 4 hands in compass layout as HTML table."""
    html = '<table class="compass">'

    # North hand (centered)
    html += '<tr><td></td><td class="hand north">'
    for i in range(4):
        html += f'{suit_html(i)} {format_cards(hands["N"][i])}<br>'
    html += '</td><td></td></tr>'

    # West and East side by side
    html += '<tr><td class="hand west">'
    for i in range(4):
        html += f'{suit_html(i)} {format_cards(hands["W"][i])}<br>'
    html += '</td><td></td><td class="hand east">'
    for i in range(4):
        html += f'{suit_html(i)} {format_cards(hands["E"][i])}<br>'
    html += '</td></tr>'

    # South hand (centered)
    html += '<tr><td></td><td class="hand south">'
    for i in range(4):
        html += f'{suit_html(i)} {format_cards(hands["S"][i])}<br>'
    html += '</td><td></td></tr>'

    html += '</table>'
    return html


def render_auction(bids, auction_dealer):
    """Render bidding auction as 4-column HTML table."""
    seat_order = ['W', 'N', 'E', 'S']
    start_idx = seat_order.index(auction_dealer)

    html = '<table class="auction">'
    html += '<tr class="auction-header"><td>W</td><td>N</td><td>E</td><td>S</td></tr>'

    # Add empty cells before dealer
    row = [''] * start_idx
    for bid in bids:
        row.append(format_bid(bid))
        if len(row) == 4:
            html += '<tr>'
            for cell in row:
                html += f'<td>{cell}</td>'
            html += '</tr>'
            row = []

    # Flush remaining bids
    if row:
        while len(row) < 4:
            row.append('')
        html += '<tr>'
        for cell in row:
            html += f'<td>{cell}</td>'
        html += '</tr>'

    html += '</table>'
    return html


def render_dd_table(dd):
    """Render double-dummy analysis as HTML table."""
    if not dd:
        return '<div class="dd-none">No DD data</div>'

    html = '<table class="dd">'
    html += f'<tr class="dd-header"><td></td><td>NT</td>'
    html += f'<td>{SUIT_HTML["S"]}</td><td>{SUIT_HTML["H"]}</td>'
    html += f'<td>{SUIT_HTML["D"]}</td><td>{SUIT_HTML["C"]}</td></tr>'

    for seat in ['N', 'S', 'E', 'W']:
        if seat in dd:
            html += f'<tr><td class="dd-seat">{seat}</td>'
            for strain in ['NT', 'S', 'H', 'D', 'C']:
                tricks = dd[seat].get(strain, '')
                html += f'<td>{tricks}</td>'
            html += '</tr>'

    html += '</table>'
    return html


def render_board(board):
    """Render a single board as HTML."""
    contract_str = board['contract']
    if contract_str not in ('--', '?', 'Pass'):
        # Format contract with suit symbol
        m = re.match(r'(\d)(NT|N|S|H|D|C)(.*)', contract_str, re.IGNORECASE)
        if m:
            level = m.group(1)
            strain = m.group(2).upper()
            suffix = m.group(3)
            if strain in ('NT', 'N'):
                contract_display = f'{level}NT{suffix}'
            else:
                contract_display = f'{level}{SUIT_HTML[strain]}{suffix}'
        else:
            contract_display = contract_str
        declarer = board['declarer']
        contract_line = f'{contract_display} by {declarer}' if declarer != '?' else contract_display
    elif contract_str == 'Pass' or contract_str == '--':
        contract_line = 'Passed Out'
    else:
        contract_line = ''

    # HCP display
    hcp = board.get('hcp', {})
    hcp_str = ''
    if hcp:
        hcp_str = f"HCP: N={hcp.get('N','')} S={hcp.get('S','')} E={hcp.get('E','')} W={hcp.get('W','')}"

    html = '<div class="board">'
    html += '<div class="board-header">'
    html += f'<span class="board-num">Board {board["number"]}</span>'
    html += f'<span class="board-info">Dlr: {board["dealer"]} &bull; Vul: {board["vul"]}</span>'
    if contract_line:
        html += f'<span class="board-contract">Contract: {contract_line}</span>'
    html += '</div>'

    html += '<div class="board-body">'
    html += '<div class="compass-col">'
    html += render_compass(board['hands'])
    html += '</div>'
    html += '<div class="auction-col">'
    html += render_auction(board['bids'], board['auction_dealer'])
    html += '</div>'
    html += '<div class="dd-col">'
    html += render_dd_table(board['dd'])
    html += '</div>'
    html += '</div>'

    if hcp_str:
        html += f'<div class="hcp-line">{hcp_str}</div>'

    html += '</div>'
    return html


def generate_html(boards, title):
    """Generate complete HTML document."""
    css = """
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
        font-family: "Times New Roman", serif;
        font-size: 11pt;
        color: #000;
        padding: 10px 20px;
    }
    html { -webkit-print-color-adjust: exact; }

    .page-title {
        font: bold 14pt Verdana, sans-serif;
        text-align: center;
        margin-bottom: 10px;
        padding: 4px 0;
        border-bottom: 2px solid #999;
    }

    .board {
        border: 1px solid #aaa;
        margin-bottom: 8px;
        padding: 6px 10px;
        background: #fff;
    }
    .board:nth-child(even) {
        background: #f5f5f5;
    }

    .board-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #ccc;
        padding-bottom: 3px;
        margin-bottom: 4px;
        font: bold 11pt Verdana, sans-serif;
    }
    .board-num {
        color: #1a5276;
    }
    .board-info {
        color: #555;
    }
    .board-contract {
        color: #922;
    }

    .board-body {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
    }

    .compass-col {
        flex: 0 0 auto;
    }
    .auction-col {
        flex: 0 0 auto;
    }
    .dd-col {
        flex: 0 0 auto;
    }

    /* Compass hand diagram */
    table.compass {
        border-collapse: collapse;
        font-size: 11pt;
        line-height: 1.25;
    }
    table.compass td {
        padding: 0 2px;
        vertical-align: top;
        white-space: nowrap;
    }
    td.hand {
        font-family: "Courier New", monospace;
        font-size: 11pt;
    }
    td.north, td.south {
        padding-left: 24px;
    }
    td.west {
        padding-right: 14px;
    }
    td.east {
        padding-left: 14px;
    }

    /* Auction table */
    table.auction {
        border-collapse: collapse;
        font-size: 11pt;
    }
    table.auction td {
        padding: 1px 6px;
        text-align: center;
        min-width: 32px;
    }
    tr.auction-header td {
        font-weight: bold;
        border-bottom: 1px solid #999;
        padding-bottom: 2px;
    }

    /* DD table */
    table.dd {
        border-collapse: collapse;
        font-size: 11pt;
    }
    table.dd td {
        padding: 1px 5px;
        text-align: center;
        min-width: 22px;
    }
    tr.dd-header td {
        font-weight: bold;
        border-bottom: 1px solid #999;
        padding-bottom: 2px;
    }
    td.dd-seat {
        font-weight: bold;
        text-align: left;
    }

    .hcp-line {
        font-size: 9pt;
        color: #666;
        text-align: right;
        margin-top: 2px;
    }

    /* Suit colors */
    .s { color: #000; }  /* spades */
    .h { color: #cc0000; }  /* hearts */
    .d { color: #cc6600; }  /* diamonds */
    .c { color: #006600; }  /* clubs */
    """

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{css}</style>
</head>
<body>
"""

    html += f'<div class="page-title">{title}</div>'
    for board in boards:
        html += render_board(board)

    html += '</body></html>'
    return html


def ensure_dd_analysis(pbn_path):
    """Solve the file if it lacks DD data. Returns the path to use.

    bridge-solver owns double dummy: bridge-wrangler had an `analyze` until its
    v0.11.0, and it was removed rather than kept as a slower second
    implementation. A file the pipeline produced is already solved by then, so
    this is the path for a one-off PBN handed to this script directly.
    """
    with open(pbn_path, 'r') as f:
        content = f.read()

    if '[OptimumResultTable' in content:
        return pbn_path

    analyzed_path = pbn_path.replace('.pbn', '-analyzed.pbn')
    print(f"Running double-dummy analysis...")
    result = subprocess.run(
        [BRIDGE_SOLVER, '-i', pbn_path, '-o', analyzed_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Warning: DD analysis failed: {result.stderr}")
        return pbn_path
    print(f"Analysis complete: {analyzed_path}")
    return analyzed_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 pbn-to-pdf.py <input.pbn> [output.pdf]")
        sys.exit(1)

    input_path = os.path.expanduser(sys.argv[1])
    if not os.path.exists(input_path):
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_path = os.path.expanduser(sys.argv[2])
    else:
        output_path = os.path.splitext(input_path)[0] + '.html'

    # Ensure DD analysis exists
    analyzed_path = ensure_dd_analysis(input_path)

    # Parse PBN
    with open(analyzed_path, 'r') as f:
        content = f.read()
    boards = parse_pbn(content)
    print(f"Parsed {len(boards)} boards")

    # Generate title from filename
    title = os.path.splitext(os.path.basename(input_path))[0]

    # Generate HTML
    html = generate_html(boards, title)

    # Write HTML
    with open(output_path, 'w') as f:
        f.write(html)

    print(f"HTML written to {output_path}")

    # Open in browser
    subprocess.run(['open', output_path])


if __name__ == '__main__':
    main()
