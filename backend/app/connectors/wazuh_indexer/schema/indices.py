from typing import Dict

from pydantic import BaseModel
from pydantic import Field


class Indices(BaseModel):
    indices_list: list
    success: bool
    message: str


class IndexConfigModel(BaseModel):
    SKIP_INDEX_NAMES: Dict[str, bool] = Field(
        default={
            "wazuh-statistics": True,
            "wazuh-monitoring": True,
            ".opendistro": True,
            ".opensearch": True,
            ".kibana": True,
            "praeco": True,
            "filebeat": True,
            ".tasks": True,
            ".task": True,
            "wazuh-states-vulnerabilities": True,
            ".plugins": True,
        },
        description="A dictionary containing index names to be skipped and their skip status.",
    )

    def is_index_skipped(self, index_name: str) -> bool:
        """
        Checks whether the given index name should be skipped.

        Args:
            index_name (str): The name of the index to check.

        Returns:
            bool: True if the index should be skipped, False otherwise.
        """
        return any(index_name.startswith(skipped) for skipped in self.SKIP_INDEX_NAMES)

    def is_valid_index(self, index_name: str) -> bool:
        """
        Checks if the index name starts with "wazuh_" and is not in the SKIP_INDEX_NAMES list.
        UPDATE: Modifying this method to return not self.is_index_skipped(index_name) and not index_name.__contains__("deflector")
        So that users whom do not use `wazuh-` index naming convention can still receive alerts.

        Args:
            index_name (str): The name of the index to check.

        Returns:
            bool: True if the index is valid, False otherwise.
        """
        # return index_name.startswith("wazuh") and not self.is_index_skipped(index_name)
        # ! Modifying the return statement to return not self.is_index_skipped(index_name) and not index_name.__contains__("deflector")
        # ! Using this so that users whom do not use `wazuh-` index naming convention can still receive alerts
        return not self.is_index_skipped(index_name) and not index_name.__contains__("deflector")
