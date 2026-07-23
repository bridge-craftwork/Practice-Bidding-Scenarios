#!/usr/bin/env python3
"""Make coaching-non-rotated/*.pbn files compatible with bridge-classroom.com.

bridge-classroom is Rick Wilson's "dumb renderer" teaching platform
(github.com/Rick-Wilson/Bridge-Classroom): it reads a PBN and follows the
embedded coaching directives literally, with no inference. To render cleanly
there, each coached board needs:

  1. No pre-auction ``{...}`` comment blocks.  The ``{Shape ...}``/``{HCP ...}``/
     ``{Losers ...}`` stats and any ``{Curate ...}`` metadata are authoring/curation
     aids the Bridge Play Trainer ignores; bridge-classroom should not see them.
  2. Sequential board numbers.  ``[Board]`` is renumbered 1..n in file order.
  3. The source board number preserved in a separate ``[OriginalBoard]`` tag
     (inserted only if absent, so it captures the number once and survives reruns).
  4. The post-auction coaching ``{...}`` block to open by revealing the student's
     hand.  If the block has no leading ``[show ...]`` directive, ``[show S]`` is
     prepended (matching the hand-tuned model board in Basic_Major.pbn).

The model for the transform is the first board of
``coaching-non-rotated/Basic_Major.pbn``.

The script edits files **in place** under ``coaching-non-rotated/`` and is
idempotent: a second run is a no-op. Run from the project root:

    python3 -P py/bridge_classroom.py              # all *.pbn
    python3 -P py/bridge_classroom.py Basic_Major  # one (with or without .pbn)
    python3 -P py/bridge_classroom.py --check       # dry run, report only

(``-P`` keeps py/'s ``select.py`` from shadowing the stdlib.)
"""

import argparse
import re
import sys
from pathlib import Path

# Load the sibling play_line module by file path. `python3 -P` omits the script
# dir from sys.path, and we must NOT prepend py/ to sys.path — it holds a
# select.py that would shadow stdlib `select` and break endplay's DDS. importlib
# by path sidesteps both.
import importlib.util as _ilu
_pl_path = Path(__file__).resolve().parent / "play_line.py"
_pl_spec = _ilu.spec_from_file_location("play_line", _pl_path)
play_line = _ilu.module_from_spec(_pl_spec)
_pl_spec.loader.exec_module(play_line)

ROOT = Path(__file__).resolve().parent.parent
COACHING_DIR = ROOT / "coaching-non-rotated"


def split_boards(text):
    """Split a PBN into per-board text chunks.

    A board starts at an ``[Event ...]`` tag at the start of a line. We split on
    that tag rather than tracking ``{}`` depth, so a board with an unbalanced
    coaching block (the known ``}}`` defect in some files) can't merge into its
    neighbour. ``[Event`` never appears inside coaching prose.
    """
    parts = re.split(r"(?m)(?=^\[Event\b)", text)
    return [p.rstrip("\n") for p in parts if p.strip()]


# A coaching/comment block: from the first '{' to the first '}'. Prose carries no
# nested braces, so non-greedy + DOTALL captures exactly one block and leaves any
# stray trailing '}' (the defect) outside the match, to be cleaned separately.
_BLOCK = re.compile(r"\{.*?\}", re.DOTALL)


def transform_board(text, seq):
    """Return (new_text, stats) for one board renumbered to ``seq``."""
    stats = {"stripped": 0, "show_added": False, "orig_added": False,
             "brace_fixed": False, "folded": 0, "fold_flagged": 0,
             "fold_unmatched": 0, "reflowed": False, "pass_added": False}

    m = re.search(r"(?m)^\[Auction\b.*$", text)
    if m is None:
        # No auction — not a coached board. Renumber only, leave the rest as-is.
        return _renumber(text, seq, stats), stats

    pre = text[: m.start()]
    post = text[m.start():]  # [Auction tag + call lines + coaching block + tail

    # 1. Drop every pre-auction {...} block (Shape/HCP/Losers, Curate, ...),
    #    consuming the block's own trailing newline so no blank gap is left.
    pre, n = _BLOCK.subn("", pre)
    pre = re.sub(r"\n[ \t]*(?=\n)", "", pre)  # squeeze any blank lines left behind
    stats["stripped"] = len(re.findall(r"\{", text[: m.start()]))

    # 2. In the auction-onward part, fix up the single coaching block.
    bm = _BLOCK.search(post)
    if bm:
        head = post[: bm.start()]          # [Auction tag + call lines
        block, added = _ensure_show_s(bm.group())
        stats["show_added"] = added
        tail = post[bm.end():]             # may start with a stray '}' (the defect)
        cleaned_tail = re.sub(r"^[ \t}]*\n?", "", tail)
        if cleaned_tail != re.sub(r"^[ \t]*\n?", "", tail):
            stats["brace_fixed"] = True
        post = head + block + ("\n" + cleaned_tail if cleaned_tail else "")

    text = _renumber(pre + post, seq, stats)
    text = _fold_partner_bids(text, stats)
    text = _anchor_ending_pass(text, stats)
    text = _break_block_anchors(text, stats)
    # [ACCEPT ...] is left intact: bridge-classroom now consumes it (scores the
    # alternate call correct). nonrotate.py already drops it everywhere except the
    # student's own bid chunks, so what reaches here is exactly what BC should see.
    return text, stats


def _contract_disp(call):
    """Render an auction bid for prose: 6C -> 6\\C, 3N -> 3NT."""
    c = call.upper()
    strain = c[1:]
    return c[0] + ("NT" if strain in ("N", "NT") else "\\" + strain)


def _anchor_ending_pass(text, stats, student="S"):
    """Anchor the student's auction-ending Pass so the renderer prompts it.

    bridge-classroom auto-plays any unanchored call, so without this the student
    never gets a turn to confirm the final contract — they just spectate after
    their last bid. If the student's **last** call is a Pass, insert a
    `[BID Pass]` chunk (before the reflective `[show …]`) naming the contract.

    Only on boards that already quiz bidding (have a `[BID]`); play boards (no
    `[BID]`) are left alone. Idempotent — skipped if a `[BID Pass]` already
    exists. (The fold step never strips a `[BID Pass]`, so it survives re-runs.)
    """
    am = re.search(r'(?m)^\[Auction "([^"]*)"\]$', text)
    if not am or am.group(1) not in "NESW":
        return text
    order = _seat_order(am.group(1))

    tokens = _auction_call_tokens(text, am.end())
    student_idxs = [i for i in range(len(tokens)) if order[i % 4] == student]
    if not student_idxs or tokens[student_idxs[-1]].lower() != "pass":
        return text  # student has no calls, or their last call isn't a Pass

    bm = _BLOCK.search(text, am.end())
    if bm is None:
        return text
    inner = bm.group()[1:-1]
    if not re.search(r"\[BID\b", inner, re.IGNORECASE):
        return text  # not a bidding-quiz board (e.g. play board) — leave alone
    if re.search(r"\[BID\s+pass\b", inner, re.IGNORECASE):
        return text  # already anchored

    contract = next((t for t in reversed(tokens)
                     if t.upper() not in ("PASS", "X", "XX")), None)
    if contract and re.fullmatch(r"[1-7][CDHSNcdhsn]+", contract):
        prose = (f"You have nothing more to show, so pass — "
                 f"{_contract_disp(contract)} is the final contract.")
    else:
        prose = "You have nothing more to show, so pass and let the auction end."

    reveals = [m for m in re.finditer(r"\[show\b[^\]]*\]", inner, re.IGNORECASE)
               if m.start() != 0]
    pos = reveals[-1].start() if reveals else len(inner)
    new_inner = (inner[:pos].rstrip() + "\n[BID Pass] " + prose + "\n"
                 + inner[pos:].lstrip("\n"))
    stats["pass_added"] = True
    return text[: bm.start()] + "{" + new_inner + "}" + text[bm.end():]


# Chunk-start markers: each begins its own coaching chunk and should sit on its
# own line. [ACCEPT ...] is a mid-chunk modifier, not an anchor — left inline.
_ANCHOR = re.compile(
    r"\[(?:BID|show|POST-AUCTION|ROLE)\b[^\]]*\](?:\[STAGE\b[^\]]*\])?",
    re.IGNORECASE,
)

def _break_block_anchors(text, stats):
    """Put each coaching anchor on its own line.

    Inserts a newline before any anchor that is currently inline (text on the
    same line before it). Anchors already at line start are left as-is, so
    existing blank-line spacing (e.g. between play `[ROLE][STAGE]` chunks) is
    preserved. The block-opening anchor stays glued to ``{``.
    """
    am = re.search(r"(?m)^\[Auction\b.*$", text)
    if am is None:
        return text
    bm = _BLOCK.search(text, am.end())
    if bm is None:
        return text
    inner = bm.group()[1:-1]

    parts = re.split(f"({_ANCHOR.pattern})", inner, flags=re.IGNORECASE)
    out = parts[0]
    changed = False
    i = 1
    while i < len(parts):
        marker = parts[i]
        after = parts[i + 1] if i + 1 < len(parts) else ""
        if i == 1 and not parts[0].strip():
            out += marker                     # opening anchor — keep glued to {
        elif re.search(r"\n[ \t]*$", out):
            out += marker                     # already at line start — leave spacing
        else:
            out = out.rstrip(" \t") + "\n" + marker   # inline — break onto its own line
            changed = True
        out += after
        i += 2

    if not changed:
        return text
    stats["reflowed"] = True
    return text[: bm.start()] + "{" + out + "}" + text[bm.end():]


_BID_TAG = re.compile(r"\[BID\s+([^\]]+)\]", re.IGNORECASE)
# A real auction call (everything else in an auction line — e.g. PBN note refs
# like `=1=` — is an annotation that must NOT occupy a bidding position, or it
# shifts seat parity for every later call).
_CALL = re.compile(r"^(?:[1-7](?:NT|[CDHSN])|Pass|X|XX)$", re.IGNORECASE)


def _auction_call_tokens(text, after_pos):
    """Real calls in auction order, dropping PBN annotations (`=1=`, …)."""
    raw = []
    for line in text[after_pos:].splitlines():
        s = line.strip()
        if s.startswith("[") or s.startswith("{"):
            break
        raw.extend(line.split())
    return [t for t in raw if _CALL.match(t)]


def _seat_order(dealer):
    s = ["N", "E", "S", "W"]
    i = s.index(dealer)
    return s[i:] + s[:i]


def _norm_call(c):
    c = c.upper().strip()
    for nt in ("1NT", "2NT", "3NT", "4NT", "5NT", "6NT", "7NT"):
        c = c.replace(nt, nt[:-1])  # 1NT -> 1N
    return c


def _fold_partner_bids(text, stats, student="S"):
    """Keep `[BID]` anchors only for the student's own calls.

    bridge-classroom's renderer assumes every `[BID]` step is a student call:
    it auto-plays the auction until a student-seat call matches the *next*
    `[BID]`'s bid, so a `[BID]` on a partner/opponent call makes it skip past —
    and auto-play — the student's own later calls. So for each `[BID]` whose
    auction call belongs to a non-student seat, drop the marker and fold its
    prose into the preceding student chunk (the Basic_Major board-1 model).

    Each `[BID]` is mapped to a call the way the renderers anchor: walk the
    auction left-to-right and consume the next call whose value matches the
    `[BID]`'s bid. This handles boards where only some calls are anchored.

    Guards (leave the `[BID]` in place, counted separately, rather than risk a
    wrong edit): a value that matches no remaining call (`fold_unmatched`), or a
    non-student `[BID]` with no preceding student `[BID]` yet (`fold_flagged`).
    """
    am = re.search(r'(?m)^\[Auction "([^"]*)"\]$', text)
    if not am or am.group(1) not in "NESW":
        return text
    order = _seat_order(am.group(1))

    tokens = _auction_call_tokens(text, am.end())
    callvals = [_norm_call(t) for t in tokens]
    callseats = [order[i % 4] for i in range(len(tokens))]

    bm = _BLOCK.search(text, am.end())
    if not bm:
        return text
    parts = re.split(r"(\[BID\s+[^\]]+\])", bm.group()[1:-1])

    out = parts[0]
    kept_student = False
    p = 0          # auction cursor for value-based matching
    i = 1
    while i < len(parts):
        tag, txt = parts[i], parts[i + 1] if i + 1 < len(parts) else ""
        val = _norm_call(_BID_TAG.match(tag).group(1))
        if val == "PASS":
            # An anchored Pass is always the student's own (partner/opponent
            # passes are never anchored), so always keep it — but the cursor MUST
            # advance past that pass. Intermediate student passes are anchored
            # too, and leaving `p` behind one makes the NEXT anchor re-match a
            # call that precedes it, mis-seat it as an opponent's, and fold the
            # student's own later call away.
            j = p
            while j < len(callvals) and not (
                    callvals[j] == "PASS" and callseats[j] == student):
                j += 1
            if j < len(callvals):
                p = j + 1
            out += tag + txt
            kept_student = True
            i += 2
            continue
        j = p
        while j < len(callvals) and callvals[j] != val:
            j += 1
        seat = callseats[j] if j < len(callvals) else None
        if seat is not None:
            p = j + 1
        if seat == student:
            out += tag + txt
            kept_student = True
        elif seat is not None and kept_student:
            merged = txt.lstrip()
            out = (out.rstrip() + " " + merged) if merged else out + txt
            stats["folded"] += 1
        else:
            out += tag + txt          # unmatched, or no preceding student chunk
            stats["fold_unmatched" if seat is None else "fold_flagged"] += 1
        i += 2

    return text[: bm.start()] + "{" + out + "}" + text[bm.end():]


def _ensure_show_s(block):
    """Prepend ``[show S]`` to a coaching block unless it already leads with a
    ``[show ...]`` directive."""
    after = block[1:]
    if after.lstrip().lower().startswith("[show"):
        return block, False
    return "{[show S]" + block[1:], True


def _renumber(text, seq, stats):
    """Renumber ``[Board]`` to ``seq`` and insert ``[OriginalBoard]`` if absent."""
    bm = re.search(r'(?m)^\[Board "([^"]*)"\]', text)
    if bm is None:
        return text
    orig = bm.group(1)
    text = text[: bm.start()] + f'[Board "{seq}"]' + text[bm.end():]
    if not re.search(r"(?m)^\[OriginalBoard ", text):
        bm = re.search(r'(?m)^\[Board "[^"]*"\]', text)
        text = text[: bm.end()] + f'\n[OriginalBoard "{orig}"]' + text[bm.end():]
        stats["orig_added"] = True
    return text


def transform_file(path, check):
    text = path.read_text()
    boards = split_boards(text)

    new_boards = []
    totals = {"stripped": 0, "show_added": 0, "orig_added": 0, "brace_fixed": 0,
              "folded": 0, "fold_flagged": 0, "fold_unmatched": 0, "reflowed": 0,
              "pass_added": 0}
    for seq, board in enumerate(boards, start=1):
        new_board, stats = transform_board(board, seq)
        new_boards.append(new_board)
        for k in totals:
            totals[k] += int(stats[k])

    out_text = "\n\n".join(b.rstrip("\n") for b in new_boards) + "\n"
    changed = out_text != text
    if changed and not check:
        path.write_text(out_text)
    # Declarer-play lessons need a recorded [Play] line so bridge-classroom can
    # play the hand out (it has no local double-dummy solver). Regenerate it here
    # as the final serve step — idempotent — so a re-serve never leaves a board
    # with coaching but no play data. Only declarer-play scenarios pay the DD cost.
    if not check and "[ROLE declarer]" in out_text:
        play_line.process(path.stem, check=False)
    return changed, len(boards), totals


def resolve_targets(names):
    if not names:
        return sorted(COACHING_DIR.glob("*.pbn"))
    targets = []
    for n in names:
        p = COACHING_DIR / (n if n.endswith(".pbn") else f"{n}.pbn")
        if not p.exists():
            sys.exit(f"error: {p} not found")
        targets.append(p)
    return targets


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenarios", nargs="*",
                    help="scenario name(s) under coaching-non-rotated/ (default: all)")
    ap.add_argument("--check", action="store_true",
                    help="report what would change without writing")
    args = ap.parse_args()

    any_changed = False
    for path in resolve_targets(args.scenarios):
        changed, n_boards, t = transform_file(path, args.check)
        any_changed = any_changed or changed
        verb = "would update" if (changed and args.check) else \
               ("updated" if changed else "ok")
        extra = ""
        if t["brace_fixed"]:
            extra += f", {t['brace_fixed']} stray-brace fixed"
        if t["folded"]:
            extra += f", {t['folded']} partner-[BID] folded"
        if t["fold_flagged"]:
            extra += f", {t['fold_flagged']} FLAGGED (non-student [BID], no preceding student chunk)"
        if t["fold_unmatched"]:
            extra += f", {t['fold_unmatched']} FLAGGED ([BID] matches no auction call)"
        if t["pass_added"]:
            extra += f", {t['pass_added']} ending-pass anchored"
        if t["reflowed"]:
            extra += f", {t['reflowed']} boards reflowed"
        detail = (f"  ({t['stripped']} blocks stripped, "
                  f"{t['orig_added']} OriginalBoard added, "
                  f"{t['show_added']} show-S added{extra})") if changed else ""
        print(f"{verb:>12}  {path.name}  [{n_boards} boards]{detail}")

    if args.check and any_changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
