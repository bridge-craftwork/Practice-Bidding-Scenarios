#!/usr/bin/env python3
"""spiral_auction.py — generate Spiral Raises convention auctions for
the Spiral Raises scenarios (see notes/plans/convention-auction-curation-plan.md).

BBA (21GF-DEFAULT) does not play Spiral Raises, so bba/Spiral_Raises_Wolpert.pbn
holds natural 2/1 auctions. The hands, however, are built so the spiral-raise
decision arises. This script computes the CORRECT spiral auction for each board
deterministically from the South/North hands, so it can be substituted into
bba-curated/ as the trainer's quiz answer key.

Stages (run from repo root):
    python3 py/spiral_auction.py report      # Gate-1 self-verify + HCP distribution
    python3 py/spiral_auction.py generate    # write the deal_hash-keyed sidecar
    python3 py/spiral_auction.py substitute  # rewrite [Auction] in bba-curated/

The convention ladder (the load-bearing spec) is confirmed with David at Gate 1
before any coaching prose is authored.
"""
import sys, os, re, json
# Append (not prepend) py/ so stdlib `select` wins over py/select.py — and run
# this script with `python3 -P` so the script dir isn't auto-prepended either.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.append(_HERE)
import curate
from curate import hands, deal_hash, tag, split_boards, hcp_of, SUITS

SCN = os.environ.get('SPIRAL_SCN', 'Spiral_Raises_Wolpert')
SI = {'S': 0, 'H': 1, 'D': 2, 'C': 3}          # index into hands()'s [S,H,D,C] lists
CALL_RE = re.compile(r'^(Pass|X|XX|AP|[1-7][CDHSN])$')

# HCP boundary inside South's 12-14 window: hcp >= MAX_CUTOFF counts as "max".
# Config-driven: the .btn '# curate:' directive (spiral_max_cutoff=NN), overridable
# by env for experimentation. The report shows the per-rung distribution.
_DIRECTIVE = curate.curate_directive(SCN) or {}
MAX_CUTOFF = int(os.environ.get('SPIRAL_MAX_CUTOFF',
                                _DIRECTIVE.get('spiral_max_cutoff', '14')))

# Which convention overlay to generate. 'spiral' (default) = the Wolpert
# cheapest-step ladder below. 'weinstein' = 2NT ask in both cases + a natural
# fit-find for the other major + a simple 4-rung answer set. Selected by the
# .btn '# curate:' directive (convention=weinstein), env-overridable for runs.
SCHEME = (os.environ.get('SPIRAL_SCHEME')
          or _DIRECTIVE.get('convention') or 'spiral').lower()

# --- the spiral answer ladder -------------------------------------------------
# One semantic ladder (ascending step order); rendered to concrete calls per
# response. Heart response: ask = 2S. Spade response: ask = 2N, answers shifted
# up exactly one step. 1C vs 1D only relabels which suit is "other minor" /
# "opened minor" in the rung MEANINGS; the calls do not move.
RUNG_ORDER = [
    '3card_bal_min', '4card_bal', '3card_short_ominor', '3card_short_omajor',
    '4card_splinter_omajor', '3card_bal_max', '4card_splinter_ominor',
    '5422_max', '5422_min',
]
HEART_CALLS = ['2N', '3C', '3D', '3H', '3S', '3N', '4C', '4D', '4H']  # over 2S ask
SPADE_CALLS = ['3C', '3D', '3H', '3S', '3N', '4C', '4D', '4H', '4S']  # over 2N ask
# rung family (min/max collapsed) -> used by the independent self-verify predicates
FAMILY = {
    '3card_bal_min': '3card_bal', '3card_bal_max': '3card_bal',
    '4card_bal': '4card_bal',
    '3card_short_ominor': '3card_short_ominor',
    '3card_short_omajor': '3card_short_omajor',
    '4card_splinter_omajor': '4card_splinter_omajor',
    '4card_splinter_ominor': '4card_splinter_ominor',
    '5422_max': '5422', '5422_min': '5422',
}


def answer_call(rung, responder_major):
    calls = HEART_CALLS if responder_major == 'H' else SPADE_CALLS
    return calls[RUNG_ORDER.index(rung)]


def other_minor(opened_minor):
    return 'D' if opened_minor == 'C' else 'C'


def other_major(responder_major):
    return 'S' if responder_major == 'H' else 'H'


def length(south, suit):
    return len(south[SI[suit]])


def short(south, suit):           # singleton or void
    return length(south, suit) <= 1


def top5_count(cards):            # A,K,Q,J,T
    return sum(1 for c in cards if c in 'AKQJT')


def unguarded(cards):             # the .btn's ruffing-value test: void/stiff, or xx
    return len(cards) < 2 or (len(cards) == 2 and top5_count(cards) == 0)


def is_5422(south, opened_minor, responder_major):
    """5 in the opened minor + 4-card support + 2-2 in the other two suits."""
    om, oM = other_minor(opened_minor), other_major(responder_major)
    return (length(south, responder_major) == 4 and length(south, opened_minor) == 5
            and length(south, om) == 2 and length(south, oM) == 2)


# --- opener's decision (mirrors the .btn) ------------------------------------
def opener_decision(south, responder_major):
    """'four' | 'suitable3' | 'unsuitable3' — which of the .btn's three buckets."""
    support = length(south, responder_major)
    if support >= 4:
        return 'four'
    if support == 3:
        non_support = [s for s in 'SHDC' if s != responder_major]
        if any(unguarded(south[SI[s]]) for s in non_support):
            return 'suitable3'
        return 'unsuitable3'
    return 'no_support'   # should not occur (the .btn guarantees 3+ support)


# --- rung classification (the cascade actually used) -------------------------
def classify_rung(south, opened_minor, responder_major):
    support = length(south, responder_major)
    om, oM = other_minor(opened_minor), other_major(responder_major)
    is_max = hcp_of(south) >= MAX_CUTOFF
    if support == 4:
        if is_5422(south, opened_minor, responder_major):
            return '5422_max' if is_max else '5422_min'
        if short(south, oM):
            return '4card_splinter_omajor'
        if short(south, om):
            return '4card_splinter_ominor'
        return '4card_bal'
    if support == 3:
        if short(south, om):
            return '3card_short_ominor'
        if short(south, oM):
            return '3card_short_omajor'
        return '3card_bal_max' if is_max else '3card_bal_min'
    return None


# --- independent self-verify predicates (rung FAMILIES, min/max collapsed) ----
def matching_families(south, opened_minor, responder_major):
    """Every family whose pure criterion the hand meets. Exactly one => clean."""
    support = length(south, responder_major)
    om, oM = other_minor(opened_minor), other_major(responder_major)
    fams = []
    if support == 3:
        if short(south, om): fams.append('3card_short_ominor')
        if short(south, oM): fams.append('3card_short_omajor')
        if not short(south, om) and not short(south, oM): fams.append('3card_bal')
    elif support == 4:
        if is_5422(south, opened_minor, responder_major):
            fams.append('5422')
        else:
            if short(south, oM): fams.append('4card_splinter_omajor')
            if short(south, om): fams.append('4card_splinter_ominor')
            if not short(south, oM) and not short(south, om): fams.append('4card_bal')
    return fams


# --- board parsing -----------------------------------------------------------
def auction_calls(chunk):
    m = re.search(r'\[Auction "\w"\]\s*\n((?:[^\[{][^\n]*\n?)*)', chunk)
    if not m:
        return []
    return [t for t in m.group(1).split() if CALL_RE.match(t)]


def board_spiral(chunk):
    """Returns a per-board dict: opening/response read from BBA, opener decision,
    rung, coded answer, and any anomaly/ambiguity flags. Auction placement is
    added in a later stage (post Gate-1)."""
    deal = tag(chunk, 'Deal')
    board = tag(chunk, 'Board')
    rec = {'board': board, 'deal_hash': deal_hash(deal) if deal else None}
    if not deal:
        rec['flag'] = 'no-deal'; return rec
    h = hands(deal)
    south = h['S']
    calls = auction_calls(chunk)
    rec['hcp_south'] = hcp_of(south)
    rec['hcp_north'] = hcp_of(h['N'])
    # opening + 1-level response come from BBA (natural, agreed by both systems)
    if len(calls) < 3 or not re.match(r'1[CD]$', calls[0]) or not re.match(r'1[HS]$', calls[2]):
        rec['flag'] = f'unexpected-open/resp:{calls[:3]}'; return rec
    if calls[1] != 'Pass' or (len(calls) > 3 and calls[3] != 'Pass'):
        rec['flag'] = 'opponents-not-silent'; return rec
    opened_minor = calls[0][1]
    responder_major = calls[2][1]
    rec['opened_minor'] = opened_minor
    rec['responder_major'] = responder_major
    rec['case'] = f'1{opened_minor}-1{responder_major}'
    rec['opening'] = calls[0]
    rec['response'] = calls[2]
    rec['decision'] = opener_decision(south, responder_major)
    if rec['decision'] in ('four', 'suitable3'):
        rec['kind'] = 'raise'
        rec['raise_call'] = '2' + responder_major
        if SCHEME == 'weinstein':
            # Weinstein: 2NT ask in both cases. The ask-vs-natural choice, the
            # rung, and the answer need North's hand, so they are filled in
            # w_build_record_raise() at the build_record stage.
            rec['ask_call'] = '2N'
        else:
            fams = matching_families(south, opened_minor, responder_major)
            rec['families'] = fams
            if len(fams) == 0:
                rec['flag'] = 'NO-RUNG'
            elif len(fams) > 1:
                rec['flag'] = 'AMBIGUOUS:' + ','.join(fams)
            rung = classify_rung(south, opened_minor, responder_major)
            rec['rung'] = rung
            rec['answer'] = answer_call(rung, responder_major) if rung else None
            rec['ask_call'] = '2S' if responder_major == 'H' else '2N'
    else:   # unsuitable3 -> decline, keep BBA's natural auction
        rec['kind'] = 'decline'
        rec['natural_rebid'] = calls[4] if len(calls) > 4 else None
    return rec


def all_boards():
    return [board_spiral(ch) for ch in split_boards(f"bba/{SCN}.pbn")]


# --- Gate-1 report -----------------------------------------------------------
def report():
    recs = all_boards()
    raises = [r for r in recs if r.get('kind') == 'raise']
    declines = [r for r in recs if r.get('kind') == 'decline']
    flagged = [r for r in recs if r.get('flag')]
    import collections
    print(f"=== {SCN} — Gate-1 self-verify (MAX_CUTOFF={MAX_CUTOFF}) ===")
    print(f"boards: {len(recs)}  raises: {len(raises)}  declines: {len(declines)}")
    print(f"flagged (anomaly/NO-RUNG/AMBIGUOUS): {len(flagged)}")
    by_case = collections.Counter(r['case'] for r in recs if r.get('case'))
    print("\nby case:", dict(by_case))
    by_decision = collections.Counter(r['decision'] for r in recs if r.get('decision'))
    print("by decision:", dict(by_decision))
    print("\n--- rung distribution (raise boards) ---")
    by_rung = collections.Counter(r['rung'] for r in raises if r.get('rung'))
    for rung in RUNG_ORDER:
        n = by_rung.get(rung, 0)
        # show example calls per case for this rung
        hc = HEART_CALLS[RUNG_ORDER.index(rung)]
        sc = SPADE_CALLS[RUNG_ORDER.index(rung)]
        print(f"  {rung:24} n={n:3}   1m-1H ask2S->{hc:3}   1m-1S ask2N->{sc}")
    print("\n--- HCP distribution on strength-split rungs (set the min/max line) ---")
    for fam in ('3card_bal', '5422'):
        sub = [r for r in raises if r.get('rung') and FAMILY[r['rung']] == fam]
        hcp_dist = collections.Counter(r['hcp_south'] for r in sub)
        print(f"  {fam:10}: South HCP {dict(sorted(hcp_dist.items()))}  (n={len(sub)})")
    print("\n--- decline natural rebids (BBA auction kept) ---")
    print("  ", dict(collections.Counter(r.get('natural_rebid') for r in declines)))
    if flagged:
        print("\n--- FLAGGED boards ---")
        for r in flagged[:40]:
            print(f"  board {r['board']}: {r.get('flag')}  case={r.get('case')} "
                  f"S-hcp={r.get('hcp_south')}")
        if len(flagged) > 40:
            print(f"  ... and {len(flagged)-40} more")
    return recs


# --- responder placement + full auction --------------------------------------
SEATS_FROM_S = ['S', 'W', 'N', 'E']        # dealer South
STRAIN_IDX = {'C': 0, 'D': 1, 'H': 2, 'S': 3, 'N': 4}
RUFFING_FAMILIES = {'3card_short_ominor', '3card_short_omajor',
                    '4card_splinter_omajor', '4card_splinter_ominor', '5422'}


def call_rank(c):
    return (int(c[0]) - 1) * 5 + STRAIN_IDX[c[1]]


def placement(rec):
    """North's final contract after decoding opener's answer. Combined 23-27, so
    no slam zone. Rule (defensible; DD tiers the close ones):
      - game if combined>=25, or >=23 with a ruffing value/extra length;
      - play the major with an 8-card fit OR a 4-3 fit + ruffing value;
        otherwise (4-3 flat) prefer 3NT at game / 2NT-or-3M at partscore;
      - then bump to be a legal call at/over opener's answer."""
    major = rec['responder_major']
    rung = rec['rung']
    family = FAMILY[rung]
    support = rec['support']
    ruffing = family in RUFFING_FAMILIES
    combined = rec['hcp_north'] + rec['hcp_south']
    heart_case = (major == 'H')
    answer = rec['answer']
    game = combined >= 25 or (combined >= 23 and ruffing)
    strain_major = (support == 4) or ruffing
    if game:
        final = '4' + major if strain_major else '3N'
    else:
        final = '3' + major if strain_major else ('2N' if heart_case else '3' + major)
    if call_rank(final) < call_rank(answer):
        # opener's coded answer already overshot the intended partscore -> must
        # land at/above it: play game in the chosen strain.
        if strain_major:
            final = '4' + major
        elif call_rank('3N') >= call_rank(answer):
            final = '3N'
        else:
            final = '4' + major
    return final


def build_calls(rec):
    """List of (seat, call) for a raise board's full spiral auction."""
    seq = [rec['opening'], 'Pass', rec['response'], 'Pass',
           rec['raise_call'], 'Pass', rec['ask_call'], 'Pass',
           rec['answer'], 'Pass']
    if rec['final'] == rec['answer']:
        seq += ['Pass', 'Pass']                       # North passes the answer
    else:
        seq += [rec['final'], 'Pass', 'Pass', 'Pass']  # North places, all pass
    return [(SEATS_FROM_S[i % 4], c) for i, c in enumerate(seq)]


def compute_declarer(calls_seats, strain):
    for seat, c in calls_seats:
        if c in ('Pass', 'X', 'XX'):
            continue
        if c[1] == strain and seat in ('N', 'S'):
            return seat
    return None


def score_ns(level, strain, tricks, vul_ns):
    need = 6 + level
    if tricks >= need:
        if strain in 'CD':
            base = level * 20
        elif strain in 'HS':
            base = level * 30
        else:
            base = 40 + (level - 1) * 30
        over = (tricks - need) * (20 if strain in 'CD' else 30)
        bonus = ((500 if vul_ns else 300) if base >= 100 else 50)
        return base + over + bonus
    return -((need - tricks) * (100 if vul_ns else 50))


def build_record(chunk):
    """Full spiral record for a raise board (auction + contract + declarer +
    result + score), or a decline marker. Keyed for the sidecar by deal_hash."""
    rec = board_spiral(chunk)
    if rec.get('flag'):
        return rec
    deal = tag(chunk, 'Deal')
    if rec.get('kind') == 'decline':
        # decline boards keep BBA's natural auction; classify its contract.
        con = tag(chunk, 'Contract'); dec = tag(chunk, 'Declarer')
        rec['contract'] = con; rec['declarer'] = dec
        if con and con not in ('--', 'Pass') and dec and dec not in (None, '', '?'):
            try:
                rec['dd_class'] = curate.classify(deal, con, dec)[0]
            except Exception:
                rec['dd_class'] = 'error'
        return rec
    if rec.get('kind') != 'raise':
        return rec
    if SCHEME == 'weinstein':
        return w_build_record_raise(rec, deal, chunk)
    h = hands(deal)
    rec['support'] = len(h['S'][SI[rec['responder_major']]])
    rec['final'] = placement(rec)
    calls_seats = build_calls(rec)
    rec['calls'] = [c for _, c in calls_seats]
    contract = next(c for _, c in reversed(calls_seats) if c not in ('Pass', 'X', 'XX'))
    strain = contract[1]
    dec = compute_declarer(calls_seats, strain)
    rec['contract'] = contract
    rec['declarer'] = dec
    tricks = curate.dd(deal, curate.DEN[strain], dec)
    vul = (tag(chunk, 'Vulnerable') or 'None')
    vul_ns = vul in ('NS', 'All', 'Both')
    rec['result'] = tricks
    rec['score'] = f"NS {score_ns(int(contract[0]), strain, tricks, vul_ns)}"
    rec['dd_class'] = curate.classify(deal, contract, dec)[0]
    return rec


def generate():
    recs = [build_record(ch) for ch in split_boards(f"bba/{SCN}.pbn")]
    raises = [r for r in recs if r.get('kind') == 'raise']
    sidecar = {}
    for r in raises:
        sidecar[r['deal_hash']] = {
            'board': r['board'], 'case': r['case'], 'rung': r['rung'],
            'auction': ' '.join(r['calls']), 'contract': r['contract'],
            'declarer': r['declarer'], 'result': r['result'], 'score': r['score'],
            'dd_class': r['dd_class'], 'hcp_south': r['hcp_south'],
            'hcp_north': r['hcp_north'], 'support': r['support'],
        }
    os.makedirs(curate.PROG, exist_ok=True)
    path = f"{curate.PROG}/{SCN}-spiral.json"
    with open(path, 'w') as f:
        json.dump(sidecar, f, indent=1)
    import collections
    cls = collections.Counter(v['dd_class'] for v in sidecar.values())
    con = collections.Counter(v['contract'] for v in sidecar.values())
    print(f"wrote {path}: {len(sidecar)} raise auctions")
    print("contract DD class:", dict(cls))
    print("final contracts:", dict(con.most_common()))
    return recs


def samples(n=2):
    """Print full sample auctions per rung (for Gate-2 review)."""
    recs = [build_record(ch) for ch in split_boards(f"bba/{SCN}.pbn")]
    raises = [r for r in recs if r.get('kind') == 'raise']
    by_rung = {}
    for r in raises:
        by_rung.setdefault(r['rung'], []).append(r)
    for rung in RUNG_ORDER:
        for r in (by_rung.get(rung, [])[:n]):
            print(f"\n[{rung}]  board {r['board']}  {r['case']}  "
                  f"S={r['hcp_south']} N={r['hcp_north']} support={r['support']}")
            print("   auction:", r['auction_str'] if 'auction_str' in r else ' '.join(r['calls']))
            print(f"   -> {r['contract']} by {r['declarer']}  "
                  f"(DD {r['result']} tricks, {r['dd_class']}, {r['score']})")


# --- deterministic grading (Layer B without an LLM pass) ---------------------
# Auctions are generated, so soundness is guaranteed by construction; tier comes
# from DD-makeability of the placed contract + how close the placement is.
GAMES = {'4H', '4S', '3N', '5C', '5D'}
DIFFICULTY = {
    '4card_bal': 2, '3card_bal_min': 2,
    '3card_short_ominor': 3, '3card_short_omajor': 3, '3card_bal_max': 3,
    '4card_splinter_omajor': 4, '4card_splinter_ominor': 4,
    '5422_max': 4, '5422_min': 4,
}


def grade_raise(rec):
    major = rec['responder_major']
    con = rec['contract']
    combined = rec['hcp_south'] + rec['hcp_north']
    if rec.get('dd_class') == 'wrong_sided':
        return 'reject', [], 'Contract makes only from the wrong seat.'
    also = []
    if rec['support'] == 3 and con == '4' + major:        # 4-3 ruff game vs 3NT
        also.append('3N')
    if con in GAMES and combined <= 24 and con == '4' + major and ('3' + major) not in also:
        also.append('3' + major)                          # aggressive game on min values
    if also:
        return 'judgment', also, f'Close: {con} vs {"/".join(also)} on {combined} combined.'
    if rec.get('dd_class') == 'down_both':
        return 'standard', [], f'Bid correctly; {con} is against the odds on this layout.'
    return 'textbook', [], f'Clean spiral to {con}.'


def grade_decline(rec):
    con = rec.get('contract')
    if not con or con in ('--', 'Pass') or not rec.get('declarer'):
        return 'reject', [], 'Passed out / no contract.'
    if rec.get('dd_class') in ('wrong_sided', 'error'):
        return 'reject', [], 'Wrong seat / undefined contract.'
    if rec.get('dd_class') == 'down_both':
        return 'standard', [], f'{con} against the odds; the decline itself is clear.'
    return 'textbook', [], f'Opener declines the raise, rebids {rec.get("natural_rebid")}.'


PLAY_NOTE = 'Bidding lesson — declarer/defense play not curated.'


def format_auction(calls):
    """Render calls into the file's 4-column PBN block style."""
    rows = []
    for i in range(0, len(calls), 4):
        rows.append("".join(f"{c:<6}" for c in calls[i:i + 4]).rstrip())
    return "\n".join(rows) + "\n"


def substitute():
    """Rewrite the raise boards' [Auction] (+ Contract/Declarer/Result/Score) in
    bba-curated/<scn>.pbn with the generated spiral auction, leaving the
    {Curate}/{Shape}/{HCP}/{Losers} blocks and the decline boards untouched."""
    path = f"bba-curated/{SCN}.pbn"
    sidecar = json.load(open(f"{curate.PROG}/{SCN}-spiral.json"))
    out, nsub = [], 0
    for ch in split_boards(path):
        d = tag(ch, 'Deal')
        s = sidecar.get(deal_hash(d)) if d else None
        if not s:
            out.append(ch); continue
        body = format_auction(s['auction'].split())
        ch = re.sub(r'(\[Auction "[^"]*"\]\n)(?:[^\[{][^\n]*\n)*',
                    lambda m: m.group(1) + body, ch, count=1)
        ch = re.sub(r'\[Contract "[^"]*"\]', f'[Contract "{s["contract"]}"]', ch)
        ch = re.sub(r'\[Declarer "[^"]*"\]', f'[Declarer "{s["declarer"]}"]', ch)
        ch = re.sub(r'\[Result "[^"]*"\]', f'[Result "{s["result"]}"]', ch)
        ch = re.sub(r'\[Score "[^"]*"\]', f'[Score "{s["score"]}"]', ch)
        out.append(ch); nsub += 1
    with open(path, 'w') as f:
        f.write("".join(out))
    print(f"substituted {nsub} spiral auctions into {path}")


def grade():
    verdicts, n_raise, n_decline, skipped = [], 0, 0, 0
    for ch in split_boards(f"bba/{SCN}.pbn"):
        rec = build_record(ch)
        kind = rec.get('kind')
        if kind == 'raise':
            tier, also, note = grade_raise(rec)
            diff = (W_DIFFICULTY if SCHEME == 'weinstein' else DIFFICULTY)[rec['rung']]
            themes = ['spiral', rec['rung'].replace('_', '-')]
            n_raise += 1
        elif kind == 'decline':
            tier, also, note = grade_decline(rec)
            diff = 3
            themes = ['decline', 'decline-' + (rec.get('natural_rebid') or 'x')]
            n_decline += 1
        else:
            skipped += 1
            continue
        verdicts.append({
            'board': rec['board'], 'deal_hash': rec['deal_hash'],
            'auction_class': 'intended', 'difficulty': diff,
            'bidding': {'tier': tier, 'also_ok': also, 'note': note, 'themes': themes},
            'declarer': {'tier': 'reject', 'themes': [], 'note': PLAY_NOTE},
            'defense': {'tier': 'reject', 'themes': [], 'note': PLAY_NOTE},
            'dd_class': rec.get('dd_class'),
        })
    out = {'scenario': SCN, 'graded': len(verdicts), 'verdicts': verdicts,
           'note': 'Deterministic grading; auctions generated by spiral_auction.py.'}
    with open(f"bba-curated/{SCN}-graded.json", 'w') as f:
        json.dump(out, f, indent=1)
    import collections
    print(f"graded {len(verdicts)}  (raises {n_raise}, declines {n_decline}, skipped {skipped})")
    print("bidding tiers:", dict(collections.Counter(v['bidding']['tier'] for v in verdicts)))
    print("difficulty   :", dict(sorted(collections.Counter(v['difficulty'] for v in verdicts).items())))


def board_decode(chunk):
    """Per-call decode for the authoring subagent: (seat, call, role, meaning) for
    every N/S non-pass call, so prose states VERIFIED convention meanings."""
    rec = build_record(chunk)
    if rec.get('kind') == 'raise':
        if SCHEME == 'weinstein':
            return w_decode_raise(rec, chunk)
        om, oM = other_minor(rec['opened_minor']), other_major(rec['responder_major'])
        rm, opm = rec['responder_major'], rec['opened_minor']
        ANS = {
            '3card_bal_min': "three-card support, balanced, minimum — no shortness, nothing extra; coded, not natural",
            '3card_bal_max': "three-card support, balanced, maximum; coded",
            '4card_bal': "four-card support, balanced (no shortness); coded",
            '3card_short_ominor': f"three-card support with shortness in the other minor ({om}) — a ruffing value; coded",
            '3card_short_omajor': f"three-card support with shortness in the other major ({oM}) — a ruffing value; coded",
            '4card_splinter_omajor': f"four-card support with a splinter (singleton/void) in the other major ({oM}); coded",
            '4card_splinter_ominor': f"four-card support with a splinter in the other minor ({om}); coded",
            '5422_max': f"five in the opened minor ({opm}) plus four-card support (5-4-2-2), maximum; coded",
            '5422_min': "5-4-2-2 with four-card support, minimum; coded",
        }
        tier, also, _ = grade_raise(rec)
        calls = [
            ('S', rec['opening'], 'open', f"opening 12-14, no five-card major, the longer minor ({opm}); says nothing about the majors"),
            ('N', rec['response'], 'response', f"four or more {rm}, at least invitational values"),
            ('S', rec['raise_call'], 'raise', f"agrees {rm} on three- OR four-card support — opens the spiral description, not a limit bid"),
            ('N', rec['ask_call'], 'ask', f"the spiral ask ({rec['ask_call']}): artificial and forcing; asks opener to spell out trump length, strength, and shortness"),
            ('S', rec['answer'], 'answer', ANS[rec['rung']]),
        ]
        if rec['final'] != rec['answer']:
            if tier == 'judgment':
                pm = f"borderline: {rec['final']} or {' '.join(also)} — both defensible (quiz accepts {' '.join(also)}); the shown shape tips it to {rec['final']}"
            elif rec['final'] in GAMES:
                pm = f"game values opposite the shown hand — bid game, {rec['final']}"
            else:
                pm = f"minimum opposite the shown hand — stop in {rec['final']}"
            calls.append(('N', rec['final'], 'place', pm))
        return {'kind': 'raise', 'tier': tier, 'also_ok': also, 'calls': calls}
    if rec.get('kind') == 'decline':
        ac = auction_calls(chunk); seats = ['S', 'W', 'N', 'E']
        calls = [
            ('S', ac[0], 'open', "opening 12-14, no five-card major, the longer minor"),
            ('N', ac[2], 'response', f"four or more {ac[2][1]}, at least invitational values"),
            ('S', ac[4], 'decline', f"declines to raise — only three-card support and no ruffing value (flat/10x), so describes the hand naturally ({ac[4]}) instead of agreeing the major; the flip side of the spiral, when NOT to raise"),
        ]
        for i in range(5, len(ac)):
            seat, c = seats[i % 4], ac[i]
            if seat in ('N', 'S') and c not in ('Pass', 'X', 'XX'):
                calls.append((seat, c, 'continuation', "natural 2/1 continuation — coach with its standard meaning"))
        return {'kind': 'decline', 'tier': grade_decline(rec)[0], 'also_ok': [], 'calls': calls}
    return {'kind': 'skip'}


def augment():
    import glob
    boards = json.load(open(f"coaching-curated/.work/{SCN}-boards.json"))
    decode = {}
    for ch in split_boards(f"bba-curated/{SCN}.pbn"):
        b = tag(ch, 'Board')
        if b in boards:
            decode[b] = board_decode(ch)
    for pf in glob.glob(f"coaching-curated/.work/{SCN}-pkt*.json"):
        data = json.load(open(pf))
        for bd in data:
            bd['decode'] = decode.get(bd['board'])
        json.dump(data, open(pf, 'w'), indent=0)
    print(f"augmented {len(decode)} boards with spiral decode")


# === Weinstein scheme =========================================================
# Spiral_Raises_Weinstein (convention=weinstein / SPIRAL_SCHEME=weinstein).
# Responder asks with 2NT in BOTH cases. UNDERNEATH the ask, a natural fit-find
# shows the other major: 2S after a 1H response, 3H after a 1S response. Opener's
# answers to the 2NT ask are a simple 4-rung ladder (no shortness shown):
#   3C = min / 3-card    3D = max / 3-card    3H = min / 4-card    3S = max / 4-card
# The raise-vs-decline split, board parsing, DD/scoring, the grading framework,
# and the entire decline path are SHARED with the spiral scheme above; only the
# raise auction (ask vs natural, answers, placement, decode) is new here.
#
# Bridge-judgment defaults flagged for Gate-1 review with David:
#   * natural fit-find triggers when North holds 4+ of the OTHER major;
#   * 4-4 found -> play the other major; otherwise revert to the agreed major;
#   * placement is coarse (no shortness shown): combined >= 25 => game,
#     8+ card fit plays the major, a 4-3 plays NT at game / the major partscore;
#   * min/max uses the same MAX_CUTOFF (14) as the spiral scheme.
W_ANSWER = {(False, False): '3C', (True, False): '3D',
            (False, True): '3H', (True, True): '3S'}   # (is_max, support>=4) -> call
W_RUNG = {'3C': 'ask_min3', '3D': 'ask_max3', '3H': 'ask_min4', '3S': 'ask_max4'}
W_DIFFICULTY = {'ask_min4': 2, 'ask_max4': 2, 'ask_min3': 3, 'ask_max3': 3,
                'natural_fit': 3, 'natural_revert': 3}
W_ANS_MEANING = {
    'ask_min3': "three-card support, minimum; coded answer to the 2NT ask",
    'ask_max3': "three-card support, maximum; coded",
    'ask_min4': "four-card support, minimum; coded",
    'ask_max4': "four-card support, maximum; coded",
}


def w_placement(rec):
    """Responder's final contract on the ASK path. Opener has shown support
    length (3/4) and strength (min/max) but NOT shortness, so placement is
    coarser than the spiral: combined >= 25 => game; an 8+ card fit plays the
    major, a 4-3 plays notrump; then bump to be legal at/over opener's answer."""
    major = rec['responder_major']
    fit = rec['support'] + rec['north_major']
    combined = rec['hcp_north'] + rec['hcp_south']
    answer = rec['answer']
    game = combined >= 25
    strain_major = fit >= 8
    if game:
        final = '4' + major if strain_major else '3N'
    else:
        final = '3' + major            # major partscore (a 4-3 here is a Moysian)
    if call_rank(final) < call_rank(answer):   # answer overshot -> land at/over it
        final = '4' + major if strain_major else '3N'
    return final


def w_build_record_raise(rec, deal, chunk):
    """Weinstein raise board: choose ASK (2NT) vs NATURAL fit-find from North's
    other-major length, build the full auction, then contract/declarer/DD/score.
    Returns the same rec shape the shared generate()/grade()/substitute() expect."""
    h = hands(deal)
    major = rec['responder_major']
    oM = other_major(major)
    rec['support'] = len(h['S'][SI[major]])            # opener's support (3 or 4)
    rec['north_major'] = len(h['N'][SI[major]])
    north_oM = len(h['N'][SI[oM]])
    opener_oM = len(h['S'][SI[oM]])
    is_max = hcp_of(h['S']) >= MAX_CUTOFF
    combined = rec['hcp_north'] + rec['hcp_south']
    game = combined >= 25

    if north_oM >= 4:                                  # NATURAL fit-find branch
        rec['path'] = 'natural'
        fit_call = '2S' if major == 'H' else '3H'
        rec['fit_call'] = fit_call
        if opener_oM >= 4:                             # 4-4 fit found in the other major
            rec['rung'] = 'natural_fit'
            if major == 'H':                           # ...2S; opener raises spades
                opener_rebid = '3S'
                final = '4S' if game else '3S'
            else:                                      # ...3H; no 3-level heart raise exists
                opener_rebid = '4H' if game else '3H'
                final = '4H' if game else '3H'
        else:                                          # no 4-4; revert to the agreed major
            rec['rung'] = 'natural_revert'
            opener_rebid = '3' + major
            final = '4' + major if game else '3' + major
        rec['ask_call'] = None
        rec['answer'] = opener_rebid                   # opener's descriptive rebid
        seq = [rec['opening'], 'Pass', rec['response'], 'Pass',
               rec['raise_call'], 'Pass', fit_call, 'Pass',
               opener_rebid, 'Pass']
    else:                                              # ASK branch (2NT)
        rec['path'] = 'ask'
        rec['ask_call'] = '2N'
        answer = W_ANSWER[(is_max, rec['support'] >= 4)]
        rec['answer'] = answer
        rec['rung'] = W_RUNG[answer]
        final = w_placement(rec)
        seq = [rec['opening'], 'Pass', rec['response'], 'Pass',
               rec['raise_call'], 'Pass', rec['ask_call'], 'Pass',
               answer, 'Pass']

    rec['final'] = final
    if final == rec['answer']:
        seq += ['Pass', 'Pass']                        # responder passes opener's rebid
    else:
        seq += [final, 'Pass', 'Pass', 'Pass']         # responder places, all pass

    calls_seats = [(SEATS_FROM_S[i % 4], c) for i, c in enumerate(seq)]
    rec['calls'] = [c for _, c in calls_seats]
    contract = next(c for _, c in reversed(calls_seats) if c not in ('Pass', 'X', 'XX'))
    strain = contract[1]
    dec = compute_declarer(calls_seats, strain)
    rec['contract'] = contract
    rec['declarer'] = dec
    tricks = curate.dd(deal, curate.DEN[strain], dec)
    vul = (tag(chunk, 'Vulnerable') or 'None')
    vul_ns = vul in ('NS', 'All', 'Both')
    rec['result'] = tricks
    rec['score'] = f"NS {score_ns(int(contract[0]), strain, tricks, vul_ns)}"
    rec['dd_class'] = curate.classify(deal, contract, dec)[0]
    return rec


def w_decode_raise(rec, chunk):
    """Per-call decode for the authoring subagent (Weinstein raise boards), so the
    coaching prose states VERIFIED meanings rather than reinventing them."""
    major = rec['responder_major']
    oM = other_major(major)
    opm = rec['opened_minor']
    tier, also, _ = grade_raise(rec)
    open_meaning = f"opening 12-14, no five-card major, the longer minor ({opm}); says nothing about the majors"
    resp_meaning = f"four or more {major}, at least invitational values"
    raise_meaning = f"agrees {major} on three- OR four-card support — minimum or better; opens the Weinstein structure, not a limit bid"
    if rec.get('path') == 'natural':
        if rec['rung'] == 'natural_fit':
            rebid_meaning = f"raises the new suit — opener also holds four {oM}, so the 4-4 {oM} fit is found and is the better strain"
        else:
            rebid_meaning = f"no four-card {oM}; returns to the agreed {major}, the known fit"
        calls = [
            ('S', rec['opening'], 'open', open_meaning),
            ('N', rec['response'], 'response', resp_meaning),
            ('S', rec['raise_call'], 'raise', raise_meaning),
            ('N', rec['fit_call'], 'fit-find', f"natural and forcing: four or more {oM}, hunting a 4-4 {oM} fit instead of asking with 2NT"),
            ('S', rec['answer'], 'rebid', rebid_meaning),
        ]
    else:
        calls = [
            ('S', rec['opening'], 'open', open_meaning),
            ('N', rec['response'], 'response', resp_meaning),
            ('S', rec['raise_call'], 'raise', raise_meaning),
            ('N', '2N', 'ask', "the 2NT ask: artificial and forcing, asking opener to show support length and strength (no shortness in this simple version)"),
            ('S', rec['answer'], 'answer', W_ANS_MEANING[rec['rung']]),
        ]
    if rec['final'] != rec['answer']:
        if tier == 'judgment':
            pm = f"borderline: {rec['final']} or {' '.join(also)} — both defensible (quiz accepts {' '.join(also)})"
        elif rec['final'] in GAMES:
            pm = f"game values opposite the shown hand — bid game, {rec['final']}"
        else:
            pm = f"minimum opposite the shown hand — stop in {rec['final']}"
        calls.append(('N', rec['final'], 'place', pm))
    return {'kind': 'raise', 'tier': tier, 'also_ok': also, 'calls': calls}


def w_report():
    """Weinstein Gate-1 self-verify: path split, rung/contract/DD distribution,
    the min/max HCP boundary, decline rebids, flags, and sample auctions."""
    import collections
    recs = [build_record(ch) for ch in split_boards(f"bba/{SCN}.pbn")]
    raises = [r for r in recs if r.get('kind') == 'raise']
    declines = [r for r in recs if r.get('kind') == 'decline']
    flagged = [r for r in recs if r.get('flag')]
    asks = [r for r in raises if r.get('path') == 'ask']
    nats = [r for r in raises if r.get('path') == 'natural']
    print(f"=== {SCN} — Weinstein Gate-1 self-verify (MAX_CUTOFF={MAX_CUTOFF}) ===")
    print(f"boards: {len(recs)}  raises: {len(raises)}  declines: {len(declines)}  flagged: {len(flagged)}")
    print("by case:", dict(collections.Counter(r['case'] for r in recs if r.get('case'))))
    print(f"\nraise paths:  ask={len(asks)}  natural={len(nats)}")
    print("  ask rungs    :", dict(collections.Counter(r['rung'] for r in asks)))
    print("  natural rungs:", dict(collections.Counter(r['rung'] for r in nats)))
    print("\nfinal contracts:", dict(collections.Counter(r.get('contract') for r in raises).most_common()))
    print("DD class       :", dict(collections.Counter(r.get('dd_class') for r in raises)))
    print("\n--- min/max HCP boundary (ask path) ---")
    for lab, sub in (('ask 3-card', [r for r in asks if r['support'] == 3]),
                     ('ask 4-card', [r for r in asks if r['support'] == 4])):
        dist = dict(sorted(collections.Counter(r['hcp_south'] for r in sub).items()))
        print(f"  {lab}: South HCP {dist}  (n={len(sub)})")
    print("\n--- decline natural rebids (BBA auction kept) ---")
    print("  ", dict(collections.Counter(r.get('natural_rebid') for r in declines)))
    if flagged:
        print("\n--- FLAGGED ---")
        for r in flagged[:40]:
            print(f"  board {r['board']}: {r.get('flag')}  case={r.get('case')}")
        if len(flagged) > 40:
            print(f"  ... and {len(flagged) - 40} more")
    print("\n--- one sample auction per rung ---")
    seen = set()
    for r in raises:
        if r.get('rung') in seen:
            continue
        seen.add(r['rung'])
        print(f"  [{r['rung']}] board {r['board']} {r['case']} "
              f"S={r['hcp_south']} N={r['hcp_north']} sup={r['support']} "
              f"-> {r['contract']} ({r['dd_class']}, {r['result']} tricks)")
        print("     ", ' '.join(r['calls']))
    return recs


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "report":
        (w_report if SCHEME == 'weinstein' else report)()
    elif cmd == "generate":
        generate()
    elif cmd == "grade":
        grade()
    elif cmd == "augment":
        augment()
    elif cmd == "samples":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        samples(n)
    elif cmd == "substitute":
        substitute()
    else:
        sys.exit(f"unknown stage '{cmd}'")
