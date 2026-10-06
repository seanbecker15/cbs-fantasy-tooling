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


def test_popup_defaults_to_shown_week_unless_it_is_unscored():
    """Respect the page's dropdown, but on Tuesday the page opens on the
    in-progress week with everyone at 0 - default to the finished week before."""
    js = (EXT / "popup.js").read_text()
    assert "setTarget(shownHasResults ? shownWeek || 1 : Math.max(1, (shownWeek || 2) - 1))" in js
    scrape_js = (EXT / "scrape.js").read_text()
    assert "hasResults" in scrape_js and "async function readPage" in scrape_js


def test_scrape_waits_for_table_rows_even_without_a_week_switch():
    js = (EXT / "scrape.js").read_text()
    body = js.split("if (targetWeek) await selectWeek(targetWeek);")[1]
    assert body.lstrip().startswith("await settle();")


def test_working_message_is_based_on_the_page_at_scrape_time():
    """ "Switching…" must only show when the page is actually on a different week."""
    html = (EXT / "popup.html").read_text()
    assert 'id="workingText">Reading the standings…' in html
    js = (EXT / "popup.js").read_text()
    scrape_fn = js.split("async function scrape()")[1].split("async function init")[0]
    assert "await inject(readPage)" in scrape_fn
    assert "page.shown !== target" in scrape_fn


def test_page_calls_cannot_hang_the_popup():
    js = (EXT / "popup.js").read_text()
    assert "Promise.race" in js and 'new Error("timeout")' in js
    assert 'id="errorDetail"' in (EXT / "popup.html").read_text()


def test_hidden_attribute_wins_over_panel_display():
    """Every view section is toggled with the `hidden` attribute; a .panel
    display rule must not override it or all panels show at once."""
    css = (EXT / "popup.css").read_text()
    assert "[hidden] { display: none !important; }" in css
    html = (EXT / "popup.html").read_text()
    for view in ("offsite", "ready", "working", "results", "error"):
        assert f'id="{view}" hidden' in html, view


def test_popup_cannot_scroll_horizontally():
    """A three-way bonus tie once widened the whole popup."""
    css = (EXT / "popup.css").read_text()
    assert "overflow-x: hidden" in css.split(".main {")[1].split("}")[0]
    bonus = css.split(".bonus__card {")[1].split("}")[0]
    assert "min-width: 0" in bonus
    who = css.split(".bonus__who {")[1].split("}")[0]
    assert "nowrap" not in who and "overflow-wrap: anywhere" in who
    assert "minmax(0, 1fr)" in css
