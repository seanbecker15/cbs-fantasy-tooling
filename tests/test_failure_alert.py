"""When every scrape attempt fails, the job emails an alert.

Without this, a failed Tuesday run exits 1 into a launchd log nobody reads.
The alert is an ops message, so it goes to the sender's own address only,
and it must never mask the real outcome: a failure to send is logged and the
job still exits 1.
"""

import base64
from email import message_from_bytes

import pytest

import cbs_fantasy_tooling.scrape as entry
from cbs_fantasy_tooling.publishers.gmail import GmailPublisher


class FakeSend:
    def __init__(self, fail=False):
        self.bodies, self.fail = [], fail

    def users(self):
        return self

    def messages(self):
        return self

    def send(self, userId, body):
        self.bodies.append(body)
        return self

    def execute(self):
        if self.fail:
            raise RuntimeError("quota")
        return {"id": "x"}


def _pub(fail=False):
    pub = GmailPublisher(
        {
            "credentials_file": "c",
            "token_file": "t",
            "from": "me@x.com",
            "from_name": "3GS",
            "to": ["me@x.com", "other@x.com"],
        }
    )
    pub.service = FakeSend(fail)
    return pub


def _msg(pub):
    return message_from_bytes(base64.urlsafe_b64decode(pub.service.bodies[0]["raw"]))


def test_alert_goes_only_to_sender():
    pub = _pub()
    assert pub.send_failure_alert(week=4, attempts=4, last_error="dropdown timeout") is True
    m = _msg(pub)
    assert m["To"] == "me@x.com"
    assert "other@x.com" not in m["To"]


def test_alert_names_week_attempts_and_error():
    pub = _pub()
    pub.send_failure_alert(week=4, attempts=4, last_error="Could not find week dropdown")
    m = _msg(pub)
    assert m["Subject"] == "3GS scrape FAILED - Week 4"
    body = m.get_payload()[0].get_payload(decode=True).decode()
    assert "4 attempts" in body and "Could not find week dropdown" in body


def test_alert_send_failure_returns_false_without_raising():
    pub = _pub(fail=True)
    assert pub.send_failure_alert(week=4, attempts=4, last_error="x") is False


def _drive(monkeypatch, outcomes, alerter):
    seq = iter(outcomes)
    monkeypatch.setattr(entry, "create_publishers", lambda: [])
    monkeypatch.setattr(entry, "ingest_pickem_results", lambda p, pubs: next(seq))
    monkeypatch.setattr(entry, "sleep", lambda s: None)
    monkeypatch.setattr(entry, "create_failure_alerter", lambda: alerter)
    with pytest.raises(SystemExit) as e:
        entry.main(attempts=len(outcomes), delay_seconds=0)
    return e.value.code


class SpyAlerter:
    def __init__(self, ok=True):
        self.calls, self.ok = [], ok

    def send_failure_alert(self, week, attempts, last_error):
        self.calls.append((week, attempts, last_error))
        return self.ok


def test_no_alert_on_success(monkeypatch):
    spy = SpyAlerter()
    assert _drive(monkeypatch, [False, True], spy) == 0
    assert spy.calls == []


def test_alert_after_exhausted_retries(monkeypatch):
    spy = SpyAlerter()
    assert _drive(monkeypatch, [False, False, False], spy) == 1
    assert len(spy.calls) == 1 and spy.calls[0][1] == 3


def test_alert_send_failure_does_not_change_exit_code(monkeypatch):
    assert _drive(monkeypatch, [False, False], SpyAlerter(ok=False)) == 1


def test_missing_alerter_does_not_crash(monkeypatch):
    assert _drive(monkeypatch, [False], None) == 1
