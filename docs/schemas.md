# Data Schemas

This document describes all data formats used in CBS Fantasy Tooling: JSON predictions, CSV outputs, and Supabase database tables.

## File Output Formats

### Strategy Summary CSV

**File**: `out/week_{N}_strategy_summary_{YYYYMMDD}_{HHMMSS}.csv`

Contains Monte Carlo simulation results comparing all strategies.

**Columns:**
```
strategy                 str    Strategy name (e.g., "Chalk-MaxPoints")
expected_total_points    float  Average total points across simulations (includes bonuses)
expected_wins            float  Average number of correct picks
expected_base_points     float  Average points without bonuses
P(get_Most_Wins_bonus)   float  Probability of winning/tying Most Wins bonus (0-1)
P(get_Most_Points_bonus) float  Probability of winning/tying Most Points bonus (0-1)
p10                      float  10th percentile total points
p25                      float  25th percentile total points
p50                      float  50th percentile (median) total points
p75                      float  75th percentile total points
p90                      float  90th percentile total points
```

**Example:**
```csv
strategy,expected_total_points,expected_wins,P(get_Most_Wins_bonus),P(get_Most_Points_bonus)
Chalk-MaxPoints,97.36,10.82,0.215,0.187
Random-MidShuffle,96.93,10.78,0.198,0.171
Slight-Contrarian,95.03,10.52,0.156,0.142
```

### Pick'em Results CSV

**File**: `out/week_{N}_pickem_results_{YYYYMMDD}_{HHMMSS}.csv`

Raw scraping output from CBS Sports.

**Columns:**
```
Name     str   Player name
Points   int   Total points for the week
Wins     int   Number of correct picks
Losses   int   Number of incorrect picks
```

**Example:**
```csv
Name,Points,Wins,Losses
Alice Johnson,128,15,1
Bob Smith,125,14,2
```

---

## JSON Prediction Files

### Prediction File Structure

**File**: `out/week_{N}_predictions_{strategy_code}_{YYYYMMDD}_{HHMMSS}.json`

**Strategy Codes:**
- `chalk` - Chalk-MaxPoints
- `slight` - Slight-Contrarian
- `aggress` - Aggressive-Contrarian
- `shuffle` - Random-MidShuffle
- `user` - Custom user picks

**Schema:**
```json
{
  "metadata": {
    "strategy": "Random-MidShuffle",
    "week": 2,
    "generated_at": "2025-09-10T09:57:05.612402",
    "total_games": 16,
    "simulator_version": "v2"
  },
  "games": [
    {
      "game_id": "unique_game_identifier",
      "away_team": "Buffalo Bills",
      "home_team": "Miami Dolphins",
      "favorite": "Buffalo Bills",
      "dog": "Miami Dolphins",
      "favorite_prob": 0.8587,
      "commence_time": "2025-09-14T17:01:00Z",
      "prediction": {
        "pick_team": "Buffalo Bills",
        "pick_is_favorite": true,
        "confidence_level": 16,
        "confidence_rank": 1
      }
    }
  ]
}
```

**Field Definitions:**

**metadata:**
- `strategy` (str): Strategy name
- `week` (int): NFL week number
- `generated_at` (str): ISO 8601 timestamp
- `total_games` (int): Number of games in this week
- `simulator_version` (str): Version identifier

**games[] (ordered by confidence_rank):**
- `game_id` (str): Unique identifier for the game
- `away_team` (str): Full away team name
- `home_team` (str): Full home team name
- `favorite` (str): Team name of the favorite
- `dog` (str): Team name of the underdog
- `favorite_prob` (float): Win probability of favorite (0-1)
- `commence_time` (str): ISO 8601 game start time
- **prediction:**
  - `pick_team` (str): Team name of your pick
  - `pick_is_favorite` (bool): Whether you picked the favorite
  - `confidence_level` (int): Points assigned (1-16)
  - `confidence_rank` (int): Rank of this pick (1=highest confidence)

**Notes:**
- Games are sorted by `confidence_rank` (1 = highest confidence)
- All timestamps are UTC (ISO 8601 format)
- Probabilities are de-vigged using median consensus

---

## Supabase Database Schema

### Table: `player_results`

Stores weekly results for each player with season tracking.

**Columns:**
```sql
id                  BIGSERIAL PRIMARY KEY
season              INT NOT NULL           -- NFL season year (e.g., 2025)
week_number         INT NOT NULL           -- NFL week number (1-18)
player_name         TEXT NOT NULL          -- Player's name
points              INT NOT NULL           -- Total points for the week
wins                INT NOT NULL           -- Number of correct picks
losses              INT NOT NULL           -- Number of incorrect picks
rank                INT                    -- Current rank by points (1st, 2nd, etc.)
points_from_leader  INT                    -- Gap to leader
created_at          TIMESTAMPTZ DEFAULT NOW()
updated_at          TIMESTAMPTZ DEFAULT NOW()

UNIQUE(season, week_number, player_name)
```

**Indexes:**
- `idx_player_results_season_week` on `(season, week_number)`
- `idx_player_results_rank` on `(season, week_number, rank)`

**Example Query:**
```sql
SELECT player_name, points, wins, rank, points_from_leader
FROM player_results
WHERE season = 2025 AND week_number = 14
ORDER BY rank;
```

### Table: `player_picks`

Stores individual picks for each player.

**Columns:**
```sql
id                  BIGSERIAL PRIMARY KEY
season              INT NOT NULL           -- NFL season year
week_number         INT NOT NULL           -- NFL week number
player_name         TEXT NOT NULL          -- Player's name
team                TEXT NOT NULL          -- Team abbreviation (e.g., "BUF", "KC")
confidence_points   INT NOT NULL           -- Confidence assigned (1-16)
is_correct          BOOLEAN                -- Whether pick was correct (nullable)
opponent_team       TEXT                   -- Opponent team for context
game_time           TIMESTAMPTZ            -- Scheduled game time
created_at          TIMESTAMPTZ DEFAULT NOW()
updated_at          TIMESTAMPTZ DEFAULT NOW()

UNIQUE(season, week_number, player_name, team)
```

**Indexes:**
- `idx_player_picks_season_week` on `(season, week_number)`
- `idx_player_picks_player` on `(player_name, season, week_number)`

**Field Notes:**
- `is_correct`: `NULL` = game pending, `true` = won, `false` = lost
- `team`: 3-letter NFL abbreviations (BAL, BUF, KC, etc.)

**Example Query:**
```sql
SELECT player_name, team, confidence_points, is_correct
FROM player_picks
WHERE season = 2025 AND week_number = 14 AND player_name = 'Alice Johnson'
ORDER BY confidence_points DESC;
```

### Table: `game_status`

Tracks game importance and metadata for streaming overlays.

**Columns:**
```sql
id                  BIGSERIAL PRIMARY KEY
season              INT NOT NULL           -- NFL season year
week_number         INT NOT NULL           -- NFL week number
home_team           TEXT NOT NULL          -- Home team abbreviation
away_team           TEXT NOT NULL          -- Away team abbreviation
game_time           TIMESTAMPTZ NOT NULL   -- Scheduled game time
is_finished         BOOLEAN DEFAULT FALSE  -- Whether game is complete
home_score          INT                    -- Home team score (nullable)
away_score          INT                    -- Away team score (nullable)
importance_score    INT                    -- Calculated based on high-confidence picks
viewer_interest     INT                    -- Count of league members who picked this game
created_at          TIMESTAMPTZ DEFAULT NOW()
updated_at          TIMESTAMPTZ DEFAULT NOW()

UNIQUE(season, week_number, home_team, away_team)
```

**Indexes:**
- `idx_game_status_season_week` on `(season, week_number)`
- `idx_game_status_time` on `(game_time)`
- `idx_game_status_importance` on `(importance_score DESC)`

**Field Notes:**
- `importance_score`: Higher values = more critical games (based on pick confidence and standings)
- `viewer_interest`: Number of players with picks in this game
- **Note**: This table is defined but not yet populated. See `docs/streaming-tasks.md` for implementation plan.

**Example Query:**
```sql
-- Get top 3 most important games
SELECT home_team, away_team, game_time, importance_score
FROM game_status
WHERE season = 2025 AND week_number = 14 AND is_finished = false
ORDER BY importance_score DESC
LIMIT 3;
```

---

## ESPN API Response Format

Used by `game_results_fetcher.py` to fetch NFL game outcomes.

**Endpoint:**
```
http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week={week}&seasontype=2&dates={year}
```

**Response Structure:**
```json
{
  "events": [
    {
      "id": "401671729",
      "name": "Kansas City Chiefs at Buffalo Bills",
      "date": "2025-01-26T23:30Z",
      "competitions": [{
        "competitors": [
          {
            "team": {"abbreviation": "KC"},
            "homeAway": "away",
            "score": "24"
          },
          {
            "team": {"abbreviation": "BUF"},
            "homeAway": "home",
            "score": "27"
          }
        ],
        "status": {
          "type": {
            "completed": true
          }
        }
      }]
    }
  ]
}
```

**Extracted Fields:**
- `id`: Unique game identifier
- `name`: Game description (e.g., "Team A at Team B")
- `date`: Game start time (ISO 8601)
- `team.abbreviation`: 3-letter team code
- `homeAway`: "home" or "away"
- `score`: Final score (as string)
- `status.type.completed`: Boolean game completion status

---

## The Odds API Response Format

Used to fetch real-time NFL moneylines.

**Endpoint:**
```
https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds?apiKey={key}&regions=us&markets=h2h
```

**Response Structure:**
```json
{
  "id": "unique_game_id",
  "sport_key": "americanfootball_nfl",
  "sport_title": "NFL",
  "commence_time": "2025-09-14T17:00:00Z",
  "home_team": "Miami Dolphins",
  "away_team": "Buffalo Bills",
  "bookmakers": [
    {
      "key": "pinnacle",
      "title": "Pinnacle",
      "markets": [
        {
          "key": "h2h",
          "outcomes": [
            {"name": "Buffalo Bills", "price": -350},
            {"name": "Miami Dolphins", "price": 280}
          ]
        }
      ]
    }
  ]
}
```

**Extracted Fields:**
- `id`: Unique game identifier
- `commence_time`: Game start (ISO 8601)
- `home_team` / `away_team`: Full team names
- `bookmakers[].key`: Sportsbook identifier (e.g., "pinnacle", "circa")
- `bookmakers[].markets[].outcomes[].price`: American odds (e.g., -350, +280)

**Processing:**
- American odds converted to implied probabilities
- De-vigged using median consensus method
- Sharp books (Pinnacle, Circa) weighted 2x

---

## Team Name Mappings

**Common Abbreviations:**
```
ARI - Arizona Cardinals
ATL - Atlanta Falcons
BAL - Baltimore Ravens
BUF - Buffalo Bills
CAR - Carolina Panthers
CHI - Chicago Bears
CIN - Cincinnati Bengals
CLE - Cleveland Browns
DAL - Dallas Cowboys
DEN - Denver Broncos
DET - Detroit Lions
GB  - Green Bay Packers
HOU - Houston Texans
IND - Indianapolis Colts
JAC - Jacksonville Jaguars
KC  - Kansas City Chiefs
LAC - Los Angeles Chargers
LAR - Los Angeles Rams
LV  - Las Vegas Raiders
MIA - Miami Dolphins
MIN - Minnesota Vikings
NE  - New England Patriots
NO  - New Orleans Saints
NYG - New York Giants
NYJ - New York Jets
PHI - Philadelphia Eagles
PIT - Pittsburgh Steelers
SEA - Seattle Seahawks
SF  - San Francisco 49ers
TB  - Tampa Bay Buccaneers
TEN - Tennessee Titans
WAS - Washington Commanders
```

---

## Versioning

**Current Schema Versions:**
- Prediction JSON: `v2`
- Database Schema: Initial (no version tracking yet)
- CSV Format: Stable (no version field)

**Breaking Changes:**
- Adding fields: Non-breaking (consumers ignore unknown fields)
- Removing fields: Breaking (increment version)
- Changing field types: Breaking (increment version)

---

## Integration Examples

### Read Prediction File
```python
import json

with open('out/week_14_predictions_chalk_20251209_120000.json') as f:
    data = json.load(f)
    
week = data['metadata']['week']
games = data['games']

for game in games:
    print(f"{game['prediction']['pick_team']} - {game['prediction']['confidence_level']} pts")
```

### Query Supabase
```python
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Get current week leaders
results = supabase.table('player_results') \
    .select('player_name, points, rank') \
    .eq('season', 2025) \
    .eq('week_number', 14) \
    .order('rank') \
    .limit(5) \
    .execute()

for player in results.data:
    print(f"{player['rank']}. {player['player_name']} - {player['points']} pts")
```

### Parse ESPN Response
```python
import requests

url = f"http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week=14&seasontype=2&dates=2025"
response = requests.get(url).json()

for event in response['events']:
    home = next(c for c in event['competitions'][0]['competitors'] if c['homeAway'] == 'home')
    away = next(c for c in event['competitions'][0]['competitors'] if c['homeAway'] == 'away')
    
    print(f"{away['team']['abbreviation']} @ {home['team']['abbreviation']}")
    print(f"Score: {away['score']} - {home['score']}")
```

---

## Notes

- All timestamps are UTC
- Database uses PostgreSQL (via Supabase)
- JSON files use pretty-print formatting (indent=2)
- CSV files use standard RFC 4180 formatting
- File naming follows pattern: `{type}_week_{N}_{details}_{timestamp}.{ext}`
