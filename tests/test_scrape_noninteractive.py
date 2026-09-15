"""The scraper must survive a session with no terminal attached.

launchd runs the Tuesday job with stdin on /dev/null. select() reports that
as readable (it is EOF), so the "press Enter" prompt called input(), raised
EOFError, and the run died before scraping - while still exiting 0.
"""

import io

import pytest

from cbs_fantasy_tooling.ingest.cbs_sports import scrape


class _NoTTY(io.StringIO):
    def isatty(self):
        return False


class _TTYAtEOF(io.StringIO):
    """Looks interactive, but reading it hits EOF immediately."""

    def isatty(self):
        return True

    def fileno(self):
        return 0


def test_non_interactive_stdin_skips_prompt_and_waits(monkeypatch):
    monkeypatch.setattr(scrape.sys, "stdin", _NoTTY())
    slept = []
    monkeypatch.setattr(scrape, "sleep", lambda s: slept.append(s))
    called = []
    monkeypatch.setattr("builtins.input", lambda *a: called.append(1))

    assert scrape.wait_for_user_input(30) is False
    assert called == [], "must not read from a non-interactive stdin"
    assert slept == [30], "keep the settling delay so the login page can load"


def test_non_interactive_stdin_is_never_an_exit_signal(monkeypatch):
    monkeypatch.setattr(scrape.sys, "stdin", _NoTTY())
    assert scrape.wait_for_exit_signal() is False


def test_eof_on_interactive_stdin_is_not_a_keypress(monkeypatch):
    monkeypatch.setattr(scrape.sys, "stdin", _TTYAtEOF())
    monkeypatch.setattr(scrape.select, "select", lambda r, w, x, t=None: (r, [], []))

    def _eof(*a):
        raise EOFError

    monkeypatch.setattr("builtins.input", _eof)
    assert scrape.wait_for_user_input(0) is False


def test_ingest_reports_failure_instead_of_swallowing(monkeypatch):
    """A failed run must return False so the entrypoint can exit non-zero."""

    def boom(params, publishers):
        raise RuntimeError("chrome exploded")

    monkeypatch.setattr(scrape, "run_scraper", boom)
    params = scrape.PickemIngestParams(curr_week=2, target_week=1)
    assert scrape.ingest_pickem_results(params, publishers=[]) is False


def test_ingest_reports_success(monkeypatch):
    row = scrape.PickemResult()
    row.name, row.results, row.picks = "A", ["10", 1, 0], []
    monkeypatch.setattr(scrape, "run_scraper", lambda p, pubs: [(1, [row])])
    monkeypatch.setattr(scrape, "publish_results", lambda r, pubs: None)
    params = scrape.PickemIngestParams(curr_week=2, target_week=1)
    assert scrape.ingest_pickem_results(params, publishers=[]) is True


def test_ingest_empty_scrape_is_failure(monkeypatch):
    monkeypatch.setattr(scrape, "run_scraper", lambda p, pubs: [])
    params = scrape.PickemIngestParams(curr_week=2, target_week=1)
    assert scrape.ingest_pickem_results(params, publishers=[]) is False


@pytest.mark.parametrize("ok, code", [(True, 0), (False, 1)])
def test_entrypoint_exit_code_reflects_outcome(monkeypatch, ok, code):
    import cbs_fantasy_tooling.scrape as entry

    monkeypatch.setattr(entry, "create_publishers", lambda: [])
    monkeypatch.setattr(entry, "ingest_pickem_results", lambda p, pubs: ok)
    with pytest.raises(SystemExit) as e:
        entry.main()
    assert e.value.code == code
