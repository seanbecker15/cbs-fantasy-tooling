from datetime import datetime
from dotenv import load_dotenv
from scrape import run_scraper
from notify import send_success_notification, send_failure_notification

override_target_week = None
override_curr_week = None

# Tuesday, September 2, 2025
week_one_start_date = '2025-09-02'


def __get_weeks_since_start():
    now = datetime.now()
    return (now - datetime.strptime(week_one_start_date, '%Y-%m-%d')).days // 7


def main():
    load_dotenv()

    prev_week_no = override_target_week if override_target_week else __get_weeks_since_start()
    curr_week_no = override_curr_week if override_curr_week else __get_weeks_since_start() + 1

    print(f"Current week number: {curr_week_no}")
    print(f"Running scraper for week {prev_week_no}...")
    
    try:
        results = run_scraper(curr_week_no, prev_week_no)
        send_success_notification(results)
    except Exception as e:
        print(f"Error occurred: {e}")
        send_failure_notification()
        return

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
