# NFL Confidence Pool Simulator - Competitive Intelligence System

## Overview

Data-driven competitive intelligence platform for NFL confidence pool strategy optimization. Analyzes historical competitor behavior to provide optimal weekly pick recommendations.

**Current Status**: Phase 2 Complete (October 3, 2025)
- ✅ 4 weeks of historical data (Weeks 1-4, 2025 season)
- ✅ 32 players analyzed (2048 total picks)
- ✅ Competitor strategy profiles built
- ✅ Real field composition identified (17 Chalk, 14 Slight, 1 Aggressive)
- ✅ **NEW**: Simulator integrated with actual field composition
- ✅ **NEW**: Contrarian opportunity ranking engine operational

---

## Quick Start

### 1. Load and Analyze Competitor Data

```python
from data_loader import load_competitor_data
from data_enrichment import full_enrichment_pipeline
from competitor_classifier import build_player_profiles, analyze_league_composition

# Load raw picks data
picks_df, players_df, weekly_stats_df = load_competitor_data()

# Enrich with game outcomes
enriched_picks, favorites = full_enrichment_pipeline(picks_df)

# Build player strategy profiles
profiles = build_player_profiles(enriched_picks)
composition = analyze_league_composition(profiles)

print(f"League: {composition['total_players']} players")
print(f"Chalk: {composition['strategy_counts']['Chalk-MaxPoints']}")
print(f"Contrarian rate: {composition['avg_contrarian_rate']:.1%}")
```

### 2. Fetch Game Results

```python
from game_results_fetcher import fetch_game_results

# Fetch results for specific weeks
results = fetch_game_results(weeks=[5, 6], season=2025, save_json=True)

# Results saved to: out/week_5_game_results.json, out/week_6_game_results.json
```

### 3. Analyze Field Consensus

```python
from data_loader import CompetitorDataLoader

loader = CompetitorDataLoader()
loader.load_all_weeks()
loader.build_picks_dataframe()

# Get consensus for Week 4
consensus = loader.get_field_consensus(week=4)
print(consensus.head(10))

# Output:
#  team  pick_count  avg_confidence  total_confidence  pick_percentage
#   BUF          32       15.781250               505          1.00000  ← 100% consensus
#   DET          32       14.375000               460          1.00000
#   LAC          32       12.843750               411          1.00000
```

---

## Module Documentation

### `data_loader.py` - Data Ingestion Pipeline

**Purpose**: Loads and normalizes competitor pick data from CBS Sports scraper JSON output.

**Key Classes:**
- `CompetitorDataLoader` - Main data loading interface

**Key Functions:**
```python
load_competitor_data(data_dir="out") -> Tuple[picks_df, players_df, weekly_stats_df]
```

**Input Files**: `out/week_{N}_results_{YYYYMMDD}_{HHMMSS}.json`

**Output DataFrames:**

1. **picks_df** (2048 rows = 32 players × 16 games × 4 weeks)
```python
Columns:
- player_name: str
- week: int (1-18)
- team: str (3-letter abbreviation)
- confidence: int (1-16)
- total_player_points: int
- total_player_wins: int
- total_player_losses: int
```

2. **players_df** (32 rows = 1 per player)
```python
Columns:
- player_name: str
- weeks_played: int
- total_points: int
- total_wins: int
- avg_points_per_week: float
- bonus_wins_most_points: int
- bonus_wins_most_wins: int
```

3. **weekly_stats_df** (4 rows = 1 per week)
```python
Columns:
- week: int
- num_players: int
- max_wins: int
- max_points: int
- avg_wins: float
- avg_points: float
```

**Usage Example:**
```python
from data_loader import CompetitorDataLoader

loader = CompetitorDataLoader(data_dir="out")
picks_df, players_df, weekly_stats_df = loader.load_and_build_all()

# Get specific player's picks
user_picks = loader.get_player_picks("User Name", week=4)

# Get field consensus for a week
consensus = loader.get_field_consensus(week=4)
```

---

### `game_results_fetcher.py` - ESPN API Integration

**Purpose**: Fetches NFL game results from ESPN API for historical analysis.

**Key Classes:**
- `NFLGameResultsFetcher` - ESPN API client

**Key Functions:**
```python
fetch_game_results(weeks: List[int], season: int = 2025, save_json: bool = True)
```

**Output Files**: `out/week_{N}_game_results.json`

**Output Format:**
```json
{
  "week": 4,
  "season": 2025,
  "num_games": 16,
  "games": [
    {
      "game_id": "401772740",
      "week": 4,
      "away_team": "NO",
      "home_team": "BUF",
      "away_score": 19,
      "home_score": 31,
      "winner": "BUF",
      "loser": "NO",
      "completed": true,
      "game_date": "2025-09-28T17:00Z"
    }
  ]
}
```

**Team Abbreviation Mapping:**
- Normalizes ESPN abbreviations to CBS/standard format
- Examples: `ARZ` → `ARI`, `GNB` → `GB`, `KAN` → `KC`

**Usage Example:**
```python
from game_results_fetcher import fetch_game_results

# Fetch Weeks 1-4
results = fetch_game_results(weeks=[1, 2, 3, 4], season=2025)

# Fetch specific week
from game_results_fetcher import NFLGameResultsFetcher
fetcher = NFLGameResultsFetcher(season=2025)
week5_games = fetcher.fetch_week_results(week=5)
```

---

### `data_enrichment.py` - Outcome Enrichment Pipeline

**Purpose**: Enriches picks with game outcomes, identifies favorites/underdogs, marks contrarian picks.

**Key Functions:**

1. **`enrich_picks_with_outcomes(picks_df, game_results_df)`**
   - Matches picks to game results
   - Adds win/loss outcomes
   - Calculates points earned

2. **`calculate_field_favorites(picks_df, game_results_df, threshold=0.50)`**
   - Determines favorite by field consensus
   - Returns favorite/underdog for each game

3. **`mark_contrarian_picks(picks_df, favorites_df)`**
   - Tags picks that chose the underdog
   - Adds field percentage for each pick

4. **`full_enrichment_pipeline(picks_df, data_dir="out")`**
   - Complete workflow: outcomes → favorites → contrarian marking
   - Returns enriched picks and favorites DataFrames

**Enriched Picks DataFrame:**
```python
Additional columns added:
- won: bool (True if pick won)
- points_earned: int (confidence if won, else 0)
- is_contrarian: bool (True if picked underdog)
- field_percentage: float (% of field that picked same team)
- opponent: str (opponent team)
- home_away: str ('home' or 'away')
- final_score: str (e.g., "31-19")
```

**Usage Example:**
```python
from data_loader import load_competitor_data
from data_enrichment import full_enrichment_pipeline

picks_df, _, _ = load_competitor_data()
enriched_picks, favorites = full_enrichment_pipeline(picks_df)

# Analyze contrarian performance
week4 = enriched_picks[enriched_picks['week'] == 4]
contrarian_stats = week4.groupby('is_contrarian').agg({
    'won': ['count', 'sum', 'mean'],
    'points_earned': 'sum'
})
```

**Validation Results:**
- Total picks: 2048
- Winning picks: 1405 (68.6%)
- Contrarian picks: 219 (10.7%)
- Contrarian win rate: 39.6% (Week 4)
- Chalk win rate: 62.7% (Week 4)

---

### `competitor_classifier.py` - Strategy Classification System

**Purpose**: Classifies each competitor's decision-making pattern for field simulation.

**Strategy Types:**
```python
class StrategyType(Enum):
    CHALK = "Chalk-MaxPoints"              # 0-10% contrarian rate
    SLIGHT_CONTRARIAN = "Slight-Contrarian"  # 10-25% contrarian rate
    AGGRESSIVE_CONTRARIAN = "Aggressive-Contrarian"  # 25%+ contrarian rate
```

**Key Functions:**

1. **`classify_player_strategy(player_picks)`**
   - Analyzes contrarian rate
   - Returns StrategyType classification

2. **`calculate_player_metrics(player_picks)`**
   - Comprehensive player statistics
   - Returns metrics dictionary

3. **`build_player_profiles(enriched_picks_df)`**
   - Builds profiles for all players
   - Returns list of profile dictionaries

4. **`analyze_league_composition(profiles)`**
   - League-level statistics
   - Strategy distribution analysis

**Player Profile Output:**
```python
{
  'player_name': 'Player A',
  'strategy': StrategyType.SLIGHT_CONTRARIAN,
  'contrarian_rate': 0.188,           # 18.8% underdog picks
  'win_rate': 0.734,                  # 73.4% picks correct
  'avg_points_per_week': 107.8,
  'avg_confidence_on_contrarian': 8.2,
  'consistency_score': 0.92,          # 1.0 = perfectly consistent
  'weeks_played': 4,
  'total_picks': 64
}
```

**League Composition Results:**
```python
{
  'total_players': 32,
  'strategy_counts': {
    'Chalk-MaxPoints': 17,          # 53.1%
    'Slight-Contrarian': 14,        # 43.8%
    'Aggressive-Contrarian': 1      # 3.1%
  },
  'avg_contrarian_rate': 0.107,     # 10.7% league-wide
  'avg_win_rate': 0.686             # 68.6% league-wide
}
```

**Usage Example:**
```python
from data_enrichment import full_enrichment_pipeline
from competitor_classifier import build_player_profiles, get_top_performers

enriched_picks, _ = full_enrichment_pipeline(picks_df)
profiles = build_player_profiles(enriched_picks)

# Get top 10 performers
top10 = get_top_performers(profiles, n=10)

# Analyze by strategy type
from competitor_classifier import get_players_by_strategy, StrategyType
chalk_players = get_players_by_strategy(profiles, StrategyType.CHALK)
print(f"Chalk players avg: {np.mean([p['avg_points_per_week'] for p in chalk_players]):.1f} pts/wk")
```

**Testing:**
- ✅ TDD approach with `test_competitor_classifier.py`
- ✅ 5/5 tests passing
- ✅ Validated with 4 weeks of real data

---

### `field_adapter.py` - Real Field Composition Adapter

**Purpose**: Adapts real competitor data to simulator's STRATEGY_MIX format, replacing theoretical assumptions.

**Key Functions:**

1. **`get_actual_field_composition(data_dir="out", exclude_user=None)`**
   - Returns actual strategy distribution from historical data
   - Compatible with main.py STRATEGY_MIX format

2. **`get_field_statistics(data_dir="out")`**
   - Comprehensive field statistics
   - Returns total players, distribution, averages, top performers

3. **`compare_theoretical_vs_actual()`**
   - Side-by-side comparison
   - Shows differences between assumption and reality

**Integration with main.py:**
```python
# In main.py (lines 73-77)
from field_adapter import get_actual_field_composition

STRATEGY_MIX = get_actual_field_composition()
# Returns: {'Chalk-MaxPoints': 17, 'Slight-Contrarian': 14, 'Aggressive-Contrarian': 1}
```

**Actual vs Theoretical:**
```
Strategy                  Theoretical  Actual  Difference
Chalk-MaxPoints                    16      17 +         1
Slight-Contrarian                  10      14 +         4
Aggressive-Contrarian               5       1          -4
```

**Usage Example:**
```python
from field_adapter import get_actual_field_composition, compare_theoretical_vs_actual

# Get actual field for simulation
actual_field = get_actual_field_composition()

# Analyze differences
comparison = compare_theoretical_vs_actual()
print(f"League is {comparison['total_actual']} players")
print(f"Differences: {comparison['differences']}")
```

---

### `contrarian_analyzer.py` - Contrarian Opportunity Ranking

**Purpose**: Identifies optimal contrarian plays based on field consensus, upset probability, and expected value.

**Key Classes:**
```python
@dataclass
class ContrarianOpportunity:
    game_id: str
    favorite: str
    underdog: str
    field_consensus: float      # % picking favorite
    underdog_win_prob: float    # Probability underdog wins
    expected_value_gain: float  # Expected point advantage
    risk_level: str             # "Low", "Medium", "High"
    recommended: bool
```

**Key Functions:**

1. **`find_contrarian_opportunities_from_data(...)`**
   - Analyzes historical data for contrarian plays
   - Filters by consensus threshold and upset probability
   - Returns ranked list of opportunities

2. **`calculate_contrarian_value(field_consensus, underdog_prob, avg_confidence)`**
   - Expected value calculation
   - Weights by probability and confidence

3. **`analyze_contrarian_performance_history(...)`**
   - Historical contrarian performance stats
   - Breakdown by field consensus level

**Historical Performance:**
```
Overall Statistics:
  Total contrarian picks: 219
  Contrarian win rate: 45.7%
  Contrarian avg points: 1.70
  Chalk win rate: 71.4%
  Chalk avg points: 6.89
```

**Week 4 Example:**
```
Underdog vs   Favorite Consensus    Upset Prob   EV Gain    Risk     Rec?
JAC      vs   SF       96.9%        100.0%       8.00       Low      ✓
PIT      vs   MIN      81.2%        100.0%       6.00       Low      ✓
```

**Usage Example:**
```python
from contrarian_analyzer import find_contrarian_opportunities_from_data

opportunities = find_contrarian_opportunities_from_data(
    enriched_picks,
    favorites,
    week=5,
    min_consensus=0.75,        # Only 75%+ consensus games
    min_upset_probability=0.35  # Underdog needs 35%+ chance
)

# Get recommendations
recommended = [o for o in opportunities if o.recommended]
for opp in recommended:
    print(f"Pick {opp.underdog} (EV: +{opp.expected_value_gain:.2f})")
```

**Risk Assessment:**
- **Low risk**: 45%+ underdog win probability (near toss-up)
- **Medium risk**: 35-45% underdog win probability
- **High risk**: <35% underdog win probability (not recommended)

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ INPUT DATA SOURCES                                              │
├─────────────────────────────────────────────────────────────────┤
│ 1. CBS Sports Scraper JSON (out/week_*_results_*.json)         │
│    - 32 players × 16 games × 4 weeks = 2048 picks              │
│                                                                 │
│ 2. ESPN API (via game_results_fetcher.py)                      │
│    - 16 games × 4 weeks = 64 games                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PIPELINE STAGE 1: DATA LOADING (data_loader.py)                │
├─────────────────────────────────────────────────────────────────┤
│ Input:  week_*_results_*.json                                   │
│ Output: picks_df, players_df, weekly_stats_df                   │
│ Function: load_competitor_data()                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PIPELINE STAGE 2: GAME RESULTS (game_results_fetcher.py)       │
├─────────────────────────────────────────────────────────────────┤
│ Input:  ESPN API requests                                       │
│ Output: week_*_game_results.json                                │
│ Function: fetch_game_results(weeks=[1,2,3,4])                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PIPELINE STAGE 3: ENRICHMENT (data_enrichment.py)              │
├─────────────────────────────────────────────────────────────────┤
│ Input:  picks_df + game_results_df                              │
│ Output: enriched_picks_df (with won, is_contrarian, etc.)       │
│ Function: full_enrichment_pipeline()                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PIPELINE STAGE 4: CLASSIFICATION (competitor_classifier.py)    │
├─────────────────────────────────────────────────────────────────┤
│ Input:  enriched_picks_df                                       │
│ Output: player_profiles (strategy, metrics, classification)     │
│ Function: build_player_profiles()                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ ANALYSIS & INSIGHTS                                             │
├─────────────────────────────────────────────────────────────────┤
│ - Actual league composition: 17 Chalk, 14 Slight, 1 Aggressive  │
│ - Chalk performance: 103.6 pts/wk, 70.2% win rate              │
│ - Contrarian performance: 39.6% win rate (underperforms)        │
│ - Field consensus analysis: 100% on BUF, DET, LAC (Week 4)     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Insights from Analysis

### Actual League Composition vs Theoretical Assumptions

| Strategy               | Actual | Theoretical | Difference |
|------------------------|--------|-------------|------------|
| Chalk-MaxPoints        | 17 (53%) | 16 (50%)   | +1 (+3%)   |
| Slight-Contrarian      | 14 (44%) | 10 (31%)   | +4 (+13%)  |
| Aggressive-Contrarian  | 1 (3%)   | 5 (16%)    | -4 (-13%)  |

**Implication**: League is MORE conservative than assumed. Fewer aggressive contrarian players means less opportunity for differentiation through contrarian plays.

### Performance by Strategy

| Strategy               | Avg Pts/Week | Win Rate | Sample Size |
|------------------------|--------------|----------|-------------|
| Chalk-MaxPoints        | 103.6        | 70.2%    | 17 players  |
| Slight-Contrarian      | 99.5         | 67.2%    | 14 players  |
| Aggressive-Contrarian  | 91.5         | 60.9%    | 1 player    |

**Implication**: Chalk strategy dominates. Contrarian plays reduce expected value.

### Top Performers

1. **Player A** - 107.8 pts/wk (Slight-Contrarian, 18.8% contrarian rate)
2. **Player B** - 107.5 pts/wk (Chalk, 1.6% contrarian rate)
3. **Player C** - 106.8 pts/wk (Chalk, 9.4% contrarian rate)

**Implication**: Top performer uses limited, strategic contrarian picks (18.8%). Pure chalk (Player B) performs nearly as well.

### Field Consensus Patterns (Week 4)

- **100% consensus**: BUF, DET, LAC, WAS, DEN, GB (6 games)
- **90%+ consensus**: NE, HOU, PHI, SF (4 more games)
- **Toss-ups**: KC vs BAL, SEA vs ARI (2 games)

**Implication**: Field heavily concentrates on clear favorites. Differentiation limited to 2-4 games per week.

---

## Next Steps (Phase 2)

### 1. Integrate Real Field into Simulator

**Current state**: `main.py` uses theoretical STRATEGY_MIX
```python
# Old assumption
STRATEGY_MIX = {
    "Chalk-MaxPoints": 16,
    "Slight-Contrarian": 10,
    "Aggressive-Contrarian": 5,
}
```

**Target state**: Use actual player profiles
```python
from competitor_classifier import build_player_profiles, analyze_league_composition

profiles = build_player_profiles(enriched_picks)
composition = analyze_league_composition(profiles)

# Use real distribution: 17/14/1
ACTUAL_FIELD = composition['strategy_counts']
```

### 2. Contrarian Opportunity Ranker

Build system to identify optimal contrarian opportunities:
- High field consensus (75%+)
- Reasonable upset probability (35%+ underdog chance)
- High confidence value (can assign 10+ confidence)

### 3. Strategy Recommendation Engine

Generate weekly pick recommendations:
- Input: Week N game odds
- Output: Optimal pick ordering based on actual field behavior
- Account for: Field consensus, upset probability, differentiation value

---

## File Structure

```
simulator/
├── README.md                      # This file
├── IMPROVEMENT_ROADMAP.md         # Project roadmap and progress
│
├── main.py                        # ✅ Main simulator (now uses actual field)
├── monte.py                       # Standalone Monte Carlo engine
│
├── data_loader.py                 # ✅ Data ingestion pipeline
├── game_results_fetcher.py        # ✅ ESPN API integration
├── data_enrichment.py             # ✅ Outcome enrichment
├── competitor_classifier.py       # ✅ Strategy classification
├── field_adapter.py               # ✅ NEW: Real field composition adapter
├── contrarian_analyzer.py         # ✅ NEW: Contrarian opportunity ranker
│
├── test_competitor_classifier.py  # ✅ Unit tests (5/5 passing)
│
└── example_result.md              # Sample simulator output
```

---

## Testing

Run all tests:
```bash
python simulator/test_competitor_classifier.py
```

Expected output:
```
✓ test_classify_pure_chalk_player
✓ test_classify_slight_contrarian
✓ test_classify_aggressive_contrarian
✓ test_calculate_player_metrics
✓ test_build_player_profiles
Tests passed: 5/5
```

---

## Dependencies

```
requests          # ESPN API calls
pandas            # Data manipulation
numpy             # Statistical analysis
python-dotenv     # Environment variables
```

For full simulator (main.py):
```
matplotlib        # Visualization
```

---

## Environment Variables

For game results fetching (optional):
```bash
# .env file
# ESPN API requires no authentication
```

For full simulator (The Odds API):
```bash
THE_ODDS_API_KEY=your_key_here
```

---

## LLM Integration Notes

This system is designed for LLM consumption and extension:

1. **Clear data contracts**: All functions have type hints and docstrings
2. **Predictable file naming**: `week_{N}_results_*.json`, `week_{N}_game_results.json`
3. **Structured outputs**: DataFrames with documented column schemas
4. **Modular architecture**: Each module has single responsibility
5. **Validation included**: Test suite ensures correctness

**For LLM tasks**:
- Data loading: Use `load_competitor_data()` - one function, returns all data
- Enrichment: Use `full_enrichment_pipeline()` - handles entire workflow
- Classification: Use `build_player_profiles()` - returns complete player analysis

**Example LLM prompt**:
```
Load competitor data and analyze Week 4 field consensus:

from data_loader import load_competitor_data
from data_enrichment import full_enrichment_pipeline

picks_df, _, _ = load_competitor_data()
enriched_picks, _ = full_enrichment_pipeline(picks_df)

week4 = enriched_picks[enriched_picks['week'] == 4]
consensus = week4.groupby('team').agg({
    'player_name': 'count',
    'is_contrarian': 'mean'
}).sort_values('player_name', ascending=False)
```

---

**Last Updated**: October 3, 2025
**Status**: ✅ Phase 2 Complete - Real field integration operational
**Data Coverage**: Weeks 1-4 (2025 NFL Season)

## Phase 2 Completion Summary

**What was delivered:**
1. ✅ `field_adapter.py` - Real field composition adapter integrated with main.py
2. ✅ `contrarian_analyzer.py` - Contrarian opportunity ranking engine
3. ✅ Actual field: 17 Chalk, 14 Slight-Contrarian, 1 Aggressive (vs 16/10/5 theoretical)
4. ✅ Historical validation: Chalk 71.4% win rate, Contrarian 45.7% win rate
5. ✅ Expected value calculations for contrarian plays
6. ✅ Complete documentation for LLM consumption

**Impact:**
- Simulator now uses actual league composition instead of theoretical assumptions
- Contrarian plays proven to underperform (45.7% vs 71.4% win rate)
- Data-driven recommendation: Stick with chalk strategy, use contrarian very sparingly
- Expected improvement: More accurate Monte Carlo simulations with real field
