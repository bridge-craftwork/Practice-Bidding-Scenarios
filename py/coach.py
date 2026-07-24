#!/usr/bin/env python3
"""coach.py — mechanics of coaching generation (see coaching-curated/GENERATOR.md).

Two steps bracket the Claude-subagent prose generation:

  python3 py/coach.py packets <scenario> [query...] [-n N]
      Select curated boards from bba-curated/<scenario>.pbn (default
      "bidding=textbook,judgment diff<=3", N=30), write the selected input
      PBN and per-chunk packet JSON into coaching-curated/.work/ for the
      subagents to coach.

  python3 py/coach.py splice <scenario>
      Splice the subagents' {board,coaching} JSON (coaching-curated/.work/
      <scenario>-coach*.json) into the selected input and write
      coaching-curated/<scenario>.pbn. Validates pronoun tokens and that no
      [BID Pass] slipped in.

  python3 py/coach.py packets|play-packets <scenario> ... --fill
      Top-up mode: select only boards NOT already in coaching-curated/
      <scenario>.pbn, up to (N - existing) of them, so an under-built file
      can grow to N without recoaching what is already reviewed.

  python3 py/coach.py fill-splice <scenario>
      Non-destructive companion to --fill: keep the existing curated file
      VERBATIM and APPEND the newly-coached boards (source slice + prose).
      Works for both play and bidding coach JSON.

The prose itself is written by Claude subagents following GENERATOR.md;
this script only does the deterministic selection and splice.
"""
import sys, os, re, json, glob
sys.path.append(os.path.dirname(__file__))
from curate import (split_boards, tag, hands, deal_hash, opening_lead_vs_nt,
                    opening_lead_vs_suit, SUITS)
from suit_tricks import trick_map
from trump_tricks import trump_trick_map
from defender_budget import defender_budget

STRAIN_IDX = {'S': 0, 'H': 1, 'D': 2, 'C': 3}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUR = os.path.join(ROOT, "bba-curated")
OUT = os.path.join(ROOT, "coaching-curated")
WORK = os.path.join(OUT, ".work")
HCP = {'A': 4, 'K': 3, 'Q': 2, 'J': 1}
RANK = {r: i for i, r in enumerate('23456789TJQKA', start=2)}
LHO = {'N': 'E', 'E': 'S', 'S': 'W', 'W': 'N'}


def _running_suit(a, b, opp):
    """Tricks NS cashes from the top in ONE notrump suit before losing the
    lead, choosing which NS hand leads (unlimited entries) so a short-hand
    unblock and blockage fall out naturally; opponents follow suit. This is
    the count-winners number, and it is exactly where eye-counting slips: a
    4-4 AKQJT runs only FOUR (the long hand's honours get used unblocking),
    and a defender's length can leave the suit short of its honour count."""
    best = 0
    for first, second in ((a, b), (b, a)):
        A = sorted(first); B = sorted(second); O = sorted(opp)
        tricks = 0; h = [A, B]
        while A and B:
            lead = 0 if A[-1] >= B[-1] else 1
            if h[lead][-1] < (O[-1] if O else -1):
                break
            tricks += 1; h[lead].pop(); h[1 - lead].pop(0)
            for _ in range(2):
                if O:
                    O.pop(0)
        rem = A if A else B; rem.sort()
        while rem and rem[-1] >= (O[-1] if O else -1):
            tricks += 1; rem.pop()
            for _ in range(2):
                if O:
                    O.pop(0)
        best = max(best, tricks)
    return best


def cash_out(h):
    """Verified per-suit cash-and-out tricks for a NOTRUMP deal, plus the
    total — the authoritative count-winners number. Authors narrate this
    verbatim instead of eye-counting (GENERATOR-PLAY.md). Only meaningful
    in notrump; suit play uses trump_trick_map."""
    per = {su: _running_suit([RANK[c] for c in h['N'][i]],
                             [RANK[c] for c in h['S'][i]],
                             [RANK[c] for c in h['E'][i]] + [RANK[c] for c in h['W'][i]])
           for i, su in enumerate('SHDC')}
    per['total'] = sum(per[su] for su in 'SHDC')
    return per


def _escape_violations(path):
    """A suit escape must name its suit: \\S/\\H/\\D/\\C then the ranks. A bare
    \\<rank> ('\\AK', '\\KQ876') is missing the suit letter and renders as a
    literal backslash in the trainer (which only substitutes \\S\\H\\D\\C).
    Deterministic and unambiguous — every bare-rank escape is a bug."""
    out = []
    for ch in split_boards(path):
        a = ch.find('[Auction'); i = ch.find('{', a)
        if i < 0:
            continue
        body = ch[i:ch.find('}', i)]
        for m in re.finditer(r'\\[AKQJT2-9]+', body):
            out.append((tag(ch, 'Board'), m.group(0)))
    return out


def _curate_block(ch):
    m = re.search(r'\{Curate\n(.*?)\n\}', ch, flags=re.S)
    d = {}
    if m:
        for line in m.group(1).splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                d[k.strip()] = v.strip()
    return d


def _match(blk, term):
    m = re.match(r'([\w-]+)\s*(<=|>=|=)\s*(.+)', term)
    key, op, val = m.group(1), m.group(2), m.group(3).strip()
    if key == 'diff':
        d = blk.get('difficulty')
        if d is None:
            return False
        d, v = int(d), int(val)
        return d <= v if op == '<=' else d >= v if op == '>=' else d == v
    content = blk.get(key)
    if content is None:
        return False
    words = content.split()
    return any(v.strip() in words for v in val.split(','))


def packets(scn, terms, n, fill=False, boards=None):
    src = os.path.join(CUR, f"{scn}.pbn")
    chunks = split_boards(src)
    if boards:
        # explicit board list (reproducible selection; mirrors play-boards.json).
        bymap = {tag(ch, 'Board'): ch for ch in chunks}
        sel = [bymap[b] for b in boards if b in bymap]
        os.makedirs(WORK, exist_ok=True)
        json.dump(boards, open(os.path.join(WORK, f"{scn}-boards.json"), "w"))
    else:
        matching = [ch for ch in chunks if all(_match(_curate_block(ch), t) for t in terms)]
        if fill:
            have = {tag(ch, 'Board') for ch in split_boards(os.path.join(OUT, f"{scn}.pbn"))}
            sel = [ch for ch in matching if tag(ch, 'Board') not in have][:max(0, n - len(have))]
        else:
            sel = matching[:n]
    os.makedirs(WORK, exist_ok=True)
    # selected input PBN — keep the {Curate} blocks so the file carries
    # per-board tier (fill mode appends them, like play files already do).
    inp = "".join(sel)
    open(os.path.join(WORK, f"{scn}-input.pbn"), "w").write(inp)
    # packets (split into chunks of 15 for parallel subagents)
    pkts = []
    for ch in sel:
        blk = _curate_block(ch)
        deal = tag(ch, 'Deal'); h = hands(deal)
        m = re.search(r'\[Auction "(\w)"\]\s*\n((?:[^\[{][^\n]*\n?)*)', ch)
        dec = tag(ch, 'Declarer')
        pkts.append({
            "board": tag(ch, 'Board'), "dealer": tag(ch, 'Dealer'),
            "vul": tag(ch, 'Vulnerable'),
            "hands": {s: " ".join(f"{su}:{''.join(h[s][i]) or '-'}"
                                  for i, su in enumerate("SHDC")) for s in "NESW"},
            "hcp": {s: sum(HCP.get(c, 0) for su in h[s] for c in su) for s in "NESW"},
            "auction": " ".join(m.group(2).split()) if m else None,
            "contract": tag(ch, 'Contract'), "declarer": dec,
            "opening_leader": LHO.get(dec) if dec in LHO else None,
            "bidding_tier": blk.get('bidding', '').split()[0] if blk.get('bidding') else '?',
            "also_ok": blk.get('also-ok', ''),
            "note": blk.get('bidding-note', ''),
        })
    size = (len(pkts) + 1) // 2 or 1
    for i in range(0, len(pkts), size):
        k = i // size + 1
        json.dump(pkts[i:i+size], open(os.path.join(WORK, f"{scn}-pkt{k}.json"), "w"), indent=0)
    print(f"{scn}: selected {len(sel)} boards -> {WORK}/{scn}-input.pbn")
    print(f"  packets: {(len(pkts)+size-1)//size} files ({size}/file)")
    print(f"  next: a subagent per packet writes {scn}-coach<k>.json per GENERATOR.md")


def splice(scn):
    coach = {}
    for f in sorted(glob.glob(os.path.join(WORK, f"{scn}-coach*.json"))):
        for o in json.load(open(f)):
            coach[str(o['board'])] = o['coaching'].strip()
    if not coach:
        sys.exit(f"no {scn}-coach*.json in {WORK} — run the subagents first")
    out = []
    for ch in split_boards(os.path.join(WORK, f"{scn}-input.pbn")):
        b = tag(ch, 'Board'); body = coach.get(str(b))
        if body:
            m = re.search(r'(\[Auction "[^"]*"\]\n(?:[^\[{][^\n]*\n)*)', ch)
            if m:
                ch = ch[:m.end()] + "{" + body + "}\n" + ch[m.end():]
        out.append(ch)
    txt = "".join(out)
    # validation
    bidpass = txt.count('[BID Pass]')
    recites = len(re.findall(r'\\[SHDC]\s?[AKQJT2-9]{2,}', txt))
    open(os.path.join(OUT, f"{scn}.pbn"), "w").write(txt)
    coached = sum(1 for ch in split_boards(os.path.join(OUT, f"{scn}.pbn"))
                  if re.search(r'\[Auction[^\]]*\]\n(?:[^\[{][^\n]*\n)*\{', ch))
    print(f"{scn}: wrote {OUT}/{scn}.pbn — {coached} coached boards, "
          f"{txt.count('[BID')} [BID anchors")
    if bidpass:
        print(f"  WARNING: {bidpass} [BID Pass] anchors (should be 0)")
    if recites:
        print(f"  WARNING: {recites} possible card recitations (should be 0)")
    validate(scn)  # structure gate: flags N/S calls missing a [BID] anchor


def _norm_call(s):
    s = s.strip().upper()
    return s + "T" if re.fullmatch(r"\d+N", s) else s


LHO = {'N': 'E', 'E': 'S', 'S': 'W', 'W': 'N'}


def play_packets(scn, theme, n, fill=False):
    """Select curated boards graded declarer textbook/standard for THEME and
    build play-coaching packets (deal + contract + declarer + leader + note).
    fill=True tops up an existing coaching-curated/<scn>.pbn: skip boards it
    already holds and select only up to (n - existing) new ones."""
    src = os.path.join(CUR, f"{scn}.pbn")
    graded = {v['deal_hash']: v for v in
              json.load(open(os.path.join(CUR, f"{scn}-graded.json")))['verdicts']}
    have, target = set(), n
    if fill:
        have = {tag(ch, 'Board') for ch in split_boards(os.path.join(OUT, f"{scn}.pbn"))}
        target = max(0, n - len(have))
    pkts = []
    for ch in split_boards(src):
        d = tag(ch, 'Deal'); v = graded.get(deal_hash(d)) if d else None
        if not v:
            continue
        decl = v.get('declarer', {})  # declarer-play GRADING (tier/themes/note)
        tier = decl.get('tier'); themes = decl.get('themes', []); note = decl.get('note', '')
        if tier not in ('textbook', 'standard') or theme not in themes:
            continue
        if fill and tag(ch, 'Board') in have:
            continue
        h = hands(d); declarer = tag(ch, 'Declarer')  # the declaring SEAT
        contract = tag(ch, 'Contract')
        strain = contract[1] if contract and len(contract) >= 2 else 'N'
        leadseat = LHO.get(declarer)
        # VERIFIED trick facts (exact double-dummy, known cards) so the subagent
        # narrates numbers instead of counting them itself. NOTRUMP and SUIT
        # contracts use different analysers (trumps + ruffing change everything)
        # and different standard opening leads:
        #   NT  -> suit_tricks.trick_map (per-suit top/establishable +
        #          development_suit); lead = 4th-best / sequence top.
        #   suit-> trump_trick_map (authoritative DD total + dd_losers, trump
        #          length split, side-suit top/establishable, ruffs in the short
        #          hand, sure_tricks/develop); lead = singleton / sequence /
        #          4th-best, never underleading an ace.
        if strain == 'N':
            tmap = trick_map(h)
            ol = opening_lead_vs_nt(h[leadseat])
        else:
            tmap = trump_trick_map(h, strain, declarer, deal_str=d)
            ol = opening_lead_vs_suit(h[leadseat], STRAIN_IDX[strain])
        lead = f"\\{SUITS[ol[0]]}{ol[1]}" if ol else None
        am = re.search(r'\[Auction "\w"\]\s*\n((?:[^\[{][^\n]*\n?)*)', ch)
        auction = " ".join(am.group(1).split()) if am else None
        pkts.append({
            "board": tag(ch, 'Board'), "contract": tag(ch, 'Contract'),
            "declarer": declarer, "leader": leadseat,
            "dealer": tag(ch, 'Dealer'), "vul": tag(ch, 'Vulnerable'),
            "theme": theme, "note": note,
            "opening_lead": lead,   # AUTHORITATIVE — use this card verbatim
            "hands": {s: " ".join(f"{su}:{''.join(h[s][i]) or '-'}"
                                  for i, su in enumerate("SHDC")) for s in "NESW"},
            "trick_map": tmap,
            # VERIFIED per-suit cash-and-out count (notrump only) — the
            # count-winners number; reconciles to the contract. Authors quote
            # this rather than eye-counting blockage-prone suits.
            "cash_out": cash_out(h) if strain == 'N' else None,
            # what declarer can KNOW (ns_hcp/defender_hcp) and INFER (per-defender
            # split + rule-of-11) about the hidden hands; see GENERATOR-PLAY.md.
            "defender_budget": defender_budget(
                h, declarer, dealer=tag(ch, 'Dealer'),
                auction=auction, opening_lead=ol, strain=strain),
        })
        if len(pkts) >= target:
            break
    os.makedirs(WORK, exist_ok=True)
    size = (len(pkts) + 1) // 2 or 1
    for i in range(0, len(pkts), size):
        json.dump(pkts[i:i+size], open(os.path.join(WORK, f"{scn}-play-pkt{i//size+1}.json"), "w"), indent=0)
    json.dump([p['board'] for p in pkts],
              open(os.path.join(WORK, f"{scn}-play-boards.json"), "w"))
    print(f"{scn}: {len(pkts)} '{theme}' boards -> {(len(pkts)+size-1)//size} play packets")
    print(f"  next: a subagent per packet writes tips per GENERATOR-PLAY.md -> {scn}-play-coach<k>.json")


def play_splice(scn):
    """Splice [ROLE]/[STAGE] play tips after each selected board's auction."""
    tips = {}
    for f in sorted(glob.glob(os.path.join(WORK, f"{scn}-play-coach*.json"))):
        for o in json.load(open(f)):
            tips[str(o['board'])] = o['coaching'].strip()
    if not tips:
        sys.exit(f"no {scn}-play-coach*.json in {WORK}")
    boards = set(json.load(open(os.path.join(WORK, f"{scn}-play-boards.json"))))
    out = []
    for ch in split_boards(os.path.join(CUR, f"{scn}.pbn")):
        b = tag(ch, 'Board')
        if str(b) in boards and str(b) in tips:
            m = re.search(r'(\[Auction "[^"]*"\]\n(?:[^\[{][^\n]*\n)*)', ch)
            if m:
                ch = ch[:m.end()] + "{" + tips[str(b)] + "}\n" + ch[m.end():]
        out.append(ch)
    txt = "".join(out)
    open(os.path.join(OUT, f"{scn}.pbn"), "w").write(txt)
    # validation: pre-lead card present + no space; matches the computed lead
    coached = [b for b in boards if b in tips]
    nolead = [b for b in coached if not re.search(r'\[ROLE leader\]\[STAGE pre-lead\]\s*Lead the \\[SHDC][AKQJT2-9]', tips[b])]
    spacelead = [b for b in coached if re.search(r'Lead the \\[SHDC]\s+[AKQJT2-9]', tips[b])]
    # cross-check the spliced lead card against the standard opening lead from
    # the leader's hand (the card is auto-played, so it must be the right one).
    # Contract-aware: NT uses the 4th-best/sequence lead, suit contracts use the
    # singleton/sequence/4th-best (no-underlead-ace) suit lead.
    wronglead = []
    info = {tag(ch, 'Board'): (tag(ch, 'Deal'), tag(ch, 'Declarer'), tag(ch, 'Contract'))
            for ch in split_boards(os.path.join(CUR, f"{scn}.pbn"))}
    for b in coached:
        deal, decl, contract = info.get(b, (None, None, None))
        if not (deal and decl):
            continue
        m = re.search(r'Lead the (\\[SHDC][AKQJT2-9])', tips[b])
        if not m:
            continue
        h = hands(deal); leadh = h[LHO.get(decl)]
        strain = contract[1] if contract and len(contract) >= 2 else 'N'
        ol = (opening_lead_vs_nt(leadh) if strain == 'N'
              else opening_lead_vs_suit(leadh, STRAIN_IDX[strain]))
        want = f"\\{SUITS[ol[0]]}{ol[1]}" if ol else None
        if want and m.group(1) != want:
            wronglead.append(f"{b}:{m.group(1)}!={want}")
    print(f"{scn}: spliced play tips into {len(coached)} boards -> {OUT}/{scn}.pbn")
    if nolead:
        print(f"  WARNING: {len(nolead)} boards missing a load-bearing 'Lead the \\Xr' pre-lead: {sorted(nolead)}")
    if spacelead:
        print(f"  WARNING: space before lead rank (breaks auto-lead): {sorted(spacelead)}")
    if wronglead:
        print(f"  WARNING: pre-lead card != standard lead: {sorted(wronglead)}")


def fill_splice(scn):
    """Non-destructive top-up: keep the existing coaching-curated/<scn>.pbn
    VERBATIM and APPEND newly-coached boards. Works for both play tips
    ([ROLE]/[STAGE]) and bidding ([BID]) prose — the source slice + prose are
    spliced after the auction exactly as play_splice/splice do, so the same
    coach JSON files feed it.

    Two passes:
      1. Existing boards are kept as-is, except a board that lacks a {Curate}
         block gets the source block (matched by deal_hash) backfilled in,
         immediately before [Auction], so the file carries per-board tier
         uniformly. Play files already carry {Curate}, so this is a no-op and
         the existing content stays byte-for-byte identical (prefix gate).
      2. Each coached board not already present is appended: the source board
         slice from bba-curated with its prose spliced after the auction.
    Then validate(scn)."""
    out_path = os.path.join(OUT, f"{scn}.pbn")
    src_chunks = split_boards(os.path.join(CUR, f"{scn}.pbn"))
    src_by_hash = {deal_hash(tag(ch, 'Deal')): ch for ch in src_chunks if tag(ch, 'Deal')}
    # prose from whichever coach files the authoring step produced
    coach = {}
    for pat in (f"{scn}-play-coach*.json", f"{scn}-coach*.json"):
        for f in sorted(glob.glob(os.path.join(WORK, pat))):
            for o in json.load(open(f)):
                coach[str(o['board'])] = o['coaching'].strip()
    if not coach:
        sys.exit(f"no {scn}-coach*.json / {scn}-play-coach*.json in {WORK}")

    raw = open(out_path, encoding='utf-8', errors='replace').read()
    existing = split_boards(out_path)
    have = {tag(ch, 'Board') for ch in existing}
    # pass 1 — backfill {Curate} only into boards missing it. If none are
    # missing (play files), keep the raw prefix verbatim so it is a byte-exact
    # prefix of the result.
    if all('{Curate' in ch for ch in existing):
        prefix = raw
    else:
        rebuilt = []
        for ch in existing:
            if '{Curate' not in ch:
                d = tag(ch, 'Deal')
                src = src_by_hash.get(deal_hash(d)) if d else None
                cm = re.search(r'(\{Curate\n.*?\n\}\n)', src, flags=re.S) if src else None
                am = re.search(r'\[Auction "', ch)
                if cm and am:
                    ch = ch[:am.start()] + cm.group(1) + ch[am.start():]
            rebuilt.append(ch)
        prefix = "".join(rebuilt)

    # pass 2 — append source slice + spliced prose for each new coached board,
    # in source order.
    new_blocks = []
    for ch in src_chunks:
        b = tag(ch, 'Board')
        if b in have or b not in coach:
            continue
        m = re.search(r'(\[Auction "[^"]*"\]\n(?:[^\[{][^\n]*\n)*)', ch)
        if m:
            ch = ch[:m.end()] + "{" + coach[b] + "}\n" + ch[m.end():]
        new_blocks.append(ch)
    open(out_path, "w").write(prefix + "".join(new_blocks))
    appended = [tag(ch, 'Board') for ch in new_blocks]
    print(f"{scn}: kept {len(existing)} existing boards, appended {len(appended)} "
          f"-> {out_path} ({len(existing) + len(appended)} total)")
    # any coached board we couldn't place (number not in source, or already had)
    missing = sorted(b for b in coach if b not in have and b not in appended)
    if missing:
        print(f"  WARNING: {len(missing)} coached board(s) not found in source: {missing}")

    # load-bearing pre-lead cross-check on appended PLAY boards (the card is
    # auto-played, so it must equal the standard opening lead from the leader).
    info = {tag(ch, 'Board'): (tag(ch, 'Deal'), tag(ch, 'Declarer'), tag(ch, 'Contract'))
            for ch in src_chunks}
    nolead, spacelead, wronglead = [], [], []
    for ch in new_blocks:
        b = tag(ch, 'Board'); body = ch[ch.find('{'):ch.find('}', ch.find('{')) + 1]
        if '[ROLE' not in body:
            continue  # bidding board — no pre-lead
        if not re.search(r'\[ROLE leader\]\[STAGE pre-lead\]\s*Lead the \\[SHDC][AKQJT2-9]', body):
            nolead.append(b)
        if re.search(r'Lead the \\[SHDC]\s+[AKQJT2-9]', body):
            spacelead.append(b)
        m = re.search(r'Lead the (\\[SHDC][AKQJT2-9])', body)
        deal, decl, contract = info.get(b, (None, None, None))
        if m and deal and decl:
            leadh = hands(deal)[LHO.get(decl)]
            strain = contract[1] if contract and len(contract) >= 2 else 'N'
            ol = (opening_lead_vs_nt(leadh) if strain == 'N'
                  else opening_lead_vs_suit(leadh, STRAIN_IDX[strain]))
            want = f"\\{SUITS[ol[0]]}{ol[1]}" if ol else None
            if want and m.group(1) != want:
                wronglead.append(f"{b}:{m.group(1)}!={want}")
    if nolead:
        print(f"  WARNING: {len(nolead)} appended play board(s) missing 'Lead the \\Xr' pre-lead: {sorted(nolead)}")
    if spacelead:
        print(f"  WARNING: space before lead rank (breaks auto-lead): {sorted(spacelead)}")
    if wronglead:
        print(f"  WARNING: pre-lead card != standard lead: {sorted(wronglead)}")
    validate(scn)


_PE_CARD = r"\\[SHDC][AKQJT2-9]+"
_PE_HCP = r"\b\d{1,2}\s*(?:HCP|points?|point|count)\b"
_PE_SHAPE = (r"\b(?:balanced|unbalanced|singleton|stiff|doubleton|void|flat|"
             r"two-suit\w*|three-suit\w*|\d=\d=\d=\d)\b")
_PE_LEN = r"\b(?:two|three|four|five|six|seven|eight)[-\s](?:card|spade|heart|diamond|club|trump)"
_PE_FULL = re.compile(f"(?:{_PE_CARD}|{_PE_HCP}|{_PE_SHAPE}|{_PE_LEN})")
_PE_HARD = re.compile(f"(?:{_PE_CARD}|{_PE_HCP})")
_PE_BIDMEAN = re.compile(r"\b(show|shows|showed|showing|promis\w+|denie\w+|deny|denying|"
                         r"reveal\w*|confirm\w*|by agreement)\b", re.I)
_PE_BIDNOUN = re.compile(r"^['’s]*\s+(opening|open|double|raise|rais\w+|bid|call|"
                         r"response|respond\w*|rebid|rebids|preference|cue\w*|jump\w*|"
                         r"transfer\w*|probe|ask\w*|advance\w*|invitation|signoff|"
                         r"signs?\s+off|step|reply)", re.I)

# --- Opponent disclosure (Class A) + narrowing (Class B): two gaps left by
# _partner_exposure_violations, which only scans intro/reflection and only for
# North/partner subjects. See GENERATOR.md ("Hidden hands: opponents and
# narrowing"). ---
_PE_HONOR = r"\b(?:ace|king|queen|jack|values|strength)\b"
_PE_OPP_CONC = re.compile(f"(?:{_PE_CARD}|{_PE_HCP}|{_PE_SHAPE}|{_PE_LEN}|{_PE_HONOR})", re.I)
# Flat ASSERTION that a named defender HOLDS concrete cards. "East-West held a
# fit" (a pair reaching a contract) is auction inference, excluded via the
# (?<![-\w]) guard against the compound name; hypotheticals ("would need the
# ace onside") never match these placement idioms.
_OPP_HELD = re.compile(r"(?<![-\w])(East|West)\b\s+(?:held|holds|had|has)\b", re.I)
_OPP_PLACE = re.compile(
    r"\b(?:sitting|sat|lies?|lying|lay)\s+with\s+(?:East|West)\b"
    r"|\bin\s+the\s+(?:East|West)\s+hand\b"
    r"|\b(?:offside|onside|sits?|sat|sitting|lies?|lay)\b[^.]{0,20}\bin\s+(?:the\s+)?(?:East|West)\b",
    re.I)
_OPP_NEG = re.compile(r"\b(?:no|not|never|nothing|without)\b", re.I)
# Narrowing: pin a HIDDEN hand to a spot inside the range its call only promised.
# "shows 15-17" is fine; "at the top of its range" resolves the ambiguity.
_NARROW_PIN = re.compile(
    r"(?:top|bottom)\s+of\s+(?:its|his|her|their|the|a)\s+(?:\w+\s+){0,2}(?:range|zone)"
    r"|(?:near|at)\s+the\s+(?:top|bottom)\s+of\s+(?:its|his|her|their|the|a)?\s*(?:\w+\s+){0,2}(?:range|zone)"
    r"|on\s+the\s+good\s+side", re.I)


def _north_roles(chunk):
    """Which role words denote North (partner) on THIS board, so "opener" is only
    treated as partner when North actually opened. Mirrors the auction walk used
    by _partner_exposure_violations."""
    SEATS = ['N', 'E', 'S', 'W']
    m = re.search(r'\[Auction "(\w)"\]\s*\n((?:[^\[{][^\n]*\n?)*)', chunk)
    if not m:
        return {'responder', 'advancer'}
    di = SEATS.index(m.group(1))
    calls = [t for t in m.group(2).split()
             if re.match(r'(?i)^(pass|x|xx|\d[cdhsn]t?)$', t)]
    for j, c in enumerate(calls):
        if c.lower() == 'pass':
            continue
        return {'opener'} if SEATS[(di + j) % 4] == 'N' else {'responder', 'advancer'}
    return {'responder', 'advancer'}


def _hidden_hand_disclosure_violations(path):
    """Two disclosures GENERATOR.md forbids but _partner_exposure_violations misses:
    (A) a named opponent's concrete holding stated as fact (intro/reflection), and
    (B) NARROWING — pinning a hidden hand (partner OR opponent) to a spot inside
    the range/zone its call only promised, in ANY chunk (including [BID] chunks,
    which the partner-exposure gate never scans). Yields (board, loc, cls, snip)."""
    def _sentences(t):
        return re.split(r'(?<=[.!?])\s+', re.sub(r'\s+', ' ', t).strip())

    def _chunks(blk):
        pos, lab = 0, 'intro'
        for m in re.finditer(r'\[(BID [^\]]+|show [^\]]+)\]', blk):
            yield lab, blk[pos:m.start()]
            tok = m.group(1)
            if tok.startswith('BID'):
                lab = 'BID:' + tok[4:].strip()
            else:
                arg = tok[5:].strip()
                lab = 'reflection' if arg in ('NS', 'NESW') else 'show ' + arg
            pos = m.end()
        yield lab, blk[pos:]

    def _opp(sent):
        for rx in (_OPP_HELD, _OPP_PLACE):
            m = rx.search(sent)
            if not m:
                continue
            tail = sent[m.end():m.end() + 45]
            if _OPP_NEG.match(tail.lstrip()[:8]):
                continue
            if rx is _OPP_HELD and not _PE_OPP_CONC.search(tail):
                continue
            return sent[m.start():m.end() + 45].strip()[:70]
        return None

    def _narrow(sent, roles):
        subs = [r"partner'?’?s?", r"North'?’?s?"] + [w for r in roles
                                                     for w in (r.capitalize(), r)]
        subj = re.compile(r"\b(" + "|".join(subs) + r")\b")
        for sm in subj.finditer(sent):
            pm = _NARROW_PIN.search(sent, sm.end())
            if not pm:
                continue
            if re.search(r"\b(you|your|South)\b", sent[sm.start():pm.end()], re.I):
                continue
            return sent[sm.start():pm.end()].strip()[:80]
        return None

    for ch in split_boards(path):
        b = tag(ch, 'Board')
        if not b:
            continue
        blk = ch[ch.rfind('{') + 1:ch.rfind('}')]
        if '[ROLE' in blk:          # play lessons use a different prose dialect
            continue
        roles = _north_roles(ch)
        for loc, seg in _chunks(blk):
            for s in _sentences(seg):
                if loc in ('intro', 'reflection'):
                    d = _opp(s)
                    if d:
                        yield b, loc, 'opponent-disclosure', d
                n = _narrow(s, roles)
                if n:
                    yield b, loc, 'narrowing', n


def _partner_exposure_violations(path):
    """Flag intro / [show NS] prose that exposes partner's (North's — the non-student
    seat in a South=student lesson) concrete hand. The INTRO is pre-auction, so ANY
    partner hand info (cards/HCP/shape/length) is out — even a feature a later bid
    would show (the student isn't told it yet; David 2026-06-20: 'responder does not
    know opener has a balanced hand'). The [show NS] reflection is post-auction, so
    bid-meaning is fine there — only outright card/HCP recitation is flagged. See
    GENERATOR.md. (Assumes South=student; rotation-aware South-exposure is not gated.)"""
    SEATS = ['N', 'E', 'S', 'W']

    def north_roles(chunk):
        m = re.search(r'\[Auction "(\w)"\]\s*\n((?:[^\[{][^\n]*\n?)*)', chunk)
        if not m:
            return {'responder', 'advancer'}
        di = SEATS.index(m.group(1))
        calls = [t for t in m.group(2).split()
                 if re.match(r'(?i)^(pass|x|xx|\d[cdhsn]t?)$', t)]
        for j, c in enumerate(calls):
            if c.lower() == 'pass':
                continue
            return {'opener'} if SEATS[(di + j) % 4] == 'N' else {'responder', 'advancer'}
        return {'responder', 'advancer'}

    def flags(text, roles, conc, allow_bidmean):
        out = []
        subs = [r"North'?’?s?"] + [w for r in roles for w in (r.capitalize(), r)]
        subj = re.compile(r"\b(" + "|".join(subs) + r")\b")
        for sm in subj.finditer(text):
            if _PE_BIDNOUN.match(text[sm.end():sm.end() + 30]):
                continue
            cm = conc.search(text[sm.end():sm.end() + 45])
            if not cm:
                continue
            if re.search(r"\bSouth\b", text[sm.end():sm.end() + cm.start()]):
                continue
            if allow_bidmean and _PE_BIDMEAN.search(text[max(0, sm.start() - 5):sm.end() + cm.end()]):
                continue
            out.append(text[sm.start():sm.end() + cm.end()].strip()[:60])
        return out

    for ch in split_boards(path):
        b = tag(ch, 'Board')
        if not b:
            continue
        blk = ch[ch.rfind('{'):]
        if '[ROLE' in blk:          # play lessons use a different prose dialect
            continue
        nr = north_roles(ch)
        intro = re.split(r'\[BID|\[show', blk[1:])[0]
        rm = re.search(r'\[show (?:NS|NESW)\](.*?)\}', blk, re.S)
        for s in flags(intro, nr, _PE_FULL, False):
            yield b, 'intro', s
        for s in flags(rm.group(1) if rm else '', nr, _PE_HARD, True):
            yield b, 'reflection', s


_SEATS4 = ['N', 'E', 'S', 'W']
# a call written in prose: 1NT, 3\S, 2\D  (suit escapes, never a bare letter)
_PROSE_CALL = re.compile(r'\b([1-7])\s*(NT|N(?![A-Za-z])|\\[SHDC])')
# a call named only to be ruled out ("too weak for 1NT", "would promise 3\H")
_REJECTED_CALL = re.compile(
    r'\b(too (?:weak|strong|light|good|much)|short of|rather than|instead of|'
    r'would (?:promise|imply|show|be)|avoids?|not quite|a shade too|light for|'
    r'without|denies|cannot|can\'t|no longer)\b[^.]{0,34}$')


def _auction_seats(chunk):
    """[(seat, call)] for the board's auction, in order."""
    m = re.search(r'\[Auction "(\w)"\]\s*\n((?:[^\[{][^\n]*\n?)*)', chunk)
    if not m:
        return []
    di = _SEATS4.index(m.group(1))
    calls = [_norm_call(t) for t in m.group(2).split()
             if re.match(r'(?i)^(pass|x|xx|\d[cdhsn]t?)$', t)]
    return [(_SEATS4[(di + j) % 4], c) for j, c in enumerate(calls)]


def _theme_of(chunk):
    """The step-0 theme: prose from the block open up to the first [BID]."""
    a = chunk.find('[Auction')
    i = chunk.find('{', a)
    if i < 0:
        return ''
    body = chunk[i:chunk.find('}', i)]
    if '[ROLE' in body or '[choose-card' in body:
        return ''                      # play lesson: reveal belongs at auction-end
    theme = re.split(r'\[BID\s', body)[0]
    theme = re.sub(r'^\{\s*(?:\[show [^\]]+\])?', '', theme)
    return theme.strip()


def _premature_theme_violations(path):
    """The step-0 theme must not name a call NOBODY HAS MADE YET.

    The theme renders before the student's first decision, so a call that lands
    later in the auction is the answer handed over in advance — "partner ... rebid
    1NT over your five-card major" while the student has yet to bid 1S
    (classroom-feedback #245/#246: "'and rebid 1NT...' is premature"). Same family
    as the no-reveal rule David set corpus-wide on 2026-06-24, but checkable: it
    keys on the auction rather than on a list of convention names, so it does not
    false-fire on a convention partner has ALREADY bid (legitimate setup)."""
    out = []
    for ch in split_boards(path):
        seats = _auction_seats(ch)
        theme = _theme_of(ch)
        if not seats or not theme:
            continue
        first = next((k for k, (s, _) in enumerate(seats) if s == 'S'), None)
        if first is None:
            continue
        # normalise BOTH sides through _norm_call ("1N" and "1NT" are one call).
        # A call named as a REJECTED option ("a shade too weak for a 1NT opening",
        # "a jump that would promise four") is describing the hand, not narrating
        # the auction — the student is being told what they are NOT doing, which is
        # legitimate setup. Only forward-looking mentions are the reveal.
        named = set()
        for m in _PROSE_CALL.finditer(theme):
            lead = theme[max(0, m.start() - 34):m.start()].lower()
            if _REJECTED_CALL.search(lead):
                continue
            named.add(_norm_call(m.group(1) + m.group(2).replace('\\', '')))
        # `k >= first`, not `k > first`: the student's OWN first call counts too.
        # Naming it ("South opens 1NT with a balanced 15 to 17") hands over the
        # answer to the very decision the theme precedes — the most direct reveal
        # there is. David ruled on this 2026-07-23, extending the 2026-06-24
        # no-reveal rule to the student's next call and not just the ones beyond it.
        later = {c for k, (_, c) in enumerate(seats)
                 if k >= first and c not in ('PASS', 'X', 'XX')}
        both = sorted(named & later)
        if both:
            out.append((tag(ch, 'Board'), both, theme[:80]))
    return out


def _intro_seat_violations(path):
    """The theme must seat the student in the chair they actually occupy.

    Seat-alternating lessons put the student in either chair, and a theme written
    for one gets served with the other: "Partner opened a minor and you rebid
    1NT..." on a board where the STUDENT opened (classroom-feedback #246, "I'm the
    opening bidder"). Slam_after_Stayman b2 manages both in one sentence —
    "Partner opened a strong notrump ... You are the opener"."""
    out = []
    for ch in split_boards(path):
        seats = _auction_seats(ch)
        theme = _theme_of(ch)
        if not seats or not theme:
            continue
        opener = next((s for s, c in seats if c != 'PASS'), None)
        if opener == 'S' and re.search(r'^\s*Partner open(?:ed|s)\b', theme):
            out.append((tag(ch, 'Board'), 'student opened, theme says "Partner opened"',
                        theme[:80]))
        elif opener == 'N' and re.search(r'^\s*You open(?:ed|s)?\b', theme):
            out.append((tag(ch, 'Board'), 'partner opened, theme says "You opened"',
                        theme[:80]))
    return out


def _response_length_violations(path):
    """A 1-level major RESPONSE shows four or more, not five or more.

    The hand may well hold five, but the call does not promise it — describing what
    a bid SHOWS has to be accurate (classroom-feedback #247). Only responses are
    flagged: a 1H/1S OPENING legitimately promises five on a five-card-major card."""
    out = []
    FIVE = re.compile(r'five(?:\s+or\s+(?:more|longer)|-card or longer)')
    for ch in split_boards(path):
        seats = _auction_seats(ch)
        if not seats:
            continue
        a = ch.find('[Auction')
        i = ch.find('{', a)
        if i < 0:
            continue
        body = ch[i:ch.find('}', i)]
        if '[ROLE' in body:
            continue
        seq = [(c, s) for s, c in seats if c != 'PASS']
        parts = re.split(r'(\[BID\s+[^\]]+\])', body)
        si = 0
        for k in range(1, len(parts), 2):
            call = _norm_call(re.match(r'\[BID\s+([^\]]+)\]', parts[k]).group(1))
            text = parts[k + 1] if k + 1 < len(parts) else ''
            while si < len(seq) and seq[si][0] != call:
                si += 1
            if si >= len(seq):
                break
            seat = seq[si][1]
            is_response = any(s == ('N' if seat == 'S' else 'S') for _, s in seq[:si])
            si += 1
            if call in ('1H', '1S') and is_response and FIVE.search(text):
                m = FIVE.search(text)
                out.append((tag(ch, 'Board'), call,
                            text[max(0, m.start() - 40):m.end() + 10].strip()))
    return out


def validate(scn):
    """Check coaching-curated/<scn>.pbn structure: every non-pass call has
    exactly one anchored [BID] chunk, intro carries no [BID], [ACCEPT] sits
    only on a non-pass [BID] chunk, and no [BID] fails to anchor. Reports
    per-board issues; returns the count."""
    path = os.path.join(OUT, f"{scn}.pbn")
    SEATS = ['N', 'E', 'S', 'W']
    CALL_RE = re.compile(r'(?i)^(pass|x|xx|ap|\d[cdhsn]t?)$')
    issues = 0
    for ch in split_boards(path):
        b = tag(ch, 'Board')
        m = re.search(r'\[Auction "(\w)"\]\s*\n((?:[^\[{][^\n]*\n?)*)', ch)
        dealer = m.group(1) if m else 'N'
        # keep only real calls (drop alert refs like =1=, !, etc.)
        raw = [t for t in (m.group(2).split() if m else []) if CALL_RE.match(t)]
        di = SEATS.index(dealer)
        # coached side = N/S; collect their non-pass calls in order
        coached = [_norm_call(c) for j, c in enumerate(raw)
                   if SEATS[(di + j) % 4] in ('N', 'S') and _norm_call(c) != 'PASS']
        a = ch.find('[Auction'); i = ch.find('{', a)
        if i < 0:
            print(f"  {scn} b{b}: no coaching block"); issues += 1; continue
        body = ch[i:ch.find('}', i)]
        # Play lessons use the [ROLE]/[STAGE] marker dialect, not bid-by-bid
        # [BID] chunks (a bidding-lesson convention). The [BID]-structure
        # checks below would false-positive on every play board, so skip them
        # here. The suit-quality gate (after this loop, file-level) still runs.
        if '[ROLE' in body or '[choose-card' in body:
            continue
        # Folded (served-format) boards — the pre-2026-07 vintage where
        # coaching-curated == coaching-non-rotated: a `[show S]` intro and
        # partner's calls merged into ⟦⟧ chunks, so ONLY the student's (South's)
        # non-pass calls carry a [BID]. Check those South-only (and allow the
        # `[show S]` intro) rather than false-failing the un-folded expectation.
        is_folded = '⟦' in body
        if is_folded:
            coached = [_norm_call(c) for j, c in enumerate(raw)
                       if SEATS[(di + j) % 4] == 'S' and _norm_call(c) != 'PASS']
        bids = re.findall(r'\[BID\s+([^\]]+)\]', body)
        nbids = [_norm_call(x) for x in bids]
        probs = []
        # Every coached-side (N/S) non-pass call must have a [BID] anchor (so
        # rotation can quiz it and [ACCEPT] can attach). Extra [BID]s on
        # opponents' calls are allowed (context narration, never quizzed).
        import collections as _c
        missing = _c.Counter(coached) - _c.Counter(nbids)
        if missing:
            probs.append(f"N/S calls with no [BID]: {sorted(missing.elements())}")
        # An [BID] on an opponent (E/W) call may exist for context, but its
        # prose must NOT use the student's voice — narrating the opponents'
        # bid as @S/@v(...) tells the student they made that call. Map each
        # anchor to the seat that made it (matching call value in auction
        # order), then flag E/W anchors whose chunk carries a student token.
        seq = [(_norm_call(c), SEATS[(di + j) % 4])
               for j, c in enumerate(raw) if _norm_call(c) != 'PASS']
        parts = re.split(r'(\[BID\s+[^\]]+\])', body)
        STU = re.compile(r'@[Ss]\b|@[Yy]our\b|@v\(')
        si = 0
        opp_voice = []
        for k in range(1, len(parts), 2):
            call = _norm_call(re.match(r'\[BID\s+([^\]]+)\]', parts[k]).group(1))
            text = parts[k + 1] if k + 1 < len(parts) else ''
            while si < len(seq) and seq[si][0] != call:
                si += 1
            seat = seq[si][1] if si < len(seq) else None
            if si < len(seq):
                si += 1
            if seat in ('E', 'W') and STU.search(text):
                opp_voice.append(call)
        if opp_voice:
            probs.append(f"opponent call(s) narrated in student voice: {opp_voice}")
        # Only the conclusion marker ([show NS] or [show NESW]) is allowed (it
        # introduces the post-auction reflection). Any other [show X] inside a
        # [BID] chunk makes the trainer DEFER that prose to post-auction, where
        # it renders in the wrong person.
        allowed_show = {'NS', 'NESW'} | ({'S'} if is_folded else set())
        bad_show = [m.group(1) for m in re.finditer(r'\[show\s+([^\]]+)\]', body)
                    if m.group(1).strip() not in allowed_show]
        if bad_show:
            probs.append(f"mid-auction [show {bad_show}] — defers/scrambles prose (only [show NS]/[show NESW] allowed)")
        # [ACCEPT] must follow a [BID <non-pass>] and not be on a Pass/opening-only
        for am in re.finditer(r'\[ACCEPT\s+([^\]]+)\]', body):
            pre = body[:am.start()]
            host = re.findall(r'\[BID\s+([^\]]+)\]', pre)
            if not host:
                probs.append(f"[ACCEPT {am.group(1)}] not inside any [BID] chunk")
        if probs:
            issues += 1
            print(f"  {scn} b{b}: " + "; ".join(probs))
    # Suit-quality gate: a suit may be called "solid" only when it really is
    # (AKQ-headed, running). The GIB standard in GENERATOR.md is a prompt
    # instruction the subagents can violate — this makes it enforceable in code
    # (issues #29/#30: KQJ964 is a GOOD suit, not solid). Deterministic, and
    # conservative enough not to fire on "solid sequence"/"solid trumps"/etc.
    from suit_quality import solidity_violations
    for v in solidity_violations(path):
        issues += 1
        print(f"  {scn} b{v['board']}: '{v['phrase']}' but {v['suit']} "
              f"holdings are {v['holding']} — not solid (GIB: needs AKQ)")
    # Malformed suit escapes: a bare \<rank> is missing its \S/\H/\D/\C suit
    # letter and renders a literal backslash to the student. Deterministic.
    for b, esc in _escape_violations(path):
        issues += 1
        print(f"  {scn} b{b}: malformed suit escape '{esc}' — missing the "
              f"\\S/\\H/\\D/\\C suit letter (renders a literal backslash)")
    # Partner-hand exposure: intro/reflection must not reveal North's (partner's)
    # concrete hand (intro = no hand info at all; reflection = no card/HCP recitation).
    for b, loc, snip in _partner_exposure_violations(path):
        issues += 1
        print(f"  {scn} b{b}: partner-hand exposure in {loc}: \"{snip}\"")
    # Opponent disclosure (Class A) and narrowing (Class B): a named opponent's
    # concrete holding, or a hidden hand pinned inside its promised range/zone
    # (checked in [BID] chunks too, which the partner-exposure gate skips).
    for b, loc, cls, snip in _hidden_hand_disclosure_violations(path):
        issues += 1
        print(f"  {scn} b{b}: {cls} in {loc}: \"{snip}\"")
    # Step-0 theme gates (classroom-feedback #245/#246/#247): the theme renders
    # before the student's first decision, so it must not narrate calls still to
    # come, and it must seat the student in the chair they actually hold.
    for b, calls, snip in _premature_theme_violations(path):
        issues += 1
        print(f"  {scn} b{b}: premature theme — names {calls}, not yet bid at "
              f"step 0: \"{snip}\"")
    for b, why, snip in _intro_seat_violations(path):
        issues += 1
        print(f"  {scn} b{b}: wrong chair — {why}: \"{snip}\"")
    for b, call, snip in _response_length_violations(path):
        issues += 1
        print(f"  {scn} b{b}: a {call} RESPONSE shows four or more, not five: "
              f"\"{snip}\"")
    print(f"{scn}: {issues} board(s) with structure issues")
    return issues


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ("packets", "splice", "validate", "play-packets",
                                  "play-splice", "fill-splice"):
        sys.exit(__doc__)
    if a[0] == "validate":
        for scn in a[1:]:
            validate(scn)
        sys.exit(0)
    if a[0] == "play-splice":
        play_splice(a[1])
        sys.exit(0)
    if a[0] == "fill-splice":
        fill_splice(a[1])
        sys.exit(0)
    if a[0] == "play-packets":
        rest = a[2:]; n = 30
        fill = "--fill" in rest; rest = [x for x in rest if x != "--fill"]
        if "-n" in rest:
            i = rest.index("-n"); n = int(rest[i+1]); del rest[i:i+2]
        theme = rest[0] if rest else "hold-up"
        play_packets(a[1], theme, n, fill=fill)
        sys.exit(0)
    cmd, scn = a[0], a[1]
    if cmd == "splice":
        splice(scn)
    else:
        rest = a[2:]
        n = 30
        fill = "--fill" in rest; rest = [x for x in rest if x != "--fill"]
        boards = None
        if "--boards" in rest:
            i = rest.index("--boards"); boards = rest[i+1].split(","); del rest[i:i+2]
        if "-n" in rest:
            i = rest.index("-n"); n = int(rest[i+1]); del rest[i:i+2]
        terms = rest or ["bidding=textbook,judgment", "diff<=3"]
        packets(scn, terms, n, fill=fill, boards=boards)
