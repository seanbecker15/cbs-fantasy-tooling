from typing import List
from cbs_fantasy_tooling.config import config
from cbs_fantasy_tooling.publishers import Publisher
from cbs_fantasy_tooling.publishers.database import DatabasePublisher
from cbs_fantasy_tooling.publishers.file import FilePublisher
from cbs_fantasy_tooling.publishers.gmail import GmailPublisher


def create_publishers():
    """Create and return list of enabled publishers"""
    publishers: List[Publisher] = []

    # File publisher (always safe to include)
    if config.is_publisher_enabled("file"):
        file_pub = FilePublisher(config.get_publisher_config("file"))
        if file_pub.validate_config() and file_pub.authenticate():
            publishers.append(file_pub)
        else:
            print("File publisher configuration invalid")

    # Gmail publisher
    if config.is_publisher_enabled("gmail"):
        gmail_pub = GmailPublisher(config.get_publisher_config("gmail"))
        if gmail_pub.validate_config() and gmail_pub.authenticate():
            publishers.append(gmail_pub)
        else:
            print("Gmail publisher configuration invalid - check credentials file and recipients")

    # Database publisher
    if config.is_publisher_enabled("database"):
        database_pub = DatabasePublisher(config.get_publisher_config("database"))
        if database_pub.validate_config() and database_pub.authenticate():
            publishers.append(database_pub)
        else:
            print("Database publisher configuration invalid")

    return publishers
