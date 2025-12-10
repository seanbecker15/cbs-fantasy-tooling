"""
Confidence Pool Strategy Simulator

Main orchestration for running Monte Carlo simulations of confidence pool strategies.
"""

from typing import Dict, Optional
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd

from cbs_fantasy_tooling.ingest.the_odds_api.api import fetch_odds

from cbs_fantasy_tooling.analysis.core.config import N_SIMS, SHARP_BOOKS, SHARP_WEIGHT, get_field_composition
from cbs_fantasy_tooling.analysis.core.strategies import STRATEGIES
from cbs_fantasy_tooling.analysis.core.simulator import simulate_many_weeks
from cbs_fantasy_tooling.analysis.odds.converter import consensus_moneyline_probs, rows_to_game_probs
from cbs_fantasy_tooling.analysis.utils.validation import validate_slate
from cbs_fantasy_tooling.analysis.utils.storage import save_predictions
from cbs_fantasy_tooling.analysis.user.analysis import simulate_user_picks, analyze_user_picks
from cbs_fantasy_tooling.utils.date import get_commence_time_from, get_commence_time_to, get_current_nfl_week


def run_strategy_simulation(
    user_picks: Optional[str | list] = None,
    analyze_only: bool = False,
    n_sims: int = N_SIMS
) -> Dict:
    """
    Run Monte Carlo simulation of confidence pool strategies.

    Args:
        user_picks: Optional user picks to analyze
        analyze_only: If True, only analyze user picks without running all strategies
        n_sims: Number of Monte Carlo simulations to run

    Returns:
        Dictionary with simulation results and recommendations
    """
    # Get field composition
    strategy_mix = get_field_composition()

    # Load odds data
    game_probs, week_mapping = get_weekly_game_probs_from_odds()
    print(f"Loaded {len(game_probs)} games from The Odds API.")

    # Validate slate
    validate_slate(week_mapping)

    results = {
        "game_probs": game_probs,
        "week_mapping": week_mapping,
        "strategy_mix": strategy_mix,
        "strategies": [],
        "user_analysis": None,
    }

    # Handle user picks if provided
    if user_picks:
        print("\n" + "="*60)
        print("ANALYZING YOUR CUSTOM PICKS")
        print("="*60)

        result = simulate_user_picks(user_picks, week_mapping, game_probs, strategy_mix, n_sims)
        if result:
            user_summary, picks, confidence = result

            # Analyze picks
            analysis = analyze_user_picks(picks, confidence, week_mapping, game_probs)

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
            user_filename = save_predictions("Custom-User", picks, confidence, week_mapping, game_probs)
            print(f"\nYour picks saved to: out/{user_filename}")

            results["user_analysis"] = {
                "summary": user_summary,
                "analysis": analysis,
                "filename": user_filename,
            }

            if analyze_only:
                return results

    # Run all strategies
    strategies_to_test = [
        "Chalk-MaxPoints",
        "Slight-Contrarian",
        "Aggressive-Contrarian",
        "Random-MidShuffle",
    ]

    strategy_results = []
    for strategy_name in strategies_to_test:
        summary = simulate_many_weeks(game_probs, strategy_name, strategy_mix, n_sims=n_sims)
        strategy_results.append(summary)

        # Save predictions
        strategy_func = STRATEGIES[strategy_name]
        picks, conf = strategy_func(game_probs)
        filename = save_predictions(strategy_name, picks, conf, week_mapping, game_probs)
        summary["prediction_file"] = filename

    # Add user summary to comparison if provided
    if results["user_analysis"]:
        strategy_results.append(results["user_analysis"]["summary"])

    results["strategies"] = strategy_results
    results["comparison_df"] = pd.DataFrame(strategy_results).sort_values("expected_total_points", ascending=False)

    user_summary = results["user_analysis"]["summary"] if results["user_analysis"] else None
    display_results(results["comparison_df"], user_summary)

    # Save results
    save_results(results["comparison_df"], week_mapping, game_probs)

    # Display recommendations
    display_recommendations(week_mapping, game_probs)

    return results

def get_weekly_game_probs_from_odds() -> tuple[np.ndarray, list[dict]]:
    """
    Master function: fetch odds → consensus de-vig → GAME_PROBS with mapping.

    Returns:
        Tuple of (game_probs_array, week_mapping)

    Raises:
        RuntimeError: If API key not set or no games returned
    """
    from_date = get_commence_time_from()
    to_date = get_commence_time_to()
    events = fetch_odds(from_date, to_date)
    rows = consensus_moneyline_probs(events, SHARP_BOOKS, SHARP_WEIGHT)
    if not rows:
        raise RuntimeError("No rows built from odds response. Check API key, region, time window, or timing.")
    return rows_to_game_probs(rows)


def display_results(df, user_summary):
    """Display results table and chart."""
    print("\nConfidence Pool Strategy — Monte Carlo Summary")
    if user_summary:
        print("(Including your custom picks)")
    print(df.round(4).to_string(index=False))

    # Plot results
    plt.figure(figsize=(8, 4.5))
    plt.bar(df["strategy"], df["expected_total_points"])
    plt.title("Expected Weekly Total (Base + Bonuses) by Strategy")
    plt.ylabel("Expected total points")
    plt.xlabel("Strategy")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.show()


def save_results(df, week_mapping, game_probs):
    """Save strategy summary and all predictions."""
    import os

    # Save strategy summary CSV
    current_week = get_current_nfl_week()
    out_filename = f"week_{current_week}_strategy_summary.csv"
    out_path = os.path.join("out", out_filename)

    os.makedirs("out", exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")

    # Save predictions for all strategies
    print("\nSaving predictions for all tested strategies...")
    strategies_to_save = ["Chalk-MaxPoints", "Slight-Contrarian", "Aggressive-Contrarian", "Random-MidShuffle"]

    for strategy_name in strategies_to_save:
        strategy_func = STRATEGIES[strategy_name]
        picks, conf = strategy_func(game_probs)
        filename = save_predictions(strategy_name, picks, conf, week_mapping, game_probs)
        print(f"  {strategy_name}: out/{filename}")


def display_recommendations(week_mapping, game_probs, recommended_strategy="Random-MidShuffle"):
    """Display pick recommendations for a specific strategy."""
    strategy = STRATEGIES[recommended_strategy]
    picks, conf = strategy(game_probs)

    print(f"\nYour picks this week using {recommended_strategy}:\n")
    for i, g in enumerate(week_mapping, 1):
        pick_team = g["favorite"] if picks[i-1] == 1 else g["dog"]
        print(f"{i:>2}. {g['away_team']} at {g['home_team']}")
        print(f"    → PICK: {pick_team}, CONFIDENCE: {conf[i-1]}")
