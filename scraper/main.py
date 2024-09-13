import sys
import os
from typing import List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
from functools import reduce
from time import sleep


class Row:
    name = ""
    results = []

    def __init__(self):
        self.name = ""
        self.results = []

    def __str__(self):
        out = "Row: { name: " + self.name + \
            ", results: [ " + self.csv() + " ] }"
        return out

    def csv(self):
        cols = [self.name] + [self.results.count]
        csv = ",".join(cols)
        return csv


def login(driver, email: str, password: str, max_time) -> int:
    url = 'https://www.cbssports.com/login?show_opts=1&xurl=https%3A%2F%2Fpicks.cbssports.com%2Ffootball%2Flobby'
    driver.get(url)

    if email == None or len(email) == 0:
        print("Email not found. Make sure .env file is configured correctly.")
        return 1

    if password == None or len(password) == 0:
        print("Password not found. Make sure .env file is configured correctly.")
        return 1

    try:
        userid_el = WebDriverWait(driver, max_time).until(
            EC.presence_of_element_located((By.ID, 'name')))
        userid_el.send_keys(email)

        
        password_el = WebDriverWait(driver, max_time).until(
            EC.presence_of_element_located((By.ID, 'password')))
        password_el.send_keys(password)

        
        button_el = WebDriverWait(driver, max_time).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Continue')]")))

        for i in range(5):
            print('Logging in in ' + str(5 - i) + ' seconds...')
            sleep(1)
        button_el.click()
        return 0
    except TimeoutException:
        print
        "It took too much time to load specified elements."
        return 1

def scrape_week_standings_new(driver, max_wait_time, current_week, target_week) -> List[Row]:
    url = "https://picks.cbssports.com/football/pickem/pools/kbxw63b2geytimrqgmyts%3D%3D%3D/standings/weekly"
    driver.get(url)
    
    # Search for div with text "Week X" and click on it to open menu
    week_div = WebDriverWait(driver, max_wait_time).until(
        EC.presence_of_element_located((By.XPATH, f"//div[contains(text(), 'Week {current_week}')]")))
    week_div.click()

    # Search for li with text "Week Y" and click on it to navigate to the target week
    target_week_li = WebDriverWait(driver, max_wait_time).until(
        EC.presence_of_element_located((By.XPATH, f"//li[contains(text(), 'Week {target_week}')]")))
    target_week_li.click()

    # Wait for 30 seconds before exiting
    WebDriverWait(driver, 30)


def scrape_week_standings(driver, max_wait_time, week) -> List[Row]:
    table_data = []

    url = "https://3gsfb.football.cbssports.com/office-pool/standings/live/" + \
        str(week)
    driver.get(url)

    if week == 17:
        mnf_fix = get_bills_mnf_fix_script()
        driver.execute_script(mnf_fix)

    try:
        table: WebElement = WebDriverWait(driver, max_wait_time).until(
            EC.presence_of_element_located((By.ID, 'nflplayerRows')))
    except:
        print("Unable to get week " + str(week) + " data")
        return table_data

    table_rows = table.find_elements(By.XPATH, "./child::*")
    for tr in table_rows:
        row_data = Row()
        is_valid = False
        cells = tr.find_elements(By.XPATH, "./child::*")
        for td in cells:
            cell_class = td.get_attribute("class")

            if cell_class == "left":
                row_data.name = td.text
                is_valid = True
            elif cell_class == "incorrect":
                row_data.results.append("lose")
                is_valid = True
            elif cell_class == "correct":
                row_data.results.append("win")
                is_valid = True

        if is_valid:
            table_data.append(row_data)

    return table_data


# output_dir = "/tmp/3gs.scraper/out/"
output_dir = "out/"


def get_bills_mnf_fix_script():
    f = open("scraper/cbs-script.js", "r")
    buffer = f.read()
    return buffer


def write_to_output_dir(filename: str, buffer: str):
    out_filename = output_dir + filename
    f = open(out_filename, "w")
    f.write(buffer)
    f.close()


def read_from_output_dir(filename: str):
    out_filename = output_dir + filename
    f = open(out_filename, "r")
    buffer = f.read()
    f.close()
    return buffer


def parse_wins_file(buf: str):
    wins_by_user = {}
    rows = buf.split("\n")
    for row in rows:
        cols = row.split(",")
        name = cols.pop(0)
        wins_by_user[name] = cols

    return wins_by_user


def get_min_week(last_cached_week_num: int, default: int, override: int = None):
    if override != None:
        return override

    if last_cached_week_num != None:
        return last_cached_week_num + 1

    return default


def get_max_week(start_date, curr_date, default: int, override: int = None):
    if override != None:
        return override

    # logic

    return default


def main() -> int:
    load_dotenv()
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")

    # enable_caching = True
    # enable_headless = False
    # dry_run = False

    # maybe_last_cached_week_num = None
    # maybe_cached_data = {}

    # if enable_caching:
    #     wins_file_buf = ""

    #     try:
    #         wins_file_buf = read_from_output_dir("wins.csv")
    #     except:
    #         print("Cached wins file not found.")

    #     maybe_cached_data = parse_wins_file(wins_file_buf)
    #     cached_values = list(maybe_cached_data.values())
    #     if len(cached_values) > 0:
    #         maybe_last_cached_week_num = len(cached_values[0])

    # min_week = get_min_week(maybe_last_cached_week_num, 1)
    # max_week = get_max_week(None, None, 19)

    max_wait_time = 10
    chrome_options = Options()

    # if enable_headless:
    #     chrome_options.add_argument("--headless")

    driver = webdriver.Chrome(options=chrome_options)

    login(driver, email, password, max_wait_time)
    scrape_week_standings_new(driver, max_wait_time, 2, 1)

    # wins_dictionary = maybe_cached_data
    # for week in range(min_week, max_week):
    #     print("Scraping " + str(week) + "...")

    #     if dry_run:
    #         continue

    #     week_standings = scrape_week_standings(driver, max_wait_time, week)
    #     if len(week_standings) == 0:
    #         print("Could not find any table data")
    #         break

    #     total_results = reduce(
    #         lambda a, b: a + len(b.results), week_standings, 0)
    #     if total_results == 0:
    #         print("No results found for week " + str(week))
    #         break

    #     for row in week_standings:
    #         if row.name not in wins_dictionary:
    #             wins_dictionary[row.name] = []

    #         wins_dictionary[row.name].append(
    #             len(list(filter(lambda res: res == 'win', row.results))))

    # csv = ""
    # for key in wins_dictionary:
    #     wins = wins_dictionary[key]
    #     cols = [key] + list(map(lambda w: str(w), wins))
    #     delimeted_row = ",".join(cols)
    #     csv += delimeted_row + "\n"

    # if not dry_run:
    #     write_to_output_dir("wins.csv", csv)

    return 0


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    sys.exit(main())
