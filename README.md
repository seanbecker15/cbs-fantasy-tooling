# CBS Fantasy Tooling

NFL confidence pool simulator with automated data ingestion, Monte Carlo analysis, and competitor intelligence.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env  # Add your credentials
cbs-scrape
```

## What It Does

- **Scrapes** CBS Sports pick'em standings (Selenium)
- **Fetches** ESPN game results + The Odds API moneylines
- **Simulates** 20K+ Monte Carlo scenarios with de-vigged probabilities
- **Analyzes** your picks vs built-in strategies (Chalk, Contrarian, etc.)
- **Publishes** to file/email/Supabase

## Main Workflows

**Weekly strategy analysis:**
```bash
cbs-scrape → Analyze Data → Strategy Simulator
```

**Data ingestion (once or real-time):**
```bash
cbs-scrape → Ingest Data → Pick'em/Games/Odds → Once/Real-Time
```

## Required `.env` Variables

```bash
# For scraping
EMAIL=your_cbs_email
PASSWORD=your_cbs_password

# Pool identity - the base32 slug from your pool URL:
# https://picks.cbssports.com/football/pickem/pools/<CBS_POOL_SLUG>/standings/weekly
# This is NEW EVERY SEASON.
CBS_POOL_SLUG=your_pool_slug

# For strategy analysis (recommended)
THE_ODDS_API_KEY=your_key  # theoddsapi.com - 500 free/mo
SEASON=2026
WEEK_ONE_START_DATE=2026-09-08  # Tuesday before Week 1

# Season-scoped storage
OUTPUT_DIR=data/2026    # this season's output
HISTORY_DIR=data/2025   # completed seasons used to model the field

# Optional
LEAGUE_SIZE=32          # number of players in the pool

# For publishers (optional)
GMAIL_FROM=you@gmail.com
NOTIFICATION_TO=recipient@example.com
SUPABASE_URL=https://xyz.supabase.co
SUPABASE_KEY=your_key
```

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Agent guardrails
- **[docs/usage.md](docs/usage.md)** - Simulator how-to
- **[docs/win-analyzer.md](docs/win-analyzer.md)** - Win scenario tool
- **[docs/data-sources.md](docs/data-sources.md)** - CBS/ESPN/Odds API details
- **[docs/monte-carlo.md](docs/monte-carlo.md)** - Simulation internals
- **[docs/publishers.md](docs/publishers.md)** - File/Gmail/Supabase output
- **[docs/schemas.md](docs/schemas.md)** - Data formats
- **[docs/season-rollover.md](docs/season-rollover.md)** - Start-of-season checklist

## Season Rollover

At the start of each season, see **[docs/season-rollover.md](docs/season-rollover.md)**.
Output filenames are not season-scoped, so a new season will overwrite the previous
one unless `OUTPUT_DIR` is pointed at a new directory.

## Outputs

All results saved to `OUTPUT_DIR` (e.g. `data/2026/`):
- `data/week_{N}_game_results.json` - ESPN game slate with live/final scores
- `data/week_{N}_pickem_results.csv` - CBS pick'em leaderboard (tabular export)
- `data/week_{N}_pickem_results.json` - CBS pick'em leaderboard (structured JSON)
- `data/week_{N}_predictions_{strategy}.json` - Picks by strategy (`chalk`, `slight`, `aggress`, `shuffle`, `user` when provided)
- `data/week_{N}_strategy_summary.csv` - Expected points per strategy
- `data/week_{N}_aggressiveness_metrics.csv` - Aggressiveness + leverage metrics per player
- `data/week_{N}_player_aggressiveness_rankings.png` - Aggressiveness leaderboard visualization

## Common Issues

| Error | Fix |
|-------|-----|
| "Only N games found" | Run before Thursday kickoff |
| "Could not match team XYZ" | Use 3-letter abbreviations (BAL, BUF) |
| "Odds fetch failed" | Check `THE_ODDS_API_KEY` in `.env` |
| ESPN returns 403 | Do not set a browser-like `User-Agent`; ESPN blocks them |
| ESPN returns wrong season | Season is selected with `dates=`, not `year=` |
| "Could not find week dropdown" | `CBS_POOL_SLUG` is stale - grab this season's slug |
| Database publisher fails | Supabase project paused/deleted; fix creds or drop `database` from `ENABLED_PUBLISHERS` |

## Scheduling (macOS)

```bash
./scripts/schedule-task.sh    # Tuesdays 9 AM
./scripts/unschedule-task.sh  # Remove
```

Logs: `/tmp/cbs-sports-scraper/`
