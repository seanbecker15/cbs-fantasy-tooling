"""Shared helpers for normalizing team names/abbreviations."""


def normalize_team_name(user_team: str, available_teams: list[str]) -> str:
    """
    Normalize team names/abbreviations to one of the provided teams.

    Args:
        user_team: Input team string (may be abbrev or partial)
        available_teams: Valid team strings to match against

    Returns:
        Matched team string from available_teams

    Raises:
        ValueError if no match found.
    """
    user_team = user_team.strip()
    avail_lower = {team.lower(): team for team in available_teams}

    if user_team.lower() in avail_lower:
        return avail_lower[user_team.lower()]

    abbrev_map = {
        "bal": "baltimore ravens",
        "buf": "buffalo bills",
        "mia": "miami dolphins",
        "ne": "new england patriots",
        "nyj": "new york jets",
        "pit": "pittsburgh steelers",
        "cle": "cleveland browns",
        "cin": "cincinnati bengals",
        "hou": "houston texans",
        "ind": "indianapolis colts",
        "jax": "jacksonville jaguars",
        "ten": "tennessee titans",
        "den": "denver broncos",
        "kc": "kansas city chiefs",
        "lv": "las vegas raiders",
        "lac": "los angeles chargers",
        "dal": "dallas cowboys",
        "nyg": "new york giants",
        "phi": "philadelphia eagles",
        "was": "washington commanders",
        "chi": "chicago bears",
        "det": "detroit lions",
        "gb": "green bay packers",
        "min": "minnesota vikings",
        "atl": "atlanta falcons",
        "car": "carolina panthers",
        "no": "new orleans saints",
        "tb": "tampa bay buccaneers",
        "ari": "arizona cardinals",
        "lar": "los angeles rams",
        "sea": "seattle seahawks",
        "sf": "san francisco 49ers",
    }

    user_lower = user_team.lower()
    for abbrev, full_name in abbrev_map.items():
        if user_lower == abbrev:
            for team in available_teams:
                if full_name in team.lower():
                    return team
        if user_lower == full_name:
            # Map full name to abbreviation if that's what's available
            if abbrev in avail_lower:
                return avail_lower[abbrev]
            for team in available_teams:
                if full_name in team.lower():
                    return team

    for team in available_teams:
        if user_team.lower() in team.lower() or team.lower() in user_team.lower():
            return team

    raise ValueError(f"Could not match team '{user_team}' to available teams: {available_teams}")
