"""
Quiz operation: Generate quiz sets from filtered BBA files.

Analyzes auction frequencies and creates varied quiz sets for each
bidding decision point where multiple bids occur with >5% frequency.

REQUIREMENTS:
=============

1. INPUT/OUTPUT:
   - Read the filtered-in PBN file (bba-filtered/{scenario}.pbn)
   - Output quiz PBN and PDF to /quiz folder

2. PARAMETERS:
   - num_per_quiz: Number of hands per quiz set (default: 6)
   - min_frequency: Minimum bid frequency to include (default: 5%)

3. AUCTION ANALYSIS:
   - Analyze auction frequencies at each decision level
   - Cycle through opener and responder decision points
   - Skip levels where only one bid occurs (no decision to make)
   - Skip bids with <5% frequency (too rare to quiz)

4. QUIZ GENERATION ALGORITHM:
   a) Start with opening bid level
      - Count frequency of each opening bid
      - If only one opening (e.g., all 1NT), skip this level
      - Otherwise, create a quiz with varied opening hands

   b) Move to responder's first bid
      - After common opening, count response frequencies
      - Example: After 1NT, responses might be Pass (6%) or 2C (94%)
      - Since both are >5%, create quiz: "Partner opens 1NT. What do you bid?"

   c) Return to opener's rebid
      - After 1NT-Pass-2C, count opener's rebids (2D, 2H, 2S)
      - Quiz: "You open 1NT and partner responds 2C, what do you bid?"

   d) Continue alternating until auctions conclude
      - Skip opponent bids (we only quiz our side's decisions)
      - Skip terminal positions (all remaining bids are Pass)

5. HAND SELECTION FOR EACH QUIZ:
   - Try for equal distribution of correct answers
   - Maximize variety in the remaining auction after the quizzed bid
   - Select from different continuations to show range of possibilities

6. QUIZ PROMPTS:
   - For responder: "Partner opens {bid}. What do you bid?"
   - For opener rebid: "You open {bid}, partner responds {bid}. What do you bid?"
   - Include full auction context as it builds

7. OUTPUT FORMAT (Console for now):
   - Show auction prefix and bid distribution
   - Display 6 hands with suit symbols
   - Show correct answer and full auction for each hand
"""
import copy
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date
from typing import Dict, List, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FOLDERS, MAC_TOOLS, PIPELINE_VERSION, PROJECT_ROOT


class Hand:
    """Represents a bridge hand with cards and auction."""
    def __init__(self, board_num: int, dealer: str, hands: Dict[str, str], auction: List[str],
                 vulnerable: str = 'None', board_token: Optional[str] = None):
        self.board_num = board_num
        self.dealer = dealer  # N, E, S, W
        self.hands = hands    # {'N': 'xxx.xxx.xxx.xxx', 'S': '...', etc}
        self.auction = auction  # ['1N', 'Pass', '2C', 'Pass', '2D', ...]
        self.vulnerable = vulnerable    # PBN [Vulnerable]: None, NS, EW, All
        self.board_token = board_token  # rotation-independent board-version token (ADR-0001)

    def get_auction_at_level(self, level: int) -> List[str]:
        """Get auction up to and including the specified bid level (0-indexed)."""
        return self.auction[:level + 1]

    def get_bid_at_level(self, level: int) -> Optional[str]:
        """Get the bid at the specified level (0-indexed)."""
        if level < len(self.auction):
            return self.auction[level]
        return None

    def __repr__(self):
        return f"Hand({self.board_num}, {self.auction})"


def parse_pbn_file(pbn_path: str) -> List[Hand]:
    """Parse a PBN file and extract hands with auctions."""
    hands = []

    with open(pbn_path, 'r') as f:
        content = f.read()

    # Split into boards
    boards = re.split(r'\[Event ', content)[1:]

    for board_text in boards:
        try:
            # Extract board number
            board_match = re.search(r'\[Board "(\d+)"\]', board_text)
            board_num = int(board_match.group(1)) if board_match else 0

            # Extract dealer
            dealer_match = re.search(r'\[Dealer "([NESW])"\]', board_text)
            dealer = dealer_match.group(1) if dealer_match else 'S'

            # Extract vulnerability
            vul_match = re.search(r'\[Vulnerable "([^"]*)"\]', board_text)
            vulnerable = vul_match.group(1) if vul_match else 'None'

            # Extract the board-version token bba-cli stamps as a bare % comment
            # right after [Board]. Opaque, rotation-independent (ADR-0001).
            token_match = re.search(r'^%\s*([0-9A-F]{16,})\s*$', board_text, re.MULTILINE)
            board_token = token_match.group(1) if token_match else None

            # Extract deal
            deal_match = re.search(r'\[Deal "([^"]+)"\]', board_text)
            if not deal_match:
                continue
            deal_str = deal_match.group(1)

            # Parse deal string like "S:xxx.xxx.xxx.xxx xxx.xxx.xxx.xxx ..."
            # Format is "first_seat:hand hand hand hand" going clockwise
            deal_parts = deal_str.split(':')
            first_seat = deal_parts[0]
            hand_strs = deal_parts[1].split()

            # Map seats in clockwise order from first_seat
            seat_order = ['N', 'E', 'S', 'W']
            start_idx = seat_order.index(first_seat)
            hands_dict = {}
            for i, hand_str in enumerate(hand_strs):
                seat = seat_order[(start_idx + i) % 4]
                hands_dict[seat] = hand_str

            # Extract auction
            auction_match = re.search(r'\[Auction "[NESW]"\]\n(.*?)(?=\n\[|\Z)', board_text, re.DOTALL)
            if not auction_match:
                continue

            auction_text = auction_match.group(1)
            # Clean up auction - remove comments and alerts
            auction_text = re.sub(r'\{[^}]*\}', '', auction_text)  # Remove {comments}
            auction_text = re.sub(r'=[^=]*=', '', auction_text)    # Remove =alerts=

            # Parse bids
            auction = []
            for bid in auction_text.split():
                bid = bid.strip()
                if bid and bid not in ['', '*']:
                    # Normalize bid names
                    bid = bid.replace('NT', 'N')
                    auction.append(bid)

            if auction:
                hands.append(Hand(board_num, dealer, hands_dict, auction,
                                  vulnerable=vulnerable, board_token=board_token))

        except Exception as e:
            # Skip malformed boards
            continue

    return hands


SEAT_ORDER = ['N', 'E', 'S', 'W']
OUR_SIDE = ('N', 'S')

# The student's hand is always rendered in the South position, so display-space
# seats are keyed off South regardless of where the hand really sits.
STUDENT_DISPLAY_SEAT = 'S'


def seat_at_level(dealer: str, level: int) -> str:
    """
    The seat that makes the call at `level` of the auction.

    Level 0 is the dealer and play proceeds clockwise. Scenario files deal from
    every seat - 1C_WalshStyle deals N, Basic_Overcall deals E - so the seat has
    to be derived from the board's own dealer rather than assumed to be South.
    """
    if dealer not in SEAT_ORDER:
        dealer = 'S'
    return SEAT_ORDER[(SEAT_ORDER.index(dealer) + level) % 4]


def partner_of(seat: str) -> str:
    return SEAT_ORDER[(SEAT_ORDER.index(seat) + 2) % 4]


def relative_role(quizzed_seat: str, seat: str) -> str:
    """Describe `seat` from the quizzed seat's point of view."""
    offset = (SEAT_ORDER.index(seat) - SEAT_ORDER.index(quizzed_seat)) % 4
    return ('you', 'lho', 'partner', 'rho')[offset]


def is_our_decision(dealer: str, level: int) -> bool:
    """Whether the call at `level` belongs to the student's side (North-South)."""
    return seat_at_level(dealer, level) in OUR_SIDE


def display_dealer_for_level(level: int) -> str:
    """
    The [Dealer] seat to write in display space for a decision at `level`.

    The quizzed hand is always shown as South, so the seat that opened the
    auction lands the same number of steps before South as it does before the
    quizzed seat. That offset is `-level`, which makes the display dealer depend
    only on the level - not on where the board was actually dealt from.
    """
    return SEAT_ORDER[(SEAT_ORDER.index(STUDENT_DISPLAY_SEAT) - level) % 4]


def analyze_auction_tree(hands: List[Hand], min_frequency: float = 0.05) -> Dict:
    """
    Build an auction tree with frequency analysis at each level.

    Returns a nested structure showing bid frequencies at each decision point.

    Only the student's side (North-South) is recorded - we never quiz a call the
    opponents made. Which levels those are depends on each board's own dealer,
    so the test is applied per hand.
    """
    # Build frequency counts at each level, grouped by prefix
    level_data = defaultdict(lambda: defaultdict(list))

    for hand in hands:
        for level in range(len(hand.auction)):
            if not is_our_decision(hand.dealer, level):
                continue
            prefix = tuple(hand.auction[:level])
            bid = hand.auction[level]
            level_data[prefix][bid].append(hand)

    return level_data


def format_hand_for_display(hand_str: str) -> str:
    """Format a hand string for display with suit symbols."""
    suits = hand_str.split('.')
    symbols = ['♠', '♥', '♦', '♣']
    parts = []
    for symbol, cards in zip(symbols, suits):
        if cards:
            parts.append(f"{symbol}{cards}")
        else:
            parts.append(f"{symbol}-")
    return ' '.join(parts)


def format_auction_prefix(auction: List[str]) -> str:
    """Format an auction prefix for display."""
    if not auction:
        return ""

    # Convert back to readable format
    formatted = []
    for bid in auction:
        bid = bid.replace('N', 'NT')
        formatted.append(bid)

    return ' - '.join(formatted)


WHO_LABEL = {'you': 'you', 'partner': 'partner', 'lho': 'LHO', 'rho': 'RHO'}


def _call_phrase(who: str, bid: str, verb: str) -> str:
    """Render one call as prose from the quizzed seat's point of view."""
    subject = WHO_LABEL[who]
    if bid == 'X':
        return f"{subject} {'double' if who == 'you' else 'doubles'}"
    if bid == 'XX':
        return f"{subject} {'redouble' if who == 'you' else 'redoubles'}"
    if who != 'you' and verb in ('open', 'bid', 'respond'):
        verb = {'open': 'opens', 'bid': 'bids', 'respond': 'responds'}[verb]
    return f"{subject} {verb} {bid}"


def generate_quiz_prompt(dealer: str, level: int, auction_prefix: List[str]) -> str:
    """
    Generate the quiz prompt for a bidding situation, narrated from the
    quizzed seat's point of view.

    Works for any dealer: the seat facing the decision may be the opener, the
    responder, or - when the opponents dealt and opened - an overcaller or
    advancer, and the prose names LHO and RHO accordingly.
    """
    quizzed_seat = seat_at_level(dealer, level)

    parts = []
    opened = False
    partner_calls = 0
    for i, bid in enumerate(auction_prefix):
        who = relative_role(quizzed_seat, seat_at_level(dealer, i))
        bid_display = bid.replace('N', 'NT')

        if bid == 'Pass':
            # Opponent passes carry no information worth narrating; ours do.
            if who == 'you':
                parts.append("you pass")
            elif who == 'partner':
                parts.append("partner passes")
            continue

        if not opened:
            opened = True
            parts.append(_call_phrase(who, bid_display, 'open'))
            continue

        if who == 'partner':
            partner_calls += 1
            # Partner's first call over our opening is a response.
            verb = 'respond' if partner_calls == 1 and parts[0].startswith('you open') else 'bid'
            parts.append(_call_phrase(who, bid_display, verb))
        else:
            parts.append(_call_phrase(who, bid_display, 'bid'))

    if not parts:
        return "What do you open with each of these hands?"

    narrative = ', '.join(parts)
    narrative = narrative[0].upper() + narrative[1:]
    return narrative + ". What do you bid with each of these hands?"


def select_quiz_hands(hands_by_bid: Dict[str, List[Hand]],
                      num_hands: int = 6,
                      kind: str = 'opener') -> List[Tuple[Hand, str]]:
    """
    Select hands for a quiz with good variety.

    Try to get equal distribution of bids, with variety in the remaining auction.
    Returns list of (Hand, correct_bid) tuples.
    """
    selected = []
    bids = list(hands_by_bid.keys())

    if not bids:
        return []

    # Calculate how many of each bid to include
    per_bid = max(1, num_hands // len(bids))
    remainder = num_hands - (per_bid * len(bids))

    for bid in bids:
        available = hands_by_bid[bid]
        if not available:
            continue

        # How many to take of this bid
        count = per_bid
        if remainder > 0:
            count += 1
            remainder -= 1

        # Sort by variety in remaining auction (prefer different continuations)
        # Group by next few bids to get variety
        by_continuation = defaultdict(list)
        for hand in available:
            # Get next 2-3 bids as continuation key
            bid_idx = len([b for b in hand.auction if b == bid])  # Rough position
            continuation = tuple(hand.auction[bid_idx:bid_idx+3]) if bid_idx < len(hand.auction) else ()
            by_continuation[continuation].append(hand)

        # Select from different continuations
        continuations = list(by_continuation.keys())
        added = 0
        cont_idx = 0
        while added < count and added < len(available):
            cont = continuations[cont_idx % len(continuations)]
            if by_continuation[cont]:
                hand = by_continuation[cont].pop(0)
                selected.append((hand, bid))
                added += 1
            cont_idx += 1
            # Safety check to avoid infinite loop
            if cont_idx > count * 2:
                break

    return selected[:num_hands]


def get_bidding_round(level: int) -> int:
    """
    Get the bidding round number (1-based) for our side.
    Round 1 = first response (level 2)
    Round 2 = opener's rebid (level 4)
    Round 3 = responder's rebid (level 6)
    Round 4 = opener's second rebid (level 8)
    etc.
    """
    # Our side bids at levels 0, 2, 4, 6, 8... (opener) and 2, 6, 10... (responder from N's view)
    # Actually opener at 0, 4, 8... responder at 2, 6, 10...
    if level == 0:
        return 0  # Opening bid
    elif level == 2:
        return 1  # First response
    elif level == 4:
        return 2  # Opener's rebid
    elif level == 6:
        return 3  # Responder's rebid
    elif level == 8:
        return 4  # Opener's second rebid
    else:
        return (level // 2)


SUIT_RANK = {'C': 0, 'D': 1, 'H': 2, 'S': 3, 'N': 4}
GAME_BIDS = {'3N', '4H', '4S', '5C', '5D'}


def bid_rank(bid: str) -> int:
    """
    Return numeric rank for a bridge bid for ordering purposes.
    1C=5, 1D=6, 1H=7, 1S=8, 1N=9, 2C=10, ..., 7N=39.
    Returns -1 for Pass, X, XX, or unrecognized bids.
    """
    if not bid or bid in ('Pass', 'X', 'XX'):
        return -1
    if len(bid) < 2:
        return -1
    level_char = bid[0]
    suit_char = bid[1]
    if level_char.isdigit() and suit_char in SUIT_RANK:
        return int(level_char) * 5 + SUIT_RANK[suit_char]
    return -1


def is_game_or_above(bid: str) -> bool:
    """Check if a bid is at game level or above (3NT, 4H, 4S, 5C, 5D, or higher)."""
    rank = bid_rank(bid)
    if rank < 0:
        return False
    # Game is 3NT (rank 19). Any bid at 3NT or higher is at/above game.
    return rank >= bid_rank('3N')


def prefix_exceeds_level(prefix: list, level_str: str) -> bool:
    """
    Check if any bid in the auction prefix is at or above the specified level.

    Args:
        prefix: List of bids in the auction so far
        level_str: Either 'game' or a specific contract like '2H'

    Returns:
        True if the prefix contains a bid at or above the target level
    """
    if level_str == 'game':
        return any(is_game_or_above(bid) for bid in prefix)

    # Specific contract level (e.g., '2H')
    # Normalize NT to N for comparison
    target = level_str.replace('NT', 'N')
    target_rank = bid_rank(target)
    if target_rank < 0:
        return False
    return any(bid_rank(bid) >= target_rank for bid in prefix)


def generate_quizzes(hands: List[Hand],
                     num_per_quiz: int = 6,
                     min_frequency: float = 0.05,
                     verbose: bool = True,
                     max_rounds: Optional[int] = None,
                     max_level: Optional[str] = None) -> List[Dict]:
    """
    Generate quiz sets from the hands, grouped by bidding round.

    For rounds 1-2, group by exact prefix.
    For rounds 3+, combine all prefixes at that level into one quiz.

    Args:
        max_rounds: Stop after this many bidding rounds (e.g., 3 = opening, response, rebid)
        max_level: Stop when bids reach this level ('game' or specific contract like '2H')

    Returns a list of quiz dictionaries.
    """
    quizzes = []
    level_data = analyze_auction_tree(hands)

    # Group decision points by bidding round
    rounds_data = defaultdict(lambda: {'hands_by_bid': defaultdict(list), 'prefixes': set()})

    for prefix, bids_dict in level_data.items():
        # analyze_auction_tree only records our side's decisions, so every
        # prefix reaching here is a call North or South has to make.
        level = len(prefix)
        round_num = get_bidding_round(level)

        # For rounds 1-2, use exact prefix as key
        # For rounds 3+, group all prefixes at that level together.
        # Level is part of the key either way: a file dealt from more than one
        # seat puts our decisions at different levels within the same round.
        if round_num <= 2:
            round_key = (round_num, level, prefix)
        else:
            round_key = (round_num, level, None)  # Group all at this round

        rounds_data[round_key]['prefixes'].add(prefix)
        rounds_data[round_key]['level'] = level
        rounds_data[round_key]['round'] = round_num

        for bid, bid_hands in bids_dict.items():
            rounds_data[round_key]['hands_by_bid'][bid].extend(bid_hands)

    # Process each round
    for round_key in sorted(rounds_data.keys()):
        data = rounds_data[round_key]
        round_num = data['round']
        level = data['level']
        hands_by_bid = data['hands_by_bid']
        prefixes = data['prefixes']

        # Apply round limit: rounds=N means N full bidding rounds (each = opener + responder turn)
        # Internal round 0,1 = bidding round 1; round 2,3 = bidding round 2; etc.
        # So rounds=N allows internal rounds 0 through (N*2 - 1)
        if max_rounds is not None and round_num >= max_rounds * 2:
            if verbose:
                print(f"  Round {round_num} (level {level}): Skipping - exceeds {max_rounds} bidding rounds")
            continue

        # Apply level limit - check if any prefix has reached the target level
        if max_level is not None:
            any_prefix_exceeds = any(prefix_exceeds_level(list(p), max_level) for p in prefixes)
            if any_prefix_exceeds:
                if verbose:
                    print(f"  Round {round_num} (level {level}): Skipping - auction reached {max_level} level")
                continue

        # Count total hands
        total_hands = sum(len(h) for h in hands_by_bid.values())
        if total_hands == 0:
            continue

        # Filter bids by frequency
        significant_bids = {}
        for bid, bid_hands in hands_by_bid.items():
            frequency = len(bid_hands) / total_hands
            if frequency >= min_frequency:
                significant_bids[bid] = bid_hands

        # Skip if only one significant bid
        if len(significant_bids) <= 1:
            if verbose:
                if significant_bids:
                    bid = list(significant_bids.keys())[0]
                    print(f"  Round {round_num} (level {level}): Only one bid ({bid}) - skipping")
            continue

        # Skip if all passes
        non_pass_bids = {b: h for b, h in significant_bids.items() if b != 'Pass'}
        if not non_pass_bids and 'Pass' in significant_bids:
            continue

        # Get a representative prefix for rounds 1-2. Rounds 3+ bucket many
        # prefixes together, and a set's iteration order moves with Python's
        # per-process hash seed - sort so the same input always yields the same
        # title and prompt, and re-running the pipeline produces no diff.
        prefix = list(sorted(prefixes)[0]) if prefixes else []

        # Determine if auctions vary (for display purposes)
        auctions_vary = len(prefixes) > 1

        # Every hand in a bucket sits at the same level, so one hand's dealer
        # fixes the seat geometry for the whole quiz.
        dealer = next(iter(significant_bids.values()))[0].dealer
        kind = classify_situation(dealer, level, prefix)

        # Generate prompt based on round
        if round_num <= 2:
            prompt = generate_quiz_prompt(dealer, level, prefix)
        else:
            # Auctions vary too much by this point to narrate one of them
            if kind == 'responder':
                prompt = "As responder, what will you rebid with each of these hands?"
            elif kind == 'opener':
                prompt = "As opener, what will you rebid with each of these hands?"
            else:
                prompt = "In a competitive auction, what will you bid with each of these hands?"

        # Select hands
        quiz_hands = select_quiz_hands(significant_bids, num_per_quiz, kind)

        if len(quiz_hands) < 2:
            continue

        bid_distribution = {bid: len(h) for bid, h in significant_bids.items()}

        quiz = {
            'level': level,
            'round': round_num,
            'prefix': prefix,
            'prefixes': prefixes,  # All prefixes if they vary
            'auctions_vary': auctions_vary,
            'dealer': dealer,
            'kind': kind,
            'prompt': prompt,
            'hands': quiz_hands,
            'bid_distribution': bid_distribution,
            'total_hands': total_hands
        }
        quizzes.append(quiz)

    return quizzes


def display_quiz(quiz: Dict, quiz_num: int):
    """Display a quiz to console."""
    print(f"\n{'='*70}")
    print(f"QUIZ {quiz_num}: {seat_at_level(quiz['dealer'], quiz['level'])}'S DECISION ({quiz['kind']})")
    print(f"{'='*70}")

    prefix_str = format_auction_prefix(quiz['prefix'])
    if prefix_str:
        print(f"Auction so far: {prefix_str}")

    print(f"\n{quiz['prompt']}\n")

    # Show bid distribution
    print("Bid frequencies at this point:")
    for bid, count in sorted(quiz['bid_distribution'].items(),
                             key=lambda x: -x[1]):
        pct = count / quiz['total_hands'] * 100
        bid_display = bid.replace('N', 'NT')
        print(f"  {bid_display}: {count} ({pct:.1f}%)")

    print(f"\n{'─'*70}")
    print("Quiz Hands:")
    print(f"{'─'*70}\n")

    for i, (hand, correct_bid) in enumerate(quiz['hands'], 1):
        hand_str = hand.hands.get(seat_at_level(hand.dealer, quiz['level']), '')
        formatted = format_hand_for_display(hand_str)
        correct_display = correct_bid.replace('N', 'NT')

        print(f"  {i}. {formatted}")
        print(f"     Answer: {correct_display}")
        print(f"     Full auction: {' - '.join(b.replace('N', 'NT') for b in hand.auction)}")
        print()


def convert_suits_for_pbn(text: str) -> str:
    """Convert suit bids in text to PBN suit symbols (\\S, \\H, \\D, \\C)."""
    # Convert bid patterns like 1NT, 2H, 3S, etc.
    # Also handle standalone suit mentions
    result = text

    # Replace bids with suit - match patterns like "1H", "2S", "3D", "4C"
    # and also "opens 1H", "responds 2C", etc.
    result = re.sub(r'\b(\d)S\b', r'\1\\S', result)
    result = re.sub(r'\b(\d)H\b', r'\1\\H', result)
    result = re.sub(r'\b(\d)D\b', r'\1\\D', result)
    result = re.sub(r'\b(\d)C\b', r'\1\\C', result)

    return result


def has_interference(prefix: List[str], level: int) -> bool:
    """
    Check if the auction prefix contains any non-pass opponent bids.

    Calls alternate sides, so a call is an opponent's exactly when its index has
    the opposite parity to the level being quizzed - true whoever dealt.
    """
    return any(bid != 'Pass' for i, bid in enumerate(prefix) if (level - i) % 2)


def generate_pbn_header(scenario: str, use_two_col: bool = True) -> str:
    """Generate PBN file header with formatting settings for quiz layout."""
    two_col = " TwoColAuctions" if use_two_col else ""
    return f"""% PBN 2.1
% EXPORT
%Content-type: text/x-pbn; charset=UTF-8
%BCOptions Center GutterH GutterV Justify PageHeader STBorder STShade{two_col}
%BidAndCardSpacing Thin
%BoardsPerPage fit,2
%CardTableColors #008000,#ffffff,#aaaaaa
%EventSpacing 12
%Font:CardTable "Arial",11,400,0
%Font:Commentary "Arial",12,400,0
%Font:Diagram "Arial",12,400,0
%Font:Event "Arial",16,700,0
%Font:FixedPitch "Courier New",10,400,0
%Font:HandRecord "Arial",11,400,0
%GutterSize 250,250
%HRTitleEvent "{scenario} - Bidding Quiz"
%Margins 1000,1000,1000,750
%PageFooter:0,0 "%D"
%PageFooter:0,2 "%n"
%PaperSize 1,2159,2794,2
%ParaIndent 0
%PipColors #000000,#ff0000,#ff0000,#000000
%ShowBoardLabels 1
%ShowCardTable 2
%Translate "Board %" "%)"
"""


def format_auction_for_pbn(prefix: List[str], include_plus: bool = True) -> str:
    """Format auction prefix for PBN [Auction] tag."""
    if not prefix:
        return "+"

    # Convert bids to PBN format
    formatted = []
    for bid in prefix:
        bid = bid.replace('N', 'NT')
        formatted.append(bid)

    # Add Pass placeholders for skipped positions and the + marker
    result = ' '.join(formatted)
    if include_plus:
        result += '\n+'

    return result


def number_to_word(n: int) -> str:
    """Convert a number to its word form (1 -> One, 2 -> Two, etc.)."""
    words = ['Zero', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven',
             'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen',
             'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen', 'Twenty']
    if n < len(words):
        return words[n]
    return str(n)


SUIT_GLYPHS = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}


def convert_suits_to_glyphs(text: str) -> str:
    """Convert suit bids in text to Unicode suit glyphs (the quiz-JSON convention)."""
    return re.sub(
        r'\b(\d)(NT|[SHDC])\b',
        lambda m: m.group(1) + (m.group(2) if m.group(2) == 'NT' else SUIT_GLYPHS[m.group(2)]),
        text,
    )


def classify_situation(dealer: str, level: int, prefix: List[str]) -> str:
    """
    Name the quizzed seat's situation: 'open', 'opener', 'responder' or 'competitive'.

    Determined by who made the auction's first real call - us, our partner, or
    an opponent. The last case covers every scenario where the opponents dealt
    and opened, which is where overcalls and takeout doubles live.
    """
    quizzed_seat = seat_at_level(dealer, level)
    for i, bid in enumerate(prefix):
        if bid == 'Pass':
            continue
        seat = seat_at_level(dealer, i)
        if seat == quizzed_seat:
            return 'opener'
        if seat == partner_of(quizzed_seat):
            return 'responder'
        return 'competitive'
    return 'open'


def _first_real_call(dealer: str, prefix: List[str], seats) -> Optional[str]:
    """First non-pass call in `prefix` made by one of `seats`, in display form."""
    for i, bid in enumerate(prefix):
        if bid != 'Pass' and seat_at_level(dealer, i) in seats:
            return bid.replace('N', 'NT')
    return None


def _last_real_call(dealer: str, prefix: List[str], seats) -> Optional[str]:
    """Last non-pass call in `prefix` made by one of `seats`, in display form."""
    for i in range(len(prefix) - 1, -1, -1):
        if prefix[i] != 'Pass' and seat_at_level(dealer, i) in seats:
            return prefix[i].replace('N', 'NT')
    return None


def generate_exercise_title(quiz: Dict, scenario: str, suit_style: str = 'pbn') -> str:
    """
    Generate a descriptive exercise title based on the auction context.

    suit_style: 'pbn' for PBN suit escapes (\\S, \\H, …), 'glyph' for Unicode pips.
    """
    prefix = quiz['prefix']
    level = quiz['level']
    dealer = quiz.get('dealer', 'S')

    quizzed_seat = seat_at_level(dealer, level)
    partner = partner_of(quizzed_seat)
    opponents = tuple(s for s in SEAT_ORDER if s not in (quizzed_seat, partner))

    # How many calls each of us has already made: our turns come every fourth
    # call, so both counts fall straight out of the level.
    my_calls = level // 4
    partner_calls = (level + 2) // 4

    kind = classify_situation(dealer, level, prefix)

    if kind == 'open':
        title = "Opening Bids"

    elif kind == 'responder':
        partner_opening = _first_real_call(dealer, prefix, (partner,))
        if my_calls == 0:
            title = f"Responding to {partner_opening}" if partner_opening \
                else "Responding to Partner's Opening"
        elif my_calls == 1:
            title = "Responder's Rebid"
        elif my_calls == 2:
            title = "Responder's Third Bid"
        else:
            title = "Responder's Continuation"

    elif kind == 'opener':
        partner_last = _last_real_call(dealer, prefix, (partner,))
        if my_calls <= 1:
            title = f"Opener's Rebid after {partner_last}" if partner_last \
                else "Opener's Rebid"
        elif my_calls == 2:
            title = "Opener's Second Rebid"
        else:
            title = "Opener's Continuation"

    else:  # competitive - the opponents opened
        their_opening = _first_real_call(dealer, prefix, opponents)
        partner_first = _first_real_call(dealer, prefix, (partner,))
        if my_calls == 0 and partner_calls == 0:
            title = f"Action over {their_opening}" if their_opening \
                else "Action over the Opponents"
        elif my_calls == 0:
            title = f"Advancing Partner's {partner_first}" if partner_first \
                else "Advancing Partner"
        elif my_calls == 1:
            title = "Your Rebid in Competition"
        else:
            title = "Your Continuation in Competition"

    # Apply suit symbols to the title
    if suit_style == 'glyph':
        return convert_suits_to_glyphs(title)
    return convert_suits_for_pbn(title)


def add_column_break(lines: List[str], num_lines: int = 8):
    """Add a spacer board to force a column break (push next content to right column)."""
    add_spacer(lines, num_lines)


def add_spacer(lines: List[str], num_lines: int = 15):
    """Add a spacer board to force page break."""
    lines.append('[Event ""]')
    lines.append('[Site ""]')
    lines.append('[Date ""]')
    lines.append('[Board "spacer"]')
    lines.append('[West ""]')
    lines.append('[North ""]')
    lines.append('[East ""]')
    lines.append('[South ""]')
    lines.append('[Dealer "N"]')
    lines.append('[Vulnerable "None"]')
    lines.append('[Deal ""]')
    lines.append('[Scoring ""]')
    lines.append('[Declarer ""]')
    lines.append('[Contract ""]')
    lines.append('[Result ""]')
    lines.append('{')
    for _ in range(num_lines):
        lines.append('')
    lines.append(' }')
    lines.append('[BCFlags "17"]')
    lines.append('')


def generate_quiz_boards(quiz: Dict, quiz_num: int, scenario: str) -> List[str]:
    """Generate PBN boards for a single quiz (header + hands)."""
    lines = []
    level = quiz['level']
    prefix = quiz['prefix']
    prompt = quiz['prompt']
    auctions_vary = quiz.get('auctions_vary', False)
    round_num = quiz.get('round', 0)

    # Generate exercise title
    exercise_title = generate_exercise_title(quiz, scenario)
    exercise_name = f"Exercise {number_to_word(quiz_num)} — {exercise_title}"

    # Convert suit symbols in prompt
    prompt_pbn = convert_suits_for_pbn(prompt)

    # The hand is always displayed in the South position so the student sees it
    # there; which seat it is *read from* depends on the board's dealer, so it is
    # resolved per hand below via seat_at_level().
    hidden = 'NEW'  # Always hide N, E, W - show only South

    # Dealer seat in display space, where the quizzed hand sits South
    dealer_seat = display_dealer_for_level(level)

    # Show auction if there's interference OR if auctions vary between hands
    show_header_auction = prefix and has_interference(prefix, level) and not auctions_vary
    show_hand_auctions = auctions_vary or round_num >= 3

    # Quiz header board with title and description
    lines.append(f'[Event "{exercise_name}"]')
    lines.append('[Site ""]')
    lines.append('[Date ""]')
    # Title bold, then description on new line
    lines.append('{<b>' + exercise_name + '</b>\n\n' + prompt_pbn + '}')
    lines.append(f'[Board "{quiz_num}"]')
    lines.append('[West ""]')
    lines.append('[North ""]')
    lines.append('[East ""]')
    lines.append('[South ""]')
    lines.append(f'[Dealer "{dealer_seat}"]')
    lines.append('[Vulnerable "None"]')
    lines.append('[Deal ""]')
    lines.append('[Scoring ""]')
    lines.append('[Declarer ""]')
    lines.append('[Contract ""]')
    lines.append('[Result ""]')
    lines.append('[BCFlags "600023"]')
    lines.append('[Hidden "NESW"]')

    # Add auction context in header only if fixed (not varying)
    if show_header_auction:
        lines.append(f'[Auction "{dealer_seat}"]')
        lines.append(format_auction_for_pbn(prefix))

    lines.append('')

    # Individual hand boards
    for hand_num, (hand, correct_bid) in enumerate(quiz['hands'], 1):
        board_id = f"{quiz_num}-{hand_num}"

        # Read the hand from the seat that actually faces the decision,
        # but always display it in the South position
        hand_str = hand.hands.get(seat_at_level(hand.dealer, level), '...')
        deal_str = f'S:{hand_str} ... ... ...'

        # Format the answer with suit symbol
        answer_bid = correct_bid.replace('N', 'NT')
        answer_pbn = convert_suits_for_pbn(answer_bid)

        # For varying auctions, get this hand's auction prefix
        if show_hand_auctions:
            # Get auction up to the decision point
            hand_prefix = hand.auction[:level]
            hand_prefix_pbn = format_auction_for_pbn(hand_prefix)

        lines.append('[Event ""]')
        lines.append('[Site ""]')
        lines.append('[Date ""]')
        lines.append(f'[Board "{board_id}"]')
        lines.append('[West ""]')
        lines.append('[North ""]')
        lines.append('[East ""]')
        lines.append('[South ""]')
        lines.append(f'[Dealer "{dealer_seat}"]')
        lines.append('[Vulnerable "None"]')
        lines.append(f'[Deal "{deal_str}"]')
        lines.append('[Scoring ""]')
        lines.append('[Declarer ""]')
        lines.append('[Contract ""]')
        lines.append('[Result ""]')
        lines.append('{<i>' + answer_pbn + '</i>}')
        lines.append('[BCFlags "60001b"]')
        lines.append(f'[Hidden "{hidden}"]')

        # Add auction for each hand if auctions vary
        if show_hand_auctions:
            lines.append(f'[Auction "{dealer_seat}"]')
            lines.append(hand_prefix_pbn)

        lines.append('')

    return lines


def generate_answer_boards(quiz: Dict, quiz_num: int, scenario: str) -> List[str]:
    """Generate PBN boards for answer sheet."""
    lines = []

    # Dealer seat in display space, where the quizzed hand sits South
    dealer_seat = display_dealer_for_level(quiz['level'])

    # Generate exercise title for answers
    exercise_title = generate_exercise_title(quiz, scenario)
    answer_title = f"Exercise {number_to_word(quiz_num)} Answers"

    # Answer header
    lines.append('[Event ""]')
    lines.append('[Site ""]')
    lines.append('[Date ""]')
    lines.append('{<b><i>' + answer_title + '</i></b>}')
    lines.append(f'[Board "{quiz_num}"]')
    lines.append('[West ""]')
    lines.append('[North ""]')
    lines.append('[East ""]')
    lines.append('[South ""]')
    lines.append(f'[Dealer "{dealer_seat}"]')
    lines.append('[Vulnerable "None"]')
    lines.append('[Deal ""]')
    lines.append('[Scoring ""]')
    lines.append('[Declarer ""]')
    lines.append('[Contract ""]')
    lines.append('[Result ""]')
    lines.append('[BCFlags "600023"]')
    lines.append('[Hidden "NESW"]')
    lines.append('')

    # Individual answer entries
    for hand_num, (hand, correct_bid) in enumerate(quiz['hands'], 1):
        board_id = f"{quiz_num}-{hand_num}"
        answer_bid = correct_bid.replace('N', 'NT')
        answer_pbn = convert_suits_for_pbn(answer_bid)

        lines.append('[Event ""]')
        lines.append('[Site ""]')
        lines.append('[Date ""]')
        lines.append(f'[Board "{board_id}"]')
        lines.append('[West ""]')
        lines.append('[North ""]')
        lines.append('[East ""]')
        lines.append('[South ""]')
        lines.append('[Dealer "N"]')
        lines.append('[Vulnerable "None"]')
        lines.append('[Deal ""]')
        lines.append('[Scoring ""]')
        lines.append('[Declarer ""]')
        lines.append('[Contract ""]')
        lines.append('[Result ""]')
        lines.append('{<b>' + board_id + ')</b> <i>' + answer_pbn + '</i>}')
        lines.append('[BCFlags "17"]')
        lines.append('')

    return lines


def generate_quiz_pbn(quizzes: List[Dict], scenario: str) -> str:
    """
    Generate complete PBN file content for all quizzes.

    Layout: Quizzes on one page, answers on the next.
    - Page 1: Exercise 1, Exercise 2
    - Page 2: Exercise 1 Answers, Exercise 2 Answers
    - Page 3: Exercise 3, Exercise 4
    - Page 4: Exercise 3 Answers, Exercise 4 Answers
    - etc.
    """
    # Always use TwoColAuctions - bridge-wrangler should handle rendering correctly
    lines = [generate_pbn_header(scenario, use_two_col=True)]

    # Process quizzes in pairs (2 per page)
    quizzes_per_page = 2

    for i in range(0, len(quizzes), quizzes_per_page):
        page_quizzes = quizzes[i:i + quizzes_per_page]

        # Generate quiz boards for this page
        for j, quiz in enumerate(page_quizzes):
            quiz_num = i + j + 1

            # Add column break before the 2nd quiz if it has a fixed auction header
            if j == 1 and not quiz.get('auctions_vary', False):
                add_column_break(lines)

            lines.extend(generate_quiz_boards(quiz, quiz_num, scenario))

        # Add spacer to force page break before answers
        add_spacer(lines, 15)

        # Generate answer boards for this page's quizzes
        for j, quiz in enumerate(page_quizzes):
            quiz_num = i + j + 1
            lines.extend(generate_answer_boards(quiz, quiz_num, scenario))

        # Add spacer after answers (before next set of quizzes)
        add_spacer(lines, 18)

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# quiz-lesson/v1 JSON emission
#
# One file per lesson (scenario), mirroring the hierarchy the generator already
# works in:
#
#     lesson  ->  exercise (a shared prompt)  ->  question (hand + answer)
#
# The generator groups hands under a common prompt because they pose the same
# bidding problem, so the JSON keeps that grouping rather than flattening it.
# lesson-studio reads a lesson file, curates a handful of questions under a
# prompt, and saves that group into the lesson document.
#
# The question shape is Contract 3's `bidding` item unchanged (lesson-studio
# documentation/contracts/quiz-json-schema.md); what changed is the envelope
# around it. The JSON still carries no pagination and no answer placement -
# those are the renderer's decisions - so a question holds its answer alongside
# it as plain data.
# ---------------------------------------------------------------------------

QUIZ_LESSON_SCHEMA = "quiz-lesson/v1"
QUIZ_INDEX_SCHEMA = "quiz-index/v1"
QUIZ_SOURCE = "Practice-Bidding-Scenarios"

# PBN [Vulnerable] values -> the contract's enum.
VULNERABILITY_MAP = {
    'None': 'None', '-': 'None', 'Love': 'None', 'Nil': 'None',
    'NS': 'NS', 'EW': 'EW',
    'All': 'Both', 'Both': 'Both',
}


def to_contract_call(bid: str) -> str:
    """Convert an internal bid token to quiz-JSON Call notation ('1N' -> '1NT', 'Pass' -> 'P')."""
    if bid == 'Pass':
        return 'P'
    if bid in ('X', 'XX'):
        return bid
    return bid.replace('N', 'NT')


def hand_to_object(holding: str) -> Dict[str, str]:
    """Convert a PBN holding ('AQ.A5.8743.QJT95') to the canonical Hand object."""
    suits = holding.split('.')
    suits += [''] * (4 - len(suits))
    return {
        'spades': suits[0],
        'hearts': suits[1],
        'diamonds': suits[2],
        'clubs': suits[3],
    }


def build_question(quiz: Dict, hand: Hand, correct_bid: str, scenario: str) -> Dict:
    """Build one question - a hand, the auction it faces, and the expected call."""
    level = quiz['level']
    seat = seat_at_level(hand.dealer, level)

    question = {
        'hand': hand_to_object(hand.hands.get(seat, '')),
        'seat': seat,
        'dealer': hand.dealer,
        'vulnerability': VULNERABILITY_MAP.get(hand.vulnerable, 'None'),
    }

    # Calls made before it is this seat's turn, dealer-first.
    context_calls = [to_contract_call(b) for b in hand.auction[:level]]
    if context_calls:
        question['context'] = {'dealer': hand.dealer, 'calls': context_calls}

    question['answer'] = to_contract_call(correct_bid)

    if hand.board_token:
        question['board'] = {
            'repo': QUIZ_SOURCE,
            'id': hand.board_token,
            'event': scenario,
            'board': hand.board_num,
        }

    return question


def build_exercise(quiz: Dict, quiz_num: int, scenario: str) -> Dict:
    """Build one exercise: a shared prompt plus the questions posed under it."""
    return {
        'id': f"{scenario}-{quiz_num}",
        'type': 'bidding',
        'title': f"Exercise {number_to_word(quiz_num)} — "
                 f"{generate_exercise_title(quiz, scenario, suit_style='glyph')}",
        'prompt': convert_suits_to_glyphs(quiz['prompt']),
        'questions': [build_question(quiz, hand, bid, scenario)
                      for hand, bid in quiz['hands']],
    }


def build_lesson_json(quizzes: List[Dict], scenario: str, generated: str,
                      skill_paths: Optional[List[str]] = None,
                      title: Optional[str] = None) -> Dict:
    """Build the whole lesson: every exercise the scenario produced, in order."""
    lesson = {
        'schema': QUIZ_LESSON_SCHEMA,
        'id': scenario,
        'title': title or scenario.replace('_', ' '),
    }
    if skill_paths:
        lesson['skill_paths'] = skill_paths
    lesson['provenance'] = {
        'source': QUIZ_SOURCE,
        'pipeline_version': PIPELINE_VERSION,
        'generated': generated,
        'source_quiz': scenario,
    }
    lesson['exercises'] = [build_exercise(q, n, scenario)
                           for n, q in enumerate(quizzes, 1)]
    return lesson


def _write_json_stable(path: str, obj: Dict, date_path: Tuple[str, ...]) -> bool:
    """
    Write `obj` as JSON, preserving the existing generation date when nothing else changed.

    These artifacts are committed, so re-running the pipeline must not churn the
    repo with date-only diffs. Returns True if the file was written.
    """
    existing = None
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except (ValueError, OSError):
            existing = None

    if existing is not None:
        probe = copy.deepcopy(obj)
        node, old = probe, existing
        for key in date_path[:-1]:
            node = node.get(key, {}) if isinstance(node, dict) else {}
            old = old.get(key, {}) if isinstance(old, dict) else {}
        if isinstance(node, dict) and isinstance(old, dict) and date_path[-1] in old:
            node[date_path[-1]] = old[date_path[-1]]
        if probe == existing:
            return False

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')
    return True


def _index_entry(lesson: Dict, filename: str) -> Dict:
    """Project a lesson envelope into its index.json entry."""
    entry = {
        'id': lesson['id'],
        'title': lesson['title'],
        'exercise_count': len(lesson['exercises']),
        'question_count': sum(len(e['questions']) for e in lesson['exercises']),
    }
    if lesson.get('skill_paths'):
        entry['skill_paths'] = lesson['skill_paths']
    entry['file'] = filename
    return entry


def update_quiz_index(quiz_folder: str, entry: Dict, generated: str) -> None:
    """
    Merge this lesson's entry into quiz/index.json.

    The index spans every lesson but the quiz operation runs one at a time, so
    the existing index is read and only this lesson's row is replaced.
    """
    index_path = os.path.join(quiz_folder, "index.json")

    lessons = []
    if os.path.exists(index_path):
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                lessons = json.load(f).get('lessons', [])
        except (ValueError, OSError):
            lessons = []

    lessons = [l for l in lessons if l.get('id') != entry['id']]
    lessons.append(entry)
    lessons.sort(key=lambda l: l.get('id', ''))

    index = {
        'schema': QUIZ_INDEX_SCHEMA,
        'generated': generated,
        'pipeline_version': PIPELINE_VERSION,
        'lessons': lessons,
    }
    _write_json_stable(index_path, index, ('generated',))


def write_quiz_json(quizzes: List[Dict], scenario: str, quiz_folder: str,
                    verbose: bool = False) -> str:
    """
    Emit the scenario's lesson JSON and refresh index.json.

    Returns the path written.
    """
    from utils.properties import fetch_property, get_button_text

    generated = date.today().isoformat()

    raw_paths = fetch_property(scenario, "skill-path")
    skill_paths = [p.strip() for p in raw_paths.split(',') if p.strip()] if raw_paths else None

    # The .btn button text is the human name for the scenario everywhere else
    # in the pipeline, so use it as the lesson title too.
    title = get_button_text(scenario)

    lesson = build_lesson_json(quizzes, scenario, generated, skill_paths, title)
    path = os.path.join(quiz_folder, f"{scenario}.json")
    _write_json_stable(path, lesson, ('provenance', 'generated'))

    update_quiz_index(quiz_folder, _index_entry(lesson, f"{scenario}.json"), generated)

    if verbose:
        print(f"  Created: {path} "
              f"({len(lesson['exercises'])} exercises) + index.json")

    return path


def run_quiz(scenario: str, num_per_quiz: int = 6, verbose: bool = False, debug: bool = False) -> bool:
    """
    Generate quizzes for a scenario.

    Args:
        scenario: Scenario name (e.g., "Stayman")
        num_per_quiz: Number of hands per quiz (default 6)
        verbose: Whether to print progress (default False)
        debug: Whether to print detailed auction analysis and quiz hands (default False)

    Returns:
        True if successful, False otherwise
    """
    from utils.properties import get_quiz_control
    quiz_control = get_quiz_control(scenario)

    if verbose:
        print(f"--------- Quiz generation for {scenario}")
        print(f"  quiz-control: rounds={quiz_control['rounds']}, level={quiz_control['level']}")

    # Read filtered PBN file
    filtered_path = os.path.join(FOLDERS["bba_filtered"], f"{scenario}.pbn")
    if not os.path.exists(filtered_path):
        if verbose:
            print(f"Error: Filtered file not found: {filtered_path}")
        return False

    if verbose:
        print(f"  Reading: {filtered_path}")

    # Parse hands
    hands = parse_pbn_file(filtered_path)
    if verbose:
        print(f"  Parsed {len(hands)} hands")

    if not hands:
        if verbose:
            print("  No hands found in file")
        return False

    # Generate quizzes
    if verbose:
        print(f"\nAnalyzing auction decision points...")
    quizzes = generate_quizzes(hands, num_per_quiz, verbose=debug,
                               max_rounds=quiz_control['rounds'],
                               max_level=quiz_control['level'])

    if not quizzes:
        if verbose:
            print("  No quiz-worthy decision points found")
        return True

    if verbose:
        print(f"\nGenerated {len(quizzes)} quiz sets")

    if debug:
        for i, quiz in enumerate(quizzes, 1):
            display_quiz(quiz, i)

    # Create quiz output folder
    quiz_folder = os.path.join(PROJECT_ROOT, "quiz")
    os.makedirs(quiz_folder, exist_ok=True)

    # Generate PBN file
    pbn_content = generate_quiz_pbn(quizzes, scenario)
    pbn_path = os.path.join(quiz_folder, f"{scenario}.pbn")

    with open(pbn_path, 'w', encoding='utf-8') as f:
        f.write(pbn_content)

    if verbose:
        print(f"\n  Created: {pbn_path}")

    # Emit the quiz/v1 JSON objects + index alongside the PBN
    write_quiz_json(quizzes, scenario, quiz_folder, verbose=verbose)

    # Generate PDF using bridge-wrangler
    bridge_wrangler = MAC_TOOLS.get("bridge_wrangler")
    if bridge_wrangler:
        pdf_path = os.path.join(quiz_folder, f"{scenario}.pdf")
        pdf_cmd = [
            bridge_wrangler, "to-pdf",
            "-i", pbn_path,
            "-o", pdf_path
        ]

        try:
            result = subprocess.run(pdf_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  Warning: PDF generation failed")
                if result.stderr:
                    print(f"    {result.stderr}")
            elif verbose:
                print(f"  Created: {pdf_path}")
        except Exception as e:
            print(f"  Warning: PDF generation failed: {e}")

    return True


if __name__ == "__main__":
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    args = [a for a in sys.argv[1:] if a not in ('--verbose', '-v')]

    scenario = args[0] if args else "Stayman"

    num_per_quiz = 6
    if len(args) > 1:
        num_per_quiz = int(args[1])

    print(f"Quiz Generation Test")
    print(f"Scenario: {scenario}")
    print(f"Hands per quiz: {num_per_quiz}")
    print()

    success = run_quiz(scenario, num_per_quiz, verbose=verbose, debug=verbose)
    print(f"\nResult: {'Success' if success else 'Failed'}")
