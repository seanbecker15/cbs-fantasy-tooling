"""Monte Carlo simulation engine for confidence pool strategies."""

import random
import numpy as np
from cbs_fantasy_tooling.analysis.core.config import BONUS_SPLIT_TIES, N_OTHERS
from cbs_fantasy_tooling.analysis.core.strategies import STRATEGIES


def _apply_bonuses(wins, points):
    """
    Calculate bonus points for most wins and most points.

    Returns arrays for most_wins_bonus, most_points_bonus, given global BONUS_SPLIT_TIES.
    +5 for Most Wins, +10 for Most Points; either full to ties or split equally.

    Args:
        wins: Array of win counts per player
        points: Array of base points per player

    Returns:
        Tuple of (most_wins_bonus, most_points_bonus) arrays
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
    """
    Simulate a single week with given probabilities and player strategies.

    Args:
        p: Array of favorite win probabilities per game
        player_strategies: List of strategy functions

    Returns:
        Tuple of (wins, points, total, most_wins_bonus, most_points_bonus)
    """
    G = len(p)
    N = len(player_strategies)
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
    """
    Run Monte Carlo simulation for a given strategy against the field.

    Args:
        p: Array of favorite win probabilities per game
        your_strategy_name: Name of strategy to test
        others_mix: Dictionary mapping strategy names to counts (field composition)
        n_sims: Number of simulations to run

    Returns:
        Dictionary with performance statistics
    """
    your_strategy = STRATEGIES[your_strategy_name]
    others = []
    for name, count in others_mix.items():
        others.extend([STRATEGIES[name]] * count)
    assert len(others) == N_OTHERS

    your_totals = []
    your_points = []
    your_wins = []
    your_mw_bonus = []
    your_mp_bonus = []

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
    return summary
