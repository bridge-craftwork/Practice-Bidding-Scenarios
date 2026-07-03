#!/usr/bin/env python3
"""play_line.py — generate a double-dummy defensive play line for declarer-play
coaching boards, emitted as a PBN [Play] section that Bridge Classroom replays.

Why this exists
---------------
BC's coaching flow can now play a declarer hand interactively (student declares
S + dummy N; the two defenders are driven by the engine). BC has no local
double-dummy solver — it only fetches a DD *table* over HTTP — so it cannot work
out the defenders' cards on its own. We compute the line HERE, at build time,
where a real DD engine (endplay/DDS) is already available, and ship it in the
served PBN as a recorded [Play] section. BC just replays each defender's card.

The line
--------
* West's OPENING LEAD is forced to the card named in the board's
  [ROLE leader][STAGE pre-lead] tip ("Lead the \\H8" -> H8). That is the lead the
  lesson teaches — usually NOT the DD-best lead (fourth-best vs a hold-up, etc.).
* Every card AFTER the opening lead is DD-optimal for whoever is on play. Because
  these lessons teach the DD-winning declarer line, the model declarer play the
  solver picks matches the coaching (e.g. Hold_Up_3N: South ducks trick 1).

Columns are fixed directions per the PBN standard: [Play "<leader>"] with rows =
tricks, four cards per row in clockwise order starting from <leader>. That lets
BC build a simple per-seat queue (column -> seat) and dequeue a defender's next
card whenever it is their turn — no trick-order bookkeeping needed for replay.

CLI
---
    python3 -P py/play_line.py <Scenario> [--check] [--only N]

Without --check it rewrites coaching-non-rotated/<Scenario>.pbn in place,
injecting (or refreshing) a [Play] section on every declarer-play board. --check
prints the sections it would write and touches nothing. --only N restricts to
the board at display index N (1-based).
"""
import argparse
import re
import sys
from pathlib import Path

from endplay.types import Deal, Player, Denom, Card

ROOT = Path(__file__).resolve().parent.parent
SERVED = ROOT / "coaching-non-rotated"

SEAT = {Player.north: "N", Player.east: "E", Player.south: "S", Player.west: "W"}
LEADER_OF = {"N": "E", "E": "S", "S": "W", "W": "N"}  # opening leader = LHO of declarer
CLOCKWISE = {"N": "E", "E": "S", "S": "W", "W": "N"}
STRAIN = {"N": Denom.nt, "S": Denom.spades, "H": Denom.hearts, "D": Denom.diamonds, "C": Denom.clubs}
PLAYER_OF = {"N": Player.north, "E": Player.east, "S": Player.south, "W": Player.west}


def contract_strain(contract):
    """'3N' -> Denom.nt, '4S' -> Denom.spades, '4NT' -> Denom.nt."""
    c = contract.upper().replace("NT", "N")
    return STRAIN[c[1]]


def lead_card_from_tip(comment):
    r"""Pull the opening-lead card from the leader pre-lead tip.

    The tip reads e.g. 'Lead the \H8.' — suit letter is backslash-escaped in the
    served prose; rank follows. Returns a 2-char code like 'H8' (T for tens), or
    None if no tip is present.
    """
    m = re.search(r"Lead the\s+\\?([SHDC])\s*(10|[2-9TJQKA])", comment)
    if not m:
        return None
    suit, rank = m.group(1), m.group(2)
    if rank == "10":
        rank = "T"
    return suit + rank


def generate_play_line(deal_str, contract, declarer, lead_code):
    """Return (leader, tricks) where tricks is a list of 4-tuples of card strings
    in fixed clockwise column order [leader, +1, +2, +3]. Cards use PBN letters
    (e.g. 'H8', 'ST'). Opening lead forced to lead_code; rest DD-optimal.
    """
    leader = LEADER_OF[declarer]
    d = Deal(deal_str)
    d.trump = contract_strain(contract)
    d.first = PLAYER_OF[leader]

    forced = Card(lead_code)  # endplay Card uses 'T' notation, matching lead_code
    from endplay.dds import solve_board

    chrono = []  # [(seat, Card)] in actual play order
    for i in range(52):
        seat = SEAT[d.curplayer]
        if i == 0:
            card = forced
        else:
            sb = solve_board(d)
            card = max(sb, key=lambda kv: kv[1])[0]
        chrono.append((seat, card))
        d.play(card)

    # Fold chronological plays into fixed-direction columns, one row per trick.
    col_order = [leader]
    for _ in range(3):
        col_order.append(CLOCKWISE[col_order[-1]])
    tricks = []
    for t in range(13):
        by_seat = {seat: card for seat, card in chrono[t * 4:t * 4 + 4]}
        tricks.append(tuple(_pbn(by_seat[s]) for s in col_order))
    return leader, tricks


def _pbn(card):
    """Card -> 'H8' style code (rank letter, T for ten)."""
    suit = card.suit.name[0].upper()  # spades/hearts/diamonds/clubs -> S/H/D/C
    rank = card.rank.name[1:]         # Rank.R8 -> '8', Rank.RT -> 'T'
    return suit + rank


def render_play_section(leader, tricks):
    lines = [f'[Play "{leader}"]']
    for trick in tricks:
        lines.append(" ".join(trick))
    return "\n".join(lines)


# ── PBN board splitting ──────────────────────────────────────────────────────

def split_boards(text):
    """Split a coaching PBN into (preamble, [board_text, ...]). A board starts at
    an [Event ...] tag."""
    parts = re.split(r"(?m)(?=^\[Event )", text)
    if parts and not parts[0].startswith("[Event "):
        return parts[0], parts[1:]
    return "", parts


def tag(board, name):
    m = re.search(rf'(?m)^\[{name} "([^"]*)"\]', board)
    return m.group(1) if m else None


def is_declarer_board(board):
    return "[ROLE declarer]" in board and tag(board, "Contract") not in (None, "Pass")


def inject_play(board, section):
    """Insert/replace the [Play] section immediately before the trailing coaching
    comment (the '{' block). Idempotent: an existing [Play ...] block is removed
    first."""
    # Strip a prior [Play] table: the header plus the trick rows that follow it.
    # Rows start with a suit letter (S/H/D/C); this must NOT consume the trailing
    # {…} coaching comment (which begins with '{'), so anchor rows on [SHDC].
    board = re.sub(r'(?m)^\[Play "[^"]*"\]\n(?:[SHDC][^\n]*\n)*', "", board)
    idx = board.find("{")
    if idx == -1:
        return board.rstrip() + "\n" + section + "\n"
    return board[:idx] + section + "\n" + board[idx:]


def process(scn, check=False, only=None):
    path = SERVED / f"{scn}.pbn"
    if not path.exists():
        sys.exit(f"no served file: {path}")
    text = path.read_text()
    preamble, boards = split_boards(text)
    out = [preamble] if preamble else []
    n_written = 0
    display = 0
    for board in boards:
        if not is_declarer_board(board):
            out.append(board)
            continue
        display += 1
        if only is not None and display != only:
            out.append(board)
            continue
        deal_str = tag(board, "Deal")
        contract = tag(board, "Contract")
        declarer = tag(board, "Declarer")
        lead = lead_card_from_tip(board)
        if not (deal_str and contract and declarer):
            out.append(board)
            continue
        if not lead:
            print(f"  board {display}: no pre-lead tip — skipped", file=sys.stderr)
            out.append(board)
            continue
        try:
            leader, tricks = generate_play_line(deal_str, contract, declarer, lead)
        except Exception as e:  # one bad board must not abort the scenario
            print(f"  board {display}: play-line generation failed ({e!r}) — skipped", file=sys.stderr)
            out.append(board)
            continue
        section = render_play_section(leader, tricks)
        n_written += 1
        if check:
            print(f"=== board {display} (Contract {contract} by {declarer}, lead {lead}) ===")
            print(section)
            out.append(board)
        else:
            out.append(inject_play(board, section))
    if not check:
        path.write_text("".join(out))
    print(f"{scn}: {'would write' if check else 'wrote'} {n_written} [Play] section(s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenario")
    ap.add_argument("--check", action="store_true", help="dry run; print sections")
    ap.add_argument("--only", type=int, metavar="N", help="only board at display index N (1-based)")
    args = ap.parse_args()
    process(args.scenario, check=args.check, only=args.only)


if __name__ == "__main__":
    main()
