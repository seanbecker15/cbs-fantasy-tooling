import os
import csv
import json
from datetime import datetime
from typing import List, Dict, Any


class Row:
    def __init__(self):
        self.name = ""
        self.results = []

    def __str__(self):
        out = "Row: { name: " + self.name + \
            ", results: [ " + self.csv() + " ] }"
        return out

    def csv(self):
        cols = [self.name] + [str(x) for x in self.results]
        csv = ",".join(cols)
        return csv


class ResultsData:
    def __init__(self, results: List[Row], week_number: int = None):
        self.results = results
        self.week_number = week_number
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
                    "losses": row.results[2]
                }
                for row in self.results
            ]
        }


class Storage:
    def __init__(self, output_dir: str = "out"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def save_csv(self, results_data: ResultsData, filename: str = None) -> str:
        if not filename:
            week_str = f"week_{results_data.week_number}_" if results_data.week_number else ""
            filename = f"{week_str}results_{results_data.timestamp.strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', newline='') as f:
            f.write(results_data.to_csv())
        
        return filepath
    
    def save_json(self, results_data: ResultsData, filename: str = None) -> str:
        if not filename:
            week_str = f"week_{results_data.week_number}_" if results_data.week_number else ""
            filename = f"{week_str}results_{results_data.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(results_data.to_dict(), f, indent=2)
        
        return filepath
    
    def load_json(self, filepath: str) -> ResultsData:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        results = []
        for result in data['results']:
            row = Row()
            row.name = result['name']
            row.results = [result['points'], result['wins'], result['losses']]
            results.append(row)
        
        results_data = ResultsData(results, data.get('week_number'))
        results_data.timestamp = datetime.fromisoformat(data['timestamp'])
        
        return results_data


def print_results_summary(results_data: ResultsData):
    print(results_data.to_csv())
    
    wins_data = results_data.get_max_wins_data()
    print(f"Most wins for the week: {wins_data['max_wins']}")
    print(f"Players with the most wins: {wins_data['players']}")
    
    points_data = results_data.get_max_points_data()
    print(f"Most points for the week: {points_data['max_points']}")
    print(f"Players with the most points: {points_data['players']}")