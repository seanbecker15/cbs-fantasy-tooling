from enum import Enum
from typing import List

from InquirerPy import inquirer
from InquirerPy.base.control import Choice

from cbs_fantasy_tooling.config import config
from cbs_fantasy_tooling.ingest.cbs_sports import PickemIngestParams, ingest_pickem_results
from cbs_fantasy_tooling.ingest.espn.api import GameOutcomeIngestParams, ingest_game_outcomes
from cbs_fantasy_tooling.models import PickemResults
from cbs_fantasy_tooling.publishers import Publisher
from cbs_fantasy_tooling.publishers.database import DatabasePublisher
from cbs_fantasy_tooling.publishers.file import FilePublisher
from cbs_fantasy_tooling.publishers.gmail import GmailPublisher
from cbs_fantasy_tooling.utils.date import get_weeks_since_start

def create_publishers():
    """Create and return list of enabled publishers"""
    publishers: List[Publisher] = []
    
    # File publisher (always safe to include)
    if config.is_publisher_enabled('file'):
        file_pub = FilePublisher(config.get_publisher_config('file'))
        if file_pub.validate_config() and file_pub.authenticate():
            publishers.append(file_pub)
        else:
            print("File publisher configuration invalid")
    
    # Gmail publisher
    if config.is_publisher_enabled('gmail'):
        gmail_pub = GmailPublisher(config.get_publisher_config('gmail'))
        if gmail_pub.validate_config() and gmail_pub.authenticate():
            publishers.append(gmail_pub)
        else:
            print("Gmail publisher configuration invalid - check credentials file and recipients")
    
    # Database publisher
    if config.is_publisher_enabled('database'):
        database_pub = DatabasePublisher(config.get_publisher_config('database'))
        if database_pub.validate_config() and database_pub.authenticate():
            publishers.append(database_pub)
        else:
            print("Database publisher configuration invalid")

    return publishers

class MenuOption(str, Enum):
    INGEST = "ingest"
    ANALYZE = "analyze"
    EXIT = "exit"


class DataType(str, Enum):
    PICKEM_RESULTS = "pickem_results"
    GAME_OUTCOMES = "game_outcomes"


class IngestMode(str, Enum):
    REAL_TIME = "real-time"
    ONCE = "once"


class AnalysisType(str, Enum):
    MATCHUP_REVIEW = "matchup_review"
    TREND_REPORT = "trend_report"


def prompt_menu_choice() -> MenuOption:
    choice = inquirer.select(
        message="What would you like to do?",
        choices=[
            Choice(value=MenuOption.INGEST, name="Ingest Data"),
            Choice(value=MenuOption.ANALYZE, name="Analyze Data"),
            Choice(value=MenuOption.EXIT, name="Exit"),
        ],
        default=MenuOption.INGEST,
    ).execute()
    return MenuOption(choice)


def ingest_flow(publishers: List[Publisher]):
    data_types = inquirer.checkbox(
        message="Select data type(s) to ingest",
        choices=[
            Choice(value=DataType.PICKEM_RESULTS, name="Pick'em Results"),
            Choice(value=DataType.GAME_OUTCOMES, name="Game Outcomes"),
        ],
        default=[DataType.PICKEM_RESULTS],
    ).execute()

    if not data_types:
        print("No data types selected for ingestion. Returning to main menu...\n")
        return

    mode = IngestMode(
        inquirer.select(
            message="Select mode",
            choices=[
                Choice(value=IngestMode.ONCE, name="Once"),
                Choice(value=IngestMode.REAL_TIME, name="Real-Time"),
            ],
            default=IngestMode.ONCE,
        ).execute()
    )

    target_week = inquirer.text(
        message="Target week number",
        default=str(get_weeks_since_start(config.week_one_start_date)),
    ).execute()

    if DataType.PICKEM_RESULTS in data_types:
        current_week = inquirer.text(
            message="Current week (for scraper dropdown)",
            default=str(get_weeks_since_start(config.week_one_start_date) + 1),
        ).execute()

        if mode == IngestMode.ONCE:
            params = PickemIngestParams(
                target_week=int(target_week),
                curr_week=int(current_week),
            )
            ingest_pickem_results(params, publishers)
        else:
            params = PickemIngestParams(
                target_week=int(target_week),
                curr_week=int(current_week),
                poll_interval=30,  # seconds
            )
            # TODO: run real-time ingestion loop in background until current process exits
            # ingest_pickem_results(params, publishers)

    if DataType.GAME_OUTCOMES in data_types:
        if mode == IngestMode.ONCE:
            params = GameOutcomeIngestParams(
                week=int(target_week),
            )
            ingest_game_outcomes(params, publishers)
        else:
            params = GameOutcomeIngestParams(
                week=int(target_week),
                poll_interval=30,  # seconds
            )
            # TODO: run real-time ingestion loop in background until current process exits
            # ingest_game_outcomes(params, publishers)
  
    print("Returning to main menu...\n")


def analysis_flow():
    analysis_types = inquirer.checkbox(
        message="Select analysis type(s)",
        choices=[
            Choice(value=AnalysisType.MATCHUP_REVIEW, name="Matchup Review"),
            Choice(value=AnalysisType.TREND_REPORT, name="Trend Report"),
        ],
        default=[AnalysisType.MATCHUP_REVIEW],
    ).execute()
    analysis_config = inquirer.text(
        message="Enter any analysis config options (key1=val1,key2=val2 or leave blank)",
        default="",
    ).execute()

    print(
        f"Configured analysis with analysis_types={analysis_types or '[]'}, "
        f"config='{analysis_config or 'default'}'."
    )
    print("TODO: call analyze_data(analysis_types, analysis_config)")
    print("Returning to main menu...\n")


def main():
    publishers = create_publishers()

    print(f"Created {len(publishers)} publishers:")
    for publisher in publishers:
        print(f" - {publisher.name}")

    while True:
        choice = prompt_menu_choice()

        if choice == MenuOption.INGEST:
            ingest_flow(publishers)
        elif choice == MenuOption.ANALYZE:
            analysis_flow()
        elif choice == MenuOption.EXIT:
            print("Exiting interactive menu.")
            break
        else:
            print("Invalid selection. Please try again.")

if __name__ == "__main__":
    main()
    
