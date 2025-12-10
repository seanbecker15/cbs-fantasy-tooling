"""Time window helpers for NFL week calculations."""

from datetime import datetime, timedelta, time, timezone


def get_current_nfl_week() -> int:
    """
    Calculate the current NFL week based on season start date (September 2, 2025).
    Week 1 starts on September 2, 2025 (Tuesday).

    Returns:
        Current NFL week number (1-18)
    """
    season_start = datetime(2025, 9, 2, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    days_since_start = (now - season_start).days
    week = max(1, min(18, (days_since_start // 7) + 1))
    return week


def get_commence_time_from() -> str:
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
    return last_tue_5am.isoformat().replace("+00:00", "Z")


def get_commence_time_to() -> str:
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
    return next_tue_459am.isoformat().replace("+00:00", "Z")
