"""
Database publisher for storing fantasy football results in Supabase.
"""

from typing import Dict, Any
from cbs_fantasy_tooling.models import PickemResults, GameResults
from cbs_fantasy_tooling.storage.providers.database import SupabaseDatabase

from . import Publisher

class DatabasePublisher(Publisher):
    """Publisher that saves results to Supabase database."""
    name = "database"

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize database publisher.

        Args:
            config: Configuration dictionary with keys:
                - url: Supabase project URL
                - key: Supabase anon/service key
                - season: NFL season year (optional)
        """
        self.config = config
        self.db = None

        if self.validate_config():
            season = config.get('season')
            self.db = SupabaseDatabase(config['url'], config['key'], season=season)

    def validate_config(self) -> bool:
        """
        Validate publisher configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        required_keys = ['url', 'key']
        for key in required_keys:
            if key not in self.config or not self.config[key]:
                print(f"Database publisher missing required config: {key}")
                return False
        return True

    def publish_pickem_results(self, results_data: PickemResults) -> bool:
        """
        Publish results to Supabase database.

        Args:
            results_data: The results data to publish

        Returns:
            True if publishing succeeded, False otherwise
        """
        if not self.db:
            print("Database publisher not initialized - invalid config")
            return False

        try:
            # Test connection first
            if not self.db.test_connection():
                print("Database connection failed")
                return False

            # Save results
            success = self.db.save_results(results_data)

            if success:
                print(f"Successfully published week {results_data.week_number} to database")
                print(f"Saved {len(results_data.results)} player results")
            else:
                print("Failed to publish to database")

            return success

        except Exception as e:
            print(f"Error publishing to database: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    def publish_game_results(self, results_data: GameResults) -> bool:
        """
        Publish game results to Supabase database.

        Args:
            results_data: The game results data to publish

        Returns:
            True if publishing succeeded, False otherwise
        """
        if not self.db:
            print("Database publisher not initialized - invalid config")
            return False

        try:
            # Test connection first
            if not self.db.test_connection():
                print("Database connection failed")
                return False
            
            # Prepare data for upsert
            game_results = results_data.games
            db_payload = [game_status.to_dict() for game_status in game_results]
            saved = self.db.upsert_game_statuses(db_payload)
            if saved:
                print(f"Upserted {len(db_payload)} game statuses into the database.")
                player_picks_saved = self.db.update_player_picks_from_game_statuses(game_results)
                if player_picks_saved:
                    print(f"Updated player picks based on latest game outcomes.")

            if saved:
                print(f"Successfully published game results for week {results_data.week} to database")
            else:
                print("Failed to publish game results to database")

            return saved

        except Exception as e:
            print(f"Error publishing game results to database: {e}")
            import traceback
            traceback.print_exc()
            return False
