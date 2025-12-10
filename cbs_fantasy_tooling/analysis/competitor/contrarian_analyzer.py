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

from typing import List, Dict
from dataclasses import dataclass
import pandas as pd


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
    field_consensus: float, underdog_prob: float, avg_confidence: int = 8
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
    max_opportunities: int = 3,
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
    week_favorites = favorites_df[favorites_df["week"] == week]
    week_picks = enriched_picks[enriched_picks["week"] == week]

    opportunities = []

    for _, game in week_favorites.iterrows():
        if game["favorite"] == "TOSSUP":
            continue

        field_consensus = game["favorite_percentage"]

        # Only consider high-consensus games
        if field_consensus < min_consensus:
            continue

        # Calculate underdog win probability from historical data
        underdog = game["underdog"]
        favorite = game["favorite"]

        # Count actual outcomes (if available in historical data)
        underdog_picks = week_picks[week_picks["team"] == underdog]
        if len(underdog_picks) > 0:
            underdog_win_rate = underdog_picks["won"].mean()
        else:
            # Estimate based on consensus (inverse relationship)
            underdog_win_rate = 1 - field_consensus

        # Filter by minimum upset probability
        if underdog_win_rate < min_upset_probability:
            continue

        # Calculate expected value
        avg_conf = week_picks[week_picks["team"] == favorite]["confidence"].mean()
        if pd.isna(avg_conf):
            avg_conf = 8  # Default mid-range

        ev_gain = calculate_contrarian_value(field_consensus, underdog_win_rate, int(avg_conf))

        # Assess risk
        risk = assess_risk_level(underdog_win_rate)

        # Recommend if positive EV and acceptable risk
        recommended = (ev_gain > 0) and (risk in ["Low", "Medium"])

        opportunities.append(
            ContrarianOpportunity(
                game_id=game["game_id"],
                favorite=favorite,
                underdog=underdog,
                field_consensus=field_consensus,
                underdog_win_prob=underdog_win_rate,
                expected_value_gain=ev_gain,
                risk_level=risk,
                recommended=recommended,
            )
        )

    # Sort by expected value gain
    opportunities.sort(key=lambda x: x.expected_value_gain, reverse=True)

    return opportunities[:max_opportunities]


def analyze_contrarian_performance_history(enriched_picks: pd.DataFrame) -> Dict:
    """
    Analyze historical performance of contrarian picks.

    Args:
        enriched_picks: Enriched picks DataFrame
        favorites_df: Field favorites DataFrame

    Returns:
        Dictionary with contrarian performance statistics
    """
    # Overall contrarian stats
    contrarian_picks = enriched_picks[enriched_picks["is_contrarian"]]
    chalk_picks = enriched_picks[~enriched_picks["is_contrarian"]]

    stats = {
        "total_contrarian_picks": len(contrarian_picks),
        "contrarian_win_rate": contrarian_picks["won"].mean(),
        "contrarian_avg_points": contrarian_picks["points_earned"].mean(),
        "chalk_win_rate": chalk_picks["won"].mean(),
        "chalk_avg_points": chalk_picks["points_earned"].mean(),
    }

    # By field consensus level
    consensus_bins = [0.5, 0.75, 0.90, 1.0]
    consensus_labels = ["50-75%", "75-90%", "90-100%"]

    contrarian_by_consensus = []
    for i in range(len(consensus_bins) - 1):
        lower = consensus_bins[i]
        upper = consensus_bins[i + 1]

        # Filter contrarian picks in this consensus range
        in_range = contrarian_picks[
            (contrarian_picks["field_percentage"] >= lower)
            & (contrarian_picks["field_percentage"] < upper)
        ]

        if len(in_range) > 0:
            contrarian_by_consensus.append(
                {
                    "consensus_range": consensus_labels[i],
                    "count": len(in_range),
                    "win_rate": in_range["won"].mean(),
                    "avg_points": in_range["points_earned"].mean(),
                }
            )

    stats["by_consensus"] = contrarian_by_consensus

    return stats
