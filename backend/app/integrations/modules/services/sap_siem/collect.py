import httpx
from loguru import logger

from app.integrations.modules.schema.sap_siem import CollectSapSiemRequest
from app.integrations.modules.schema.sap_siem import InvokeSapSiemAnalysis


async def post_to_copilot_sap_module_collect(data: CollectSapSiemRequest):
    """
    Send a POST request to the copilot-sap-module Docker container.

    Args:
        data (CollectHuntress): The data to send to the copilot-sap-module Docker container.
    """
    logger.info(f"Sending POST request to http://copilot-sap-module/collect with data: {data.dict()}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://copilot-sap-module/sap-siem/collect",
                json=data.to_dict(),
                timeout=120,
            )
            logger.info(f"Response from copilot-sap-module: {response.json()}")
        except httpx.RequestError as e:
            logger.error(f"An error occurred while sending the POST request to copilot-sap-module: {e}")
    return None


async def post_to_copilot_sap_module_sap_siem_successful_user_login_with_different_ip(data: InvokeSapSiemAnalysis):
    """
    Send a POST request to the copilot-sap-module Docker container.

    Args:
        data (InvokeSapSiemAnalysis): The data to send to the copilot-sap-module Docker container.
    """
    logger.info(
        f"Sending POST request to http://copilot-sap-module/sap-siem/same_user_failed_login_from_different_ip with data: {data.dict()}",
    )
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://copilot-sap-module/sap-siem/successful_user_login_with_different_ip",
                json=data.dict(),
                timeout=120,
            )
            logger.info(f"Response from copilot-sap-module: {response.json()}")
        except httpx.RequestError as e:
            logger.error(f"An error occurred while sending the POST request to copilot-sap-module: {e}")
    return None


async def post_to_copilot_sap_module_same_user_failed_login_from_different_ip(data: InvokeSapSiemAnalysis):
    """
    Send a POST request to the copilot-sap-module Docker container.

    Args:
        data (InvokeSapSiemAnalysis): The data to send to the copilot-sap-module Docker container.
    """
    logger.info(
        f"Sending POST request to http://copilot-sap-module/sap-siem/same_user_failed_login_from_different_ip with data: {data.dict()}",
    )
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://copilot-sap-module/sap-siem/same_user_failed_login_from_different_ip",
                json=data.dict(),
                timeout=120,
            )
            logger.info(f"Response from copilot-sap-module: {response.json()}")
        except httpx.RequestError as e:
            logger.error(f"An error occurred while sending the POST request to copilot-sap-module: {e}")
    return None


async def post_to_copilot_sap_module_same_user_failed_login_from_different_geo_location(data: InvokeSapSiemAnalysis):
    """
    Send a POST request to the copilot-sap-module Docker container.

    Args:
        data (InvokeSapSiemAnalysis): The data to send to the copilot-sap-module Docker container.
    """
    logger.info(
        f"Sending POST request to http://copilot-sap-module/sap-siem/same_user_failed_login_from_different_geo_location with data: {data.dict()}",
    )
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://copilot-sap-module/sap-siem/same_user_failed_login_from_different_geo_location",
                json=data.dict(),
                timeout=120,
            )
            logger.info(f"Response from copilot-sap-module: {response.json()}")
        except httpx.RequestError as e:
            logger.error(f"An error occurred while sending the POST request to copilot-sap-module: {e}")
    return None


async def post_to_copilot_sap_module_same_user_successful_login_from_different_geo_location(data: InvokeSapSiemAnalysis):
    """
    Send a POST request to the copilot-sap-module Docker container.

    Args:
        data (InvokeSapSiemAnalysis): The data to send to the copilot-sap-module Docker container.
    """
    logger.info(
        f"Sending POST request to http://copilot-sap-module/sap-siem/same_user_successful_login_from_different_geo_location with data: {data.dict()}",
    )
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://copilot-sap-module/sap-siem/same_user_successful_login_from_different_geo_location",
                json=data.dict(),
                timeout=120,
            )
            logger.info(f"Response from copilot-sap-module: {response.json()}")
        except httpx.RequestError as e:
            logger.error(f"An error occurred while sending the POST request to copilot-sap-module: {e}")
    return None


async def post_to_copilot_sap_module_brute_force_failed_logins_multiple_ips(data: InvokeSapSiemAnalysis):
    """
    Send a POST request to the copilot-sap-module Docker container.

    Args:
        data (InvokeSapSiemAnalysis): The data to send to the copilot-sap-module Docker container.
    """
    logger.info(
        f"Sending POST request to http://copilot-sap-module/sap-siem/brute_force_failed_logins_multiple_ips with data: {data.dict()}",
    )
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://copilot-sap-module/sap-siem/brute_force_failed_logins_multiple_ips",
                json=data.dict(),
                timeout=120,
            )
            logger.info(f"Response from copilot-sap-module: {response.json()}")
        except httpx.RequestError as e:
            logger.error(f"An error occurred while sending the POST request to copilot-sap-module: {e}")
    return None


async def post_to_copilot_sap_module_brute_force_failed_logins_same_ip(data: InvokeSapSiemAnalysis):
    """
    Send a POST request to the copilot-sap-module Docker container.

    Args:
        data (InvokeSapSiemAnalysis): The data to send to the copilot-sap-module Docker container.
    """
    logger.info(f"Sending POST request to http://copilot-sap-module/sap-siem/brute_force_failed_logins_same_ip with data: {data.dict()}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://copilot-sap-module/sap-siem/brute_force_failed_logins_same_ip",
                json=data.dict(),
                timeout=120,
            )
            logger.info(f"Response from copilot-sap-module: {response.json()}")
        except httpx.RequestError as e:
            logger.error(f"An error occurred while sending the POST request to copilot-sap-module: {e}")
    return None


async def post_to_copilot_sap_module_successful_login_after_multiple_failed_logins(data: InvokeSapSiemAnalysis):
    """
    Send a POST request to the copilot-sap-module Docker container.

    Args:
        data (InvokeSapSiemAnalysis): The data to send to the copilot-sap-module Docker container.
    """
    logger.info(
        f"Sending POST request to http://copilot-sap-module/sap-siem/successful_login_after_multiple_failed_logins with data: {data.dict()}",
    )
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://copilot-sap-module/sap-siem/successful_login_after_multiple_failed_logins",
                json=data.dict(),
                timeout=120,
            )
            logger.info(f"Response from copilot-sap-module: {response.json()}")
        except httpx.RequestError as e:
            logger.error(f"An error occurred while sending the POST request to copilot-sap-module: {e}")
    return None
