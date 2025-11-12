"""
Database publisher for storing fantasy football results in Supabase.
"""

from typing import Dict, Any
from storage import ResultsData
from database import SupabaseDatabase


class DatabasePublisher:
    """Publisher that saves results to Supabase database."""

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

    def test_authentication(self) -> bool:
        """Test database connection before scraping"""
        if not self.db:
            print("✗ Database publisher not initialized - invalid config")
            return False

        try:
            if self.db.test_connection():
                print("✓ Database connection successful")
                return True
            else:
                print("✗ Database connection failed")
                return False
        except Exception as error:
            print(f"✗ Database connection error: {error}")
            return False

    def publish(self, results_data: ResultsData) -> bool:
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
