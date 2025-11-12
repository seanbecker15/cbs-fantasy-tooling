"""
Entry point for ESPN game status polling pipeline.

Fetches NFL game status data from the ESPN API on a schedule and writes
updates to the Supabase `game_status` table.
"""

import argparse
import sys
import time
from datetime import datetime
from typing import List, Optional

from config import Config
from database import SupabaseDatabase
from game_status_fetcher import ESPNGameStatusFetcher, GameStatusRecord


def get_weeks_since_start(start_date: str) -> int:
    """Calculate the current week number (1-indexed) based on a start date."""
    now = datetime.now()
    weeks_elapsed = (now - datetime.strptime(start_date, '%Y-%m-%d')).days // 7
    return max(1, weeks_elapsed + 1)


def create_database_client(config: Config) -> Optional[SupabaseDatabase]:
    """Create and validate a Supabase database client."""
    db_config = config.get_publisher_config('database')

    if not db_config or not db_config.get('url') or not db_config.get('key'):
        print("ERROR: Missing Supabase configuration. Set SUPABASE_URL and SUPABASE_KEY in .env.")
        return None

    db = SupabaseDatabase(db_config['url'], db_config['key'], season=db_config.get('season'))

    if not db.test_connection():
        print("ERROR: Unable to connect to Supabase with provided credentials.")
        return None

    return db


def summarize_statuses(statuses: List[GameStatusRecord]) -> None:
    """Print a quick summary of the current game statuses."""
    finished = sum(1 for status in statuses if status.is_finished)
    total = len(statuses)
    print(f"Fetched {total} games ({finished} finished)")

    preview = statuses[:3]
    for status in preview:
        away_score = status.away_score if status.away_score is not None else '-'
        home_score = status.home_score if status.home_score is not None else '-'
        state = status.status_text or ('Final' if status.is_finished else 'Scheduled')
        print(f"  {status.away_team} @ {status.home_team} | {away_score}-{home_score} | {state}")


def poll_game_statuses(
    db: SupabaseDatabase,
    fetcher: ESPNGameStatusFetcher,
    week: int,
    poll_interval: int,
    run_once: bool
) -> None:
    """Continuously fetch and upsert game status data."""
    last_snapshot: Optional[List[dict]] = None

    try:
        while True:
            standings = fetcher.fetch_week_status(week)

            if not standings:
                print("No game status data returned from ESPN.")
            else:
                summarize_statuses(standings)
                payload = [status.to_db_dict() for status in standings]

                if payload != last_snapshot:
                    saved = db.upsert_game_statuses(payload)
                    if saved:
                        db.update_player_picks_from_game_statuses(standings)
                        last_snapshot = payload
                    else:
                        print("Skipping pick update due to game status upsert failure")
                else:
                    print("No changes detected since last poll.")

            if run_once:
                break

            time.sleep(poll_interval)

    except KeyboardInterrupt:
        print("\nPolling interrupted by user.")
    except Exception as exc:
        print(f"ERROR: Polling failed: {exc}")
        import traceback
        traceback.print_exc()


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Poll the ESPN API and populate Supabase game_status table."
    )
    parser.add_argument(
        '--week',
        type=int,
        help='NFL week number to poll (defaults to current week)'
    )
    parser.add_argument(
        '--season',
        type=int,
        help='NFL season year (defaults to Config.season)'
    )
    parser.add_argument(
        '--poll-interval',
        type=int,
        default=90,
        help='Seconds between polls (default: 90)'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run a single fetch/upsert cycle instead of continuous polling'
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    config = Config()

    db = create_database_client(config)
    if not db:
        sys.exit(1)

    season = args.season or config.season
    week = args.week or get_weeks_since_start(config.week_one_start_date)

    print("\n" + "=" * 60)
    print("GAME STATUS POLLING")
    print("=" * 60)
    print(f"Season: {season}")
    print(f"Week: {week}")
    print(f"Poll interval: {args.poll_interval} seconds")
    print(f"Run mode: {'once' if args.once else 'continuous'}")
    print("=" * 60 + "\n")

    fetcher = ESPNGameStatusFetcher(season=season)

    poll_game_statuses(
        db=db,
        fetcher=fetcher,
        week=week,
        poll_interval=args.poll_interval,
        run_once=args.once
    )


if __name__ == '__main__':
    main()
