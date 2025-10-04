"""
Field Composition Adapter

Adapts real competitor data to the simulator's STRATEGY_MIX format.
Replaces theoretical assumptions with actual player strategy distributions.

Usage:
    from field_adapter import get_actual_field_composition

    STRATEGY_MIX = get_actual_field_composition()
    # Returns: {"Chalk-MaxPoints": 17, "Slight-Contrarian": 14, "Aggressive-Contrarian": 1}
"""

from typing import Dict
from data_loader import load_competitor_data
from data_enrichment import full_enrichment_pipeline
from competitor_classifier import build_player_profiles, analyze_league_composition


def get_actual_field_composition(data_dir: str = "../out", exclude_user: str = None) -> Dict[str, int]:
    """
    Get actual league field composition from historical data.

    Args:
        data_dir: Directory containing week result JSON files
        exclude_user: Player name to exclude (e.g., "User Name" for user's own picks)

    Returns:
        Dictionary of strategy counts compatible with main.py STRATEGY_MIX format
        Example: {"Chalk-MaxPoints": 17, "Slight-Contrarian": 14, "Aggressive-Contrarian": 1}
    """
    # Load and analyze competitor data
    picks_df, _, _ = load_competitor_data(data_dir)
    enriched_picks, _ = full_enrichment_pipeline(picks_df, data_dir)

    # Exclude user if specified (since they're simulating against the field)
    if exclude_user:
        enriched_picks = enriched_picks[enriched_picks['player_name'] != exclude_user]

    # Build player profiles and get composition
    profiles = build_player_profiles(enriched_picks)
    composition = analyze_league_composition(profiles)

    # Return in STRATEGY_MIX format
    strategy_counts = composition['strategy_counts']

    return {
        "Chalk-MaxPoints": strategy_counts.get("Chalk-MaxPoints", 0),
        "Slight-Contrarian": strategy_counts.get("Slight-Contrarian", 0),
        "Aggressive-Contrarian": strategy_counts.get("Aggressive-Contrarian", 0),
    }


def get_field_statistics(data_dir: str = "out") -> Dict:
    """
    Get comprehensive field statistics for analysis.

    Returns:
        Dictionary with:
        - total_players: int
        - strategy_distribution: dict
        - avg_contrarian_rate: float
        - avg_win_rate: float
        - avg_points_per_week: float
        - top_performers: list
    """
    picks_df, _, _ = load_competitor_data(data_dir)
    enriched_picks, _ = full_enrichment_pipeline(picks_df, data_dir)
    profiles = build_player_profiles(enriched_picks)
    composition = analyze_league_composition(profiles)

    # Calculate avg points per week
    import numpy as np
    avg_points = np.mean([p['avg_points_per_week'] for p in profiles])

    # Get top 5 performers
    top_performers = sorted(profiles, key=lambda p: p['avg_points_per_week'], reverse=True)[:5]

    return {
        'total_players': composition['total_players'],
        'strategy_distribution': composition['strategy_counts'],
        'avg_contrarian_rate': composition['avg_contrarian_rate'],
        'avg_win_rate': composition['avg_win_rate'],
        'avg_points_per_week': avg_points,
        'top_performers': [
            {
                'name': p['player_name'],
                'strategy': p['strategy'].value,
                'avg_points': p['avg_points_per_week']
            }
            for p in top_performers
        ]
    }


def compare_theoretical_vs_actual() -> Dict:
    """
    Compare theoretical assumptions vs actual field composition.

    Returns:
        Dictionary with theoretical, actual, and differences
    """
    # Theoretical assumption (from old main.py)
    theoretical = {
        "Chalk-MaxPoints": 16,
        "Slight-Contrarian": 10,
        "Aggressive-Contrarian": 5,
    }

    # Actual from data
    actual = get_actual_field_composition()

    # Calculate differences
    differences = {
        strategy: actual[strategy] - theoretical[strategy]
        for strategy in theoretical.keys()
    }

    return {
        'theoretical': theoretical,
        'actual': actual,
        'differences': differences,
        'total_theoretical': sum(theoretical.values()),
        'total_actual': sum(actual.values())
    }


if __name__ == "__main__":
    print("=" * 60)
    print("FIELD COMPOSITION ADAPTER - ANALYSIS")
    print("=" * 60)

    print("\n1. ACTUAL FIELD COMPOSITION")
    print("-" * 60)
    actual_field = get_actual_field_composition()
    total = sum(actual_field.values())
    print(f"Total opponents: {total}")
    for strategy, count in actual_field.items():
        pct = count / total * 100
        print(f"  {strategy:<25} {count:2d} ({pct:5.1f}%)")

    print("\n2. THEORETICAL VS ACTUAL COMPARISON")
    print("-" * 60)
    comparison = compare_theoretical_vs_actual()

    print("\nStrategy                  Theoretical  Actual  Difference")
    print("-" * 60)
    for strategy in comparison['theoretical'].keys():
        theo = comparison['theoretical'][strategy]
        act = comparison['actual'][strategy]
        diff = comparison['differences'][strategy]
        sign = "+" if diff > 0 else ""
        print(f"{strategy:<25} {theo:11d} {act:7d} {sign:>1}{diff:10d}")

    print("\n3. FIELD STATISTICS")
    print("-" * 60)
    stats = get_field_statistics()
    print(f"Total Players: {stats['total_players']}")
    print(f"Avg Contrarian Rate: {stats['avg_contrarian_rate']:.1%}")
    print(f"Avg Win Rate: {stats['avg_win_rate']:.1%}")
    print(f"Avg Points/Week: {stats['avg_points_per_week']:.1f}")

    print("\n4. TOP 5 PERFORMERS")
    print("-" * 60)
    print(f"{'Player':<25} {'Strategy':<25} {'Avg Pts/Wk'}")
    print("-" * 60)
    for performer in stats['top_performers']:
        print(f"{performer['name']:<25} {performer['strategy']:<25} {performer['avg_points']:11.1f}")

    print("\n5. INTEGRATION CODE FOR MAIN.PY")
    print("-" * 60)
    print("\nReplace this in main.py:")
    print("```python")
    print("# Old theoretical assumption")
    print("STRATEGY_MIX = {")
    print('    "Chalk-MaxPoints": 16,')
    print('    "Slight-Contrarian": 10,')
    print('    "Aggressive-Contrarian": 5,')
    print("}")
    print("```")
    print("\nWith this:")
    print("```python")
    print("# Use actual field composition from historical data")
    print("from field_adapter import get_actual_field_composition")
    print("")
    print("STRATEGY_MIX = get_actual_field_composition()")
    print("# Auto-loads from out/ directory, analyzes all players")
    print("# Returns: {'Chalk-MaxPoints': 17, 'Slight-Contrarian': 14, 'Aggressive-Contrarian': 1}")
    print("```")
