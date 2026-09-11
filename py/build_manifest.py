#!/usr/bin/env python3
"""
build_manifest.py — Generate the BBO / Bridge-Classroom deal-source manifest(s).

Motivation (PBS issue #167): the BBO browser extension and the Bridge-Classroom
deal-source dialog used to build their scenario menu by fetching the layout
file and then one `.pbs` file per button (~300 requests) plus GitHub-API listing
calls for the orphan diagnostics — roughly 400 hits every time a menu was
built. This script pre-computes a single JSON manifest per tier so a consumer
makes ONE request instead. On a click, the consumer fetches dlr/<name>.dlr.

Each manifest folds together everything the menu needs:
  * the button LAYOUT (majors, action buttons, sections, button rows with
    grouping / color / width, separators) — the menu structure;
  * per-scenario metadata (button text, chat/tooltip, alias, gib-works,
    bba-works, convention cards);
  * the MISSING / ORPHAN deltas the extension computes at runtime today.

Tiers (the BBO extension's Use_Beta_Layout toggle picks one):

  release : -button-layout-release.txt  +  dlr/
  beta    : -button-layout-beta.txt     +  dlr/

The `test` and `release-test` tiers, which added pbs-test/ scenarios, went with
pbs-test/ (issue #321). The extension falls back from them to beta / release.

Pure stdlib so it runs unchanged in GitHub Actions (ubuntu) and on the Mac.
Layout / btn parsing lineage: build-scripts-mac/build_pbs_from_layout.py.

Usage:
    python3 py/build_manifest.py                 # all tiers -> manifest/
    python3 py/build_manifest.py --tier release
    python3 py/build_manifest.py --out-dir manifest --check
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter

# The manifest build runs under `python3 -P` / PYTHONSAFEPATH=1 (see the workflow
# and py/select.py stdlib-shadow note), which drops this script's own directory
# from sys.path — so re-add it explicitly for the sibling import below.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from board_version_token import board_version_token, normalize_calls  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "build-scripts-mac"))
from bbo_dealer import parse_dlr_file  # noqa: E402

SCHEMA_VERSION = 2

# Repo root = parent of this file's directory (py/).
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BTN_DIR = os.path.join(ROOT, "btn")
DLR_DIR = os.path.join(ROOT, "dlr")
# Bridge-Classroom-served coaching collection: source of the v2 `lessons` roster
# (producer contract R5). One .pbn per lesson; key = PBN basename.
COACHING_DIR = os.path.join(ROOT, "coaching-non-rotated")

# tier -> layout filename
TIERS = {
    "release": "-button-layout-release.txt",
    "beta":    "-button-layout-beta.txt",
}


# --------------------------------------------------------------------------- #
# .btn metadata
# --------------------------------------------------------------------------- #
def parse_btn_metadata(btn_path):
    """Header (`# key: value`) + /*@chat ... @chat*/ block from a .btn file."""
    meta = {
        "alias": None,
        "buttonText": None,
        "gibWorks": None,
        "bbaWorks": None,
        "conventionCardNS": None,
        "conventionCardEW": None,
        "chat": None,
    }
    chat_lines = []
    in_chat = False
    with open(btn_path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = raw.rstrip("\n")
            stripped = line.strip()
            if in_chat:
                if stripped == "@chat*/" or stripped.endswith("@chat*/"):
                    in_chat = False
                    continue
                chat_lines.append(line)
                continue
            if stripped.startswith("/*@chat"):
                in_chat = True
                continue
            if stripped.startswith("#"):
                if stripped.startswith("# alias:"):
                    meta["alias"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("# button-text:"):
                    meta["buttonText"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("# gib-works:"):
                    meta["gibWorks"] = stripped.split(":", 1)[1].strip().lower() == "true"
                elif stripped.startswith("# bba-works:"):
                    meta["bbaWorks"] = stripped.split(":", 1)[1].strip().lower() == "true"
                elif stripped.startswith("# convention-card-ns:"):
                    meta["conventionCardNS"] = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("# convention-card-ew:"):
                    meta["conventionCardEW"] = stripped.split(":", 1)[1].strip()
    if chat_lines:
        meta["chat"] = "\n".join(chat_lines).strip("\n")
    return meta


def load_all_btn_metadata():
    out = {}
    if not os.path.isdir(BTN_DIR):
        return out
    for fn in os.listdir(BTN_DIR):
        if fn.endswith(".btn") and not fn.startswith("-"):
            out[fn[:-4]] = parse_btn_metadata(os.path.join(BTN_DIR, fn))
    return out


# --------------------------------------------------------------------------- #
# .dlr header (source of the on-screen text + chat the menu renders)
# --------------------------------------------------------------------------- #
def parse_dlr_button(dlr_path):
    """Return {'buttonText','chat','alias'} from a .dlr header.

    Chat comes out in the form the BBO extension renders: literal `\\n` tokens
    for line breaks, and wide commas, because the .pbs Button record it used to
    come from separated its fields with commas. The extension's dealerFromDlr
    produces the same string.
    """
    with open(dlr_path, "r", encoding="utf-8") as fh:
        parsed = parse_dlr_file(fh.read())
    chat = parsed["chat"]
    if chat:
        chat = "\\n" + "\\n".join(chat.replace(", ", "，").split("\n")) + "\\n"
    alias = parsed["alias"] or "Unknown"
    return {
        "buttonText": parsed["button_text"] or alias,
        "chat": chat,
        "alias": alias,
    }


# --------------------------------------------------------------------------- #
# layout parsing (adapted from build_pbs_from_layout.py)
# --------------------------------------------------------------------------- #
def _parse_button_item(item):
    """'file', 'file:blue', 'file:38%', 'file:blue:12%' -> dict."""
    item = item.strip()
    bits = item.split(":")
    name = bits[0]
    color = None
    width = None
    for b in bits[1:]:
        if b.endswith("%"):
            width = b
        else:
            color = b
    return {"name": name, "color": color, "width": width}


def _parse_button_row(line):
    """Parse a button-row line into a list of button dicts (grouping aware)."""
    parts = []
    cur = ""
    depth = 0
    for ch in line:
        if ch == "(":
            depth += 1
            cur += ch
        elif ch == ")":
            depth -= 1
            cur += ch
        elif ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())

    buttons = []
    for part in parts:
        if part.startswith("(") and part.endswith(")"):
            group = [s.strip() for s in part[1:-1].split(",")]
            n = len(group)
            base = 50 // n
            rem = 50 % n
            for i, item in enumerate(group):
                b = _parse_button_item(item)
                b["width"] = f"{base + (1 if i >= n - rem else 0)}%"
                b["grouped"] = True
                buttons.append(b)
        else:
            b = _parse_button_item(part)
            b["grouped"] = False
            buttons.append(b)

    non_grouped = [b for b in buttons if not b["grouped"]]
    grouped = [b for b in buttons if b["grouped"]]
    if len(non_grouped) == 1 and not grouped:
        non_grouped[0]["width"] = non_grouped[0]["width"] or "100%"
    elif len(non_grouped) == 2 and not grouped:
        for b in non_grouped:
            b["width"] = b["width"] or "50%"
    elif len(non_grouped) == 1 and grouped:
        non_grouped[0]["width"] = non_grouped[0]["width"] or "50%"
    return buttons


def parse_layout(layout_path):
    """Return (layout_items, referenced_names).

    layout_items is the ordered menu tree; referenced_names is the list of every
    scenario filename the layout points at (order-preserving, de-duped).
    """
    items = []
    referenced = []
    seen = set()
    with open(layout_path, "r", encoding="utf-8") as fh:
        for raw in fh:
            stripped = raw.strip()
            if not stripped:
                items.append({"type": "empty"})
                continue
            if stripped.startswith("#"):
                continue
            if stripped.startswith("[Major]"):
                content = stripped[len("[Major]"):].strip()
                title, url = (content.split("|", 1) + [None])[:2]
                items.append({"type": "major", "title": title.strip(),
                              **({"url": url.strip()} if url else {})})
            elif stripped.startswith("[Section]"):
                content = stripped[len("[Section]"):].strip()
                title, url = (content.split("|", 1) + [None])[:2]
                items.append({"type": "section", "title": title.strip(),
                              **({"url": url.strip()} if url else {})})
            elif stripped.startswith("[Action]"):
                content = stripped[len("[Action]"):].strip()
                p = content.split("|")
                items.append({
                    "type": "action",
                    "text": p[0].strip(),
                    "script": p[1].strip() if len(p) > 1 else "",
                    "width": p[2].strip() if len(p) > 2 else "50",
                })
            elif stripped == "---":
                items.append({"type": "separator"})
            else:
                buttons = _parse_button_row(stripped)
                clean = []
                for b in buttons:
                    if b["name"] == "---":
                        clean.append({"name": "---"})
                        continue
                    clean.append({
                        "name": b["name"],
                        "color": b["color"],
                        "width": b["width"],
                        "grouped": b["grouped"],
                    })
                    if b["name"] not in seen:
                        seen.add(b["name"])
                        referenced.append(b["name"])
                items.append({"type": "row", "buttons": clean})
    return items, referenced


# --------------------------------------------------------------------------- #
# lessons roster (schema v2 — producer contract R5)
#
# Authoritative per-board description of the Bridge-Classroom-served coaching
# collection. Keyed by PBN basename (= the deal_subfolder BC stores on
# observations). Each board carries number / stable / boardVersionToken /
# skillPath. Per contract §7 the collection id, `report` flag and `prerelease`
# column stay BC's — we do NOT emit them.
#
#   stable            : from `[Stable]` (board) over `%bridge-classroom-stable:`
#                       (file). ABSENT ⇒ false (prerelease) — the safe default.
#   boardVersionToken : R3 rotation-canonical hash, computed here from the
#                       extracted deal + auction (board_version_token.py). Boards
#                       do not yet carry the `[BoardVersionToken]` tag (the R3
#                       back-stamp build step is a separate follow-up); computing
#                       it in the manifest is equivalent and needs no file edits.
#   skillPath         : from `[SkillPath]`; `uncategorized` while prerelease (R4).
# --------------------------------------------------------------------------- #
def _parse_coaching_board(text):
    """One board chunk -> roster fields, or None if it isn't a board."""
    bnum = re.search(r'\[Board "(\d+)"\]', text)
    deal = re.search(r'\[Deal "([^"]+)"\]', text)
    if not bnum or not deal:
        return None
    skill = re.search(r'\[SkillPath "([^"]*)"\]', text)
    stable = re.search(r'\[Stable "([^"]*)"\]', text)
    am = re.search(r'\[Auction "([^"]*)"\]\n(.*?)(?=\n\[|\n\{|\Z)', text, re.S)
    if am:
        dealer, calls = am.group(1), normalize_calls(am.group(2).split())
    else:
        dm = re.search(r'\[Dealer "([^"]*)"\]', text)
        dealer, calls = (dm.group(1) if dm else ""), []
    return {
        "number": int(bnum.group(1)),
        "stable_tag": stable.group(1).strip().lower() if stable else None,
        "skillPath": skill.group(1) if skill else None,
        "deal": deal.group(1),
        "dealer": dealer,
        "calls": calls,
    }


def build_lessons():
    """Build the `lessons` roster from coaching-non-rotated/*.pbn."""
    lessons = {}
    if not os.path.isdir(COACHING_DIR):
        return lessons
    for fn in sorted(os.listdir(COACHING_DIR)):
        if not fn.endswith(".pbn"):
            continue
        with open(os.path.join(COACHING_DIR, fn), encoding="utf-8") as fh:
            raw = fh.read()
        header = raw.split("[Event", 1)[0]
        fm = re.search(r'%\s*bridge-classroom-stable:\s*(true|false)', header, re.I)
        file_stable = bool(fm) and fm.group(1).lower() == "true"

        boards = []
        for chunk in re.split(r'(?=\[Event )', raw):
            try:
                b = _parse_coaching_board(chunk)   # normalize_calls may raise
            except ValueError as e:
                bn = re.search(r'\[Board "(\d+)"\]', chunk)
                raise ValueError(f"{fn} board {bn.group(1) if bn else '?'}: {e}") from e
            if not b:
                continue
            stable = file_stable if b["stable_tag"] is None else (b["stable_tag"] == "true")
            try:
                token = board_version_token(b["deal"], b["dealer"], b["calls"])
            except ValueError:
                token = None  # malformed deal — surface as null rather than crash
            boards.append({
                "number": b["number"],
                "stable": stable,
                "boardVersionToken": token,
                "skillPath": b["skillPath"] or "uncategorized",
            })
        if not boards:
            continue
        # lesson-level default = most common board skillPath (positional tie-break).
        lesson_skill = Counter(x["skillPath"] for x in boards).most_common(1)[0][0]
        lessons[fn[:-4]] = {
            "skillPath": lesson_skill,
            "boardCount": len(boards),
            "stableBoardCount": sum(1 for x in boards if x["stable"]),
            "boards": boards,  # positional order (file order)
        }
    return lessons


# --------------------------------------------------------------------------- #
# manifest assembly
# --------------------------------------------------------------------------- #
def list_dlr():
    if not os.path.isdir(DLR_DIR):
        return {}
    return {fn[:-4]: os.path.join(DLR_DIR, fn)
            for fn in os.listdir(DLR_DIR) if fn.endswith(".dlr")}


def scenario_entry(name, btn_meta, dlr_button, missing):
    """Merge .btn metadata + .dlr header into one manifest scenario entry."""
    bm = btn_meta.get(name, {})
    text = (dlr_button or {}).get("buttonText") or bm.get("buttonText") or name
    chat = (dlr_button or {}).get("chat")
    if not chat:
        chat = bm.get("chat")
    alias = (dlr_button or {}).get("alias") or bm.get("alias") or name
    return {
        "buttonText": text,
        "chat": chat,
        "alias": alias,
        "gibWorks": bm.get("gibWorks"),
        "bbaWorks": bm.get("bbaWorks"),
        "conventionCardNS": bm.get("conventionCardNS"),
        "conventionCardEW": bm.get("conventionCardEW"),
        "missing": missing,
    }


def git_sha():
    sha = os.environ.get("GITHUB_SHA")
    if sha:
        return sha
    try:
        return subprocess.check_output(
            ["git", "-C", ROOT, "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return None


def build_tier(tier, btn_meta, lessons, dlr_index):
    layout_name = TIERS[tier]
    layout_path = os.path.join(BTN_DIR, layout_name)
    items, referenced = parse_layout(layout_path)

    scenarios = {}
    missing = []
    for name in referenced:
        dlr_path = dlr_index.get(name)
        button = parse_dlr_button(dlr_path) if dlr_path else None
        is_missing = dlr_path is None
        if is_missing:
            missing.append(name)
        scenarios[name] = scenario_entry(name, btn_meta, button, is_missing)

    # Orphans: a .dlr the layout doesn't reference.
    ref_set = set(referenced)
    orphans = sorted(n for n in dlr_index if n not in ref_set)

    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "tier": tier,
        "generatedAtCommit": git_sha(),
        "sources": {"layout": f"btn/{layout_name}", "dlr": "dlr"},
        "layout": items,
        "scenarios": scenarios,
        # v2 producer-contract R5 roster (tier-independent — coaching collection).
        "lessons": lessons,
        "deltas": {"missing": sorted(missing), "orphans": orphans},
        "counts": {
            "referenced": len(referenced),
            "scenarios": len(scenarios),
            "missing": len(missing),
            "orphans": len(orphans),
        },
    }

    return manifest


def main():
    ap = argparse.ArgumentParser(description="Build BBO/BC deal-source manifest(s).")
    ap.add_argument("--tier", choices=sorted(TIERS), help="only this tier (default: all)")
    ap.add_argument("--out-dir", default="manifest", help="output dir (default: manifest/)")
    ap.add_argument("--check", action="store_true",
                    help="build in memory and report; do not write files")
    args = ap.parse_args()

    btn_meta = load_all_btn_metadata()
    dlr_index = list_dlr()
    lessons = build_lessons()  # tier-independent; compute once, share across tiers
    tiers = [args.tier] if args.tier else sorted(TIERS)
    out_dir = os.path.join(ROOT, args.out_dir)
    if not args.check:
        os.makedirs(out_dir, exist_ok=True)

    lesson_boards = sum(l["boardCount"] for l in lessons.values())
    lesson_stable = sum(l["stableBoardCount"] for l in lessons.values())
    print(f"[lessons] {len(lessons)} lessons, {lesson_boards} boards "
          f"({lesson_stable} stable)")

    for tier in tiers:
        m = build_tier(tier, btn_meta, lessons, dlr_index)
        c = m["counts"]
        print(f"[{tier}] referenced={c['referenced']} "
              f"missing={c['missing']} orphans={c['orphans']}")
        if not args.check:
            path = os.path.join(out_dir, f"manifest-{tier}.json")
            # Preserve the prior generatedAtCommit when nothing else changed, so a
            # rebuild triggered by an unrelated input edit doesn't churn the file.
            # generatedAtCommit then means "commit where this content last changed",
            # and the CI commit-gate (git status --porcelain) skips no-op rebuilds
            # instead of committing a SHA-only diff every push.
            if os.path.exists(path):
                try:
                    with open(path, encoding="utf-8") as fh:
                        old = json.load(fh)
                    old_sha = old.pop("generatedAtCommit", None)
                    if old_sha is not None and old == {k: v for k, v in m.items()
                                                       if k != "generatedAtCommit"}:
                        m["generatedAtCommit"] = old_sha
                except Exception:
                    pass
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(m, fh, ensure_ascii=False, indent=2, sort_keys=False)
                fh.write("\n")
            print(f"       wrote {os.path.relpath(path, ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
