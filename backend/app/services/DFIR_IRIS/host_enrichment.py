from abc import ABC
from typing import Dict
from typing import Union

import requests
from loguru import logger
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


class AssetValidator(ABC):
    """
    Base class for asset validators.

    Attributes:
        os (str): The OS to be validated.
    """

    ASSET_TYPE_ID: int = 1

    def __init__(self, os: str) -> None:
        """
        Initialize a Validator.

        Args:
            os (str): The OS to be validated.
        """
        self.os = os.lower()

    def validate(self) -> Dict[str, Union[bool, str, int]]:
        """
        Validate the OS.

        If the OS matches the type of this validator,
        the method returns a dictionary indicating success, the matching message, and the asset type id.

        Returns:
            Dict[str, Union[bool, str, int]]: The validation result.
        """
        raise NotImplementedError


class WindowsAssetValidator(AssetValidator):
    """
    Class to check if an OS is Windows.
    """

    ASSET_TYPE_ID = 9

    def validate(self) -> Dict[str, Union[bool, str, int]]:
        if "windows" in self.os:
            return {
                "success": True,
                "message": f"{self.os} is a valid Windows OS.",
                "asset_type_id": self.ASSET_TYPE_ID,
            }
        else:
            return {
                "success": False,
                "message": f"{self.os} is not a Windows OS.",
                "asset_type_id": self.ASSET_TYPE_ID,
            }


class LinuxAssetValidator(AssetValidator):
    """
    Class to check if an OS is Linux.
    """

    ASSET_TYPE_ID = 4

    def validate(self) -> Dict[str, Union[bool, str, int]]:
        if "linux" in self.os:
            return {
                "success": True,
                "message": f"{self.os} is a valid Linux OS.",
                "asset_type_id": self.ASSET_TYPE_ID,
            }
        else:
            return {
                "success": False,
                "message": f"{self.os} is not a Linux OS.",
                "asset_type_id": self.ASSET_TYPE_ID,
            }


class FirewallAssetValidator(AssetValidator):
    """
    Class to check if an OS is Firewall.
    """

    ASSET_TYPE_ID = 2

    def validate(self) -> Dict[str, Union[bool, str, int]]:
        if "firewall" in self.os:
            return {
                "success": True,
                "message": f"{self.os} is a valid Firewall OS.",
                "asset_type_id": self.ASSET_TYPE_ID,
            }
        else:
            return {
                "success": False,
                "message": f"{self.os} is not a Firewall OS.",
                "asset_type_id": self.ASSET_TYPE_ID,
            }


class UbuntuAssetValidator(AssetValidator):
    """
    Class to check if an OS is Ubuntu.
    """

    ASSET_TYPE_ID = 4

    def validate(self) -> Dict[str, Union[bool, str, int]]:
        if "ubuntu" in self.os:
            return {
                "success": True,
                "message": f"{self.os} is a valid Ubuntu OS.",
                "asset_type_id": self.ASSET_TYPE_ID,
            }
        else:
            return {
                "success": False,
                "message": f"{self.os} is not an Ubuntu OS.",
                "asset_type_id": self.ASSET_TYPE_ID,
            }


class AssetTypeResolver:
    """
    Class to iterate over asset validators and return the successful validator's asset type id.
    """

    def __init__(self, os: str):
        """
        Initialize AssetTypeResolver.

        Args:
            os (str): The OS to be validated.
        """
        self.os = os
        self.validators = [
            WindowsAssetValidator,
            LinuxAssetValidator,
            FirewallAssetValidator,
            UbuntuAssetValidator,
        ]

    def get_asset_type_id(self) -> int:
        """
        Iterate over validators and return the successful validator's asset type id.

        Returns:
            int: The asset type id.
        """
        for Validator in self.validators:
            validator = Validator(self.os)
            result = validator.validate()
            if result["success"] is True:
                return result["asset_type_id"]

        # Return default asset type id (1) if no validators succeed
        return 1
