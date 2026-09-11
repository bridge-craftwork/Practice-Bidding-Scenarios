#!/usr/bin/env python3
"""
Have BBO's GIB robots bid N deals from a scenario's dealer script, and save the
auctions as PBN (issue #323).

    python3 py/gib_capture.py Smolen                 # 30 boards -> GIB/Smolen.pbn
    python3 py/gib_capture.py Smolen -n 500          # a full capture, deliberately
    python3 py/gib_capture.py Smolen --delay 5       # pause 5s between boards
    python3 py/gib_capture.py path/to/Leveled.dlr -n 50 --out /tmp/x.pbn
    python3 py/gib_capture.py Smolen --dry-run       # show what BBO would receive
    python3 py/gib_capture.py Smolen --demo          # the same table, left to you

The dealer script is stripped exactly as the BBO extension strips it when a
button is clicked (bbo_dealer_code in build-scripts-mac/bbo_dealer.py), and
handed straight to setDealerCode on a live table: no GitHub round trip, so no
CDN staleness, and the robots bid exactly what we ship.

How: pbs-bbo-extension's test/playwright/pwrun.mjs (the live-BBO harness, with
its signed-in test profile, invisible sign-in and hard watchdog) runs
js/gib-capture.mjs, which starts a bidding table with four robots, sets the
dealer script with rotation off, and turns on the BBOalert PBNcapture plugin.

--demo stops before capture: the browser is left open at that table with the
script loaded, for testing it by hand - redealing, reading the robots' bid
explanations, and so on. Nothing is written. Close the BBO tab to end it.

Output: boards are written to <out>.partial as they arrive. A complete run
renames it to <out>; a short one leaves the .partial and any existing <out>
untouched. Exit status is 0 only for a complete run. An existing <out> is
never replaced without --force: GIB/ also holds the hand-collected captures.

This drives a real BBO account, and we are guests there: one run at a time
(enforced with a lock), and a small default N. Mac only. Measured at about 2
seconds a board once the table is up; --delay adds a pause after each board,
before the next deal, to go easier on the site.
"""
import os
import sys

# py/select.py shadows the stdlib module subprocess imports; drop py/ from the
# path so this runs without python3 -P.
sys.path = [p for p in sys.path if os.path.abspath(p or '.') != os.path.dirname(os.path.abspath(__file__))]

import argparse  # noqa: E402
import fcntl  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'build-scripts-mac'))
from bbo_dealer import bbo_dealer_code  # noqa: E402

CAPTURE_MODULE = os.path.join(PROJECT_ROOT, 'js', 'gib-capture.mjs')
PWRUN = os.environ.get('PBS_PWRUN', os.path.expanduser(
    '~/Development/GitHub/pbs-bbo-extension/test/playwright/pwrun.mjs'))
PROFILE = os.path.expanduser('~/.playwright-mcp/bbo-profile-test')
OUT_DIR = os.path.join(PROJECT_ROOT, 'GIB')
LOCK = os.path.join(tempfile.gettempdir(), 'pbs-gib-capture.lock')


def resolve_dlr(arg: str) -> tuple:
    """A scenario name or a .dlr path -> (scenario name, .dlr path)."""
    if arg.endswith('.dlr') or os.sep in arg:
        path = os.path.abspath(arg)
        return os.path.splitext(os.path.basename(path))[0], path
    return arg, os.path.join(PROJECT_ROOT, 'dlr', f'{arg}.dlr')


def count_boards(pbn_path: str) -> tuple:
    """(boards, sorted dealers seen) in a capture file."""
    if not os.path.exists(pbn_path):
        return 0, []
    with open(pbn_path, encoding='utf-8') as f:
        text = f.read()
    dealers = re.findall(r'^\[Dealer "(\w)"\]', text, re.MULTILINE)
    return len(re.findall(r'^\[Event ', text, re.MULTILINE)), sorted(set(dealers))


def run_harness(job: dict, profile: str, timeout: int, keep_open: bool, workdir: str) -> dict:
    """Run pwrun.mjs on the capture module; return its result JSON."""
    job_path = os.path.join(workdir, 'job.json')
    result_path = os.path.join(workdir, 'result.json')
    with open(job_path, 'w', encoding='utf-8') as f:
        json.dump(job, f)

    cmd = ['node', PWRUN, '--test', CAPTURE_MODULE, '--out', result_path,
           '--only', 'pbs', '--profile', profile, '--timeout', str(timeout)]
    env = {**os.environ, 'GIB_JOB': job_path}
    if keep_open:
        # The harness outlives this script, so it must not hold our stdout: a
        # caller reading it (a pipe, tee, the VS Code runner) would wait until
        # the browser closed. Log to a file instead and echo it once ready.
        cmd.append('--keep-open')
        log_path = os.path.join(tempfile.gettempdir(), 'pbs-bbo-demo.log')
        with open(log_path, 'w') as log:
            proc = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, start_new_session=True)
    else:
        proc = subprocess.Popen(cmd, env=env)
    # With --keep-open the harness never exits; its result file is the signal.
    while proc.poll() is None and not (keep_open and os.path.exists(result_path)):
        time.sleep(1)
    if keep_open:
        with open(log_path) as log:
            print(log.read(), end='', flush=True)
        print(f'  (harness pid {proc.pid}; log {log_path})')

    if not os.path.exists(result_path):
        return {'status': 'error', 'error': f'harness exited {proc.returncode} with no result file'}
    with open(result_path, encoding='utf-8') as f:
        return json.load(f)


def run_demo(scenario: str, dlr_path: str, code: str, seat: str, profile: str) -> int:
    """Set up the capture table with the script loaded, and leave it open for a person."""
    print(f'BBO demo: {scenario}, dealer {seat}\n  from {dlr_path}', flush=True)
    job = {'scenario': scenario, 'code': code, 'seat': seat, 'boards': 0, 'demo': True}
    with tempfile.TemporaryDirectory(prefix='bbo-demo-') as workdir:
        # The watchdog covers only the setup; it is cleared once the table is ready.
        result = run_harness(job, profile, 300, True, workdir)

    demo = result.get('result') or {}
    if demo.get('status') == 'demo':
        print('Ready: four robots, the script loaded, rotation off, nothing captured.\n'
              'Click Redeal for a new deal. Close the BBO tab when done.')
        return 0
    print(f"demo failed: {demo.get('error') or result.get('error') or result.get('status')}")
    if result.get('log'):
        print('harness log (last 15):\n  ' + '\n  '.join(result['log'][-15:]))
    return 2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('scenario', help='scenario name (reads dlr/<name>.dlr) or a path to a .dlr')
    ap.add_argument('-n', '--boards', type=int, default=30,
                    help='boards to capture (default 30; ask for more deliberately)')
    ap.add_argument('--out', help='output PBN (default GIB/<scenario>.pbn)')
    ap.add_argument('--force', action='store_true',
                    help='replace the output file if it already exists')
    ap.add_argument('--profile', default=PROFILE, help='Playwright browser profile (default: %(default)s)')
    ap.add_argument('--delay', type=float, default=0,
                    help='seconds to pause after each board before redealing (default 0)')
    ap.add_argument('--timeout', type=int,
                    help='hard watchdog, seconds (default 180 + (10 + delay) per board)')
    ap.add_argument('--stall', type=int, default=60,
                    help='seconds without a new board before clicking Redeal (default 60)')
    ap.add_argument('--keep-open', action='store_true',
                    help='leave the browser up afterwards to inspect; kill it by the pid it prints')
    ap.add_argument('--demo', action='store_true',
                    help='set up the table and script, capture nothing, and leave the browser open')
    ap.add_argument('--dry-run', action='store_true',
                    help='print the dealer seat and script BBO would receive, and stop')
    args = ap.parse_args()

    scenario, dlr_path = resolve_dlr(args.scenario)
    if not os.path.exists(dlr_path):
        print(f'Error: no .dlr at {dlr_path}', file=sys.stderr)
        return 1
    with open(dlr_path, encoding='utf-8') as f:
        code, seat = bbo_dealer_code(f.read())

    if args.dry_run:
        print(f'# dealer seat: {seat}\n{code}')
        return 0

    for path, what in ((PWRUN, 'pwrun.mjs (set PBS_PWRUN)'), (args.profile, 'test profile')):
        if not os.path.exists(path):
            print(f'Error: {what} not found: {path}', file=sys.stderr)
            return 1

    lock = open(LOCK, 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('Error: another GIB capture is running (one live BBO session at a time)', file=sys.stderr)
        return 1

    if args.demo:
        return run_demo(scenario, dlr_path, code, seat, args.profile)

    out = os.path.abspath(args.out or os.path.join(OUT_DIR, f'{scenario}.pbn'))
    # GIB/ also holds the hand-collected captures, many of them 500 boards: a
    # quick 30-board run must not replace one. Checked before BBO is touched.
    if os.path.exists(out) and not args.force:
        print(f'Error: {out} already exists ({count_boards(out)[0]} boards). '
              'Use --force to replace it, or --out to write elsewhere.', file=sys.stderr)
        return 1
    partial = out + '.partial'
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(partial):
        os.remove(partial)
    timeout = args.timeout or int(180 + (10 + args.delay) * args.boards)

    print(f'GIB capture: {scenario}, {args.boards} boards, dealer {seat}, '
          f'delay {args.delay:g}s, watchdog {timeout}s\n  from {dlr_path}\n  to   {out}', flush=True)
    job = {'scenario': scenario, 'code': code, 'seat': seat, 'boards': args.boards,
           'partialPbn': partial, 'stallSeconds': args.stall, 'delaySeconds': args.delay}
    with tempfile.TemporaryDirectory(prefix='gib-capture-') as workdir:
        result = run_harness(job, args.profile, timeout, args.keep_open, workdir)

    capture = result.get('result') or {}
    boards, dealers = count_boards(partial)
    print(f"harness: {result.get('status')}  capture: {capture.get('status', '-')}  "
          f"boards: {boards}/{args.boards}")
    if capture.get('error') or result.get('error'):
        print(f"  error: {capture.get('error') or result.get('error')}")
    if capture.get('discarded'):
        print(f"  discarded {capture['discarded']} board(s) dealt before the dealer script was set")
    if result.get('dialogs'):
        print(f"  dialogs: {result['dialogs']}")
    if dealers and dealers != [seat]:
        print(f'  WARNING: dealers {dealers} in the capture, expected only {seat} (was rotation on?)')

    if boards >= args.boards and capture.get('status') == 'ok':
        os.replace(partial, out)
        print(f'wrote {out}')
        return 0
    if boards:
        print(f'incomplete: {boards} boards kept in {partial}')
    if result.get('log'):
        print('harness log (last 15):\n  ' + '\n  '.join(result['log'][-15:]))
    return 2


if __name__ == '__main__':
    sys.exit(main())
