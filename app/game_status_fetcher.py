"""
ESPN game status fetcher for NFL schedules and live scores.

Provides normalized game status records suitable for Supabase persistence.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import time

import requests


@dataclass
class GameStatusRecord:
    """Represents a single NFL game status snapshot."""

    game_id: str
    season: int
    week: int
    home_team: str
    away_team: str
    game_time: Optional[datetime]
    is_finished: bool
    home_score: Optional[int]
    away_score: Optional[int]
    status_text: Optional[str]
    winning_team: Optional[str]

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert the record into a Supabase-compatible dictionary."""
        record: Dict[str, Any] = {
            'season': self.season,
            'week_number': self.week,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'is_finished': self.is_finished,
        }

        if self.game_time:
            record['game_time'] = self.game_time.isoformat()

        if self.home_score is not None:
            record['home_score'] = self.home_score

        if self.away_score is not None:
            record['away_score'] = self.away_score

        return record


class ESPNGameStatusFetcher:
    """Fetches NFL game status data from the ESPN scoreboard API."""

    BASE_URL = "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    SEASON_TYPE_REGULAR = 2

    TEAM_MAPPING = {
        'ARI': 'ARI', 'ARZ': 'ARI',
        'ATL': 'ATL',
        'BAL': 'BAL',
        'BUF': 'BUF',
        'CAR': 'CAR',
        'CHI': 'CHI',
        'CIN': 'CIN',
        'CLE': 'CLE',
        'DAL': 'DAL',
        'DEN': 'DEN',
        'DET': 'DET',
        'GB': 'GB', 'GNB': 'GB',
        'HOU': 'HOU',
        'IND': 'IND',
        'JAC': 'JAC', 'JAX': 'JAC',
        'KC': 'KC', 'KAN': 'KC',
        'LAC': 'LAC',
        'LAR': 'LAR',
        'LV': 'LV', 'LVR': 'LV',
        'MIA': 'MIA',
        'MIN': 'MIN',
        'NE': 'NE', 'NEP': 'NE',
        'NO': 'NO', 'NOR': 'NO',
        'NYG': 'NYG',
        'NYJ': 'NYJ',
        'PHI': 'PHI',
        'PIT': 'PIT',
        'SEA': 'SEA',
        'SF': 'SF', 'SFO': 'SF',
        'TB': 'TB', 'TAM': 'TB',
        'TEN': 'TEN',
        'WAS': 'WAS', 'WSH': 'WAS'
    }

    def __init__(self, season: int, session: Optional[requests.Session] = None):
        self.season = season
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; GameStatusFetcher/1.0)'
        })

    def normalize_team_abbrev(self, espn_abbrev: str) -> str:
        """Normalize ESPN team abbreviation to standard form."""
        return self.TEAM_MAPPING.get(espn_abbrev.upper(), espn_abbrev.upper())

    def fetch_week_status(self, week: int, season: Optional[int] = None, max_retries: int = 3) -> List[GameStatusRecord]:
        """
        Fetch game status data for a specific week.

        Args:
            week: NFL week number (1-18)
            season: Season year (defaults to initialized season)
            max_retries: Number of retry attempts for API calls

        Returns:
            List of GameStatusRecord objects
        """
        if week < 1 or week > 18:
            raise ValueError(f"Invalid week number: {week}. Must be between 1 and 18.")

        target_season = season or self.season
        params = {
            'seasontype': self.SEASON_TYPE_REGULAR,
            'week': week,
            'year': target_season,
            'limit': 100
        }

        for attempt in range(max_retries):
            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                return self._parse_response(data, week, target_season)
            except requests.RequestException as exc:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"Retrying ESPN fetch ({attempt + 1}/{max_retries}) after {wait_time}s: {exc}")
                    time.sleep(wait_time)
                else:
                    print(f"Failed to fetch ESPN data after {max_retries} attempts: {exc}")
                    return []

        return []

    def _parse_response(self, data: Dict[str, Any], week: int, season: int) -> List[GameStatusRecord]:
        """Convert ESPN JSON payload into GameStatusRecord objects."""
        records: List[GameStatusRecord] = []

        for event in data.get('events', []):
            try:
                record = self._parse_event(event, week, season)
                if record:
                    records.append(record)
            except (KeyError, ValueError, TypeError) as exc:
                event_id = event.get('id')
                print(f"Warning: could not parse event {event_id}: {exc}")

        records.sort(
            key=lambda record: (
                record.game_time.isoformat() if record.game_time else '',
                record.game_id
            )
        )

        return records

    def _parse_event(self, event: Dict[str, Any], week: int, season: int) -> Optional[GameStatusRecord]:
        """Parse individual event into a GameStatusRecord."""
        competitions = event.get('competitions', [])
        if not competitions:
            return None

        competition = competitions[0]
        competitors = competition.get('competitors', [])
        if len(competitors) != 2:
            return None

        home_team: Optional[Dict[str, Any]] = None
        away_team: Optional[Dict[str, Any]] = None

        for competitor in competitors:
            team_abbrev = self.normalize_team_abbrev(
                competitor.get('team', {}).get('abbreviation', '')
            )
            score_value = self._parse_score(competitor.get('score'))
            entry = {
                'team': team_abbrev,
                'score': score_value
            }
            if competitor.get('homeAway') == 'home':
                home_team = entry
            else:
                away_team = entry

        if not home_team or not away_team:
            return None

        status_info = competition.get('status', {})
        status_type = status_info.get('type', {})
        is_finished = bool(status_type.get('completed', False))
        status_text = status_type.get('detail') or status_type.get('description')

        start_date = competition.get('startDate') or event.get('date')
        game_time = self._parse_datetime(start_date)

        winning_team = self._determine_winner(is_finished, home_team['score'], away_team['score'], home_team['team'], away_team['team'])

        return GameStatusRecord(
            game_id=event.get('id', ''),
            season=season,
            week=week,
            home_team=home_team['team'],
            away_team=away_team['team'],
            game_time=game_time,
            is_finished=is_finished,
            home_score=home_team['score'],
            away_score=away_team['score'],
            status_text=status_text,
            winning_team=winning_team
        )

    @staticmethod
    def _parse_datetime(timestamp: Optional[str]) -> Optional[datetime]:
        """Safely parse ISO8601 timestamp strings."""
        if not timestamp:
            return None
        try:
            return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            return None

    @staticmethod
    def _parse_score(score: Optional[str]) -> Optional[int]:
        """Convert score strings to integers, handling blanks."""
        if score is None or score == '':
            return None
        try:
            return int(float(score))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _determine_winner(
        is_finished: bool,
        home_score: Optional[int],
        away_score: Optional[int],
        home_team: str,
        away_team: str
    ) -> Optional[str]:
        """Determine winning team abbreviation when available."""
        if not is_finished:
            return None

        if home_score is None or away_score is None:
            return None

        if home_score == away_score:
            return None

        return home_team if home_score > away_score else away_team
