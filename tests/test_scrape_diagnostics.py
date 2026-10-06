"""On navigation failure the scraper records where the browser actually was.

"Could not find week dropdown" told us nothing: a failed login, a bot
challenge and a slow render all look identical. Capture URL, title, a page
excerpt and a screenshot so the next unattended failure diagnoses itself.
"""

from cbs_fantasy_tooling.ingest.cbs_sports import scrape


class FakeDriver:
    current_url = "https://www.cbssports.com/login?x=1"
    title = "Sign In - CBS Sports"

    def __init__(self, fail_shot=False):
        self.fail_shot = fail_shot
        self.shots = []

    def find_element(self, by, value):
        class El:
            text = "Sign in to your CBS Sports account\nEmail\nPassword"

        return El()

    def save_screenshot(self, path):
        if self.fail_shot:
            raise RuntimeError("no display")
        self.shots.append(path)
        return True


def test_capture_records_url_title_excerpt_and_screenshot(tmp_path):
    d = FakeDriver()
    info = scrape.capture_page_state(d, tmp_path, label="week4-attempt1")
    assert info["url"] == d.current_url
    assert info["title"] == d.title
    assert "Sign in" in info["excerpt"]
    assert d.shots and d.shots[0].startswith(str(tmp_path))
    assert "week4-attempt1" in d.shots[0]


def test_capture_survives_screenshot_failure(tmp_path):
    info = scrape.capture_page_state(FakeDriver(fail_shot=True), tmp_path, label="x")
    assert info["url"] and info["screenshot"] is None


def test_capture_never_raises_on_dead_driver(tmp_path):
    class Dead:
        def __getattr__(self, name):
            raise RuntimeError("session gone")

    info = scrape.capture_page_state(Dead(), tmp_path, label="x")
    assert info["url"] is None and info["screenshot"] is None


def test_summary_mentions_login_when_stuck_on_login_page():
    s = scrape.describe_page_state(
        {
            "url": "https://www.cbssports.com/login?a=1",
            "title": "Sign In",
            "excerpt": "",
            "screenshot": None,
        }
    )
    assert "login" in s.lower()


def test_summary_mentions_standings_when_on_standings():
    s = scrape.describe_page_state(
        {
            "url": "https://picks.cbssports.com/football/pickem/pools/abc/standings/weekly",
            "title": "Weekly Standings",
            "excerpt": "",
            "screenshot": "/tmp/x.png",
        }
    )
    assert "standings" in s.lower() and "/tmp/x.png" in s
