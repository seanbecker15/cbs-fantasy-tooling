"""
Competitor Intelligence Analysis

Analyzes historical competitor pick patterns to identify strategies and find opportunities.
"""

from typing import Dict, Optional

from cbs_fantasy_tooling.analysis.data.loader import load_competitor_data
from cbs_fantasy_tooling.analysis.data.enrichment import full_enrichment_pipeline
from cbs_fantasy_tooling.analysis.competitor.competitor_classifier import (
    build_player_profiles,
    analyze_league_composition,
    get_top_performers,
)
from cbs_fantasy_tooling.analysis.competitor.contrarian_analyzer import (
    find_contrarian_opportunities_from_data,
    analyze_contrarian_performance_history,
)
from cbs_fantasy_tooling.analysis.competitor.field_adapter import (
    get_field_statistics,
)


def analyze_competitors(
    data_dir: str = "out",
    week: Optional[int] = None,
) -> Dict:
    """
    Perform comprehensive competitor intelligence analysis.

    Args:
        data_dir: Directory containing competitor pick data
        week: Optional week number for contrarian opportunity analysis

    Returns:
        Dictionary with competitor analysis results
    """
    print("="*60)
    print("COMPETITOR INTELLIGENCE ANALYSIS")
    print("="*60)

    # Load data
    print("\nLoading competitor data...")
    picks_df, players_df, weekly_stats_df = load_competitor_data(data_dir)
    print(f"Loaded {len(picks_df)} total picks from {players_df.shape[0]} players")

    # Enrich with game outcomes
    print("\nEnriching with game outcomes...")
    enriched_picks, favorites = full_enrichment_pipeline(picks_df, data_dir)

    # Build player profiles
    print("\nBuilding player strategy profiles...")
    profiles = build_player_profiles(enriched_picks)
    composition = analyze_league_composition(profiles)

    print(f"\nLeague Composition:")
    print(f"  Total Players: {composition['total_players']}")
    print(f"\nStrategy Distribution:")
    for strategy, count in composition['strategy_counts'].items():
        pct = composition['strategy_percentages'][strategy]
        print(f"  {strategy}: {count} ({pct:.1%})")

    print(f"\nLeague Averages:")
    print(f"  Contrarian Rate: {composition['avg_contrarian_rate']:.1%}")
    print(f"  Win Rate: {composition['avg_win_rate']:.1%}")

    # Top performers
    print("\n" + "="*60)
    print("TOP 10 PERFORMERS")
    print("="*60)
    top_performers = get_top_performers(profiles, n=10)
    for i, p in enumerate(top_performers, 1):
        print(f"{i}. {p['player_name']:<25} {p['strategy']:<25} {p['avg_points_per_week']:.1f} pts/wk")

    # Field statistics
    print("\n" + "="*60)
    print("FIELD STATISTICS")
    print("="*60)
    field_stats = get_field_statistics(data_dir)
    print(f"\nTotal Players Analyzed: {field_stats['total_players']}")
    print("Strategy Distribution:")
    for strategy, count in field_stats['strategy_distribution'].items():
        pct = count / field_stats['total_players']
        print(f"  {strategy}: {count} ({pct:.1%})")
    print(f"\nAverage Contrarian Rate: {field_stats['avg_contrarian_rate']:.1%}")
    print(f"Average Win Rate: {field_stats['avg_win_rate']:.1%}")
    print(f"Average Points per Week: {field_stats['avg_points_per_week']:.2f} pts")
    print("\nTop 5 Performers:")
    for i, p in enumerate(field_stats['top_performers'], 1):
        print(f"{i}. {p['name']:<25} {p['strategy']:<25} {p['avg_points']:.1f} pts/wk")
    

    # Contrarian performance
    print("\n" + "="*60)
    print("CONTRARIAN PERFORMANCE HISTORY")
    print("="*60)
    contrarian_perf = analyze_contrarian_performance_history(enriched_picks)
    print(f"\nOverall Statistics:")
    print(f"  Total contrarian picks: {contrarian_perf['total_contrarian_picks']}")
    print(f"  Contrarian win rate: {contrarian_perf['contrarian_win_rate']:.1%}")
    print(f"  Contrarian avg points: {contrarian_perf['contrarian_avg_points']:.2f}")
    print(f"  Chalk win rate: {contrarian_perf['chalk_win_rate']:.1%}")
    print(f"  Chalk avg points: {contrarian_perf['chalk_avg_points']:.2f}")

    # Week-specific contrarian opportunities
    opportunities = None
    if week:
        print(f"\n" + "="*60)
        print(f"WEEK {week} CONTRARIAN OPPORTUNITIES")
        print("="*60)
        opportunities = find_contrarian_opportunities_from_data(
            enriched_picks,
            favorites,
            week=week,
            min_consensus=0.75,
            min_upset_probability=0.30
        )
        if opportunities:
            print(f"\nFound {len(opportunities)} contrarian opportunities:")
            for i, opp in enumerate(opportunities, 1):
                rec = "✓" if opp.recommended else "✗"
                print(f"{i}. {opp.underdog} over {opp.favorite}")
                print(f"   Consensus: {opp.field_consensus:.1%} on {opp.favorite}")
                print(f"   Upset Prob: {opp.underdog_win_prob:.1%}")
                print(f"   EV Gain: +{opp.expected_value_gain:.2f} points")
                print(f"   Risk: {opp.risk_level} | Recommended: {rec}")

    results = {
        "picks_df": picks_df,
        "enriched_picks": enriched_picks,
        "profiles": profiles,
        "composition": composition,
        "top_performers": top_performers,
        "field_stats": field_stats,
        "contrarian_performance": contrarian_perf,
        "opportunities": opportunities,
    }

    return results
