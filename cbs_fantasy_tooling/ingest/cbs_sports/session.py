"""Reuse the user's signed-in Chrome session for scraping.

CBS added reCAPTCHA to its login form, which blocks a scripted login. The
user's own Chrome profile already holds a valid CBS session, so a copy of
it lets the scraper land on the pool as the user with no login at all.

Only the session-bearing files are staged. The full profile is gigabytes
of caches, service workers and extensions, and Chrome holds a lock on the
live profile while it runs, so it is never used directly.
"""

import os
import shutil
from pathlib import Path

from selenium.webdriver.chrome.options import Options

# What a session actually lives in. Everything else is cache or UI state.
SESSION_FILES = [
    "Cookies",
    "Cookies-journal",
    "Login Data",
    "Login Data-journal",
    "Preferences",
    "Secure Preferences",
    "Web Data",
    "Web Data-journal",
    "Network/Cookies",
    "Network/Cookies-journal",
]
REQUIRED_ANY = ("Cookies", "Network/Cookies")  # at least one must exist
TOP_LEVEL_FILES = ["Local State"]


class ProfileError(RuntimeError):
    """The Chrome profile could not be staged for reuse."""


def default_profile_root() -> Path:
    """Chrome's user-data directory on macOS."""
    return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"


def stage_profile(root: Path, profile: str, dest: Path) -> Path:
    """Copy the session-bearing parts of `root/profile` into `dest`.

    Re-stages from scratch each time so a previous run cannot leave stale
    state behind. Returns `dest`.
    """
    root, dest = Path(root), Path(dest)
    src_profile = root / profile
    if not src_profile.is_dir():
        raise ProfileError(f"Chrome profile not found: {src_profile}")
    if not any((src_profile / f).exists() for f in REQUIRED_ANY):
        raise ProfileError(f"No Cookies database in {src_profile}; is this the right profile?")

    if dest.exists():
        shutil.rmtree(dest)
    (dest / profile).mkdir(parents=True)

    for name in TOP_LEVEL_FILES:
        if (root / name).exists():
            shutil.copy2(root / name, dest / name)
    for rel in SESSION_FILES:
        src = src_profile / rel
        if src.exists():
            out = dest / profile / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out)
    return dest


def chrome_options_for(user_data_dir: Path, profile: str) -> Options:
    """Chrome options that launch against the staged profile."""
    opts = Options()
    opts.add_argument(f"--user-data-dir={user_data_dir}")
    opts.add_argument(f"--profile-directory={profile}")
    opts.add_argument("--window-size=1600,1200")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    return opts


def is_logged_in(driver) -> bool:
    """True when the browser landed on the pool rather than the login form.

    A `/join` landing means the session is signed in but CBS did not attach
    the pool entry - usually a non-canonical pool slug - so it counts as
    not-ready rather than signed in.
    """
    url = driver.current_url or ""
    return "/login" not in url and "/join" not in url and "picks.cbssports.com" in url


def canonical_slug(slug: str) -> str:
    """CBS pool slugs are base32 and the site canonicalises to the padded form.

    An unpadded slug 307-redirects, and on that redirect the pool entry
    context can be dropped (landing on /join). Pad to a multiple of 8 so the
    first request is already canonical.
    """
    s = (slug or "").rstrip("=")
    return s + "=" * (-len(s) % 8)


def staging_dir() -> Path:
    return Path(os.getenv("SCRAPE_PROFILE_DIR", "/tmp/cbs-sports-scraper/chrome-profile"))
