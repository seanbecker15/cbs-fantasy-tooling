"""Configuration constants and settings for the simulator."""

import os
from dotenv import load_dotenv

load_dotenv()

# League settings
LEAGUE_SIZE = 32
N_OTHERS = LEAGUE_SIZE - 1
N_SIMS = 20000  # reduce (e.g., 5000) if runs are slow on your machine

# The Odds API configuration
SPORT = "americanfootball_nfl"
REGION = "us"  # us|uk|eu|au (controls which books)
MARKETS = "h2h"  # moneylines for win probabilities
ODDS_FORMAT = "american"  # american|decimal

# Sharp books configuration
# Books to overweight (The Odds API 'title' must contain one of these strings)
SHARP_BOOKS = ("Pinnacle", "Circa")
SHARP_WEIGHT = 2  # simple duplication weight; set to 1 to disable

# Bonus rules
# Tie bonus rules (by default, full bonus to all tied winners)
BONUS_SPLIT_TIES = False  # if True, split bonuses equally among all tied players

# Slate validation settings
# Expected weekly game count sanity check (regular season typically 16; varies with byes/late-season)
SLATE_MIN_GAMES = 12
SLATE_MAX_GAMES = 18

# Fallback settings for when API is unavailable
FALLBACK_NUM_GAMES = 16
FALLBACK_SEED = 42

# Strategy codes for file naming
STRATEGY_CODES = {
    "Chalk-MaxPoints": "chalk",
    "Slight-Contrarian": "slight",
    "Aggressive-Contrarian": "aggress",
    "Random-MidShuffle": "shuffle",
    "Custom-User": "user"
}

# Field composition
# Uses actual field composition from historical data analysis if available
def get_field_composition():
    """Get field composition mix for the league."""
    try:
        from cbs_fantasy_tooling.analysis.competitor.field_adapter import get_actual_field_composition
        USER_NAME = os.getenv("USER_NAME")
        strategy_mix = get_actual_field_composition(exclude_user=USER_NAME)
        print(f"Using ACTUAL field composition from historical data (excluding {USER_NAME}):")
        print(f"  Chalk: {strategy_mix['Chalk-MaxPoints']}, Slight: {strategy_mix['Slight-Contrarian']}, Aggressive: {strategy_mix['Aggressive-Contrarian']}")
        return strategy_mix
    except (ImportError, FileNotFoundError) as e:
        # Fallback to theoretical if field_adapter not available or data incomplete
        strategy_mix = {
            "Chalk-MaxPoints": 16,
            "Slight-Contrarian": 10,
            "Aggressive-Contrarian": 5,
        }
        if isinstance(e, FileNotFoundError):
            print("Warning: Incomplete historical data. Using THEORETICAL field composition.")
        else:
            print("Warning: Using THEORETICAL field composition (field_adapter not found)")
        return strategy_mix
