import sys

from cbs_fantasy_tooling.ingest.cbs_sports.scrape import PickemIngestParams, ingest_pickem_results
from cbs_fantasy_tooling.publishers.factory import create_publishers
from cbs_fantasy_tooling.utils.date import get_last_completed_week


def main() -> None:
    """Scheduled entrypoint: scrape the week that just finished and publish it."""
    target_week = get_last_completed_week()
    publishers = create_publishers()
    params = PickemIngestParams(target_week=target_week, curr_week=target_week + 1)
    ok = ingest_pickem_results(params, publishers)
    # launchd only sees the exit code; a failed week must not look like success.
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
