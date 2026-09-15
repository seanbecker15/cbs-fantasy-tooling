"""The weekly email must look like mail, not like an API payload.

Gmail showed "This message isn't authenticated and the sender can't be
verified" on the week 1 email. An A/B send with canonical header names and a
display name was clean; the original emitted lowercase `from:`/`to:` with a
bare address. Lock in the well-formed shape.
"""

import base64
from email import message_from_bytes

from cbs_fantasy_tooling.models import PickemResult, PickemResults
from cbs_fantasy_tooling.publishers.gmail import GmailPublisher


def _results():
    rows = []
    for name, pts, wins, losses in [("A", "100", 12, 4), ("B", "90", 10, 6)]:
        r = PickemResult()
        r.name, r.results, r.picks = name, [pts, wins, losses], []
        rows.append(r)
    return PickemResults(rows, week=1)


def _raw(cfg):
    pub = GmailPublisher(cfg)
    return base64.urlsafe_b64decode(pub._create_message(_results())["raw"])


BASE = {
    "credentials_file": "x",
    "token_file": "y",
    "from": "me@example.com",
    "from_name": "3GS Pick'em",
    "to": ["me@example.com", "you@example.com"],
}


def test_headers_are_canonical_case():
    raw = _raw(BASE)
    assert b"\nFrom: " in raw and b"\nTo: " in raw and b"\nSubject: " in raw
    for bad in (b"\nfrom: ", b"\nto: ", b"\nsubject: "):
        assert bad not in raw


def test_from_carries_display_name():
    msg = message_from_bytes(_raw(BASE))
    assert msg["From"] == "3GS Pick'em <me@example.com>"


def test_display_name_defaults_when_missing():
    cfg = {k: v for k, v in BASE.items() if k != "from_name"}
    msg = message_from_bytes(_raw(cfg))
    assert msg["From"].endswith("<me@example.com>") and msg["From"] != "me@example.com"


def test_subject_includes_week_and_recipients_joined():
    msg = message_from_bytes(_raw(BASE))
    assert msg["Subject"] == "3GS Results - Week 1"
    assert msg["To"] == "me@example.com, you@example.com"


def test_csv_attachment_still_present():
    msg = message_from_bytes(_raw(BASE))
    names = [p.get_filename() for p in msg.walk() if p.get_filename()]
    assert names == ["results.csv"]
