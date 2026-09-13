#!/bin/bash
# Update dashboard, scenario summary, and convention card summary, then push to GitHub Pages
# Run by launchd at 6:00 AM, 12:00 PM, and 6:00 PM daily

cd /Users/adavidbailey/Practice-Bidding-Scenarios

echo "$(date): Starting dashboard update"

# Bring main level with GitHub first, so the push at the end is a fast-forward.
# Without this, a PR merged on GitHub between runs leaves every later push rejected
# and the dashboard commits pile up locally. --autostash tolerates a dirty tree.
if ! git pull --rebase --autostash origin main; then
    echo "$(date): pull --rebase failed; aborting and leaving the tree as it was"
    git rebase --abort 2>/dev/null
    exit 1
fi

# Generate dashboard data
/usr/bin/python3 docs/generateDashboardData.py

# Generate scenario summary
/usr/bin/python3 build-scripts-mac/scenario_summary.py

# Generate convention card summary
/usr/bin/python3 build-scripts-mac/convention_card_summary.py

# Check if there are changes to commit
if git diff --quiet docs/index.html docs/dashboard-data.json docs/Scenario_Summary.html docs/Convention_Card_Summary.html; then
    echo "$(date): No changes to commit"
else
    echo "$(date): Committing and pushing changes"
    git add docs/index.html docs/dashboard-data.json docs/Scenario_Summary.html docs/Convention_Card_Summary.html
    git commit -m "Daily dashboard update"
    # The manifest bot can land a commit in the seconds between the pull and this push;
    # one more rebase covers that race.
    if ! git push; then
        echo "$(date): Push rejected; rebasing once more and retrying"
        git pull --rebase origin main && git push
    fi
    echo "$(date): Push complete"
fi

echo "$(date): Dashboard update finished"
