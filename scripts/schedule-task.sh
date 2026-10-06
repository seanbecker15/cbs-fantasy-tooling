#!/usr/bin/env bash
# (Re-)enable the Tuesday 9:30 scrape job.
# NOTE: as of Oct 2026 the Selenium login is blocked by CBS's reCAPTCHA; the
# Chrome extension (extension/README.md) replaced this job. Re-enable only if
# the scraper can log in again.
set -euo pipefail
PLIST="$HOME/Library/LaunchAgents/com.cbs-sports.scraper.plist"
[ -f "$PLIST.disabled" ] && mv "$PLIST.disabled" "$PLIST"
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "Scheduled: $(launchctl list | grep com.cbs-sports.scraper || echo 'not loaded?')"
