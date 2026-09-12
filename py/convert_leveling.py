#!/usr/bin/env python3
"""
Convert a .btn scenario from the spot-card leveling ladder to dealer3's
generated leveling (issue #294).

Before:

    #include "script/Leveling"
    ...
    levLow  = nLow  and keep
    levMid  = nMid  and keep03
    levHigh = nHigh and keep25
    levelTheDeal = levLow or levMid or levHigh

After:

    HandType_Low  = nLow
    HandType_Mid  = nMid
    HandType_High = nHigh

    ### BEGIN GENERATED LEVELING ###
    noLeveling = 1
    levelTheDeal = noLeveling
    ### END GENERATED LEVELING ###

The `level` pipeline operation then has dealer3 measure each type and write
dlr-leveled/<name>.dlr with the keeps. See docs/leveling-guide.md in the
dealer3 repo.

Only mechanical conversions are made. The tool refuses (and says why) when
the verdict is not an `or` of hand types, a type uses more than one keep, a
ladder name is used anywhere else, and so on. It does not decide whether the
types overlap or leave a gap: dealer3 refuses those when it levels, and they
are questions about what the scenario teaches.

It does not touch the @chat text. A mix stated there (e.g. "Partscore 35%")
has to be replaced by hand with {{level-mix:TYPE}} tokens, and an uneven one
kept with HandType_TYPE_Share weights. The report lists chat lines that look
like they state a mix.

Usage (from the project root):

    python3 py/convert_leveling.py Drury            # report only
    python3 py/convert_leveling.py Drury --diff     # show the rewrite
    python3 py/convert_leveling.py Drury --write    # rewrite btn/Drury.btn
    python3 py/convert_leveling.py --all --json     # screen every ladder scenario
    python3 py/convert_leveling.py Drury --out DIR  # write DIR/Drury.btn and DIR/Drury.dlr

Two variants, both keeping exactly the set of deals the scenario produces:

    --narrow   also add `and (HandType_a or HandType_b ...)` to the condition.
               dealer3's fix for a gap: the old verdict was an `or` of the
               same types, so deals outside them were never dealt anyway.
    --unlevel  take out a ladder that levels nothing (every keep `keep` or
               `keep0`, or a verdict the condition no longer uses) instead of
               converting it.
"""
import argparse
import difflib
import json
import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BTN_DIR = os.path.join(PROJECT_ROOT, "btn")
LEVELING_SCRIPT = os.path.join(PROJECT_ROOT, "script", "Leveling")

INCLUDE_RE = re.compile(r'^\s*#include\s+"script/Leveling"\s*$')
# The ladder pasted in rather than included
INLINE_MARKERS = [
    ("### Imported Leveling Code ###", "### End of Imported Leveling Code ###"),
    ("# Imported Leveling Code", "# End of Imported Leveling Code"),
]
DEF_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
VERDICT_RE = re.compile(r"^\s*(levelTheDeal|keepTheDeal)\s*=\s*(.*)$")
NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

PLACEHOLDER = [
    "### BEGIN GENERATED LEVELING ###",
    "noLeveling = 1",
    "levelTheDeal = noLeveling",
    "### END GENERATED LEVELING ###",
]

# chat lines that look like they promise a mix
MIX_HINT_RE = re.compile(r"\d\s*%|level", re.IGNORECASE)


class Refused(Exception):
    pass


def strip_comment(s: str) -> str:
    for marker in ("//", "#"):
        i = s.find(marker)
        if i >= 0:
            s = s[:i]
    return s.strip()


def ladder_names_from(lines) -> set:
    names = set()
    for line in lines:
        m = DEF_RE.match(line)
        if m and not line.lstrip().startswith("#"):
            names.add(m.group(1))
    return names


def tokens(expr: str):
    """Split an expression into (, ), operator words and everything else."""
    expr = expr.replace("||", " or ").replace("&&", " and ")
    return re.findall(r"\(|\)|[^\s()]+", expr)


def split_top(expr: str, op: str):
    """Split expr at top-level `op` ("and" or "or"), respecting parentheses.
    Returns the parts as strings, or None if the parentheses don't balance."""
    parts, cur, depth = [], [], 0
    for tok in tokens(expr):
        if tok == "(":
            depth += 1
        elif tok == ")":
            depth -= 1
            if depth < 0:
                return None
        if depth == 0 and tok == op:
            parts.append(cur)
            cur = []
        else:
            cur.append(tok)
    if depth != 0:
        return None
    parts.append(cur)
    return [" ".join(p).replace("( ", "(").replace(" )", ")") for p in parts]


def unwrap(expr: str) -> str:
    """Drop parentheses that enclose the whole expression."""
    expr = expr.strip()
    while expr.startswith("(") and expr.endswith(")"):
        depth = 0
        for i, ch in enumerate(expr):
            depth += ch == "("
            depth -= ch == ")"
            if depth == 0 and i < len(expr) - 1:
                return expr
        expr = expr[1:-1].strip()
    return expr


def mentions(expr: str, names) -> list:
    return sorted({n for n in NAME_RE.findall(expr) if n in names})


def continues(lines, i) -> bool:
    """True if the statement on line i carries on to the next line."""
    this = strip_comment(lines[i])
    if re.search(r"(\band|\bor|&&|\|\||\()\s*$", this):
        return True
    for nxt in lines[i + 1:]:
        s = strip_comment(nxt)
        if not s:
            continue
        return bool(re.match(r"^(and|or|&&|\|\|)\b", s))
    return False


def make_label(term: str) -> str:
    """levLow -> Low, level12_14 -> 12_14, lC -> C, level_type_1 -> type_1,
    levnOC1 -> nOC1, lx4 -> x4."""
    for prefix in ("level", "lev", "l"):
        if term.startswith(prefix):
            rest = term[len(prefix):].lstrip("_")
            if not rest:
                continue
            if rest[0].isupper() or rest[0].isdigit() or term[len(prefix)] == "_":
                return rest
            if prefix == "lev" and term.startswith("level"):
                continue
            # levwkr -> wkr; but a bare `l` only when what is left still reads
            # as a name (lx4 -> x4, not lead -> ead)
            if prefix == "lev" and len(rest) > 1 or re.search(r"[A-Z0-9]", rest):
                return rest
    return term


def convert(text: str, narrow: bool = False, unlevel: bool = False):
    """Return (new_text, info). Raises Refused.

    narrow:  also add `and (HandType_a or HandType_b ...)` to the condition,
             dealer3's fix for a gap. The old verdict was an `or` of the same
             types, so this keeps exactly the deals the scenario produced.
    unlevel: instead of converting, take out a ladder that levels nothing --
             every keep `keep` or `keep0`, or a verdict the condition no longer
             uses -- keeping exactly the deals the scenario produces."""
    lines = text.split("\n")

    # --- where the ladder comes from
    ladder_lines = None
    remove = set()
    for i, line in enumerate(lines):
        if INCLUDE_RE.match(line):
            with open(LEVELING_SCRIPT, encoding="utf-8") as f:
                ladder_lines = f.read().split("\n")
            remove.add(i)
    if ladder_lines is None:
        for begin, end in INLINE_MARKERS:
            starts = [i for i, l in enumerate(lines) if l.strip() == begin]
            ends = [i for i, l in enumerate(lines) if l.strip() == end]
            if starts and ends and ends[0] > starts[0]:
                ladder_lines = lines[starts[0]:ends[0] + 1]
                remove.update(range(starts[0], ends[0] + 1))
                break
    if ladder_lines is None:
        raise Refused("no ladder: no #include \"script/Leveling\" and no pasted ladder")
    ladder = ladder_names_from(ladder_lines)
    # a commented-out include of the ladder goes with the ladder
    for i, line in enumerate(lines):
        if re.match(r'^\s*##+include\s+"script/Leveling"\s*$', line):
            remove.add(i)

    in_chat = set()
    inside = False
    for i, line in enumerate(lines):
        if "/*@chat" in line:
            inside = True
        if inside:
            in_chat.add(i)
        if "@chat*/" in line:
            inside = False

    # --- the verdict
    verdicts = [i for i, l in enumerate(lines)
                if i not in in_chat and i not in remove and VERDICT_RE.match(l)]
    if not verdicts:
        raise Refused("no levelTheDeal")
    if len(verdicts) > 1:
        raise Refused("levelTheDeal defined %d times" % len(verdicts))
    vi = verdicts[0]
    if continues(lines, vi):
        raise Refused("levelTheDeal runs over more than one line")
    vname = VERDICT_RE.match(lines[vi]).group(1)
    vexpr = strip_comment(VERDICT_RE.match(lines[vi]).group(2))

    # `a or b`, `(a or b)`, `x and (a or b)`
    prefix = None
    ands = split_top(vexpr, "and")
    if ands is None:
        raise Refused("levelTheDeal's parentheses don't balance: %r" % vexpr)
    if len(ands) == 2 and unwrap(ands[1]) != ands[1]:
        prefix, body = ands[0], unwrap(ands[1])
    else:
        body = unwrap(vexpr)
    if prefix and mentions(prefix, ladder):
        raise Refused("levelTheDeal's prefix uses the ladder: %r" % prefix)
    ors = split_top(body, "or")
    if ors is None:
        raise Refused("levelTheDeal's parentheses don't balance: %r" % vexpr)

    # --- each term: a name, or (name and keepNN)
    defs = {}          # name -> last line index defining it, before the verdict
    for i, line in enumerate(lines[:vi]):
        if i in in_chat or i in remove:
            continue
        m = DEF_RE.match(line)
        if m and not line.lstrip().startswith("#"):
            defs[m.group(1)] = i

    types = []         # dicts: term, label, cond_line, keep
    rewrite = {}       # line index -> new text
    consumed = {vi}
    for raw in ors:
        term_expr = unwrap(raw)
        parts = split_top(term_expr, "and")
        keeps = [p for p in parts if p in ladder]
        others = [p for p in parts if p not in ladder]
        if len(parts) > 1:
            # inline `(name and keepNN)` in the verdict itself
            if len(keeps) != 1 or len(others) != 1 or not NAME_RE.fullmatch(others[0]):
                raise Refused("verdict term is not a name or (name and keep): %r" % raw)
            name, keep = others[0], keeps[0]
            if mentions(name, ladder):
                raise Refused("verdict term uses the ladder: %r" % raw)
            types.append({"term": name, "keep": keep, "line": None})
            continue
        name = term_expr
        if not NAME_RE.fullmatch(name):
            raise Refused("verdict term is not a plain name: %r" % raw)
        if name in ladder:
            raise Refused("verdict keeps %s outright" % name)
        if name not in defs:
            raise Refused("term %s is never defined" % name)
        di = defs[name]
        if continues(lines, di):
            raise Refused("term %s runs over more than one line" % name)
        m = DEF_RE.match(lines[di])
        expr = strip_comment(m.group(2))
        tparts = split_top(expr, "and")
        if tparts is None:
            raise Refused("term %s's parentheses don't balance: %r" % (name, expr))
        if len(split_top(expr, "or")) > 1 and mentions(expr, ladder):
            # `a or b and keep25` keeps all of a: not `condition and keep`
            raise Refused("term %s is not `condition and keep`: %r" % (name, expr))
        tkeeps = [p for p in tparts if p in ladder]
        tconds = [p for p in tparts if p not in ladder]
        if len(tkeeps) > 1:
            raise Refused("term %s uses %d keeps" % (name, len(tkeeps)))
        if any(mentions(p, ladder) for p in tconds):
            raise Refused("term %s uses the ladder inside its condition: %r" % (name, expr))
        if not tconds:
            raise Refused("term %s has no condition, only a keep" % name)
        cond = " and ".join(tconds)
        types.append({"term": name, "keep": tkeeps[0] if tkeeps else None,
                      "line": di, "cond": cond})
        consumed.add(di)

    if len(types) < 2 and not unlevel:
        raise Refused("only %d hand type" % len(types))

    # --- nothing else may use the ladder
    for i, line in enumerate(lines):
        if i in consumed or i in remove or i in in_chat:
            continue
        code = strip_comment(line)
        if code.startswith("include") or line.lstrip().startswith("#"):
            continue
        used = mentions(code, ladder)
        if used:
            raise Refused("ladder name %s used outside the level lines: %r"
                          % (", ".join(used), line.strip()))

    zero = [t["term"] for t in types if t["keep"] == "keep0"]
    if zero and not unlevel:
        raise Refused("term(s) %s are kept never (keep0); needs a _Share of 0 decided by hand"
                      % ", ".join(zero))

    # --- the condition must use the verdict
    code_after = [strip_comment(l) for i, l in enumerate(lines) if i > vi and i not in in_chat]
    verdict_used = any(re.search(r"\b%s\b" % vname, c) for c in code_after)
    if not verdict_used and not unlevel:
        raise Refused("%s is defined but nothing after it uses it" % vname)
    if unlevel and verdict_used:
        real = ["%s (%s)" % (t["term"], t["keep"]) for t in types
                if t["keep"] not in (None, "keep", "keep0")]
        if real:
            raise Refused("not a ladder that levels nothing: %s" % ", ".join(real))

    # --- labels
    labels = {}
    for t in types:
        label = make_label(t["term"])
        if label.lower() in {l.lower() for l in labels.values()}:
            label = t["term"]
        labels[t["term"]] = label
        t["label"] = label

    # --- rewrite
    elsewhere = set()
    for i, line in enumerate(lines):
        if i in consumed or i in remove:
            continue
        code = line if i in in_chat else strip_comment(line)
        for t in types:
            if re.search(r"\b%s\b" % re.escape(t["term"]), code):
                elsewhere.add(t["term"])

    def trailing_comment(line):
        raw = DEF_RE.match(line).group(2)
        for marker in ("//", "#"):
            j = raw.find(marker)
            if j >= 0:
                return "  " + raw[j:].strip()
        return ""

    if unlevel:
        return unlevel_text(lines, remove, rewrite, types, elsewhere, vi, vname, prefix,
                            verdict_used, trailing_comment), {
            "types": [{"label": t["label"], "term": t["term"], "keep": t["keep"]} for t in types],
            "prefix": prefix, "chat_mix_lines": [], "verdict_used": verdict_used}

    handtype_lines = []
    for t in types:
        ht = "HandType_%s" % t["label"]
        line = lines[t["line"]] if t["line"] is not None else None
        if line is not None and not prefix and t["term"] not in elsewhere:
            # the term's own line becomes the hand type
            rewrite[t["line"]] = "%s = %s%s" % (ht, t["cond"], trailing_comment(line))
        else:
            if line is not None and t["keep"]:
                # keep the name, drop the keep
                m = DEF_RE.match(line)
                rewrite[t["line"]] = line[:m.start(2)] + t["cond"] + trailing_comment(line)
            body = "(%s) and %s" % (prefix, t["term"]) if prefix else t["term"]
            handtype_lines.append("%s = %s" % (ht, body))

    # A comment about leveling right above the include, heading nothing but
    # the include (a blank line follows it), goes with it
    for i in sorted(remove):
        j = i - 1
        if j >= 0 and j not in remove and re.match(r"^\s*#(?!include)", lines[j]) \
                and re.search(r"level", lines[j], re.IGNORECASE) \
                and (i + 1 >= len(lines) or not lines[i + 1].strip()):
            remove.add(j)

    out = []
    after_removal = False
    for i, line in enumerate(lines):
        if i in remove:
            after_removal = True
            continue
        if i == vi:
            if handtype_lines:
                out.extend(handtype_lines)
            if out and out[-1].strip():
                out.append("")
            out.extend(PLACEHOLDER)
            after_removal = False
            continue
        # a removal can leave two blank lines together; collapse only those
        if after_removal and not line.strip() and out and not out[-1].strip():
            continue
        after_removal = after_removal and not line.strip()
        out.append(rewrite.get(i, line))
    if narrow:
        clause = "(%s)" % " or ".join("HandType_%s" % t["label"] for t in types)
        end = out.index(PLACEHOLDER[-1])
        for j in range(end + 1, len(out)):
            if not out[j].lstrip().startswith("#") and \
                    re.search(r"\b%s\b" % vname, strip_comment(out[j])):
                out[j] = re.sub(r"\b%s\b" % vname, "%s and %s" % (clause, vname), out[j], count=1)
                break
        else:
            raise Refused("found no condition line using %s to narrow" % vname)
    new_text = "\n".join(out)
    if vname != "levelTheDeal":
        new_text = re.sub(r"\b%s\b" % vname, "levelTheDeal", new_text)

    chat_hints = [lines[i].strip() for i in sorted(in_chat)
                  if MIX_HINT_RE.search(lines[i]) and "@chat" not in lines[i]]
    info = {
        "types": [{"label": t["label"], "term": t["term"], "keep": t["keep"]} for t in types],
        "prefix": prefix,
        "chat_mix_lines": chat_hints,
    }
    return new_text, info


def unlevel_text(lines, remove, rewrite, types, elsewhere, vi, vname, prefix,
                 verdict_used, trailing_comment):
    """The scenario with a ladder that levels nothing taken out."""
    remove = set(remove)
    kept = []
    for t in types:
        line = lines[t["line"]] if t["line"] is not None else None
        drop_line = t["term"] not in elsewhere and (not verdict_used or t["keep"] == "keep0")
        if line is not None:
            if drop_line:
                remove.add(t["line"])
            elif t["keep"]:
                m = DEF_RE.match(line)
                rewrite[t["line"]] = line[:m.start(2)] + t["cond"] + trailing_comment(line)
        if t["keep"] != "keep0":
            kept.append(t["term"])
    if verdict_used:
        body = " or ".join(kept) if len(kept) > 1 else kept[0]
        if prefix:
            body = "%s and (%s)" % (prefix, body)
        rewrite[vi] = "%s = %s" % (vname, body)
    else:
        remove.add(vi)
        # the switched-off use goes too
        for i, line in enumerate(lines):
            if re.match(r"^\s*#+\s*(and\s+)?%s\s*$" % vname, line):
                remove.add(i)
    for i in sorted(remove):
        j = i - 1
        if j >= 0 and j not in remove and re.match(r"^\s*#(?!include)", lines[j]) \
                and re.search(r"level", lines[j], re.IGNORECASE) \
                and (i + 1 >= len(lines) or not lines[i + 1].strip() or i + 1 in remove):
            remove.add(j)
    out = []
    after_removal = False
    for i, line in enumerate(lines):
        if i in remove:
            after_removal = True
            continue
        if after_removal and not line.strip() and out and not out[-1].strip():
            continue
        after_removal = after_removal and not line.strip()
        out.append(rewrite.get(i, line))
    return "\n".join(out)


def ladder_scenarios():
    names = []
    for f in sorted(os.listdir(BTN_DIR)):
        if not f.endswith(".btn"):
            continue
        with open(os.path.join(BTN_DIR, f), encoding="utf-8") as fh:
            text = fh.read()
        if any(INCLUDE_RE.match(l) for l in text.split("\n")) or \
                any(b in text for b, _ in INLINE_MARKERS):
            names.append(f[:-4])
    return names


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("scenarios", nargs="*")
    ap.add_argument("--all", action="store_true", help="every btn that uses the ladder")
    ap.add_argument("--write", action="store_true", help="rewrite btn/<name>.btn in place")
    ap.add_argument("--diff", action="store_true", help="print a unified diff")
    ap.add_argument("--out", help="write <out>/<name>.btn and the dlr made from it")
    ap.add_argument("--json", action="store_true", help="one JSON line per scenario")
    ap.add_argument("--narrow", action="store_true",
                    help="also narrow the condition to the hand types (dealer3's fix for a gap)")
    ap.add_argument("--unlevel", action="store_true",
                    help="take out a ladder that levels nothing, keeping the deals the same")
    args = ap.parse_args()

    names = ladder_scenarios() if args.all else args.scenarios
    if not names:
        ap.error("name a scenario, or --all")

    failed = 0
    for name in names:
        path = os.path.join(BTN_DIR, name + ".btn")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        try:
            new_text, info = convert(text, narrow=args.narrow, unlevel=args.unlevel)
        except Refused as e:
            failed += 1
            if args.json:
                print(json.dumps({"scenario": name, "ok": False, "why": str(e)}))
            else:
                print("%s: not converted: %s" % (name, e))
            continue

        if args.json:
            print(json.dumps(dict({"scenario": name, "ok": True}, **info)))
        else:
            print("%s: %s" % (name, ", ".join(
                "%s (was %s)" % (t["label"], t["keep"] or "no keep") for t in info["types"])))
            for line in info["chat_mix_lines"]:
                print("    chat: %s" % line)
        if args.diff:
            sys.stdout.writelines(difflib.unified_diff(
                text.splitlines(True), new_text.splitlines(True),
                "btn/%s.btn" % name, "btn/%s.btn (converted)" % name))
        if args.out:
            os.makedirs(args.out, exist_ok=True)
            out_btn = os.path.join(args.out, name + ".btn")
            with open(out_btn, "w", encoding="utf-8") as f:
                f.write(new_text)
            sys.path.insert(0, os.path.join(PROJECT_ROOT, "build-scripts-mac"))
            from operations.dlr_from_btn import generate_dlr
            with open(os.path.join(args.out, name + ".dlr"), "w", encoding="utf-8") as f:
                f.write(generate_dlr(out_btn, name))
        if args.write:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_text)
    sys.exit(1 if failed and not args.all else 0)


if __name__ == "__main__":
    main()
