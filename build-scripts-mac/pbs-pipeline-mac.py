#!/usr/bin/env python3
import os
os.environ["PYTHONUNBUFFERED"] = "1"

"""
Mac build pipeline for Practice-Bidding-Scenarios.
Replaces OneScriptToRuleThemAll.ps1 from Windows.

Usage:
    python build.py <scenario_pattern> <operations>

Examples:
    python build.py Smolen "*"           # All operations on Smolen
    python build.py Smolen dlr,pbn,bba   # Specific operations
    python build.py Smolen "bba+"        # From bba through end
    python build.py "*" "*"              # All scenarios, all operations
    python build.py "1N*" "*"            # Pattern match scenarios
"""
import argparse
import fnmatch
import json
import os
import sys
import time

from config import FOLDERS, OPERATIONS_ORDER, PROJECT_ROOT, DEALER_PLATFORM
from utils.properties import get_bba_works, get_bba_direct

# ANSI color codes
RED = '\033[91m'
RESET = '\033[0m'


def print_error(msg: str):
    """Print error message in red."""
    print(f"{RED}{msg}{RESET}")

# Import operations
from operations.pbn_from_dlr import run_pbn
from operations.rotate import run_rotate
from operations.bba_from_pbn import run_bba
from operations.filter import run_filter
from operations.filter_stats import run_filter_stats
from operations.bidding_sheet import run_bidding_sheet
from operations.dlr_from_btn import run_dlr
from operations.pbs_from_dlr import run_pbs
from operations.quiz import run_quiz
from operations.release import run_release
from operations.release_layout import run_release_layout
from operations.package import run_package
from scenario_summary import generate_summary


# Map operation names to functions
OPERATIONS = {
    "dlr": run_dlr,         # Generate DLR from BTN
    "pbs": run_pbs,         # Generate PBS from DLR
    "pbn": run_pbn,
    "rotate": run_rotate,
    "bba": run_bba,
    "filter": run_filter,
    "filterStats": run_filter_stats,
    "biddingSheet": run_bidding_sheet,
    "quiz": run_quiz,
    # release, release-layout, and package are NOT in OPERATIONS_ORDER, so they won't run with "*" or "op+"
    "release": run_release,
    "release-layout": run_release_layout,
    "package": run_package,
}

# Create case-insensitive lookup: lowercase -> canonical name
OPERATIONS_LOOKUP = {name.lower(): name for name in OPERATIONS.keys()}
OPERATIONS_ORDER_LOOKUP = {name.lower(): name for name in OPERATIONS_ORDER}


def normalize_operation(op: str) -> str:
    """Convert operation name to canonical form (case-insensitive)."""
    return OPERATIONS_LOOKUP.get(op.lower(), op)


def get_scenarios(pattern: str) -> list:
    """
    Get list of scenarios matching the pattern.
    Scenarios are discovered from the btn/ folder (.btn files).

    Args:
        pattern: Scenario name or wildcard pattern (e.g., "Smolen", "*", "1N*")

    Returns:
        List of scenario names (without .btn extension)
    """
    btn_dir = FOLDERS["btn"]

    # Get all .btn files
    btn_files = [f[:-4] for f in os.listdir(btn_dir)
                 if f.endswith('.btn') and not f.startswith('.') and not f.startswith('-')]

    if pattern == "*":
        # All scenarios
        return sorted(btn_files)
    elif "*" in pattern or "?" in pattern:
        # Wildcard pattern
        scenarios = []
        for f in btn_files:
            if fnmatch.fnmatch(f, pattern):
                scenarios.append(f)
        return sorted(scenarios)
    else:
        # Single scenario - find with correct case
        for f in btn_files:
            if f.lower() == pattern.lower():
                return [f]
        # No match found, return as-is (will fail later with clear error)
        return [pattern]


def expand_operations(operation_spec: str) -> list:
    """
    Expand operation specification into list of operations.

    Supports:
        "*" - all operations
        "op1,op2,op3" - specific operations (case-insensitive)
        "op+" - from op through end (case-insensitive)

    Args:
        operation_spec: Operation specification

    Returns:
        List of operation names (canonical form)
    """
    if operation_spec == "*" or operation_spec.lower() == "all":
        return OPERATIONS_ORDER.copy()

    # Check for "operation+" syntax
    if operation_spec.endswith("+"):
        start_op = operation_spec[:-1].lower()
        if start_op in OPERATIONS_ORDER_LOOKUP:
            canonical = OPERATIONS_ORDER_LOOKUP[start_op]
            start_idx = OPERATIONS_ORDER.index(canonical)
            return OPERATIONS_ORDER[start_idx:]
        else:
            print(f"Unknown operation: {operation_spec[:-1]}")
            return []

    # Comma-separated list
    operations = [op.strip() for op in operation_spec.split(",")]

    # Validate and normalize operations
    valid_ops = []
    for op in operations:
        canonical = normalize_operation(op)
        if canonical in OPERATIONS:
            valid_ops.append(canonical)
        else:
            print(f"Warning: Unknown operation '{op}', skipping")

    return valid_ops


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


# BBA and downstream operations that require bba-works=true
BBA_AND_DOWNSTREAM = {'bba', 'filter', 'filterStats', 'biddingSheet', 'quiz'}

# Dealer-side operations skipped for bba-direct scenarios (curated bba files).
# dlr/pbs still run so the BTN's @chat metadata flows to BBO via the PBS file.
BBA_DIRECT_SKIP = {'pbn', 'rotate', 'bba'}


def filter_operations_for_scenario(scenario: str, operations: list) -> list:
    """
    Filter operations based on scenario capabilities.
    - bba-works=false: exclude bba and downstream operations.
    - bba-direct=true: skip dealer/pbn/bba steps; the bba/{scenario}.pbn file
      is taken as the pre-curated input to filter.

    Args:
        scenario: Scenario name
        operations: List of operation names

    Returns:
        Filtered list of operations
    """
    if get_bba_direct(scenario):
        return [op for op in operations if op not in BBA_DIRECT_SKIP]

    if get_bba_works(scenario):
        return operations

    return [op for op in operations if op not in BBA_AND_DOWNSTREAM]


def _cleanup_filter_outputs(scenario: str, verbose: bool = True):
    """Remove stale filter output files when bba-works is false."""
    for folder_key in ['bba_filtered', 'bba_filtered_out']:
        folder = FOLDERS[folder_key]
        for ext in ['.pbn', '.pdf']:
            path = os.path.join(folder, f"{scenario}{ext}")
            if os.path.exists(path):
                os.remove(path)
                if verbose:
                    folder_name = os.path.basename(folder)
                    print(f"  Removed stale: {folder_name}/{scenario}{ext}")


def run_operations(scenario: str, operations: list, verbose: bool = True) -> tuple:
    """
    Run a list of operations on a scenario.

    Args:
        scenario: Scenario name
        operations: List of operation names
        verbose: Whether to print progress

    Returns:
        (success, durations) — success is True if all operations succeeded;
        durations maps each op that ran to its elapsed seconds (empty when
        every operation was filtered out, e.g. bba-works=false leaves nothing).
    """
    # Filter operations based on scenario capabilities
    filtered_ops = filter_operations_for_scenario(scenario, operations)

    if verbose and len(filtered_ops) < len(operations):
        skipped = [op for op in operations if op not in filtered_ops]
        print(f"  Skipping BBA+ operations (bba-works=false): {', '.join(skipped)}")

    # Clean up stale filter outputs when filter is skipped
    if 'filter' in set(operations) - set(filtered_ops):
        _cleanup_filter_outputs(scenario, verbose)

    if not filtered_ops:
        if verbose:
            print("  No operations to run after filtering")
        return True, {}

    success = True
    durations = {}

    for op in filtered_ops:
        if op not in OPERATIONS:
            print(f"Unknown operation: {op}")
            continue

        op_func = OPERATIONS[op]
        start_time = time.time()
        try:
            result = op_func(scenario, verbose=verbose)
            elapsed = time.time() - start_time
            durations[op] = elapsed
            if not result:
                print_error(f"Operation {op} failed for {scenario} ({format_duration(elapsed)})")
                success = False
                break  # Stop on first failure
        except Exception as e:
            elapsed = time.time() - start_time
            durations[op] = elapsed
            print_error(f"Error in operation {op} for {scenario}: {e} ({format_duration(elapsed)})")
            success = False
            break  # Stop on first failure

    # Print duration summary (always shown, even in quiet mode)
    if durations:
        total = sum(durations.values())
        print(f"\n  {scenario} duration summary:")
        for op, dur in durations.items():
            print(f"    {op:15} {format_duration(dur):>10}")
        print(f"    {'─' * 26}")
        print(f"    {'Total':15} {format_duration(total):>10}")

    return success, durations


def _print_build_summary(all_durations: dict, build_elapsed: float, failed: list):
    """Print a final build summary with total duration and slow scenarios."""
    print(f"\n{'=' * 60}")
    print(f"BUILD SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total scenarios: {len(all_durations)}")
    print(f"Failed: {len(failed)}")
    print(f"Total build time: {format_duration(build_elapsed)}")

    # Compute per-scenario totals and per-operation totals
    scenario_totals = {}
    op_totals = {}
    for scenario, durations in all_durations.items():
        scenario_totals[scenario] = sum(durations.values())
        for op, dur in durations.items():
            op_totals[op] = op_totals.get(op, 0) + dur

    # Per-operation aggregate
    print(f"\nTime by operation:")
    for op, total in sorted(op_totals.items(), key=lambda x: -x[1]):
        avg = total / len(all_durations) if all_durations else 0
        print(f"  {op:15} {format_duration(total):>10}  (avg {format_duration(avg)})")

    # Slowest scenarios overall
    sorted_scenarios = sorted(scenario_totals.items(), key=lambda x: -x[1])
    print(f"\nSlowest scenarios (top 10):")
    for scenario, total in sorted_scenarios[:10]:
        durations = all_durations[scenario]
        # Find which operation was slowest
        slowest_op = max(durations, key=durations.get) if durations else "?"
        slowest_dur = durations.get(slowest_op, 0)
        print(f"  {scenario:45} {format_duration(total):>10}  ({slowest_op} {format_duration(slowest_dur)})")

    # Slowest per-operation (pbn is usually the bottleneck)
    for target_op in ['pbn', 'bba']:
        op_scenarios = [(s, d.get(target_op, 0)) for s, d in all_durations.items() if target_op in d]
        op_scenarios.sort(key=lambda x: -x[1])
        if op_scenarios and op_scenarios[0][1] > 10:  # only show if any took > 10s
            print(f"\nSlowest {target_op} scenarios (top 5):")
            for scenario, dur in op_scenarios[:5]:
                print(f"  {scenario:45} {format_duration(dur):>10}")


TIMING_FILE = os.path.join(PROJECT_ROOT, "build-data", "pipeline-timing.json")


def _save_timing_data(all_durations: dict):
    """Save per-scenario timing data to JSON, merging with existing data."""
    timing_dir = os.path.dirname(TIMING_FILE)
    os.makedirs(timing_dir, exist_ok=True)

    # Load existing data
    existing = {}
    if os.path.exists(TIMING_FILE):
        with open(TIMING_FILE, "r") as f:
            existing = json.load(f)

    # Merge at operation level: preserve existing op timings, update only ops that ran
    for scenario, durations in all_durations.items():
        if scenario not in existing:
            existing[scenario] = {}
        existing[scenario].update(durations)

    with open(TIMING_FILE, "w") as f:
        json.dump(existing, f, indent=2, sort_keys=True)


def main():
    parser = argparse.ArgumentParser(
        description="Mac build pipeline for Practice-Bidding-Scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python build.py Smolen "*"           # All operations on Smolen
    python build.py Smolen dlr,pbn,bba   # Specific operations
    python build.py Smolen "bba+"        # From bba through end
    python build.py "*" "*"              # All scenarios, all operations
    python build.py "1N*" "*"            # Pattern match scenarios

Operations (in order):
    dlr         - Generate DLR from BTN file (outputs to dlr/)
    pbs         - Generate PBS from DLR file (outputs to pbs-test/)
    pbn         - Generate PBN hands from DLR using dealer
    rotate      - Create rotated PBN/LIN files for 4-player practice
    bba         - Analyze bidding with BBA
    filter      - Filter hands by auction pattern
    filterStats - Show filter statistics
    biddingSheet - Generate bidding sheets PDF
    quiz        - Generate quiz PBN/PDF from filtered BBA
        """,
    )

    parser.add_argument(
        "scenario_pattern",
        help="Scenario name or pattern (e.g., 'Smolen', '*', '1N*')",
    )
    parser.add_argument(
        "operations",
        help="Operations to run: '*' for all, 'op1,op2' for specific, 'op+' from op to end",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Reduce output verbosity",
    )

    args = parser.parse_args()

    verbose = not args.quiet

    # Get scenarios
    scenarios = get_scenarios(args.scenario_pattern)
    if not scenarios:
        print(f"No scenarios found matching: {args.scenario_pattern}")
        sys.exit(1)

    # Get operations
    operations = expand_operations(args.operations)
    if not operations:
        print(f"No valid operations specified: {args.operations}")
        sys.exit(1)

    if verbose:
        print(f"Scenarios: {', '.join(scenarios)}")
        print(f"Operations: {', '.join(operations)}")
        print()

    # Run operations on each scenario
    failed_scenarios = []
    all_durations = {}  # scenario -> {op: seconds}
    build_start = time.time()

    for scenario in scenarios:
        if verbose:
            print(f"{'=' * 60}")
            print(f"Processing: {scenario}")
            print(f"{'=' * 60}")

        success, durations = run_operations(scenario, operations, verbose=verbose)
        all_durations[scenario] = durations

        if not success:
            failed_scenarios.append(scenario)
            print_error(f"\nFailed: {scenario} - continuing with next scenario")
        elif verbose:
            print(f"\nCompleted: {scenario}")

        if verbose:
            print()

    build_elapsed = time.time() - build_start

    # Persist timing data
    _save_timing_data(all_durations)

    # Update Scenario Summary report (skip for non-pipeline operations like release)
    if set(operations) & set(OPERATIONS_ORDER):
        generate_summary()

    # Final summary
    if len(scenarios) > 1:
        _print_build_summary(all_durations, build_elapsed, failed_scenarios)

    if failed_scenarios:
        print_error(f"\n{len(failed_scenarios)} scenario(s) had errors:")
        for s in failed_scenarios:
            print_error(f"  - {s}")
        sys.exit(1)
    elif verbose:
        print("All scenarios completed successfully!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAborted.")
        sys.exit(130)
