"""
Contrarian Opportunity Analyzer

Identifies optimal contrarian opportunities based on:
1. Field consensus (high % on one side)
2. Upset probability (underdog has reasonable chance)
3. Differentiation value (potential point gain vs field)

Usage:
    from contrarian_analyzer import find_contrarian_opportunities

    opportunities = find_contrarian_opportunities(
        week=5,
        min_consensus=0.75,
        min_upset_probability=0.35
    )
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class ContrarianOpportunity:
    """Represents a contrarian opportunity"""
    game_id: str
    favorite: str
    underdog: str
    field_consensus: float  # % picking favorite
    underdog_win_prob: float  # Probability underdog wins
    expected_value_gain: float  # Expected point advantage vs field
    risk_level: str  # "Low", "Medium", "High"
    recommended: bool


def calculate_contrarian_value(
    field_consensus: float,
    underdog_prob: float,
    avg_confidence: int = 8
) -> float:
    """
    Calculate expected value gain from taking contrarian position.

    Args:
        field_consensus: % of field picking favorite (0-1)
        underdog_prob: Probability underdog wins (0-1)
        avg_confidence: Average confidence assigned to this game

    Returns:
        Expected point advantage vs average field opponent
    """
    # If you pick underdog and it wins, you gain points vs field
    # Weighted by probability and typical confidence assigned

    # Expected points if underdog wins
    points_if_win = avg_confidence * underdog_prob

    # Expected points field gets (they're on favorite)
    field_expected = avg_confidence * (1 - underdog_prob) * field_consensus

    # Net advantage
    advantage = points_if_win - field_expected

    return advantage


def assess_risk_level(underdog_prob: float) -> str:
    """
    Categorize risk level based on underdog win probability.

    Args:
        underdog_prob: Probability underdog wins (0-1)

    Returns:
        "Low", "Medium", or "High" risk designation
    """
    if underdog_prob >= 0.45:
        return "Low"  # Near toss-up
    elif underdog_prob >= 0.35:
        return "Medium"  # Reasonable upset chance
    else:
        return "High"  # Long shot


def find_contrarian_opportunities_from_data(
    enriched_picks: pd.DataFrame,
    favorites_df: pd.DataFrame,
    week: int,
    min_consensus: float = 0.75,
    min_upset_probability: float = 0.35,
    max_opportunities: int = 3
) -> List[ContrarianOpportunity]:
    """
    Find contrarian opportunities from historical data analysis.

    Args:
        enriched_picks: Enriched picks DataFrame
        favorites_df: Field favorites DataFrame
        week: Week number to analyze
        min_consensus: Minimum field consensus to consider (default 75%)
        min_upset_probability: Minimum underdog win chance (default 35%)
        max_opportunities: Maximum opportunities to return

    Returns:
        List of ContrarianOpportunity objects, sorted by expected value
    """
    week_favorites = favorites_df[favorites_df['week'] == week]
    week_picks = enriched_picks[enriched_picks['week'] == week]

    opportunities = []

    for _, game in week_favorites.iterrows():
        if game['favorite'] == 'TOSSUP':
            continue

        field_consensus = game['favorite_percentage']

        # Only consider high-consensus games
        if field_consensus < min_consensus:
            continue

        # Calculate underdog win probability from historical data
        underdog = game['underdog']
        favorite = game['favorite']

        # Count actual outcomes (if available in historical data)
        underdog_picks = week_picks[week_picks['team'] == underdog]
        if len(underdog_picks) > 0:
            underdog_win_rate = underdog_picks['won'].mean()
        else:
            # Estimate based on consensus (inverse relationship)
            underdog_win_rate = 1 - field_consensus

        # Filter by minimum upset probability
        if underdog_win_rate < min_upset_probability:
            continue

        # Calculate expected value
        avg_conf = week_picks[week_picks['team'] == favorite]['confidence'].mean()
        if pd.isna(avg_conf):
            avg_conf = 8  # Default mid-range

        ev_gain = calculate_contrarian_value(field_consensus, underdog_win_rate, int(avg_conf))

        # Assess risk
        risk = assess_risk_level(underdog_win_rate)

        # Recommend if positive EV and acceptable risk
        recommended = (ev_gain > 0) and (risk in ["Low", "Medium"])

        opportunities.append(ContrarianOpportunity(
            game_id=game['game_id'],
            favorite=favorite,
            underdog=underdog,
            field_consensus=field_consensus,
            underdog_win_prob=underdog_win_rate,
            expected_value_gain=ev_gain,
            risk_level=risk,
            recommended=recommended
        ))

    # Sort by expected value gain
    opportunities.sort(key=lambda x: x.expected_value_gain, reverse=True)

    return opportunities[:max_opportunities]


def analyze_contrarian_performance_history(
    enriched_picks: pd.DataFrame,
    favorites_df: pd.DataFrame
) -> Dict:
    """
    Analyze historical performance of contrarian picks.

    Args:
        enriched_picks: Enriched picks DataFrame
        favorites_df: Field favorites DataFrame

    Returns:
        Dictionary with contrarian performance statistics
    """
    # Overall contrarian stats
    contrarian_picks = enriched_picks[enriched_picks['is_contrarian']]
    chalk_picks = enriched_picks[~enriched_picks['is_contrarian']]

    stats = {
        'total_contrarian_picks': len(contrarian_picks),
        'contrarian_win_rate': contrarian_picks['won'].mean(),
        'contrarian_avg_points': contrarian_picks['points_earned'].mean(),
        'chalk_win_rate': chalk_picks['won'].mean(),
        'chalk_avg_points': chalk_picks['points_earned'].mean(),
    }

    # By field consensus level
    consensus_bins = [0.5, 0.75, 0.90, 1.0]
    consensus_labels = ['50-75%', '75-90%', '90-100%']

    contrarian_by_consensus = []
    for i in range(len(consensus_bins) - 1):
        lower = consensus_bins[i]
        upper = consensus_bins[i + 1]

        # Filter contrarian picks in this consensus range
        in_range = contrarian_picks[
            (contrarian_picks['field_percentage'] >= lower) &
            (contrarian_picks['field_percentage'] < upper)
        ]

        if len(in_range) > 0:
            contrarian_by_consensus.append({
                'consensus_range': consensus_labels[i],
                'count': len(in_range),
                'win_rate': in_range['won'].mean(),
                'avg_points': in_range['points_earned'].mean()
            })

    stats['by_consensus'] = contrarian_by_consensus

    return stats


if __name__ == "__main__":
    from data_loader import load_competitor_data
    from data_enrichment import full_enrichment_pipeline

    print("=" * 70)
    print("CONTRARIAN OPPORTUNITY ANALYZER - DEMO")
    print("=" * 70)

    # Load data
    print("\nLoading historical data...")
    picks_df, _, _ = load_competitor_data()
    enriched_picks, favorites = full_enrichment_pipeline(picks_df)

    print("\n" + "=" * 70)
    print("HISTORICAL CONTRARIAN PERFORMANCE")
    print("=" * 70)

    perf = analyze_contrarian_performance_history(enriched_picks, favorites)

    print(f"\nOverall Statistics:")
    print(f"  Total contrarian picks: {perf['total_contrarian_picks']}")
    print(f"  Contrarian win rate: {perf['contrarian_win_rate']:.1%}")
    print(f"  Contrarian avg points: {perf['contrarian_avg_points']:.2f}")
    print(f"  Chalk win rate: {perf['chalk_win_rate']:.1%}")
    print(f"  Chalk avg points: {perf['chalk_avg_points']:.2f}")

    print(f"\nBy Field Consensus:")
    print(f"  {'Consensus':<15} {'Count':<8} {'Win Rate':<12} {'Avg Points'}")
    print("  " + "-" * 50)
    for stat in perf['by_consensus']:
        print(f"  {stat['consensus_range']:<15} {stat['count']:<8} {stat['win_rate']:<12.1%} {stat['avg_points']:.2f}")

    print("\n" + "=" * 70)
    print("WEEK 4 CONTRARIAN OPPORTUNITIES")
    print("=" * 70)

    opportunities = find_contrarian_opportunities_from_data(
        enriched_picks,
        favorites,
        week=4,
        min_consensus=0.75,
        min_upset_probability=0.30
    )

    print(f"\nFound {len(opportunities)} contrarian opportunities:")
    print(f"\n{'Underdog':<8} {'vs':<4} {'Favorite':<8} {'Consensus':<12} {'Upset Prob':<12} {'EV Gain':<10} {'Risk':<8} {'Rec?'}")
    print("-" * 80)

    for opp in opportunities:
        rec = "✓" if opp.recommended else "✗"
        print(f"{opp.underdog:<8} {'vs':<4} {opp.favorite:<8} {opp.field_consensus:<12.1%} "
              f"{opp.underdog_win_prob:<12.1%} {opp.expected_value_gain:<10.2f} "
              f"{opp.risk_level:<8} {rec}")

    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)

    recommended = [o for o in opportunities if o.recommended]
    if recommended:
        print(f"\nTop contrarian plays for Week 4:")
        for i, opp in enumerate(recommended, 1):
            print(f"\n{i}. Pick {opp.underdog} over {opp.favorite}")
            print(f"   - {opp.field_consensus:.0%} of field on {opp.favorite}")
            print(f"   - {opp.underdog} has {opp.underdog_win_prob:.0%} win chance")
            print(f"   - Expected value gain: +{opp.expected_value_gain:.2f} points")
            print(f"   - Risk level: {opp.risk_level}")
    else:
        print("\nNo recommended contrarian opportunities this week.")
        print("Stick with chalk strategy.")
