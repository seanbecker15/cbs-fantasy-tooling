"""User pick analysis and simulation."""

import random
import numpy as np
from cbs_fantasy_tooling.analysis.user.picks import parse_user_picks, create_user_strategy
from cbs_fantasy_tooling.analysis.core.config import N_SIMS, N_OTHERS
from cbs_fantasy_tooling.analysis.core.strategies import STRATEGIES
from cbs_fantasy_tooling.analysis.core.simulator import simulate_week_once


def simulate_user_picks(user_input: str | list, week_mapping: list[dict], game_probs: np.ndarray,
                       others_mix: dict, n_sims: int = N_SIMS) -> dict | None:
    """
    Simulate user picks against the field using Monte Carlo analysis.

    Args:
        user_input: User's picks (string or list)
        week_mapping: Current week's games
        game_probs: Win probabilities
        others_mix: Field composition
        n_sims: Number of simulations

    Returns:
        Summary statistics dictionary or None if parsing failed
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

    user_totals = []
    user_points = []
    user_wins = []
    user_mw_bonus = []
    user_mp_bonus = []

    for _ in range(n_sims):
        random.shuffle(others)
        players = [user_strategy] + others
        wins, points, total, mw_bonus, mp_bonus = simulate_week_once(game_probs, players)
        user_totals.append(total[0])
        user_points.append(points[0])
        user_wins.append(wins[0])
        user_mw_bonus.append(1 if mw_bonus[0] > 0 else 0)
        user_mp_bonus.append(1 if mp_bonus[0] > 0 else 0)

    user_totals = np.array(user_totals)
    user_points = np.array(user_points)
    user_wins = np.array(user_wins)
    user_mw_bonus = np.array(user_mw_bonus)
    user_mp_bonus = np.array(user_mp_bonus)

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

    Args:
        user_picks: User's picks array
        user_confidence: User's confidence levels
        week_mapping: Current week's games
        game_probs: Win probabilities

    Returns:
        Analysis dictionary with metrics and categorizations
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
