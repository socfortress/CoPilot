from typing import Dict, List, Union, Optional
from cortex4py.api import Api
from loguru import logger
from app.services.cortex.universal import UniversalService

class AnalyzerService:
    """
    A service class that encapsulates the logic for working with Cortex Analyzers.
    This class provides methods to fetch and process analyzers from Cortex.
    """

    def __init__(self) -> None:
        """
        Initialize the AnalyzerService instance.

        The constructor initializes the UniversalService object, fetches the necessary
        connection details for Cortex, and creates an API instance for further interactions.
        """
        self.universal_service: UniversalService = UniversalService("Cortex")
        self.connector_url: str
        self.connector_api_key: str
        self.connector_url, self.connector_api_key = self.universal_service.collect_cortex_details("Cortex")
        self.api: Optional[Api] = self.create_api_instance()

    def create_api_instance(self) -> Optional[Api]:
        """
        Create an API instance for connecting to Cortex.

        Returns:
            Optional[Api]: An Api object for Cortex interactions if successful, None otherwise.
        """
        try:
            return Api(self.connector_url, self.connector_api_key)
        except Exception as e:
            logger.error(f"Error initializing Cortex API: {e}")
            return None

    def fetch_analyzers(self) -> List[Dict]:
        """
        Fetch the list of analyzers from Cortex.

        Returns:
            List[Dict]: A list of dictionaries, each representing an analyzer.
        """
        if self.api is None:
            return []
        return self.api.analyzers.find_all({}, range='all')

    def extract_analyzer_names(self, analyzers: List[Dict]) -> List[str]:
        """
        Extract the names of the analyzers from the fetched analyzer data.

        Args:
            analyzers (List[Dict]): A list of dictionaries, each representing an analyzer.

        Returns:
            List[str]: A list of analyzer names.
        """
        return [analyzer.name for analyzer in analyzers]

    def get_analyzers(self) -> Dict[str, Union[bool, str, List[str]]]:
        """
        Retrieve the list of analyzers from Cortex.

        This function fetches the analyzers, extracts their names, and returns a
        dictionary containing the success status and the list of analyzers.

        Returns:
            Dict[str, Union[bool, str, List[str]]]: A dictionary containing the success status,
                a message, and the list of fetched analyzers.
        """
        try:
            logger.info("Collecting analyzers from Cortex")
            analyzers = self.fetch_analyzers()
            all_analyzers = self.extract_analyzer_names(analyzers)

            return {
                "success": True,
                "message": "Successfully collected analyzers from Cortex",
                "analyzers": all_analyzers
            }
        except Exception as e:
            logger.error(f"Error collecting analyzers from Cortex: {e}")
            return {
                "success": False,
                "message": f"Error collecting analyzers from Cortex: {e}"
            }
