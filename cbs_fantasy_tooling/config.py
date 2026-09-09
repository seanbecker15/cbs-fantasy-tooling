import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# The repository root: parent of the cbs_fantasy_tooling package. Every relative
# path in config is anchored here so behaviour does not depend on the CWD -
# scratch scripts and the scheduled job would otherwise silently load no
# secrets and write output to the wrong place.
REPO_ROOT = Path(__file__).resolve().parent.parent


def _anchor(path: Optional[str]) -> Optional[str]:
    """Resolve a possibly-relative path against REPO_ROOT; absolute paths pass through."""
    if not path:
        return None
    p = Path(path)
    return str(p if p.is_absolute() else REPO_ROOT / p)


class Config:
    def __init__(self, env_file: Optional[str] = None):
        self.env_path = Path(_anchor(env_file or ".env"))
        load_dotenv(self.env_path)

        # Scraping configuration
        self.email = os.getenv("EMAIL")
        self.password = os.getenv("PASSWORD")

        # Gmail API configuration
        self.gmail_credentials_file = _anchor(
            os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
        )
        self.gmail_token_file = _anchor(os.getenv("GMAIL_TOKEN_FILE", "token.json"))
        self.gmail_from = os.getenv("GMAIL_FROM")

        # SendGrid configuration (legacy)
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.notification_from = os.getenv("NOTIFICATION_FROM")
        self.notification_to = self._parse_recipients(os.getenv("NOTIFICATION_TO"))

        # File storage configuration
        self.output_dir = _anchor(os.getenv("OUTPUT_DIR", "data"))
        self.backup_dir = _anchor(os.getenv("BACKUP_DIR"))

        # Historical data used to model the field (prior seasons). Output files are
        # not season-scoped by name, so a new season's ingest would otherwise
        # overwrite the history the competitor model is built from.
        self.history_dir = _anchor(os.getenv("HISTORY_DIR")) or self.output_dir

        # Publisher configuration - which publishers to use
        self.enabled_publishers = self._parse_enabled_publishers()

        # Week configuration
        self.week_one_start_date = os.getenv("WEEK_ONE_START_DATE", "2026-09-08")

        # CBS pool configuration - base32 slug from the pool URL
        # e.g. https://picks.cbssports.com/football/pickem/pools/<slug>/standings/weekly
        self.cbs_pool_slug = os.getenv("CBS_POOL_SLUG")

        # User configuration
        self.user_name = os.getenv("USER_NAME")

        # The Odds API configuration
        self.the_odds_api_key = os.getenv("THE_ODDS_API_KEY")

        # Supabase database configuration
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")

        # Season configuration (year of the NFL season)
        self.season = int(os.getenv("SEASON", datetime.now().year))

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
            self.gmail_credentials_file
            and os.path.exists(self.gmail_credentials_file)
            and self.gmail_from
            and self.notification_to
        )

    def validate_sendgrid_config(self) -> bool:
        return bool(self.sendgrid_api_key and self.notification_from and self.notification_to)

    def validate_database_config(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    def get_publisher_config(self, publisher_name: str) -> Dict[str, Any]:
        """Get configuration specific to a publisher"""
        configs = {
            "gmail": {
                "credentials_file": self.gmail_credentials_file,
                "token_file": self.gmail_token_file,
                "from": self.gmail_from,
                "to": self.notification_to,
            },
            "sendgrid": {
                "api_key": self.sendgrid_api_key,
                "from": self.notification_from,
                "to": self.notification_to,
            },
            "file": {"output_dir": self.output_dir, "backup_dir": self.backup_dir},
            "database": {"url": self.supabase_url, "key": self.supabase_key, "season": self.season},
        }
        return configs.get(publisher_name, {})

    def is_publisher_enabled(self, publisher_name: str) -> bool:
        return publisher_name.lower() in self.enabled_publishers


config = Config()
