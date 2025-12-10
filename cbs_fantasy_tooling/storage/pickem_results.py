from models.pickem_results import PickemResults
from providers.file import load_json

def load_pickem_results(week: int) -> PickemResults:
    """
    Load game results for a specific week from the database.

    Args:
        week: The week number to load results for.
    Returns:
        PickemResults object containing the pickem results for the week.
    """
    filename = f"week_{week}_pickem_results.json"
    data = load_json(filename)
    return PickemResults.from_dict(data)
    
    