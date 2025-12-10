from models.game_results import GameResults
from providers.file import load_json

def load_game_results(week: int) -> GameResults:
    """
    Load game results for a specific week from the database.

    Args:
        week: The week number to load results for.
    Returns:
        GameResults object containing the game results for the week.
    """
    filename = f"week_{week}_game_results.json"
    data = load_json(filename)
    return GameResults.from_dict(data)
    
    