#!/usr/bin/env python3
"""nonrotate.py — resolve a tokenized coaching-curated/<scn>.pbn into the
South=student coaching-non-rotated/<scn>.pbn, folding partner's calls.

The coaching-curated file is rotation-tokenized: every non-pass N/S call has its
own `[BID]` chunk written for its own actor with `@S`/`@v(base|third)` tokens.
The non-rotated file is what bridge-classroom (a literal renderer) reads, so it
fixes South=student and differs in TWO ways:

  1. Tokens are resolved with the trainer's `fill_pronouns` rule — South's calls
     render 2nd person ("You open 1D"), North's render 3rd ("Your partner ...").
  2. Partner's (North's) `[BID]` anchors are FOLDED away: bridge-classroom quizzes
     only the student, so each North chunk is merged into the adjacent South chunk
     and only South's calls keep a `[BID]`. South's auction-ending Pass is anchored
     with `[BID Pass]`.

Fold direction follows who opened (strict N/S alternation in these uncontested
auctions): if North opens (South is responder) each North chunk PREPENDS to the
following South chunk, and a trailing North chunk (partner's final bid that South
passes) becomes a `[BID Pass]` chunk. If South opens, each North chunk APPENDS to
the preceding South chunk.

Run from the project root, then run `bridge_classroom.py <scn>` to strip the
pre-auction stat blocks, renumber, and add [OriginalBoard]:

    python3 -P py/nonrotate.py Fourth_Suit_Forcing
    python3 -P py/bridge_classroom.py Fourth_Suit_Forcing
"""
import os, re, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from curate import split_boards, tag

SEATS = ['N', 'E', 'S', 'W']
_VERB = re.compile(r'@v\(([^|]*)\|([^)]*)\)')


_SUBJ = re.compile(r'@[Ss]')
_POSS = re.compile(r'@(?:Your|your)')
# [ACCEPT call ...] marks an extra defensible call for the bid quiz. bridge-classroom
# scores it against the STUDENT's own call, so it is only meaningful on South's bid
# chunks. Drop it elsewhere: on partner's (North) calls it would fold into the
# absorbing South chunk and wrongly accept the alternate for the student's call, and
# in play/reflection text (e.g. a [PLAY]/[WHY] card accept) it isn't a bid at all.
_ACCEPT = re.compile(r'[ \t]*\[ACCEPT\b[^\]]*\]', re.IGNORECASE)


def _cap_at(text, pos):
    """True if position `pos` begins a sentence (start, or after . ! ? : — / newline)."""
    j = pos - 1
    while j >= 0 and text[j] == ' ':
        j -= 1
    return j < 0 or text[j] in '.!?:\n—'


def fill_pronouns(text, is_student):
    """Resolve rotation tokens for a fixed seat (the trainer's fill_pronouns rule),
    but position-aware: a subject/possessive token is capitalized only when it
    starts a sentence, so an `@S` an author placed mid-sentence still reads
    "you", not "You". Baked into the static bridge-classroom file."""
    if not text or '@' not in text:
        return text
    text = _VERB.sub((lambda m: m.group(1)) if is_student else (lambda m: m.group(2)), text)
    subj = ('you', 'You') if is_student else ('your partner', 'Your partner')
    poss = ('your', 'Your') if is_student else ('their', 'Their')
    text = _SUBJ.sub(lambda m: subj[1] if _cap_at(text, m.start()) else subj[0], text)
    text = _POSS.sub(lambda m: poss[1] if _cap_at(text, m.start()) else poss[0], text)
    return text


def seat_seq(dealer):
    i = SEATS.index(dealer)
    while True:
        yield SEATS[i % 4]
        i += 1


def auction_seats(chunk):
    """List of (seat, call) for the board's auction, in order."""
    dealer = re.search(r'\[Dealer "([NESW])"\]', chunk).group(1)
    am = re.search(r'\[Auction "[NESW]"\]\s*(.*?)(?=\n\[|\n\{)', chunk, re.S)
    calls = [t for t in am.group(1).split()
             if re.match(r'^(Pass|X|XX|[1-7](N|NT|[SHDC]))$', t)]
    g = seat_seq(dealer)
    return [(next(g), c) for c in calls]


def contract_display(chunk):
    c = tag(chunk, 'Contract') or ''
    m = re.match(r'^([1-7])(N|NT|[SHDC])(X*)$', c)
    if not m:
        return c
    lvl, strain, dbl = m.groups()
    if strain in ('N', 'NT'):
        return f"{lvl}NT{dbl}"
    return f"{lvl}\\{strain}{dbl}"


def parse_block(chunk):
    """Return (intro, [(call, text), ...], reflection) from the LAST {...} block."""
    block = chunk[chunk.rfind('{') + 1: chunk.rfind('}')]
    # split on [BID xxx] and the closing reflection marker ([show NS] or the
    # current [show NESW] — both are accepted; curated files use [show NESW]).
    parts = re.split(r'(\[BID [^\]]+\]|\[show N(?:S|ESW)\])', block)
    intro = parts[0].strip()
    chunks, reflection = [], ''
    i = 1
    cur_call = None
    while i < len(parts):
        marker, body = parts[i], parts[i + 1] if i + 1 < len(parts) else ''
        if marker.startswith('[BID'):
            cur_call = marker[len('[BID '):-1].strip()
            chunks.append((cur_call, body.strip()))
        elif marker in ('[show NS]', '[show NESW]'):
            reflection = body.strip()
        i += 2
    return intro, chunks, reflection


def fold_board(chunk):
    # Bracket the student's OWN justification with ⟦ ⟧ so bridge-classroom can fade
    # it to a brief affirmation on a correct call, while always keeping the folded-in
    # partner/opponent text (which sits OUTSIDE the brackets). See coaching-feedback-fade.
    JBEG, JEND = '⟦', '⟧'   # ⟦ ⟧
    seats = auction_seats(chunk)
    ns_nonpass = [(s, c) for s, c in seats if s in 'NS' and c != 'Pass']
    south_all = [c for s, c in seats if s == 'S']
    south_ends_pass = bool(south_all) and south_all[-1] == 'Pass'

    intro, chunks, reflection = parse_block(chunk)
    # Play / choose-card boards carry no [BID] anchors: the student is South (the
    # declarer), the prose is seat-fixed and token-free, and bridge-classroom reads
    # the block verbatim. There is nothing to rotate or fold, so emit the coaching
    # block unchanged. (The pre-auction {Shape}/{HCP}/{Losers}/{Curate} stat blocks
    # are stripped afterward by bridge_classroom.py.)
    if not chunks:
        return chunk[chunk.rfind('{'): chunk.rfind('}') + 1]
    # Old-format curated files bake a leading [show S] into the intro; strip any
    # leading [show ...] so the [show S] we add below isn't doubled.
    intro = re.sub(r'^\s*\[show [^\]]+\]\s*', '', intro)
    assert len(chunks) == len(ns_nonpass), \
        f"board {tag(chunk,'Board')}: {len(chunks)} BID chunks vs {len(ns_nonpass)} N/S calls"
    # [ACCEPT] survives only on South's own bid chunks (the student's quiz calls).
    # Strip it from intro/reflection (not bids) and from partner's calls (which fold
    # into a South chunk and would otherwise mis-accept the student's call).
    intro = _ACCEPT.sub('', intro)
    reflection = _ACCEPT.sub('', reflection)
    # attach seat to each chunk
    seated = []
    for i, (call, text) in enumerate(chunks):
        is_student = ns_nonpass[i][0] == 'S'
        text = fill_pronouns(text, is_student)
        if not is_student:
            # Drop partner's [ACCEPT] and tidy the space it leaves, so folding this
            # single-line bid prose into the South chunk doesn't double a space.
            text = _ACCEPT.sub('', text).strip()
        seated.append((ns_nonpass[i][0], call, text))

    opener = ns_nonpass[0][0] if ns_nonpass else 'S'
    out = []  # list of (anchor_call, text)
    if opener == 'N':                      # South is responder → prepend partner's preceding call
        pending = None
        for seat, call, text in seated:
            if seat == 'N':
                pending = text
            else:                          # South
                merged = (pending + ' ' if pending else '') + JBEG + text + JEND
                out.append((call, merged))
                pending = None
        if south_ends_pass:                # partner's final bid + South's closing pass
            tail = (pending + ' ' if pending else '')
            out.append(('Pass', f"{tail}{JBEG}You pass; {contract_display(chunk)} is the final contract.{JEND}"))
        elif pending:                      # safety: leftover partner call with no anchor
            out[-1] = (out[-1][0], out[-1][1] + ' ' + pending)
    else:                                  # South opens → append partner's following call
        for seat, call, text in seated:
            if seat == 'S':
                out.append((call, JBEG + text + JEND))
            else:
                out[-1] = (out[-1][0], out[-1][1] + ' ' + text)
        if south_ends_pass:
            out.append(('Pass', JBEG + f"You pass; {contract_display(chunk)} is the final contract." + JEND))

    body_lines = ['[show S]' + intro]
    for call, text in out:
        body_lines.append(f'[BID {call}] {text}')
    body_lines.append('[show NESW]' + reflection)
    return '{' + '\n'.join(body_lines) + '}'


def main():
    scn = sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__)
    src = f"coaching-curated/{scn}.pbn"
    raw = open(src, encoding='utf-8').read()
    chunks = split_boards(src)
    pre = raw[:raw.find(chunks[0])] if chunks else raw
    out = [pre]
    n = 0
    for ch in chunks:
        if not tag(ch, 'Board'):
            out.append(ch)
            continue
        new_block = fold_board(ch)
        old_start = ch.rfind('{')
        old_end = ch.rfind('}') + 1
        out.append(ch[:old_start] + new_block + ch[old_end:])
        n += 1
    dst = f"coaching-non-rotated/{scn}.pbn"
    open(dst, 'w', encoding='utf-8').write(''.join(out))
    print(f"{scn}: folded {n} boards -> {dst}")
    print("  next: python3 -P py/bridge_classroom.py " + scn)


if __name__ == "__main__":
    main()
