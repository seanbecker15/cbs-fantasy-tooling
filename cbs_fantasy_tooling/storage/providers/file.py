import os

from cbs_fantasy_tooling.config import config


def save_json(data: dict, filename: str) -> None:
    """
    Save data as JSON to a file.

    Args:
        data: Dictionary to save as JSON.
        file_path: Path to the output JSON file.
    """
    import json

    filepath = os.path.join(config.output_dir, filename)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def load_json(filename: str) -> dict:
    """
    Load JSON data from a file.

    Args:
        file_path: Path to the JSON file.
    Returns:
        Dictionary with the loaded JSON data.
    """
    import json

    filepath = os.path.join(config.output_dir, filename)
    with open(filepath, "r") as f:
        data = json.load(f)
    return data
