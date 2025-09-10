import os
import requests
import numpy as np
from dotenv import load_dotenv
from statistics import median

load_dotenv()

API_KEY = os.getenv("THE_ODDS_API_KEY")
SPORT = "americanfootball_nfl"
REGION = "us"             # us | uk | eu | au
MARKETS = "h2h"           # add ",spreads,totals" if desired
ODDS_FORMAT = "american"  # american | decimal

def american_to_implied_prob(ml):
    # -200 -> 66.67%, +170 -> 37.04%
    if ml < 0:
        return (-ml) / ((-ml) + 100.0)
    else:
        return 100.0 / (ml + 100.0)

def devig_two_way(pA, pB, method="normalize"):
    # Basic de-vig: normalize so pA+pB == 1
    overround = pA + pB
    if overround <= 0: 
        return pA, pB
    return pA / overround, pB / overround

def get_commence_time_from():
    # Returns ISO 8601 string for previous Tuesday at 5 AM UTC
    from datetime import datetime, timedelta, time
    now = datetime.now()
    days_since_tue = (now.weekday() - 1) % 7
    last_tue = now - timedelta(days=days_since_tue)
    last_tue_5am = datetime.combine(last_tue.date(), time(5, 0))
    return last_tue_5am.isoformat() + "Z"

def get_commence_time_to():
    # Returns ISO 8601 string for next Tuesday at 4:59 AM UTC
    from datetime import datetime, timedelta, time
    now = datetime.now()
    days_since_tue = (now.weekday() - 1) % 7
    last_tue = now - timedelta(days=days_since_tue)
    last_tue_5am = datetime.combine(last_tue.date(), time(5, 0))
    next_tue_459am = last_tue_5am + timedelta(days=7, minutes=-1)
    return next_tue_459am.isoformat() + "Z"

def get_week_odds():
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": REGION,
        "markets": MARKETS,
        "oddsFormat": ODDS_FORMAT,
        "dateFormat": "iso",
        "commenceTimeFrom": get_commence_time_from(),
        "commenceTimeTo": get_commence_time_to()
    }
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def consensus_moneyline_probs(events, sharp_books=("Pinnacle", "Circa")):
    game_rows = []  # list of dicts: {id, home_team, away_team, p_home, p_away}
    for ev in events:
        eid = ev["id"]
        home = ev["home_team"]
        away = ev["away_team"]

        # gather per-bookmaker de-vigged probs for this event
        p_home_list = []
        p_away_list = []

        for book in ev.get("bookmakers", []):
            bk_name = book.get("title", "")
            markets = book.get("markets", [])
            # Find h2h market
            m = next((m for m in markets if m.get("key") == "h2h"), None)
            if not m: 
                continue
            outcomes = {o["name"]: o for o in m.get("outcomes", [])}
            if home not in outcomes or away not in outcomes:
                continue

            ml_home = outcomes[home].get("price")  # American line as int
            ml_away = outcomes[away].get("price")

            if ml_home is None or ml_away is None:
                continue

            p_home_raw = american_to_implied_prob(ml_home)
            p_away_raw = american_to_implied_prob(ml_away)
            p_home_fair, p_away_fair = devig_two_way(p_home_raw, p_away_raw)

            # Weight sharp books higher by duplicating entries (simple, transparent)
            weight = 2 if any(s in bk_name for s in sharp_books) else 1
            p_home_list.extend([p_home_fair] * weight)
            p_away_list.extend([p_away_fair] * weight)

        if not p_home_list or not p_away_list:
            continue

        # consensus = median (robust to outliers)
        p_home_cons = median(p_home_list)
        p_away_cons = median(p_away_list)

        game_rows.append({
            "id": eid,
            "home_team": home,
            "away_team": away,
            "p_home": p_home_cons,
            "p_away": p_away_cons
        })

    return game_rows

def to_GAME_PROBS(game_rows, pick_favorite=True):
    probs = []
    mapping = []  # keep which team is "favorite" at index i
    for g in game_rows:
        if g["p_home"] >= g["p_away"]:
            fav_prob = g["p_home"]
            fav_team = g["home_team"]
            dog_team = g["away_team"]
        else:
            fav_prob = g["p_away"]
            fav_team = g["away_team"]
            dog_team = g["home_team"]

        probs.append(fav_prob)
        mapping.append({"favorite": fav_team, "dog": dog_team, "p_fav": fav_prob})
    return np.array(probs), mapping

# --- fetch & build weekly GAME_PROBS ---
events = get_week_odds()
rows = consensus_moneyline_probs(events)
GAME_PROBS, WEEK_MAPPING = to_GAME_PROBS(rows)
# print(f"{len(GAME_PROBS)} games loaded. Example:", WEEK_MAPPING[0])

# save events to file for debugging
with open("simulator_weekly_events.txt", "w") as f:
    for ev in events:
        f.write(f"{ev}\n")



# save to file for debugging
with open("simulator_weekly_probs.txt", "w") as f:
    for r in WEEK_MAPPING:
        f.write(f"{r}\n")
