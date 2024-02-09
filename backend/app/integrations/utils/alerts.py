import ipaddress
import re
from abc import ABC
from typing import Dict
from typing import Optional
from typing import Union

import httpx
import regex
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.utils.schema import ShufflePayload
from app.utils import get_customer_alert_settings


#################### ! DFIR IRIS ASSET VALIDATOR ! ####################
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


#################### ! DFIR IRIS ASSET VALIDATOR END ! ####################


#################### ! DFIR IRIS IOC VALIDATOR ! ##########################


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


#################### ! DFIR IRIS IOC VALIDATOR END ! ##########################


async def get_asset_type_id(os: str) -> int:
    """
    Use AssetTypeResolver to determine the asset type ID to set within DFIR-IRIS.

    Parameters
    ----------
    os : str
        The operating system (OS) string used to resolve the asset type ID.

    Returns
    -------
    int
        The ID corresponding to the asset type.
    """
    asset_resolver = AssetTypeResolver(os)
    return asset_resolver.get_asset_type_id()


async def validate_ioc_type(ioc_value: str) -> str:
    """
    Validate IoC type using validators.

    Parameters
    ----------
    ioc_value : str
        The value to validate the IoC type.

    Returns
    -------
    str
        The type of the IoC. Returns None if validation fails.
    """
    validators = [IPv4AddressValidator, HashValidator, DomainValidator]
    ioc_type = None

    for Validator in validators:
        validator = Validator(ioc_value)
        result = validator.validate()

        if result["success"]:
            ioc_type = result["ioc_type"]
            break

    if ioc_type is None:
        logger.error("Failed to validate IoC value.")
    return ioc_type


async def send_to_shuffle(payload: ShufflePayload, session: AsyncSession) -> bool:
    """
    Sends payload to Shuffle listening Webhook asynchronously using httpx.
    """
    logger.info(f"Sending {payload} to Shuffle Webhook.")
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(
                (
                    await get_customer_alert_settings(
                        customer_code=payload.customer_code,
                        session=session,
                    )
                ).shuffle_endpoint,
                json=payload.to_dict(),
            )

        return response.status_code == 200

    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error: {e}",
        )


# def send_to_wazuh(msg) -> None:
#     # Uncomment when doing dev work
#     # logger.info(f"Sending {msg} to Wazuh Socket.")
#     # return
#     socketAddr = "/var/ossec/queue/sockets/queue"
#     from socket import AF_UNIX
#     from socket import SOCK_DGRAM
#     from socket import socket

#     if isinstance(msg, str):
#         try:
#             msg = json.loads(msg)
#         except json.JSONDecodeError as e:
#             logger.error(f"Invalid JSON string: {e}")
#             raise HTTPException(
#                 status_code=400,
#                 detail="Invalid JSON string.",
#             )
#     elif not isinstance(msg, dict):
#         logger.error("Invalid message type. Expected str or dict.")
#         raise HTTPException(
#             status_code=400,
#             detail="Invalid message type. Expected str or dict.",
#         )

#     try:
#         integration = msg["integration"]
#     except KeyError as e:
#         logger.error(f"KeyError: {e}")
#         raise HTTPException(
#             status_code=400,
#             detail="Invalid message format. Could not extract 'integration'.",
#         )

#     socketAddr = "/var/ossec/queue/sockets/queue"

#     try:
#         msg_str = json.dumps(msg)
#         logger.info(f"Sending {msg_str} to {socketAddr} socket.")
#         message = f"1:{integration}:{msg_str}"
#         sock = socket(AF_UNIX, SOCK_DGRAM)
#         sock.connect(socketAddr)
#         sock.send(message.encode())
#         sock.close()
#         logger.info(f"Message sent to {socketAddr} socket.")
#         return {"success": True, "message": "Message sent to Wazuh Socket."}
#     except Exception as e:
#         logger.error(f"Error: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error: {e}",
#         )
