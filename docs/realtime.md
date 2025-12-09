# Realtime Polling (CBS Pick'em)

Lightweight guide for keeping the CBS standings page open and streaming updates into Supabase. The interactive CLI’s “Real-Time” option is not wired yet; use the snippet below for now.

## Requirements
- Chrome + matching chromedriver installed.  
- `.env`: `EMAIL`, `PASSWORD`, `SUPABASE_URL`, `SUPABASE_KEY`, `ENABLED_PUBLISHERS=database` (file/gmail are skipped in realtime loop).  
- Supabase tables as defined in `storage/providers/database.py` (`player_results`, `player_picks`).

## One-Off Scrape (no polling)
Recommended when you just need the current standings.
```bash
python -m cbs_fantasy_tooling.main
# Ingest Data → Pick'em Results → Once
# Choose target week when prompted
```
Results are saved via enabled publishers (file/database/gmail).

## Realtime Polling (manual entry point)
```bash
python - <<'PY'
from cbs_fantasy_tooling.ingest.cbs_sports.scrape import PickemIngestParams, ingest_pickem_results
from cbs_fantasy_tooling.publishers.factory import create_publishers

publishers = create_publishers()
params = PickemIngestParams(curr_week=14, target_week=14, poll_interval=30)  # seconds
ingest_pickem_results(params, publishers)
PY
```
Behavior:
- Opens Chrome, logs in, navigates to target week, then refreshes/scrapes every `poll_interval` seconds.  
- Only publishes to the **database** publisher during polling (change detection keeps writes minimal).  
- Press Enter in the terminal to stop; the browser closes cleanly.

## Notes and Limitations
- Game outcome polling is not wired; this loop only streams CBS pick’em standings.  
- If Supabase creds are missing, realtime updates will skip publishing.  
- Polling frequency defaults to 30s; increase if CBS rate limits or your IP is slow.  
- For public-facing overlays, review Supabase RLS policies before enabling writes.
