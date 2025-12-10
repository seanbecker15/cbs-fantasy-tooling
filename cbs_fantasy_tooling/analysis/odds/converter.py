"""Odds conversion and de-vig utilities."""

from statistics import median
import numpy as np


def american_to_implied_prob(ml: int) -> float | None:
    """
    Convert an American moneyline to an implied probability (with vig).

    Args:
        ml: American moneyline (e.g., -150, +200)

    Returns:
        Implied probability or None if invalid
    """
    if ml is None:
        return None
    if ml < 0:
        return (-ml) / ((-ml) + 100.0)
    return 100.0 / (ml + 100.0)


def devig_two_way(pA: float | None, pB: float | None) -> tuple[float | None, float | None]:
    """
    Remove the vig for a two-outcome market via simple normalization.

    Uses: pA' = pA / (pA + pB), pB' = pB / (pA + pB)
    For more sophistication, could use Shin/multiplicative method.

    Args:
        pA: Implied probability for outcome A (with vig)
        pB: Implied probability for outcome B (with vig)

    Returns:
        Tuple of (devigged_pA, devigged_pB)
    """
    if pA is None or pB is None:
        return None, None
    s = pA + pB
    if s <= 0:
        return None, None
    return pA / s, pB / s


def consensus_moneyline_probs(events: list[dict], sharp_books: tuple[str, ...],
                              sharp_weight: int) -> list[dict]:
    """
    Build consensus de-vig probabilities per game from multiple sportsbooks.

    Args:
        events: List of event dictionaries from The Odds API
        sharp_books: Tuple of sharp book names to overweight
        sharp_weight: Weight multiplier for sharp books

    Returns:
        List of game dictionaries with consensus probabilities:
        {id, home_team, away_team, p_home, p_away, commence_time}
    """
    rows = []
    for ev in events:
        eid = ev.get("id")
        home = ev.get("home_team")
        away = ev.get("away_team")
        commence = ev.get("commence_time")

        if not home or not away:
            continue

        p_home_list, p_away_list = [], []

        for book in ev.get("bookmakers", []):
            title = book.get("title", "") or ""
            # Find the h2h market
            m = next((m for m in book.get("markets", []) if m.get("key") == "h2h"), None)
            if not m:
                continue
            outcomes = {o["name"]: o for o in m.get("outcomes", [])}
            if home not in outcomes or away not in outcomes:
                continue

            ml_home = outcomes[home].get("price")
            ml_away = outcomes[away].get("price")

            p_home_raw = american_to_implied_prob(ml_home)
            p_away_raw = american_to_implied_prob(ml_away)
            p_home_fair, p_away_fair = devig_two_way(p_home_raw, p_away_raw)
            if p_home_fair is None or p_away_fair is None:
                continue

            # Simple sharp weighting by duplication
            weight = sharp_weight if any(s in title for s in sharp_books) else 1
            p_home_list.extend([p_home_fair] * weight)
            p_away_list.extend([p_away_fair] * weight)

        if not p_home_list or not p_away_list:
            continue

        rows.append({
            "id": eid,
            "home_team": home,
            "away_team": away,
            "p_home": median(p_home_list),
            "p_away": median(p_away_list),
            "commence_time": commence,
        })
    return rows


def rows_to_game_probs(rows: list[dict]) -> tuple[np.ndarray, list[dict]]:
    """
    Convert per-game rows to probability arrays and mapping.

    Args:
        rows: List of game dictionaries with p_home and p_away

    Returns:
        Tuple of:
        - GAME_PROBS: np.array of the favorite's win prob per game
        - MAPPING: list of {favorite, dog, p_fav, home_team, away_team, id, commence_time}
    """
    probs, mapping = [], []
    for g in rows:
        if g["p_home"] >= g["p_away"]:
            fav_prob, fav_team, dog_team = g["p_home"], g["home_team"], g["away_team"]
        else:
            fav_prob, fav_team, dog_team = g["p_away"], g["away_team"], g["home_team"]
        probs.append(fav_prob)
        mapping.append({
            "id": g["id"],
            "home_team": g["home_team"],
            "away_team": g["away_team"],
            "favorite": fav_team,
            "dog": dog_team,
            "p_fav": float(fav_prob),
            "commence_time": g.get("commence_time"),
        })
    return np.array(probs, dtype=float), mapping
