"""cbs-publish: take an exported results JSON and run the publishers on it."""

import json

import pytest

from cbs_fantasy_tooling import publish


def _data(week=4, rows=None):
    rows = (
        rows
        if rows is not None
        else [
            {
                "name": "A",
                "points": "88",
                "wins": 11,
                "losses": 5,
                "picks": [{"team": "GB", "points": "12"}] * 16,
            },
            {
                "name": "B",
                "points": "80",
                "wins": 8,
                "losses": 8,
                "picks": [{"team": "KC", "points": "1"}] * 16,
            },
        ]
    )
    return {
        "timestamp": "2026-10-06T18:00:00.000000",
        "week_number": week,
        "max_wins": {"max_wins": 11, "players": "A"},
        "max_points": {"max_points": 88, "players": "A"},
        "results": rows,
    }


def test_validate_accepts_good_file():
    publish.validate(_data())


@pytest.mark.parametrize(
    "mutate, msg",
    [
        (lambda d: d.update(week_number=0), "week_number"),
        (lambda d: d.update(week_number="4"), "week_number"),
        (lambda d: d.update(results=[]), "rows"),
        (lambda d: d["results"][0].update(name=""), "no player name"),
        (lambda d: d["results"][0].update(points="eighty"), "not a number"),
        (lambda d: d["results"][0].update(wins=20), "exceeds pick count"),
    ],
)
def test_validate_rejects_bad_files(mutate, msg):
    d = _data()
    mutate(d)
    with pytest.raises(publish.InvalidResults, match=msg):
        publish.validate(d)


def test_stages_into_output_dir_under_canonical_name(tmp_path, monkeypatch):
    monkeypatch.setattr(publish.config, "output_dir", str(tmp_path / "out"))
    src = tmp_path / "Downloads" / "week_4_pickem_results (1).json"
    src.parent.mkdir()
    src.write_text(json.dumps(_data()))
    dest = publish.stage_into_output_dir(src)
    assert dest == tmp_path / "out" / "week_4_pickem_results.json"
    assert json.loads(dest.read_text())["week_number"] == 4


def test_main_publishes_valid_file(tmp_path, monkeypatch):
    monkeypatch.setattr(publish.config, "output_dir", str(tmp_path / "out"))
    src = tmp_path / "week_4_pickem_results.json"
    src.write_text(json.dumps(_data()))
    published = []

    class Pub:
        name = "fake"

        def publish_pickem_results(self, results):
            published.append((results.week_number, len(results.results)))
            return True

    monkeypatch.setattr(publish, "create_publishers", lambda: [Pub()])
    assert publish.main([str(src)]) == 0
    assert published == [(4, 2)]


def test_main_refuses_invalid_file_before_publishing(tmp_path, monkeypatch):
    src = tmp_path / "bad.json"
    src.write_text(json.dumps(_data(rows=[])))
    monkeypatch.setattr(publish, "create_publishers", lambda: pytest.fail("must not publish"))
    assert publish.main([str(src)]) == 1


def test_main_with_no_file_and_no_download_is_usage_error(monkeypatch):
    monkeypatch.setattr(publish, "newest_download", lambda: None)
    assert publish.main([]) == 2
