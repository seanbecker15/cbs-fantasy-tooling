"""
Realtime scraper that keeps browser open and polls for updates.

This module provides a realtime polling mode that:
1. Keeps the Chrome window open
2. Polls for updates every X seconds (default: 10)
3. Detects changes and updates the database
4. Continues until user presses a key to exit
"""

import os
import sys
import select
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from time import sleep
from typing import Callable, Optional
from datetime import datetime
from storage import Row
from database import compare_results


def wait_for_exit_signal(timeout_seconds: int = 10) -> bool:
    """
    Wait for user input with a timeout. Non-blocking check for exit signal.

    Args:
        timeout_seconds: How long to wait before returning

    Returns:
        True if user pressed a key, False if timeout
    """
    # Check if stdin has data available (non-blocking)
    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
        # Consume any input
        sys.stdin.readline()
        return True
    return False


def login_to_cbs(driver, max_wait_time: int, email: str, password: str) -> bool:
    """
    Navigate to CBS login page and authenticate.

    Args:
        driver: Selenium WebDriver instance
        max_wait_time: Maximum seconds to wait for page elements
        email: CBS Sports login email
        password: CBS Sports login password

    Returns:
        True if login successful, False otherwise
    """
    login_page_url = 'https://www.cbssports.com/login?masterProductId=41010&product_abbrev=opm&show_opts=1&xurl=https%3A%2F%2Fpicks.cbssports.com%2Ffootball%2Fpickem%2Fpools%2Fizxw65dcmfwgyudjmnvwk3knmfxgcz3fojig633mhiytgobtgq2deoi%253D%2Fstandings%2Fweekly%3Fdevice%3Ddesktop%26device%3Ddesktop'

    driver.get(login_page_url)

    if not email or len(email) == 0:
        print("Email not found. Make sure .env file is configured correctly.")
        return False
    if not password or len(password) == 0:
        print("Password not found. Make sure .env file is configured correctly.")
        return False

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

        print("✓ Logged in successfully")
        print("Waiting for page to load completely...")
        sleep(10)  # Give extra time for redirect and page load

        return True

    except TimeoutException:
        print("Timeout during login process")
        return False


def navigate_to_week(driver, max_wait_time: int, curr_week_number: int, target_week_number: int) -> bool:
    """
    Navigate to a specific week's standings.

    Args:
        driver: Selenium WebDriver instance
        max_wait_time: Maximum seconds to wait
        curr_week_number: Current NFL week number
        target_week_number: Week to navigate to

    Returns:
        True if navigation successful, False otherwise
    """
    try:
        # Search for div with text "Week X" and click on it to open menu
        print(f"Looking for dropdown with text 'Week {curr_week_number}'")
        week_div = WebDriverWait(driver, max_wait_time).until(
            EC.presence_of_element_located((By.XPATH, f"//div[contains(text(), 'Week {curr_week_number}')]")))
        week_div.click()

        # Search for li with text "Week Y" and click on it to navigate to the target week
        print(f"Selecting 'Week {target_week_number}'")
        target_week_li = WebDriverWait(driver, max_wait_time).until(
            EC.presence_of_element_located((By.XPATH, f"//li[contains(text(), 'Week {target_week_number}')]")))
        target_week_li.click()

        sleep(2)
        return True

    except TimeoutException:
        print(f"Could not navigate to week {target_week_number}")
        return False


def scrape_current_standings(driver, max_wait_time: int) -> list[Row]:
    """
    Scrape the current standings from the page.

    Args:
        driver: Selenium WebDriver instance
        max_wait_time: Maximum seconds to wait

    Returns:
        List of Row objects with scraped data
    """
    # Import here to avoid circular dependency issues
    from scrape import __scrape_week_standings
    return __scrape_week_standings(driver, max_wait_time, False)


def run_realtime_scraper(
    curr_week_number: int,
    target_week_number: int,
    poll_interval: int = 30,
    on_update: Optional[Callable[[list[Row]], None]] = None
) -> None:
    """
    Run the realtime scraper with polling.

    This keeps the browser open and polls for updates every poll_interval seconds.
    CBS does not update the page in real-time, so we refresh between each poll.
    Press Enter at any time to exit.

    Args:
        curr_week_number: Current NFL week number
        target_week_number: Week to scrape data for
        poll_interval: Seconds between polls (default: 30)
        on_update: Optional callback function called with results on each update
    """
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")

    max_wait_time = 30
    chrome_options = Options()
    # Removed headless mode to keep window visible

    driver = webdriver.Chrome(options=chrome_options)

    try:
        # Login
        print("=" * 60)
        print("REALTIME SCRAPER MODE")
        print("=" * 60)
        print(f"Target week: {target_week_number}")
        print(f"Poll interval: {poll_interval} seconds")
        print(f"Press Enter at any time to exit")
        print("=" * 60)

        if not login_to_cbs(driver, max_wait_time, email, password):
            print("Login failed, exiting...")
            return

        # Wait for user to bypass captcha if needed
        print("\nIf there's a captcha, please solve it now.")
        print("Press Enter when ready to continue...")
        input()

        # Sometimes on first load the page doesn't finish loading
        driver.refresh()
        sleep(3)

        # Navigate to target week
        i = curr_week_number
        succeeded = False

        while i >= target_week_number and not succeeded:
            try:
                print(f"Looking for dropdown with text 'Week {i}'")
                if navigate_to_week(driver, max_wait_time, i, target_week_number):
                    succeeded = True
                    break
            except TimeoutException:
                print(f"Could not find dropdown with text 'Week {i}'.")
                i -= 1

        if not succeeded:
            raise Exception(
                f"Could not find week dropdown. Searched {curr_week_number}..{target_week_number}.")

        print(f"\n✓ Successfully navigated to Week {target_week_number}")
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
                current_results = scrape_current_standings(driver, max_wait_time)

                if not current_results or len(current_results) == 0:
                    print("⚠ No results found in this poll")
                else:
                    print(f"✓ Scraped {len(current_results)} player results")

                    # Check if data changed using deep comparison
                    comparison = compare_results(previous_results, current_results)

                    if previous_results is None:
                        print("  First poll - saving baseline data")
                        if on_update:
                            on_update(current_results)
                    elif comparison['changed']:
                        print(f"  ⚡ CHANGE DETECTED - {comparison['summary']}")
                        for change in comparison['changes'][:5]:  # Show first 5 changes
                            print(f"    • {change}")
                        if len(comparison['changes']) > 5:
                            print(f"    ... and {len(comparison['changes']) - 5} more changes")

                        if on_update:
                            on_update(current_results)
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
                if wait_for_exit_signal(1):
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
