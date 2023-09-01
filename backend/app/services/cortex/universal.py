import ipaddress
from typing import Optional
from typing import Tuple

import regex
from loguru import logger

from app.models.connectors import Connector
from app.models.connectors import connector_factory

HASH_PATTERN = r"^[a-fA-F\d]{64}$"
DOMAIN_PATTERN = r"^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$"
HASH_REGEX = regex.compile(HASH_PATTERN, regex.IGNORECASE)
DOMAIN_REGEX = regex.compile(DOMAIN_PATTERN, regex.IGNORECASE)


class UniversalService:
    """
    A service class that encapsulates the logic for interfacing with Cortex. This class handles tasks like creating a session,
    fetching and parsing data, and retrieving connector details.
    """

    def __init__(self, connector_name: str) -> None:
        """
        Initializes the UniversalService by collecting Cortex details associated with the specified connector name.

        Args:
            connector_name (str): The name of the Cortex connector.
        """
        self.connector_url, self.connector_api_key = self.collect_cortex_details(
            connector_name,
        )

    def collect_cortex_details(
        self,
        connector_name: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Collects the details of the DFIR-IRIS connector.

        Args:
            connector_name (str): The name of the DFIR-IRIS connector.

        Returns:
            tuple: A tuple containing the connection URL and API key. If the connection is not successful, both elements of the tuple are
            None.
        """
        connector_instance = connector_factory.create(connector_name, connector_name)
        connection_successful = connector_instance.verify_connection()
        if connection_successful:
            connection_details = Connector.get_connector_info_from_db(connector_name)
            return (
                connection_details.get("connector_url"),
                connection_details.get("connector_api_key"),
            )
        else:
            return None, None

    def is_valid_datatype(self, value: str) -> Tuple[bool, str]:
        """
        Check if input value is a valid data type - IPv4, hash, or domain.

        Args:
            value (str): The input value to check.

        Returns:
            tuple: A tuple containing a boolean indicating whether the input value is a valid data type and a string indicating the data type.
        """
        if self._is_valid_ipv4(value):
            return True, "ip"
        elif self._is_valid_hash(value):
            return True, "hash"
        elif self._is_valid_domain(value):
            return True, "domain"
        else:
            return False, "Unknown"

    def _is_valid_ipv4(self, value: str) -> bool:
        """
        Check if input value is a valid IPv4 address.

        Args:
            value (str): The input value to check.

        Returns:
            bool: True if the input value is a valid IPv4 address, False otherwise.
        """
        try:
            ipaddress.IPv4Address(value)
            return True
        except ValueError:
            return False

    def _is_valid_hash(self, value: str) -> bool:
        """
        Check if input value is a valid hash.

        Args:
            value (str): The input value to check.

        Returns:
            bool: True if the input value is a valid hash, False otherwise.
        """
        try:
            return bool(HASH_REGEX.match(value))
        except Exception as e:
            logger.error(f"Error validating hash: {e}")
            return False

    def _is_valid_domain(self, value: str) -> bool:
        """
        Check if input value is a valid domain.

        Args:
            value (str): The input value to check.

        Returns:
            bool: True if the input value is a valid domain, False otherwise.
        """
        try:
            return bool(DOMAIN_REGEX.match(value))
        except Exception as e:
            logger.error(f"Error validating domain: {e}")
            return False
