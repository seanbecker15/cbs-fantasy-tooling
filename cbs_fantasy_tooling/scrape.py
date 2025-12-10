from cbs_fantasy_tooling.config import config
from cbs_fantasy_tooling.ingest.cbs_sports.scrape import PickemIngestParams, ingest_pickem_results
from cbs_fantasy_tooling.publishers.factory import create_publishers
from cbs_fantasy_tooling.utils.date import get_weeks_since_start


if __name__ == "__main__":
    target_week = get_weeks_since_start(config.week_one_start_date)
    current_week = target_week + 1

    publishers = create_publishers()
    params = PickemIngestParams(
        target_week=int(target_week),
        curr_week=int(current_week),
    )
    ingest_pickem_results(params, publishers)