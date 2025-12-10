from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any

from .pickem_result import PickemResult

@dataclass
class PickemResults:
    results: List[PickemResult]
    week_number: int = None
    timestamp: datetime = datetime.now()
    max_wins_players: List[str] = None
    max_wins_value: int = None
    max_points_players: List[str] = None
    max_points_value: int = None

    def __init__(self, results: List[PickemResult], week: int = None):
        self.results = results
        self.week_number = week
        self.timestamp = datetime.now()
        max_wins_data = self.get_max_wins_data()
        self.max_wins_value = max_wins_data["max_wins"]
        self.max_wins_players = max_wins_data["players"]
        max_points_data = self.get_max_points_data()
        self.max_points_value = max_points_data["max_points"]
        self.max_points_players = max_points_data["players"]
    
    def to_csv(self) -> str:
        csv_data = "Name,Points,Wins,Losses\n"
        for row in self.results:
            csv_data += row.csv() + "\n"
        return csv_data
    
    def get_max_wins_data(self) -> Dict[str, Any]:
        max_wins = 0
        for row in self.results:
            if row.results[1] > max_wins:
                max_wins = row.results[1]
        players_with_max_wins = [
            row.name for row in self.results if row.results[1] == max_wins]
        
        return {
            "max_wins": max_wins,
            "players": ', '.join(players_with_max_wins)
        }
    
    def get_max_points_data(self) -> Dict[str, Any]:
        max_points = 0
        for row in self.results:
            curr_row_points = int(row.results[0])
            if curr_row_points > max_points:
                max_points = curr_row_points
        players_with_max_points = [
            row.name for row in self.results if int(row.results[0]) == max_points]
        
        return {
            "max_points": max_points,
            "players": ', '.join(players_with_max_points)
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'PickemResults':
        results = []
        for result in data['results']:
            row = PickemResult()
            row.name = result['name']
            row.results = [result['points'], result['wins'], result['losses']]
            row.picks = result.get('picks', [])
            results.append(row)
        
        results_data = PickemResults(results, data.get('week_number'))
        results_data.timestamp = datetime.fromisoformat(data['timestamp'])
        results_data.max_wins_value = data.get('max_wins', {}).get('max_wins')
        results_data.max_wins_players = data.get('max_wins', {}).get('players')
        results_data.max_points_value = data.get('max_points', {}).get('max_points')
        results_data.max_points_players = data.get('max_points', {}).get('players')
        return results_data
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "week_number": self.week_number,
            "max_wins": self.get_max_wins_data(),
            "max_points": self.get_max_points_data(),
            "results": [
                {
                    "name": row.name,
                    "points": row.results[0],
                    "wins": row.results[1],
                    "losses": row.results[2],
                    "picks": row.picks
                }
                for row in self.results
            ]
        }

