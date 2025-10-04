"""
Competitor Picks Data Ingestion Pipeline

Loads historical pick data from CBS Sports scraper JSON output and transforms
it into normalized DataFrames for competitive intelligence analysis.

Data Sources: out/week_{N}_results_{YYYYMMDD}_{HHMMSS}.json

Output Format:
- picks_df: Normalized picks matrix (player, week, team, confidence)
- players_df: Player metadata (name, total performance across weeks)
- weekly_stats_df: Week-level aggregate statistics
"""

import json
import glob
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import numpy as np


@dataclass
class WeekData:
    """Structured representation of a single week's results"""
    week_number: int
    timestamp: datetime
    max_wins_value: int
    max_wins_players: List[str]
    max_points_value: int
    max_points_players: List[str]
    player_results: List[Dict]


class CompetitorDataLoader:
    """
    Loads and processes historical competitor pick data from JSON files.

    Provides normalized DataFrames optimized for:
    - Player strategy classification
    - Field consensus analysis
    - Pick prediction modeling
    - Performance tracking
    """

    def __init__(self, data_dir: str = "out"):
        """
        Initialize the data loader.

        Args:
            data_dir: Directory containing week_*_results_*.json files
        """
        self.data_dir = data_dir
        self.weeks_data: Dict[int, WeekData] = {}
        self.picks_df: Optional[pd.DataFrame] = None
        self.players_df: Optional[pd.DataFrame] = None
        self.weekly_stats_df: Optional[pd.DataFrame] = None

    def load_all_weeks(self) -> None:
        """
        Load all available week JSON files from data directory.

        Scans for files matching pattern: week_{N}_results_{timestamp}.json
        Populates self.weeks_data dictionary keyed by week number.
        """
        pattern = os.path.join(self.data_dir, "week_*_results_*.json")
        files = sorted(glob.glob(pattern))

        if not files:
            raise FileNotFoundError(f"No week result files found in {self.data_dir}")

        print(f"Found {len(files)} week result files")

        for filepath in files:
            week_data = self._load_week_file(filepath)
            self.weeks_data[week_data.week_number] = week_data
            print(f"  Loaded Week {week_data.week_number}: {week_data.timestamp.strftime('%Y-%m-%d')}")

    def _load_week_file(self, filepath: str) -> WeekData:
        """
        Load and parse a single week JSON file.

        Args:
            filepath: Path to week results JSON file

        Returns:
            WeekData object with structured week information
        """
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Parse timestamp
        timestamp = datetime.fromisoformat(data['timestamp'])

        # Parse max wins players (may be comma-separated string)
        max_wins_players = [p.strip() for p in data['max_wins']['players'].split(',')]
        max_points_players = [p.strip() for p in data['max_points']['players'].split(',')]

        return WeekData(
            week_number=data['week_number'],
            timestamp=timestamp,
            max_wins_value=data['max_wins']['max_wins'],
            max_wins_players=max_wins_players,
            max_points_value=data['max_points']['max_points'],
            max_points_players=max_points_players,
            player_results=data['results']
        )

    def build_picks_dataframe(self) -> pd.DataFrame:
        """
        Build normalized picks matrix DataFrame.

        Returns:
            DataFrame with columns:
            - player_name: str
            - week: int
            - team: str (3-letter abbreviation)
            - confidence: int (1-16)
            - actual_points: int (confidence if won, 0 if lost)
            - won: bool
        """
        rows = []

        for week_num, week_data in self.weeks_data.items():
            for player in week_data.player_results:
                player_name = player['name']
                total_points = int(player['points'])
                wins = player['wins']
                losses = player['losses']

                # Track which picks contributed to total points
                # This allows us to infer win/loss for each pick
                picks_by_confidence = sorted(
                    player['picks'],
                    key=lambda p: int(p['points']),
                    reverse=True
                )

                # Calculate actual points each pick earned
                # If we have perfect information, we can infer outcomes
                for pick in player['picks']:
                    team = pick['team']
                    confidence = int(pick['points'])

                    # We'll mark outcome as unknown for now
                    # (can be enriched with actual game results later)
                    rows.append({
                        'player_name': player_name,
                        'week': week_num,
                        'team': team,
                        'confidence': confidence,
                        'total_player_points': total_points,
                        'total_player_wins': wins,
                        'total_player_losses': losses
                    })

        self.picks_df = pd.DataFrame(rows)
        return self.picks_df

    def build_players_dataframe(self) -> pd.DataFrame:
        """
        Build player metadata DataFrame with aggregate statistics.

        Returns:
            DataFrame with columns:
            - player_name: str
            - weeks_played: int
            - total_points: int
            - total_wins: int
            - total_losses: int
            - avg_points_per_week: float
            - avg_wins_per_week: float
            - bonus_wins_most_points: int
            - bonus_wins_most_wins: int
        """
        if self.picks_df is None:
            self.build_picks_dataframe()

        player_stats = []

        for player_name in self.picks_df['player_name'].unique():
            player_weeks = self.picks_df[self.picks_df['player_name'] == player_name]

            # Count bonus wins
            bonus_most_points = 0
            bonus_most_wins = 0

            for week_num in player_weeks['week'].unique():
                week_data = self.weeks_data[week_num]
                if player_name in week_data.max_points_players:
                    bonus_most_points += 1
                if player_name in week_data.max_wins_players:
                    bonus_most_wins += 1

            # Aggregate by week to get totals
            weekly_agg = player_weeks.groupby('week').first()

            player_stats.append({
                'player_name': player_name,
                'weeks_played': len(weekly_agg),
                'total_points': weekly_agg['total_player_points'].sum(),
                'total_wins': weekly_agg['total_player_wins'].sum(),
                'total_losses': weekly_agg['total_player_losses'].sum(),
                'avg_points_per_week': weekly_agg['total_player_points'].mean(),
                'avg_wins_per_week': weekly_agg['total_player_wins'].mean(),
                'bonus_wins_most_points': bonus_most_points,
                'bonus_wins_most_wins': bonus_most_wins
            })

        self.players_df = pd.DataFrame(player_stats)
        self.players_df = self.players_df.sort_values('total_points', ascending=False)
        return self.players_df

    def build_weekly_stats_dataframe(self) -> pd.DataFrame:
        """
        Build week-level aggregate statistics DataFrame.

        Returns:
            DataFrame with columns:
            - week: int
            - timestamp: datetime
            - num_players: int
            - max_wins: int
            - max_points: int
            - avg_wins: float
            - avg_points: float
            - std_wins: float
            - std_points: float
        """
        if self.picks_df is None:
            self.build_picks_dataframe()

        weekly_stats = []

        for week_num, week_data in self.weeks_data.items():
            week_picks = self.picks_df[self.picks_df['week'] == week_num]

            # Get unique player stats per week
            player_week_stats = week_picks.groupby('player_name').first()

            weekly_stats.append({
                'week': week_num,
                'timestamp': week_data.timestamp,
                'num_players': len(player_week_stats),
                'max_wins': week_data.max_wins_value,
                'max_points': week_data.max_points_value,
                'avg_wins': player_week_stats['total_player_wins'].mean(),
                'avg_points': player_week_stats['total_player_points'].mean(),
                'std_wins': player_week_stats['total_player_wins'].std(),
                'std_points': player_week_stats['total_player_points'].std()
            })

        self.weekly_stats_df = pd.DataFrame(weekly_stats)
        self.weekly_stats_df = self.weekly_stats_df.sort_values('week')
        return self.weekly_stats_df

    def get_field_consensus(self, week: int) -> pd.DataFrame:
        """
        Calculate field consensus for a specific week.

        Args:
            week: Week number to analyze

        Returns:
            DataFrame with columns:
            - team: str
            - pick_count: int
            - pick_percentage: float (0-1)
            - avg_confidence: float
            - total_confidence: int
        """
        if self.picks_df is None:
            self.build_picks_dataframe()

        week_picks = self.picks_df[self.picks_df['week'] == week]
        num_players = week_picks['player_name'].nunique()

        consensus = week_picks.groupby('team').agg({
            'player_name': 'count',
            'confidence': ['mean', 'sum']
        }).reset_index()

        consensus.columns = ['team', 'pick_count', 'avg_confidence', 'total_confidence']
        consensus['pick_percentage'] = consensus['pick_count'] / num_players
        consensus = consensus.sort_values('pick_count', ascending=False)

        return consensus

    def get_player_picks(self, player_name: str, week: Optional[int] = None) -> pd.DataFrame:
        """
        Get picks for a specific player, optionally filtered by week.

        Args:
            player_name: Player name to filter
            week: Optional week number to filter (None = all weeks)

        Returns:
            DataFrame of player's picks
        """
        if self.picks_df is None:
            self.build_picks_dataframe()

        picks = self.picks_df[self.picks_df['player_name'] == player_name]

        if week is not None:
            picks = picks[picks['week'] == week]

        return picks.sort_values(['week', 'confidence'], ascending=[True, False])

    def load_and_build_all(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Convenience method to load all data and build all DataFrames.

        Returns:
            Tuple of (picks_df, players_df, weekly_stats_df)
        """
        self.load_all_weeks()
        picks_df = self.build_picks_dataframe()
        players_df = self.build_players_dataframe()
        weekly_stats_df = self.build_weekly_stats_dataframe()

        return picks_df, players_df, weekly_stats_df


def load_competitor_data(data_dir: str = "out") -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Convenience function to load all competitor data.

    Args:
        data_dir: Directory containing week result JSON files

    Returns:
        Tuple of (picks_df, players_df, weekly_stats_df)
    """
    loader = CompetitorDataLoader(data_dir)
    return loader.load_and_build_all()


if __name__ == "__main__":
    # Demo/testing
    print("=" * 60)
    print("COMPETITOR DATA LOADER - DEMO")
    print("=" * 60)

    loader = CompetitorDataLoader()
    picks_df, players_df, weekly_stats_df = loader.load_and_build_all()

    print("\n" + "=" * 60)
    print("PICKS DATAFRAME")
    print("=" * 60)
    print(f"Shape: {picks_df.shape}")
    print(f"Columns: {list(picks_df.columns)}")
    print(f"\nSample (first 10 rows):")
    print(picks_df.head(10))

    print("\n" + "=" * 60)
    print("PLAYERS DATAFRAME (Top 10)")
    print("=" * 60)
    print(players_df.head(10).to_string(index=False))

    print("\n" + "=" * 60)
    print("WEEKLY STATS DATAFRAME")
    print("=" * 60)
    print(weekly_stats_df.to_string(index=False))

    print("\n" + "=" * 60)
    print("FIELD CONSENSUS - WEEK 4")
    print("=" * 60)
    consensus = loader.get_field_consensus(week=4)
    print(consensus.head(20).to_string(index=False))

    print("\n" + "=" * 60)
    print("SAMPLE PLAYER PICKS - Week 4")
    print("=" * 60)
    sample_player = players_df.iloc[0]['player_name']
    player_picks = loader.get_player_picks(sample_player, week=4)
    print(f"\nPlayer: {sample_player}")
    print(player_picks.to_string(index=False))
