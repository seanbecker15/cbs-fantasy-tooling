from datetime import datetime

def get_weeks_since_start(start_date: str) -> int:
    """Calculate weeks since start date."""
    now = datetime.now()
    weeks_elapsed = (now - datetime.strptime(start_date, '%Y-%m-%d')).days // 7
    return min(max(weeks_elapsed, 1), 18)