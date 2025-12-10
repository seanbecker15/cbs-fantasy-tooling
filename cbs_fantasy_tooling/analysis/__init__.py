"""CBS Fantasy Tooling Analysis Module

Provides confidence pool strategy analysis and simulation capabilities.
"""

from .monte_carlo import run_strategy_simulation
from .competitor_intelligence import analyze_competitors
from .visualization.contrarian_picks import analyze_contrarian_picks

__all__ = [
    "run_strategy_simulation",
    "analyze_competitors",
    "analyze_contrarian_picks",
]
