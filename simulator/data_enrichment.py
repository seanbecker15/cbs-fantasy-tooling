"""
Data Enrichment Module

Enriches competitor picks DataFrame with game outcome data and calculates
contrarian picks based on field consensus and actual game results.

This is critical business logic - tested comprehensively.
"""

import json
import glob
import os
from typing import Dict, List, Tuple

import pandas as pd
import numpy as np


def load_game_results(data_dir: str = "out") -> pd.DataFrame:
    """
    Load game results from JSON files into DataFrame.

    Args:
        data_dir: Directory containing week_{N}_game_results.json files

    Returns:
        DataFrame with columns:
        - week, away_team, home_team, away_score, home_score, winner, loser
    """
    pattern = os.path.join(data_dir, "week_*_game_results.json")
    files = sorted(glob.glob(pattern))

    if not files:
        raise FileNotFoundError(f"No game result files found in {data_dir}")

    all_games = []

    for filepath in files:
        with open(filepath, 'r') as f:
            data = json.load(f)

        for game in data['games']:
            all_games.append({
                'week': game['week'],
                'away_team': game['away_team'],
                'home_team': game['home_team'],
                'away_score': game['away_score'],
                'home_score': game['home_score'],
                'winner': game['winner'],
                'loser': game['loser'],
                'game_id': game['game_id']
            })

    return pd.DataFrame(all_games)


def enrich_picks_with_outcomes(picks_df: pd.DataFrame,
                                game_results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrich picks DataFrame with game outcome data (won/lost).

    Critical business logic: Determines which picks earned points.

    Args:
        picks_df: DataFrame of player picks
        game_results_df: DataFrame of game results

    Returns:
        Enriched picks DataFrame with additional columns:
        - won: bool (True if pick won)
        - opponent: str (opponent team in the matchup)
        - home_away: str ('home' or 'away')
        - final_score: str (e.g., "24-20")
    """
    enriched_picks = picks_df.copy()

    # Initialize new columns
    enriched_picks['won'] = False
    enriched_picks['opponent'] = None
    enriched_picks['home_away'] = None
    enriched_picks['final_score'] = None

    # For each week, match picks to game results
    for week in enriched_picks['week'].unique():
        week_picks = enriched_picks['week'] == week
        week_games = game_results_df[game_results_df['week'] == week]

        for idx in enriched_picks[week_picks].index:
            team = enriched_picks.loc[idx, 'team']

            # Find this team's game
            game = week_games[
                (week_games['home_team'] == team) |
                (week_games['away_team'] == team)
            ]

            if len(game) == 0:
                # Team didn't play this week (bye week or data mismatch)
                continue

            game = game.iloc[0]

            # Determine if pick won
            won = (game['winner'] == team)
            enriched_picks.loc[idx, 'won'] = won

            # Determine opponent and home/away
            if game['home_team'] == team:
                enriched_picks.loc[idx, 'opponent'] = game['away_team']
                enriched_picks.loc[idx, 'home_away'] = 'home'
                score = f"{game['home_score']}-{game['away_score']}"
            else:
                enriched_picks.loc[idx, 'opponent'] = game['home_team']
                enriched_picks.loc[idx, 'home_away'] = 'away'
                score = f"{game['away_score']}-{game['home_score']}"

            enriched_picks.loc[idx, 'final_score'] = score

    # Calculate points earned (confidence if won, 0 if lost)
    enriched_picks['points_earned'] = enriched_picks.apply(
        lambda row: row['confidence'] if row['won'] else 0,
        axis=1
    )

    return enriched_picks


def calculate_field_favorites(picks_df: pd.DataFrame,
                                game_results_df: pd.DataFrame,
                                threshold: float = 0.50) -> pd.DataFrame:
    """
    Determine which team was the "favorite" based on field consensus.

    Args:
        picks_df: Enriched picks DataFrame
        game_results_df: Game results DataFrame
        threshold: Percentage threshold to be considered favorite (default 50%)

    Returns:
        DataFrame with columns:
        - week, game_id, favorite, underdog, favorite_percentage
    """
    favorites = []

    for week in picks_df['week'].unique():
        week_picks = picks_df[picks_df['week'] == week]
        week_games = game_results_df[game_results_df['week'] == week]

        for _, game in week_games.iterrows():
            home_team = game['home_team']
            away_team = game['away_team']

            # Count picks for each team
            home_picks = len(week_picks[week_picks['team'] == home_team])
            away_picks = len(week_picks[week_picks['team'] == away_team])
            total_picks = home_picks + away_picks

            if total_picks == 0:
                # No one picked either team (shouldn't happen)
                continue

            home_percentage = home_picks / total_picks
            away_percentage = away_picks / total_picks

            # Determine favorite
            if home_percentage > threshold:
                favorite = home_team
                underdog = away_team
                favorite_pct = home_percentage
            elif away_percentage > threshold:
                favorite = away_team
                underdog = home_team
                favorite_pct = away_percentage
            else:
                # Toss-up game
                favorite = 'TOSSUP'
                underdog = 'TOSSUP'
                favorite_pct = max(home_percentage, away_percentage)

            favorites.append({
                'week': week,
                'game_id': game['game_id'],
                'home_team': home_team,
                'away_team': away_team,
                'favorite': favorite,
                'underdog': underdog,
                'favorite_percentage': favorite_pct,
                'home_pick_percentage': home_percentage,
                'away_pick_percentage': away_percentage
            })

    return pd.DataFrame(favorites)


def mark_contrarian_picks(picks_df: pd.DataFrame,
                           favorites_df: pd.DataFrame) -> pd.DataFrame:
    """
    Mark which picks were contrarian (picked the underdog).

    Args:
        picks_df: Enriched picks DataFrame
        favorites_df: Field favorites DataFrame

    Returns:
        Picks DataFrame with additional column:
        - is_contrarian: bool (True if picked underdog)
        - field_percentage: float (% of field that picked same team)
    """
    enriched = picks_df.copy()
    enriched['is_contrarian'] = False
    enriched['field_percentage'] = None

    for idx in enriched.index:
        week = enriched.loc[idx, 'week']
        team = enriched.loc[idx, 'team']

        # Find the game this pick belongs to
        game_info = favorites_df[
            (favorites_df['week'] == week) &
            ((favorites_df['home_team'] == team) |
             (favorites_df['away_team'] == team))
        ]

        if len(game_info) == 0:
            continue

        game_info = game_info.iloc[0]

        # Check if this was a contrarian pick
        is_contrarian = (team == game_info['underdog'])
        enriched.loc[idx, 'is_contrarian'] = is_contrarian

        # Get field percentage for this team
        if team == game_info['home_team']:
            field_pct = game_info['home_pick_percentage']
        else:
            field_pct = game_info['away_pick_percentage']

        enriched.loc[idx, 'field_percentage'] = field_pct

    return enriched


def full_enrichment_pipeline(picks_df: pd.DataFrame,
                               data_dir: str = "out") -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Complete enrichment pipeline.

    Args:
        picks_df: Raw picks DataFrame from data_loader
        data_dir: Directory containing game result JSON files

    Returns:
        Tuple of (enriched_picks_df, favorites_df)
    """
    print("Loading game results...")
    game_results = load_game_results(data_dir)
    print(f"  Loaded {len(game_results)} games across {game_results['week'].nunique()} weeks")

    print("\nEnriching picks with game outcomes...")
    enriched_picks = enrich_picks_with_outcomes(picks_df, game_results)
    total_picks = len(enriched_picks)
    wins = enriched_picks['won'].sum()
    win_rate = wins / total_picks
    print(f"  Total picks: {total_picks}")
    print(f"  Winning picks: {wins} ({win_rate:.1%})")

    print("\nCalculating field favorites...")
    favorites = calculate_field_favorites(enriched_picks, game_results)
    print(f"  Analyzed {len(favorites)} games")

    print("\nMarking contrarian picks...")
    enriched_picks = mark_contrarian_picks(enriched_picks, favorites)
    contrarian_picks = enriched_picks['is_contrarian'].sum()
    contrarian_rate = contrarian_picks / total_picks
    print(f"  Contrarian picks: {contrarian_picks} ({contrarian_rate:.1%})")

    return enriched_picks, favorites


if __name__ == "__main__":
    # Demo/testing
    from data_loader import load_competitor_data

    print("=" * 60)
    print("DATA ENRICHMENT PIPELINE - DEMO")
    print("=" * 60)

    # Load raw picks data
    print("\nLoading competitor picks...")
    picks_df, players_df, weekly_stats_df = load_competitor_data()

    print("\n" + "=" * 60)
    print("RUNNING ENRICHMENT PIPELINE")
    print("=" * 60)

    # Run full enrichment
    enriched_picks, favorites = full_enrichment_pipeline(picks_df)

    print("\n" + "=" * 60)
    print("SAMPLE ENRICHED PICKS")
    print("=" * 60)

    # Show sample enriched picks
    sample = enriched_picks[
        (enriched_picks['player_name'] == 'User Name') &
        (enriched_picks['week'] == 4)
    ].sort_values('confidence', ascending=False)

    print("\nUser Name - Week 4 Picks:")
    print(sample[['team', 'confidence', 'won', 'points_earned', 'is_contrarian', 'field_percentage', 'final_score']].to_string(index=False))

    print("\n" + "=" * 60)
    print("CONTRARIAN ANALYSIS - WEEK 4")
    print("=" * 60)

    week4_picks = enriched_picks[enriched_picks['week'] == 4]
    contrarian_summary = week4_picks.groupby('is_contrarian').agg({
        'won': ['count', 'sum', 'mean'],
        'points_earned': 'sum'
    }).round(3)

    print("\nContrarian vs Chalk Performance:")
    print(contrarian_summary)

    print("\n" + "=" * 60)
    print("FIELD FAVORITES - WEEK 4")
    print("=" * 60)

    week4_favorites = favorites[favorites['week'] == 4].sort_values('favorite_percentage', ascending=False)
    print(week4_favorites[['home_team', 'away_team', 'favorite', 'favorite_percentage']].head(10).to_string(index=False))
