import sys
from time import sleep

from cbs_fantasy_tooling.ingest.cbs_sports.scrape import PickemIngestParams, ingest_pickem_results
from cbs_fantasy_tooling.publishers.factory import create_publishers
from cbs_fantasy_tooling.utils.date import get_last_completed_week

# The scrape fails transiently now and then (a dropdown that has not rendered
# when it is looked up). Unattended, that used to mean silence until someone
# noticed. Space a few retries out so a flake at 9:30 lands by 10:30.
ATTEMPTS = 4
RETRY_DELAY_SECONDS = 15 * 60


def main(attempts: int = ATTEMPTS, delay_seconds: int = RETRY_DELAY_SECONDS) -> None:
    """Scheduled entrypoint: scrape the week that just finished and publish it."""
    target_week = get_last_completed_week()
    params = PickemIngestParams(target_week=target_week, curr_week=target_week + 1)

    for attempt in range(1, attempts + 1):
        print(f"[scrape] attempt {attempt}/{attempts} for week {target_week}")
        # Fresh publishers per attempt: a failed run may leave a stale session behind.
        if ingest_pickem_results(params, create_publishers()):
            sys.exit(0)
        if attempt < attempts:
            print(f"[scrape] attempt {attempt} failed; retrying in {delay_seconds}s")
            sleep(delay_seconds)

    # launchd only sees the exit code; a failed week must not look like success.
    print(f"[scrape] all {attempts} attempts failed for week {target_week}")
    sys.exit(1)


if __name__ == "__main__":
    main()
