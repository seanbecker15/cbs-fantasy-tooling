"""
Database module for storing fantasy football results in Supabase.

This module provides a database storage layer that stores results in Supabase
instead of local files, enabling real-time updates and multi-device access.

Expected Supabase Schema:

Table: player_results
- id: bigint (primary key, auto-increment)
- season: int (not null) - NFL season year (e.g., 2025)
- week_number: int (not null)
- player_name: text (not null)
- points: int (not null)
- wins: int (not null)
- losses: int (not null)
- rank: int (nullable) - Current rank by points for the week
- points_from_leader: int (nullable) - Points behind the leader
- created_at: timestamp with time zone (default: now())
- updated_at: timestamp with time zone (default: now())
- UNIQUE constraint on (season, week_number, player_name)

Table: player_picks
- id: bigint (primary key, auto-increment)
- season: int (not null) - NFL season year (e.g., 2025)
- week_number: int (not null)
- player_name: text (not null)
- team: text (not null)
- confidence_points: int (not null)
- is_correct: boolean (nullable) - Whether the pick was correct (null if game not finished)
- opponent_team: text (nullable) - Opponent team for context
- game_time: timestamptz (nullable) - Scheduled game time
- created_at: timestamp with time zone (default: now())
- updated_at: timestamp with time zone (default: now())
- UNIQUE constraint on (season, week_number, player_name, team)

Table: game_status (for streaming overlay - shows which games are key)
- id: bigint (primary key, auto-increment)
- season: int (not null)
- week_number: int (not null)
- home_team: text (not null)
- away_team: text (not null)
- game_time: timestamptz (not null)
- is_finished: boolean (default: false)
- home_score: int (nullable)
- away_score: int (nullable)
- importance_score: int (nullable) - Calculated based on high-confidence picks
- viewer_interest: int (nullable) - Count of league members who picked this game
- created_at: timestamptz (default: now())
- updated_at: timestamptz (default: now())
- UNIQUE constraint on (season, week_number, home_team, away_team)

SQL to create tables:

-- Player results table
CREATE TABLE player_results (
    id BIGSERIAL PRIMARY KEY,
    season INT NOT NULL,
    week_number INT NOT NULL,
    player_name TEXT NOT NULL,
    points INT NOT NULL,
    wins INT NOT NULL,
    losses INT NOT NULL,
    rank INT,
    points_from_leader INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(season, week_number, player_name)
);

-- Player picks table
CREATE TABLE player_picks (
    id BIGSERIAL PRIMARY KEY,
    season INT NOT NULL,
    week_number INT NOT NULL,
    player_name TEXT NOT NULL,
    team TEXT NOT NULL,
    confidence_points INT NOT NULL,
    is_correct BOOLEAN,
    opponent_team TEXT,
    game_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(season, week_number, player_name, team)
);

-- Game status table (for streaming overlay)
CREATE TABLE game_status (
    id BIGSERIAL PRIMARY KEY,
    season INT NOT NULL,
    week_number INT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    game_time TIMESTAMPTZ NOT NULL,
    is_finished BOOLEAN DEFAULT FALSE,
    home_score INT,
    away_score INT,
    importance_score INT,
    viewer_interest INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(season, week_number, home_team, away_team)
);

-- Indexes for performance
CREATE INDEX idx_player_results_season_week ON player_results(season, week_number);
CREATE INDEX idx_player_results_rank ON player_results(season, week_number, rank);
CREATE INDEX idx_player_picks_season_week ON player_picks(season, week_number);
CREATE INDEX idx_player_picks_player ON player_picks(player_name, season, week_number);
CREATE INDEX idx_game_status_season_week ON game_status(season, week_number);
CREATE INDEX idx_game_status_time ON game_status(game_time);
CREATE INDEX idx_game_status_importance ON game_status(importance_score DESC);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE player_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_picks ENABLE ROW LEVEL SECURITY;
ALTER TABLE game_status ENABLE ROW LEVEL SECURITY;

-- Create policies (example: allow all for anon key)
CREATE POLICY "Enable read access for all users" ON player_results FOR SELECT USING (true);
CREATE POLICY "Enable insert for all users" ON player_results FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for all users" ON player_results FOR UPDATE USING (true);
CREATE POLICY "Enable delete for all users" ON player_results FOR DELETE USING (true);

CREATE POLICY "Enable read access for all users" ON player_picks FOR SELECT USING (true);
CREATE POLICY "Enable insert for all users" ON player_picks FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for all users" ON player_picks FOR UPDATE USING (true);
CREATE POLICY "Enable delete for all users" ON player_picks FOR DELETE USING (true);

CREATE POLICY "Enable read access for all users" ON game_status FOR SELECT USING (true);
CREATE POLICY "Enable insert for all users" ON game_status FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for all users" ON game_status FOR UPDATE USING (true);
CREATE POLICY "Enable delete for all users" ON game_status FOR DELETE USING (true);

-- Enable Realtime (for live updates)
-- Run this in Supabase Dashboard SQL editor or via API
-- Note: Realtime is enabled per-table in Supabase dashboard settings
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from supabase import create_client, Client
from storage import Row, ResultsData


class SupabaseDatabase:
    """
    Database storage using Supabase for real-time updates.
    """

    def __init__(self, url: str, key: str, season: int = None):
        """
        Initialize Supabase client.

        Args:
            url: Supabase project URL
            key: Supabase anon/service key
            season: NFL season year (default: current year)
        """
        self.client: Client = create_client(url, key)
        self.results_table = "player_results"
        self.picks_table = "player_picks"
        self.game_status_table = "game_status"
        self.season = season or datetime.now().year

    def save_results(self, results_data: ResultsData) -> bool:
        """
        Save results to Supabase database using upsert to handle updates.
        Automatically calculates rankings and metadata.

        Args:
            results_data: ResultsData object containing week results

        Returns:
            True if successful, False otherwise
        """
        if not results_data.week_number:
            print("Week number is required to save to database")
            return False

        try:
            week_number = results_data.week_number

            # Sort results by points to calculate rankings
            sorted_results = sorted(results_data.results, key=lambda r: int(r.results[0]), reverse=True)
            max_points = int(sorted_results[0].results[0]) if sorted_results else 0

            # Prepare player results for upsert
            player_results = []
            player_picks_all = []

            for rank, row in enumerate(sorted_results, start=1):
                points = int(row.results[0])
                points_from_leader = max_points - points

                # Player results record with ranking metadata
                player_result = {
                    'season': self.season,
                    'week_number': week_number,
                    'player_name': row.name,
                    'points': points,
                    'wins': row.results[1],
                    'losses': row.results[2],
                    'rank': rank,
                    'points_from_leader': points_from_leader,
                    'updated_at': results_data.timestamp.isoformat()
                }
                player_results.append(player_result)

                # Player picks records
                for pick in row.picks:
                    pick_record = {
                        'season': self.season,
                        'week_number': week_number,
                        'player_name': row.name,
                        'team': pick['team'],
                        'confidence_points': int(pick['points']),
                        'updated_at': results_data.timestamp.isoformat()
                    }
                    player_picks_all.append(pick_record)

            # Upsert player results (insert or update on conflict)
            print(f"Upserting {len(player_results)} player results for season {self.season} week {week_number}...")
            self.client.table(self.results_table)\
                .upsert(player_results, on_conflict='season,week_number,player_name')\
                .execute()

            # Upsert player picks
            if player_picks_all:
                print(f"Upserting {len(player_picks_all)} player picks for season {self.season} week {week_number}...")
                self.client.table(self.picks_table)\
                    .upsert(player_picks_all, on_conflict='season,week_number,player_name,team')\
                    .execute()

            print(f"Successfully saved data for season {self.season} week {week_number}")
            return True

        except Exception as e:
            print(f"Error saving to database: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_results(self, week_number: int, season: int = None) -> Optional[ResultsData]:
        """
        Retrieve results for a specific week from database.

        Args:
            week_number: Week number to retrieve
            season: Season year (defaults to instance season)

        Returns:
            ResultsData object or None if not found
        """
        season = season or self.season

        try:
            # Get player results
            results_response = self.client.table(self.results_table)\
                .select('*')\
                .eq('season', season)\
                .eq('week_number', week_number)\
                .execute()

            if not results_response.data:
                return None

            # Get player picks
            picks_response = self.client.table(self.picks_table)\
                .select('*')\
                .eq('season', season)\
                .eq('week_number', week_number)\
                .execute()

            # Group picks by player
            picks_by_player = {}
            for pick in picks_response.data:
                player_name = pick['player_name']
                if player_name not in picks_by_player:
                    picks_by_player[player_name] = []
                picks_by_player[player_name].append({
                    'team': pick['team'],
                    'points': str(pick['confidence_points'])
                })

            # Build ResultsData
            results = []
            for record in results_response.data:
                row = Row()
                row.name = record['player_name']
                row.results = [record['points'], record['wins'], record['losses']]
                row.picks = picks_by_player.get(record['player_name'], [])
                results.append(row)

            results_data = ResultsData(results, week_number)

            # Get timestamp from first record if available
            if results_response.data and 'updated_at' in results_response.data[0]:
                results_data.timestamp = datetime.fromisoformat(
                    results_response.data[0]['updated_at'].replace('Z', '+00:00')
                )

            return results_data

        except Exception as e:
            print(f"Error retrieving from database: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_latest_week(self, season: int = None) -> Optional[int]:
        """
        Get the latest week number in the database.

        Args:
            season: Season year (defaults to instance season)

        Returns:
            Latest week number or None if no data
        """
        season = season or self.season

        try:
            response = self.client.table(self.results_table)\
                .select('week_number')\
                .eq('season', season)\
                .order('week_number', desc=True)\
                .limit(1)\
                .execute()

            if response.data:
                return response.data[0]['week_number']
            return None

        except Exception as e:
            print(f"Error getting latest week: {e}")
            return None

    def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try a simple query
            self.client.table(self.results_table).select('id').limit(1).execute()
            print("Database connection test successful")
            return True
        except Exception as e:
            print(f"Database connection test failed: {e}")
            return False

    def delete_week(self, week_number: int, season: int = None) -> bool:
        """
        Delete all data for a specific week.

        Args:
            week_number: Week number to delete
            season: Season year (defaults to instance season)

        Returns:
            True if successful, False otherwise
        """
        season = season or self.season

        try:
            print(f"Deleting season {season} week {week_number} data...")

            # Delete player results
            self.client.table(self.results_table)\
                .delete()\
                .eq('season', season)\
                .eq('week_number', week_number)\
                .execute()

            # Delete player picks
            self.client.table(self.picks_table)\
                .delete()\
                .eq('season', season)\
                .eq('week_number', week_number)\
                .execute()

            print(f"Successfully deleted season {season} week {week_number} data")
            return True

        except Exception as e:
            print(f"Error deleting week data: {e}")
            return False


def compare_results(old_results: list[Row], new_results: list[Row]) -> Dict[str, Any]:
    """
    Deep comparison of two result sets to detect changes.

    Args:
        old_results: Previous results
        new_results: Current results

    Returns:
        Dictionary with change details:
        - changed: bool - Whether any changes detected
        - changes: list - List of specific changes
        - summary: str - Human-readable summary
    """
    changes = []

    # Quick checks
    if old_results is None or new_results is None:
        return {
            'changed': True,
            'changes': ['Initial data or one set is None'],
            'summary': 'Initial data load or missing data'
        }

    if len(old_results) != len(new_results):
        changes.append(f"Player count changed: {len(old_results)} → {len(new_results)}")

    # Create lookup dictionaries
    old_by_name = {row.name: row for row in old_results}
    new_by_name = {row.name: row for row in new_results}

    # Check each player
    for name in new_by_name:
        new_row = new_by_name[name]

        if name not in old_by_name:
            changes.append(f"New player: {name}")
            continue

        old_row = old_by_name[name]

        # Compare results (points, wins, losses)
        if old_row.results != new_row.results:
            old_points, old_wins, old_losses = old_row.results[0], old_row.results[1], old_row.results[2]
            new_points, new_wins, new_losses = new_row.results[0], new_row.results[1], new_row.results[2]

            if old_points != new_points:
                changes.append(f"{name}: points {old_points} → {new_points}")
            if old_wins != new_wins:
                changes.append(f"{name}: wins {old_wins} → {new_wins}")
            if old_losses != new_losses:
                changes.append(f"{name}: losses {old_losses} → {new_losses}")

        # Compare picks (deep comparison)
        old_picks_sorted = sorted(old_row.picks, key=lambda p: p.get('team', ''))
        new_picks_sorted = sorted(new_row.picks, key=lambda p: p.get('team', ''))

        if old_picks_sorted != new_picks_sorted:
            changes.append(f"{name}: picks changed")

    # Check for removed players
    for name in old_by_name:
        if name not in new_by_name:
            changes.append(f"Player removed: {name}")

    # Generate summary
    changed = len(changes) > 0
    summary = f"{len(changes)} change(s) detected" if changed else "No changes detected"

    return {
        'changed': changed,
        'changes': changes,
        'summary': summary
    }
