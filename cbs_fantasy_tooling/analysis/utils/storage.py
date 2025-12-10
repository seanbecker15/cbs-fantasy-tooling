"""Prediction storage utilities."""

import os
import json
from datetime import datetime
import numpy as np
from cbs_fantasy_tooling.analysis.core.config import STRATEGY_CODES
from cbs_fantasy_tooling.utils.date import get_current_nfl_week


def save_predictions(strategy_name: str, picks: np.ndarray, confidence: np.ndarray,
                    week_mapping: list[dict], game_probs: np.ndarray = None) -> str:
    """
    Save strategy predictions to JSON file following the existing file naming pattern.

    Args:
        strategy_name: Name of the strategy
        picks: Picks array (1=favorite, 0=underdog)
        confidence: Confidence levels array
        week_mapping: Week's game mapping
        game_probs: Optional game probabilities

    Returns:
        Filename of the saved file
    """
    # Create out directory if it doesn't exist
    os.makedirs("out", exist_ok=True)

    # Get current week and timestamp
    current_week = get_current_nfl_week()
    strategy_code = STRATEGY_CODES.get(strategy_name, strategy_name.lower().replace("-", ""))

    # Build filename following existing pattern
    filename = f"week_{current_week}_predictions_{strategy_code}.json"
    filepath = os.path.join("out", filename)

    # Build prediction data structure
    predictions = {
        "metadata": {
            "strategy": strategy_name,
            "week": current_week,
            "generated_at": datetime.now().isoformat(),
            "total_games": len(week_mapping),
            "simulator_version": "v2"
        },
        "games": []
    }

    # Add each game with predictions
    for i, game in enumerate(week_mapping):
        pick_team = game["favorite"] if picks[i] == 1 else game["dog"]
        pick_is_favorite = bool(picks[i] == 1)

        game_data = {
            "game_id": game.get("id", f"game_{i+1}"),
            "away_team": game["away_team"],
            "home_team": game["home_team"],
            "favorite": game["favorite"],
            "dog": game["dog"],
            "favorite_prob": float(game["p_fav"]),
            "commence_time": game.get("commence_time"),
            "prediction": {
                "pick_team": pick_team,
                "pick_is_favorite": pick_is_favorite,
                "confidence_level": int(confidence[i]),
                "confidence_rank": int(len(week_mapping) - confidence[i] + 1)  # 1 = highest confidence
            }
        }
        predictions["games"].append(game_data)

    # Sort games by confidence level (highest first)
    predictions["games"].sort(key=lambda x: x["prediction"]["confidence_level"], reverse=True)

    # Save to file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(predictions, f, indent=2, ensure_ascii=False)

    return filename
