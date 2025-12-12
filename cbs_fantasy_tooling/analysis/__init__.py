"""CBS Fantasy Tooling Analysis Module

Provides confidence pool strategy analysis and simulation capabilities.
"""

from .monte_carlo import run_strategy_simulation
from .competitor_intelligence import analyze_competitors
from .visualization.contrarian_picks import analyze_contrarian_picks
from .win_scenario import analyze_win_scenarios, analyze_win_leaderboard
from .user_win_percentage import analyze_user_win_percentage

__all__ = [
    "run_strategy_simulation",
    "analyze_competitors",
    "analyze_contrarian_picks",
    "analyze_win_scenarios",
    "analyze_win_leaderboard",
    "analyze_user_win_percentage",
]
