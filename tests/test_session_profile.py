"""The scraper reuses the user's signed-in Chrome session instead of logging in.

CBS added reCAPTCHA to its login form and the scripted login is blocked. A
copy of the user's Chrome profile already carries a valid session, so the
scraper lands on the standings page as the user and never sees the form.

Only the session-bearing files are copied: the full profile is ~2GB of
caches and service workers, and Chrome locks the live one while it runs.
"""

import os

from cbs_fantasy_tooling.ingest.cbs_sports import session


def _fake_profile(root, files):
    prof = root / "Chrome"
    for rel in files:
        p = prof / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x" * 10)
    return prof


def test_copies_session_files_and_skips_caches(tmp_path):
    src = _fake_profile(
        tmp_path,
        [
            "Local State",
            "Default/Cookies",
            "Default/Preferences",
            "Default/Login Data",
            "Default/Cache/data_0",
            "Default/Service Worker/big",
            "Default/Extensions/x/manifest.json",
        ],
    )
    dest = session.stage_profile(src, "Default", tmp_path / "staged")
    assert (dest / "Local State").exists()
    assert (dest / "Default" / "Cookies").exists()
    assert (dest / "Default" / "Preferences").exists()
    assert not (dest / "Default" / "Cache").exists()
    assert not (dest / "Default" / "Service Worker").exists()
    assert not (dest / "Default" / "Extensions").exists()


def test_missing_optional_files_are_tolerated(tmp_path):
    src = _fake_profile(tmp_path, ["Local State", "Default/Cookies"])
    dest = session.stage_profile(src, "Default", tmp_path / "staged")
    assert (dest / "Default" / "Cookies").exists()


def test_missing_cookies_raises_clear_error(tmp_path):
    src = _fake_profile(tmp_path, ["Local State", "Default/Preferences"])
    try:
        session.stage_profile(src, "Default", tmp_path / "staged")
    except session.ProfileError as e:
        assert "Cookies" in str(e)
    else:
        raise AssertionError("expected ProfileError without Cookies")


def test_missing_profile_dir_raises_clear_error(tmp_path):
    try:
        session.stage_profile(tmp_path / "nope", "Default", tmp_path / "staged")
    except session.ProfileError as e:
        assert "nope" in str(e)
    else:
        raise AssertionError("expected ProfileError")


def test_restages_cleanly_over_previous_copy(tmp_path):
    src = _fake_profile(tmp_path, ["Local State", "Default/Cookies"])
    dest = tmp_path / "staged"
    session.stage_profile(src, "Default", dest)
    (dest / "Default" / "stale-leftover").write_text("old")
    session.stage_profile(src, "Default", dest)
    assert not (dest / "Default" / "stale-leftover").exists()


def test_chrome_options_point_at_staged_profile(tmp_path):
    opts = session.chrome_options_for(tmp_path / "staged", "Default")
    args = opts.arguments
    assert f"--user-data-dir={tmp_path / 'staged'}" in args
    assert "--profile-directory=Default" in args
    assert any(a.startswith("--window-size") for a in args)


def test_default_profile_root_is_macos_chrome():
    root = session.default_profile_root()
    assert str(root).endswith(os.path.join("Google", "Chrome"))


def test_is_logged_in_detects_login_page():
    class D:
        current_url = "https://www.cbssports.com/login?x=1"

    assert session.is_logged_in(D()) is False


def test_is_logged_in_detects_pool_page():
    class D:
        current_url = "https://picks.cbssports.com/football/pickem/pools/abc/standings/weekly"

    assert session.is_logged_in(D()) is True


def test_is_logged_in_treats_join_page_as_not_ready():
    class D:
        current_url = "https://picks.cbssports.com/football/pickem/pools/abc===/join?device=desktop"

    assert session.is_logged_in(D()) is False


def test_canonical_slug_pads_to_multiple_of_eight():
    assert session.canonical_slug("kbxw63b2ge3dknzzg42to") == "kbxw63b2ge3dknzzg42to==="
    assert session.canonical_slug("kbxw63b2ge3dknzzg42to===") == "kbxw63b2ge3dknzzg42to==="
    assert session.canonical_slug("abcdefgh") == "abcdefgh"
