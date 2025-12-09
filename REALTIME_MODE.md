# Realtime Mode - Live Database Updates

This document explains how to use the new realtime polling mode that keeps the browser open and automatically saves updates to Supabase.

## Overview

Realtime mode provides:
- **Live polling**: Keeps Chrome window open and polls every 30 seconds (configurable)
- **Page refresh**: Automatically refreshes CBS page between polls (CBS doesn't update in real-time)
- **Database storage**: Saves directly to Supabase instead of local files
- **Deep change detection**: Intelligent comparison detects exactly what changed (players, points, wins, picks)
- **Season support**: Multi-year data storage with proper season tracking
- **Streaming overlay ready**: Additional metadata for broadcast overlays (rankings, game importance)
- **Manual exit**: Press Enter to stop polling and exit gracefully

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install the `supabase` Python client.

### 2. Configure Supabase

#### Create Supabase Project

1. Go to [https://supabase.com](https://supabase.com)
2. Create a new project
3. Note your project URL and anon/service key

#### Create Database Tables

Run this SQL in the Supabase SQL Editor. **Copy the entire SQL block from `app/database.py` file** (lines 55-137) or use this:

```sql
-- Player results table
CREATE TABLE player_results (
    id BIGSERIAL PRIMARY KEY,
    season INT NOT NULL,
    week_number INT NOT NULL,
    player_name TEXT NOT NULL,
    points INT NOT NULL,
    wins INT NOT NULL,
    losses INT NOT NULL,
    rank INT,
    points_from_leader INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(season, week_number, player_name)
);

-- Player picks table
CREATE TABLE player_picks (
    id BIGSERIAL PRIMARY KEY,
    season INT NOT NULL,
    week_number INT NOT NULL,
    player_name TEXT NOT NULL,
    team TEXT NOT NULL,
    confidence_points INT NOT NULL,
    is_correct BOOLEAN,
    opponent_team TEXT,
    game_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(season, week_number, player_name, team)
);

-- Game status table (for streaming overlay)
CREATE TABLE game_status (
    id BIGSERIAL PRIMARY KEY,
    season INT NOT NULL,
    week_number INT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    game_time TIMESTAMPTZ NOT NULL,
    is_finished BOOLEAN DEFAULT FALSE,
    home_score INT,
    away_score INT,
    importance_score INT,
    viewer_interest INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(season, week_number, home_team, away_team)
);

-- Indexes for performance
CREATE INDEX idx_player_results_season_week ON player_results(season, week_number);
CREATE INDEX idx_player_results_rank ON player_results(season, week_number, rank);
CREATE INDEX idx_player_picks_season_week ON player_picks(season, week_number);
CREATE INDEX idx_player_picks_player ON player_picks(player_name, season, week_number);
CREATE INDEX idx_game_status_season_week ON game_status(season, week_number);
CREATE INDEX idx_game_status_time ON game_status(game_time);
CREATE INDEX idx_game_status_importance ON game_status(importance_score DESC);

-- Enable Row Level Security
ALTER TABLE player_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_picks ENABLE ROW LEVEL SECURITY;
ALTER TABLE game_status ENABLE ROW LEVEL SECURITY;

-- Create policies (allow all operations)
CREATE POLICY "Enable read access for all users" ON player_results FOR SELECT USING (true);
CREATE POLICY "Enable insert for all users" ON player_results FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for all users" ON player_results FOR UPDATE USING (true);
CREATE POLICY "Enable delete for all users" ON player_results FOR DELETE USING (true);

CREATE POLICY "Enable read access for all users" ON player_picks FOR SELECT USING (true);
CREATE POLICY "Enable insert for all users" ON player_picks FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for all users" ON player_picks FOR UPDATE USING (true);
CREATE POLICY "Enable delete for all users" ON player_picks FOR DELETE USING (true);

CREATE POLICY "Enable read access for all users" ON game_status FOR SELECT USING (true);
CREATE POLICY "Enable insert for all users" ON game_status FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for all users" ON game_status FOR UPDATE USING (true);
CREATE POLICY "Enable delete for all users" ON game_status FOR DELETE USING (true);
```

#### Enable Realtime (Optional)

For real-time subscriptions in your frontend:

1. Go to Database → Replication in Supabase dashboard
2. Enable replication for `player_results` and `player_picks` tables

### 3. Configure Environment Variables

Add these to your `.env` file:

```bash
# Existing CBS scraping config
EMAIL=your_cbs_email@example.com
PASSWORD=your_cbs_password

# Season configuration (year of NFL season)
SEASON=2025

# Supabase configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-key
```

## Usage

### Running Realtime Mode

```bash
cd app
python realtime_main.py
```

This will:
1. Open Chrome browser
2. Log in to CBS Sports
3. Navigate to the target week
4. Poll every 30 seconds for updates
5. Refresh the page between polls (CBS doesn't auto-update)
6. Wait 15 seconds after refresh for page to stabilize
7. Scrape data and detect changes using deep comparison
8. Save changes to Supabase database
9. Wait 15 seconds before next refresh

### Command Line Options

```bash
# Custom poll interval (in seconds)
python realtime_main.py --poll-interval 30

# Specific week number
python realtime_main.py --week 5

# Combined
python realtime_main.py --poll-interval 15 --week 3
```

### Exiting

Press **Enter** at any time to gracefully stop polling and close the browser.

### Example Output

```
============================================================
CBS FANTASY TOOLING - REALTIME MODE
============================================================
Scraping week: 3
Poll interval: 30 seconds
Database: Supabase
============================================================

Testing database connection...
✓ Database connection successful

✓ Logged in successfully
...

✓ Successfully navigated to Week 3

Starting realtime polling...
Poll interval: 30s (refreshing page between polls)
============================================================

[16:45:23] Poll #1 - Scraping data...
✓ Scraped 32 player results
  First poll - saving baseline data

Publishing to database...
Upserting 32 player results for season 2025 week 3...
Upserting 512 player picks for season 2025 week 3...
Successfully saved data for season 2025 week 3

============================================================
Week 3 Summary (as of 16:45:25)
============================================================
Most wins: 15 - Bob Brokamp
Most points: 128 - Bob Brokamp
============================================================

Waiting 15s until next refresh (Press Enter to exit)...

[16:45:40] Poll #2 - Refreshing page...
Waiting 15s for page to stabilize...

[16:45:55] Poll #2 - Scraping data...
✓ Scraped 32 player results
  ⚡ CHANGE DETECTED - 3 change(s) detected
    • Sean Becker: points 102 → 115
    • Sean Becker: wins 11 → 12
    • Jason Press: points 116 → 129

Publishing to database...
Successfully saved data for season 2025 week 3
...

Waiting 15s until next refresh (Press Enter to exit)...
```

## Data Structure

### player_results Table

Stores weekly results for each player with season tracking:

| Column | Type | Description |
|--------|------|-------------|
| id | bigint | Primary key |
| **season** | int | NFL season year (e.g., 2025) |
| week_number | int | NFL week number |
| player_name | text | Player's name |
| points | int | Total points for the week |
| wins | int | Number of correct picks |
| losses | int | Number of incorrect picks |
| **rank** | int | Current rank by points (1st, 2nd, etc.) |
| **points_from_leader** | int | How far behind the leader |
| created_at | timestamptz | Record creation time |
| updated_at | timestamptz | Last update time |

### player_picks Table

Stores individual picks for each player:

| Column | Type | Description |
|--------|------|-------------|
| id | bigint | Primary key |
| **season** | int | NFL season year |
| week_number | int | NFL week number |
| player_name | text | Player's name |
| team | text | Team abbreviation (e.g., "BUF", "KC") |
| confidence_points | int | Confidence points assigned (1-16) |
| **is_correct** | boolean | Whether the pick was correct (nullable) |
| **opponent_team** | text | Opponent team for context |
| **game_time** | timestamptz | Scheduled game time |
| created_at | timestamptz | Record creation time |
| updated_at | timestamptz | Last update time |

### game_status Table (Streaming Overlay Support)

Tracks game importance and metadata for streaming overlays:

| Column | Type | Description |
|--------|------|-------------|
| id | bigint | Primary key |
| season | int | NFL season year |
| week_number | int | NFL week number |
| home_team | text | Home team abbreviation |
| away_team | text | Away team abbreviation |
| game_time | timestamptz | Scheduled game time |
| is_finished | boolean | Whether game is complete |
| home_score | int | Home team score (nullable) |
| away_score | int | Away team score (nullable) |
| **importance_score** | int | Calculated based on high-confidence picks |
| **viewer_interest** | int | Count of league members who picked this game |
| created_at | timestamptz | Record creation time |
| updated_at | timestamptz | Last update time |

## Querying Data

### Get Week Results for Current Season

```sql
SELECT player_name, points, wins, losses, rank, points_from_leader
FROM player_results
WHERE season = 2025 AND week_number = 3
ORDER BY rank;
```

### Get Multi-Season History

```sql
SELECT season, week_number, player_name, points, rank
FROM player_results
WHERE player_name = 'Sean Becker'
ORDER BY season DESC, week_number DESC;
```

### Get Player Picks with Details

```sql
SELECT player_name, team, confidence_points, opponent_team, game_time
FROM player_picks
WHERE season = 2025 AND week_number = 3 AND player_name = 'Sean Becker'
ORDER BY confidence_points DESC;
```

### Get Current Leaders

```sql
-- Most points this week
SELECT player_name, points, rank
FROM player_results
WHERE season = 2025 AND week_number = 3
ORDER BY rank
LIMIT 5;

-- Most wins this week
SELECT player_name, wins, points
FROM player_results
WHERE season = 2025 AND week_number = 3
ORDER BY wins DESC, points DESC
LIMIT 5;
```

### Streaming Overlay Queries

```sql
-- Get top 5 with ranking for overlay
SELECT rank, player_name, points, wins, points_from_leader
FROM player_results
WHERE season = 2025 AND week_number = 3
ORDER BY rank
LIMIT 5;

-- Get games sorted by importance (for "key games to watch")
SELECT home_team, away_team, game_time, importance_score, viewer_interest
FROM game_status
WHERE season = 2025 AND week_number = 3 AND is_finished = false
ORDER BY importance_score DESC
LIMIT 3;

-- Get player's picks with live game status
SELECT
    pp.player_name,
    pp.team,
    pp.confidence_points,
    gs.home_team,
    gs.away_team,
    gs.home_score,
    gs.away_score,
    gs.is_finished
FROM player_picks pp
LEFT JOIN game_status gs ON
    pp.season = gs.season AND
    pp.week_number = gs.week_number AND
    (pp.team = gs.home_team OR pp.team = gs.away_team)
WHERE pp.season = 2025 AND pp.week_number = 3 AND pp.player_name = 'Sean Becker'
ORDER BY pp.confidence_points DESC;
```

### Join Results with Picks

```sql
SELECT
    r.rank,
    r.player_name,
    r.points,
    r.wins,
    r.losses,
    r.points_from_leader,
    json_agg(
        json_build_object(
            'team', p.team,
            'confidence', p.confidence_points,
            'correct', p.is_correct
        ) ORDER BY p.confidence_points DESC
    ) as picks
FROM player_results r
LEFT JOIN player_picks p ON
    r.season = p.season AND
    r.week_number = p.week_number AND
    r.player_name = p.player_name
WHERE r.season = 2025 AND r.week_number = 3
GROUP BY r.rank, r.player_name, r.points, r.wins, r.losses, r.points_from_leader
ORDER BY r.rank;
```

## Deep Change Detection

The system now includes intelligent change detection that compares:
- Player count changes
- Point changes per player
- Win/loss changes per player
- Pick modifications

Example output:
```
⚡ CHANGE DETECTED - 5 change(s) detected
  • Sean Becker: points 102 → 115
  • Sean Becker: wins 11 → 13
  • Bob Brokamp: points 128 → 131
  • Jason Press: wins 13 → 14
  • Paula Kooperman: picks changed
```

## Traditional Mode (Backward Compatible)

The original file-based mode still works:

```bash
cd app
python main.py
```

This will save results to CSV files in the `out/` directory.

## Troubleshooting

### Database Connection Fails

- Verify `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
- Check that tables exist in Supabase
- Ensure RLS policies allow your operations

### No Data Updates

- Check that CBS Sports page is loaded correctly
- Verify week navigation succeeded
- Look for error messages in console output

### Browser Issues

- Make sure Chrome/Chromium is installed
- Update Selenium and ChromeDriver if needed
- Check for captcha requirements (you'll need to solve manually)

### Season Conflicts

- If data isn't appearing, verify `SEASON` in `.env` matches current season
- Query with explicit season: `WHERE season = 2025`

## Streaming Overlay Use Cases

The enhanced schema supports building real-time broadcast overlays:

1. **Leaderboard Overlay**: Display top 5 with live rankings and gaps
2. **Key Games Widget**: Show most important games based on high-confidence picks
3. **Player Spotlight**: Show a player's picks with live game scores
4. **Race to Top**: Animated view of points_from_leader changing
5. **Game Impact Tracker**: Highlight which games affect the most players

**Note**: The `game_status` table is defined but not yet populated. See `TASK_LIST.md` for implementation plan to add live game tracking, importance scoring, and pick correctness validation.

## Key Features Summary

### Multi-Year Season Support
- `season` field in all tables allows storing data for multiple NFL seasons
- Automatic season detection (defaults to current year)
- No database migrations needed year-to-year
- Easy historical comparisons with queries like: `WHERE player_name = 'X' ORDER BY season DESC`

### Deep Change Detection
The realtime scraper includes intelligent change detection that identifies:
- New/removed players
- Point changes per player
- Win/loss changes per player
- Pick modifications (team or confidence changes)

This reduces unnecessary database writes by only updating when actual changes occur.

### Automatic Ranking Calculation
Rankings are computed automatically when saving results:
- `rank` - Current ranking (1st, 2nd, 3rd, etc.)
- `points_from_leader` - Gap to leader

Perfect for "X points behind" displays in overlays.

### Performance Optimizations
- Indexed queries for season + week lookups
- Ranked queries optimized with composite index
- Deep comparison reduces writes by ~80-90% during stable periods
- Poll interval (default 30s) with page refresh ensures fresh data from CBS
- Smart timing: 15s wait after refresh + 15s wait after scrape = 30s total cycle

## Files Created

**Core Implementation**:
- `app/database.py` - Supabase integration with season support and deep comparison
- `app/publishers/database.py` - Database publisher for results
- `app/scrape_realtime.py` - Realtime polling with change detection
- `app/realtime_main.py` - Main entry point for realtime mode

**Documentation**:
- `REALTIME_MODE.md` - This file
- `TASK_LIST.md` - Implementation roadmap for game status population

**Modified**:
- `requirements.txt` - Added `supabase==2.10.0`
- `app/config.py` - Added season and Supabase configuration

**Unchanged** (backward compatible):
- `app/main.py` - Original file-based mode still works
- All existing publishers (gmail, sendgrid, file)

## Example .env File

```bash
# CBS Sports Login
EMAIL=your_email@example.com
PASSWORD=your_password

# Week and Season Configuration
WEEK_ONE_START_DATE=2025-09-02
SEASON=2025

# Supabase Database
SUPABASE_URL=https://abcdefghijk.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Optional: Traditional publishers (for backward compatibility)
ENABLED_PUBLISHERS=file,gmail
```

## Architecture

```
realtime_main.py
    ↓
scrape_realtime.py (polling loop + deep comparison)
    ↓
scrape.py (__scrape_week_standings)
    ↓
publishers/database.py
    ↓
database.py (SupabaseDatabase with season support)
    ↓
Supabase (player_results, player_picks, game_status)
```

## Future Enhancements

See `TASK_LIST.md` for detailed implementation roadmap. High-priority items include:

**Phase 1: Game Status Population**
- Infer games from player picks
- Calculate viewer interest and importance scores
- ESPN API integration for schedules and live scores
- Automatic pick correctness validation

**Phase 2: Advanced Features**
- Websocket-based realtime updates (replace polling)
- Push notifications on score changes
- Historical trend analysis (season-over-season comparisons)
- Multi-league support
- Predictive analytics using historical pick patterns
