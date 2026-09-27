#!/usr/bin/env python3
"""
Check whether a scenario's convention card could be replaced by 21GF-SPECIALS.

Usage:
    python3 check-convention-card.py <scenario>
    python3 check-convention-card.py <scenario> --test
    python3 check-convention-card.py --scan

Arguments:
    <scenario>   Scenario name (e.g., "Gambling_3N")
    --test       Run BBA + filter comparison test (takes ~10 seconds per scenario)
    --scan       Scan all scenarios and report which could use SPECIALS

Examples:
    python3 check-convention-card.py Gambling_3N
    python3 check-convention-card.py Gambling_3N --test
    python3 check-convention-card.py --scan
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.leveling import leveled_or_original
from config import FOLDERS, MAC_TOOLS, DEFAULT_CC1, DEFAULT_CC2

# ---------------------------------------------------------------------------
# BBSA parsing
# ---------------------------------------------------------------------------

def parse_bbsa(filepath):
    """Parse a .bbsa file into a dict of setting -> value."""
    settings = {}
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if " = " in line:
                key, val = line.rsplit(" = ", 1)
                if key != "Not defined":
                    settings[key] = val
    return settings


# ---------------------------------------------------------------------------
# Conflict groups — settings that are mutually exclusive
# ---------------------------------------------------------------------------

# Conflict groups: "hard" conflicts define the same bid differently and
# are likely to affect filtering. "soft" conflicts are preference differences
# that rarely matter in practice.

CONFLICT_GROUPS = {
    "2D opening": {
        "settings": ["Weak natural 2D", "Flannery", "Multi", "Benjamin 2D",
                      "French 2D", "Precision 2D", "Strong natural 2D", "Wilkosz"],
        "description": "What does a 2D opening mean?",
        "severity": "hard",
    },
    "1N-2S meaning": {
        "settings": ["1N-2S transfer to clubs", "1N-2S Minor Suit Stayman"],
        "description": "What does 1NT-2S mean?",
        "severity": "hard",
    },
    "Gambling 3N": {
        "settings": ["Gambling"],
        "description": "Is 3NT opening Gambling?",
        "severity": "hard",
    },
    "Inverted minors": {
        "settings": ["Inverted minors"],
        "description": "Are minor raises inverted?",
        "severity": "hard",
    },
    "System type": {
        "settings": ["System type"],
        "description": "Base bidding system (0=2/1GF, 1=variant, etc.)",
        "severity": "hard",
    },
    "1NT defense": {
        "settings": ["Cappelletti", "Multi-Landy", "Landy"],
        "description": "How do we compete after opponent's 1NT?",
        "severity": "soft",
    },
    "Bergen": {
        "settings": ["Bergen"],
        "description": "Bergen raises enabled?",
        "severity": "hard",
    },
    "1M-3M raises": {
        "settings": ["1M-3M blocking", "1M-3M inviting"],
        "description": "Are 1M-3M raises invitational or preemptive?",
        "severity": "soft",
    },
    "Blackwood variant": {
        "settings": ["Blackwood 0314", "Blackwood 1430", "Blackwood 0123"],
        "description": "Which Blackwood response order?",
        "severity": "soft",
    },
    "Lebensohl vs Rubensohl": {
        "settings": ["Lebensohl after 1NT", "Rubensohl after 1NT",
                      "Lebensohl after 1m", "Rubensohl after 1m",
                      "Lebensohl after double", "Rubensohl after double"],
        "description": "Lebensohl or Rubensohl after interference?",
        "severity": "soft",
    },
    "NMF variant": {
        "settings": ["New Minor Forcing", "Two Way New Minor Forcing", "Checkback"],
        "description": "Which new minor forcing variant?",
        "severity": "soft",
    },
}


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def diff_cards(card_a, card_b):
    """Return settings that differ between two parsed cards.
    Treats missing settings as '0' (the BBSA default for absent settings)."""
    diffs = {}
    all_keys = set(card_a) | set(card_b)
    for key in all_keys:
        val_a = card_a.get(key, "0")
        val_b = card_b.get(key, "0")
        if val_a != val_b:
            diffs[key] = (val_a, val_b)
    return diffs


def check_conflict_groups(card_a, card_b):
    """Check which conflict groups have differences between two cards."""
    conflicts = []
    for group_name, group in CONFLICT_GROUPS.items():
        for setting in group["settings"]:
            val_a = card_a.get(setting)
            val_b = card_b.get(setting)
            if val_a is not None and val_b is not None and val_a != val_b:
                conflicts.append({
                    "group": group_name,
                    "setting": setting,
                    "val_a": val_a,
                    "val_b": val_b,
                    "description": group["description"],
                })
    return conflicts


def get_convention_card_name(scenario):
    """Get the convention card name from the DLR file."""
    dlr_path = os.path.join(FOLDERS["dlr"], f"{scenario}.dlr")
    if not os.path.exists(dlr_path):
        return None
    pattern = re.compile(r"^#?\s*convention-card(?:-ns)?:\s*(.+)$", re.IGNORECASE)
    with open(dlr_path) as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                return match.group(1).strip()
    return DEFAULT_CC1


def get_auction_filter(scenario):
    """Get the auction filter from the DLR file."""
    dlr_path = os.path.join(FOLDERS["dlr"], f"{scenario}.dlr")
    if not os.path.exists(dlr_path):
        return None
    pattern = re.compile(r"^#?\s*auction-filter:\s*(.+)$", re.IGNORECASE)
    with open(dlr_path) as f:
        for line in f:
            match = pattern.match(line.strip())
            if match:
                return match.group(1).strip()
    return None


def classify_filter(filter_expr):
    """Classify a filter as annotation-based, auction-pattern, or contract-based."""
    if not filter_expr:
        return "none"
    if "Note" in filter_expr:
        return "annotation"
    if "Contract" in filter_expr:
        return "contract"
    return "auction-pattern"


# ---------------------------------------------------------------------------
# BBA + filter test
# ---------------------------------------------------------------------------

def normalize_filter_for_bw(filter_expr):
    """Normalize filter expression for bridge-wrangler."""
    result = filter_expr
    result = result.replace("\\r?\\n", "\n")
    result = result.replace("\\n", "\n")
    result = result.replace(" ", r"\s+")
    if not result.startswith("(?s)"):
        result = "(?s)" + result
    return result


def count_boards(filepath):
    """Count [Board] entries in a PBN file."""
    if not os.path.exists(filepath):
        return 0
    with open(filepath) as f:
        return sum(1 for line in f if line.startswith('[Board '))


def extract_board_numbers(filepath):
    """Extract board numbers from a PBN file."""
    boards = set()
    if not os.path.exists(filepath):
        return boards
    with open(filepath) as f:
        for line in f:
            m = re.match(r'\[Board "(\d+)"\]', line)
            if m:
                boards.add(m.group(1))
    return boards


def run_bba_test(scenario, current_cc_name):
    """Run BBA with both current card and SPECIALS, filter, and compare."""
    bba_cli = MAC_TOOLS.get("bba_cli")
    bridge_wrangler = MAC_TOOLS.get("bridge_wrangler")

    if not bba_cli or not os.path.exists(bba_cli):
        print("  Error: bba-cli-mac not found")
        return None
    if not bridge_wrangler or not os.path.exists(bridge_wrangler):
        print("  Error: bridge-wrangler not found")
        return None

    pbn_path = leveled_or_original(scenario, "pbn")
    if not os.path.exists(pbn_path):
        print(f"  Error: PBN file not found: {pbn_path}")
        return None

    filter_expr = get_auction_filter(scenario)
    if not filter_expr:
        print("  Warning: No auction filter for this scenario; comparing raw BBA board counts only")

    current_cc_path = os.path.join(FOLDERS["bbsa"], f"{current_cc_name}.bbsa")
    specials_cc_path = os.path.join(FOLDERS["bbsa"], "21GF-SPECIALS.bbsa")
    cc2_path = os.path.join(FOLDERS["bbsa"], f"{DEFAULT_CC2}.bbsa")

    with tempfile.TemporaryDirectory(prefix="cc-test-") as tmpdir:
        results = {}
        for label, cc1_path in [("current", current_cc_path), ("SPECIALS", specials_cc_path)]:
            bba_out = os.path.join(tmpdir, f"{label}.pbn")
            cmd = [
                bba_cli,
                "--input", pbn_path,
                "--output", bba_out,
                "--ns-conventions", cc1_path,
                "--ew-conventions", cc2_path,
                "--event", scenario.replace("_", " "),
            ]
            print(f"  Running BBA with {label} card...", end="", flush=True)
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if result.returncode != 0:
                    print(f" FAILED ({result.stderr.strip()})")
                    return None
                print(" done")
            except subprocess.TimeoutExpired:
                print(" TIMEOUT")
                return None

            if filter_expr:
                matched = os.path.join(tmpdir, f"{label}_matched.pbn")
                nomatch = os.path.join(tmpdir, f"{label}_nomatch.pbn")
                norm = normalize_filter_for_bw(filter_expr)
                fcmd = [bridge_wrangler, "filter", "-i", bba_out,
                        "-p", norm, "-m", matched, "-n", nomatch]
                subprocess.run(fcmd, capture_output=True, text=True)
                boards = extract_board_numbers(matched)
                total = count_boards(bba_out)
                results[label] = {"matched": len(boards), "total": total, "boards": boards}
            else:
                total = count_boards(bba_out)
                results[label] = {"matched": total, "total": total, "boards": set()}

        return results


# ---------------------------------------------------------------------------
# Main commands
# ---------------------------------------------------------------------------

def check_scenario(scenario, run_test=False):
    """Check a single scenario and print analysis."""
    cc_name = get_convention_card_name(scenario)
    if not cc_name:
        print(f"  Error: Could not find DLR file for '{scenario}'")
        return

    filter_expr = get_auction_filter(scenario)
    filter_type = classify_filter(filter_expr)

    print(f"\nScenario:     {scenario}")
    print(f"Current card: {cc_name}")
    print(f"Filter:       {filter_expr or '(none)'}")
    print(f"Filter type:  {filter_type}")

    if cc_name in (DEFAULT_CC1, "21GF-GIB"):
        print(f"\n  This scenario uses the default card ({cc_name}). No change needed.")
        return

    if cc_name == "21GF-SPECIALS":
        print(f"\n  Already using SPECIALS.")
        return

    # Parse cards
    default_path = os.path.join(FOLDERS["bbsa"], f"{DEFAULT_CC1}.bbsa")
    specials_path = os.path.join(FOLDERS["bbsa"], "21GF-SPECIALS.bbsa")
    current_path = os.path.join(FOLDERS["bbsa"], f"{cc_name}.bbsa")

    if not os.path.exists(current_path):
        print(f"\n  Error: Card file not found: {current_path}")
        return
    if not os.path.exists(specials_path):
        print(f"\n  Error: SPECIALS card not found: {specials_path}")
        return

    default_card = parse_bbsa(default_path)
    specials_card = parse_bbsa(specials_path)
    current_card = parse_bbsa(current_path)

    # What does the current card change from default?
    current_vs_default = diff_cards(default_card, current_card)
    print(f"\n--- {cc_name} changes {len(current_vs_default)} settings from DEFAULT ---")
    for key in sorted(current_vs_default):
        val_d, val_c = current_vs_default[key]
        marker = ""
        # Check if SPECIALS has this same change
        spec_val = specials_card.get(key, "0")
        if spec_val == val_c:
            marker = "  (in SPECIALS)"
        elif spec_val == val_d:
            marker = "  ** NOT in SPECIALS **"
        else:
            marker = f"  ** SPECIALS={spec_val} **"
        print(f"  {key:45s} {val_d:>3} -> {val_c:>3}{marker}")

    # Check conflict groups between current card and SPECIALS
    conflicts = check_conflict_groups(current_card, specials_card)

    hard_conflicts = [c for c in conflicts
                      if CONFLICT_GROUPS[c["group"]]["severity"] == "hard"]
    soft_conflicts = [c for c in conflicts
                      if CONFLICT_GROUPS[c["group"]]["severity"] == "soft"]

    print(f"\n--- Conflict group analysis: {cc_name} vs SPECIALS ---")
    if not conflicts:
        print("  No conflict group collisions detected.")
    else:
        if hard_conflicts:
            for c in hard_conflicts:
                print(f"  HARD CONFLICT [{c['group']}]: {c['setting']}")
                print(f"    {cc_name}={c['val_a']}, SPECIALS={c['val_b']}")
                print(f"    ({c['description']})")
        if soft_conflicts:
            groups = sorted(set(c["group"] for c in soft_conflicts))
            print(f"  Soft differences (usually don't affect filtering): {', '.join(groups)}")

    # Overall recommendation
    print(f"\n--- Recommendation ---")

    # Check if all essential changes are in SPECIALS
    essential_missing = []
    essential_conflict = []
    for key, (val_d, val_c) in current_vs_default.items():
        spec_val = specials_card.get(key, "0")
        if spec_val == val_c:
            continue  # SPECIALS has this change
        else:
            if spec_val == val_d:
                essential_missing.append((key, val_c))
            else:
                essential_conflict.append((key, val_c, spec_val))

    if hard_conflicts:
        groups = sorted(set(c["group"] for c in hard_conflicts))
        print(f"  -> INCOMPATIBLE. Hard conflicts in: {', '.join(groups)}")
        print(f"     Keep the current card ({cc_name}).")
    elif not essential_missing and not essential_conflict:
        print("  -> SPECIALS is compatible. All essential settings are present.")
        if filter_type == "annotation":
            print("     Note: This scenario uses annotation-based filtering.")
            print("     Extra conventions in SPECIALS *could* affect Note annotations.")
            print("     Recommend running with --test to verify.")
        else:
            print("     This scenario uses structural filtering - low risk of interference.")
    elif essential_conflict:
        print("  -> SPECIALS has settings that differ from what this card wants.")
        for key, wanted, has in essential_conflict:
            print(f"     {key}: needs {wanted}, SPECIALS has {has}")
        print("     Run with --test to check if this actually matters.")
    else:
        print("  -> SPECIALS is missing some settings from the current card.")
        print("     These are likely incidental (the current card was probably")
        print("     created from a different base, not from DEFAULT).")
        print("     Run with --test to verify SPECIALS works for this scenario.")
        if len(essential_missing) <= 8:
            for key, val in essential_missing:
                print(f"     Missing: {key} = {val}")

    # Run BBA test if requested
    if run_test:
        print(f"\n--- BBA + Filter Test ---")
        results = run_bba_test(scenario, cc_name)
        if results:
            curr = results["current"]
            spec = results["SPECIALS"]
            print(f"\n  {'Card':<12} {'Matched':>8} / {'Total':>5}")
            print(f"  {'Current':<12} {curr['matched']:>8} / {curr['total']:>5}")
            print(f"  {'SPECIALS':<12} {spec['matched']:>8} / {spec['total']:>5}")

            if filter_expr:
                common = curr["boards"] & spec["boards"]
                lost = curr["boards"] - spec["boards"]
                gained = spec["boards"] - curr["boards"]
                print(f"\n  Boards in common: {len(common)}")
                if lost:
                    print(f"  LOST boards (in current, not SPECIALS): {len(lost)}")
                    print(f"    {sorted(lost, key=int)[:15]}")
                if gained:
                    print(f"  GAINED boards (in SPECIALS, not current): {len(gained)}")
                    print(f"    {sorted(gained, key=int)[:15]}")
                if not lost and not gained:
                    print(f"\n  VERDICT: SPECIALS produces identical filtered output.")
                    print(f"  Safe to switch this scenario to 21GF-SPECIALS.")
                elif not lost and gained:
                    print(f"\n  VERDICT: SPECIALS finds {len(gained)} additional boards. No boards lost.")
                    print(f"  Likely safe, but review the extra boards.")
                elif lost and len(lost) <= 2:
                    print(f"\n  VERDICT: {len(lost)} boards differ (minor). Probably safe.")
                else:
                    print(f"\n  VERDICT: {len(lost)} boards lost. Keep the current card.")


def scan_all(run_test=False):
    """Scan all scenarios and report SPECIALS compatibility."""
    dlr_dir = FOLDERS["dlr"]
    if not os.path.exists(dlr_dir):
        print("Error: DLR directory not found")
        return

    # Collect all scenarios with non-default cards
    scenarios = []
    for f in sorted(os.listdir(dlr_dir)):
        if not f.endswith(".dlr"):
            continue
        name = f.replace(".dlr", "")
        cc = get_convention_card_name(name)
        if cc and cc not in (DEFAULT_CC1, "21GF-GIB", "21GF-SPECIALS"):
            scenarios.append((name, cc))

    if not scenarios:
        print("No scenarios with non-default convention cards found.")
        return

    specials_path = os.path.join(FOLDERS["bbsa"], "21GF-SPECIALS.bbsa")
    default_path = os.path.join(FOLDERS["bbsa"], f"{DEFAULT_CC1}.bbsa")

    if not os.path.exists(specials_path):
        print("Error: 21GF-SPECIALS.bbsa not found")
        return

    specials_card = parse_bbsa(specials_path)
    default_card = parse_bbsa(default_path)

    compatible = []
    incompatible = []
    missing_card = []

    for name, cc in scenarios:
        cc_path = os.path.join(FOLDERS["bbsa"], f"{cc}.bbsa")
        if not os.path.exists(cc_path):
            missing_card.append((name, cc))
            continue

        current_card = parse_bbsa(cc_path)
        conflicts = check_conflict_groups(current_card, specials_card)
        hard_conflicts = [c for c in conflicts
                          if CONFLICT_GROUPS[c["group"]]["severity"] == "hard"]
        soft_conflicts = [c for c in conflicts
                          if CONFLICT_GROUPS[c["group"]]["severity"] == "soft"]

        filter_type = classify_filter(get_auction_filter(name))

        if hard_conflicts:
            incompatible.append((name, cc, hard_conflicts, filter_type))
        else:
            has_soft = bool(soft_conflicts)
            compatible.append((name, cc, has_soft, filter_type))

    print(f"\n{'='*70}")
    print(f"SPECIALS COMPATIBILITY SCAN ({len(scenarios)} scenarios with special cards)")
    print(f"{'='*70}")

    print(f"\n--- COMPATIBLE with SPECIALS ({len(compatible)} scenarios) ---")
    print(f"  No hard conflicts. Use --test to verify before switching.\n")
    print(f"  {'Scenario':<40} {'Current Card':<25} {'Filter':<15} {'Notes'}")
    print(f"  {'-'*39} {'-'*24} {'-'*14} {'-'*20}")
    for name, cc, has_soft, ft in compatible:
        notes = ""
        if has_soft:
            notes = "soft diffs"
        if ft == "annotation":
            notes += " annotation-filter" if notes else "annotation-filter"
        print(f"  {name:<40} {cc:<25} {ft:<15} {notes}")

    print(f"\n--- INCOMPATIBLE with SPECIALS ({len(incompatible)} scenarios) ---\n")
    print(f"  {'Scenario':<40} {'Current Card':<25} {'Conflict Group'}")
    print(f"  {'-'*39} {'-'*24} {'-'*30}")
    for name, cc, conflicts, ft in incompatible:
        groups = ", ".join(set(c["group"] for c in conflicts))
        print(f"  {name:<40} {cc:<25} {groups}")

    if missing_card:
        print(f"\n--- MISSING CARD FILES ({len(missing_card)}) ---")
        for name, cc in missing_card:
            print(f"  {name}: {cc}.bbsa not found")

    total_compatible = len(compatible)
    total = len(scenarios)
    print(f"\n--- Summary ---")
    print(f"  {total_compatible}/{total} scenarios could potentially use SPECIALS")
    print(f"  {len(incompatible)}/{total} scenarios need their own card (conflict groups)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Check if a scenario's convention card could be replaced by 21GF-SPECIALS."
    )
    parser.add_argument("scenario", nargs="?", help="Scenario name (e.g., Gambling_3N)")
    parser.add_argument("--test", action="store_true",
                        help="Run BBA + filter comparison test")
    parser.add_argument("--scan", action="store_true",
                        help="Scan all scenarios for SPECIALS compatibility")
    args = parser.parse_args()

    if args.scan:
        scan_all()
    elif args.scenario:
        check_scenario(args.scenario, run_test=args.test)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
