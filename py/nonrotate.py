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
     and only South's calls keep a `[BID]`.

EVERY South call is anchored — including the intermediate passes the student would
have to make at the table. An unanchored call is one bridge-classroom makes silently
on the student's behalf, which reads as a skipped turn (classroom-feedback #243, "I
did not make the first pass"). South's passes carry generated prose: the auction-
ending one names the final contract, an intermediate one is a bare "You pass."

Partner's non-pass calls fold into an adjacent South chunk: partner's OPENING (any
call before South first acts) goes into the intro prompt, and each LATER partner call
is appended to the previous South chunk — whose post-answer is the next step's
prompt, so the student sees partner's bid before having to answer it. Partner's
passes and the opponents' calls are not narrated; they appear only where the curated
prose mentions them.

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
    # [ACCEPT] survives only on South's own bid chunks (the student's quiz calls).
    # Strip it from intro/reflection (not bids) and from partner's calls (which fold
    # into a South chunk and would otherwise mis-accept the student's call).
    intro = _ACCEPT.sub('', intro)
    reflection = _ACCEPT.sub('', reflection)
    # Bind each curated chunk to the auction call it explains by walking both in
    # order and matching on the call's VALUE (the way the renderers anchor), rather
    # than assuming chunks line up 1:1 with the N/S non-pass calls. That assumption
    # forbids the one thing a chunk legitimately wants to explain but the old
    # positional scheme had no slot for: SOUTH'S OWN PASS. Partner's passes are
    # never authored, but South's may be — a pass the student still has to make can
    # carry real teaching prose ("you have shown your hand, so you let it go"), and
    # an unmatched South pass simply falls through to generated text below.
    ns_calls = [(i, s, c) for i, (s, c) in enumerate(seats) if s in 'NS']
    seated = {}                      # index into `seats` -> (seat, call, text)
    p = 0
    for call, text in chunks:
        j = p
        while j < len(ns_calls) and ns_calls[j][2] != call:
            j += 1
        assert j < len(ns_calls), (
            f"board {tag(chunk,'Board')}: chunk [BID {call}] matches no remaining "
            f"N/S call in {[c for _, _, c in ns_calls]}")
        idx, seat, _ = ns_calls[j]
        is_student = seat == 'S'
        text = fill_pronouns(text, is_student)
        if not is_student:
            # Drop partner's [ACCEPT] and tidy the space it leaves, so folding this
            # single-line bid prose into the South chunk doesn't double a space.
            text = _ACCEPT.sub('', text).strip()
        seated[idx] = (seat, call, text)
        p = j + 1

    # Walk the FULL auction so EVERY South call carries its own [BID] anchor —
    # including the intermediate passes the student would have to make at the table.
    # (classroom-feedback #243: "I did not make the first pass" — an unanchored pass
    # is made silently by bridge-classroom, so the student never gets the call.)
    # A [BID] step reveals text BEFORE the tag as the PROMPT (seen before acting) and
    # text AFTER as the post-answer. The post-answer of one step is the prompt of the
    # next. So partner's calls must land in the *next* decision's prompt, not the
    # current step's post-answer — otherwise the student doesn't see what partner bid
    # until after they respond to it. Partner's OPENING (calls before South ever acts)
    # goes into the intro prompt; each LATER partner call is appended to the previous
    # South chunk. Partner's passes and the opponents' calls stay unnarrated — they are
    # mentioned only where the curated prose says so.
    south_idx = [i for i, (s, c) in enumerate(seats) if s == 'S']
    last_south = south_idx[-1] if south_idx else -1
    out = []                               # list of (anchor_call, text)
    for i, (seat, call) in enumerate(seats):
        if seat not in 'NS':
            continue
        ent = seated.get(i)
        if seat == 'S':
            if ent:                        # authored prose for this call
                text = ent[2]
            elif call == 'Pass':           # unauthored pass — generate the prose
                text = (f"You pass; {contract_display(chunk)} is the final contract."
                        if i == last_south and south_ends_pass else "You pass.")
            else:
                raise AssertionError(
                    f"board {tag(chunk,'Board')}: South's {call} has no coaching chunk")
            out.append((call, JBEG + text + JEND))
        elif ent and ent[2]:               # partner's authored call (passes: never)
            if out:                        # later partner bid → previous step's post-answer
                out[-1] = (out[-1][0], out[-1][1] + ' ' + ent[2])
            else:                          # partner's opening, before South acts
                intro = (intro + ' ' if intro else '') + ent[2]

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
