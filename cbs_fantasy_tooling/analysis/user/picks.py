"""User pick parsing and validation."""

from difflib import get_close_matches
import numpy as np


def normalize_team_name(user_team: str, available_teams: list[str]) -> str:
    """
    Normalize user input team name to match available team names.
    Handles common variations and abbreviations.

    Args:
        user_team: User's team name input
        available_teams: List of valid team names for this week

    Returns:
        Normalized team name matching available teams

    Raises:
        ValueError: If team cannot be matched
    """
    user_team = user_team.strip()

    # Direct match first
    for team in available_teams:
        if user_team.lower() == team.lower():
            return team

    # Try partial matching (e.g., "Ravens" -> "Baltimore Ravens")
    for team in available_teams:
        if user_team.lower() in team.lower() or team.lower() in user_team.lower():
            return team

    # Common abbreviations mapping
    abbrev_map = {
        'bal': 'baltimore ravens', 'buf': 'buffalo bills', 'mia': 'miami dolphins',
        'ne': 'new england patriots', 'nyj': 'new york jets', 'pit': 'pittsburgh steelers',
        'cle': 'cleveland browns', 'cin': 'cincinnati bengals', 'hou': 'houston texans',
        'ind': 'indianapolis colts', 'jax': 'jacksonville jaguars', 'ten': 'tennessee titans',
        'den': 'denver broncos', 'kc': 'kansas city chiefs', 'lv': 'las vegas raiders',
        'lac': 'los angeles chargers', 'dal': 'dallas cowboys', 'nyg': 'new york giants',
        'phi': 'philadelphia eagles', 'was': 'washington commanders', 'chi': 'chicago bears',
        'det': 'detroit lions', 'gb': 'green bay packers', 'min': 'minnesota vikings',
        'atl': 'atlanta falcons', 'car': 'carolina panthers', 'no': 'new orleans saints',
        'tb': 'tampa bay buccaneers', 'ari': 'arizona cardinals', 'lar': 'los angeles rams',
        'sea': 'seattle seahawks', 'sf': 'san francisco 49ers'
    }

    user_lower = user_team.lower()
    for abbrev, full_name in abbrev_map.items():
        if user_lower == abbrev:
            # Find matching team in available teams
            for team in available_teams:
                if full_name in team.lower():
                    return team

    # Fuzzy matching as last resort
    matches = get_close_matches(user_team, available_teams, n=1, cutoff=0.6)
    if matches:
        return matches[0]

    raise ValueError(f"Could not match team '{user_team}' to available teams: {available_teams}")


def validate_user_picks(user_picks: list[str], week_mapping: list[dict]) -> tuple[list[str], list[str]]:
    """
    Validate user picks against available teams for the current week.

    Args:
        user_picks: List of team names in confidence order
        week_mapping: Current week's games mapping

    Returns:
        Tuple of (normalized_picks, error_messages)
    """
    errors = []
    normalized_picks = []

    # Extract all available teams from week mapping
    all_teams = set()
    for game in week_mapping:
        all_teams.add(game["home_team"])
        all_teams.add(game["away_team"])
    all_teams = list(all_teams)

    if len(user_picks) != len(week_mapping):
        errors.append(f"Expected {len(week_mapping)} picks, got {len(user_picks)}")
        return [], errors

    for i, pick in enumerate(user_picks, 1):
        try:
            normalized = normalize_team_name(pick, all_teams)
            normalized_picks.append(normalized)
        except ValueError as e:
            errors.append(f"Pick {i}: {str(e)}")

    # Check for duplicates
    if len(set(normalized_picks)) != len(normalized_picks):
        duplicates = [pick for pick in set(normalized_picks) if normalized_picks.count(pick) > 1]
        errors.append(f"Duplicate picks found: {duplicates}")

    return normalized_picks, errors


def parse_user_picks(user_input: str | list, week_mapping: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """
    Parse user picks from various input formats into picks and confidence arrays.

    Args:
        user_input: String (comma-separated) or list of team names in confidence order (16->1)
        week_mapping: Current week's games mapping

    Returns:
        Tuple of (picks_array, confidence_array) where:
        - picks_array: 1 for favorite, 0 for underdog
        - confidence_array: confidence levels 1-16

    Raises:
        ValueError: If picks are invalid
    """
    # Handle string input
    if isinstance(user_input, str):
        user_picks = [team.strip() for team in user_input.split(',')]
    else:
        user_picks = user_input

    # Validate picks
    normalized_picks, errors = validate_user_picks(user_picks, week_mapping)
    if errors:
        raise ValueError("Validation errors:\n" + "\n".join(errors))

    # Create picks and confidence arrays
    num_games = len(week_mapping)
    picks = np.zeros(num_games, dtype=int)
    confidence = np.zeros(num_games, dtype=int)

    # Create a copy to avoid modifying the original
    remaining_picks = normalized_picks.copy()

    for i, game in enumerate(week_mapping):
        # Find which team user picked for this game
        user_pick = None
        confidence_level = None
        pick_index = None

        for j, pick in enumerate(remaining_picks):
            if pick == game["home_team"] or pick == game["away_team"]:
                user_pick = pick
                # Find the original position in the user's pick order
                original_index = normalized_picks.index(pick)
                confidence_level = num_games - original_index  # First pick = 16, last pick = 1
                pick_index = j
                break

        if user_pick is None:
            raise ValueError(f"No pick found for game: {game['away_team']} at {game['home_team']}")

        confidence[i] = confidence_level
        # Remove from remaining picks
        remaining_picks.pop(pick_index)

        # Determine if pick is favorite (1) or underdog (0)
        if user_pick == game["favorite"]:
            picks[i] = 1
        else:
            picks[i] = 0

    return picks, confidence


def create_user_strategy(user_picks: np.ndarray, user_confidence: np.ndarray):
    """
    Create a strategy function from user picks that can be used in simulations.

    Args:
        user_picks: Array of picks (1=favorite, 0=underdog)
        user_confidence: Array of confidence levels

    Returns:
        Strategy function compatible with simulator
    """
    def user_strategy_fn(_):
        # Return the user's fixed picks and confidence, ignoring probabilities
        return user_picks.copy(), user_confidence.copy()

    return user_strategy_fn
