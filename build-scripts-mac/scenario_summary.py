#!/usr/bin/env python3
"""
Generate a Scenario Summary document (HTML) showing per-scenario
deal counts, filter counts, filter-out counts, and elapsed times.

Usage:
    python3 scenario_summary.py              # All scenarios
    python3 scenario_summary.py "1N*"        # Filter by pattern
"""
import fnmatch
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import FOLDERS, OPERATIONS_ORDER, PROJECT_ROOT
from utils.properties import get_bba_works, get_btn_property, get_chat_text

TIMING_FILE = os.path.join(PROJECT_ROOT, "build-data", "pipeline-timing.json")
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "docs", "Scenario_Summary.html")

# Columns for ET: operation names and their short display headers
OP_COLUMNS = [
    ("dlr", "dlr"),
    ("pbs", "pbs"),
    ("pbn", "pbn"),
    ("rotate", "rotate"),
    ("bba", "bba"),
    ("filter", "filter"),
    ("filterStats", "fStats"),
    ("biddingSheet", "bSheet"),
    ("quiz", "quiz"),
    ("package", "package"),
]


def count_boards(file_path: str) -> int:
    """Count [Board occurrences in a PBN file."""
    if not os.path.exists(file_path):
        return 0
    regex = re.compile(r"\[Board")
    count = 0
    with open(file_path, "r") as f:
        for line in f:
            if regex.search(line):
                count += 1
    return count


def get_scenarios(pattern: str) -> list:
    """Get scenario names from btn/ folder, sorted by button-text display name.
    Subordinate scenarios sort immediately after their parent."""
    btn_dir = FOLDERS["btn"]
    btn_files = [f[:-4] for f in os.listdir(btn_dir)
                 if f.endswith('.btn') and not f.startswith('.') and not f.startswith('-')]

    if pattern != "*":
        btn_files = [f for f in btn_files if fnmatch.fnmatch(f, pattern)]

    # Pre-compute button-text for sort keys
    btn_text = {}
    for name in btn_files:
        btn_text[name] = (get_btn_property(name, "button-text") or name.replace('_', ' ')).lower()

    def sort_key(name):
        if name.endswith('_Leveled'):
            base = name[:-len('_Leveled')]
            base_text = btn_text.get(base, base.replace('_', ' ').lower())
            if base in _CHILD_TO_PARENT:
                parent, idx = _CHILD_TO_PARENT[base]
                parent_text = btn_text.get(parent, parent.replace('_', ' ').lower())
                return parent_text + '\x00' + f'{idx:03d}' + '\x00Leveled'
            return base_text + '\x00Leveled'
        if name in _CHILD_TO_PARENT:
            parent, idx = _CHILD_TO_PARENT[name]
            parent_text = btn_text.get(parent, parent.replace('_', ' ').lower())
            return parent_text + '\x00' + f'{idx:03d}'
        return btn_text[name]

    return sorted(btn_files, key=sort_key)


def format_et(seconds: float) -> str:
    """Format elapsed time concisely."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m{secs:.0f}s"


def _esc(text: str) -> str:
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _esc_attr(text: str) -> str:
    """Escape text for use in an HTML attribute value."""
    return _esc(text).replace('"', "&quot;").replace("\n", "&#10;")


GITHUB_BTN_URL = "https://raw.githubusercontent.com/bridge-craftwork/Practice-Bidding-Scenarios/main/btn"


# Explicit parent→children indent groups
_INDENT_PARENTS = {
    "Rule_of_16": ["Rule_of_16-15", "Rule_of_16-16", "Rule_of_16-17", "Rule_of_16-18"],
    "Soloway_Jump_Shift": ["Soloway_Jump_Shift_Type-1", "Soloway_Jump_Shift_Type-2",
                           "Soloway_Jump_Shift_Type-3", "Soloway_Jump_Shift_Type-4"],
    "We_Overcall_1N": ["We_Overcall_1N_then_Gerber"],
    "We_Overcall_NT": ["We_Overcall_NT_then_Jacoby", "We_Overcall_NT_then_MSS",
                        "We_Overcall_NT_then_MST", "We_Overcall_NT_then_Smolen",
                        "We_Overcall_NT_then_Stayman", "We_Overcall_NT_then_Texas"],
    "Open_In_Fourth_Seat": ["Open_In_Fourth_13", "Open_In_Fourth_14",
                             "Open_In_Fourth_15", "Open_In_Fourth_16"],
    "Misfit6-5": ["Misfit_06-10", "Misfit_11-12", "Misfit_13-Plus"],
}
_INDENT_CHILDREN = {child for children in _INDENT_PARENTS.values() for child in children}

# Reverse lookup: child → (parent, index) for sort ordering
_CHILD_TO_PARENT = {}
for _parent, _children in _INDENT_PARENTS.items():
    for _i, _child in enumerate(_children):
        _CHILD_TO_PARENT[_child] = (_parent, _i)


def _is_subordinate(name: str) -> bool:
    """Return True if name is in the explicit indent children set or is a _Leveled variant."""
    if name in _INDENT_CHILDREN:
        return True
    if name.endswith('_Leveled'):
        return True
    return False


def _scenario_td(name: str, btn_info: dict, style: str = "",
                 indent: bool = False) -> str:
    """Build a <td> with button-text display and CSS hover tooltip."""
    display = _esc(btn_info.get("button_text") or name)
    url = f'{GITHUB_BTN_URL}/{name}.btn'
    github_link = f'<a href="{url}" onclick="window.open(\'{url}\');return false;" style="color:#8cf;text-decoration:none;">{name}.btn</a>'
    chat = btn_info.get("chat_text", "")
    chat_html = f"\n{_esc(chat)}" if chat else ""
    tooltip = f'{github_link}{chat_html}'
    pad = "padding-left:24px;" if indent else ""
    combined = f"{pad}{style}" if pad or style else ""
    style_attr = f' style="{combined}"' if combined else ""
    return f'<td{style_attr}><span class="has-tip">{display}<span class="tip">{tooltip}</span></span></td>'


def generate_summary(pattern: str = "*"):
    """Generate the Scenario_Summary.html file."""
    scenarios = get_scenarios(pattern)
    if not scenarios:
        print(f"No scenarios found matching: {pattern}")
        return

    # Load timing data
    timing = {}
    if os.path.exists(TIMING_FILE):
        with open(TIMING_FILE, "r") as f:
            timing = json.load(f)
    else:
        print(f"Note: No timing data found at {TIMING_FILE}")
        print("  Run the pipeline to generate timing data.")

    # Collect data for each scenario
    rows = []
    for scenario in scenarios:
        deals = count_boards(os.path.join(FOLDERS["pbn"], f"{scenario}.pbn"))
        filtered = count_boards(os.path.join(FOLDERS["bba_filtered"], f"{scenario}.pbn"))
        filtered_out = count_boards(os.path.join(FOLDERS["bba_filtered_out"], f"{scenario}.pbn"))

        et = timing.get(scenario, {})
        op_times = []
        op_seconds = []
        total_et = 0.0
        for op_name, _ in OP_COLUMNS:
            t = et.get(op_name)
            if t is not None:
                op_times.append(format_et(t))
                op_seconds.append(t)
                total_et += t
            else:
                op_times.append("-")
                op_seconds.append(0.0)

        rows.append({
            "name": scenario,
            "btn_info": {
                "button_text": get_btn_property(scenario, "button-text"),
                "chat_text": get_chat_text(scenario),
            },
            "deals": deals,
            "filtered": filtered,
            "filtered_out": filtered_out,
            "op_times": op_times,
            "op_seconds": op_seconds,
            "total_et": format_et(total_et) if total_et > 0 else "-",
        })

    # Build btn_info lookup for summary cards
    btn_lookup = {row["name"]: row["btn_info"] for row in rows}

    # Compute top-10 summaries
    filter_pcts = []
    for row in rows:
        if row["deals"] > 0 and get_bba_works(row["name"]):
            pct = (row["filtered"] / row["deals"]) * 100
            filter_pcts.append((row["name"], pct, row["filtered"], row["deals"]))
    filter_pcts.sort(key=lambda x: x[1])
    lowest_filter = filter_pcts[:10]

    deal_rows = [(row["name"], row["deals"]) for row in rows if 0 < row["deals"] < 500]
    deal_rows.sort(key=lambda x: x[1])
    lowest_deals = deal_rows[:10]

    # Newest scenarios by git first-commit date, with last-commit date
    newest_scenarios = []
    for row in rows:
        btn_rel = os.path.join("btn", f"{row['name']}.btn")
        btn_path = os.path.join(PROJECT_ROOT, btn_rel)
        if not os.path.exists(btn_path):
            continue
        try:
            # First commit (created)
            result = subprocess.run(
                ["git", "log", "--diff-filter=A", "--format=%at", "--", btn_rel],
                capture_output=True, text=True, cwd=PROJECT_ROOT)
            created = float(result.stdout.strip().split('\n')[-1]) if result.stdout.strip() else 0
            # Last commit (modified)
            result = subprocess.run(
                ["git", "log", "-1", "--format=%at", "--", btn_rel],
                capture_output=True, text=True, cwd=PROJECT_ROOT)
            modified = float(result.stdout.strip()) if result.stdout.strip() else 0
        except (ValueError, IndexError):
            continue
        if created > 0:
            newest_scenarios.append((row["name"], created, modified, row["deals"]))
    newest_scenarios.sort(key=lambda x: -x[2])  # Sort by modified date, not created
    newest_10 = newest_scenarios[:10]

    pipeline_ops = {op for op, _ in OP_COLUMNS}
    et_rows = []
    for row in rows:
        et = timing.get(row["name"], {})
        total = sum(v for k, v in et.items() if k in pipeline_ops)
        if total > 0:
            et_rows.append((row["name"], total))
    et_rows.sort(key=lambda x: -x[1])
    longest_et = et_rows[:10]

    # Build HTML
    h = []
    h.append('<!DOCTYPE html>')
    h.append('<html lang="en">')
    h.append('<head>')
    h.append('  <meta charset="UTF-8">')
    h.append('  <meta name="viewport" content="width=device-width, initial-scale=1.0">')
    h.append('  <title>Scenario Summary</title>')
    h.append('  <style>')
    h.append('    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;')
    h.append('           font-size: 13px; max-width: 1400px; margin: 30px auto; padding: 20px;')
    h.append('           background: #f5f5f5; color: #333; }')
    h.append('    h1 { color: #222; text-align: center; font-size: 22px; margin-bottom: 5px; }')
    h.append('    .subtitle { text-align: center; color: #666; margin-bottom: 25px; }')
    h.append('    .nav-btn { display: inline-block; padding: 6px 14px; background: #0077b6; color: #fff;')
    h.append('              border-radius: 4px; text-decoration: none; font-size: 12px; margin: 0 4px; }')
    h.append('    .nav-btn:hover { background: #005f8a; }')
    h.append('    .nav-btn-active { background: #333; pointer-events: none; }')
    h.append('    .summaries { display: flex; gap: 20px; margin-bottom: 25px; }')
    h.append('    .summary-card { background: #fff; border-radius: 8px; padding: 15px 20px;')
    h.append('                    box-shadow: 0 2px 4px rgba(0,0,0,0.08); flex: 1; }')
    h.append('    .summary-card h3 { margin: 0 0 10px 0; font-size: 14px; color: #333; }')
    h.append('    table { border-collapse: collapse; width: 100%; }')
    h.append('    .main-table { background: #fff; border-radius: 8px; padding: 15px;')
    h.append('                  box-shadow: 0 2px 4px rgba(0,0,0,0.08); overflow-x: auto; }')
    h.append('    th { background: #f0f0f0; font-weight: 600; text-align: right; padding: 6px 8px;')
    h.append('         border-bottom: 2px solid #ddd; font-size: 12px; white-space: nowrap; }')
    h.append('    th:first-child { text-align: left; }')
    h.append('    td { padding: 4px 8px; border-bottom: 1px solid #eee; text-align: right;')
    h.append('         font-size: 12px; white-space: nowrap; }')
    h.append('    td:first-child { text-align: left; }')
    h.append('    .main-table tr:hover td { background: #f8f8f8; cursor: pointer; }')
    h.append('    .main-table th { cursor: pointer; }')
    h.append('    .main-table th:first-child { cursor: default; }')
    h.append('    .main-table tr.highlighted td { background: #fff3cd !important; }')
    h.append('    .main-table .col-highlighted { background: #d0e8f7 !important; }')
    h.append('    .main-table tr.highlighted .col-highlighted { background: #d4e9c7 !important; }')
    h.append('    .totals td { font-weight: bold; border-top: 2px solid #ddd; text-align: center; }')
    h.append('    .summary-card td, .summary-card th { font-size: 12px; }')
    h.append('    .summary-card th { background: transparent; border-bottom: 1px solid #ddd; }')
    h.append('    .has-tip { position: relative; cursor: help; border-bottom: 1px dotted #999; }')
    h.append('    .has-tip .tip { display: none; position: absolute; left: 0; top: 100%;')
    h.append('                    background: #333; color: #fff; padding: 6px 10px; border-radius: 4px;')
    h.append('                    font-size: 11px; white-space: pre-line; z-index: 100;')
    h.append('                    min-width: 200px; max-width: 400px; box-shadow: 0 2px 8px rgba(0,0,0,0.3); }')
    h.append('    .has-tip:hover .tip { display: block; animation: fadeIn 0.2s ease-in 0.5s both; }')
    h.append('    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }')
    h.append('  </style>')
    h.append('</head>')
    h.append('<body>')
    h.append('  <h1>Scenario Summary</h1>')
    utc_ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    h.append(f'  <p class="subtitle">{len(rows)} scenarios &mdash; Generated <span id="gen-time" data-utc="{utc_ts}"></span>')
    h.append(f'    &mdash; <a class="nav-btn" href="./">Dashboard</a>')
    h.append(f'    <a class="nav-btn nav-btn-active" href="Scenario_Summary.html">Scenario Summary</a>')
    h.append(f'    <a class="nav-btn" href="Convention_Card_Summary.html">Convention Cards</a></p>')

    # Side-by-side summaries
    h.append('  <div class="summaries">')

    # Lowest Filter Rate
    h.append('    <div class="summary-card">')
    h.append('      <h3>Lowest Filter Rate</h3>')
    h.append('      <table>')
    h.append('        <tr><th>#</th><th style="text-align:left">Scenario</th><th>Filt</th><th>Deals</th><th>Rate</th></tr>')
    for i, (name, pct, filt, deals) in enumerate(lowest_filter, 1):
        h.append(f'        <tr><td>{i}</td>{_scenario_td(name, btn_lookup[name], "text-align:left")}<td>{filt}</td><td>{deals}</td><td>{pct:.1f}%</td></tr>')
    h.append('      </table>')
    h.append('    </div>')

    # Lowest Deal Counts
    h.append('    <div class="summary-card">')
    h.append('      <h3>Lowest Deal Counts</h3>')
    h.append('      <table>')
    h.append('        <tr><th>#</th><th style="text-align:left">Scenario</th><th>Deals</th></tr>')
    for i, (name, deals) in enumerate(lowest_deals, 1):
        h.append(f'        <tr><td>{i}</td>{_scenario_td(name, btn_lookup[name], "text-align:left")}<td>{deals}</td></tr>')
    h.append('      </table>')
    h.append('    </div>')

    # Newest Scenarios
    h.append('    <div class="summary-card">')
    h.append('      <h3>Recent Changes</h3>')
    h.append('      <table>')
    h.append('        <tr><th>#</th><th style="text-align:left">Scenario</th><th>Created</th><th>Modified</th></tr>')
    for i, (name, created, modified, deals) in enumerate(newest_10, 1):
        created_str = datetime.fromtimestamp(created).strftime('%Y-%m-%d')
        modified_str = datetime.fromtimestamp(modified).strftime('%Y-%m-%d')
        h.append(f'        <tr><td>{i}</td>{_scenario_td(name, btn_lookup[name], "text-align:left")}<td>{created_str}</td><td>{modified_str}</td></tr>')
    h.append('      </table>')
    h.append('    </div>')

    # Longest Total ET
    h.append('    <div class="summary-card">')
    h.append('      <h3>Longest Total ET</h3>')
    h.append('      <table>')
    if longest_et:
        h.append('        <tr><th>#</th><th style="text-align:left">Scenario</th><th>Total ET</th></tr>')
        for i, (name, total) in enumerate(longest_et, 1):
            h.append(f'        <tr><td>{i}</td>{_scenario_td(name, btn_lookup[name], "text-align:left")}<td>{format_et(total)}</td></tr>')
    else:
        h.append('        <tr><td><em>No timing data available.</em></td></tr>')
    h.append('      </table>')
    h.append('    </div>')

    h.append('  </div>')

    # Main table
    op_headers = [hdr for _, hdr in OP_COLUMNS]
    h.append('  <div class="main-table">')
    h.append('    <table>')
    h.append('      <tr>')
    h.append('        <th>Scenario</th><th>Deals</th><th>Filtered</th><th>Flt-Out</th>')
    for hdr in op_headers:
        h.append(f'        <th>{_esc(hdr)}</th>')
    h.append('        <th>Total</th>')
    h.append('      </tr>')

    # Compute totals before emitting rows
    total_deals = sum(row["deals"] for row in rows)
    total_filtered = sum(row["filtered"] for row in rows)
    total_filtered_out = sum(row["filtered_out"] for row in rows)
    col_totals = [sum(row["op_seconds"][i] for row in rows) for i in range(len(OP_COLUMNS))]
    grand_total = sum(col_totals)
    filt_pct_str = f'{total_filtered / total_deals * 100:.1f}%' if total_deals > 0 else '-'
    fout_pct_str = f'{total_filtered_out / total_deals * 100:.1f}%' if total_deals > 0 else '-'

    # Totals row (at top)
    h.append('      <tr class="totals">')
    h.append(f'        <td>Total</td><td>{total_deals}</td><td>{total_filtered}</td><td>{total_filtered_out}</td>')
    for ct in col_totals:
        h.append(f'        <td>{format_et(ct) if ct > 0 else "-"}</td>')
    h.append(f'        <td>{format_et(grand_total) if grand_total > 0 else "-"}</td>')
    h.append('      </tr>')
    # Percentage row
    h.append('      <tr class="totals">')
    h.append(f'        <td>%</td><td></td><td>{filt_pct_str}</td><td>{fout_pct_str}</td>')
    for ct in col_totals:
        pct = (ct / grand_total * 100) if grand_total > 0 else 0
        h.append(f'        <td>{pct:.1f}%</td>' if ct > 0 else '        <td>-</td>')
    h.append('        <td>100%</td>')
    h.append('      </tr>')

    # Data rows
    for row in rows:
        deals_str = str(row["deals"]) if row["deals"] > 0 else "-"
        filt_str = str(row["filtered"]) if row["filtered"] > 0 else "-"
        fout_str = str(row["filtered_out"]) if row["filtered_out"] > 0 else "-"

        h.append('      <tr>')
        h.append(f'        {_scenario_td(row["name"], row["btn_info"], indent=_is_subordinate(row["name"]))}<td>{deals_str}</td><td>{filt_str}</td><td>{fout_str}</td>')
        for t in row["op_times"]:
            h.append(f'        <td>{t}</td>')
        h.append(f'        <td>{row["total_et"]}</td>')
        h.append('      </tr>')

    # Repeat totals at bottom
    h.append('      <tr class="totals">')
    h.append(f'        <td>Total</td><td>{total_deals}</td><td>{total_filtered}</td><td>{total_filtered_out}</td>')
    for ct in col_totals:
        h.append(f'        <td>{format_et(ct) if ct > 0 else "-"}</td>')
    h.append(f'        <td>{format_et(grand_total) if grand_total > 0 else "-"}</td>')
    h.append('      </tr>')
    h.append('      <tr class="totals">')
    h.append(f'        <td>%</td><td></td><td>{filt_pct_str}</td><td>{fout_pct_str}</td>')
    for ct in col_totals:
        pct = (ct / grand_total * 100) if grand_total > 0 else 0
        h.append(f'        <td>{pct:.1f}%</td>' if ct > 0 else '        <td>-</td>')
    h.append('        <td>100%</td>')
    h.append('      </tr>')
    # Repeat column headings after totals
    h.append('      <tr>')
    h.append('        <th></th><th>Deals</th><th>Filtered</th><th>Flt-Out</th>')
    for hdr in op_headers:
        h.append(f'        <th>{_esc(hdr)}</th>')
    h.append('        <th>Total</th>')
    h.append('      </tr>')

    h.append('    </table>')
    h.append('  </div>')
    h.append('  <script>')
    h.append('    var span = document.getElementById("gen-time");')
    h.append('    var d = new Date(span.dataset.utc);')
    h.append('    span.textContent = d.toLocaleDateString() + " " + d.toLocaleTimeString([], {hour: "2-digit", minute: "2-digit", timeZoneName: "short"});')
    h.append('    var table = document.querySelector(".main-table table");')
    h.append('    var hCol = -1;')
    h.append('    function clearCol() {')
    h.append('      table.querySelectorAll(".col-highlighted").forEach(function(c) {')
    h.append('        c.classList.remove("col-highlighted");')
    h.append('      });')
    h.append('      hCol = -1;')
    h.append('    }')
    h.append('    function applyCol(col) {')
    h.append('      clearCol();')
    h.append('      if (col < 1) return;')
    h.append('      hCol = col;')
    h.append('      var rows = table.rows;')
    h.append('      for (var i = 0; i < rows.length; i++) {')
    h.append('        if (rows[i].cells[col]) rows[i].cells[col].classList.add("col-highlighted");')
    h.append('      }')
    h.append('    }')
    h.append('    table.addEventListener("click", function(e) {')
    h.append('      var th = e.target.closest("th");')
    h.append('      if (th && table.contains(th)) {')
    h.append('        var col = th.cellIndex;')
    h.append('        if (col === hCol) clearCol(); else applyCol(col);')
    h.append('        return;')
    h.append('      }')
    h.append('      var td = e.target.closest("td");')
    h.append('      if (!td || !table.contains(td)) return;')
    h.append('      var col = td.cellIndex;')
    h.append('      var row = td.parentNode;')
    h.append('      if (row.classList.contains("totals")) return;')
    h.append('      var prev = table.querySelector("tr.highlighted");')
    h.append('      if (prev && prev !== row) prev.classList.remove("highlighted");')
    h.append('      row.classList.toggle("highlighted");')
    h.append('      if (col === hCol) clearCol(); else applyCol(col);')
    h.append('    });')
    h.append('  </script>')
    h.append('</body>')
    h.append('</html>')

    content = "\n".join(h)
    with open(OUTPUT_FILE, "w") as f:
        f.write(content)

    print(f"Summary written to {OUTPUT_FILE}")
    print(f"  {len(rows)} scenarios, {total_deals} total deals")


if __name__ == "__main__":
    pattern = sys.argv[1] if len(sys.argv) > 1 else "*"
    generate_summary(pattern)
