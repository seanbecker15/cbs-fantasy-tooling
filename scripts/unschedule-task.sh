#!/usr/bin/env bash
# Stop the Tuesday scrape job and keep it stopped across logins.
# `launchctl unload` alone is not enough: launchd reloads every .plist in
# ~/Library/LaunchAgents at login, so the file is renamed out of the way.
set -euo pipefail
PLIST="$HOME/Library/LaunchAgents/com.cbs-sports.scraper.plist"
if [ -f "$PLIST" ]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  mv "$PLIST" "$PLIST.disabled"
  echo "Unscheduled. Plist kept at $PLIST.disabled; run scripts/schedule-task.sh to re-enable."
else
  echo "Nothing scheduled ($PLIST not present)."
fi
