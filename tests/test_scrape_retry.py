"""The scheduled scrape retries transient failures instead of giving up.

The week 3 job failed at 9:30 on a timing flake (the week dropdown had not
rendered when it was looked up), exited 1, and nothing happened until a
human noticed that evening. The same code path succeeded on the next
attempt. A few spaced retries turn that into a non-event.
"""

import pytest

import cbs_fantasy_tooling.scrape as entry


def _run(monkeypatch, outcomes, attempts=3, delay=0):
    """Drive main() with a scripted sequence of ingest outcomes."""
    calls = []
    seq = iter(outcomes)

    def fake_ingest(params, publishers):
        calls.append(params.target_week)
        return next(seq)

    slept = []
    monkeypatch.setattr(entry, "create_publishers", lambda: [])
    monkeypatch.setattr(entry, "ingest_pickem_results", fake_ingest)
    monkeypatch.setattr(entry, "sleep", lambda s: slept.append(s))
    with pytest.raises(SystemExit) as e:
        entry.main(attempts=attempts, delay_seconds=delay)
    return e.value.code, calls, slept


def test_first_try_success_does_not_retry(monkeypatch):
    code, calls, slept = _run(monkeypatch, [True])
    assert code == 0 and len(calls) == 1 and slept == []


def test_transient_failure_then_success_exits_zero(monkeypatch):
    code, calls, slept = _run(monkeypatch, [False, True], delay=600)
    assert code == 0
    assert len(calls) == 2
    assert slept == [600], "waits between attempts, not after success"


def test_exhausted_retries_exit_nonzero(monkeypatch):
    code, calls, slept = _run(monkeypatch, [False, False, False], attempts=3, delay=5)
    assert code == 1
    assert len(calls) == 3
    assert slept == [5, 5], "no sleep after the final attempt"


def test_each_attempt_builds_fresh_publishers(monkeypatch):
    """A stale Gmail service or browser must not leak across attempts."""
    built = []
    monkeypatch.setattr(entry, "create_publishers", lambda: built.append(1) or [])
    monkeypatch.setattr(entry, "ingest_pickem_results", lambda p, pubs: len(built) == 2)
    monkeypatch.setattr(entry, "sleep", lambda s: None)
    with pytest.raises(SystemExit) as e:
        entry.main(attempts=3, delay_seconds=0)
    assert e.value.code == 0 and len(built) == 2
