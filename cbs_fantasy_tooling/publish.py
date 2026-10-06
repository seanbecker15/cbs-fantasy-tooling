"""Publish a week of pick'em results from a JSON file.

The browser extension scrapes standings and saves
week_N_pickem_results.json to Downloads. This copies it into OUTPUT_DIR and
runs the configured publishers (file, gmail) on it - the same path the
scheduled scraper takes after a scrape.

    cbs-publish ~/Downloads/week_4_pickem_results.json
    cbs-publish            # newest week_*_pickem_results.json in ~/Downloads
"""

import glob
import json
import os
import shutil
import sys
from pathlib import Path

from cbs_fantasy_tooling.config import config
from cbs_fantasy_tooling.ingest.cbs_sports.scrape import publish_results
from cbs_fantasy_tooling.models import PickemResults
from cbs_fantasy_tooling.publishers.factory import create_publishers
from cbs_fantasy_tooling.publishers.file import JSON_FILENAMES


class InvalidResults(ValueError):
    """The results file is not something we should email to the league."""


def validate(data: dict) -> None:
    """Refuse to publish a file that is obviously wrong."""
    week = data.get("week_number")
    if not isinstance(week, int) or not 1 <= week <= 18:
        raise InvalidResults(f"week_number must be 1-18, got {week!r}")
    rows = data.get("results") or []
    if len(rows) < 2:
        raise InvalidResults(f"expected a full standings table, got {len(rows)} rows")
    for r in rows:
        if not r.get("name"):
            raise InvalidResults("a row has no player name")
        if not str(r.get("points", "")).lstrip("-").isdigit():
            raise InvalidResults(f"{r['name']}: points is {r.get('points')!r}, not a number")
        picks = r.get("picks") or []
        if picks and r.get("wins", 0) + r.get("losses", 0) > len(picks):
            raise InvalidResults(f"{r['name']}: wins+losses exceeds pick count")


def newest_download() -> Path | None:
    pattern = str(Path.home() / "Downloads" / JSON_FILENAMES["pickem_results"]("*"))
    files = glob.glob(pattern)
    return Path(max(files, key=os.path.getmtime)) if files else None


def stage_into_output_dir(src: Path) -> Path:
    """Copy the file into OUTPUT_DIR under its canonical name; no-op if already there."""
    data = json.loads(src.read_text())
    dest = Path(config.output_dir) / JSON_FILENAMES["pickem_results"](data["week_number"])
    if src.resolve() != dest.resolve():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    return dest


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    src = Path(argv[0]).expanduser() if argv else newest_download()
    if src is None or not src.exists():
        print("No results file given and none found in ~/Downloads.")
        print("Usage: cbs-publish [path/to/week_N_pickem_results.json]")
        return 2

    data = json.loads(src.read_text())
    try:
        validate(data)
    except InvalidResults as e:
        print(f"Refusing to publish {src.name}: {e}")
        return 1

    dest = stage_into_output_dir(src)
    print(f"Publishing week {data['week_number']} from {dest}")
    results = PickemResults.from_dict(data)
    publishers = create_publishers()
    if not publishers:
        print("No publishers configured (check ENABLED_PUBLISHERS).")
        return 1
    publish_results(results, publishers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
