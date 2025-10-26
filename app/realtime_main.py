"""
Realtime mode entry point for CBS Fantasy Tooling.

This mode keeps the browser open and polls for updates every 10 seconds,
saving directly to the Supabase database instead of files.

Usage:
    python realtime_main.py [--poll-interval SECONDS] [--week WEEK_NUM]
"""

import argparse
from datetime import datetime
from scrape_realtime import run_realtime_scraper
from config import Config
from storage import ResultsData
from publishers.database import DatabasePublisher


def get_weeks_since_start(start_date: str) -> int:
    """Calculate weeks since start date."""
    now = datetime.now()
    return (now - datetime.strptime(start_date, '%Y-%m-%d')).days // 7


def create_database_publisher(config: Config) -> DatabasePublisher:
    """Create and validate database publisher."""
    db_config = config.get_publisher_config('database')

    if not db_config or not db_config.get('url') or not db_config.get('key'):
        print("ERROR: Database configuration missing!")
        print("Please set SUPABASE_URL and SUPABASE_KEY in your .env file")
        return None

    db_pub = DatabasePublisher(db_config)

    if not db_pub.validate_config():
        print("ERROR: Database publisher configuration invalid")
        return None

    return db_pub


def main():
    """Main entry point for realtime mode."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Run CBS Fantasy scraper in realtime mode with database storage'
    )
    parser.add_argument(
        '--poll-interval',
        type=int,
        default=30,
        help='Seconds between polls (default: 30)'
    )
    parser.add_argument(
        '--week',
        type=int,
        help='Week number to scrape (default: auto-detect based on current date)'
    )
    args = parser.parse_args()

    # Load configuration
    config = Config()

    if not config.validate_scraping_config():
        print("ERROR: Scraping configuration invalid - check EMAIL and PASSWORD in .env")
        return

    # Create database publisher
    db_publisher = create_database_publisher(config)
    if not db_publisher:
        return

    # Determine week numbers
    if args.week:
        curr_week_no = args.week
        curr_week_no = args.week + 1
    else:
        curr_week_no = get_weeks_since_start(config.week_one_start_date)
        curr_week_no = curr_week_no + 1

    print("\n" + "=" * 60)
    print("CBS FANTASY TOOLING - REALTIME MODE")
    print("=" * 60)
    print(f"Scraping week: {curr_week_no}")
    print(f"Poll interval: {args.poll_interval} seconds")
    print(f"Database: Supabase")
    print("=" * 60 + "\n")

    # Test database connection
    print("Testing database connection...")
    if not db_publisher.db.test_connection():
        print("ERROR: Could not connect to database!")
        print("Please check your SUPABASE_URL and SUPABASE_KEY settings")
        return

    print("✓ Database connection successful\n")

    # Define update callback
    def on_update(results):
        """Called when new data is scraped."""
        try:
            # Convert to ResultsData
            results_data = ResultsData(results, curr_week_no)

            # Publish to database
            print("\nPublishing to database...")
            success = db_publisher.publish(results_data)

            if success:
                # Print summary
                wins_data = results_data.get_max_wins_data()
                points_data = results_data.get_max_points_data()

                print(f"\n{'=' * 60}")
                print(f"Week {curr_week_no} Summary (as of {results_data.timestamp.strftime('%H:%M:%S')})")
                print(f"{'=' * 60}")
                print(f"Most wins: {wins_data['max_wins']} - {wins_data['players']}")
                print(f"Most points: {points_data['max_points']} - {points_data['players']}")
                print(f"{'=' * 60}\n")
            else:
                print("⚠ Failed to publish to database")

        except Exception as e:
            print(f"⚠ Error in update callback: {e}")
            import traceback
            traceback.print_exc()

    # Run realtime scraper
    try:
        run_realtime_scraper(
            curr_week_number=curr_week_no,
            target_week_number=curr_week_no,
            poll_interval=args.poll_interval,
            on_update=on_update
        )
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n✓ Realtime scraper stopped")


if __name__ == '__main__':
    main()
