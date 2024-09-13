from datetime import datetime
from dotenv import load_dotenv
from scrape import run_scraper

# Thursday, September 5, 2024
week_one_start_date = '2024-09-05'


def __get_weeks_since_start():
    now = datetime.now()
    return (now - datetime.strptime(week_one_start_date, '%Y-%m-%d')).days // 7


def main() -> int:
    curr_week_no = __get_weeks_since_start() + 1
    print(f"Current week number: {curr_week_no}")
    load_dotenv()
    run_scraper(curr_week_no, curr_week_no - 1)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
