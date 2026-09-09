"""Tests covering the season-rollover seams.

These are the pieces that silently broke between the 2025 and 2026 seasons:
the CBS pool slug, the ESPN client's headers, the game-results schema key,
and the field composition that feeds the simulator.
"""

import json
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest

from cbs_fantasy_tooling.analysis.core.simulator import build_field
from cbs_fantasy_tooling.analysis.data.enrichment import load_game_results
from cbs_fantasy_tooling.ingest.cbs_sports.scrape import build_login_url
from cbs_fantasy_tooling.ingest.espn.api import ESPNGameOutcomeApi


class TestBuildLoginUrl:
    """The pool slug changes every season, so it must come from config."""

    def test_embeds_pool_slug_in_redirect(self):
        url = build_login_url("abc123slug")
        xurl = parse_qs(urlparse(url).query)["xurl"][0]
        assert "/pools/abc123slug/standings/weekly" in xurl

    def test_redirect_is_url_encoded(self):
        # The slug must be encoded inside xurl, not left as a bare nested URL.
        url = build_login_url("abc123slug")
        assert "xurl=https%3A%2F%2Fpicks.cbssports.com" in url

    def test_missing_slug_raises_actionable_error(self, monkeypatch):
        monkeypatch.setattr(
            "cbs_fantasy_tooling.ingest.cbs_sports.scrape.config.cbs_pool_slug", None
        )
        with pytest.raises(ValueError, match="CBS_POOL_SLUG"):
            build_login_url()


class TestEspnClient:
    """ESPN's edge 403s browser-like User-Agents; we must not send one."""

    def test_does_not_override_user_agent(self):
        api = ESPNGameOutcomeApi(season=2026)
        assert "Mozilla" not in api.session.headers.get("User-Agent", "")

    def test_uses_https(self):
        from cbs_fantasy_tooling.ingest.espn.api import BASE_URL

        assert BASE_URL.startswith("https://")

    def test_rejects_out_of_range_week(self):
        api = ESPNGameOutcomeApi(season=2026)
        with pytest.raises(ValueError):
            api.fetch_game_results(week=19)

    def test_selects_season_with_dates_not_year(self):
        """ESPN ignores `year` and always returns the current season.

        Only `dates` actually selects a season, so historical backfills break
        silently if this regresses.
        """
        api = ESPNGameOutcomeApi(season=2025)
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"events": []}

        class FakeSession:
            def get(self, url, params=None, timeout=None):
                captured.update(params)
                return FakeResponse()

        api.session = FakeSession()
        api.fetch_game_results(week=17)

        assert captured["dates"] == 2025
        assert "year" not in captured


class TestLoadGameResults:
    """Game result JSON stores the week as `week_number`, not `week`."""

    def _write(self, tmp_path, payload):
        (tmp_path / "week_1_game_results.json").write_text(json.dumps(payload))

    def test_reads_week_number_field(self, tmp_path):
        self._write(
            tmp_path,
            {
                "week": 1,
                "season": 2026,
                "games": [
                    {
                        "game_id": "1",
                        "week_number": 1,
                        "home_team": "SEA",
                        "away_team": "NE",
                        "home_score": 24,
                        "away_score": 20,
                        "winning_team": "SEA",
                        "losing_team": "NE",
                    }
                ],
            },
        )
        df = load_game_results(str(tmp_path))
        assert df.iloc[0]["week"] == 1
        assert df.iloc[0]["winning_team"] == "SEA"

    def test_falls_back_to_top_level_week(self, tmp_path):
        self._write(
            tmp_path,
            {
                "week": 7,
                "season": 2026,
                "games": [
                    {
                        "game_id": "1",
                        "home_team": "SEA",
                        "away_team": "NE",
                        "home_score": 24,
                        "away_score": 20,
                        "winning_team": "SEA",
                        "losing_team": "NE",
                    }
                ],
            },
        )
        df = load_game_results(str(tmp_path))
        assert df.iloc[0]["week"] == 7

    def test_missing_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_game_results(str(tmp_path / "nope"))


class TestBuildField:
    """Roster size drifts between seasons; the sim must adapt, not crash."""

    def test_exact_match(self):
        mix = {"Chalk-MaxPoints": 13, "Slight-Contrarian": 18, "Aggressive-Contrarian": 0}
        assert len(build_field(mix, n_others=31)) == 31

    def test_pads_when_field_too_small(self):
        mix = {"Chalk-MaxPoints": 5, "Slight-Contrarian": 5}
        assert len(build_field(mix, n_others=31)) == 31

    def test_trims_when_field_too_large(self):
        mix = {"Chalk-MaxPoints": 40, "Slight-Contrarian": 10}
        assert len(build_field(mix, n_others=31)) == 31

    def test_empty_mix_raises(self):
        with pytest.raises(ValueError, match="empty"):
            build_field({"Chalk-MaxPoints": 0}, n_others=31)


class TestWeekCalculation:
    """Current week vs last completed week must not be conflated.

    Week 1 is the case that broke: the old clamp made "current week" resolve
    to 2 while the Week 1 slate was still being played.
    """

    @staticmethod
    def _freeze(monkeypatch, year, month, day, start="2026-09-08"):
        import cbs_fantasy_tooling.utils.date as date_utils

        class FakeDatetime(date_utils.datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(year, month, day)

        monkeypatch.setattr(date_utils, "datetime", FakeDatetime)
        monkeypatch.setattr(date_utils.config, "week_one_start_date", start)
        return date_utils

    def test_current_week_is_one_during_week_one(self, monkeypatch):
        d = self._freeze(monkeypatch, 2026, 9, 10)
        assert d.calc_weeks_elapsed() == 0
        assert d.get_current_week() == 1

    def test_current_week_advances_in_week_two(self, monkeypatch):
        d = self._freeze(monkeypatch, 2026, 9, 16)
        assert d.get_current_week() == 2
        assert d.get_last_completed_week() == 1

    def test_last_completed_week_clamps_to_one_in_week_one(self, monkeypatch):
        d = self._freeze(monkeypatch, 2026, 9, 10)
        assert d.get_last_completed_week() == 1

    def test_clamps_to_eighteen(self, monkeypatch):
        d = self._freeze(monkeypatch, 2027, 6, 1)
        assert d.get_current_week() == 18
        assert d.get_last_completed_week() == 18

    def test_deprecated_alias_matches_last_completed(self, monkeypatch):
        d = self._freeze(monkeypatch, 2026, 10, 20)
        assert d.calc_weeks_since_start() == d.get_last_completed_week()


def test_pandas_available():
    """Guard against the enrichment pipeline losing its pandas dependency."""
    assert pd is not None
