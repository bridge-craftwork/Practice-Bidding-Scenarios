#!/usr/bin/env python3
"""Exam gap detector — the four types the Finesse_Exam could not field
from earlier scans, hunted with tighter, teachable signatures. One pass,
four classes; a board's DD line is computed once and tested per class.

  dblsplit — double finesse with a SPLIT tenace (A+Q+T or A+J+T spread
      across both NS hands, both missing honors with defenders). Acid: the
      suit is led toward a tenace card at least twice and a sub-honor wins
      while a missing honor is still live.

  twoway — a true two-way queen guess made TEACHABLE by the auction: NS
      hold A,K with J in one hand and T in the other (hookable either way),
      the Q sits with the ONLY defender who bid, and the DD line hooks
      through that bidder (sub-honor wins while the Q is live; Q never
      scores). "Play the bidder for the queen."

  choice — combine two chances with the fallback visible: some suit X sees
      a led-toward sub-honor LOSE to a defender honor, and a LATER trick in
      a different suit Y sees a led-toward sub-honor WIN while a missing
      honor is live. First chance fails, second chance lands.

  rabbi — the marked drop: one NS hand holds A+Q (3+ cards, no K in NS),
      the K is SINGLETON with a defender who made a non-pass bid (his bid
      is the reason to reject the finesse), and the DD line drops the K
      under the ace with the defense never winning that suit.

South declares a game/slam (3N or 4+) making EXACTLY. Passive lead for the
scan; the real-lead re-verify and dump-read remain the human gates.

Usage: exam_gap_detect.py bba/Pool_A.pbn [...] > scan.json
"""
import sys, json, re
from endplay.dds import calc_dd_table, solve_board
from endplay.types import Deal, Denom, Player, Card

SEATS = ["N","E","S","W"]
RANKS = "AKQJT98765432"
DENOM = {"C": Denom.clubs, "D": Denom.diamonds, "H": Denom.hearts,
         "S": Denom.spades, "N": Denom.nt}
PLAYER = {"N": Player.north, "E": Player.east, "S": Player.south, "W": Player.west}
SEAT_OF = {Player.north:"N", Player.east:"E", Player.south:"S", Player.west:"W"}
PL = {"N":"north","E":"east","S":"south","W":"west"}
LEADER_OF = {"N":"E","E":"S","S":"W","W":"N"}

def parse(ds):
    first, rest = ds.split(":"); hands = rest.split()
    order = [first] + [SEATS[(SEATS.index(first)+i)%4] for i in range(1,4)]
    return {s: dict(zip("SHDC", h.split("."))) for s, h in zip(order, hands)}

def tricks(ds, declarer, strain):
    return calc_dd_table(Deal(ds))[DENOM[strain], PLAYER[declarer]]

def sl(c): return c.suit.name[0].upper()
def rk(c): return c.rank.name[1:]

def winner(trick, trumpL):
    ts = None if trumpL == "N" else trumpL
    bs, bc = trick[0]
    for s, c in trick[1:]:
        if ts and sl(c) == ts and sl(bc) != ts: bs, bc = s, c
        elif sl(c) == sl(bc) and c.rank.value > bc.rank.value: bs, bc = s, c
    return bs, bc

def dd_line(ds, contract, declarer, lead):
    d = Deal(ds); d.trump = DENOM[contract[1]]
    d.first = getattr(Player, PL[LEADER_OF[declarer]])
    chrono = []
    for i in range(52):
        s = SEAT_OF[d.curplayer]
        c = Card(lead) if i == 0 else max(solve_board(d), key=lambda kv: kv[1])[0]
        chrono.append((s, c)); d.play(c)
    return chrono

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from harvest_common import book_lead

def passive_lead(hands, leader, *rest):
    """Book lead (harvest_common) — trump letter is the LAST argument; any
    avoid-suit argument from older call sites is intentionally ignored: the
    acid must run on the REAL lead, even when it hits the taught suit."""
    return book_lead(hands, leader, rest[-1])

def compact_auction(b):
    am = re.search(r'\[Auction "[NESW]"\]\s*\n(.*?)(?=\n\[|\n\{|\Z)', b, re.S)
    if not am: return ""
    return " ".join(tok for ln in am.group(1).strip().splitlines() for tok in ln.split())

def seat_calls(calls, dealer):
    out = {s: [] for s in SEATS}
    seat = dealer
    for tok in calls.split():
        if tok.startswith("="): continue
        if tok not in ("Pass", "AP"): out[seat].append(tok)
        seat = SEATS[(SEATS.index(seat)+1) % 4]
    return out

def suit_events(chrono, hands, trumpL):
    """Per trick: (t, suit, led_seat, winner, win_rank, honors_out_before) for
    tricks led in a plain suit; honors_out = A/K/Q/J of the suit still unplayed
    with the DEFENDERS at the moment the trick starts."""
    played = {s: {su: set() for su in "SHDC"} for s in SEATS}
    ev = []
    for t in range(13):
        trick = chrono[t*4:t*4+4]
        led_seat, led_card = trick[0]
        suit = sl(led_card)
        if suit != trumpL:
            out = sum(1 for s in ("E","W") for r in hands[s][suit]
                      if r in "AKQJ" and r not in played[s][suit])
            w, wc = winner(trick, trumpL)
            ev.append((t+1, suit, led_seat, w, rk(wc), out))
        for s, c in trick:
            played[s][sl(c)].add(rk(c))
    return ev

def scan(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    out = []
    for b in re.split(r'(?=^\[Board )', txt, flags=re.M):
        mb = re.search(r'\[Board "(\d+)"\]', b)
        mc = re.search(r'\[Contract "(\d)([CDHSN])', b)
        mdeal = re.search(r'\[Deal "([^"]+)"\]', b)
        mdlr = re.search(r'\[Dealer "([NESW])"\]', b)
        if not (mb and mc and mdeal and mdlr and re.search(r'\[Declarer "S"\]', b)):
            continue
        level, strain = int(mc.group(1)), mc.group(2)
        if not (level >= 4 or (level == 3 and strain == "N")):
            continue
        hands = parse(mdeal.group(1))
        calls = compact_auction(b)
        sc = seat_calls(calls, mdlr.group(1))
        bidders = [s for s in ("E","W") if sc[s]]

        # ---- structural pre-filters (cheap) ----
        cands = []
        for suit in "SHDC":
            if suit == strain: continue
            n, s_ = hands["N"][suit], hands["S"][suit]
            comb = set(n) | set(s_)
            # dblsplit: A,Q,T or A,J,T combined but split, missing two honors
            for ten, mis in (({"A","Q","T"}, ("K","J")), ({"A","J","T"}, ("K","Q"))):
                if ten <= comb and not (set(mis) & comb):
                    in_n = len(set(n) & ten)
                    if 1 <= in_n <= 2 and len(n) >= 2 and len(s_) >= 2:
                        hold = [next((x for x in SEATS if m in hands[x][suit]), None) for m in mis]
                        if all(h in ("E","W") for h in hold):
                            cands.append(("dblsplit", suit, {"missing":"".join(mis),"holders":hold}))
                    break
            # twoway: missing only Q; J and T split across NS; A,K in NS
            if ({"A","K"} <= comb and "Q" not in comb and {"J","T"} <= comb
                    and len(n) >= 3 and len(s_) >= 3
                    and (("J" in n) != ("T" in n))):
                qh = next((x for x in ("E","W") if "Q" in hands[x][suit]), None)
                if qh and len(bidders) == 1 and qh == bidders[0]:
                    cands.append(("twoway", suit, {"qholder":qh,"bidder_calls":sc[qh]}))
            # rabbi: A+Q one hand (no K in NS), K stiff with a bidder
            for hand in ("N","S"):
                h = hands[hand][suit]
                if "A" in h and "Q" in h and len(h) >= 3 and "K" not in comb:
                    kh = next((x for x in ("E","W") if hands[x][suit] == "K"), None)
                    if kh and sc[kh]:
                        cands.append(("rabbi", suit, {"kholder":kh,"tenace_hand":hand,
                                                      "kbids":sc[kh]}))
        # choice pre-filter: two+ plain suits with an NS ace + a missing K/Q out
        csuits = [su for su in "SHDC" if su != strain
                  and "A" in (hands["N"][su] + hands["S"][su])
                  and any(m not in hands["N"][su]+hands["S"][su] for m in "KQ")
                  and len(hands["N"][su]) + len(hands["S"][su]) >= 6]
        if len(csuits) >= 2:
            cands.append(("choice", "-", {"suits":csuits}))
        if not cands:
            continue

        need = 6 + level
        try:
            if tricks(mdeal.group(1), "S", strain) != need:
                continue
        except Exception:
            continue
        lead = passive_lead(hands, "W", strain)
        try:
            chrono = dd_line(mdeal.group(1), f"{level}{strain}", "S", lead)
        except Exception:
            continue
        ev = suit_events(chrono, hands, strain)

        hits = []
        for cls, suit, info in cands:
            if cls in ("dblsplit", "twoway"):
                rel = [e for e in ev if e[1] == suit and e[2] in ("N","S")]
                subwins = [e for e in rel if e[3] in ("N","S")
                           and e[4] not in "AK" and e[5] >= 1
                           and RANKS.index(e[4]) > 1]
                if cls == "dblsplit":
                    if len(rel) >= 2 and subwins:
                        losses = [e for e in rel if e[3] in ("E","W")]
                        hits.append({"class":cls,"suit":suit,**info,
                                     "leads":len(rel),"first_lost":bool(losses and rel[0][3] in ('E','W'))})
                else:
                    q_won = any(e[1]==suit and e[3]==info["qholder"] and e[4]=="Q" for e in ev)
                    if subwins and not q_won:
                        hits.append({"class":cls,"suit":suit,**info,
                                     "hook_trick":subwins[0][0]})
            elif cls == "rabbi":
                drop = [e for e in ev if e[1] == suit and e[3] in ("N","S")
                        and e[4] == "A"]
                k_never = not any(e[1]==suit and e[3]==info["kholder"] for e in ev)
                if drop and k_never:
                    hits.append({"class":cls,"suit":suit,**info,
                                 "drop_trick":drop[0][0]})
            else:  # choice
                # neither chance may live in the LED suit — those "wins" are
                # stopper artifacts, the class's chronic false positive
                lead_suit = lead[0]
                loss = None
                for e in ev:
                    if (e[1] in info["suits"] and e[1] != lead_suit
                            and e[2] in ("N","S") and e[3] in ("E","W")):
                        loss = e; break
                if loss:
                    win = next((e for e in ev if e[0] > loss[0] and e[1] in info["suits"]
                                and e[1] != loss[1] and e[1] != lead_suit
                                and e[2] in ("N","S")
                                and e[3] in ("N","S") and e[4] not in "AK"
                                and e[5] >= 1), None)
                    if win:
                        hits.append({"class":cls,"lose":{"suit":loss[1],"trick":loss[0]},
                                     "win":{"suit":win[1],"trick":win[0],"card":win[4]}})
        if not hits:
            continue
        out.append({"board": int(mb.group(1)), "contract": f"{level}{strain}",
                    "deal": mdeal.group(1), "auction": calls, "lead": lead,
                    "hits": hits})
    return out

if __name__ == "__main__":
    results = {}
    for path in sys.argv[1:]:
        name = re.sub(r'.*/', '', path).replace(".pbn", "")
        try:
            results[name] = scan(path)
            sys.stderr.write(f"{name}: {len(results[name])} candidates\n")
        except Exception as e:
            sys.stderr.write(f"{name}: ERROR {e}\n")
    print(json.dumps(results, indent=1))
