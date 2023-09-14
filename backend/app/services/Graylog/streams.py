# from datetime import datetime
from typing import Dict
from typing import List
from typing import Union

import requests
from loguru import logger

from app.services.graylog.universal import UniversalService

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
        else:
            return {"message": "Failed to collect streams", "success": False}

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
            # If streams is None, return an empty list
            if streams is None:
                return {
                    "message": "Collected empty list of streams",
                    "success": True,
                    "streams": [],
                }
            return {
                "message": "Successfully collected streams",
                "success": True,
                "streams": streams.json(),
            }
        except Exception as e:
            logger.error(f"Failed to collect streams: {e}")
            return {"message": "Failed to collect streams", "success": False}

    def pause_stream(self, stream_id: str) -> Dict[str, Union[bool, str]]:
        """
        Pauses a stream in Graylog.

        Args:
            stream_id (str): The ID of the stream to pause.

        Returns:
            dict: A dictionary containing the success status and a message.
        """
        if self.connector_url is None or self.connector_username is None or self.connector_password is None:
            return {"message": "Failed to collect Graylog details", "success": False}

        pause_stream = self._pause_stream(stream_id)

        if pause_stream["success"]:
            return pause_stream

    def _pause_stream(self, stream_id: str) -> Dict[str, Union[bool, str]]:
        """
        Pauses a stream in Graylog.

        Args:
            stream_id (str): The ID of the stream to pause.

        Returns:
            dict: A dictionary containing the success status and a message.
        """
        try:
            requests.post(
                f"{self.connector_url}/api/streams/{stream_id}/pause",
                headers=self.HEADERS,
                auth=(self.connector_username, self.connector_password),
                verify=False,
            )
            return {
                "message": "Successfully paused stream",
                "success": True,
            }
        except Exception as e:
            logger.error(f"Failed to pause stream: {e}")
            return {"message": "Failed to pause stream", "success": False}

    def resume_stream(self, stream_id: str) -> Dict[str, Union[bool, str]]:
        """
        Resumes a stream in Graylog.

        Args:
            stream_id (str): The ID of the stream to resume.

        Returns:
            dict: A dictionary containing the success status and a message.
        """
        if self.connector_url is None or self.connector_username is None or self.connector_password is None:
            return {"message": "Failed to collect Graylog details", "success": False}

        resume_stream = self._resume_stream(stream_id)

        if resume_stream["success"]:
            return resume_stream

    def _resume_stream(self, stream_id: str) -> Dict[str, Union[bool, str]]:
        """
        Resumes a stream in Graylog.

        Args:
            stream_id (str): The ID of the stream to resume.

        Returns:
            dict: A dictionary containing the success status and a message.
        """
        try:
            requests.post(
                f"{self.connector_url}/api/streams/{stream_id}/resume",
                headers=self.HEADERS,
                auth=(self.connector_username, self.connector_password),
                verify=False,
            )
            return {
                "message": "Successfully resumed stream",
                "success": True,
            }
        except Exception as e:
            logger.error(f"Failed to resume stream: {e}")
            return {"message": "Failed to resume stream", "success": False}
