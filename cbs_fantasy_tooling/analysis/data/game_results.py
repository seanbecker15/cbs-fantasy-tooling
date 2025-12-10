from cbs_fantasy_tooling.config import config
from cbs_fantasy_tooling.publishers.file import JSON_FILENAMES



def assert_game_results(week: int):
    """
    Check if game results for the specified week are available locally.

    Args:
        week: NFL week number to check
    """
    import os

    results_file = os.path.join(config.output_dir, JSON_FILENAMES['game_results'](week))
    if not os.path.exists(results_file):
        raise FileNotFoundError(f"Game results for week {week} not found in {config.output_dir}")

    
def get_weeks_missing_game_results(week: int) -> list[int]:
    """
    Determine which weeks' game results are missing locally.

    Args:
        week: Current NFL week number

    Returns:
        List of week numbers that need to be fetched
    """
    import os

    missing_weeks = []
    for w in range(1, week + 1):
        results_file = os.path.join(config.output_dir, JSON_FILENAMES['game_results'](w))
        if not os.path.exists(results_file):
            missing_weeks.append(w)
    
    return missing_weeks
