# Realtime Polling

Real-time ingestion runs background threads that continuously poll for Pick'em standings (CBS) and Game Outcomes (ESPN) until the program exits.

## Quick Start

```bash
python -m cbs_fantasy_tooling.main
# Select: Ingest Data → Pick'em/Game Outcomes → Real-Time → Enter week
```

**Requirements**: `.env` with `EMAIL`, `PASSWORD` (CBS), `THE_ODDS_API_KEY` (ESPN), optionally `SUPABASE_URL`/`SUPABASE_KEY` for database publishing.

## How It Works

- **Background threads**: Real-time mode spawns daemon threads (30s polling interval)
- **Main menu**: Returns immediately while threads run in background
- **Status**: Active thread count shown in menu
- **Exit**: All threads terminate when program exits

**Data Sources**:
- **Pick'em Results**: Scrapes CBS via Chrome, publishes changes to database only
- **Game Outcomes**: Polls ESPN API, publishes to all enabled publishers

## One-Off Ingestion

For single snapshots without polling, select "Once" mode instead of "Real-Time".

## Troubleshooting

- **"No changes detected"**: Normal when data unchanged between polls
- **Browser stays open**: Expected for CBS scraping during real-time mode
- **Missing database updates**: Verify Supabase credentials in `.env`
- **Rate limits**: Keep 30s default interval for CBS scraping
