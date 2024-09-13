import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from time import sleep

login_page_url = 'https://www.cbssports.com/login?masterProductId=40482&product_abbrev=opm&show_opts=1&xurl=https%3A%2F%2Fpicks.cbssports.com%2Ffootball%2Fpickem%2Fpools%2Fkbxw63b2geytimrqgmyts%253D%253D%253D%2Fstandings%2Fweekly'


def __navigate_login(driver, max_wait_time, email: str, password: str) -> int:
    driver.get(login_page_url)
    if email == None or len(email) == 0:
        print("Email not found. Make sure .env file is configured correctly.")
        return 1
    if password == None or len(password) == 0:
        print("Password not found. Make sure .env file is configured correctly.")
        return 1
    try:
        userid_el = WebDriverWait(driver, max_wait_time).until(
            EC.presence_of_element_located((By.NAME, 'email')))
        userid_el.send_keys(email)
        password_el = WebDriverWait(driver, max_wait_time).until(
            EC.presence_of_element_located((By.NAME, 'password')))
        password_el.send_keys(password)
        button_el = WebDriverWait(driver, max_wait_time).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Continue')]")))
        print('Logging in in 5 seconds...')
        sleep(5)
        button_el.click()
    except TimeoutException:
        print("It took too much time to load specified elements.")


def __navigate_week_standings(driver, max_wait_time, curr_week_number, target_week_number) -> any:
    # Search for div with text "Week X" and click on it to open menu
    week_div = WebDriverWait(driver, max_wait_time).until(
        EC.presence_of_element_located((By.XPATH, f"//div[contains(text(), 'Week {curr_week_number}')]")))
    week_div.click()
    # Search for li with text "Week Y" and click on it to navigate to the target week
    target_week_li = WebDriverWait(driver, max_wait_time).until(
        EC.presence_of_element_located((By.XPATH, f"//li[contains(text(), 'Week {target_week_number}')]")))
    target_week_li.click()


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
        cols = [self.name] + [str(x) for x in self.results]
        csv = ",".join(cols)
        return csv


def __scrape_week_standings(driver, max_wait_time) -> list[Row]:
    # Search for a table with aria-label "Weekly Standings" and get all rows
    table = WebDriverWait(driver, max_wait_time).until(
        EC.presence_of_element_located((By.XPATH, "//table[@aria-label='Weekly Standings']")))
    table_body = table.find_element(By.TAG_NAME, "tbody")
    rows = table_body.find_elements(By.TAG_NAME, "tr")

    parsed_rows = []
    # Find the number of points for each player
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        # Player name is in the first cell
        # <div class="MuiStack-root mui-style-1bnhsfk"><span class="MuiTypography-root MuiTypography-menu mui-style-d4wxq0">1st</span><span class="MuiTypography-root MuiTypography-menu MuiTypography-noWrap mui-style-dz364d">Joe Capezio</span></div>
        player_name = cells[0].find_elements(By.TAG_NAME, "span")
        if len(player_name) < 2:
            print("Skipping row with no player name. See below:")
            print(player_name)
            continue
        player_name = player_name[1].text
        # Points for the week are in the second cell
        player_points = cells[1].text
        # Points for the year are in the third cell
        # Number of wins and losses are in the remaining cells
        wins = 0
        losses = 0
        for cell in cells[3:]:
            cell_type = __get_cell_type(cell)
            if cell_type == "win":
                wins += 1
            elif cell_type == "loss":
                losses += 1

        row_obj = Row()
        row_obj.name = player_name
        row_obj.results = [player_points, wins, losses]
        parsed_rows.append(row_obj)
        print(
            f"Player: {player_name}, Points: {player_points}, Wins: {wins}, Losses: {losses}")

    return parsed_rows


icon_check_svg_path = "M12 22c5.5 0 10-4.5 10-10S17.5 2 12 2 2 6.5 2 12s4.5 10 10 10zm-1-5.2c-.4 0-.8-.2-1.1-.6l-2.2-2.6c-.2-.3-.3-.5-.3-.8 0-.6.5-1.1 1.1-1.1.3 0 .6.1.9.4l1.6 2 3.7-5.8c.3-.4.6-.6.9-.6.6 0 1.1.4 1.1 1 0 .2-.1.5-.3.7L12 16.2c-.3.3-.6.6-1 .6z"
icon_x_svg_path = "M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm4.3 14.3c-.4.4-1 .4-1.4 0L12 13.4l-2.9 2.9c-.4.4-1 .4-1.4 0-.4-.4-.4-1 0-1.4l2.9-2.9-2.9-2.9c-.4-.4-.4-1 0-1.4.4-.4 1-.4 1.4 0l2.9 2.9 2.9-2.9c.4-.4 1-.4 1.4 0 .4.4.4 1 0 1.4L13.4 12l2.9 2.9c.4.4.4 1 0 1.4z"


def __get_cell_type(cell: WebElement) -> str:
    # Check if cell has an svg indicating a win or loss
    try:
        path = cell.find_element(By.TAG_NAME, "path")
        if path:
            path_d = path.get_attribute("d")
            if path_d == icon_check_svg_path:
                return "win"
            elif path_d == icon_x_svg_path:
                return "loss"
    except:
        pass

    return "unknown"


def __print_csv(results):
    csv = "Name,Points,Wins,Losses\n"
    for row in results:
        csv += row.csv() + "\n"
    print(csv)


def __print_most_wins(results):
    max_wins = 0
    for row in results:
        if row.results[1] > max_wins:
            max_wins = row.results[1]
    players_with_max_wins = [
        row.name for row in results if row.results[1] == max_wins]
    print(f"Most wins for the week: {max_wins}")
    print(f"Players with the most wins: {', '.join(players_with_max_wins)}")


def __print_most_points(results):
    max_points = 0
    for row in results:
        curr_row_points = int(row.results[0])
        if curr_row_points > max_points:
            max_points = curr_row_points
    players_with_max_points = [
        row.name for row in results if int(row.results[0]) == max_points]
    print(f"Most points for the week: {max_points}")
    print(
        f"Players with the most points: {', '.join(players_with_max_points)}")


def run_scraper(curr_week_number: int, target_week_number: int) -> list[Row]:
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")

    max_wait_time = 10
    chrome_options = Options()

    driver = webdriver.Chrome(options=chrome_options)

    __navigate_login(driver, max_wait_time, email, password)
    sleep(5)

    __navigate_week_standings(driver, max_wait_time,
                              curr_week_number, target_week_number)
    sleep(5)

    results = __scrape_week_standings(driver, max_wait_time)
    __print_csv(results)
    __print_most_wins(results)
    __print_most_points(results)

    return results
