# Confidence Pool Strategy Simulator
#
# This notebook simulates weekly outcomes in an NFL-style confidence pool
# with 32 participants, two weekly bonuses:
#  - Most Wins bonus: +5 points (awarded to all tied for most wins)
#  - Most Points bonus: +10 points (awarded to all tied for most points)
#
# You (the "user") can be assigned different strategies, and the rest of the field
# can be a mix of strategies. We estimate expected base points, wins, bonus win rates,
# and total weekly EV using Monte Carlo.
#
# How to customize:
# 1) Edit GAME_PROBS below (list of favorite win probabilities for each game).
# 2) Adjust STRATEGY_MIX for the other 31 players.
# 3) Add/modify strategies in `STRATEGIES` if desired.
#
# Then re-run.

import numpy as np
import pandas as pd
import random
import matplotlib.pyplot as plt

# ------------------------------
# 1) Inputs
# ------------------------------

# Example slate of 16 games with favorite win probabilities.
# Edit these with real probabilities (e.g., from betting markets) if you like.
# Structure: p = probability the FAVORITE wins that game.
# (Outcomes will be simulated as 1 = favorite wins, 0 = underdog wins)
np.random.seed(42)
random.seed(42)

# Construct a realistic-ish spread of probabilities:
#  - 4 heavy favorites: 0.78 - 0.85
#  - 6 moderate favorites: 0.62 - 0.70
#  - 4 close-ish: 0.54 - 0.58
#  - 2 near pick'em: 0.50 - 0.52
heavy = list(np.random.uniform(0.78, 0.85, 4))
moderate = list(np.random.uniform(0.62, 0.70, 6))
closeish = list(np.random.uniform(0.54, 0.58, 4))
pickem = list(np.random.uniform(0.50, 0.52, 2))
GAME_PROBS = np.array(heavy + moderate + closeish + pickem)
np.random.shuffle(GAME_PROBS)

NUM_GAMES = len(GAME_PROBS)
LEAGUE_SIZE = 32             # total players (you + 31 others)
N_OTHERS = LEAGUE_SIZE - 1
N_SIMS = 20000               # number of Monte Carlo weeks to simulate

# Mix of other players' strategies in the league
# (keys must be names that exist in STRATEGIES below)
STRATEGY_MIX = {
    "Chalk-MaxPoints": 16,       # pick favorites, rank by probability (max EV for points)
    "Slight-Contrarian": 10,     # 1-2 contrarian picks among coin-flips, 1 mid-confidence boost
    "Aggressive-Contrarian": 5,  # 3-5 contrarian picks incl. some moderate dogs, 1-2 mid-high boosts
}

assert sum(STRATEGY_MIX.values()) == N_OTHERS, "STRATEGY_MIX must sum to 31 (others in league)"

# ------------------------------
# 2) Strategy definitions
# ------------------------------

def assign_confidence_order(order_indices, num_games):
    """Given an ordering of indices from most to least confident, return 1..N mapping."""
    conf = np.zeros(num_games, dtype=int)
    # highest confidence gets N, next N-1, ..., last gets 1
    for rank, idx in enumerate(order_indices):
        conf[idx] = num_games - rank
    return conf

def order_by_probability_desc(p):
    return list(np.argsort(-p))

def confidence_by_probability(p):
    return assign_confidence_order(order_by_probability_desc(p), len(p))

def picks_favorites(p):
    # 1 = favorite, 0 = underdog
    return np.ones_like(p, dtype=int)

def picks_with_contrarians(p, num_coinflip_dogs=2, num_moderate_dogs=0):
    """
    Start from picking favorites, then flip a certain number of games to underdogs:
      - among near-coinflips (|p-0.5| <= 0.06)
      - among moderate favorites (0.58 < p <= 0.66)
    """
    picks = picks_favorites(p)
    idx_coinflip = [i for i, x in enumerate(p) if abs(x - 0.5) <= 0.06]
    idx_moderate = [i for i, x in enumerate(p) if 0.58 < x <= 0.66]

    # Select contrarian targets
    random.shuffle(idx_coinflip)
    random.shuffle(idx_moderate)

    for i in idx_coinflip[:num_coinflip_dogs]:
        picks[i] = 0  # underdog

    for i in idx_moderate[:num_moderate_dogs]:
        picks[i] = 0  # underdog

    return picks

def reorder_with_mid_boost(base_order, boost_indices, target_positions):
    """
    Move specified indices into desired target positions (list of positions in the order array).
    Positions are 0-based where 0 is most confident.
    """
    order = [x for x in base_order if x not in boost_indices]
    # Clip target positions to valid range and avoid duplicates
    used_positions = set()
    for idx, pos in zip(boost_indices, target_positions):
        pos = int(max(0, min(len(order), pos)))
        # adjust if occupied
        while pos in used_positions:
            pos += 1
        used_positions.add(pos)
        order.insert(pos, idx)
    return order

def strategy_chalk_maxpoints(p):
    picks = picks_favorites(p)
    conf = confidence_by_probability(p)
    return picks, conf

def strategy_slight_contrarian(p):
    picks = picks_with_contrarians(p, num_coinflip_dogs=2, num_moderate_dogs=0)
    base_order = order_by_probability_desc(p)
    # Boost one contrarian (if any) into mid confidence (positions near middle)
    contrarian_idxs = [i for i, pick in enumerate(picks) if pick == 0]
    if contrarian_idxs:
        # Middle positions roughly around NUM_GAMES*0.55
        mid_pos = int(NUM_GAMES * 0.55)
        order = reorder_with_mid_boost(base_order, [contrarian_idxs[0]], [mid_pos])
    else:
        order = base_order
    conf = assign_confidence_order(order, len(p))
    return picks, conf

def strategy_aggressive_contrarian(p):
    picks = picks_with_contrarians(p, num_coinflip_dogs=3, num_moderate_dogs=2)
    base_order = order_by_probability_desc(p)
    # Boost up to two contrarians into mid/high positions
    contrarian_idxs = [i for i, pick in enumerate(picks) if pick == 0]
    boost = contrarian_idxs[:2]
    targets = [int(NUM_GAMES * 0.65), int(NUM_GAMES * 0.5)] if len(boost) >= 2 else [int(NUM_GAMES * 0.65)]
    order = reorder_with_mid_boost(base_order, boost, targets)
    conf = assign_confidence_order(order, len(p))
    return picks, conf

def strategy_random_midshuffle(p):
    picks = picks_favorites(p)
    # Sort by p, but shuffle within the middle band to reduce correlation
    order = order_by_probability_desc(p)
    n = len(order)
    lo, hi = int(n * 0.30), int(n * 0.75)
    mid_slice = order[lo:hi]
    random.shuffle(mid_slice)
    order = order[:lo] + mid_slice + order[hi:]
    conf = assign_confidence_order(order, len(p))
    return picks, conf

STRATEGIES = {
    "Chalk-MaxPoints": strategy_chalk_maxpoints,
    "Slight-Contrarian": strategy_slight_contrarian,
    "Aggressive-Contrarian": strategy_aggressive_contrarian,
    "Random-MidShuffle": strategy_random_midshuffle,
}

# ------------------------------
# 3) Simulation engine
# ------------------------------

def simulate_week_once(p, player_strategies):
    """
    Simulate one week given:
      p: array of favorite win probabilities (length N games)
      player_strategies: list of strategy callables, one per player (len = league size)
    Returns:
      wins (array), points (array), total_points_including_bonuses (array)
    Notes:
      - Most Wins bonus: +5 to all tied for most wins
      - Most Points bonus: +10 to all tied for most points
    """
    N = len(player_strategies)
    G = len(p)

    # Simulate game outcomes: 1 if favorite wins, else 0
    outcomes = (np.random.rand(G) < p).astype(int)

    wins = np.zeros(N, dtype=int)
    points = np.zeros(N, dtype=int)

    # Each player creates picks/conf and scores
    for j, strat_fn in enumerate(player_strategies):
        picks, conf = strat_fn(p)
        correct = (picks == outcomes).astype(int)
        wins[j] = int(correct.sum())
        points[j] = int(np.dot(correct, conf))

    # Bonuses (award full bonus to all tied winners)
    max_wins = wins.max()
    max_points = points.max()
    most_wins_bonus = (wins == max_wins).astype(int) * 5
    most_points_bonus = (points == max_points).astype(int) * 10

    total = points + most_wins_bonus + most_points_bonus
    return wins, points, total, most_wins_bonus, most_points_bonus

def simulate_many_weeks(p, your_strategy_name, others_mix, n_sims=5000):
    """
    Simulate n_sims weeks with you using `your_strategy_name` and
    the other N_OTHERS players using `others_mix`.
    Returns a dict of summary stats and per-sim totals for distribution metrics.
    """
    your_strategy = STRATEGIES[your_strategy_name]

    # Build list of strategies for the league (you at index 0)
    others = []
    for name, count in others_mix.items():
        fn = STRATEGIES[name]
        others.extend([fn] * count)
    assert len(others) == N_OTHERS

    # We'll keep you at index 0 and shuffle the others each sim for realism
    your_totals = []
    your_points = []
    your_wins = []
    your_mw_bonus = []   # Most Wins bonus hits
    your_mp_bonus = []   # Most Points bonus hits

    for _ in range(n_sims):
        random.shuffle(others)
        players = [your_strategy] + others
        wins, points, total, mw_bonus, mp_bonus = simulate_week_once(p, players)
        your_totals.append(total[0])
        your_points.append(points[0])
        your_wins.append(wins[0])
        your_mw_bonus.append(1 if mw_bonus[0] > 0 else 0)
        your_mp_bonus.append(1 if mp_bonus[0] > 0 else 0)

    your_totals = np.array(your_totals)
    your_points = np.array(your_points)
    your_wins = np.array(your_wins)
    your_mw_bonus = np.array(your_mw_bonus)
    your_mp_bonus = np.array(your_mp_bonus)

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
    dist = {
        "totals": your_totals,
        "points": your_points,
        "wins": your_wins,
    }
    return summary, dist

# ------------------------------
# 4) Run sims for several user strategies
# ------------------------------

USER_STRATEGIES_TO_TEST = [
    "Chalk-MaxPoints",
    "Slight-Contrarian",
    "Aggressive-Contrarian",
    "Random-MidShuffle",
]

summaries = []
dists = {}

for sname in USER_STRATEGIES_TO_TEST:
    summary, dist = simulate_many_weeks(GAME_PROBS, sname, STRATEGY_MIX, n_sims=N_SIMS)
    summaries.append(summary)
    dists[sname] = dist

df = pd.DataFrame(summaries).sort_values("expected_total_points", ascending=False)

# Show the slate probabilities for reference
slate_df = pd.DataFrame({"game": np.arange(1, NUM_GAMES+1), "favorite_win_prob": GAME_PROBS})
print("Weekly slate favorite win probabilities:\n", slate_df.round(3))
print("\nConfidence Pool Strategy — Monte Carlo Summary:\n", df.round(4))

# ------------------------------
# 5) Plot: Expected total weekly points (with bonuses)
# ------------------------------

plt.figure(figsize=(8, 4.5))
plt.bar(df["strategy"], df["expected_total_points"])
plt.title("Expected Weekly Total (Base + Bonuses) by Strategy")
plt.ylabel("Expected total points")
plt.xlabel("Strategy")
plt.xticks(rotation=20, ha="right")
plt.tight_layout()
plt.show()

# Save CSV for download (works in most environments)
out_path = "confidence_pool_strategy_summary.csv"
df.to_csv(out_path, index=False)
print(f"Saved: {out_path}")
