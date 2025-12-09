# Publishers (Outputs)

Publishers decide where scraped/ingested data goes. Enable them via `.env` `ENABLED_PUBLISHERS` (comma-separated, e.g., `file,gmail,database`).

## File (default, safest)
- **Config**: none required; uses `OUTPUT_DIR` (default `out/`) and optional `BACKUP_DIR`.  
- **Writes**: `week_{n}_pickem_results.csv|json`, `week_{n}_game_results.json`.  
- **Use when**: developing locally or feeding downstream analysis from files.

## Gmail
- **Config**:  
  - `GMAIL_CREDENTIALS_FILE` (default `credentials.json` from Google Cloud OAuth client).  
  - `GMAIL_TOKEN_FILE` (default `token.json`, created on first auth).  
  - `GMAIL_FROM`, `NOTIFICATION_TO` (comma-separated).  
- **Behavior**: emails CSV/JSON attachments of scrape results.  
- **Setup**: create OAuth client (Desktop), download creds, run a one-off ingest to complete the OAuth browser flow.

## Database (Supabase)
- **Config**: `SUPABASE_URL`, `SUPABASE_KEY`, optional `SEASON`. Add `database` to `ENABLED_PUBLISHERS`.  
- **Schema**: see `storage/providers/database.py` for table definitions (`player_results`, `player_picks`, `game_status`).  
- **Behavior**: upserts results with rankings; used by win analyzer and any streaming overlays.  
- **Realtime loop**: realtime polling uses only this publisher (see `docs/realtime.md`).

## Tips
- Keep `file` enabled even when using other publishers for easy auditing.  
- Gmail is best-effort; failures are logged but should not block the run.  
- For Supabase, set RLS policies before exposing data publicly.
