from typing import Dict
from typing import List
from typing import Union

import requests
from loguru import logger

from app.services.Graylog.universal import UniversalService


class IndexService:
    """
    A service class for interacting with Graylog's index management API.
    """

    HEADERS: Dict[str, str] = {"X-Requested-By": "CoPilot"}
    FAILED_DETAILS_MSG: str = "Failed to collect Graylog details"
    FAILED_INDEX_MSG: str = "Failed to collect managed indices"

    def __init__(self) -> None:
        """
        Initialize the IndexService by collecting Graylog details.
        """
        self.connector_url, self.connector_username, self.connector_password = UniversalService().collect_graylog_details("Graylog")

    def _check_graylog_details(self) -> bool:
        """
        Checks if Graylog details are available.

        Returns:
            bool: True if all Graylog details are available, False otherwise.
        """
        return all([self.connector_url, self.connector_username, self.connector_password])

    def _index_exists(self, index_name: str, managed_indices: Dict) -> bool:
        """
        Checks if an index exists in Graylog.

        Args:
            index_name (str): The name of the index to check.
            managed_indices (Dict): The managed indices information.

        Returns:
            bool: True if the index exists, False otherwise.
        """
        index_names = self._extract_index_names(managed_indices)
        return index_name in index_names

    def _is_index_deleted(self, index_name: str) -> bool:
        """
        Checks if an index has been deleted from Graylog.

        Args:
            index_name (str): The name of the index to check.

        Returns:
            bool: True if the index has been deleted, False otherwise.
        """
        managed_indices = self._collect_managed_indices()
        return managed_indices["success"] and not self._index_exists(index_name, managed_indices)

    def collect_indices(self) -> Dict[str, Union[bool, str, Dict]]:
        """
        Collects the indices managed by Graylog.

        Returns:
            Dict[str, Union[bool, str, Dict]]: A dictionary containing the success status, a message, and potentially a dictionary with indices.
        """
        if not self._check_graylog_details():
            return {"message": self.FAILED_DETAILS_MSG, "success": False}

        managed_indices = self._collect_managed_indices()
        if managed_indices["success"]:
            managed_indices["index_names"] = self._extract_index_names(managed_indices)
        return managed_indices

    def _collect_managed_indices(self) -> Dict[str, Union[bool, str, Dict]]:
        """
        Fetches the indices managed by Graylog.

        Returns:
            Dict[str, Union[bool, str, Dict]]: A dictionary containing the success status, a message, and potentially a dictionary with indices.
        """
        try:
            response = requests.get(
                f"{self.connector_url}/api/system/indexer/indices",
                headers=self.HEADERS,
                auth=(self.connector_username, self.connector_password),
                verify=False,
            )
            return {"message": "Successfully collected managed indices", "success": True, "indices": response.json()["all"]["indices"]}
        except Exception as e:
            logger.error(f"{self.FAILED_INDEX_MSG}: {e}")
            return {"message": self.FAILED_INDEX_MSG, "success": False}

    def _extract_index_names(self, response: Dict[str, object]) -> List[str]:
        """
        Extracts the names of indices from the Graylog response.

        Args:
            response (Dict[str, object]): The Graylog API response.

        Returns:
            List[str]: A list of index names.
        """
        return list(response.get("indices", {}).keys())

    def delete_index(self, index_name: str) -> Dict[str, Union[bool, str]]:
        """
        Deletes a specified index from Graylog.

        Args:
            index_name (str): The name of the index to delete.

        Returns:
            Dict[str, Union[bool, str]]: A dictionary containing the success status and a message.
        """
        logger.info(f"Deleting index {index_name} from Graylog")

        if not self._check_graylog_details():
            return {"message": self.FAILED_DETAILS_MSG, "success": False}

        managed_indices = self._collect_managed_indices()
        if managed_indices["success"] and self._index_exists(index_name, managed_indices):
            self._delete_index(index_name)
            if self._is_index_deleted(index_name):
                return {"message": f"Successfully deleted index {index_name} from Graylog", "success": True}
            else:
                return {
                    "message": f"Failed to delete index {index_name} from Graylog. Please rotate the index via Graylog's WebUI and try again.",
                    "success": False,
                }

        return {"message": f"Failed to delete index {index_name} from Graylog", "success": False}

    def _delete_index(self, index_name: str) -> Dict[str, Union[bool, str]]:
        """
        Deletes a specified index from Graylog.

        Args:
            index_name (str): The name of the index to delete.

        Returns:
            Dict[str, Union[bool, str]]: A dictionary containing the success status and a message.
        """
        try:
            requests.delete(
                f"{self.connector_url}/api/system/indexer/indices/{index_name}",
                headers=self.HEADERS,
                auth=(self.connector_username, self.connector_password),
                verify=False,
            )
            return {"message": f"Successfully deleted index {index_name} from Graylog", "success": True}
        except Exception as e:
            logger.error(f"Failed to delete index {index_name} from Graylog: {e}")
            return {
                "message": f"Failed to delete index {index_name} from Graylog. Please rotate the index via Graylog's WebUI and try again.",
                "success": False,
            }
