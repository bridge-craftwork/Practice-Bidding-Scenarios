#!/usr/bin/env python3
"""
board_version_token.py — R3 rotation-canonical board-version token.

The Bridge-Classroom producer contract (coaching-non-rotated/CLAUDE.md, R3)
requires a per-board content-identity stamp that is INVARIANT to table rotation:
every rotation of the same deal+auction maps to the same token. BC treats it as
opaque — it records the token and echoes it into "Report a Problem" but never
computes, verifies, or compares it. There is exactly one implementation of the
scheme: this one.

Algorithm (per the contract):
  1. Find the seat holding the ♠A (every deal has exactly one).
  2. Rotate so that holder → North (apply the SAME rotation k to the hands and to
     the auction: calls keep their order, only the dealer/seat label shifts by k).
  3. token = sha256( normalize(canonical_deal) + "|" + normalize(canonical_auction) )
     lowercase hex, computed over EXTRACTED values (not raw file bytes), so
     cosmetic reformatting never churns the token.

Normalization (defined here — opaque to BC, so this file IS the definition):
  * canonical_deal   -> "N:<h0> <h1> <h2> <h3>", hands clockwise from the ♠A
    holder (N,E,S,W); each hand uppercased with ranks sorted A→2 within each suit.
  * canonical_auction-> "<dealer>:<call> <call> …", dealer = rotated dealer seat
    letter; calls uppercased, in order, PASS/X/XX preserved, notrump collapsed to
    one form (`3N`==`3NT`). Alerts (`=n=`) / annotations (`!`,`?`) are stripped;
    any OTHER unrecognized token raises (so variance can't silently churn a token).

Pure stdlib (runs unchanged in GitHub Actions and on the Mac).
"""
import hashlib
import re

_SEATS = "NESW"
_RANK_ORDER = "AKQJT98765432"
_BID_RE = re.compile(r"^([1-7])(C|D|H|S|NT|N)$")
_ALERT_RE = re.compile(r"^=\d+=$")   # BBA alert marker — not a call
_ANNOT_RE = re.compile(r"^[!?]+$")    # PBN call annotation (!, ?, !!) — not a call


def _norm_hand(hand):
    """Uppercase a 'S.H.D.C' hand and sort ranks A→2 within each suit."""
    suits = hand.split(".")
    out = []
    for s in suits:
        cs = sorted(s.upper(), key=lambda c: _RANK_ORDER.index(c)
                    if c in _RANK_ORDER else len(_RANK_ORDER))
        out.append("".join(cs))
    return ".".join(out)


def parse_deal(deal):
    """PBN [Deal] value -> [N_hand, E_hand, S_hand, W_hand] (seat order)."""
    prefix, rest = deal.split(":", 1)
    start = _SEATS.index(prefix.strip()[-1].upper())
    hands = rest.split()
    if len(hands) != 4:
        raise ValueError(f"expected 4 hands, got {len(hands)}: {deal!r}")
    by_seat = {}
    for i, h in enumerate(hands):
        by_seat[_SEATS[(start + i) % 4]] = h
    return [by_seat["N"], by_seat["E"], by_seat["S"], by_seat["W"]]


def _spade_ace_seat(hands):
    """Index (0=N..3=W) of the hand holding the ♠A."""
    for i, h in enumerate(hands):
        if "A" in h.split(".")[0].upper():
            return i
    raise ValueError(f"no ♠A found in {hands!r}")


def normalize_calls(tokens):
    """Raw auction token stream -> canonical calls (PASS/X/XX/bids).

    Two hardenings so the (once-locked) token can't drift on future data-entry
    variance:
      * notrump is canonicalized to one form: `3N` and `3NT` both -> `3NT`.
      * a token that is neither a call nor a KNOWN-droppable annotation (BBA
        `=n=` alert, PBN `!`/`?`) RAISES, rather than being silently dropped —
        so a stray/typo'd call surfaces loudly instead of changing the hash.
    """
    calls = []
    for t in tokens:
        u = t.strip().upper()
        if not u:
            continue
        if u in ("PASS", "X", "XX"):
            calls.append(u)
            continue
        m = _BID_RE.match(u)
        if m:
            calls.append(m.group(1) + ("NT" if m.group(2) == "N" else m.group(2)))
            continue
        if _ALERT_RE.match(u) or _ANNOT_RE.match(u):
            continue  # alert / annotation — legitimately not a call
        raise ValueError(f"unrecognized auction token: {t!r}")
    return calls


def board_version_token(deal, dealer, calls):
    """Return the lowercase-hex rotation-canonical token for one board.

    deal   : PBN [Deal] value, e.g. "N:T75.KJ2.A872.J92 K842.3.JT5.AQT64 …"
    dealer : dealer seat letter (from [Auction "S"] or [Dealer]); '' tolerated.
    calls  : already-normalized list of calls (use normalize_calls first).
    """
    hands = parse_deal(deal)
    s = _spade_ace_seat(hands)
    canon_hands = [_norm_hand(hands[(s + j) % 4]) for j in range(4)]
    canonical_deal = "N:" + " ".join(canon_hands)
    d = _SEATS.index(dealer.strip().upper()) if dealer and dealer.strip().upper() in _SEATS else 0
    canonical_dealer = _SEATS[(d - s) % 4]
    canonical_auction = canonical_dealer + ":" + " ".join(calls)
    payload = canonical_deal + "|" + canonical_auction
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    # Self-test: determinism + rotation invariance.
    deal = "N:T75.KJ2.A872.J92 K842.3.JT5.AQT64 AQ9.QT854.KQ43.K J63.A976.96.8753"
    dealer, calls = "S", ["1H", "PASS", "2H", "PASS", "3H", "PASS", "4H", "PASS", "PASS", "PASS"]
    base = board_version_token(deal, dealer, calls)
    print("token:", base)

    def rotate_deal(dl, r):
        hands = parse_deal(dl)  # N,E,S,W
        rot = [hands[(i - r) % 4] for i in range(4)]  # physical table rotation
        return "N:" + " ".join(rot)

    ok = True
    for r in range(4):
        rd = rotate_deal(deal, r)
        rdealer = _SEATS[(_SEATS.index(dealer) + r) % 4]
        t = board_version_token(rd, rdealer, calls)
        print(f"  rot {r}: dealer={rdealer} token={t} {'OK' if t == base else 'MISMATCH'}")
        ok = ok and (t == base)
    print("rotation-invariant:", ok)

    # Hardening checks: NT canonicalization + raise on unrecognized token.
    nt_deal = "N:AKQ.234.567.8TJ 234.567.8TJ.9QK 567.89T.JQK.A23 89T.AKQ.234.456"
    assert (board_version_token(nt_deal, "N", normalize_calls("3N PASS PASS PASS".split()))
            == board_version_token(nt_deal, "N", normalize_calls("3NT PASS PASS PASS".split()))), \
        "3N and 3NT must collapse to the same token"
    try:
        normalize_calls(["1H", "ZZ", "PASS"])
        raise AssertionError("expected ValueError on unrecognized token")
    except ValueError:
        pass
    print("NT-collapse + raise-on-unknown: OK")
