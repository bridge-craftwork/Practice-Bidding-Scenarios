#!/bin/bash
# Update dashboard, scenario summary, and convention card summary, then push to GitHub Pages
# Run by launchd at 6:00 AM, 12:00 PM, and 6:00 PM daily

cd /Users/adavidbailey/Practice-Bidding-Scenarios

echo "$(date): Starting dashboard update"

# launchd runs a job missed during sleep the moment the Mac wakes, often before the
# network is back. Wait up to 5 minutes for github.com rather than failing the run.
for i in $(seq 1 30); do
    git ls-remote --exit-code origin HEAD >/dev/null 2>&1 && break
    [ "$i" -eq 30 ] && { echo "$(date): github.com unreachable after 5 minutes; giving up"; exit 1; }
    sleep 10
done

# Bring main level with GitHub first, so the push at the end is a fast-forward.
# Without this, a PR merged on GitHub between runs leaves every later push rejected
# and the dashboard commits pile up locally. --autostash tolerates a dirty tree.
if ! git pull --rebase --autostash origin main; then
    echo "$(date): pull --rebase failed; aborting and leaving the tree as it was"
    git rebase --abort 2>/dev/null
    exit 1
fi

# One timestamp for every page this run writes, so their "Generated" times agree.
export PBS_GENERATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Generate dashboard data
/usr/bin/python3 docs/generateDashboardData.py

# Generate scenario summary
/usr/bin/python3 build-scripts-mac/scenario_summary.py

# Generate convention card summary
/usr/bin/python3 build-scripts-mac/convention_card_summary.py

# Generate curation summary
/usr/bin/python3 docs/generateCurationSummary.py

# Check if there are changes to commit
if git diff --quiet docs/index.html docs/dashboard-data.json docs/Scenario_Summary.html docs/Convention_Card_Summary.html docs/Curation_Summary.html; then
    echo "$(date): No changes to commit"
else
    echo "$(date): Committing and pushing changes"
    git add docs/index.html docs/dashboard-data.json docs/Scenario_Summary.html docs/Convention_Card_Summary.html docs/Curation_Summary.html
    git commit -m "Daily dashboard update"
    # The manifest bot can land a commit in the seconds between the pull and this push;
    # one more rebase covers that race.
    if ! git push; then
        echo "$(date): Push rejected; rebasing once more and retrying"
        if ! { git pull --rebase --autostash origin main && git push; }; then
            echo "$(date): Push failed; the commit is left local"
            exit 1
        fi
    fi
    echo "$(date): Push complete"
fi

echo "$(date): Dashboard update finished"
