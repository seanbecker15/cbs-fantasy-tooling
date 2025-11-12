import os
import shutil
from typing import Dict, Any
from datetime import datetime

try:
    import dropbox
    from dropbox.exceptions import AuthError, ApiError
    DROPBOX_AVAILABLE = True
except ImportError:
    DROPBOX_AVAILABLE = False

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


class DropboxPublisher(Publisher):
    """Publisher that uploads results to Dropbox"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        if not DROPBOX_AVAILABLE:
            raise ImportError("dropbox package not installed. Run: pip install dropbox")
    
    def validate_config(self) -> bool:
        return 'access_token' in self.config and self.config['access_token']

    def test_authentication(self) -> bool:
        """Test Dropbox authentication before scraping"""
        try:
            dbx = dropbox.Dropbox(self.config['access_token'])
            dbx.users_get_current_account()
            print("✓ Dropbox authentication successful")
            return True
        except AuthError:
            print("✗ Dropbox authentication failed. Check access token.")
            return False
        except Exception as error:
            print(f"✗ Dropbox authentication error: {error}")
            return False

    def publish(self, results_data: ResultsData) -> bool:
        """Upload results to Dropbox"""
        try:
            dbx = dropbox.Dropbox(self.config['access_token'])
            
            # Test connection
            try:
                dbx.users_get_current_account()
            except AuthError:
                print("Dropbox authentication failed. Check access token.")
                return False
            
            folder = self.config.get('folder', '/3gs-results')
            timestamp = results_data.timestamp.strftime('%Y%m%d_%H%M%S')
            week_str = f"week_{results_data.week_number}_" if results_data.week_number else ""
            
            # Upload CSV
            csv_filename = f"{week_str}results_{timestamp}.csv"
            csv_path = f"{folder}/{csv_filename}"
            csv_data = results_data.to_csv().encode()
            
            dbx.files_upload(csv_data, csv_path, mode=dropbox.files.WriteMode.overwrite)
            print(f"CSV uploaded to Dropbox: {csv_path}")
            
            # Upload JSON
            json_filename = f"{week_str}results_{timestamp}.json"
            json_path = f"{folder}/{json_filename}"
            import json
            json_data = json.dumps(results_data.to_dict(), indent=2).encode()
            
            dbx.files_upload(json_data, json_path, mode=dropbox.files.WriteMode.overwrite)
            print(f"JSON uploaded to Dropbox: {json_path}")
            
            # Create shareable links
            try:
                csv_link = dbx.sharing_create_shared_link(csv_path)
                print(f"Shareable CSV link: {csv_link.url}")
            except ApiError as e:
                if e.error.is_shared_link_already_exists():
                    links = dbx.sharing_list_shared_links(path=csv_path)
                    if links.links:
                        print(f"Existing CSV link: {links.links[0].url}")
            
            return True
            
        except Exception as error:
            print(f"Dropbox publisher error: {error}")
            return False