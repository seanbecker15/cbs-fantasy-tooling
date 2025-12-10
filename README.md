## CBS Fantasy Tooling

Scrapes CBS confidence-pool standings, pulls game outcomes from ESPN, and runs Monte Carlo strategy simulations using betting odds.

### Setup
- Python 3.9+ recommended.  
- Create a venv and install editable package:
  ```bash
  python -m venv .venv && source .venv/bin/activate
  pip install -e .
  ```
  
  **Note**: All required dependencies are specified in `pyproject.toml` and will be installed automatically. The `requirements.txt` file is kept for backwards compatibility and pinned versions but is not required for installation.
- Create `.env` in the repo root:
  ```bash
  EMAIL=you@example.com           # CBS login (required for scraping)
  PASSWORD=your_password          # CBS password
  THE_ODDS_API_KEY=your_key       # For strategy simulator
  ENABLED_PUBLISHERS=file,gmail   # file is safe default; add database if Supabase is configured
  GMAIL_FROM=you@example.com      # If using Gmail publisher (see docs/publishers.md)
  SUPABASE_URL=...                # Optional: for database publisher + win analyzer
  SUPABASE_KEY=...                # Optional: anon/service key
  USER_NAME=Your Name             # Optional default for analyzers
  WEEK_ONE_START_DATE=2025-09-02  # Used for week detection
  ```

### Daily Usage (Interactive CLI)
```bash
cbs-scrape
# OR
python -m cbs_fantasy_tooling.main
```
- **Ingest Data** → Pick'em Results (CBS scrape) and/or Game Outcomes (ESPN API).  
- **Analyze Data** → Strategy simulator, competitor intelligence, or contrarian visualization.  
Outputs are written to `out/` (CSV/JSON summaries, strategy predictions).

### Outputs
- `out/week_{n}_pickem_results.csv|json` — CBS scrape results.  
- `out/week_{n}_game_results.json` — ESPN game outcomes.  
- `out/week_{n}_strategy_summary.csv` + `out/week_{n}_predictions_{code}.json` — Monte Carlo strategies and recommendations.

### Scheduling (macOS)
Helper scripts wrap `launchctl`:
```bash
./scripts/schedule-task.sh     # schedule Tuesday 9am run
./scripts/unschedule-task.sh   # remove scheduled task
```
Logs land in `/tmp/cbs-sports-scraper/`.

### Troubleshooting
- Chrome/Selenium issues: ensure Chrome + matching chromedriver are installed.  
- Missing odds: check `THE_ODDS_API_KEY`.  
- Database publisher failures: verify `SUPABASE_URL`/`SUPABASE_KEY` and table schema (docs/publishers.md).  
- If the CLI real-time option is chosen, note that long-running polling is not yet wired; run manual real-time ingestion from `ingest/cbs_sports/scrape.py` (see docs/realtime.md).
