"""Configuration constants and settings for the simulator."""

import os

from dotenv import load_dotenv

from cbs_fantasy_tooling.config import config

load_dotenv()

# League settings
# Roster size changes between seasons, so allow it to be overridden via env.
LEAGUE_SIZE = int(os.getenv("LEAGUE_SIZE", "32"))
N_OTHERS = LEAGUE_SIZE - 1
N_SIMS = 20000  # reduce (e.g., 5000) if runs are slow on your machine

# Sharp books configuration
# Books to overweight (The Odds API 'title' must contain one of these strings)
SHARP_BOOKS = ("Pinnacle", "Circa")
SHARP_WEIGHT = 2  # simple duplication weight; set to 1 to disable

# Bonus rules
# How a tie for a weekly bonus is resolved:
#   "single" - one tied player collects the whole bonus. This is the league rule:
#              a tie for most points is broken by a Monday-night total guess.
#              The sim can't model the guess, so it picks a tied player at random.
#   "all"    - every tied player collects in full (the old, incorrect assumption)
#   "split"  - the bonus is divided evenly among tied players
TIE_RULE = os.getenv("TIE_RULE", "single")

# Slate validation settings
# Expected weekly game count sanity check (regular season typically 16; varies with byes/late-season)
SLATE_MIN_GAMES = 12
SLATE_MAX_GAMES = 18

# Strategy codes for file naming
STRATEGY_CODES = {
    "Chalk-MaxPoints": "chalk",
    "Slight-Contrarian": "slight",
    "Aggressive-Contrarian": "aggress",
    "Random-MidShuffle": "shuffle",
    "Custom-User": "user",
}


# Field composition
# Uses actual field composition from historical data analysis if available
def get_field_composition():
    """Get field composition mix for the league."""
    try:
        from cbs_fantasy_tooling.analysis.competitor.field_adapter import (
            get_actual_field_composition,
        )

        user_name = config.user_name
        strategy_mix = get_actual_field_composition(exclude_user=user_name)
        print(f"Using ACTUAL field composition from historical data (excluding {user_name}):")
        print(
            f"  Chalk: {strategy_mix['Chalk-MaxPoints']}, Slight: {strategy_mix['Slight-Contrarian']}, Aggressive: {strategy_mix['Aggressive-Contrarian']}"
        )
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
