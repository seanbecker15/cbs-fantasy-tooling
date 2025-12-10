import datetime
import json
import os
import shutil
from typing import Dict, Any

from cbs_fantasy_tooling.models import PickemResult, PickemResults

from . import Publisher

JSON_FILENAMES = {
    'pickem_results': lambda week: f"week_{week}_pickem_results.json",
    'game_results': lambda week: f"week_{week}_game_results.json",
}

CSV_FILENAMES = {
    'pickem_results': lambda week: f"week_{week}_pickem_results.csv",
}


class FilePublisher(Publisher):
    """Publisher that saves results to local files"""
    name = "file"
    output_dir: str
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.output_dir = config.get('output_dir', 'out')
        os.makedirs(self.output_dir, exist_ok=True)
    
    def validate_config(self) -> bool:
        return True  # File publisher has minimal requirements
    
    def publish_pickem_results(self, results_data: PickemResults) -> bool:
        """Save results to local files"""
        try:
            # Save CSV
            csv_path = self.save_csv(results_data)
            print(f"Results saved to CSV: {csv_path}")
            
            # Save JSON for more detailed data
            json_path = self.save_json(results_data)
            print(f"Results saved to JSON: {json_path}")
            
            # Create backup if backup_dir is specified
            backup_dir = self.config.get('backup_dir')
            if backup_dir:
                self._create_backup(csv_path, json_path, backup_dir)
            
            return True
            
        except Exception as error:
            print(f"File publisher error: {error}")
            return False
        
    def publish_game_results(self, results_data):
        """Save game results to local files"""
        try:
            filename = f"week_{results_data.week}_game_results.json"
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, 'w') as f:
                json.dump(results_data.to_dict(), f, indent=2)
            
        except Exception as error:
            print(f"File publisher error: {error}")
            return False
        
    
    def _create_backup(self, csv_path: str, json_path: str, backup_dir: str):
        """Create backup copies of the files"""
        try:
            os.makedirs(backup_dir, exist_ok=True)
            
            csv_backup = os.path.join(backup_dir, os.path.basename(csv_path))
            json_backup = os.path.join(backup_dir, os.path.basename(json_path))
            
            shutil.copy2(csv_path, csv_backup)
            shutil.copy2(json_path, json_backup)
            
            print(f"Backups created in: {backup_dir}")
            
        except Exception as error:
            print(f"Backup creation failed: {error}")

    def save_csv(self, results_data: PickemResults, filename: str = None) -> str:
        if not filename:
            week = results_data.week_number
            filename = CSV_FILENAMES['pickem_results'](week)
        
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', newline='') as f:
            f.write(results_data.to_csv())
        
        return filepath
    
    def save_json(self, results_data: PickemResults, filename: str = None) -> str:
        if not filename:
            week = results_data.week_number
            filename = JSON_FILENAMES['pickem_results'](week)
        
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(results_data.to_dict(), f, indent=2)
        
        return filepath
    
    def load_json(self, filepath: str) -> PickemResults:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        results = []
        for result in data['results']:
            row = PickemResult()
            row.name = result['name']
            row.results = [result['points'], result['wins'], result['losses']]
            results.append(row)
        
        results_data = PickemResults(results, data.get('week_number'))
        results_data.timestamp = datetime.fromisoformat(data['timestamp'])
        
        return results_data
