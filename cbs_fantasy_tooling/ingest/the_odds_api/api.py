from datetime import datetime
import requests

from cbs_fantasy_tooling import config

SPORT = "americanfootball_nfl"
REGION = "us"  # us|uk|eu|au (controls which books)
MARKETS = "h2h"  # moneylines for win probabilities
ODDS_FORMAT = "american"  # american|decimal


def fetch_odds(from_date: datetime, to_date: datetime) -> list[dict]:
    """Fetch current NFL moneylines across US books, restricted to *this* week."""
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"
    params = {
        "apiKey": config.the_odds_api_key,
        "regions": REGION,
        "markets": MARKETS,
        "oddsFormat": ODDS_FORMAT,
        "dateFormat": "iso",
        "commenceTimeFrom": format_date(from_date),
        "commenceTimeTo": format_date(to_date),
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    # Optional: examine quota headers
    # print("Remaining:", r.headers.get("x-requests-remaining"), "Used:", r.headers.get("x-requests-used"))
    return r.json()


def format_date(date: datetime) -> str:
    """Takes datetime and returns formatted string for API."""
    return date.isoformat().replace("+00:00", "Z")
