# Schemas & File Formats

## Local Output Files
- **`week_{n}_pickem_results.csv`**  
  - Columns: `Name, Points, Wins, Losses`.  
  - Source: CBS scrape.
- **`week_{n}_pickem_results.json`**  
  - Keys: `timestamp`, `week_number`, `max_wins`, `max_points`, `results[]` where each result has `name`, `points`, `wins`, `losses`, `picks[]` (team/confidence when available).
- **`week_{n}_game_results.json`**  
  - List of games with `game_id`, `game_time`, `season`, `week_number`, `home_team`, `away_team`, `home_score`, `away_score`, `is_finished`, `status_text`, `winning_team`, `losing_team`.  
  - Source: ESPN scoreboard.
- **`week_{n}_strategy_summary.csv`**  
  - One row per strategy: `strategy, expected_total_points, expected_wins, ...` (Monte Carlo outputs).
- **`week_{n}_predictions_{code}.json`** (`chalk`, `slight`, `aggress`, `shuffle`, `user`)  
  - `metadata`: strategy, week, generated_at, total_games.  
  - `games[]`: `away_team`, `home_team`, `favorite`, `dog`, `favorite_prob`, `commence_time`, `prediction` (`pick_team`, `pick_is_favorite`, `confidence_level`, `confidence_rank`).

## Supabase Tables (see `storage/providers/database.py`)
- **player_results**: `season`, `week_number`, `player_name`, `points`, `wins`, `losses`, `rank`, `points_from_leader`, timestamps.  
- **player_picks**: `season`, `week_number`, `player_name`, `team`, `confidence_points`, `is_correct`, `opponent_team`, `game_time`, timestamps.  
- **game_status** (for overlays): `season`, `week_number`, `home_team`, `away_team`, `game_time`, `is_finished`, `home_score`, `away_score`, `importance_score`, `viewer_interest`.

## Naming Conventions
- All files live under `out/`.  
- Week numbers are 1-based; season defaults to current year unless overridden in `.env` (`SEASON`).
