from enum import Enum
from typing import List
import threading

from InquirerPy import inquirer
from InquirerPy.base.control import Choice

from cbs_fantasy_tooling.config import config
from cbs_fantasy_tooling.analysis import (
    run_strategy_simulation,
    analyze_competitors,
    analyze_contrarian_picks,
)
from cbs_fantasy_tooling.ingest.cbs_sports import PickemIngestParams, ingest_pickem_results
from cbs_fantasy_tooling.ingest.espn.api import GameOutcomeIngestParams, ingest_game_outcomes
from cbs_fantasy_tooling.publishers import Publisher
from cbs_fantasy_tooling.publishers.factory import create_publishers
from cbs_fantasy_tooling.utils.date import get_current_nfl_week


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
    CONFIDENCE_POOL_STRATEGY = "confidence_pool_strategy"
    COMPETITOR_INTELLIGENCE = "competitor_intelligence"
    VISUALIZE_CONTRARIAN_PICKS = "visualize_contrarian_picks"


# Global list to track background ingestion threads
_background_threads: List[threading.Thread] = []
_threads_lock = threading.Lock()


def start_background_ingestion(target_func, *args, **kwargs):
    """
    Start an ingestion function in a background thread.

    Args:
        target_func: The ingestion function to run (e.g., ingest_game_outcomes)
        *args, **kwargs: Arguments to pass to the target function

    Returns:
        The started thread
    """
    thread = threading.Thread(target=target_func, args=args, kwargs=kwargs, daemon=True)
    thread.start()
    with _threads_lock:
        _background_threads.append(thread)
    return thread


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
        default=str(get_current_nfl_week()),
    ).execute()

    if DataType.PICKEM_RESULTS in data_types:
        current_week = inquirer.text(
            message="Current week (for scraper dropdown)",
            default=str(get_current_nfl_week() + 1),
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
            print("Starting Pick'em Results real-time ingestion in background (30s interval)...")
            start_background_ingestion(ingest_pickem_results, params, publishers)
            print("✓ Pick'em Results ingestion started in background")

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
            print("Starting Game Outcomes real-time ingestion in background (30s interval)...")
            start_background_ingestion(ingest_game_outcomes, params, publishers)
            print("✓ Game Outcomes ingestion started in background")

    print("Returning to main menu...\n")


def analysis_flow():
    analysis_types = inquirer.checkbox(
        message="Select analysis type(s)",
        choices=[
            Choice(
                value=AnalysisType.CONFIDENCE_POOL_STRATEGY,
                name="Confidence Pool Strategy Simulator",
            ),
            Choice(
                value=AnalysisType.COMPETITOR_INTELLIGENCE, name="Competitor Intelligence Analysis"
            ),
            Choice(
                value=AnalysisType.VISUALIZE_CONTRARIAN_PICKS, name="Visualize Contrarian Picks"
            ),
        ],
        default=[AnalysisType.CONFIDENCE_POOL_STRATEGY],
    ).execute()

    if not analysis_types:
        print("No analysis types selected. Returning to main menu...\n")
        return

    # Handle Confidence Pool Strategy Simulation
    if AnalysisType.CONFIDENCE_POOL_STRATEGY in analysis_types:
        user_picks_input = inquirer.text(
            message="Enter your picks (comma-separated team names, or leave blank)",
            default="",
        ).execute()

        user_picks = user_picks_input if user_picks_input.strip() else None

        analyze_only = False
        if user_picks:
            analyze_only = inquirer.confirm(
                message="Analyze only your picks (skip built-in strategies)?",
                default=False,
            ).execute()

        print("\n" + "=" * 60)
        print("RUNNING CONFIDENCE POOL STRATEGY SIMULATION")
        print("=" * 60)

        results = run_strategy_simulation(user_picks=user_picks, analyze_only=analyze_only)

        if not analyze_only:
            print("\n" + "=" * 60)
            print("STRATEGY COMPARISON")
            print("=" * 60)
            print(results["comparison_df"].round(4).to_string(index=False))

            print("\nResults saved to output directory")

    # Handle Competitor Intelligence Analysis
    if AnalysisType.COMPETITOR_INTELLIGENCE in analysis_types:
        target_week_input = inquirer.text(
            message="Analyze contrarian opportunities for week (or leave blank for overview only)",
            default="",
        ).execute()

        target_week = int(target_week_input) if target_week_input.strip() else None

        print("\n" + "=" * 60)
        print("RUNNING COMPETITOR INTELLIGENCE ANALYSIS")
        print("=" * 60)

        results = analyze_competitors(data_dir=config.output_dir, week=target_week)

    if AnalysisType.VISUALIZE_CONTRARIAN_PICKS in analysis_types:
        target_week_input = inquirer.text(
            message="Visualize contrarian picks for week number",
            default=str(get_current_nfl_week()),
        ).execute()

        target_week = int(target_week_input)

        print("\n" + "=" * 60)
        print("VISUALIZING CONTRARIAN PICKS")
        print("=" * 60)

        analyze_contrarian_picks(week=target_week)

    print("\nReturning to main menu...\n")


def main():
    publishers = create_publishers()

    print(f"Created {len(publishers)} publishers:")
    for publisher in publishers:
        print(f" - {publisher.name}")

    while True:
        # Show status of background threads if any are active
        with _threads_lock:
            active_threads = [t for t in _background_threads if t.is_alive()]
        if active_threads:
            print(f"\n📡 {len(active_threads)} background ingestion thread(s) running")

        choice = prompt_menu_choice()

        if choice == MenuOption.INGEST:
            ingest_flow(publishers)
        elif choice == MenuOption.ANALYZE:
            analysis_flow()
        elif choice == MenuOption.EXIT:
            with _threads_lock:
                active_threads = [t for t in _background_threads if t.is_alive()]
            if active_threads:
                print(
                    f"\nNote: {len(active_threads)} background ingestion thread(s) will stop when the program exits."
                )
            print("Exiting interactive menu.")
            break
        else:
            print("Invalid selection. Please try again.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGoodbye!")
