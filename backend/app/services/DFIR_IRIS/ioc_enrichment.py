import ipaddress
import re
from abc import ABC
from typing import Dict
from typing import Optional
from typing import Union

import regex
from loguru import logger


class IoCValidator(ABC):
    """
    Base class for validators.

    Attributes:
        value (str): The value to be validated.
    """

    PATTERN: Optional[str] = None  # type: ignore
    IOC_TYPE: Optional[int] = None  # type: ignore

    def __init__(self, value: str) -> None:
        """
        Initialize a Validator.

        Args:
            value (str): The value to be validated.
        """
        self.value = value

    def validate(self) -> Dict[str, Union[bool, str, int]]:
        """
        Validate the value.

        If the value matches the pattern,
        the method returns a dictionary indicating success, the matching message, and the IOC type.

        Returns:
            Dict[str, Union[bool, str, int]]: The validation result.
        """
        logger.info(f"Validating {self.value} against {self.PATTERN}.")
        if self.PATTERN and regex.match(self.PATTERN, self.value, re.IGNORECASE):
            return {
                "success": True,
                "message": f"{self.value} matches the pattern.",
                "ioc_type": self.IOC_TYPE,
            }
        else:
            return {
                "success": False,
                "message": f"{self.value} does not match the pattern.",
                "ioc_type": self.IOC_TYPE,
            }


class IPv4AddressValidator(IoCValidator):
    """
    Class to check if a string is a valid IPv4 address.
    """

    IOC_TYPE = 76

    def validate(self) -> Dict[str, Union[bool, str, int]]:
        """
        Validate if the given value is a valid IPv4 address.

        Returns:
            dict: A dictionary containing success status, message, and the associated IoC type.
        """
        try:
            # if the value is like this `162.159.133.233|443` strip the port
            if "|" in self.value:
                self.value = self.value.split("|")[0]
            logger.info(f"Validating {self.value} as an IPv4 address.")
            ipaddress.IPv4Address(self.value)
            return {
                "success": True,
                "message": f"{self.value} is a valid IPv4 address.",
                "ioc_type": self.IOC_TYPE,
            }
        except ValueError:
            return {
                "success": False,
                "message": f"{self.value} is not a valid IPv4 address.",
                "ioc_type": self.IOC_TYPE,
            }


class HashValidator(IoCValidator):
    """
    Class to check if a string is a valid SHA256 hash.
    """

    PATTERN = r"^[a-fA-F\d]{64}$"
    IOC_TYPE = 113


class DomainValidator(IoCValidator):
    """
    Class to check if a string is a valid domain name.
    """

    PATTERN = r"^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$"
    IOC_TYPE = 20
