# Confidence Pool Simulator (Usage)

Purpose: run Monte Carlo simulations using The Odds API, compare built-in strategies, and optionally score your own pick list.

## Prerequisites
- `.env` must include `THE_ODDS_API_KEY` (see README for the rest).  
- Install deps and activate venv (`pip install -e .` recommended).  
- Odds fetch window is based on `WEEK_ONE_START_DATE`; make sure it matches the current season.

## Fast Path (Interactive)
1) `python -m cbs_fantasy_tooling.main`  
2) Choose **Analyze Data** → **Confidence Pool Strategy Simulator**.  
3) Provide picks when prompted (or leave blank to only run the built-ins).  
4) Results + prediction files are written to `out/`.

## What You Get
- **Summary CSV**: `out/week_{n}_strategy_summary.csv` with expected total points per strategy.  
- **Prediction JSON**: `out/week_{n}_predictions_{code}.json` for each tested strategy (`chalk`, `slight`, `aggress`, `shuffle`, `user`). Sorted by confidence.
- **Console view**: table of expected totals; if you entered picks, a short risk/contrarian readout.

## Built-in Strategies (80/20 view)
- **Chalk-MaxPoints**: Favorites in probability order (highest EV).  
- **Random-MidShuffle**: Chalk with mid-confidence shuffle to reduce correlation.  
- **Slight-Contrarian**: A couple of coin-flip underdogs.  
- **Aggressive-Contrarian**: Multiple underdogs; high variance, usually worse EV.

## Supplying Your Picks
- When prompted, paste comma-separated teams (names or abbreviations).  
- Choose whether to **analyze-only** (skips running other strategies).  
- Your picks are saved as `week_{n}_predictions_user.json` alongside the strategy files.

## Tips
- Run mid-week (Tue–Thu) for stable odds.  
- If odds fetch returns 0 games, check `THE_ODDS_API_KEY` or rerun closer to game day.  
- The simulator writes files to `out/`; the win analyzer reads those for weighted probabilities.
