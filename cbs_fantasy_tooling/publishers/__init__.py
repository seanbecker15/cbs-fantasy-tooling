from abc import ABC, abstractmethod
from typing import Any, Dict

from cbs_fantasy_tooling.models import PickemResults, GameResults


class Publisher(ABC):
    """Abstract base class for all publishers"""

    name: str

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate that the configuration is sufficient for this publisher.

        Returns:
            bool: True if configuration is valid, False otherwise
        """
        pass

    def publish_pickem_results(self, results_data: PickemResults) -> bool:
        """
        Publish the results data.

        Args:
            results_data: The processed results to publish

        Returns:
            bool: True if publishing succeeded, False otherwise
        """
        return True

    def publish_game_results(self, results_data: GameResults) -> bool:
        """
        Publish the game results data.

        Args:
            results_data: The processed game results to publish

        Returns:
            bool: True if publishing succeeded, False otherwise
        """
        return True

    def authenticate(self) -> bool:
        """
        Authenticate the publisher if required.

        Returns:
            bool: True if authentication succeeded or is not required, False otherwise
        """
        # Default implementation - no authentication required
        return True
