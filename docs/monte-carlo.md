# Monte Carlo Internals (Quick Reference)

Applies betting-market probabilities to simulate confidence-pool outcomes.

## Core Flow
1) Fetch odds from The Odds API (`ingest/the_odds_api/api.py`) for the current week window.  
2) Convert to consensus de-vig probabilities (`analysis/odds/converter.py`) with sharp-book weighting.  
3) Generate picks/confidence for each strategy (`analysis/core/strategies.py`).  
4) Simulate many seasons/weeks (`analysis/core/simulator.py`) using field composition from `analysis/core/config.py`.  
5) Save summaries + per-strategy prediction files to `out/`.

## Key Tunables (`analysis/core/config.py`)
- `N_SIMS`: default simulation count (passed through from `run_strategy_simulation`).  
- `SHARP_BOOKS` / `SHARP_WEIGHT`: which books to prioritize when building consensus.  
- `STRATEGY_MIX`: expected league composition for Monte Carlo opponent modeling.  
- `BONUS_POINTS_*`: bonus assumptions if your league awards “most wins/points”.

## Strategies (`analysis/core/strategies.py`)
- `Chalk-MaxPoints`, `Random-MidShuffle`, `Slight-Contrarian`, `Aggressive-Contrarian`.  
- Each returns arrays of picks (1=favorite, 0=dog) and confidence rankings.

## Outputs
- `week_{n}_strategy_summary.csv`: expected totals per strategy.  
- `week_{n}_predictions_{code}.json`: ordered picks + probabilities per game.  
- Used by the win analyzer for weighted scenario math.

## Quick Customization
- Adjust `STRATEGY_MIX` to mirror your league before simulating.  
- Swap `N_SIMS` when calling `run_strategy_simulation(..., n_sims=50000)` for higher precision.  
- If you need a new strategy, add it to `analysis/core/strategies.py` and wire into `STRATEGIES` + `STRATEGY_CODES`.
