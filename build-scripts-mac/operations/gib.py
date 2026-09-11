"""
GIB operations (issue #323): measure how well a scenario's dealer script
matches what BBO's GIB robots actually bid.

This is a report, not a second lesson pipeline - BBA stays the source of the
auctions everything downstream is built from.

  gib        capture robot auctions with py/gib_capture.py, then run gibReport
             dlr/{scenario}.dlr -> GIB/{scenario}.pbn
  gibReport  filter the capture by the scenario's auction-filter, and report
             GIB/{scenario}.pbn -> GIB-filtered/{scenario}.pbn + .pdf
                                -> GIB-filtered-out/{scenario}.pbn + .pdf
                                -> GIB-report/{scenario}.md
             and refresh GIB-report/-summary.md across every report
  bbo-demo   the gib table with the script loaded, left open for testing by
             hand (bid explanations and so on); captures and writes nothing

gibReport touches only local files, so it also works on the hand-collected
captures already in GIB/. None of these is in the default order: gib and
bbo-demo drive a live BBO account, so they run deliberately, one scenario at a
time.
"""
import os
import re
import subprocess
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FOLDERS, PROJECT_ROOT
from utils.properties import get_auction_filter
from operations.filter import bridge_wrangler_filter

CAPTURE_SCRIPT = os.path.join(PROJECT_ROOT, "py", "gib_capture.py")

# Failing sequences shown in full, and deals shown for each.
MAX_FAILING_SEQUENCES = 10
EXAMPLES_PER_SEQUENCE = 3


def capture_path(scenario: str) -> str:
    """GIB/{scenario}.pbn, or the extensionless name some hand captures use."""
    path = os.path.join(FOLDERS["gib"], f"{scenario}.pbn")
    bare = os.path.join(FOLDERS["gib"], scenario)
    if not os.path.exists(path) and os.path.isfile(bare):
        return bare
    return path


def run_gib(scenario: str, verbose: bool = True) -> bool:
    """Capture GIB auctions for a scenario (replacing any earlier capture), then report."""
    if verbose:
        print(f"--------- GIB capture for {scenario}")
    # --force: regenerating is this op's job, and the old capture is in git.
    sys.stdout.flush()
    result = subprocess.run([sys.executable, CAPTURE_SCRIPT, scenario, "--force"])
    if result.returncode != 0:
        print(f"Error: gib: capture failed for {scenario} (exit {result.returncode})")
        return False
    return run_gib_report(scenario, verbose)


def run_bbo_demo(scenario: str, verbose: bool = True) -> bool:
    """Open the gib table on live BBO with the scenario's script loaded, for a person."""
    if verbose:
        print(f"--------- BBO demo for {scenario}")
    sys.stdout.flush()
    result = subprocess.run([sys.executable, CAPTURE_SCRIPT, scenario, "--demo"])
    return result.returncode == 0


def split_boards(path: str) -> list:
    """PBN file -> list of board records (text)."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return [r.strip() for r in re.split(r"\n(?=\[Event )", text) if r.strip().startswith("[Event ")]


def auction_sequence(board: str) -> str:
    """A board's auction as oneSummary.py writes it: 1N-P-2C-P-2D, closing passes dropped."""
    m = re.search(r'^\[Auction "\w"\]\n(.*?)(?:\n\s*\n|\n\[|\n\{|\Z)', board + "\n", re.MULTILINE | re.DOTALL)
    if not m:
        return "(no auction)"
    calls = m.group(1).replace("Pass", "P").split()
    seq = "-".join(calls)
    return seq[:-len("-P-P-P")] if seq.endswith("-P-P-P") else seq


def robots(boards: list) -> str:
    names = Counter(re.findall(r'^\[South "([^"]*)"\]', "\n".join(boards), re.MULTILINE))
    return ", ".join(names) or "unknown"


def run_gib_report(scenario: str, verbose: bool = True) -> bool:
    """Filter GIB/{scenario}.pbn by the scenario's auction-filter and write the report."""
    if verbose:
        print(f"--------- GIB report for {scenario}")

    source = capture_path(scenario)
    if not os.path.exists(source):
        print(f"Error: gibReport: no GIB capture at {source} (run the gib operation first)")
        return False

    filter_expr = get_auction_filter(scenario)
    if not filter_expr:
        print(f"  {scenario} doesn't have a filter expression, skipping")
        return True
    if verbose:
        print(f"  Filter: {filter_expr}")

    matched_path = os.path.join(FOLDERS["gib_filtered"], f"{scenario}.pbn")
    unmatched_path = os.path.join(FOLDERS["gib_filtered_out"], f"{scenario}.pbn")
    if not bridge_wrangler_filter(source, filter_expr, matched_path, unmatched_path, verbose):
        return False

    matched = split_boards(matched_path)
    unmatched = split_boards(unmatched_path)
    total = len(matched) + len(unmatched)
    pct = 100 * len(matched) / total if total else 0.0

    os.makedirs(FOLDERS["gib_report"], exist_ok=True)
    report_path = os.path.join(FOLDERS["gib_report"], f"{scenario}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(_report(scenario, source, filter_expr, matched, unmatched, pct))
    if verbose:
        print(f"  Matched {len(matched)}/{total} ({pct:.1f}%)")
        print(f"  Created: {report_path}")

    _write_summary()
    return True


def _report(scenario, source, filter_expr, matched, unmatched, pct) -> str:
    rel = lambda p: os.path.relpath(p, PROJECT_ROOT)
    total = len(matched) + len(unmatched)
    lines = [
        f"# GIB report: {scenario}",
        "",
        f"Match: {len(matched)}/{total} = {pct:.1f}%",
        "",
        f"- Capture: `{rel(source)}` ({total} boards; robots: {robots(matched + unmatched)})",
        f"- Filter: `{filter_expr}`",
        f"- Matched: `GIB-filtered/{scenario}.pdf`",
        f"- Not matched: `GIB-filtered-out/{scenario}.pdf` (board numbers below are this file's)",
        "",
    ]
    if "Note" in filter_expr:
        lines += [
            "> **This filter anchors on BBA `Note` tags.** GIB captures have none, so it",
            "> matches nothing here and the percentage above means nothing. It needs an",
            "> auction-only form for GIB.",
            "",
        ]

    for title, boards in (("Not matched", unmatched), ("Matched", matched)):
        seqs = Counter(auction_sequence(b) for b in boards)
        lines += [f"## {title}: {len(boards)} boards, by sequence", "", "```"]
        lines += [f"{n:5}  {seq}" for seq, n in sorted(seqs.items(), key=lambda kv: (-kv[1], kv[0]))]
        lines += ["```", ""]

    by_seq = {}
    for b in unmatched:
        by_seq.setdefault(auction_sequence(b), []).append(b)
    failing = sorted(by_seq.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    if failing:
        lines += ["## Not matched: example deals", ""]
        for seq, boards in failing[:MAX_FAILING_SEQUENCES]:
            lines += [f"### {seq} ({len(boards)})", "", "```"]
            lines += ["\n\n".join(boards[:EXAMPLES_PER_SEQUENCE]), "```", ""]
        if len(failing) > MAX_FAILING_SEQUENCES:
            lines += [f"...and {len(failing) - MAX_FAILING_SEQUENCES} more sequences; "
                      f"see GIB-filtered-out/{scenario}.pdf", ""]
    return "\n".join(lines)


def _write_summary():
    """GIB-report/-summary.md: one row per report, read back from each report's Match line."""
    folder = FOLDERS["gib_report"]
    rows = []
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".md") or name.startswith("-"):
            continue
        with open(os.path.join(folder, name), encoding="utf-8") as f:
            text = f.read()
        m = re.search(r"^Match: (\d+)/(\d+) = ([\d.]+)%", text, re.MULTILINE)
        if m:
            note = "filter uses BBA Notes" if "anchors on BBA `Note` tags" in text else ""
            rows.append(f"| {name[:-3]} | {m.group(1)} | {m.group(2)} | {m.group(3)}% | {note} |")
    with open(os.path.join(folder, "-summary.md"), "w", encoding="utf-8") as f:
        f.write("# GIB match summary\n\nGenerated by the gibReport operation.\n\n"
                "| Scenario | Matched | Boards | Match | |\n|---|---:|---:|---:|---|\n")
        f.write("\n".join(rows) + "\n")
