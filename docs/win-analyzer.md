# Win Scenario Analyzer

Answer: “What needs to happen for me to win this week?” Calculates winning scenarios from Supabase picks/results and (optionally) weights them with odds pulled from simulator prediction files.

## Prerequisites
- Supabase tables `player_results` and `player_picks` populated (see `storage/providers/database.py` for schema). Use the CBS scraper + database publisher to load data.  
- `.env` with `SUPABASE_URL`, `SUPABASE_KEY`, and optional `USER_NAME`.  
- For weighted probabilities, have a recent `out/week_{n}_predictions_chalk_*.json` file from the strategy simulator; otherwise the analyzer falls back to 50/50.

## Run Commands
```bash
# Single player (uses USER_NAME if --player omitted)
python -m cbs_fantasy_tooling.analysis.win_scenario_analyzer --week 12 --player "Your Name"

# Detailed paths to victory (top 20 combos + TL;DR)
python -m cbs_fantasy_tooling.analysis.win_scenario_analyzer --week 12 --player "Your Name" --detailed

# Leaderboard for everyone in the table
python -m cbs_fantasy_tooling.analysis.win_scenario_analyzer --week 12 --all-players
```

## Reading the Output
- **Remaining Games**: shows your pending picks with confidence points.  
- **Winning Scenarios**: count of scenario combinations where you beat everyone (ties treated as losses).  
- **Win Probability**: weighted if odds are available, otherwise naive 50/50.  
- **Detailed mode**: prints a handful of winning combinations plus a TL;DR of games you must win/lose or that don’t matter.

## Common Pitfalls
- Empty probabilities: run the strategy simulator first to produce `week_*_predictions_chalk_*.json`.  
- Player not found: ensure Supabase records match the exact name and week.  
- Slow runs: if 14+ games are still pending, scenario count grows to 16k+; wait until some games finish or trust leaderboard mode.
