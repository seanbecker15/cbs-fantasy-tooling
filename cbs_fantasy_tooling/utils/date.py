from datetime import datetime, time, timedelta, timezone

from cbs_fantasy_tooling import config

MAX_WEEK = 18


def calc_weeks_elapsed() -> int:
    """
    Whole weeks completed since Week 1 kicked off.

    Returns 0 while Week 1 is still in progress.
    """
    now = datetime.now()
    start_date = datetime.strptime(config.week_one_start_date, "%Y-%m-%d")
    return max((now - start_date).days // 7, 0)


def get_current_week() -> int:
    """
    The NFL week currently in progress (1-18).

    This is the week CBS shows in its standings dropdown and the week the
    current odds slate belongs to.
    """
    return min(calc_weeks_elapsed() + 1, MAX_WEEK)


def get_last_completed_week() -> int:
    """
    The most recent week whose games have finished (1-18).

    This is the week to scrape standings for. Clamped to 1 so that early in
    Week 1 (before anything has completed) callers still get a usable week.
    """
    return min(max(calc_weeks_elapsed(), 1), MAX_WEEK)


def calc_weeks_since_start() -> int:
    """Deprecated alias for :func:`get_last_completed_week`."""
    return get_last_completed_week()


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
