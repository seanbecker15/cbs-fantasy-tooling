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
from dotenv import load_dotenv
from datetime import datetime, timedelta, time, timezone
from statistics import median

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

# Field composition (others in your 32-person league)
STRATEGY_MIX = {
    "Chalk-MaxPoints": 16,
    "Slight-Contrarian": 10,
    "Aggressive-Contrarian": 5,
}
assert sum(STRATEGY_MIX.values()) == N_OTHERS, "STRATEGY_MIX must sum to 31."

# ===============================
# 1) TIME WINDOW HELPERS (CURRENT NFL WEEK)
# ===============================

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
# 5) VALIDATION & DISPLAY
# ===============================

def validate_slate(mapping: list[dict], min_g=SLATE_MIN_GAMES, max_g=SLATE_MAX_GAMES):
    n = len(mapping)
    if n == 0:
        print("[ERROR] No games found for the current week window.")
        return
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
# 6) MAIN
# ===============================

def main():
    # 6a) Build GAME_PROBS from API (or fallback)
    try:
        GAME_PROBS, WEEK_MAPPING = get_weekly_GAME_PROBS_from_odds()
        print(f"Loaded {len(GAME_PROBS)} games from The Odds API.")
    except Exception as e:
        print("[WARN] Odds fetch failed, using fallback slate. Reason:", str(e))
        GAME_PROBS, WEEK_MAPPING = fallback_GAME_PROBS()

    # 6b) Validate slate size & preview
    validate_slate(WEEK_MAPPING)

    # 6c) Compare user strategies vs the field
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

    df = pd.DataFrame(results).sort_values("expected_total_points", ascending=False)
    print("\nConfidence Pool Strategy — Monte Carlo Summary")
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

    # Save CSV
    out_path = "confidence_pool_strategy_summary.csv"
    df.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")

    # Pick a strategy to actually use
    my_strategy_name = "Random-MidShuffle"          # choose your strategy here
    my_strategy = STRATEGIES[my_strategy_name]

    # Generate picks + confidence ordering
    picks, conf = my_strategy(GAME_PROBS)

    print(f"\nYour picks this week using {my_strategy_name}:\n")
    for i, g in enumerate(WEEK_MAPPING, 1):
        pick_team = g["favorite"] if picks[i-1] == 1 else g["dog"]
        print(f"{i:>2}. {g['away_team']} at {g['home_team']}")
        print(f"    → PICK: {pick_team}, CONFIDENCE: {conf[i-1]}")


if __name__ == "__main__":
    main()
