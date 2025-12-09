# Data Sources

Where the toolkit pulls data and how to keep it healthy.

## CBS Sports (Pick'em Standings)
- **What**: Weekly standings + each player’s picks and confidence points.  
- **How**: Selenium scrape in `ingest/cbs_sports/scrape.py` (requires Chrome + credentials).  
- **Run**: `python -m cbs_fantasy_tooling.main` → Ingest Data → Pick'em Results. For realtime polling, see `docs/realtime.md`.  
- **Secrets**: `.env` `EMAIL`, `PASSWORD`.  
- **Output**: `PickemResults` to file/gmail/database publishers; optional Supabase tables `player_results`, `player_picks`.

## ESPN Scoreboard (Schedules/Scores)
- **What**: Game times, scores, completion status, winner/loser.  
- **How**: HTTP fetch in `ingest/espn/api.py` using the public scoreboard API.  
- **Run**: `python -m cbs_fantasy_tooling.main` → Ingest Data → Game Outcomes (once).  
- **Usage**: Feeds pick correctness, live standings, and future `game_status` overlay data. No API key required.

## The Odds API (Market Probabilities)
- **What**: Moneyline odds for upcoming games; converted to consensus win probabilities.  
- **How**: `ingest/the_odds_api/api.py` called by `analysis/monte_carlo.py`.  
- **Run**: Strategy simulator (see `docs/usage.md`).  
- **Secrets**: `.env` `THE_ODDS_API_KEY`. Free tier is 500 requests/mo; each sim call is 1 request.  
- **Output**: Probabilities saved into `out/week_{n}_predictions_{code}.json` for the simulator and consumed by the win analyzer for weighted probabilities.

## Failure Modes to Watch
- CBS DOM changes → rerun scraper in “Once” mode and inspect output before polling.  
- Odds API returns 0 games → check date window or run closer to kickoff.  
- ESPN timeouts → the fetcher already retries with backoff; rerun if empty.
