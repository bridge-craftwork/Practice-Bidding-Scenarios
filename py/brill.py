#!/usr/bin/env python3
"""brill.py — bid PBS scenario hands through Thorvald's Brill engine API and
compare the results against BBA (issue #293).

Service: https://brillservice.aalborgdata.dk (Swagger at /swagger/index.html,
though the spec documents no parameters — the grammar below was discovered by
probing).  We drive GET /bid one call at a time, accumulating the auction in
`ctx`, then write a PBN shaped like the one bba-cli emits so the existing
`auction-filter` regexes in btn/ apply unchanged and bridge-wrangler can do
the filtering — the same tool, same pattern, same normalization as the `filter`
pipeline operation uses on bba/.

API grammar (probed 2026-08-30, service version 0.1.0+20260829):
  GET /bid?hand=<PBN hand>&ctx=<calls>&seat=<NESW>&details=true|false
    hand    "AKQ5.KJ4.A73.K82"  (S.H.D.C, the PBN hand format)
    ctx     calls joined by '-', Pass is "P", double "X", redouble "XX",
            NT is "N" ("1N", not "1NT").  Empty for the opening call.
    seat    whose hand this is.  THE SERVICE HAS NO `dealer` PARAMETER: it
            always assumes ctx[0] was made by North and rejects the call with
            "Not X's turn to bid" otherwise.  So we relabel every board so the
            real dealer is presented as North (see virtual_seat) and translate
            back when writing the PBN.  Vulnerability is not a parameter at
            all, so Brill bids every board as if non-vulnerable.
  -> {"bid": "1N", "alert": true, "explanation": "...", "requires": "...",
      "analysis": [...]}   or {"message": "Bidding is over"}
      or 400 {"error": "..."}

  SERVICE BUG (reported in issue #293): /bid rejects any ONE-CHARACTER ctx --
  "Invalid auction context 'P': unexpected character at position 0".  "1C" and
  "P-P" both parse, and the error for ctx="P-X" reads "Current auction: [P]",
  so the tokenizer handles P fine mid-string; only a length-1 context trips it.
  The one auction that hits this is "dealer passed, second seat to call" -- i.e.
  ~1 board in 4.  We fall back to the legacy /bidold endpoint for exactly that
  call (it accepts ctx="P" and returns the same opening decisions) and count how
  often we did.  /bidold is NOT a general substitute: it ignores the auction
  context entirely (it bids 1C over an opponent's 1N), so it is used for this
  single case only.

GET /autoplay?deal=<PBN deal>&dealer=<seat> bids AND plays a whole board in one
request -- it takes a real dealer parameter, so it needs no relabeling and hits
no tokenizer bug, and it returns contract/declarer/tricks/score as well.  But it
always plays all 52 cards (30-50s per board; no flag suppresses it), so it is a
cross-check mode here, not the workhorse.

Subcommands
  probe    verify the ctx grammar and service liveness
  bid      pbn/<scn>.pbn  -> brill/<scn>.pbn
  filter   brill/<scn>.pbn -> brill-filtered/<scn>.pbn  (bridge-wrangler)
  compare  report Brill vs BBA pass rates + annotation coverage

Usage
  python3 py/brill.py probe
  python3 py/brill.py bid 1N --limit 20 --workers 8
  python3 py/brill.py filter 1N
  python3 py/brill.py compare 1N 1m-1N Jacoby_2N

Run from the project root.
"""
import os
import sys

# py/select.py shadows the stdlib `select` that subprocess imports, so drop this
# script's own directory from sys.path before importing anything else. (The rest
# of the repo sidesteps this by always running under `python3 -P`; this way
# `python3 py/brill.py` works too.)
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [p for p in sys.path if p and os.path.abspath(p) != _HERE]

import argparse
import json
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(ROOT, "build-scripts-mac"))

BASE = os.environ.get("BRILL_URL", "https://brillservice.aalborgdata.dk")
SEATS = "NESW"
PASS = "P"
SEP = "-"
MAX_CALLS = 60          # runaway guard
BIDOLD_FALLBACKS = [0]  # count of single-pass contexts routed to /bidold
SIDE = {"N": "NS", "S": "NS", "E": "EW", "W": "EW"}


# ---------------------------------------------------------------- HTTP


def api(path, params, timeout=30, retries=3):
    url = f"{BASE}/{path}?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:          # 400 carries a JSON error
            body = e.read().decode("utf-8", "replace")
            try:
                return json.loads(body)
            except ValueError:
                last = f"HTTP {e.code}: {body[:200]}"
        except Exception as e:                       # noqa: BLE001
            last = e
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{url}\n  failed after {retries} tries: {last}")


# ---------------------------------------------------------------- PBN in


def split_boards(raw):
    parts = re.split(r'(?=^\[Event )', raw, flags=re.M)
    return [p for p in parts if p.startswith("[Event")]


def tag(chunk, name):
    m = re.search(r'\[' + name + r' "([^"]*)"\]', chunk)
    return m.group(1) if m else None


def parse_deal(deal):
    """'N:h1 h2 h3 h4' -> {'N': h1, 'E': h2, ...} (clockwise from the prefix)."""
    first, hands = deal.split(":", 1)
    hands = hands.split()
    start = SEATS.index(first.strip())
    return {SEATS[(start + i) % 4]: h for i, h in enumerate(hands)}


# ---------------------------------------------------------------- auction


def virtual_seat(actual, dealer):
    """Relabel so the dealer is North — the only frame the service accepts."""
    return SEATS[(SEATS.index(actual) - SEATS.index(dealer)) % 4]


def auction_closed(calls):
    if len(calls) < 4:
        return False
    return all(c == PASS for c in calls[-3:])


def bid_board(deal, dealer, details=True, sleep=0.0):
    """Drive /bid until the auction closes. Returns (calls, explanations)."""
    hands = parse_deal(deal)
    calls, notes = [], []
    while not auction_closed(calls) and len(calls) < MAX_CALLS:
        actual = SEATS[(SEATS.index(dealer) + len(calls)) % 4]
        ctx = SEP.join(calls)
        params = {
            "hand": hands[actual],
            "ctx": ctx,
            "seat": virtual_seat(actual, dealer),
            "details": "true" if details else "false",
        }
        r = api("bid", params)
        if "bid" not in r and len(ctx) == 1 and \
                "position 0" in (r.get("error") or ""):
            BIDOLD_FALLBACKS[0] += 1          # the ctx="P" service bug
            r = api("bidold", params)
        if "bid" not in r:
            raise RuntimeError(r.get("error") or r.get("message") or str(r)[:200])
        calls.append(r["bid"].strip().upper())
        notes.append((r.get("explanation") or "").strip())
        if sleep:
            time.sleep(sleep)
    if not auction_closed(calls):
        raise RuntimeError(f"auction did not close in {MAX_CALLS} calls")
    return calls, notes


def is_bid(call):
    return call not in (PASS, "X", "XX")


def contract_of(calls, dealer):
    """Return (contract, declarer) BBA-style, e.g. ('3NTX','S') or ('Pass','')."""
    last, last_i, doubled = None, None, ""
    for i, c in enumerate(calls):
        if is_bid(c):
            last, last_i, doubled = c, i, ""
        elif c in ("X", "XX"):
            doubled = c
    if last is None:
        return "Pass", ""
    level, denom = last[0], ("NT" if last[1:] in ("N", "NT") else last[1:])
    seat_of = [SEATS[(SEATS.index(dealer) + i) % 4] for i in range(len(calls))]
    side = SIDE[seat_of[last_i]]
    for i, c in enumerate(calls):        # declarer = first of that side to name it
        if is_bid(c) and ("NT" if c[1:] in ("N", "NT") else c[1:]) == denom \
                and SIDE[seat_of[i]] == side:
            return f"{level}{denom}{doubled}", seat_of[i]
    return f"{level}{denom}{doubled}", seat_of[last_i]


def autoplay_board(deal, dealer):
    """One request per board via /autoplay: bids AND plays. Slow but exact."""
    r = api("autoplay", {"deal": deal, "dealer": dealer}, timeout=180)
    if "auction" not in r:
        raise RuntimeError(r.get("error") or str(r)[:200])
    calls = [c.strip().upper() for c in r["auction"].split(SEP) if c.strip()]
    by_bid = r.get("auction_with_explanations") or []
    notes = [(e.get("means") or "").strip() for e in by_bid]
    notes += [""] * (len(calls) - len(notes))
    extra = {"Contract": r.get("contract"), "Declarer": r.get("declarer"),
             "Result": r.get("tricks"), "Score": r.get("score")}
    return calls, notes, extra


# ---------------------------------------------------------------- PBN out


def pbn_call(c):
    return "Pass" if c == PASS else c


def render_auction(calls, notes, dealer, annotate=True):
    """Emit a bba-cli-shaped [Auction] block with =n= note markers."""
    toks, note_lines, n = [], [], 0
    for c, expl in zip(calls, notes):
        t = pbn_call(c)
        if annotate and expl:
            n += 1
            t = f"{t} ={n}="
            note_lines.append(f'[Note "{n}:{expl}"]')
        toks.append(t)
    w = max([6] + [len(t) + 2 for t in toks])
    rows = ["".join(x.ljust(w) for x in toks[i:i + 4]).rstrip()
            for i in range(0, len(toks), 4)]
    return f'[Auction "{dealer}"]\n' + "\n".join(rows) + "\n" + \
           ("\n".join(note_lines) + "\n" if note_lines else "")


def board_pbn(src, calls, notes, dealer, annotate=True, extra=None):
    out = []
    for k in ("Event", "Site", "Board", "West", "North", "East", "South",
              "Dealer", "Vulnerable", "Deal"):
        v = tag(src, k)
        if v is not None:
            out.append(f'[{k} "{v}"]')
    contract, declarer = contract_of(calls, dealer)
    if extra and extra.get("Contract"):          # /autoplay knows for certain
        contract, declarer = extra["Contract"], extra.get("Declarer") or declarer
    result = str(extra["Result"]) if extra and extra.get("Result") is not None else "?"
    out += [f'[Declarer "{declarer}"]', f'[Contract "{contract}"]',
            f'[Result "{result}"]']
    if extra and extra.get("Score") is not None:
        out.append(f'[Score "NS {extra["Score"]}"]')
    return "\n".join(out) + "\n" + render_auction(calls, notes, dealer, annotate) + "\n"


# ---------------------------------------------------------------- filtering


def auction_filter(scn):
    """The btn/ auction-filter directive (dlr/ carries the same comment)."""
    for path in (f"btn/{scn}.btn", f"dlr/{scn}.dlr"):
        if os.path.exists(path):
            m = re.search(r'^#?\s*auction-filter:\s*(.+)$',
                          open(path, encoding="utf-8", errors="replace").read(),
                          flags=re.M | re.I)
            if m:
                return m.group(1).strip()
    return None


def normalize(expr):
    """The exact normalization the pipeline's filter operation applies."""
    from operations.filter import normalize_filter_for_bridge_wrangler
    return normalize_filter_for_bridge_wrangler(expr)


def count_boards(path):
    if not os.path.exists(path):
        return None
    return len(split_boards(open(path, encoding="utf-8", errors="replace").read()))


# ---------------------------------------------------------------- commands


def cmd_probe(args):
    print(f"service : {BASE}")
    print(f"version : {api('version', {})}")
    print(f"systems : {api('systems', {})}")
    deal = "N:T82.A843.43.K952 Q974.75.J9865.J6 A63.QJ92.AT2.A83 KJ5.KT6.KQ7.QT74"
    for dealer in SEATS:                 # every dealer must work, not just North
        t = time.time()
        calls, notes = bid_board(deal, dealer, details=True)
        print(f"\ndealer {dealer}: {[pbn_call(c) for c in calls]}  "
              f"-> {contract_of(calls, dealer)}   ({time.time()-t:.1f}s)")
        if dealer == "S":
            for c, n in zip(calls, notes):
                print(f"    {pbn_call(c):<6} {n}")
    print("\nIf those auctions are legal and sensible, the ctx grammar and the "
          "dealer->North relabeling are right.")


def cmd_bid(args):
    src_path = args.source or f"pbn/{args.scenario}.pbn"
    boards = split_boards(open(src_path, encoding="utf-8", errors="replace").read())
    if args.limit:
        boards = boards[:args.limit]
    os.makedirs("brill", exist_ok=True)
    out_path = f"brill/{args.scenario}.pbn"
    t0 = time.time()
    done = [0]

    def work(b):
        deal, dealer = tag(b, "Deal"), tag(b, "Dealer")
        if not deal or not dealer:
            return None
        try:
            if args.autoplay:
                calls, notes, extra = autoplay_board(deal, dealer)
            else:
                calls, notes = bid_board(deal, dealer, args.details, args.sleep)
                extra = None
        except Exception as e:                        # noqa: BLE001
            print(f"  board {tag(b,'Board')}: {e}", file=sys.stderr)
            return None
        done[0] += 1
        if done[0] % 25 == 0:
            print(f"  {done[0]}/{len(boards)} boards, {time.time()-t0:.0f}s",
                  file=sys.stderr)
        return board_pbn(b, calls, notes, dealer, args.details, extra)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(work, boards))

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"% Generated by py/brill.py from {src_path}\n")
        f.write(f"% Engine: {BASE} {api('version', {}).get('version','?')}\n")
        for r in results:
            if r:
                f.write(r)
    ok = sum(1 for r in results if r)
    el = time.time() - t0
    print(f"{args.scenario}: {ok}/{len(boards)} boards -> {out_path} "
          f"({el:.0f}s, {el/max(ok,1):.2f}s/board, {len(boards)-ok} failed)")
    if BIDOLD_FALLBACKS[0]:
        print(f"  note: {BIDOLD_FALLBACKS[0]} call(s) used /bidold for the "
              f"ctx='P' service bug (see the module docstring)")


def cmd_filter(args):
    pat = auction_filter(args.scenario)
    if not pat:
        sys.exit(f"no auction-filter for {args.scenario}")
    src = f"brill/{args.scenario}.pbn"
    if not os.path.exists(src):
        sys.exit(f"{src} not found — run `bid` first")
    from config import MAC_TOOLS
    # Brill explains EVERY call, so brill/ carries a =n= marker on every bid,
    # whereas bba-cli marks only conventional ones.  The btn/ auction patterns
    # are written against that BBA shape ("1H +Pass +2N"), so an unstripped
    # brill file fails every one of them.  Filter a marker-free copy to keep
    # the comparison apples-to-apples; [Note] lines survive, so the patterns
    # that match on note text still see them.
    stripped = re.sub(r' +=\d+=', '',
                      open(src, encoding="utf-8", errors="replace").read())
    src_nomark = f"brill/.{args.scenario}.nomarks.pbn"
    open(src_nomark, "w", encoding="utf-8").write(stripped)
    os.makedirs("brill-filtered", exist_ok=True)
    os.makedirs("brill-filtered-out", exist_ok=True)
    kept = f"brill-filtered/{args.scenario}.pbn"
    out = f"brill-filtered-out/{args.scenario}.pbn"
    cmd = [MAC_TOOLS["bridge_wrangler"], "filter", "-i", src_nomark,
           "-p", normalize(pat), "-m", kept, "-n", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"bridge-wrangler filter failed:\n{r.stderr}")
    os.remove(src_nomark)
    k, n = count_boards(kept) or 0, count_boards(src) or 0
    print(f"{args.scenario}: {k}/{n} kept ({100*k/max(n,1):.1f}%)  pattern={pat!r}")


def cmd_compare(args):
    hdr = f"{'scenario':<28}{'BBA kept':>14}{'Brill kept':>14}   annotation"
    print(hdr)
    print("-" * len(hdr))
    for scn in args.scenarios:
        bk, bn = count_boards(f"bba-filtered/{scn}.pbn"), count_boards(f"bba/{scn}.pbn")
        rk, rn = count_boards(f"brill-filtered/{scn}.pbn"), count_boards(f"brill/{scn}.pbn")
        if rn is None:
            print(f"{scn:<28}  (no brill/{scn}.pbn — run `bid` first)")
            continue
        raw = open(f"brill/{scn}.pbn", encoding="utf-8", errors="replace").read()
        marks = len(re.findall(r'=\d+=', raw))
        calls = len(re.findall(r'^(?:Pass|X{1,2}|\dN?[CDHSN]?)\b', raw, flags=re.M))
        bba_s = f"{bk}/{bn} {100*bk/bn:.0f}%" if bk is not None and bn else "-"
        br_s = f"{rk}/{rn} {100*rk/rn:.0f}%" if rk is not None and rn else f"-/{rn}"
        print(f"{scn:<28}{bba_s:>14}{br_s:>14}   {marks} notes on {rn} boards")


def main():
    p = argparse.ArgumentParser(description="Brill engine harness for PBS (issue #293)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("probe", help="verify ctx grammar + service liveness")
    pr.set_defaults(func=cmd_probe)

    b = sub.add_parser("bid", help="bid a scenario's hands through Brill")
    b.add_argument("scenario")
    b.add_argument("--source", help="input PBN (default pbn/<scn>.pbn)")
    b.add_argument("--limit", type=int, default=0, help="first N boards only")
    b.add_argument("--workers", type=int, default=8, help="parallel boards")
    b.add_argument("--sleep", type=float, default=0.0, help="delay between calls")
    b.add_argument("--autoplay", action="store_true",
                   help="use /autoplay (one request/board; also plays the hand "
                        "for contract+tricks; 30-50s/board)")
    b.add_argument("--no-details", dest="details", action="store_false",
                   help="skip explanations (faster, no [Note] output)")
    b.set_defaults(func=cmd_bid, details=True)

    f = sub.add_parser("filter", help="apply the btn auction-filter to brill/")
    f.add_argument("scenario")
    f.set_defaults(func=cmd_filter)

    c = sub.add_parser("compare", help="Brill vs BBA filter pass rates")
    c.add_argument("scenarios", nargs="+")
    c.set_defaults(func=cmd_compare)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
