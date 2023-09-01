import time
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

from cortex4py.api import Api
from loguru import logger

from app.services.cortex.universal import UniversalService


class AnalyzerService:
    """
    A service class for working with Cortex Analyzers.
    Provides methods to fetch, process, and run analyzers from Cortex.
    """

    def __init__(self) -> None:
        """
        Initialize the AnalyzerService instance.
        """
        self.universal_service = UniversalService("Cortex")
        self.connector_url, self.connector_api_key = self.initialize_connection_details()
        self.api: Optional[Api] = self.create_api_instance()

    def initialize_connection_details(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Initialize the connection details for Cortex.

        Returns:
            tuple: Connector URL and API key
        """
        return self.universal_service.collect_cortex_details("Cortex")

    def create_api_instance(self) -> Optional[Api]:
        """
        Create an API instance for Cortex.

        Returns:
            Optional[Api]: API instance if successful; None otherwise.
        """
        try:
            return Api(self.connector_url, self.connector_api_key)
        except Exception as e:
            logger.error(f"Error initializing Cortex API: {e}")
            return None

    def get_analyzers(self) -> Dict[str, Union[bool, str, List[str]]]:
        """
        Retrieve analyzers from Cortex.

        Returns:
            Dict: Success status, a message, and fetched analyzers.
        """
        if self.api is None:
            return {"success": False, "message": "API initialization failed"}

        analyzers = self.fetch_analyzers()
        return self.build_analyzer_response(analyzers)

    def fetch_analyzers(self) -> List[Dict]:
        """
        Fetch analyzers from Cortex.

        Returns:
            List[Dict]: List of fetched analyzers.
        """
        return self.api.analyzers.find_all({}, range="all")

    def build_analyzer_response(self, analyzers: List[Dict]) -> Dict[str, Union[bool, str, List[str]]]:
        """
        Build the response object for the fetched analyzers.

        Args:
            analyzers (List[Dict]): Fetched analyzers.

        Returns:
            Dict: Success status, message, and list of analyzer names.
        """
        try:
            analyzer_names = [analyzer.name for analyzer in analyzers]
            return {"success": True, "message": "Successfully fetched analyzers", "analyzers": analyzer_names}
        except Exception as e:
            logger.error(f"Error processing analyzers: {e}")
            return {"success": False, "message": f"Error processing analyzers: {e}"}

    def run_and_wait_for_analyzer(self, analyzer_name: str, ioc_value: str, data_type: str) -> Dict[str, Any]:
        """
        Initiates and monitors the execution of a specified Cortex analyzer.

        Args:
            analyzer_name (str): The name of the Cortex analyzer to run.
            ioc_value (str): The Indicator of Compromise (IoC) to be analyzed.
            data_type (str): The type of the IoC (e.g., "IP", "hash", "domain").

        Returns:
            Dict[str, Any]: A dictionary containing the success status, a message, and optionally the results of the analysis.
        """
        if self.api is None:
            return {"success": False, "message": "API initialization failed"}
        try:
            job = self.api.analyzers.run_by_name(
                analyzer_name,
                {
                    "data": ioc_value,
                    "dataType": data_type,
                    "tlp": 1,
                    "message": "custom message sent to analyzer",
                },
                force=1,
            )
            return self.monitor_analyzer_job(job)
        except Exception as e:
            logger.error(f"Error running analyzer {analyzer_name}: {e}")
            return {"success": False, "message": f"Error running analyzer {analyzer_name}: {e}"}

    def monitor_analyzer_job(self, job: Any) -> Dict[str, Any]:
        """
        Monitors the progress of a running Cortex analyzer job.

        Args:
            job (Any): The job object representing the running analyzer.

        Returns:
            Dict[str, Any]: A dictionary containing the success status and a message.
        """
        r_json = job.json()
        job_id = r_json["id"]
        logger.info(f"Job ID is: {job_id}")

        job_state = r_json["status"]
        timer = 0

        while job_state != "Success":
            if timer == 60:
                logger.error("Job failed to complete after 5 minutes.")
                return {"success": False, "message": "Job timed out"}
            timer += 1
            logger.info(f"Timer is: {timer}")

            if job_state == "Failure":
                error_message = r_json["errorMessage"]
                logger.error(f"Cortex Failure: {error_message}")
                return {"success": False, "message": f"Analyzer failed: {error_message}"}

            time.sleep(5)
            followup_request = self.api.jobs.get_by_id(job_id)
            r_json = followup_request.json()
            job_state = r_json["status"]

        return self.retrieve_final_report(job_id)

    def retrieve_final_report(self, job_id: str) -> Dict[str, Any]:
        """
        Retrieves the final report of a completed Cortex analyzer job.

        Args:
            job_id (str): The ID of the completed job.

        Returns:
            Dict[str, Any]: A dictionary containing the success status, a message, and the report of the analysis.
        """
        report = self.api.jobs.get_report(job_id).report
        final_report = report["full"]
        return {"success": True, "message": "Analyzer ran successfully", "report": final_report}
