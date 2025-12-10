# NFL Confidence Pool Simulator - Usage Guide

## Overview

This simulator helps you make optimal weekly picks for NFL confidence pool leagues by:
- Fetching real-time betting market odds from The Odds API
- Converting odds to win probabilities using advanced de-vig techniques
- Running 20,000 Monte Carlo simulations to compare strategy performance
- Analyzing your custom picks against simulated opponents
- Generating weekly pick recommendations with confidence levels

## Quick Start

### Prerequisites

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Get The Odds API key:**
   - Sign up at [The Odds API](https://the-odds-api.com/)
   - Free tier includes 500 requests/month (sufficient for weekly use)

3. **Configure environment:**
```bash
# Add to .env file in project root
THE_ODDS_API_KEY=your_key_here
USER_NAME=YourName  # Optional: for actual field composition
```

### Basic Usage

**Run simulator with built-in strategies:**
```bash
# Fetch game results data up to current week
python simulator/game_results_fetcher.py && \
# Run simulations
python simulator/main.py
```

This will:
1. Fetch current week's NFL odds
2. Calculate win probabilities for each game
3. Simulate 20,000 weeks comparing 4 strategies
4. Display performance metrics and recommendations
5. Save results to `./out/` directory

## Analyzing Your Custom Picks

### Option 1: Command Line Input

Provide your picks as a comma-separated list (highest confidence to lowest):

```bash
python simulator/main.py --user-picks "Ravens,Bills,Cardinals,Cowboys,Lions,Rams,49ers,Bengals,Packers,Vikings,Steelers,Chargers,Texans,Broncos,Dolphins,Eagles"
```

**Team Name Formats (all work identically):**
- Full names: `"Baltimore Ravens,Buffalo Bills,Arizona Cardinals,..."`
- Common names: `"Ravens,Bills,Cardinals,..."`
- Abbreviations: `"BAL,BUF,ARI,DAL,DET,LAR,SF,CIN,GB,MIN,PIT,LAC,HOU,DEN,MIA,PHI"`

### Option 2: JSON File Input

Create a picks file (e.g., `my_picks.json`):
```json
{
  "picks": [
    "Ravens",
    "Bills",
    "Cardinals",
    "Cowboys",
    "Lions",
    "Rams",
    "49ers",
    "Bengals",
    "Packers",
    "Vikings",
    "Steelers",
    "Chargers",
    "Texans",
    "Broncos",
    "Dolphins",
    "Eagles"
  ]
}
```

Then run:
```bash
python simulator/main.py --picks-file my_picks.json
```

### Option 3: Analyze Only Your Picks

Skip built-in strategy comparison (faster):
```bash
python simulator/main.py --user-picks "Ravens,Bills,..." --analyze-only
```

## Understanding the Output

### 1. Slate Preview

Shows current week's games with favorite probabilities:
```
Slate preview (favorite vs dog, p_fav):
  1. Baltimore Ravens vs Buffalo Bills | p_fav=0.587 | commence=2025-09-14T17:00:00Z
  2. Detroit Lions vs Arizona Cardinals | p_fav=0.742 | commence=2025-09-15T13:00:00Z
  ...
```

**Key insight:** Higher `p_fav` = stronger favorite = safer chalk pick

### 2. Custom Pick Analysis

```
Your Custom Pick Analysis:
Expected Performance: 96.80 total points
Expected Wins: 10.31
Risk Assessment: Conservative (no contrarian picks)
Contrarian Picks: 0
```

**Metrics explained:**
- **Expected Performance**: Average total points across 20,000 simulations (including bonuses)
- **Expected Wins**: Average number of correct picks
- **Risk Assessment**: Strategy classification based on contrarian picks
- **Contrarian Picks**: Number of underdog picks (typically reduces expected value)

### 3. Contrarian Game Details

If you picked any underdogs:
```
Contrarian Games:
  New England Patriots at Miami Dolphins -> Patriots (Conf: 12, Prob: 48.0%)
  Jacksonville Jaguars at Cincinnati Bengals -> Jaguars (Conf: 8, Prob: 37.8%)
```

**Warning:** Historical data shows contrarian picks win only 45.7% vs 71.4% for chalk picks

### 4. Strategy Comparison

```
Confidence Pool Strategy — Monte Carlo Summary
             strategy  expected_total_points  expected_wins  P(get_Most_Wins_bonus)
      Chalk-MaxPoints                97.36          10.82                    0.215
    Random-MidShuffle                96.93          10.78                    0.198
          Custom-User                96.80          10.31                    0.187
    Slight-Contrarian                95.03          10.52                    0.156
Aggressive-Contrarian                91.72           9.89                    0.092
```

**How to interpret:**
- Your strategy is ranked against built-in strategies
- **expected_total_points**: Includes base points + bonus probability
- **P(get_Most_Wins_bonus)**: Chance of tying/winning the 5-point weekly bonus
- **P(get_Most_Points_bonus)**: Chance of tying/winning the 10-point weekly bonus

### 5. Saved Files

All outputs saved to `./out/` directory:

**Strategy Summary:**
```
out/week_2_strategy_summary_20250910_095705.csv
```
Comparative Monte Carlo results for all strategies

**Prediction Files (JSON):**
```
out/week_2_predictions_user_20250910_095705.json     # Your picks
out/week_2_predictions_chalk_20250910_095705.json    # Chalk strategy
out/week_2_predictions_slight_20250910_095705.json   # Slight contrarian
out/week_2_predictions_aggress_20250910_095705.json  # Aggressive contrarian
out/week_2_predictions_shuffle_20250910_095705.json  # Random mid-shuffle
```

Each prediction file contains structured game-by-game picks with confidence levels.

## Built-in Strategies Explained

### 1. Chalk-MaxPoints (Recommended)
- **Strategy**: Pick all favorites, order confidence by win probability
- **Performance**: 103.6 pts/week avg (17 players, 70.2% win rate)
- **Use case**: Maximize expected value through probability-based ordering

### 2. Random-MidShuffle
- **Strategy**: Pick all favorites, shuffle middle-tier confidence (30th-75th percentile)
- **Performance**: Similar to chalk, reduces correlation with field
- **Use case**: Differentiate from other chalk players without sacrificing EV

### 3. Slight-Contrarian
- **Strategy**: Pick 2 coin-flip underdogs, boost one to mid-confidence
- **Performance**: 99.5 pts/week avg (14 players, 67.2% win rate)
- **Use case**: Strategic differentiation on near-tossup games

### 4. Aggressive-Contrarian
- **Strategy**: Pick 3 coin-flip + 2 moderate underdogs
- **Performance**: 91.5 pts/week avg (1 player, 60.9% win rate)
- **Use case**: High variance, not recommended based on historical data

## Advanced Usage

### Customizing League Composition

Edit `simulator/main.py` lines 72-88 to match your league's actual mix:

```python
STRATEGY_MIX = {
    "Chalk-MaxPoints": 16,
    "Slight-Contrarian": 10,
    "Aggressive-Contrarian": 5,
}
```

Or use real field data (if you have historical picks):
```python
from field_adapter import get_actual_field_composition
STRATEGY_MIX = get_actual_field_composition(exclude_user="YourName")
```

### Adjusting Simulation Parameters

In `simulator/main.py`:

```python
N_SIMS = 20000        # Increase for more precision (slower)
LEAGUE_SIZE = 32      # Your league size
SHARP_WEIGHT = 2      # Weight for sharp books (Pinnacle, Circa)
```

### Bonus Tie Handling

```python
BONUS_SPLIT_TIES = False  # True = split bonuses among ties
                           # False = full bonus to all tied (default)
```

## Common Use Cases

### 1. Weekly Pick Generation
```bash
# Generate optimal picks for current week
python simulator/main.py
# Use the Random-MidShuffle strategy picks from the output
```

### 2. Evaluate Your Draft Picks
```bash
# Before submitting, analyze your picks
python simulator/main.py --user-picks "Team1,Team2,..." --analyze-only
# Review expected performance vs built-in strategies
```

### 3. Compare Multiple Pick Sets
```bash
# Test different variations
python simulator/main.py --user-picks "Set1..." > results_set1.txt
python simulator/main.py --user-picks "Set2..." > results_set2.txt
# Compare expected_total_points
```

### 4. Historical Analysis
```bash
# After the week completes, compare prediction vs actual
# Check saved prediction files in ./out/week_N_predictions_*.json
```

## Timing Recommendations

**Optimal time to run:**
- **Tuesday-Thursday**: After lines settle, before games start
- **Avoid Friday-Monday**: Games in progress excluded from API results

**Weekly workflow:**
1. **Tuesday AM**: Fetch previous week game data and run initial simulation with early lines
2. **Thursday AM**: Re-run with settled lines (closer to accurate)
3. **Thursday PM**: Finalize picks and submit

## Troubleshooting

### "Only N games found (expected 14+)"
**Cause**: Some games already started or API issues
**Solution**:
```bash
# Run simulator before Thursday night game starts
# Check The Odds API status page
# Verify API key in .env file
```

### "Odds fetch failed, using fallback slate"
**Cause**: API key missing/invalid or network issue
**Solution**:
```bash
# Verify .env file contains:
THE_ODDS_API_KEY=your_actual_key_here

# Test API key:
curl "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds?apiKey=YOUR_KEY&regions=us&markets=h2h"
```

### "Could not match team 'XYZ'"
**Cause**: Team name not recognized
**Solution**:
- Check slate preview for exact team names
- Use 3-letter abbreviations (BAL, BUF, etc.)
- Verify you have exactly 16 teams (or current week's game count)

### "Expected X picks, got Y"
**Cause**: Wrong number of teams provided
**Solution**:
```bash
# First run without --user-picks to see game count
python simulator/main.py
# Count games in slate preview, then provide that many picks
```

## API Usage & Costs

**The Odds API Limits:**
- Free tier: 500 requests/month
- Each simulator run = 1 request
- 500 requests = ~100 weeks of usage (running 5x per week)

**Optimizing API usage:**
- Use `--analyze-only` when testing your picks (doesn't fetch odds twice)
- Save results to file, review later without re-running
- Consider upgrading ($10/month) for unlimited requests during season

## File Naming Conventions

All outputs follow consistent patterns:

**Strategy Summary:**
```
week_{N}_strategy_summary_{YYYYMMDD}_{HHMMSS}.csv
```

**Prediction Files:**
```
week_{N}_predictions_{code}_{YYYYMMDD}_{HHMMSS}.json

Strategy codes:
  chalk   = Chalk-MaxPoints
  slight  = Slight-Contrarian
  aggress = Aggressive-Contrarian
  shuffle = Random-MidShuffle
  user    = Custom-User (your picks)
```

## Data-Driven Insights

Based on 4 weeks of historical analysis (Weeks 1-4, 2025 season):

**League Composition (32 players):**
- 17 Chalk players (53%)
- 14 Slight-Contrarian players (44%)
- 1 Aggressive-Contrarian player (3%)

**Performance by Strategy:**
| Strategy               | Avg Points/Week | Win Rate |
|------------------------|-----------------|----------|
| Chalk-MaxPoints        | 103.6           | 70.2%    |
| Slight-Contrarian      | 99.5            | 67.2%    |
| Aggressive-Contrarian  | 91.5            | 60.9%    |

**Contrarian Pick Success:**
- Overall contrarian win rate: 45.7%
- Chalk (favorite) win rate: 71.4%
- **Recommendation**: Use contrarian picks sparingly, only on near-tossups

**Field Consensus Patterns:**
- 6-10 games per week have 90%+ consensus (entire field picks same team)
- 2-4 games per week are tossups (40-60% split)
- Differentiation limited to handful of games

## Support & Resources

**Documentation:**
- Main simulator code: `simulator/main.py`
- Competitive intelligence: `simulator/README.md`
- Project overview: `CLAUDE.md`

**Getting Help:**
```bash
python simulator/main.py --help
```

**Issue Reporting:**
- GitHub: https://github.com/anthropics/claude-code/issues
- Include: Error message, command used, API response (if applicable)

---

**Last Updated**: October 9, 2025
**Simulator Version**: v2
**Compatible with**: The Odds API v4
