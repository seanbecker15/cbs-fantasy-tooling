from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

@dataclass
class GameResult:
    """Represents a single NFL game status snapshot."""

    game_id: str
    game_time: Optional[datetime]
    season: int
    week_number: int
    home_team: str
    away_team: str
    is_finished: bool
    home_score: Optional[int]
    away_score: Optional[int]
    status_text: Optional[str]
    winning_team: Optional[str]
    losing_team: Optional[str]

    @staticmethod
    def from_dict(data: dict) -> 'GameResult':
        game_time = data.get('game_time')
        if game_time:
            game_time = datetime.fromisoformat(game_time)
        return GameResult(
            game_id=data.get('game_id', ''),
            game_time=game_time,
            season=data.get('season', 0),
            week_number=data.get('week', 0),
            home_team=data.get('home_team', ''),
            away_team=data.get('away_team', ''),
            is_finished=data.get('is_finished', False),
            home_score=data.get('home_score'),
            away_score=data.get('away_score'),
            status_text=data.get('status_text'),
            winning_team=data.get('winning_team'),
            losing_team=data.get('losing_team')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the record into a Supabase-compatible dictionary."""
        record: Dict[str, Any] = {
            'season': self.season,
            'week_number': self.week_number,
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