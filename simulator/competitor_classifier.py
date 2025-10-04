"""
Competitor Strategy Classifier

Analyzes historical pick patterns to classify each competitor's strategy type.
Critical for building accurate field simulations and identifying contrarian opportunities.

Strategy Types:
- CHALK: Picks favorites, minimal risk (0-10% contrarian rate)
- SLIGHT_CONTRARIAN: Strategic underdog picks (10-25% contrarian rate)
- AGGRESSIVE_CONTRARIAN: Frequent contrarian plays (25%+ contrarian rate)
"""

from enum import Enum
from typing import List, Dict
from dataclasses import dataclass

import pandas as pd
import numpy as np


class StrategyType(str, Enum):
    """Player strategy classification"""
    CHALK = "Chalk-MaxPoints"
    SLIGHT_CONTRARIAN = "Slight-Contrarian"
    AGGRESSIVE_CONTRARIAN = "Aggressive-Contrarian"


@dataclass
class PlayerProfile:
    """Complete player strategy profile"""
    player_name: str
    strategy: StrategyType
    contrarian_rate: float
    win_rate: float
    avg_points_per_week: float
    avg_confidence_on_contrarian: float
    consistency_score: float
    weeks_played: int
    total_picks: int


def classify_player_strategy(player_picks: pd.DataFrame) -> StrategyType:
    """
    Classify a player's strategy based on their pick patterns.

    Args:
        player_picks: DataFrame of picks for a single player

    Returns:
        StrategyType enum value
    """
    if len(player_picks) == 0:
        return StrategyType.CHALK

    contrarian_rate = player_picks['is_contrarian'].mean()

    if contrarian_rate < 0.10:
        return StrategyType.CHALK
    elif contrarian_rate < 0.25:
        return StrategyType.SLIGHT_CONTRARIAN
    else:
        return StrategyType.AGGRESSIVE_CONTRARIAN


def calculate_player_metrics(player_picks: pd.DataFrame) -> Dict:
    """
    Calculate comprehensive metrics for a player.

    Args:
        player_picks: DataFrame of picks for a single player

    Returns:
        Dictionary of player metrics
    """
    player_name = player_picks['player_name'].iloc[0]
    total_picks = len(player_picks)
    weeks_played = player_picks['week'].nunique()

    # Contrarian metrics
    contrarian_rate = player_picks['is_contrarian'].mean()
    contrarian_picks = player_picks[player_picks['is_contrarian']]

    if len(contrarian_picks) > 0:
        avg_conf_contrarian = contrarian_picks['confidence'].mean()
    else:
        avg_conf_contrarian = 0.0

    # Performance metrics
    win_rate = player_picks['won'].mean()

    # Weekly performance for consistency
    weekly_points = player_picks.groupby('week')['points_earned'].sum()
    if len(weekly_points) > 1:
        consistency_score = 1.0 - (weekly_points.std() / weekly_points.mean())
    else:
        consistency_score = 1.0

    avg_points_per_week = weekly_points.mean()

    return {
        'player_name': player_name,
        'total_picks': total_picks,
        'weeks_played': weeks_played,
        'contrarian_rate': contrarian_rate,
        'win_rate': win_rate,
        'avg_points_per_week': avg_points_per_week,
        'avg_confidence_on_contrarian': avg_conf_contrarian,
        'consistency_score': consistency_score
    }


def build_player_profiles(enriched_picks_df: pd.DataFrame) -> List[Dict]:
    """
    Build strategy profiles for all players.

    Args:
        enriched_picks_df: Enriched picks DataFrame with outcomes

    Returns:
        List of player profile dictionaries
    """
    profiles = []

    for player_name in enriched_picks_df['player_name'].unique():
        player_picks = enriched_picks_df[
            enriched_picks_df['player_name'] == player_name
        ]

        # Calculate metrics
        metrics = calculate_player_metrics(player_picks)

        # Classify strategy
        strategy = classify_player_strategy(player_picks)

        # Build profile
        profile = {
            **metrics,
            'strategy': strategy
        }

        profiles.append(profile)

    return profiles


def analyze_league_composition(profiles: List[Dict]) -> Dict:
    """
    Analyze overall league strategy composition.

    Args:
        profiles: List of player profiles

    Returns:
        Dictionary with league-level statistics
    """
    strategy_counts = {}
    for strategy_type in StrategyType:
        count = sum(1 for p in profiles if p['strategy'] == strategy_type)
        strategy_counts[strategy_type.value] = count

    total_players = len(profiles)

    return {
        'total_players': total_players,
        'strategy_counts': strategy_counts,
        'strategy_percentages': {
            k: v / total_players for k, v in strategy_counts.items()
        },
        'avg_contrarian_rate': np.mean([p['contrarian_rate'] for p in profiles]),
        'avg_win_rate': np.mean([p['win_rate'] for p in profiles])
    }


def get_top_performers(profiles: List[Dict], n: int = 10) -> List[Dict]:
    """
    Get top N performers by average points per week.

    Args:
        profiles: List of player profiles
        n: Number of top performers to return

    Returns:
        List of top performer profiles
    """
    sorted_profiles = sorted(
        profiles,
        key=lambda p: p['avg_points_per_week'],
        reverse=True
    )
    return sorted_profiles[:n]


def get_players_by_strategy(profiles: List[Dict],
                              strategy: StrategyType) -> List[Dict]:
    """
    Filter players by strategy type.

    Args:
        profiles: List of player profiles
        strategy: Strategy type to filter by

    Returns:
        List of profiles matching the strategy
    """
    return [p for p in profiles if p['strategy'] == strategy]


if __name__ == "__main__":
    # Demo with real data
    from data_loader import load_competitor_data
    from data_enrichment import full_enrichment_pipeline

    print("=" * 60)
    print("COMPETITOR STRATEGY CLASSIFIER - DEMO")
    print("=" * 60)

    # Load and enrich data
    print("\nLoading competitor data...")
    picks_df, _, _ = load_competitor_data()

    print("\nEnriching with game outcomes...")
    enriched_picks, _ = full_enrichment_pipeline(picks_df)

    print("\n" + "=" * 60)
    print("BUILDING PLAYER PROFILES")
    print("=" * 60)

    profiles = build_player_profiles(enriched_picks)
    print(f"Built profiles for {len(profiles)} players")

    print("\n" + "=" * 60)
    print("LEAGUE COMPOSITION ANALYSIS")
    print("=" * 60)

    composition = analyze_league_composition(profiles)
    print(f"\nTotal Players: {composition['total_players']}")
    print("\nStrategy Distribution:")
    for strategy, count in composition['strategy_counts'].items():
        pct = composition['strategy_percentages'][strategy]
        print(f"  {strategy}: {count} ({pct:.1%})")

    print(f"\nLeague Averages:")
    print(f"  Contrarian Rate: {composition['avg_contrarian_rate']:.1%}")
    print(f"  Win Rate: {composition['avg_win_rate']:.1%}")

    print("\n" + "=" * 60)
    print("TOP 10 PERFORMERS")
    print("=" * 60)

    top_performers = get_top_performers(profiles, n=10)
    print(f"\n{'Player':<25} {'Strategy':<25} {'Avg Pts/Wk':<12} {'Contrarian %':<15} {'Win %'}")
    print("-" * 95)
    for p in top_performers:
        print(f"{p['player_name']:<25} {p['strategy']:<25} {p['avg_points_per_week']:<12.1f} "
              f"{p['contrarian_rate']:<15.1%} {p['win_rate']:.1%}")

    print("\n" + "=" * 60)
    print("STRATEGY BREAKDOWN")
    print("=" * 60)

    for strategy_type in StrategyType:
        players = get_players_by_strategy(profiles, strategy_type)
        if players:
            print(f"\n{strategy_type.value} ({len(players)} players):")
            avg_points = np.mean([p['avg_points_per_week'] for p in players])
            avg_win_rate = np.mean([p['win_rate'] for p in players])
            print(f"  Avg Points/Week: {avg_points:.1f}")
            print(f"  Avg Win Rate: {avg_win_rate:.1%}")
            print(f"  Players: {', '.join([p['player_name'] for p in players[:5]])}")
            if len(players) > 5:
                print(f"           ... and {len(players) - 5} more")
