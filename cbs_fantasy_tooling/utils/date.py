from datetime import datetime, time, timedelta, timezone

from cbs_fantasy_tooling import config


def get_current_nfl_week() -> int:
    """
    Calculate the current NFL week based on configured start date.

    Returns:
        Current NFL week number (1-18)
    """
    now = datetime.now()
    start_date = datetime.strptime(config.week_one_start_date, '%Y-%m-%d')
    weeks_ellapsed = (now - start_date).days // 7
    return min(max(weeks_ellapsed, 1), 18)


def get_commence_time_from() -> datetime:
    """
    Returns ISO 8601 string for previous Tuesday at 05:00:00 UTC.
    This sets the start of the NFL "week" window.

    Returns:
        ISO 8601 timestamp string
    """
    now = datetime.now(timezone.utc)
    # Monday=0, Tuesday=1, ... Sunday=6. We want most recent Tuesday.
    days_since_tue = (now.weekday() - 1) % 7
    last_tue = now - timedelta(days=days_since_tue)
    last_tue_5am = datetime.combine(last_tue.date(), time(5, 0, 0, tzinfo=timezone.utc))
    return last_tue_5am


def get_commence_time_to() -> datetime:
    """
    Returns ISO 8601 string for next Tuesday at 04:59:00 UTC.
    This ends the NFL "week" window (one minute before the next 05:00 UTC).

    Returns:
        ISO 8601 timestamp string
    """
    now = datetime.now(timezone.utc)
    days_since_tue = (now.weekday() - 1) % 7
    last_tue = now - timedelta(days=days_since_tue)
    last_tue_5am = datetime.combine(last_tue.date(), time(5, 0, 0, tzinfo=timezone.utc))
    next_tue_459am = last_tue_5am + timedelta(days=7, minutes=-1)
    return next_tue_459am