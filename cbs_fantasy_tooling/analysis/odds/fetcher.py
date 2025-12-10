"""Fetch NFL odds from The Odds API."""

import os
import numpy as np
import requests
from cbs_fantasy_tooling.analysis.odds.converter import consensus_moneyline_probs, rows_to_game_probs
from cbs_fantasy_tooling.analysis.core.config import (
    SPORT, REGION, MARKETS, ODDS_FORMAT,
    SHARP_BOOKS, SHARP_WEIGHT,
    FALLBACK_NUM_GAMES, FALLBACK_SEED
)
from cbs_fantasy_tooling.analysis.utils.time_helpers import get_commence_time_from, get_commence_time_to


def fetch_current_week_odds(api_key: str) -> list[dict]:
    """
    Fetch current NFL moneylines across US books, restricted to current week.

    Args:
        api_key: The Odds API key

    Returns:
        List of event dictionaries from the API

    Raises:
        HTTPError: If API request fails
    """
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"
    params = {
        "apiKey": api_key,
        "regions": REGION,
        "markets": MARKETS,
        "oddsFormat": ODDS_FORMAT,
        "dateFormat": "iso",
        "commenceTimeFrom": get_commence_time_from(),
        "commenceTimeTo": get_commence_time_to(),
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    # Optional: examine quota headers
    # print("Remaining:", r.headers.get("x-requests-remaining"), "Used:", r.headers.get("x-requests-used"))
    return r.json()


def get_weekly_game_probs_from_odds() -> tuple[np.ndarray, list[dict]]:
    """
    Master function: fetch odds → consensus de-vig → GAME_PROBS with mapping.

    Returns:
        Tuple of (game_probs_array, week_mapping)

    Raises:
        RuntimeError: If API key not set or no games returned
    """
    api_key = os.getenv("THE_ODDS_API_KEY")
    if not api_key:
        raise RuntimeError("Set THE_ODDS_API_KEY environment variable with your The Odds API key.")

    events = fetch_current_week_odds(api_key)
    rows = consensus_moneyline_probs(events, SHARP_BOOKS, SHARP_WEIGHT)
    if not rows:
        raise RuntimeError("No rows built from odds response. Check API key, region, time window, or timing.")
    return rows_to_game_probs(rows)


def fallback_game_probs(num_games=FALLBACK_NUM_GAMES, seed=FALLBACK_SEED) -> tuple[np.ndarray, list[dict]]:
    """
    Generate synthetic slate if the API isn't available (keeps the tool usable).

    Args:
        num_games: Number of games to simulate
        seed: Random seed for reproducibility

    Returns:
        Tuple of (game_probs_array, week_mapping)
    """
    np.random.seed(seed)
    heavy = list(np.random.uniform(0.78, 0.85, 4))
    moderate = list(np.random.uniform(0.62, 0.70, 6))
    closeish = list(np.random.uniform(0.54, 0.58, 4))
    pickem = list(np.random.uniform(0.50, 0.52, max(0, num_games - 14)))
    arr = np.array(heavy + moderate + closeish + pickem, dtype=float)
    np.random.shuffle(arr)
    mapping = [
        {
            "id": f"fake-{i+1}",
            "home_team": f"HOME{i+1}",
            "away_team": f"AWAY{i+1}",
            "favorite": "HOME" if p >= 0.5 else "AWAY",
            "dog": "AWAY" if p >= 0.5 else "HOME",
            "p_fav": float(p),
            "commence_time": None
        }
        for i, p in enumerate(arr)
    ]
    return arr, mapping
