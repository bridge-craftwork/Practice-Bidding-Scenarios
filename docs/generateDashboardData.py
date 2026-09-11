#!/usr/bin/env python3
"""
Generate dashboard data from activity logs and git history.
Embeds data directly into dashboard.html for file:// protocol compatibility.
"""
import json
import os
import subprocess
import re
from datetime import datetime, timedelta
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))


def load_activity_log():
    """Load and parse activity-log.json"""
    log_path = os.path.join(PROJECT_ROOT, 'activity-log.json')
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            return json.load(f)
    return {"version": 1, "events": []}


def get_git_commits(days=365):
    """Get git commits from the past N days"""
    since_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    try:
        result = subprocess.run(
            ['git', 'log', f'--since={since_date}', '--format=%H|%ai|%s'],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        commits = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('|', 2)
                if len(parts) == 3:
                    commits.append({
                        'hash': parts[0][:8],
                        'date': parts[1],
                        'message': parts[2]
                    })
        return commits
    except Exception as e:
        print(f"Error getting git commits: {e}")
        return []


def current_scenarios():
    """Names of the current scenarios: the .btn master files"""
    btn_dir = os.path.join(PROJECT_ROOT, 'btn')
    if not os.path.exists(btn_dir):
        return set()
    return {f[:-4] for f in os.listdir(btn_dir)
            if f.endswith('.btn') and not f.startswith(('.', '-'))}


def get_scenario_count():
    """Count the number of scenarios"""
    return len(current_scenarios())


def get_unique_scenarios_worked(events):
    """Count unique scenarios that have been worked on (file saves or pipeline runs)"""
    scenarios = set()
    for event in events:
        event_type = event.get('type')
        if event_type in ('file_save', 'pipeline_run'):
            scenario = event.get('details', {}).get('scenario')
            if scenario:
                scenarios.add(scenario)
    return len(scenarios)


def get_scenarios_worked_from_git(days=1095):
    """
    Get cumulative unique scenarios worked on per month from git history.
    Looks at commits that modified files in scenario directories (PBS, dlr, pbn, etc.)
    and also at root level files from earlier project structure.
    Only counts scenarios that currently exist in btn/.
    Returns dict with monthly cumulative scenario counts and total unique scenarios.
    """
    since_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    scenario_dirs = ['pbs-release/', 'PBS/', 'dlr/', 'pbn/', 'bba/', 'bba-filtered/', 'bidding-sheets/']

    # The current scenario names, as canonical names
    valid_scenarios = current_scenarios()

    # Build a normalized lookup for matching historical names to current names
    # Current: "3_Under_Invitational_Jump", Historical: "Dealer: 3 Under Invitational Jump.gdoc"
    def normalize_name(name):
        """Normalize a name for matching (lowercase, replace spaces with underscores)."""
        # Remove common prefixes (longer prefixes first to avoid partial matches)
        for prefix in ['Dealer:  ', 'Dealer: ', 'Dealer-', 'Dealer ',
                       'Gavin:  ', 'Gavin: ', 'Gavin-', 'Gavin ',
                       'Basic-', 'Basic ']:
            if name.startswith(prefix):
                name = name[len(prefix):]
        # Remove extensions
        for ext in ['.pbs', '.gdoc', '.dlr', '.pbn', '.pdf', '.bba', '.lin', '.txt']:
            if name.lower().endswith(ext):
                name = name[:-len(ext)]
        # Normalize: replace spaces with underscores, lowercase
        return name.replace(' ', '_').replace('-', '_').lower()

    # Build normalized lookup from valid scenarios
    normalized_to_scenario = {}
    for scenario in valid_scenarios:
        normalized_to_scenario[normalize_name(scenario)] = scenario

    def extract_scenario_name(filepath):
        """Extract and match scenario name from various file formats."""
        # Get just the filename
        filename = filepath.split('/')[-1] if '/' in filepath else filepath
        normalized = normalize_name(filename)
        # Return the actual scenario name if it matches
        return normalized_to_scenario.get(normalized)

    try:
        # Get commits with their dates and changed files
        result = subprocess.run(
            ['git', 'log', f'--since={since_date}', '--format=%ai', '--name-only'],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )

        monthly_scenarios = defaultdict(set)  # month -> set of scenario names
        all_scenarios = set()
        current_month = None

        for line in result.stdout.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Check if this is a date line (e.g., "2026-01-26 14:30:00 -0500")
            if line[0].isdigit() and len(line) >= 10 and line[4] == '-':
                current_month = line[:7]
            elif current_month:
                scenario = None

                # Check if this is a file path in a scenario directory
                for dir_prefix in scenario_dirs:
                    if line.startswith(dir_prefix):
                        filename = line[len(dir_prefix):]
                        base_name = filename.split('.')[0] if '.' in filename else filename
                        if base_name in valid_scenarios:
                            scenario = base_name
                        else:
                            # Try normalized matching
                            scenario = extract_scenario_name(filename)
                        break

                # Also check root level files (historical format)
                if not scenario and '/' not in line:
                    scenario = extract_scenario_name(line)

                # Add if we found a valid scenario
                if scenario:
                    monthly_scenarios[current_month].add(scenario)
                    all_scenarios.add(scenario)

        # Build cumulative counts by month
        sorted_months = sorted(monthly_scenarios.keys())
        cumulative_scenarios = set()
        cumulative_counts = {}

        for month in sorted_months:
            cumulative_scenarios.update(monthly_scenarios[month])
            cumulative_counts[month] = len(cumulative_scenarios)

        return {
            'monthly': cumulative_counts,
            'total': len(all_scenarios)
        }
    except Exception as e:
        print(f"Error getting scenarios worked from git: {e}")
        return {'monthly': {}, 'total': 0}


def aggregate_events_by_month(events, type_filter=None):
    """Aggregate events by month (YYYY-MM format)"""
    monthly = defaultdict(int)
    for event in events:
        if type_filter and event.get('type') != type_filter:
            continue
        ts = event.get('timestamp', '')
        if ts:
            month = ts[:7]  # "2026-01"
            monthly[month] += 1
    return dict(sorted(monthly.items()))


def aggregate_commits_by_month(commits):
    """Aggregate commits by month"""
    monthly = defaultdict(int)
    for commit in commits:
        date_str = commit.get('date', '')
        if date_str:
            # Format: "2026-01-26 14:30:00 -0500"
            month = date_str[:7]
            monthly[month] += 1
    return dict(sorted(monthly.items()))


def calculate_session_stats(events):
    """Calculate total session time in minutes from activity log"""
    total_minutes = 0
    for event in events:
        if event.get('type') == 'session_end':
            duration = event.get('details', {}).get('durationMinutes', 0)
            if duration:
                total_minutes += duration
    return total_minutes


def estimate_file_edits_from_git(days=365):
    """
    Estimate file edits from git commit history.
    Counts number of files changed per commit, aggregated by month.
    Returns dict with monthly totals and overall total.
    """
    since_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    try:
        # Get commit dates with file change counts
        result = subprocess.run(
            ['git', 'log', f'--since={since_date}', '--format=%ai', '--shortstat'],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )

        monthly_edits = defaultdict(int)
        total_edits = 0
        current_month = None

        for line in result.stdout.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Check if this is a date line (e.g., "2026-01-26 14:30:00 -0500")
            if line and line[0].isdigit() and len(line) >= 10 and line[4] == '-':
                current_month = line[:7]
            # Check if this is a stat line (e.g., "3 files changed, 10 insertions(+)")
            elif 'file' in line and 'changed' in line:
                # Extract number of files changed
                match = re.search(r'(\d+) file', line)
                if match and current_month:
                    files_changed = int(match.group(1))
                    monthly_edits[current_month] += files_changed
                    total_edits += files_changed

        return {
            'monthly': dict(sorted(monthly_edits.items())),
            'total': total_edits
        }
    except Exception as e:
        print(f"Error estimating file edits: {e}")
        return {'monthly': {}, 'total': 0}


def estimate_session_hours_from_git(days=365):
    """
    Estimate VS Code session hours from git commit patterns.
    For each day with commits, estimates hours based on time span between
    first and last commit (minimum 1 hour, capped at 8 hours per day).
    Returns dict with monthly totals and overall total.
    """
    since_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    try:
        result = subprocess.run(
            ['git', 'log', f'--since={since_date}', '--format=%ai'],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )

        # Track first and last commit hour per day
        daily_first = {}
        daily_last = {}

        for line in result.stdout.strip().split('\n'):
            if line:
                # Format: "2026-01-26 14:30:00 -0500"
                parts = line.split()
                if len(parts) >= 2:
                    date = parts[0]
                    time_parts = parts[1].split(':')
                    if len(time_parts) >= 1:
                        hour = int(time_parts[0])
                        if date not in daily_first or hour < daily_first[date]:
                            daily_first[date] = hour
                        if date not in daily_last or hour > daily_last[date]:
                            daily_last[date] = hour

        # Calculate hours per day and aggregate by month
        monthly_hours = defaultdict(int)
        total_hours = 0

        for date in daily_first:
            # Hours = span from first to last commit + 1, capped at 8
            span = daily_last[date] - daily_first[date] + 1
            hours = max(1, min(span, 8))
            month = date[:7]
            monthly_hours[month] += hours
            total_hours += hours

        return {
            'monthly': dict(sorted(monthly_hours.items())),
            'total': total_hours
        }
    except Exception as e:
        print(f"Error estimating session hours: {e}")
        return {'monthly': {}, 'total': 0}


def get_last_n_months(n=12):
    """Get list of last N month labels"""
    months = []
    now = datetime.now()
    for i in range(n, -1, -1):
        date = now - timedelta(days=i * 30)
        months.append(date.strftime('%Y-%m'))
    return months


def format_month_labels(months):
    """Format month keys to readable labels"""
    labels = []
    for m in months:
        try:
            date = datetime.strptime(m, '%Y-%m')
            labels.append(date.strftime('%b %y'))
        except:
            labels.append(m)
    return labels


def generate_dashboard_data():
    """Generate all dashboard data"""
    log = load_activity_log()
    events = log.get('events', [])
    commits = get_git_commits(days=850)  # ~28 months back to Sep 2023

    # Get last 28 months (Sep 2023 to Jan 2026) for consistent chart labels
    months = get_last_n_months(28)

    # Aggregate data from activity log
    pipeline_runs_by_month = aggregate_events_by_month(events, 'pipeline_run')
    commits_by_month = aggregate_commits_by_month(commits)
    file_saves_by_month = aggregate_events_by_month(events, 'file_save')

    # Aggregate session hours from activity log
    session_hours_from_log = defaultdict(int)
    for event in events:
        if event.get('type') == 'session_end':
            duration = event.get('details', {}).get('durationMinutes', 0)
            if duration:
                ts = event.get('timestamp', '')
                if ts:
                    month = ts[:7]
                    session_hours_from_log[month] += duration // 60  # Convert to hours

    # Get git-based estimates for historical data (~28 months)
    session_hours_from_git = estimate_session_hours_from_git(days=850)
    file_edits_from_git = estimate_file_edits_from_git(days=850)
    scenarios_worked_from_git = get_scenarios_worked_from_git(days=850)

    # Combine: use activity log data where available, git estimates for the rest
    session_hours_by_month = {}
    file_edits_by_month = {}

    for m in months:
        # Session hours: prefer activity log if we have data for that month
        if session_hours_from_log.get(m, 0) > 0:
            session_hours_by_month[m] = session_hours_from_log[m]
        else:
            session_hours_by_month[m] = session_hours_from_git['monthly'].get(m, 0)

        # File edits: prefer activity log file saves if we have data for that month
        if file_saves_by_month.get(m, 0) > 0:
            file_edits_by_month[m] = file_saves_by_month[m]
        else:
            file_edits_by_month[m] = file_edits_from_git['monthly'].get(m, 0)

    # Get cumulative scenarios worked per month
    scenarios_worked_by_month = scenarios_worked_from_git['monthly']

    # Fill in zeros for months with no data
    for m in months:
        pipeline_runs_by_month.setdefault(m, 0)
        commits_by_month.setdefault(m, 0)
        session_hours_by_month.setdefault(m, 0)
        file_edits_by_month.setdefault(m, 0)

    # For cumulative scenarios, carry forward previous value for missing months
    sorted_months = sorted(months)
    prev_value = 0
    for m in sorted_months:
        if m in scenarios_worked_by_month:
            prev_value = scenarios_worked_by_month[m]
        else:
            scenarios_worked_by_month[m] = prev_value

    # Calculate totals (sum of combined monthly data)
    total_session_hours = sum(session_hours_by_month.values())
    total_file_edits = sum(file_edits_by_month.values())
    total_scenarios_worked = scenarios_worked_from_git['total']

    # Sort and extract values for charts
    sorted_months = sorted(months)
    labels = format_month_labels(sorted_months)

    return {
        "generatedAt": datetime.now().isoformat(),
        "summary": {
            "totalScenarios": get_scenario_count(),
            "scenariosWorked": total_scenarios_worked,
            "totalFileEdits": total_file_edits,
            "totalPipelineRuns": len([e for e in events if e.get('type') == 'pipeline_run']),
            "totalSessionHours": total_session_hours,
            "totalCommits": len(commits)
        },
        "charts": {
            "labels": labels,
            "fileEdits": [file_edits_by_month.get(m, 0) for m in sorted_months],
            "pipelineRuns": [pipeline_runs_by_month.get(m, 0) for m in sorted_months],
            "commits": [commits_by_month.get(m, 0) for m in sorted_months],
            "sessionHours": [session_hours_by_month.get(m, 0) for m in sorted_months],
            "scenariosWorked": [scenarios_worked_by_month.get(m, 0) for m in sorted_months]
        },
        "recentActivity": events[-20:] if events else [],
        "recentCommits": commits[:10] if commits else []
    }


def embed_data_in_html(dashboard_data):
    """Update index.html with embedded data"""
    html_path = os.path.join(DASHBOARD_DIR, 'index.html')

    with open(html_path, 'r') as f:
        html = f.read()

    # Create the data script
    data_json = json.dumps(dashboard_data, indent=2)
    data_script = f'const DASHBOARD_DATA = {data_json};'

    # Check if DASHBOARD_DATA already exists and replace it
    pattern = r'const DASHBOARD_DATA = \{[\s\S]*?\};'
    if re.search(pattern, html):
        # Use lambda to avoid interpreting backslashes in data_script as regex escapes
        html = re.sub(pattern, lambda m: data_script, html)
    else:
        # Insert before closing </head> tag
        html = html.replace('</head>', f'    <script>\n{data_script}\n    </script>\n</head>')

    with open(html_path, 'w') as f:
        f.write(html)

    print(f"Dashboard data embedded in {html_path}")


def main():
    print("Generating dashboard data...")

    dashboard_data = generate_dashboard_data()

    # Save JSON file (for debugging/inspection)
    json_path = os.path.join(DASHBOARD_DIR, 'dashboard-data.json')
    with open(json_path, 'w') as f:
        json.dump(dashboard_data, f, indent=2)
    print(f"Dashboard data saved to {json_path}")

    # Embed data in HTML
    embed_data_in_html(dashboard_data)

    # Print summary
    summary = dashboard_data['summary']
    print(f"\nSummary (since Sep 2023):")
    print(f"  Total scenarios: {summary['totalScenarios']}")
    print(f"  Scenarios worked on: {summary['scenariosWorked']}")
    print(f"  File edits: {summary['totalFileEdits']}")
    print(f"  Pipeline runs logged: {summary['totalPipelineRuns']}")
    print(f"  Estimated VS Code hours: {summary['totalSessionHours']}")
    print(f"  Git commits: {summary['totalCommits']}")


if __name__ == '__main__':
    main()
