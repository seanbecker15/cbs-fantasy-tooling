"""Confidence pool betting strategies."""

import random
import numpy as np


def assign_confidence_order(order_indices, num_games):
    """Assign confidence levels based on ordered game indices."""
    conf = np.zeros(num_games, dtype=int)
    for rank, idx in enumerate(order_indices):
        conf[idx] = num_games - rank
    return conf


def order_by_probability_desc(p):
    """Return game indices ordered by probability (descending)."""
    return list(np.argsort(-p))


def confidence_by_probability(p):
    """Assign confidence levels based on win probability."""
    return assign_confidence_order(order_by_probability_desc(p), len(p))


def picks_favorites(p):
    """Pick all favorites (return all 1s)."""
    return np.ones_like(p, dtype=int)


def picks_with_contrarians(p, num_coinflip_dogs=2, num_moderate_dogs=0):
    """
    Pick mostly favorites with some strategic contrarian picks.

    Args:
        p: Win probabilities for favorites
        num_coinflip_dogs: Number of near-tossup underdogs to pick
        num_moderate_dogs: Number of moderate underdogs to pick

    Returns:
        Picks array (1=favorite, 0=underdog)
    """
    picks = picks_favorites(p)
    idx_coinflip = [i for i, x in enumerate(p) if abs(x - 0.5) <= 0.06]
    idx_moderate = [i for i, x in enumerate(p) if 0.58 < x <= 0.66]
    random.shuffle(idx_coinflip)
    random.shuffle(idx_moderate)
    for i in idx_coinflip[:num_coinflip_dogs]:
        picks[i] = 0
    for i in idx_moderate[:num_moderate_dogs]:
        picks[i] = 0
    return picks


def reorder_with_mid_boost(base_order, boost_indices, target_positions):
    """
    Reorder picks to boost certain games to mid-confidence positions.

    Args:
        base_order: Base ordering of game indices
        boost_indices: Indices of games to boost
        target_positions: Target positions for boosted games

    Returns:
        Reordered game indices
    """
    order = [x for x in base_order if x not in boost_indices]
    used = set()
    for idx, pos in zip(boost_indices, target_positions):
        pos = max(0, min(len(order), int(pos)))
        while pos in used:
            pos += 1
        used.add(pos)
        order.insert(pos, idx)
    return order


# ===============================
# Strategy Implementations
# ===============================


def strategy_chalk_maxpoints(p):
    """
    Chalk-MaxPoints: Pick all favorites, order by probability.
    Pure favorite-picking strategy with minimal risk.
    """
    return picks_favorites(p), confidence_by_probability(p)


def strategy_slight_contrarian(p):
    """
    Slight-Contrarian: Strategic contrarian picks on coin-flip games.
    Picks 2 near-tossup underdogs and boosts one to mid-confidence.
    """
    picks = picks_with_contrarians(p, num_coinflip_dogs=2, num_moderate_dogs=0)
    base_order = order_by_probability_desc(p)
    contrarians = [i for i, pick in enumerate(picks) if pick == 0]
    order = (
        reorder_with_mid_boost(base_order, contrarians[:1], [int(len(p) * 0.55)])
        if contrarians
        else base_order
    )
    return picks, assign_confidence_order(order, len(p))


def strategy_aggressive_contrarian(p):
    """
    Aggressive-Contrarian: Multiple contrarian picks including moderate underdogs.
    Picks 3 coin-flip underdogs + 2 moderate underdogs with strategic positioning.
    """
    picks = picks_with_contrarians(p, num_coinflip_dogs=3, num_moderate_dogs=2)
    base_order = order_by_probability_desc(p)
    contrarians = [i for i, pick in enumerate(picks) if pick == 0][:2]
    targets = [int(len(p) * 0.65), int(len(p) * 0.50)][: len(contrarians)]
    order = reorder_with_mid_boost(base_order, contrarians, targets)
    return picks, assign_confidence_order(order, len(p))


def strategy_random_midshuffle(p):
    """
    Random-MidShuffle: Probability-based ordering with middle-tier shuffling.
    Reduces correlation with field by shuffling middle 30-75% of confidence levels.
    """
    picks = picks_favorites(p)
    order = order_by_probability_desc(p)
    n = len(order)
    lo, hi = int(n * 0.30), int(n * 0.75)
    mid = order[lo:hi]
    random.shuffle(mid)
    order = order[:lo] + mid + order[hi:]
    return picks, assign_confidence_order(order, len(p))


# Strategy registry
STRATEGIES = {
    "Chalk-MaxPoints": strategy_chalk_maxpoints,
    "Slight-Contrarian": strategy_slight_contrarian,
    "Aggressive-Contrarian": strategy_aggressive_contrarian,
    "Random-MidShuffle": strategy_random_midshuffle,
}
