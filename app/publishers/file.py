import os
import shutil
from typing import Dict, Any

from . import Publisher
from storage import ResultsData, Storage


class FilePublisher(Publisher):
    """Publisher that saves results to local files"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.storage = Storage(config.get('output_dir', 'out'))
    
    def validate_config(self) -> bool:
        return True  # File publisher has minimal requirements
    
    def publish(self, results_data: ResultsData) -> bool:
        """Save results to local files"""
        try:
            # Save CSV
            csv_path = self.storage.save_csv(results_data)
            print(f"Results saved to CSV: {csv_path}")
            
            # Save JSON for more detailed data
            json_path = self.storage.save_json(results_data)
            print(f"Results saved to JSON: {json_path}")
            
            # Create backup if backup_dir is specified
            backup_dir = self.config.get('backup_dir')
            if backup_dir:
                self._create_backup(csv_path, json_path, backup_dir)
            
            return True
            
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
