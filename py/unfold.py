#!/usr/bin/env python3
"""unfold.py — reconstruct a PRE-FOLD coaching-curated block from a folded one.

Drift = `coaching-curated/<scn>.pbn` holds folded (served) content, so
`nonrotate.py` can't re-fold it. This inverts `fold_board`.

TWO fold generations are in the corpus and both must be inverted:

    prepend (older):  [BID s] <partner text BEFORE s> ⟦<south text>⟧
    append  (current):[BID s] ⟦<south text>⟧ <partner text AFTER s>

so each anchor is parsed as `L ⟦T⟧ R`: T is South's own justification (the ⟦ ⟧
brackets make that split exact), L belongs to the partner call immediately
BEFORE this South call, R to the partner call immediately AFTER it.

A `[BID Pass]` whose T is generated ("You pass." / "You pass; 4\\H is the final
contract.") is fold output, not source — it is dropped and regenerated. A pass
carrying AUTHORED prose is kept as a real curated chunk, which the value-matching
fold now binds correctly.

The intro/partner-opening split is the one genuinely ambiguous point, but fold
rejoins the two with a single space, so ANY split reproduces the served file
byte-for-byte; we pick the trailing sentence naming partner's call so the curated
file reads correctly for a human author.

Correctness is proven by round-trip, not inspection: unfold -> nonrotate ->
bridge_classroom must reproduce the served file exactly, modulo the intentionally
added `[BID Pass]` anchors.
"""
import re
import sys

SEATS = ['N', 'E', 'S', 'W']
CALL_RE = r'(?:Pass|X|XX|[1-7](?:NT?|[SHDC]))'
SYNTH_PASS = re.compile(r'^You pass(?:\.\s*$|;\s*\S+\s+is the final contract\.\s*$)')


def auction_seats(chunk):
    dealer = re.search(r'\[Dealer "([NESW])"\]', chunk).group(1)
    am = re.search(r'\[Auction "[NESW]"\]\s*(.*?)(?=\n\[|\n\{)', chunk, re.S)
    calls = [re.sub(r'=\d+=', '', t) for t in am.group(1).split()]
    calls = [c for c in calls if re.fullmatch(CALL_RE, c)]
    i = SEATS.index(dealer)
    return [(SEATS[(i + k) % 4], c) for k, c in enumerate(calls)]


def parse_folded(block):
    """-> (intro, [(call, L, T, R)], reflection)"""
    parts = re.split(r'(\[BID [^\]]+\]|\[show N(?:S|ESW)\])', block)
    intro = re.sub(r'^\s*\[show [^\]]+\]\s*', '', parts[0]).strip()
    anchors, reflection = [], ''
    i = 1
    while i < len(parts):
        marker, body = parts[i], (parts[i + 1] if i + 1 < len(parts) else '')
        if marker.startswith('[BID'):
            call = marker[len('[BID '):-1].strip()
            m = re.match(r'^(.*?)⟦(.*?)⟧(.*)$', body.strip(), re.S)
            if m:
                anchors.append((call, m.group(1).strip(),
                                m.group(2).strip(), m.group(3).strip()))
            else:                       # unbracketed: already pre-fold prose
                anchors.append((call, '', body.strip(), ''))
        elif marker in ('[show NS]', '[show NESW]'):
            reflection = body.strip()
        i += 2
    return intro, anchors, reflection


def split_intro(intro, partner_call):
    """Split served intro into (curated intro, partner's opening text)."""
    sents = [s for s in re.findall(r'[^.!?]*[.!?]+(?:\s|$)|[^.!?]+$', intro) if s.strip()]
    strain = partner_call[-1]
    needle = partner_call[0] + (('\\' + strain) if strain in 'SHDC' else '')
    for k in range(len(sents) - 1, -1, -1):
        tail = ''.join(sents[k:]).strip()
        if needle in tail or re.search(r'\bpartner\b', tail, re.I):
            return ''.join(sents[:k]).strip(), tail
    return intro, ''


def unfold_board(chunk):
    seats = auction_seats(chunk)
    block = chunk[chunk.rfind('{') + 1: chunk.rfind('}')]
    if '⟦' not in block:
        # Already pre-fold: fold() always brackets South's own justification, so a
        # block with no ⟦ ⟧ has not been folded. Skip it, which makes the whole
        # script safely re-runnable on a partly-repaired file (and on a healthy one,
        # a no-op) instead of failing on partner's legitimate [BID] anchors.
        return None
    intro, anchors, reflection = parse_folded(block)
    if not anchors:
        return None                                     # play board

    # Bind each anchor to the South call it explains (value walk, as fold does).
    south = [i for i, (s, _) in enumerate(seats) if s == 'S']
    amap, p = {}, 0
    for call, L, T, R in anchors:
        j = p
        while j < len(south) and seats[south[j]][1] != call:
            j += 1
        if j >= len(south):
            raise AssertionError(f'anchor [BID {call}] matches no South call')
        amap[south[j]] = [L, T, R]
        p = j + 1

    out = []
    for i, (seat, call) in enumerate(seats):
        if seat not in 'NS':
            continue
        if seat == 'S':
            if i in amap:
                T = amap[i][1]
                if not (call == 'Pass' and SYNTH_PASS.match(T)):
                    out.append((call, T))               # keep AUTHORED pass prose
        elif call != 'Pass':
            # partner's text sits in the R of the nearest preceding anchor, or the
            # L of the nearest following one; consume it so it is used once.
            # Scan BACK through every preceding anchor for an unconsumed R (an
            # intervening anchor — typically a synthesized pass — often carries
            # none, so stopping at the nearest one drops the text), then FORWARD
            # through the following anchors for an unconsumed L.
            text = ''
            prev = sorted([k for k in amap if k < i], reverse=True)
            nxt = sorted(k for k in amap if k > i)
            for k in prev:
                if amap[k][2]:
                    text, amap[k][2] = amap[k][2], ''
                    break
            if not text:
                for k in nxt:
                    if amap[k][0]:
                        text, amap[k][0] = amap[k][0], ''
                        break
            if not text and not prev:                   # partner opened: in the intro
                intro, text = split_intro(intro, call)
            # Emit even when empty: `coach.py validate` requires a [BID] for every
            # N/S call, and a partner call the author never wrote prose for is
            # faithfully an empty chunk. fold() skips empty partner text, so this
            # cannot reintroduce a stray separator.
            out.append((call, text))

    lines = ['{' + intro]
    for call, text in out:
        lines.append(f'[BID {call}] {text}'.rstrip())
    lines.append('[show NESW]' + reflection + '}')
    return '\n'.join(lines)


def main():
    scn = sys.argv[1]
    src = f'coaching-curated/{scn}.pbn'
    chunks = re.split(r'(?=\[Event )', open(src).read())
    n = 0
    for i, ch in enumerate(chunks):
        if '[Deal ' not in ch or '{' not in ch:
            continue
        new = unfold_board(ch)
        if new is None:
            continue
        chunks[i] = ch[:ch.rfind('{')] + new + ch[ch.rfind('}') + 1:]
        n += 1
    open(src, 'w').write(''.join(chunks))
    print(f'{scn}: unfolded {n} boards -> {src}')


if __name__ == '__main__':
    main()
