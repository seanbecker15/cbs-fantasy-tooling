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
        cols = [self.name] + self.results
        csv = ",".join(cols)
        return csv


def login(driver, max_time) -> int:
    url = 'https://3gsfb.football.cbssports.com/opm'
    driver.get(url)

    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")

    if email == "":
        print("Email not found. Make sure .env file is configured correctly.")
        return 1

    if password == "":
        print("Password not found. Make sure .env file is configured correctly.")
        return 1

    try:
        userid_el = WebDriverWait(driver, max_time).until(
            EC.presence_of_element_located((By.ID, 'userid')))
        password_el = WebDriverWait(driver, max_time).until(
            EC.presence_of_element_located((By.ID, 'password')))
        form_el = WebDriverWait(driver, max_time).until(
            EC.presence_of_element_located((By.ID, 'login_form')))

        userid_el.send_keys(email)
        password_el.send_keys(password)
        form_el.submit()
        return 0
    except TimeoutException:
        print
        "It took too much time to load specified elements."
        return 1


def get_data(driver, max_time, week) -> List[Row]:
    table_data = []

    url = "https://3gsfb.football.cbssports.com/office-pool/standings/live/" + \
        str(week)
    driver.get(url)
    table: WebElement = WebDriverWait(driver, max_time).until(
        EC.presence_of_element_located((By.ID, 'nflplayerRows')))
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
        else:
            print(tr.text)

    return table_data


def get_csv(data):
    csv = ""
    for r in data:
        csv += r.csv() + "\n"
    return csv


def write_file(buffer, week):
    filename = "out/" + "week" + str(week) + ".csv"
    f = open(filename, "w")
    f.write(buffer)
    f.close()


def get_week():
    return 14


def main() -> int:
    load_dotenv()

    week = 16
    max_timeout = 10

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)

    login_res = login(driver, max_timeout)
    if login_res != 0:
        return login_res

    data = get_data(driver, max_timeout, week)
    if len(data) == 0:
        print("Could not find any table data")
        return 1

    output = get_csv(data)
    write_file(output, week)

    return 0


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    sys.exit(main())
