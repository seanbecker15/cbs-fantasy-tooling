"""
Confidence Pool Strategy Simulator + The Odds API integration
- Restricts to the CURRENT NFL WEEK via commenceTimeFrom/To (Tue 05:00 UTC → next Tue 04:59 UTC)
- Pulls NFL moneylines (h2h), converts to de-vig probabilities
- Aggregates by median with optional sharp-book weighting (e.g., Pinnacle, Circa)
- Validates slate size and runs Monte Carlo comparison of strategies

Requirements: requests, numpy, pandas, matplotlib
Env: export ODDS_API_KEY="your_key_here"

Notes:
- Bonuses award FULL points to ALL ties by default (configurable).
- If the API fails, a synthetic slate is used so you can still test the simulator.
"""

import os
import math
import random
import json
import argparse
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta, time, timezone
from statistics import median
from difflib import get_close_matches

import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ===============================
# 0) CONFIG
# ===============================

load_dotenv()

LEAGUE_SIZE = 32
N_OTHERS = LEAGUE_SIZE - 1
N_SIMS = 20000            # reduce (e.g., 5000) if runs are slow on your machine

SPORT = "americanfootball_nfl"
REGION = "us"             # us|uk|eu|au (controls which books)
MARKETS = "h2h"           # moneylines for win probabilities
ODDS_FORMAT = "american"  # american|decimal

# Books to overweight (The Odds API 'title' must contain one of these strings)
SHARP_BOOKS = ("Pinnacle", "Circa")
SHARP_WEIGHT = 2  # simple duplication weight; set to 1 to disable

# Tie bonus rules (by default, full bonus to all tied winners)
BONUS_SPLIT_TIES = False  # if True, split bonuses equally among all tied players

# Expected weekly game count sanity check (regular season typically 16; varies with byes/late-season)
SLATE_MIN_GAMES = 12
SLATE_MAX_GAMES = 18

# If API unavailable, fall back to a synthetic slate
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

# ===============================
# 0.5) AUTO-FETCH MISSING GAME RESULTS
# ===============================

def ensure_game_results_available(data_dir="../out", season=2025):
    """
    Automatically fetch missing game results from ESPN API.
    Checks weeks 1-current and fetches any missing game result files.
    """
    import glob

    # Determine which weeks have player picks
    picks_pattern = os.path.join(data_dir, "week_*_results_*.json")
    picks_files = glob.glob(picks_pattern)

    weeks_with_picks = set()
    for f in picks_files:
        # Extract week number from filename like "week_5_results_20251008_101907.json"
        basename = os.path.basename(f)
        if basename.startswith("week_") and "_results_" in basename:
            try:
                week_num = int(basename.split("_")[1])
                weeks_with_picks.add(week_num)
            except (IndexError, ValueError):
                continue

    if not weeks_with_picks:
        return  # No player picks data yet

    # Check which weeks are missing game results
    missing_weeks = []
    for week in sorted(weeks_with_picks):
        results_file = os.path.join(data_dir, f"week_{week}_game_results.json")
        if not os.path.exists(results_file):
            missing_weeks.append(week)

    # Fetch missing game results
    if missing_weeks:
        print(f"Fetching missing game results for weeks: {missing_weeks}")
        try:
            sys.path.insert(0, os.path.dirname(__file__))  # Ensure simulator modules are importable
            from game_results_fetcher import fetch_game_results
            fetch_game_results(weeks=missing_weeks, season=season, save_json=True)
            print(f"✓ Successfully fetched game results for weeks {missing_weeks}")
        except Exception as e:
            print(f"Warning: Could not fetch game results: {e}")

# Auto-fetch missing game results before loading field composition
ensure_game_results_available()

# Field composition (others in your 32-person league)
# UPDATED: Using actual field composition from historical data analysis
try:
    from field_adapter import get_actual_field_composition
    USER_NAME = os.getenv("USER_NAME")
    STRATEGY_MIX = get_actual_field_composition(exclude_user=USER_NAME)
    print(f"Using ACTUAL field composition from historical data (excluding {USER_NAME}):")
    print(f"  Chalk: {STRATEGY_MIX['Chalk-MaxPoints']}, Slight: {STRATEGY_MIX['Slight-Contrarian']}, Aggressive: {STRATEGY_MIX['Aggressive-Contrarian']}")
except (ImportError, FileNotFoundError) as e:
    # Fallback to theoretical if field_adapter not available or data incomplete
    STRATEGY_MIX = {
        "Chalk-MaxPoints": 16,
        "Slight-Contrarian": 10,
        "Aggressive-Contrarian": 5,
    }
    if isinstance(e, FileNotFoundError):
        print("Warning: Incomplete historical data. Using THEORETICAL field composition.")
    else:
        print("Warning: Using THEORETICAL field composition (field_adapter not found)")

assert sum(STRATEGY_MIX.values()) == N_OTHERS, "STRATEGY_MIX must sum to 31."

# ===============================
# 1) TIME WINDOW HELPERS (CURRENT NFL WEEK)
# ===============================

def get_current_nfl_week() -> int:
    """
    Calculate the current NFL week based on season start date (September 2, 2025).
    Week 1 starts on September 2, 2025 (Tuesday).
    """
    season_start = datetime(2025, 9, 2, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    days_since_start = (now - season_start).days
    week = max(1, min(18, (days_since_start // 7) + 1))
    return week

def get_commence_time_from() -> str:
    """
    Returns ISO 8601 string for previous Tuesday at 05:00:00 UTC.
    This sets the start of the NFL "week" window.
    """
    now = datetime.now(timezone.utc)
    # Monday=0, Tuesday=1, ... Sunday=6. We want most recent Tuesday.
    days_since_tue = (now.weekday() - 1) % 7
    last_tue = now - timedelta(days=days_since_tue)
    last_tue_5am = datetime.combine(last_tue.date(), time(5, 0, 0, tzinfo=timezone.utc))
    return last_tue_5am.isoformat().replace("+00:00", "Z")

def get_commence_time_to() -> str:
    """
    Returns ISO 8601 string for next Tuesday at 04:59:00 UTC.
    This ends the NFL "week" window (one minute before the next 05:00 UTC).
    """
    now = datetime.now(timezone.utc)
    days_since_tue = (now.weekday() - 1) % 7
    last_tue = now - timedelta(days=days_since_tue)
    last_tue_5am = datetime.combine(last_tue.date(), time(5, 0, 0, tzinfo=timezone.utc))
    next_tue_459am = last_tue_5am + timedelta(days=7, minutes=-1)
    return next_tue_459am.isoformat().replace("+00:00", "Z")

# ===============================
# 2) ODDS → PROBABILITIES HELPERS
# ===============================

def american_to_implied_prob(ml: int) -> float | None:
    """Convert an American moneyline to an implied probability (with vig)."""
    if ml is None:
        return None
    if ml < 0:
        return (-ml) / ((-ml) + 100.0)
    return 100.0 / (ml + 100.0)

def devig_two_way(pA: float | None, pB: float | None) -> tuple[float | None, float | None]:
    """
    Remove the vig for a two-outcome market via simple normalization:
      pA' = pA / (pA + pB), pB' = pB / (pA + pB)
    For more sophistication, plug in Shin/multiplicative here.
    """
    if pA is None or pB is None:
        return None, None
    s = pA + pB
    if s <= 0:
        return None, None
    return pA / s, pB / s

def fetch_current_week_odds(api_key: str) -> list[dict]:
    """Fetch current NFL moneylines across US books, restricted to *this* week."""
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

def consensus_moneyline_probs(events: list[dict],
                              sharp_books: tuple[str, ...] = SHARP_BOOKS,
                              sharp_weight: int = SHARP_WEIGHT) -> list[dict]:
    """
    Build consensus de-vig probabilities per game.
    Returns list of rows: {id, home_team, away_team, p_home, p_away, commence_time}
    """
    rows = []
    for ev in events:
        eid = ev.get("id")
        home = ev.get("home_team")
        away = ev.get("away_team")
        commence = ev.get("commence_time")

        if not home or not away:
            continue

        p_home_list, p_away_list = [], []

        for book in ev.get("bookmakers", []):
            title = book.get("title", "") or ""
            # find the h2h market
            m = next((m for m in book.get("markets", []) if m.get("key") == "h2h"), None)
            if not m:
                continue
            outcomes = {o["name"]: o for o in m.get("outcomes", [])}
            if home not in outcomes or away not in outcomes:
                continue

            ml_home = outcomes[home].get("price")
            ml_away = outcomes[away].get("price")

            p_home_raw = american_to_implied_prob(ml_home)
            p_away_raw = american_to_implied_prob(ml_away)
            p_home_fair, p_away_fair = devig_two_way(p_home_raw, p_away_raw)
            if p_home_fair is None or p_away_fair is None:
                continue

            # simple sharp weighting by duplication
            weight = sharp_weight if any(s in title for s in sharp_books) else 1
            p_home_list.extend([p_home_fair] * weight)
            p_away_list.extend([p_away_fair] * weight)

        if not p_home_list or not p_away_list:
            continue

        rows.append({
            "id": eid,
            "home_team": home,
            "away_team": away,
            "p_home": median(p_home_list),
            "p_away": median(p_away_list),
            "commence_time": commence,
        })
    return rows

def rows_to_GAME_PROBS(rows: list[dict]) -> tuple[np.ndarray, list[dict]]:
    """
    Convert per-game rows to:
      GAME_PROBS: np.array of the favorite's win prob per game
      MAPPING: list of {favorite, dog, p_fav, home_team, away_team, id, commence_time}
    """
    probs, mapping = [], []
    for g in rows:
        if g["p_home"] >= g["p_away"]:
            fav_prob, fav_team, dog_team = g["p_home"], g["home_team"], g["away_team"]
        else:
            fav_prob, fav_team, dog_team = g["p_away"], g["away_team"], g["home_team"]
        probs.append(fav_prob)
        mapping.append({
            "id": g["id"],
            "home_team": g["home_team"],
            "away_team": g["away_team"],
            "favorite": fav_team,
            "dog": dog_team,
            "p_fav": float(fav_prob),
            "commence_time": g.get("commence_time"),
        })
    return np.array(probs, dtype=float), mapping

def get_weekly_GAME_PROBS_from_odds() -> tuple[np.ndarray, list[dict]]:
    """Master function: fetch odds → consensus de-vig → GAME_PROBS (with mapping)."""
    api_key = os.getenv("THE_ODDS_API_KEY")
    if not api_key:
        raise RuntimeError("Set THE_ODDS_API_KEY environment variable with your The Odds API key.")

    events = fetch_current_week_odds(api_key)
    rows = consensus_moneyline_probs(events)
    if not rows:
        raise RuntimeError("No rows built from odds response. Check API key, region, time window, or timing.")
    return rows_to_GAME_PROBS(rows)

def fallback_GAME_PROBS(num_games=FALLBACK_NUM_GAMES, seed=FALLBACK_SEED) -> tuple[np.ndarray, list[dict]]:
    """Synthetic slate if the API isn’t available (keeps the tool usable)."""
    np.random.seed(seed)
    heavy = list(np.random.uniform(0.78, 0.85, 4))
    moderate = list(np.random.uniform(0.62, 0.70, 6))
    closeish = list(np.random.uniform(0.54, 0.58, 4))
    pickem = list(np.random.uniform(0.50, 0.52, max(0, num_games - 14)))
    arr = np.array(heavy + moderate + closeish + pickem, dtype=float)
    np.random.shuffle(arr)
    mapping = [{"id": f"fake-{i+1}", "home_team": f"HOME{i+1}", "away_team": f"AWAY{i+1}",
                "favorite": "HOME" if p >= 0.5 else "AWAY", "dog": "AWAY" if p >= 0.5 else "HOME",
                "p_fav": float(p), "commence_time": None} for i, p in enumerate(arr)]
    return arr, mapping

# ===============================
# 3) STRATEGIES (same as original)
# ===============================

def assign_confidence_order(order_indices, num_games):
    conf = np.zeros(num_games, dtype=int)
    for rank, idx in enumerate(order_indices):
        conf[idx] = num_games - rank
    return conf

def order_by_probability_desc(p):
    return list(np.argsort(-p))

def confidence_by_probability(p):
    return assign_confidence_order(order_by_probability_desc(p), len(p))

def picks_favorites(p):
    return np.ones_like(p, dtype=int)

def picks_with_contrarians(p, num_coinflip_dogs=2, num_moderate_dogs=0):
    picks = picks_favorites(p)
    idx_coinflip = [i for i, x in enumerate(p) if abs(x - 0.5) <= 0.06]
    idx_moderate = [i for i, x in enumerate(p) if 0.58 < x <= 0.66]
    random.shuffle(idx_coinflip); random.shuffle(idx_moderate)
    for i in idx_coinflip[:num_coinflip_dogs]:
        picks[i] = 0
    for i in idx_moderate[:num_moderate_dogs]:
        picks[i] = 0
    return picks

def reorder_with_mid_boost(base_order, boost_indices, target_positions):
    order = [x for x in base_order if x not in boost_indices]
    used = set()
    for idx, pos in zip(boost_indices, target_positions):
        pos = max(0, min(len(order), int(pos)))
        while pos in used:
            pos += 1
        used.add(pos)
        order.insert(pos, idx)
    return order

def strategy_chalk_maxpoints(p):
    return picks_favorites(p), confidence_by_probability(p)

def strategy_slight_contrarian(p):
    picks = picks_with_contrarians(p, num_coinflip_dogs=2, num_moderate_dogs=0)
    base_order = order_by_probability_desc(p)
    contrarians = [i for i, pick in enumerate(picks) if pick == 0]
    order = reorder_with_mid_boost(base_order, contrarians[:1], [int(len(p)*0.55)]) if contrarians else base_order
    return picks, assign_confidence_order(order, len(p))

def strategy_aggressive_contrarian(p):
    picks = picks_with_contrarians(p, num_coinflip_dogs=3, num_moderate_dogs=2)
    base_order = order_by_probability_desc(p)
    contrarians = [i for i, pick in enumerate(picks) if pick == 0][:2]
    targets = [int(len(p)*0.65), int(len(p)*0.50)][:len(contrarians)]
    order = reorder_with_mid_boost(base_order, contrarians, targets)
    return picks, assign_confidence_order(order, len(p))

def strategy_random_midshuffle(p):
    picks = picks_favorites(p)
    order = order_by_probability_desc(p)
    n = len(order); lo, hi = int(n*0.30), int(n*0.75)
    mid = order[lo:hi]; random.shuffle(mid)
    order = order[:lo] + mid + order[hi:]
    return picks, assign_confidence_order(order, len(p))

STRATEGIES = {
    "Chalk-MaxPoints": strategy_chalk_maxpoints,
    "Slight-Contrarian": strategy_slight_contrarian,
    "Aggressive-Contrarian": strategy_aggressive_contrarian,
    "Random-MidShuffle": strategy_random_midshuffle,
}

# ===============================
# 3.5) USER PICK FUNCTIONS
# ===============================

def normalize_team_name(user_team: str, available_teams: list[str]) -> str:
    """
    Normalize user input team name to match available team names.
    Handles common variations and abbreviations.
    """
    user_team = user_team.strip()
    
    # Direct match first
    for team in available_teams:
        if user_team.lower() == team.lower():
            return team
    
    # Try partial matching (e.g., "Ravens" -> "Baltimore Ravens")
    for team in available_teams:
        if user_team.lower() in team.lower() or team.lower() in user_team.lower():
            return team
    
    # Common abbreviations mapping
    abbrev_map = {
        'bal': 'baltimore ravens', 'buf': 'buffalo bills', 'mia': 'miami dolphins',
        'ne': 'new england patriots', 'nyj': 'new york jets', 'pit': 'pittsburgh steelers',
        'cle': 'cleveland browns', 'cin': 'cincinnati bengals', 'hou': 'houston texans',
        'ind': 'indianapolis colts', 'jax': 'jacksonville jaguars', 'ten': 'tennessee titans',
        'den': 'denver broncos', 'kc': 'kansas city chiefs', 'lv': 'las vegas raiders',
        'lac': 'los angeles chargers', 'dal': 'dallas cowboys', 'nyg': 'new york giants',
        'phi': 'philadelphia eagles', 'was': 'washington commanders', 'chi': 'chicago bears',
        'det': 'detroit lions', 'gb': 'green bay packers', 'min': 'minnesota vikings',
        'atl': 'atlanta falcons', 'car': 'carolina panthers', 'no': 'new orleans saints',
        'tb': 'tampa bay buccaneers', 'ari': 'arizona cardinals', 'lar': 'los angeles rams',
        'sea': 'seattle seahawks', 'sf': 'san francisco 49ers'
    }
    
    user_lower = user_team.lower()
    for abbrev, full_name in abbrev_map.items():
        if user_lower == abbrev:
            # Find matching team in available teams
            for team in available_teams:
                if full_name in team.lower():
                    return team
    
    # Fuzzy matching as last resort
    matches = get_close_matches(user_team, available_teams, n=1, cutoff=0.6)
    if matches:
        return matches[0]
    
    raise ValueError(f"Could not match team '{user_team}' to available teams: {available_teams}")

def validate_user_picks(user_picks: list[str], week_mapping: list[dict]) -> tuple[list[str], list[str]]:
    """
    Validate user picks against available teams for the current week.
    Returns (normalized_picks, error_messages)
    """
    errors = []
    normalized_picks = []
    
    # Extract all available teams from week mapping
    all_teams = set()
    for game in week_mapping:
        all_teams.add(game["home_team"])
        all_teams.add(game["away_team"])
    all_teams = list(all_teams)
    
    if len(user_picks) != len(week_mapping):
        errors.append(f"Expected {len(week_mapping)} picks, got {len(user_picks)}")
        return [], errors
    
    for i, pick in enumerate(user_picks, 1):
        try:
            normalized = normalize_team_name(pick, all_teams)
            normalized_picks.append(normalized)
        except ValueError as e:
            errors.append(f"Pick {i}: {str(e)}")
    
    # Check for duplicates
    if len(set(normalized_picks)) != len(normalized_picks):
        duplicates = [pick for pick in set(normalized_picks) if normalized_picks.count(pick) > 1]
        errors.append(f"Duplicate picks found: {duplicates}")
    
    return normalized_picks, errors

def parse_user_picks(user_input: str | list, week_mapping: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """
    Parse user picks from various input formats into picks and confidence arrays.
    
    Args:
        user_input: String (comma-separated) or list of team names in confidence order (16->1)
        week_mapping: Current week's games mapping
        
    Returns:
        (picks_array, confidence_array) where:
        - picks_array: 1 for favorite, 0 for underdog
        - confidence_array: confidence levels 1-16
    """
    # Handle string input
    if isinstance(user_input, str):
        user_picks = [team.strip() for team in user_input.split(',')]
    else:
        user_picks = user_input
    
    # Validate picks
    normalized_picks, errors = validate_user_picks(user_picks, week_mapping)
    if errors:
        raise ValueError("Validation errors:\n" + "\n".join(errors))
    
    # Create picks and confidence arrays
    num_games = len(week_mapping)
    picks = np.zeros(num_games, dtype=int)
    confidence = np.zeros(num_games, dtype=int)
    
    # Create a copy to avoid modifying the original
    remaining_picks = normalized_picks.copy()
    
    for i, game in enumerate(week_mapping):
        # Find which team user picked for this game
        user_pick = None
        confidence_level = None
        pick_index = None
        
        for j, pick in enumerate(remaining_picks):
            if pick == game["home_team"] or pick == game["away_team"]:
                user_pick = pick
                # Find the original position in the user's pick order
                original_index = normalized_picks.index(pick)
                confidence_level = num_games - original_index  # First pick = 16, last pick = 1
                pick_index = j
                break
        
        if user_pick is None:
            raise ValueError(f"No pick found for game: {game['away_team']} at {game['home_team']}")
        
        confidence[i] = confidence_level
        # Remove from remaining picks
        remaining_picks.pop(pick_index)
        
        # Determine if pick is favorite (1) or underdog (0)
        if user_pick == game["favorite"]:
            picks[i] = 1
        else:
            picks[i] = 0
    
    return picks, confidence

def create_user_strategy(user_picks: np.ndarray, user_confidence: np.ndarray):
    """
    Create a strategy function from user picks that can be used in simulations.
    """
    def user_strategy_fn(_):
        # Return the user's fixed picks and confidence, ignoring probabilities
        return user_picks.copy(), user_confidence.copy()
    
    return user_strategy_fn

def simulate_user_picks(user_input: str | list, week_mapping: list[dict], game_probs: np.ndarray, 
                       others_mix: dict, n_sims: int = N_SIMS) -> dict:
    """
    Simulate user picks against the field using Monte Carlo analysis.
    """
    try:
        picks, confidence = parse_user_picks(user_input, week_mapping)
    except ValueError as e:
        print(f"Error parsing user picks: {e}")
        return None
    
    user_strategy = create_user_strategy(picks, confidence)
    
    # Run simulation using same framework as built-in strategies
    others = []
    for name, count in others_mix.items():
        others.extend([STRATEGIES[name]] * count)
    assert len(others) == N_OTHERS
    
    user_totals = []; user_points = []; user_wins = []
    user_mw_bonus = []; user_mp_bonus = []
    
    for _ in range(n_sims):
        random.shuffle(others)
        players = [user_strategy] + others
        wins, points, total, mw_bonus, mp_bonus = simulate_week_once(game_probs, players)
        user_totals.append(total[0]); user_points.append(points[0]); user_wins.append(wins[0])
        user_mw_bonus.append(1 if mw_bonus[0] > 0 else 0)
        user_mp_bonus.append(1 if mp_bonus[0] > 0 else 0)
    
    user_totals = np.array(user_totals); user_points = np.array(user_points); user_wins = np.array(user_wins)
    user_mw_bonus = np.array(user_mw_bonus); user_mp_bonus = np.array(user_mp_bonus)
    
    summary = {
        "strategy": "Custom-User",
        "expected_base_points": float(user_points.mean()),
        "expected_wins": float(user_wins.mean()),
        "P(get_Most_Wins_bonus)": float(user_mw_bonus.mean()),
        "P(get_Most_Points_bonus)": float(user_mp_bonus.mean()),
        "expected_bonus_points": float(5*user_mw_bonus.mean() + 10*user_mp_bonus.mean()),
        "expected_total_points": float(user_totals.mean()),
        "stdev_total_points": float(user_totals.std(ddof=1)),
        "p10_total_points": float(np.percentile(user_totals, 10)),
        "p50_total_points": float(np.percentile(user_totals, 50)),
        "p90_total_points": float(np.percentile(user_totals, 90)),
    }
    
    return summary, picks, confidence

def analyze_user_picks(user_picks: np.ndarray, user_confidence: np.ndarray, 
                      week_mapping: list[dict], game_probs: np.ndarray) -> dict:
    """
    Analyze user picks to identify contrarian choices, risk level, and expected value.
    """
    analysis = {
        "total_games": len(week_mapping),
        "contrarian_picks": [],
        "high_confidence_games": [],
        "low_confidence_games": [],
        "expected_wins": 0.0,
        "risk_assessment": "Unknown"
    }
    
    contrarian_count = 0
    expected_correct = 0.0
    
    for pick, conf, game, prob in zip(user_picks, user_confidence, week_mapping, game_probs):
        game_analysis = {
            "game": f"{game['away_team']} at {game['home_team']}",
            "pick": game["favorite"] if pick == 1 else game["dog"],
            "confidence": int(conf),
            "is_contrarian": pick == 0,
            "favorite_prob": float(prob),
            "pick_prob": float(prob if pick == 1 else 1 - prob)
        }
        
        if pick == 0:  # Contrarian pick
            contrarian_count += 1
            analysis["contrarian_picks"].append(game_analysis)
        
        if conf >= 13:  # High confidence
            analysis["high_confidence_games"].append(game_analysis)
        elif conf <= 4:  # Low confidence
            analysis["low_confidence_games"].append(game_analysis)
        
        # Calculate expected wins
        expected_correct += game_analysis["pick_prob"]
    
    analysis["expected_wins"] = expected_correct
    analysis["contrarian_count"] = contrarian_count
    
    # Risk assessment
    if contrarian_count == 0:
        analysis["risk_assessment"] = "Conservative (no contrarian picks)"
    elif contrarian_count <= 2:
        analysis["risk_assessment"] = "Moderate (limited contrarian picks)"
    else:
        analysis["risk_assessment"] = "Aggressive (multiple contrarian picks)"
    
    return analysis

# ===============================
# 4) SIMULATOR (same as original, + optional tie-splitting)
# ===============================

def _apply_bonuses(wins, points):
    """
    Returns arrays for most_wins_bonus, most_points_bonus, given global BONUS_SPLIT_TIES.
    +5 for Most Wins, +10 for Most Points; either full to ties or split equally.
    """
    max_w = wins.max()
    max_p = points.max()
    idx_w = np.where(wins == max_w)[0]
    idx_p = np.where(points == max_p)[0]

    if BONUS_SPLIT_TIES:
        mw_each = 5.0 / len(idx_w)
        mp_each = 10.0 / len(idx_p)
        most_wins_bonus = np.zeros_like(points, dtype=float)
        most_points_bonus = np.zeros_like(points, dtype=float)
        most_wins_bonus[idx_w] = mw_each
        most_points_bonus[idx_p] = mp_each
    else:
        most_wins_bonus = (wins == max_w).astype(float) * 5.0
        most_points_bonus = (points == max_p).astype(float) * 10.0
    return most_wins_bonus, most_points_bonus

def simulate_week_once(p, player_strategies):
    G = len(p); N = len(player_strategies)
    outcomes = (np.random.rand(G) < p).astype(int)
    wins = np.zeros(N, dtype=int)
    points = np.zeros(N, dtype=int)

    for j, strat_fn in enumerate(player_strategies):
        picks, conf = strat_fn(p)
        correct = (picks == outcomes).astype(int)
        wins[j] = int(correct.sum())
        points[j] = int(np.dot(correct, conf))

    most_wins_bonus, most_points_bonus = _apply_bonuses(wins, points)
    total = points + most_wins_bonus + most_points_bonus
    return wins, points, total, most_wins_bonus, most_points_bonus

def simulate_many_weeks(p, your_strategy_name, others_mix, n_sims=5000):
    your_strategy = STRATEGIES[your_strategy_name]
    others = []
    for name, count in others_mix.items():
        others.extend([STRATEGIES[name]] * count)
    assert len(others) == N_OTHERS

    your_totals = []; your_points = []; your_wins = []
    your_mw_bonus = []; your_mp_bonus = []

    for _ in range(n_sims):
        random.shuffle(others)
        players = [your_strategy] + others
        wins, points, total, mw_bonus, mp_bonus = simulate_week_once(p, players)
        your_totals.append(total[0]); your_points.append(points[0]); your_wins.append(wins[0])
        your_mw_bonus.append(1 if mw_bonus[0] > 0 else 0)
        your_mp_bonus.append(1 if mp_bonus[0] > 0 else 0)

    your_totals = np.array(your_totals); your_points = np.array(your_points); your_wins = np.array(your_wins)
    your_mw_bonus = np.array(your_mw_bonus); your_mp_bonus = np.array(your_mp_bonus)

    summary = {
        "strategy": your_strategy_name,
        "expected_base_points": float(your_points.mean()),
        "expected_wins": float(your_wins.mean()),
        "P(get_Most_Wins_bonus)": float(your_mw_bonus.mean()),
        "P(get_Most_Points_bonus)": float(your_mp_bonus.mean()),
        "expected_bonus_points": float(5*your_mw_bonus.mean() + 10*your_mp_bonus.mean()),
        "expected_total_points": float(your_totals.mean()),
        "stdev_total_points": float(your_totals.std(ddof=1)),
        "p10_total_points": float(np.percentile(your_totals, 10)),
        "p50_total_points": float(np.percentile(your_totals, 50)),
        "p90_total_points": float(np.percentile(your_totals, 90)),
    }
    return summary

# ===============================
# 5) PREDICTION STORAGE
# ===============================

def save_predictions(strategy_name: str, picks: np.ndarray, confidence: np.ndarray, 
                    week_mapping: list[dict], game_probs: np.ndarray = None) -> str:
    """
    Save strategy predictions to JSON file following the existing file naming pattern.
    Returns the filename of the saved file.
    """
    # Create out directory if it doesn't exist
    os.makedirs("out", exist_ok=True)
    
    # Get current week and timestamp
    current_week = get_current_nfl_week()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    strategy_code = STRATEGY_CODES.get(strategy_name, strategy_name.lower().replace("-", ""))
    
    # Build filename following existing pattern
    filename = f"week_{current_week}_predictions_{strategy_code}_{timestamp}.json"
    filepath = os.path.join("out", filename)
    
    # Build prediction data structure
    predictions = {
        "metadata": {
            "strategy": strategy_name,
            "week": current_week,
            "generated_at": datetime.now().isoformat(),
            "total_games": len(week_mapping),
            "simulator_version": "v2"
        },
        "games": []
    }
    
    # Add each game with predictions
    for i, game in enumerate(week_mapping):
        pick_team = game["favorite"] if picks[i] == 1 else game["dog"]
        pick_is_favorite = bool(picks[i] == 1)
        
        game_data = {
            "game_id": game.get("id", f"game_{i+1}"),
            "away_team": game["away_team"],
            "home_team": game["home_team"],
            "favorite": game["favorite"],
            "dog": game["dog"],
            "favorite_prob": float(game["p_fav"]),
            "commence_time": game.get("commence_time"),
            "prediction": {
                "pick_team": pick_team,
                "pick_is_favorite": pick_is_favorite,
                "confidence_level": int(confidence[i]),
                "confidence_rank": int(len(week_mapping) - confidence[i] + 1)  # 1 = highest confidence
            }
        }
        predictions["games"].append(game_data)
    
    # Sort games by confidence level (highest first)
    predictions["games"].sort(key=lambda x: x["prediction"]["confidence_level"], reverse=True)
    
    # Save to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(predictions, f, indent=2, ensure_ascii=False)
    
    return filename

# ===============================
# 6) VALIDATION & DISPLAY
# ===============================

def validate_slate(mapping: list[dict], min_g=SLATE_MIN_GAMES, max_g=SLATE_MAX_GAMES):
    n = len(mapping)
    if n == 0:
        print("[ERROR] No games found for the current week window.")
        sys.exit(1)

    # Check for missing games (likely already started or API issues)
    EXPECTED_MIN_GAMES = 14  # Typical NFL week (adjust for bye weeks)
    if n < EXPECTED_MIN_GAMES:
        print(f"[WARNING] Only {n} games found (expected {EXPECTED_MIN_GAMES}+ for typical week)")
        print("          Possible causes:")
        print("          - Some games have already started (excluded from betting markets)")
        print("          - API issues or rate limiting")
        print("          - Bye weeks (Weeks 5-14 typically have 13-14 games)")

        # Interactive confirmation
        response = input(f"\nContinue with only {n} games? (y/n): ").strip().lower()
        if response != 'y':
            print("Exiting. Please check game schedule and run simulator before games start.")
            sys.exit(1)

    if not (min_g <= n <= max_g):
        print(f"[WARN] Unexpected number of games returned: {n} (expected {min_g}–{max_g}).")
        print("       Check time window, bye weeks, or API filters.")
    else:
        print(f"[OK] {n} games found within the current NFL week window.")

    # Show a compact slate preview
    print("\nSlate preview (favorite vs dog, p_fav):")
    for i, g in enumerate(mapping, 1):
        fav = g["favorite"]; dog = g["dog"]; p = g["p_fav"]
        when = g.get("commence_time")
        print(f" {i:>2}. {fav} vs {dog} | p_fav={p:.3f} | commence={when}")

# ===============================
# 8) COMMAND LINE INTERFACE
# ===============================

def parse_arguments():
    """Parse command line arguments for user picks."""
    parser = argparse.ArgumentParser(description="NFL Confidence Pool Strategy Simulator")
    parser.add_argument("--user-picks", type=str, 
                       help="Comma-separated list of team names in confidence order (16->1)")
    parser.add_argument("--picks-file", type=str,
                       help="Path to JSON file containing user picks")
    parser.add_argument("--analyze-only", action="store_true",
                       help="Only analyze user picks, skip built-in strategies")
    return parser.parse_args()

# ===============================
# 9) MAIN
# ===============================

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Build GAME_PROBS from API (or fallback)
    try:
        GAME_PROBS, WEEK_MAPPING = get_weekly_GAME_PROBS_from_odds()
        print(f"Loaded {len(GAME_PROBS)} games from The Odds API.")
    except Exception as e:
        print("[WARN] Odds fetch failed, using fallback slate. Reason:", str(e))
        GAME_PROBS, WEEK_MAPPING = fallback_GAME_PROBS()

    # Validate slate size & preview
    validate_slate(WEEK_MAPPING)

    # Handle user picks if provided
    user_summary = None
    user_picks = None
    user_confidence = None
    
    if args.user_picks or args.picks_file:
        print("\n" + "="*60)
        print("ANALYZING YOUR CUSTOM PICKS")
        print("="*60)
        
        try:
            if args.picks_file:
                # Load from JSON file
                with open(args.picks_file, 'r') as f:
                    picks_data = json.load(f)
                user_input = picks_data.get("picks", [])
            else:
                user_input = args.user_picks
            
            # Simulate user picks
            result = simulate_user_picks(user_input, WEEK_MAPPING, GAME_PROBS, STRATEGY_MIX)
            if result:
                user_summary, user_picks, user_confidence = result
                
                # Analyze picks
                analysis = analyze_user_picks(user_picks, user_confidence, WEEK_MAPPING, GAME_PROBS)
                
                print(f"\nYour Custom Pick Analysis:")
                print(f"Expected Performance: {user_summary['expected_total_points']:.2f} total points")
                print(f"Expected Wins: {user_summary['expected_wins']:.2f}")
                print(f"Risk Assessment: {analysis['risk_assessment']}")
                print(f"Contrarian Picks: {analysis['contrarian_count']}")
                
                if analysis['contrarian_picks']:
                    print(f"\nContrarian Games:")
                    for game in analysis['contrarian_picks']:
                        print(f"  {game['game']} -> {game['pick']} (Conf: {game['confidence']}, Prob: {game['pick_prob']:.1%})")
                
                # Save user predictions
                user_filename = save_predictions("Custom-User", user_picks, user_confidence, WEEK_MAPPING, GAME_PROBS)
                print(f"\nYour picks saved to: out/{user_filename}")
                
        except Exception as e:
            print(f"Error analyzing user picks: {e}")
            return
    
    # Skip built-in strategies if analyze-only mode
    if args.analyze_only and user_summary:
        print(f"\nAnalysis complete. Your expected performance: {user_summary['expected_total_points']:.2f} points")
        return

    # Compare strategies vs the field
    USER_STRATEGIES_TO_TEST = [
        "Chalk-MaxPoints",
        "Slight-Contrarian",
        "Aggressive-Contrarian",
        "Random-MidShuffle",
    ]

    results = []
    for sname in USER_STRATEGIES_TO_TEST:
        summary = simulate_many_weeks(GAME_PROBS, sname, STRATEGY_MIX, n_sims=N_SIMS)
        results.append(summary)

    # Add user picks to comparison if provided
    if user_summary:
        results.append(user_summary)

    df = pd.DataFrame(results).sort_values("expected_total_points", ascending=False)
    
    print("\nConfidence Pool Strategy — Monte Carlo Summary")
    if user_summary:
        print("(Including your custom picks)")
    print(df.round(4).to_string(index=False))

    # 6d) Plot
    plt.figure(figsize=(8, 4.5))
    plt.bar(df["strategy"], df["expected_total_points"])
    plt.title("Expected Weekly Total (Base + Bonuses) by Strategy")
    plt.ylabel("Expected total points")
    plt.xlabel("Strategy")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.show()

    # Save strategy summary CSV following established naming pattern
    current_week = get_current_nfl_week()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"week_{current_week}_strategy_summary_{timestamp}.csv"
    out_path = os.path.join("out", out_filename)
    
    # Ensure out directory exists
    os.makedirs("out", exist_ok=True)
    
    df.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")

    # Pick a strategy to actually use
    my_strategy_name = "Random-MidShuffle"          # choose your strategy here
    my_strategy = STRATEGIES[my_strategy_name]

    # Generate picks + confidence ordering
    picks, conf = my_strategy(GAME_PROBS)

    # Save predictions to file
    saved_filename = save_predictions(my_strategy_name, picks, conf, WEEK_MAPPING, GAME_PROBS)
    print(f"\nPredictions saved to: out/{saved_filename}")

    # Also save predictions for all strategies tested
    print("\nSaving predictions for all tested strategies...")
    for strategy_name in USER_STRATEGIES_TO_TEST:
        strategy_func = STRATEGIES[strategy_name]
        strategy_picks, strategy_conf = strategy_func(GAME_PROBS)
        strategy_filename = save_predictions(strategy_name, strategy_picks, strategy_conf, WEEK_MAPPING, GAME_PROBS)
        print(f"  {strategy_name}: out/{strategy_filename}")

    print(f"\nYour picks this week using {my_strategy_name}:\n")
    for i, g in enumerate(WEEK_MAPPING, 1):
        pick_team = g["favorite"] if picks[i-1] == 1 else g["dog"]
        print(f"{i:>2}. {g['away_team']} at {g['home_team']}")
        print(f"    → PICK: {pick_team}, CONFIDENCE: {conf[i-1]}")


if __name__ == "__main__":
    main()
