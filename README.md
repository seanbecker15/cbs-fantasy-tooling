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

# For strategy analysis (recommended)
THE_ODDS_API_KEY=your_key  # theoddsapi.com - 500 free/mo
SEASON=2025
WEEK_ONE_START_DATE=2025-09-02

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

## Outputs

All results saved to `out/`:
- `out/week_{N}_game_results.json` - ESPN game slate with live/final scores
- `out/week_{N}_pickem_results.csv` - CBS pick'em leaderboard (tabular export)
- `out/week_{N}_pickem_results.json` - CBS pick'em leaderboard (structured JSON)
- `out/week_{N}_predictions_{strategy}.json` - Picks by strategy (`chalk`, `slight`, `aggress`, `shuffle`, `user` when provided)
- `out/week_{N}_strategy_summary.csv` - Expected points per strategy
- `out/week_{N}_aggressiveness_metrics.csv` - Aggressiveness + leverage metrics per player
- `out/week_{N}_player_aggressiveness_rankings.png` - Aggressiveness leaderboard visualization

## Common Issues

| Error | Fix |
|-------|-----|
| "Only N games found" | Run before Thursday kickoff |
| "Could not match team XYZ" | Use 3-letter abbreviations (BAL, BUF) |
| "Odds fetch failed" | Check `THE_ODDS_API_KEY` in `.env` |

## Scheduling (macOS)

```bash
./scripts/schedule-task.sh    # Tuesdays 9 AM
./scripts/unschedule-task.sh  # Remove
```

Logs: `/tmp/cbs-sports-scraper/`
