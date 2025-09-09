import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv


class Config:
    def __init__(self, env_file: str = ".env"):
        load_dotenv(env_file)
        
        # Scraping configuration
        self.email = os.getenv("EMAIL")
        self.password = os.getenv("PASSWORD")
        
        # Gmail API configuration
        self.gmail_credentials_file = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
        self.gmail_token_file = os.getenv("GMAIL_TOKEN_FILE", "token.json")
        self.gmail_from = os.getenv("GMAIL_FROM")
        
        # SendGrid configuration (legacy)
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.notification_from = os.getenv("NOTIFICATION_FROM")
        self.notification_to = self._parse_recipients(os.getenv("NOTIFICATION_TO"))
        
        # File storage configuration
        self.output_dir = os.getenv("OUTPUT_DIR", "out")
        self.backup_dir = os.getenv("BACKUP_DIR", "backups")
        
        # Dropbox configuration (optional)
        self.dropbox_access_token = os.getenv("DROPBOX_ACCESS_TOKEN")
        self.dropbox_folder = os.getenv("DROPBOX_FOLDER", "/3gs-results")
        
        # Web publishing configuration
        self.web_output_dir = os.getenv("WEB_OUTPUT_DIR", "web")
        self.web_title = os.getenv("WEB_TITLE", "3GS Fantasy Results")
        
        # Publisher configuration - which publishers to use
        self.enabled_publishers = self._parse_enabled_publishers()
        
        # Week configuration
        self.week_one_start_date = os.getenv("WEEK_ONE_START_DATE", "2025-09-02")
    
    def _parse_recipients(self, recipients_str: Optional[str]) -> List[str]:
        if not recipients_str:
            return []
        return [email.strip() for email in recipients_str.split(",")]
    
    def _parse_enabled_publishers(self) -> List[str]:
        publishers_str = os.getenv("ENABLED_PUBLISHERS", "file,gmail")
        return [pub.strip().lower() for pub in publishers_str.split(",")]
    
    def validate_scraping_config(self) -> bool:
        return bool(self.email and self.password)
    
    def validate_gmail_config(self) -> bool:
        return bool(
            self.gmail_credentials_file and 
            os.path.exists(self.gmail_credentials_file) and 
            self.gmail_from and 
            self.notification_to
        )
    
    def validate_sendgrid_config(self) -> bool:
        return bool(self.sendgrid_api_key and self.notification_from and self.notification_to)
    
    def validate_dropbox_config(self) -> bool:
        return bool(self.dropbox_access_token)
    
    def get_publisher_config(self, publisher_name: str) -> Dict[str, Any]:
        """Get configuration specific to a publisher"""
        configs = {
            "gmail": {
                "credentials_file": self.gmail_credentials_file,
                "token_file": self.gmail_token_file,
                "from": self.gmail_from,
                "to": self.notification_to
            },
            "sendgrid": {
                "api_key": self.sendgrid_api_key,
                "from": self.notification_from,
                "to": self.notification_to
            },
            "file": {
                "output_dir": self.output_dir,
                "backup_dir": self.backup_dir
            },
            "dropbox": {
                "access_token": self.dropbox_access_token,
                "folder": self.dropbox_folder
            },
            "web": {
                "output_dir": self.web_output_dir,
                "title": self.web_title
            }
        }
        return configs.get(publisher_name, {})
    
    def is_publisher_enabled(self, publisher_name: str) -> bool:
        return publisher_name.lower() in self.enabled_publishers