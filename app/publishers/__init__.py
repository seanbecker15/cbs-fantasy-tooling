from abc import ABC, abstractmethod
from typing import Any, Dict
from storage import ResultsData


class Publisher(ABC):
    """Abstract base class for all publishers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    @abstractmethod
    def publish(self, results_data: ResultsData) -> bool:
        """
        Publish the results data.
        
        Args:
            results_data: The processed results to publish
            
        Returns:
            bool: True if publishing succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate that the configuration is sufficient for this publisher.

        Returns:
            bool: True if configuration is valid, False otherwise
        """
        pass

    def test_authentication(self) -> bool:
        """
        Test that the publisher can authenticate successfully before scraping.

        This is called before the scraper runs to fail fast if authentication
        will fail. Publishers that require authentication should override this
        method.

        Returns:
            bool: True if authentication succeeds or is not required, False otherwise
        """
        # Default implementation - no authentication required
        return True