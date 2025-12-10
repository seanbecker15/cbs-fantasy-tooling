from dataclasses import dataclass
from datetime import datetime
import os
import sys
import select
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from time import sleep

from cbs_fantasy_tooling.models import PickemResult, PickemResults
from cbs_fantasy_tooling.publishers import Publisher
from cbs_fantasy_tooling.publishers.database import DatabasePublisher
from cbs_fantasy_tooling.storage.providers.database import compare_results

login_page_url = 'https://www.cbssports.com/login?masterProductId=41010&product_abbrev=opm&show_opts=1&xurl=https%3A%2F%2Fpicks.cbssports.com%2Ffootball%2Fpickem%2Fpools%2Fizxw65dcmfwgyudjmnvwk3knmfxgcz3fojig633mhiytgobtgq2deoi%253D%2Fstandings%2Fweekly%3Fdevice%3Ddesktop%26device%3Ddesktop'


def navigate_login(driver, max_wait_time, email: str, password: str) -> int:
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

        sleep(5)        
        button_el.click()
    except TimeoutException:
        print("It took too much time to load specified elements.")


def navigate_standings(driver, max_wait_time, curr_week, target_week) -> any:
    # Search for div with text "Week X" and click on it to open menu
    print(f"Looking for div with text 'Week {curr_week}'")
    week_div = WebDriverWait(driver, max_wait_time).until(
        EC.presence_of_element_located((By.XPATH, f"//div[contains(text(), 'Week {curr_week}')]")))
    week_div.click()

    # Search for li with text "Week Y" and click on it to navigate to the target week
    print(f"Looking for li with text 'Week {target_week}'")
    target_week_li = WebDriverWait(driver, max_wait_time).until(
        EC.presence_of_element_located((By.XPATH, f"//li[contains(text(), 'Week {target_week}')]")))
    target_week_li.click()


def scrape_standings(driver, max_wait_time, debug) -> list[PickemResult]:
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
        picks = []
        for cell in cells[3:]:
            cell_type = check_cell_type(cell)
            if cell_type == "win":
                wins += 1
            elif cell_type == "loss":
                losses += 1
            
            cell_text = extract_cell_text(cell)
            pick_details = parse_pick(cell_text)
            if pick_details:
                picks.append(pick_details)

        row_obj = PickemResult()
        row_obj.name = player_name
        row_obj.results = [player_points, wins, losses]
        row_obj.picks = picks
        parsed_rows.append(row_obj)
        if debug:
            print(
                f"Player: {player_name}, Points: {player_points}, Wins: {wins}, Losses: {losses}")

    return parsed_rows


icon_check_svg_path = "M12 22c5.5 0 10-4.5 10-10S17.5 2 12 2 2 6.5 2 12s4.5 10 10 10zm-1-5.2c-.4 0-.8-.2-1.1-.6l-2.2-2.6c-.2-.3-.3-.5-.3-.8 0-.6.5-1.1 1.1-1.1.3 0 .6.1.9.4l1.6 2 3.7-5.8c.3-.4.6-.6.9-.6.6 0 1.1.4 1.1 1 0 .2-.1.5-.3.7L12 16.2c-.3.3-.6.6-1 .6z"
icon_x_svg_path = "M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm4.3 14.3c-.4.4-1 .4-1.4 0L12 13.4l-2.9 2.9c-.4.4-1 .4-1.4 0-.4-.4-.4-1 0-1.4l2.9-2.9-2.9-2.9c-.4-.4-.4-1 0-1.4.4-.4 1-.4 1.4 0l2.9 2.9 2.9-2.9c.4-.4 1-.4 1.4 0 .4.4.4 1 0 1.4L13.4 12l2.9 2.9c.4.4.4 1 0 1.4z"


def check_cell_type(cell: WebElement) -> str:
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

def extract_cell_text(cell: WebElement) -> str:
    # Get cell text (e.g. "SEA (12)")
    try:
        spans = cell.find_elements(By.TAG_NAME, "span")
        if spans and len(spans) == 2:
            return spans[0].text + " " + spans[1].text
    except:
        pass

    return ""

def parse_pick(pick: str) -> dict:
    # Example pick: "SEA (12)"
    parts = pick.split(" ")
    if len(parts) != 2:
        return {}
    team = parts[0]
    points = parts[1].replace("(", "").replace(")", "")
    return {
        "team": team,
        "points": points
    }

def print_csv(results):
    csv = "Name,Points,Wins,Losses\n"
    for row in results:
        csv += row.csv() + "\n"
    print(csv)


def print_most_wins(results):
    max_wins = 0
    for row in results:
        if row.results[1] > max_wins:
            max_wins = row.results[1]
    players_with_max_wins = [
        row.name for row in results if row.results[1] == max_wins]
    print(f"Most wins for the week: {max_wins}")
    print(f"Players with the most wins: {', '.join(players_with_max_wins)}")


def print_most_points(results):
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


@dataclass
class PickemIngestParams:
    curr_week: int
    target_week: int
    poll_interval: int | None = None

def ingest_pickem_results(params: PickemIngestParams, publishers: list[Publisher]):
    try:
        pickem_result_items = run_scraper(params, publishers)
        pickem_results = PickemResults(pickem_result_items, params.target_week)
        publish_results(pickem_results, publishers)
    except Exception as e:
        print(f"Error occurred during scraping or publishing: {e}")

def run_scraper(params: PickemIngestParams, publishers: list[Publisher]) -> list[PickemResult]:
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")

    max_wait_time = 30
    chrome_options = Options()

    driver = webdriver.Chrome(options=chrome_options)

    navigate_login(driver, max_wait_time, email, password)
    wait_for_user_input(30)


    i = params.curr_week
    succeeded = False

    # Sometimes on first load the page doesn't finish loading
    driver.refresh()
    
    while i >= params.target_week and not succeeded:
        try:
            print(f"Looking for dropdown with text 'Week {i}'")
            navigate_standings(
                driver, max_wait_time, i, params.target_week)
            sleep(2)
            succeeded = True
            break
        except TimeoutException:
            print(
                f"Could not find dropdown with text 'Week {i}'.")
            i -= 1

    if not succeeded:
        raise Exception(
            f"Could not find week dropdown. Searched {params.curr_week}..{params.target_week}.")

    sleep(5)

    print(f"\n✓ Successfully navigated to Week {params.target_week}")
    
    poll_interval = params.poll_interval

    try:
        if not poll_interval or poll_interval <= 0:
            results = scrape_standings(driver, max_wait_time, True)
            print_csv(results)
            print_most_wins(results)
            print_most_points(results)
            if not results or len(results) == 0:
                raise Exception("No results found.")
            return results
        
        print("\nStarting realtime polling...")
        print(f"Poll interval: {poll_interval}s (refreshing page between polls)")
        print("=" * 60)

        previous_results = None
        poll_count = 0
        half_poll_interval = poll_interval // 2

        while True:
            poll_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")

            # Refresh page before scraping (CBS doesn't update in real-time)
            if poll_count > 1:  # Skip refresh on first poll
                print(f"\n[{timestamp}] Poll #{poll_count} - Refreshing page...")
                driver.refresh()
                print(f"Waiting {half_poll_interval}s for page to stabilize...")

                # Wait half the poll interval, checking for exit signal
                for i in range(half_poll_interval):
                    if wait_for_exit_signal(1):
                        print("\n✓ Exit signal received")
                        return
                    sleep(1)

            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Poll #{poll_count} - Scraping data...")

            try:
                # Scrape current data
                current_results = scrape_standings(driver, max_wait_time, False)

                if not current_results or len(current_results) == 0:
                    print("⚠ No results found in this poll")
                else:
                    print(f"✓ Scraped {len(current_results)} player results")

                    # Check if data changed using deep comparison
                    comparison = compare_results(previous_results, current_results)

                    if previous_results is None:
                        print("  First poll - saving baseline data")
                        on_update(params, publishers, current_results)
                    elif comparison['changed']:
                        print(f"  ⚡ CHANGE DETECTED - {comparison['summary']}")
                        for change in comparison['changes'][:5]:  # Show first 5 changes
                            print(f"    • {change}")
                        if len(comparison['changes']) > 5:
                            print(f"    ... and {len(comparison['changes']) - 5} more changes")
                        on_update(params, publishers, current_results)
                    else:
                        print("  No changes detected")

                    previous_results = current_results

            except Exception as e:
                print(f"⚠ Error during scraping: {e}")
                import traceback
                traceback.print_exc()

            # Wait after scraping before next poll (half the poll interval)
            print(f"\nWaiting {half_poll_interval}s until next refresh (Press Enter to exit)...")

            for i in range(half_poll_interval):
                if wait_for_exit_signal():
                    print("\n✓ Exit signal received")
                    return
                sleep(1)

    except KeyboardInterrupt:
        print("\n✓ Interrupted by user")
    except Exception as e:
        print(f"\n⚠ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nClosing browser...")
        driver.quit()
        print("✓ Browser closed")


def on_update(params: PickemIngestParams, publishers: list[Publisher], results: list[PickemResult]):
    """Called when new data is scraped."""
    print(f"on_update called with {len(results)} results")
    try:
        # Convert to PickemResults
        results_data = PickemResults(results, params.target_week)

        # Find database publisher
        db_publisher = next((p for p in publishers if isinstance(p, DatabasePublisher)), None)
        if not db_publisher:
            print("No database publisher configured, skipping publish step")
            return
        
        # Publish to database
        print("\nPublishing to database...")
        success = db_publisher.publish_pickem_results(results_data) if db_publisher else False

        if success:
            # Print summary
            wins_data = results_data.get_max_wins_data()
            points_data = results_data.get_max_points_data()

            print(f"\n{'=' * 60}")
            print(f"Week {params.target_week} Summary (as of {results_data.timestamp.strftime('%H:%M:%S')})")
            print(f"{'=' * 60}")
            print(f"Most wins: {wins_data['max_wins']} - {wins_data['players']}")
            print(f"Most points: {points_data['max_points']} - {points_data['players']}")
            print(f"{'=' * 60}\n")
        else:
            print("⚠ Failed to publish to database")

    except Exception as e:
        print(f"⚠ Error in update callback: {e}")
        import traceback
        traceback.print_exc()


def publish_results(results: PickemResults, publishers: list[Publisher]):
    """Publish results using all configured publishers"""
    success_count = 0
    errors = []
    
    for name, publisher in publishers:
        print(f"\nPublishing via {name}...")
        try:
            if publisher.publish(results):
                print(f"✓ {name} publisher succeeded")
                success_count += 1
            else:
                print(f"✗ {name} publisher failed")
                errors.append(name)
        except Exception as e:
            print(f"✗ {name} publisher error: {e}")
            errors.append(name)
    
    print(f"\nPublication summary: {success_count}/{len(publishers)} publishers succeeded")
    if errors:
        print(f"Failed publishers: {', '.join(errors)}")


def wait_for_exit_signal() -> bool:
    """
    Wait for user input with a timeout. Non-blocking check for exit signal.

    Returns:
        True if user pressed a key, False if timeout
    """
    # Check if stdin has data available (non-blocking)
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        # Consume any input
        sys.stdin.readline()
        return True
    return False


def wait_for_user_input(timeout_seconds=30):
    """Wait for user input with a timeout. Returns True if user pressed Enter, False if timeout."""
    print(f"Press Enter to continue (will auto-continue in {timeout_seconds} seconds)...")
    
    # Use select to check if input is available
    if sys.stdin in select.select([sys.stdin], [], [], timeout_seconds)[0]:
        input()  # Consume the input
        return True
    else:
        print(f"\nTimeout reached after {timeout_seconds} seconds, continuing automatically...")
        return False