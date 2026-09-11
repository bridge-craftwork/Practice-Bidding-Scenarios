#!/usr/bin/env python3
"""curate.py — Layer A of the curate pipeline op (see notes/plans/pbn-curation-plan.md).

Generalizes the (since retired) curation_trial.py prototype across all coaching scenarios:
  - DD soundness classify (ok / wrong_sided / down_both) vs each board's own
    contract, for the current coaching set AND the full bba/ pool
  - by-force honor-swap test (by-force lessons)
  - hold-up single-dummy oracle (Hold_Up_3N)
  - avoidance shape filter (finesse-choice lessons)
  - matched_intended_auction: the .btn '# auction-filter' regex, demoted to a
    feature; cross-checked against actual bba-filtered/ membership
  - freak/void flags, HCP, duplicate detection (deal_hash)

Emits bba-curated/<scenario>.json + bba-curated/<scenario>-report.md.
No PBN selection yet (that follows Layer B grading). Run from repo root:
    python3 py/curate.py [scenario ...]      # default: all 20
"""
import sys, os, re, json, time, hashlib, collections
from endplay.types import Deal, Denom, Player, Card
from endplay.dds import calc_dd_table, solve_board

# Time-budgeted, resumable execution: progress is checkpointed per board to
# bba-curated/.progress/*.jsonl so the run can be driven by repeated short
# invocations (the Cowork sandbox kills long-running calls). Set
# CURATE_BUDGET (seconds) per invocation; rerun until "ALL-COMPLETE".
BUDGET = float(os.environ.get('CURATE_BUDGET', '30'))
START = time.time()
def out_of_time():
    return time.time() - START > BUDGET

DEN = {'C': Denom.clubs, 'D': Denom.diamonds, 'H': Denom.hearts,
       'S': Denom.spades, 'N': Denom.nt}
PL = {'N': Player.north, 'E': Player.east, 'S': Player.south, 'W': Player.west}
PART = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}
SUITS = ['S', 'H', 'D', 'C']
HCP = {'A': 4, 'K': 3, 'Q': 2, 'J': 1}
RANK = "AKQJT98765432"

def curate_directive(scn):
    """Parse '# curate: kind=... [oracle=...] [contract=...] [seat=...]' from
    the .btn master. Returns dict or None. The .btn is the source of truth;
    CONFIG below is only a fallback for scenarios without a directive."""
    path = f"btn/{scn}.btn"
    if not os.path.exists(path): return None
    for line in open(path, encoding='utf-8', errors='replace'):
        if line.startswith('# curate:'):
            d = dict(kv.split('=', 1) for kv in line[len('# curate:'):].split())
            return d
    return None

# Fallback: scenario -> (kind, oracle). Superseded by the .btn '# curate:' directive.
CONFIG = {
    'Basic_Major':                 ('bidding',   None),
    'Basic_Minor':                 ('bidding',   None),
    'Basic_NT':                    ('bidding',   None),
    'Basic_Overcall':              ('bidding',   None),
    'Basic_Takeout_Double':        ('bidding',   None),
    'Basic_Weak_2':                ('bidding',   None),
    'Basic_What_To_Open':          ('bidding',   None),
    'Play_Top_Tricks':             ('byforce',   None),   # any contract, own
    'Play_Top_Tricks_NT':          ('byforce',   None),
    'Play_Top_Tricks_Suit':        ('byforce',   None),
    'Rabbis_Rule':                 ('byforce',   None),
    'Suit_Promotion':              ('byforce',   None),
    'Finesse_Simple':              ('soundness', None),
    'Endplay_3rd_Round_Strip':     ('soundness', None),
    'Side_Suit_Ruff_Before_Trump': ('soundness', None),
    'Hold_Up_3N':                  ('avoidance', 'holdup'),
    'Choice_Of_Finesses':          ('avoidance', 'shape'),
    'Two_Way_Finesse':             ('avoidance', 'shape'),
    'To_Finesse_Or_Not_To_Finesse': ('avoidance', 'shape'),
}

_dd_cache = {}
def dd(deal_str, strain, seat):
    t = _dd_cache.get(deal_str)
    if t is None:
        t = calc_dd_table(Deal(deal_str)); _dd_cache[deal_str] = t
    return t[strain, PL[seat]]

def split_boards(path):
    """Split a PBN file into per-board raw chunks on [Event lookahead."""
    raw = open(path, encoding='utf-8', errors='replace').read()
    parts = re.split(r'(?=^\[Event )', raw, flags=re.M)
    return [p for p in parts if p.startswith('[Event')]

def tag(chunk, name):
    m = re.search(r'\[' + name + r' "([^"]*)"\]', chunk)
    return m.group(1) if m else None

def hands(deal_str):
    body = deal_str.split(":")[1].split()
    start = deal_str.split(":")[0]
    order = {'N': ['N','E','S','W'], 'E': ['E','S','W','N'],
             'S': ['S','W','N','E'], 'W': ['W','N','E','S']}[start]
    return {s: body[i].split('.') for i, s in enumerate(order)}

def hcp_of(suits):
    return sum(HCP.get(c, 0) for su in suits for c in su)

def deal_hash(deal_str):
    return hashlib.sha1(deal_str.encode()).hexdigest()[:16]

def classify(deal_str, con, dec):
    """ok / wrong_sided / down_both vs the board's own contract."""
    strain = DEN[con[1]]; need = 6 + int(con[0])
    d_decl = dd(deal_str, strain, dec)
    d_part = dd(deal_str, strain, PART[dec])
    if d_decl >= need: return 'ok', d_decl, d_part
    if d_part >= need: return 'wrong_sided', d_decl, d_part
    return 'down_both', d_decl, d_part

def swap_ew(deal_str):
    h = hands(deal_str)
    def hs(seat): return '.'.join(h[seat])
    return "N:" + " ".join([hs('N'), hs('W'), hs('S'), hs('E')])

def by_force(deal_str, con, dec):
    strain = DEN[con[1]]; need = 6 + int(con[0])
    if dd(deal_str, strain, dec) < need: return False
    return dd(swap_ew(deal_str), strain, dec) >= need

def lowest(holding): return holding[-1] if holding else None

def lowest_overall(seat_suits):
    best = None
    for si, su in enumerate(SUITS):
        if seat_suits[si]:
            r = seat_suits[si][-1]
            if best is None or RANK.index(r) > RANK.index(best[1]):
                best = (su, r)
    return best[0] + best[1]

def _honor_sequence_top(cards):
    """True if the top 3 cards form a leadable honour sequence headed by an
    honour (T or higher) and you lead the top card. Covers solid sequences
    (KQJ, QJT, JT9) AND broken/interior sequences with a single internal gap
    (KQT, QJ9, JT8) — standard practice leads the top of KQ10 just as for KQJ."""
    if len(cards) < 3: return False
    idx = [RANK.index(c) for c in cards[:3]]
    touching_top = idx[1] == idx[0] + 1          # top two adjacent
    near_third = idx[2] <= idx[1] + 2            # third within one gap
    return touching_top and near_third and RANK.index(cards[0]) <= RANK.index('T')

def opening_lead_vs_nt(west_suits):
    """West's standard opening lead vs notrump: 4th-best from the longest,
    strongest suit (top of a 3+ honor sequence if present). Returns (suit_idx,
    rank) or None if West is void everywhere. west_suits is [S,H,D,C] rank strings."""
    best = None  # (length, hcp, suit_idx)
    for si, cards in enumerate(west_suits):
        if not cards: continue
        key = (len(cards), sum(HCP.get(c, 0) for c in cards))
        if best is None or key > best[:2]:
            best = (key[0], key[1], si)
    if best is None: return None
    si = best[2]; cards = west_suits[si]
    if _honor_sequence_top(cards):
        rank = cards[0]
    elif len(cards) >= 4:
        rank = cards[3]            # 4th-best
    elif len(cards) == 3:
        rank = cards[-1]           # low from three small
    elif len(cards) == 2:
        rank = cards[0]            # high from a doubleton
    else:
        rank = cards[0]            # singleton
    return si, rank

def _lead_card_from_holding(cards):
    """The standard card to lead from a chosen holding (suit-contract rules):
    K from AK(x...); top of a 3+ touching/interior honour sequence; 4th-best
    from four+; low from three small; top of a doubleton; the card from a
    singleton."""
    if len(cards) >= 2 and cards[0] == 'A' and cards[1] == 'K':
        return 'K'                 # K from AK
    if len(cards) >= 3 and _honor_sequence_top(cards):
        return cards[0]            # top of a sequence
    if len(cards) >= 4:
        return cards[3]            # 4th-best
    if len(cards) == 3:
        return cards[-1]           # low from three
    return cards[0]                # top of a doubleton / the singleton

def opening_lead_vs_suit(leader_suits, trump_idx):
    """West's standard opening lead vs a SUIT contract (opponents silent, so no
    partner suit to lead). Priority, matching the authored lead rules in
    GENERATOR-PLAY.md: (1) a small side-suit singleton, never a singleton honor
    (a singleton K/Q/J costs the honor, not gains a ruff); (2) the top of
    a side-suit touching-honour sequence (incl. K from AK); (3) 4th-best from
    the longest side suit, AVOIDING underleading an ace (lead low only from a
    suit not headed by a bare ace). Falls back to leading an ace-headed suit's
    ace, then to a trump, only if nothing safer exists. Returns (suit_idx, rank)
    or None if void everywhere. leader_suits is [S,H,D,C] rank strings;
    trump_idx is 0..3."""
    side = [i for i in range(4) if i != trump_idx]
    # 1. a SMALL side-suit singleton (ruff-seeking) — NOT a singleton honor
    #    (A/K/Q/J): leading a stiff honor crashes it rather than winning a ruff,
    #    and it destroys lessons like Rabbi's Rule (dropping a hidden singleton K).
    small_singles = [i for i in side
                     if len(leader_suits[i]) == 1 and leader_suits[i][0] not in 'AKQJ']
    if small_singles:
        i = small_singles[0]
        return i, leader_suits[i][0]
    # 2. top of a side-suit touching-honour sequence (longest such suit)
    seqs = []
    for i in side:
        c = leader_suits[i]
        if (len(c) >= 2 and c[0] == 'A' and c[1] == 'K') or \
           (len(c) >= 3 and _honor_sequence_top(c)):
            seqs.append((len(c), i))
    if seqs:
        i = max(seqs)[1]
        return i, _lead_card_from_holding(leader_suits[i])
    # 3. longest side suit (strongest as tiebreak), skipping bare-ace suits to
    #    avoid underleading the ace into a trump contract.
    order = sorted(side, key=lambda i: (len(leader_suits[i]),
                   sum(HCP.get(c, 0) for c in leader_suits[i])), reverse=True)
    for i in order:
        c = leader_suits[i]
        if not c:
            continue
        if c[0] == 'A' and not (len(c) >= 2 and c[1] == 'K'):
            continue               # don't underlead a bare ace yet
        return i, _lead_card_from_holding(c)
    # 4. forced: a bare-ace side suit (lead the ace itself, never underlead it),
    #    else a trump.
    for i in order:
        if leader_suits[i]:
            return i, leader_suits[i][0]
    if leader_suits[trump_idx]:
        return trump_idx, _lead_card_from_holding(leader_suits[trump_idx])
    return None

def holdup_required(deal_str):
    """Lead-driven hold-up oracle. True iff 3NT by South makes double-dummy
    (so ducking is available) BUT fails when declarer is denied the duck —
    i.e. must WIN the first round of the suit West actually leads. This is
    keyed to West's real opening lead (West's longest/strongest suit), not to
    a guessed danger suit, and is independent of stopper count (it catches the
    two-stopper 'duck once to strand the short hand' hold-up as well as the
    classic Axx single-stopper one). None = not testable / not a hold-up here."""
    if dd(deal_str, Denom.nt, 'S') < 9: return False
    h = hands(deal_str)
    lead = opening_lead_vs_nt(h['W'])
    if lead is None: return None
    si, wrank = lead; su = SUITS[si]
    # Trick 1: W leads; dummy (N) low; E low; S wins with cheapest winning card.
    n_card = su + lowest(h['N'][si]) if h['N'][si] else lowest_overall(h['N'])
    e_card = su + lowest(h['E'][si]) if h['E'][si] else lowest_overall(h['E'])
    # Highest rank played by W/N/E in the led suit that S must beat to win.
    in_suit = [wrank]
    if h['N'][si]: in_suit.append(n_card[1])
    if h['E'][si]: in_suit.append(e_card[1])
    high = min(in_suit, key=lambda r: RANK.index(r))  # min index == highest rank
    s_winners = [c for c in h['S'][si] if RANK.index(c) < RANK.index(high)]
    if not s_winners: return None      # South cannot win trick 1 → not a hold-up
    s_card = su + s_winners[-1]        # cheapest winning card
    d = Deal(deal_str); d.trump = Denom.nt; d.first = Player.west
    try:
        for card in (su + wrank, n_card, e_card, s_card):
            d.play(Card(card))
        decl_more = max(t for _, t in solve_board(d))
    except Exception:
        return None
    return (1 + decl_more) < 9

def avoidance_shaped(deal_str):
    h = hands(deal_str)
    one_stop = any('A' in (h['N'][i] + h['S'][i]) and 'K' not in (h['N'][i] + h['S'][i])
                   and len(h['E'][i]) + len(h['W'][i]) >= 5 for i in range(4))
    tenace = sum(1 for i in range(4) for hd in [h['N'][i], h['S'][i]]
                 if ('A' in hd and 'Q' in hd and 'K' not in hd)
                 or ('K' in hd and 'J' in hd and 'Q' not in hd))
    return bool(one_stop and tenace >= 1)

def freak_flags(deal_str):
    h = hands(deal_str)
    flags = set()
    for s in 'NESW':
        ln = [len(x) for x in h[s]]
        if 0 in ln: flags.add('void')
        if max(ln) >= 7: flags.add('seven-card-suit')
        if sorted(ln, reverse=True)[:2] >= [5, 5]: flags.add('two-suiter')
    return sorted(flags)

def auction_filter_regex(scn):
    for line in open(f"btn/{scn}.btn", encoding='utf-8', errors='replace'):
        if line.startswith('# auction-filter:'):
            return line[len('# auction-filter:'):].strip()
    return None

def board_record(chunk, scn_kind, oracle, flt_re):
    deal = tag(chunk, 'Deal'); con = tag(chunk, 'Contract'); dec = tag(chunk, 'Declarer')
    rec = {'board': tag(chunk, 'Board'), 'deal_hash': deal_hash(deal) if deal else None,
           'contract': con, 'declarer': dec}
    if not deal:
        rec['error'] = 'no-deal'; return rec
    h = hands(deal)
    rec['hcp'] = {s: hcp_of(h[s]) for s in 'NESW'}
    rec['flags'] = freak_flags(deal)
    if flt_re is not None:
        try:
            rec['matched_intended_auction'] = bool(re.search(flt_re, chunk))
        except re.error:
            rec['matched_intended_auction'] = None
    if not con or con in ('--', 'Pass') or dec in (None, '?', ''):
        rec['dd_class'] = 'passed_out'; return rec
    try:
        k, de, dp = classify(deal, con, dec)
        rec['dd_class'] = k; rec['dd_declarer_tricks'] = de; rec['dd_partner_tricks'] = dp
    except Exception as e:
        rec['dd_class'] = 'error'; rec['error'] = str(e); return rec
    if scn_kind == 'byforce' and rec['dd_class'] == 'ok':
        try: rec['by_force'] = by_force(deal, con, dec)
        except Exception: rec['by_force'] = None
    if oracle == 'holdup' and con == '3N' and dec == 'S':
        rec['holdup_required'] = holdup_required(deal)
    if oracle == 'shape':
        rec['avoidance_shaped'] = avoidance_shaped(deal)
    return rec

PROG = "bba-curated/.progress"

def scenario_config(scn):
    """kind, oracle, target (contract, seat) — from .btn directive, else CONFIG."""
    d = curate_directive(scn)
    if d:
        return d['kind'], d.get('oracle'), (d.get('contract'), d.get('seat'))
    if scn in CONFIG:
        k, o = CONFIG[scn]
        return k, ('holdup' if o == 'holdup' else 'shape' if o == 'shape' else None), (None, None)
    return 'bidding', None, (None, None)

def process_scenario(scn):
    """Resume-able pass; returns 'complete' or 'partial'."""
    kind, oracle, _target = scenario_config(scn)
    flt = auction_filter_regex(scn)
    os.makedirs(PROG, exist_ok=True)
    for src, path in (('coaching', f"coaching/{scn}.pbn"), ('pool', f"bba/{scn}.pbn")):
        if not os.path.exists(path): continue
        jl = f"{PROG}/{scn}-{src}.jsonl"
        done = sum(1 for _ in open(jl)) if os.path.exists(jl) else 0
        chunks = split_boards(path)
        if done >= len(chunks): continue
        with open(jl, "a") as f:
            for ch in chunks[done:]:
                if out_of_time(): return 'partial'
                r = board_record(ch, kind, oracle if kind == 'avoidance' else None, flt)
                f.write(json.dumps(r) + "\n")
    return 'complete'

def assemble(scn):
    kind, oracle, target = scenario_config(scn)
    flt = auction_filter_regex(scn)
    out = {'scenario': scn, 'kind': kind, 'oracle': oracle,
           'target_contract': target[0], 'target_seat': target[1],
           'auction_filter': flt}
    filtered_hashes = set()
    if os.path.exists(f"bba-filtered/{scn}.pbn"):
        for ch in split_boards(f"bba-filtered/{scn}.pbn"):
            d = tag(ch, 'Deal')
            if d: filtered_hashes.add(deal_hash(d))
    for src in ('coaching', 'pool'):
        jl = f"{PROG}/{scn}-{src}.jsonl"
        if not os.path.exists(jl):
            out[src] = None; continue
        recs, seen = [], collections.Counter()
        for line in open(jl):
            r = json.loads(line)
            if r.get('deal_hash'):
                seen[r['deal_hash']] += 1
                if seen[r['deal_hash']] > 1: r.setdefault('flags', []).append('duplicate')
                r['in_bba_filtered'] = r['deal_hash'] in filtered_hashes
            recs.append(r)
        out[src] = recs
    return out

def summarize(out):
    s = {'scenario': out['scenario'], 'kind': out['kind']}
    for src in ('coaching', 'pool'):
        recs = out.get(src)
        if not recs: continue
        cc = collections.Counter(r.get('dd_class') for r in recs)
        agg = {'boards': len(recs), 'dd': dict(cc)}
        m = [r for r in recs if 'matched_intended_auction' in r]
        if m:
            agg['regex_matched'] = sum(1 for r in m if r['matched_intended_auction'])
            agg['in_bba_filtered'] = sum(1 for r in m if r.get('in_bba_filtered'))
            agg['regex_vs_filtered_disagree'] = sum(
                1 for r in m if r['matched_intended_auction'] != r.get('in_bba_filtered'))
        bf = [r for r in recs if 'by_force' in r]
        if bf: agg['by_force'] = sum(1 for r in bf if r['by_force'])
        hu = [r for r in recs if 'holdup_required' in r]
        if hu: agg['holdup_required'] = sum(1 for r in hu if r['holdup_required'] is True)
        av = [r for r in recs if 'avoidance_shaped' in r]
        if av: agg['avoidance_shaped'] = sum(1 for r in av if r['avoidance_shaped'])
        agg['dupes'] = sum(1 for r in recs if 'duplicate' in (r.get('flags') or []))
        s[src] = agg
    return s

def report_md(out, summ):
    L = [f"# curate Layer A report — {out['scenario']}",
         f"kind: **{out['kind']}** · auction-filter: `{out['auction_filter']}`", ""]
    for src in ('coaching', 'pool'):
        if not summ.get(src): continue
        a = summ[src]
        L.append(f"## {src} ({a['boards']} boards)")
        L.append(f"- DD classes: {a['dd']}")
        for k in ('regex_matched', 'in_bba_filtered', 'regex_vs_filtered_disagree',
                  'by_force', 'holdup_required', 'avoidance_shaped', 'dupes'):
            if k in a: L.append(f"- {k}: {a[k]}")
        L.append("")
    bad = [r for r in (out.get('coaching') or [])
           if r.get('dd_class') in ('wrong_sided', 'down_both')]
    if bad:
        L.append("## Defective coaching boards")
        for r in bad:
            L.append(f"- board {r['board']}: {r['contract']} by {r['declarer']} — "
                     f"{r['dd_class']} (decl {r.get('dd_declarer_tricks')}, "
                     f"partner {r.get('dd_partner_tricks')})")
    return "\n".join(L) + "\n"

if __name__ == "__main__":
    scns = sys.argv[1:] or list(CONFIG)
    os.makedirs("bba-curated", exist_ok=True)
    all_summ, all_done = [], True
    for scn in scns:
        status = process_scenario(scn)
        if status == 'partial':
            all_done = False
            print(f"PARTIAL {scn} ({time.time()-START:.0f}s)", flush=True)
            break
        if not os.path.exists(f"bba-curated/{scn}.json"):
            out = assemble(scn)
            summ = summarize(out)
            with open(f"bba-curated/{scn}.json", "w") as f:
                json.dump(out, f, indent=1)
            with open(f"bba-curated/{scn}-report.md", "w") as f:
                f.write(report_md(out, summ))
            print("DONE " + json.dumps(summ), flush=True)
    if all_done:
        for scn in scns:
            out = assemble(scn)
            all_summ.append(summarize(out))
        with open("bba-curated/-layerA-summary.json", "w") as f:
            json.dump(all_summ, f, indent=1)
        print("ALL-COMPLETE")
