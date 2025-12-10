from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any

from .pickem_result import PickemResult

@dataclass
class PickemResults:
    results: List[PickemResult]
    week_number: int = None
    timestamp: datetime = datetime.now()

    def __init__(self, results: List[PickemResult], week: int = None):
        self.results = results
        self.week_number = week
        self.timestamp = datetime.now()
    
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

