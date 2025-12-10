from dataclasses import asdict, dataclass

from .game_result import GameResult

@dataclass
class GameResults:
    """Represents a week of NFL game results."""

    week: int
    season: int
    num_games: int
    games: list[GameResult]

    @staticmethod
    def from_dict(data: dict) -> 'GameResults':
        games = [GameResult.from_dict(game_data) for game_data in data.get('games', [])]
        return GameResults(
            week=data.get('week', 0),
            season=data.get('season', 0),
            num_games=data.get('num_games', len(games)),
            games=games
        )

    def to_dict(self) -> dict:
        games = [asdict(game) for game in self.games]
        for game in games:
            if game['game_time']:
                game['game_time'] = game['game_time'].isoformat()

        return {
            "week": self.week,
            "season": self.season,
            "num_games": self.num_games,
            "games": games
        }

