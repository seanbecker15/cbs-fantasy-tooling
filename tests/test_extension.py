"""The browser extension must stay in lockstep with the Python scraper, and
must stay dependency-free: no npm, no bundler, no CDN scripts, no web fonts."""

import json
import re
from pathlib import Path

from cbs_fantasy_tooling.ingest.cbs_sports import scrape as py

EXT = Path(__file__).resolve().parent.parent / "extension"


def test_svg_constants_match_python():
    js = (EXT / "scrape.js").read_text()
    check = re.search(r'const ICON_CHECK = "([^"]+)"', js).group(1)
    x = re.search(r'const ICON_X = "([^"]+)"', js).group(1)
    assert check == py.icon_check_svg_path
    assert x == py.icon_x_svg_path


def test_manifest_is_v3_and_scoped_to_cbs():
    m = json.loads((EXT / "manifest.json").read_text())
    assert m["manifest_version"] == 3
    assert m["host_permissions"] == ["https://picks.cbssports.com/*"]
    assert set(m["permissions"]) <= {"activeTab", "scripting", "downloads", "storage"}
    for icon in m["icons"].values():
        assert (EXT / icon).exists()


def test_no_external_dependencies():
    """Everything the extension needs ships in the folder."""
    assert not (EXT / "package.json").exists()
    assert not (EXT / "node_modules").exists()
    for name in ("popup.html", "popup.css", "popup.js", "scrape.js"):
        text = (EXT / name).read_text()
        assert "http://" not in text.replace("https://picks.cbssports.com", "")
        assert "https://" not in text.replace("https://picks.cbssports.com", "").replace(
            "https:\\/\\/picks", ""
        )
        assert "@import" not in text and "fonts.googleapis" not in text
    html = (EXT / "popup.html").read_text()
    for src in re.findall(r'<script src="([^"]+)"', html):
        assert (EXT / src).exists(), src
    for href in re.findall(r'<link rel="stylesheet" href="([^"]+)"', html):
        assert (EXT / href).exists(), href


def test_export_filename_matches_pipeline():
    js = (EXT / "popup.js").read_text()
    assert "week_${lastData.week}_pickem_results.json" in js
    assert "week_${lastData.week}_pickem_results.csv" in js


def test_popup_defaults_to_the_week_shown_on_the_page():
    """The dropdown on the page is already the user's choice; don't second-guess it."""
    js = (EXT / "popup.js").read_text()
    assert "setTarget(shownWeek || 1)" in js
    assert "shownWeek - 1" not in js.split("function setTarget")[0].split("async function init")[-1]


def test_working_message_is_based_on_the_page_at_scrape_time():
    """ "Switching…" must only show when the page is actually on a different week."""
    html = (EXT / "popup.html").read_text()
    assert 'id="workingText">Reading the standings…' in html
    js = (EXT / "popup.js").read_text()
    scrape_fn = js.split("async function scrape()")[1].split("async function init")[0]
    assert "await inject(readPage)" in scrape_fn
    assert "page.shown !== target" in scrape_fn
