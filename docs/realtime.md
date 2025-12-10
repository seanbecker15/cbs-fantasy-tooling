# Realtime Polling

Guide for real-time ingestion of both CBS Pick'em standings and ESPN Game Outcomes. The interactive CLI now supports "Real-Time" mode, which runs background threads that poll for updates until the program exits.

## Requirements
- Chrome + matching chromedriver installed (for CBS Pick'em scraping)
- `.env`: `EMAIL`, `PASSWORD` (for CBS Pick'em)
- `.env`: `SUPABASE_URL`, `SUPABASE_KEY` (optional, for database publisher)
- `.env`: `THE_ODDS_API_KEY` (for Game Outcomes)
- Supabase tables as defined in `storage/providers/database.py` (`player_results`, `player_picks`, `game_results`)

## Interactive CLI - Real-Time Mode

The recommended way to use real-time ingestion is through the interactive CLI:

```bash
python -m cbs_fantasy_tooling.main
# 1. Select "Ingest Data"
# 2. Select data type(s): "Pick'em Results" and/or "Game Outcomes"
# 3. Select mode: "Real-Time"
# 4. Enter target week number
```

### How Real-Time Mode Works

- **Background Threads**: When you select "Real-Time" mode, the ingestion runs in a background daemon thread
- **Polling Interval**: Default is 30 seconds between polls
- **Return to Menu**: After starting real-time ingestion, you return to the main menu while the background thread continues
- **Multiple Threads**: You can start multiple real-time ingestions (e.g., both Pick'em Results and Game Outcomes)
- **Thread Status**: The main menu shows how many background ingestion threads are running
- **Graceful Exit**: When you exit the program, all background threads automatically terminate

### Behavior Details

**Pick'em Results (CBS Scraping)**:
- Opens Chrome browser, logs in, navigates to target week
- Refreshes page and scrapes standings every 30 seconds
- Only publishes changes to database publisher (change detection minimizes writes)
- Browser remains open for the duration of polling

**Game Outcomes (ESPN API)**:
- Polls ESPN scoreboard API every 30 seconds
- Fetches game status, scores, and winners for the target week
- Publishes to all enabled publishers (file, gmail, database)
- Only writes when data changes from previous poll

## One-Off Ingestion (No Polling)

If you just need current data without continuous polling:

```bash
python -m cbs_fantasy_tooling.main
# 1. Select "Ingest Data"
# 2. Select data type(s)
# 3. Select mode: "Once"
# 4. Enter target week number
```

Results are saved via enabled publishers (file/database/gmail).

## Advanced: Manual Polling (Deprecated)

For backward compatibility, you can still manually invoke the polling functions:

### CBS Pick'em Manual Polling
```bash
python - <<'PY'
from cbs_fantasy_tooling.ingest.cbs_sports.scrape import PickemIngestParams, ingest_pickem_results
from cbs_fantasy_tooling.publishers.factory import create_publishers

publishers = create_publishers()
params = PickemIngestParams(curr_week=14, target_week=14, poll_interval=30)  # seconds
ingest_pickem_results(params, publishers)
PY
```

### Game Outcomes Manual Polling
```bash
python - <<'PY'
from cbs_fantasy_tooling.ingest.espn.api import GameOutcomeIngestParams, ingest_game_outcomes
from cbs_fantasy_tooling.publishers.factory import create_publishers

publishers = create_publishers()
params = GameOutcomeIngestParams(week=14, poll_interval=30)  # seconds
ingest_game_outcomes(params, publishers)
PY
```

**Note**: Manual polling blocks the current terminal. Press Ctrl+C to stop.

## Notes and Limitations

- **CBS Rate Limiting**: Keep poll_interval at 30s or higher to avoid rate limits
- **ESPN API**: Publicly accessible, no authentication required
- **Database Publisher**: If Supabase credentials are missing, realtime updates will skip database publishing
- **Publisher Selection**: Configure via `ENABLED_PUBLISHERS` in `.env` (default: `file,gmail`)
- **Chrome Requirement**: CBS Pick'em scraping requires Chrome browser
- **Thread Safety**: Background threads are daemon threads and will automatically terminate when the main program exits
- **Multiple Data Sources**: You can run both Pick'em Results and Game Outcomes real-time ingestion simultaneously

## Troubleshooting

**"No changes detected" messages**: 
- This is normal when data hasn't changed between polls
- Change detection prevents unnecessary writes

**Browser stays open during Pick'em polling**:
- This is expected behavior - the browser is reused for each poll
- Exit the program to close the browser

**Background threads not visible**:
- Check the main menu - it shows active background thread count
- Threads run silently in the background

**Data not updating in real-time**:
- Verify your publishers are configured correctly in `.env`
- Check that database credentials (if using database publisher) are valid
- Look for error messages in the console output

## For Public-Facing Applications

If exposing data via Supabase for overlays or dashboards:
- Review Supabase Row Level Security (RLS) policies
- Consider read-only access for public endpoints
- Monitor API usage and implement rate limiting if needed
