# from datetime import datetime
from typing import Dict
from typing import List
from typing import Union

import requests
from loguru import logger

from app.services.Graylog.universal import UniversalService

# from typing import List


class StreamsService:
    """
    A service class that encapsulates the logic for pulling pipeline data from Graylog.
    """

    HEADERS: Dict[str, str] = {"X-Requested-By": "CoPilot"}

    def __init__(self):
        """
        Initializes the InputsService by collecting Graylog details.
        """
        (
            self.connector_url,
            self.connector_username,
            self.connector_password,
        ) = UniversalService().collect_graylog_details("Graylog")

    def collect_streams(
        self,
    ) -> Dict[str, Union[bool, str, List[Dict[str, Union[str, int]]]]]:
        """
        Collects the streams that are managed by Graylog.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially a list of streams.
        """
        if self.connector_url is None or self.connector_username is None or self.connector_password is None:
            return {"message": "Failed to collect Graylog details", "success": False}

        streams = self._collect_streams()

        if streams["success"]:
            return streams

    def _collect_streams(
        self,
    ) -> Dict[str, Union[bool, str, List[Dict[str, Union[str, int]]]]]:
        """
        Collects the streams that are managed by Graylog.

        Returns:
            dict: A dictionary containing the success status, a message, and potentially a list of streams.
        """
        try:
            streams = requests.get(
                f"{self.connector_url}/api/streams",
                headers=self.HEADERS,
                auth=(self.connector_username, self.connector_password),
                verify=False,
            )
            return {
                "message": "Successfully collected streams",
                "success": True,
                "streams": streams.json(),
            }
        except Exception as e:
            logger.error(f"Failed to collect streams: {e}")
            return {"message": "Failed to collect streams", "success": False}
