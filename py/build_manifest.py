#!/usr/bin/env python3
"""
build_manifest.py — Generate the BBO / Bridge-Classroom deal-source manifest(s).

Motivation (PBS issue #167): the BBO browser extension and the Bridge-Classroom
deal-source dialog currently build their scenario menu by fetching the layout
file and then one `.pbs` file per button (~300 requests) plus GitHub-API listing
calls for the test/orphan diagnostics — roughly 400 hits every time a menu is
built. This script pre-computes a single JSON manifest per tier so a consumer
makes ONE request instead.

Each manifest folds together everything the menu needs:
  * the button LAYOUT (majors, action buttons, sections, button rows with
    grouping / color / width, separators) — the menu structure;
  * per-scenario metadata (button text, chat/tooltip, alias, gib-works,
    bba-works, convention cards);
  * the MISSING / ORPHAN deltas the extension computes at runtime today.

Tiers (see also btn/-button-layout-{release,beta}.txt and the PBS Dynamic
Layout plugin's Use_Beta_Layout / Enable_Test_Mode toggles):

  release : -button-layout-release.txt  +  pbs-release/
  beta    : -button-layout-beta.txt     +  pbs-release/
  test    : -button-layout-beta.txt     +  pbs-release/ and pbs-test/
            (adds a testScenarios list for the [TEST: pbs-test/] section)
  release-test : -button-layout-release.txt + pbs-release/ and pbs-test/
            (the 4th toggle combination: release layout with test mode on)

The two extension toggles (Use_Beta_Layout, Enable_Test_Mode) are orthogonal —
these four tiers are the four combinations. See the TIERS table below.

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

SCHEMA_VERSION = 1

# Repo root = parent of this file's directory (py/).
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BTN_DIR = os.path.join(ROOT, "btn")

# tier -> (layout filename, list of pbs source dirs [primary first])
#
# The extension's two toggles are orthogonal, giving 4 combinations; each tier
# below is one of them (Use_Beta_Layout selects the layout file, Enable_Test_Mode
# adds pbs-test/ as an override source + a testScenarios list):
#
#   tier          | Use_Beta_Layout | Enable_Test_Mode | layout   | pbs sources
#   ------------- | --------------- | ---------------- | -------- | ----------------------
#   release       | false           | false            | release  | pbs-release
#   beta          | true            | false            | beta     | pbs-release
#   test          | true            | true             | beta     | pbs-release + pbs-test
#   release-test  | false           | true             | release  | pbs-release + pbs-test
TIERS = {
    "release":      ("-button-layout-release.txt", ["pbs-release"]),
    "beta":         ("-button-layout-beta.txt",    ["pbs-release"]),
    "test":         ("-button-layout-beta.txt",    ["pbs-release", "pbs-test"]),
    "release-test": ("-button-layout-release.txt", ["pbs-release", "pbs-test"]),
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
# .pbs Button line (source of the on-screen text + chat the menu renders today)
# --------------------------------------------------------------------------- #
_ALIAS_RE = re.compile(r"%([A-Za-z][A-Za-z0-9_]*)%")


def parse_pbs_button(pbs_path):
    """Return {'buttonText','chat','alias','style'} from a .pbs Button record.

    The record is multi-line, each continued physical line ending with `\\`
    (BBOalert line-continuation), terminated by a `%alias%` token, mirroring the
    extension's parsePbsButton. Returns None if there is no Button line.
    """
    with open(pbs_path, "r", encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("Button,"):
            start = i
            break
    if start is None:
        return None

    # First line: Button,<text>,<chat-fragment...>
    first = lines[start]
    parts = first.split(",", 2)
    button_text = parts[1] if len(parts) > 1 else ""
    frag = parts[2] if len(parts) > 2 else ""

    chat_pieces = []
    alias = None
    style = None

    def consume(fragment, is_first):
        """Append a fragment's chat, return True once %alias% terminator seen."""
        nonlocal alias, style
        m = _ALIAS_RE.search(fragment)
        if m:
            alias = m.group(1)
            chat_pieces.append(fragment[: m.start()].rstrip("\\"))
            style = fragment[m.end():].lstrip(",").strip()
            return True
        chat_pieces.append(fragment.rstrip("\\") if fragment.endswith("\\") else fragment)
        return False

    done = consume(frag, True)
    idx = start + 1
    while not done and idx < len(lines):
        done = consume(lines[idx], False)
        idx += 1

    chat = "".join(chat_pieces)
    return {
        "buttonText": button_text,
        "chat": chat,
        "alias": alias,
        "style": style or None,
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
# manifest assembly
# --------------------------------------------------------------------------- #
def list_pbs(dir_name):
    d = os.path.join(ROOT, dir_name)
    if not os.path.isdir(d):
        return {}
    return {fn[:-4]: os.path.join(d, fn)
            for fn in os.listdir(d) if fn.endswith(".pbs")}


def scenario_entry(name, btn_meta, pbs_button, missing):
    """Merge .btn metadata + .pbs Button line into one manifest scenario entry."""
    bm = btn_meta.get(name, {})
    text = (pbs_button or {}).get("buttonText") or bm.get("buttonText") or name
    chat = (pbs_button or {}).get("chat")
    if not chat:
        chat = bm.get("chat")
    alias = (pbs_button or {}).get("alias") or bm.get("alias") or name
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


def build_tier(tier, btn_meta):
    layout_name, pbs_dirs = TIERS[tier]
    layout_path = os.path.join(BTN_DIR, layout_name)
    items, referenced = parse_layout(layout_path)

    # Map filename -> .pbs path, primary dir first (pbs-test overrides release).
    pbs_index = {}
    per_dir = {}
    for d in pbs_dirs:
        per_dir[d] = list_pbs(d)
    for d in pbs_dirs:  # last dir wins so pbs-test overrides pbs-release
        pbs_index.update(per_dir[d])

    scenarios = {}
    missing = []
    for name in referenced:
        pbs_path = pbs_index.get(name)
        button = parse_pbs_button(pbs_path) if pbs_path else None
        is_missing = pbs_path is None
        if is_missing:
            missing.append(name)
        scenarios[name] = scenario_entry(name, btn_meta, button, is_missing)

    # Orphans: a .pbs in the primary (release) source not referenced by layout.
    ref_set = set(referenced)
    orphans = sorted(n for n in per_dir[pbs_dirs[0]] if n not in ref_set)

    manifest = {
        "schemaVersion": SCHEMA_VERSION,
        "tier": tier,
        "generatedAtCommit": git_sha(),
        "sources": {"layout": f"btn/{layout_name}", "pbs": pbs_dirs},
        "layout": items,
        "scenarios": scenarios,
        "deltas": {"missing": sorted(missing), "orphans": orphans},
        "counts": {
            "referenced": len(referenced),
            "scenarios": len(scenarios),
            "missing": len(missing),
            "orphans": len(orphans),
        },
    }

    # Any test-mode tier (pbs-test in its sources): expose the pbs-test-only
    # scenarios for the [TEST] section. Same output as before for `test`.
    if "pbs-test" in pbs_dirs:
        test_only = sorted(n for n in per_dir.get("pbs-test", {})
                           if n not in per_dir.get("pbs-release", {}))
        manifest["testScenarios"] = [
            scenario_entry(n, btn_meta,
                           parse_pbs_button(per_dir["pbs-test"][n]), False)
            | {"name": n}
            for n in test_only
        ]
        manifest["counts"]["testOnly"] = len(test_only)

    return manifest


def main():
    ap = argparse.ArgumentParser(description="Build BBO/BC deal-source manifest(s).")
    ap.add_argument("--tier", choices=sorted(TIERS), help="only this tier (default: all)")
    ap.add_argument("--out-dir", default="manifest", help="output dir (default: manifest/)")
    ap.add_argument("--check", action="store_true",
                    help="build in memory and report; do not write files")
    args = ap.parse_args()

    btn_meta = load_all_btn_metadata()
    tiers = [args.tier] if args.tier else sorted(TIERS)
    out_dir = os.path.join(ROOT, args.out_dir)
    if not args.check:
        os.makedirs(out_dir, exist_ok=True)

    for tier in tiers:
        m = build_tier(tier, btn_meta)
        c = m["counts"]
        print(f"[{tier}] referenced={c['referenced']} "
              f"missing={c['missing']} orphans={c['orphans']}"
              + (f" testOnly={c.get('testOnly')}" if "testOnly" in c else ""))
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
