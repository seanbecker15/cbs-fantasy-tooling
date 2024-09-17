from datetime import datetime
from dotenv import load_dotenv
from scrape import run_scraper
from notify import send_success_notification, send_failure_notification

# Tuesday, September 3, 2024
week_one_start_date = '2024-09-03'

def __get_weeks_since_start():
    now = datetime.now()
    return (now - datetime.strptime(week_one_start_date, '%Y-%m-%d')).days // 7


def main():
    load_dotenv()

    curr_week_no = __get_weeks_since_start() + 1
    print(f"Current week number: {curr_week_no}")
    print(f"Running scraper for week {curr_week_no - 1}...")
    results = run_scraper(curr_week_no, curr_week_no - 1)

    if not results or len(results) == 0:
        send_failure_notification()
    else:
        send_success_notification(results)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
