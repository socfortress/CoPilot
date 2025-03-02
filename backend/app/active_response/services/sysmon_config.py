from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import xml.etree.ElementTree as ET
from pydantic import BaseModel
from xml.parsers.expat import ExpatError
from loguru import logger
import aiohttp
import os
import tempfile
from urllib.parse import urlparse
from app.utils import get_connector_attribute
from typing import Tuple, Optional

from app.active_response.schema.sysmon_config import SysmonConfigDeploymentResult


from app.data_store.data_store_operations import upload_sysmon_config, download_sysmon_config, list_sysmon_configs


async def validate_sysmon_config(xml_content: str) -> None:
    """
    Validate a Sysmon configuration XML string.

    Args:
        xml_content: The XML content as a string

    Raises:
        HTTPException: If validation fails
    """
    try:
        root = ET.fromstring(xml_content)

        # Verify root element
        if root.tag != 'Sysmon':
            raise HTTPException(status_code=400, detail="Root element must be 'Sysmon'")

        # Verify EventFiltering element
        event_filtering = root.find("EventFiltering")
        if event_filtering is None:
            raise HTTPException(status_code=400, detail="Missing required 'EventFiltering' element")

        # Check for direct text content in EventFiltering (catches "adsf" issue)
        if event_filtering.text and event_filtering.text.strip():
            raise HTTPException(
                status_code=400,
                detail="Invalid text content found directly in EventFiltering element"
            )

        # Check for RuleGroup elements
        rule_groups = event_filtering.findall("RuleGroup")
        if not rule_groups:
            raise HTTPException(
                status_code=400,
                detail="EventFiltering must contain at least one RuleGroup"
            )

        # Check that each RuleGroup has required attributes
        for rule_group in rule_groups:
            if not rule_group.attrib.get("groupRelation"):
                raise HTTPException(
                    status_code=400,
                    detail="RuleGroup must have 'groupRelation' attribute"
                )

    except ET.ParseError as e:
        raise HTTPException(status_code=400, detail=f"Invalid XML syntax: {str(e)}")

async def check_config_exists(customer_code: str) -> bool:
    """Check if a sysmon config exists for the given customer"""
    try:
        await download_sysmon_config(customer_code)
        return True
    except HTTPException as e:
        if e.status_code == 404:
            return False
        raise


async def validate_sysmon_config(xml_content: str) -> None:
    """Validate a Sysmon configuration XML string."""
    try:
        root = ET.fromstring(xml_content)

        # Verify root element
        if root.tag != 'Sysmon':
            raise HTTPException(status_code=400, detail="Root element must be 'Sysmon'")

        # Verify EventFiltering element
        event_filtering = root.find("EventFiltering")
        if event_filtering is None:
            raise HTTPException(status_code=400, detail="Missing required 'EventFiltering' element")

        # Check for direct text content in EventFiltering
        if event_filtering.text and event_filtering.text.strip():
            raise HTTPException(
                status_code=400,
                detail="Invalid text content found directly in EventFiltering element"
            )

        # Check for RuleGroup elements
        rule_groups = event_filtering.findall("RuleGroup")
        if not rule_groups:
            raise HTTPException(
                status_code=400,
                detail="EventFiltering must contain at least one RuleGroup"
            )

        # Check that each RuleGroup has required attributes
        for rule_group in rule_groups:
            if not rule_group.attrib.get("groupRelation"):
                raise HTTPException(
                    status_code=400,
                    detail="RuleGroup must have 'groupRelation' attribute"
                )

    except ET.ParseError as e:
        raise HTTPException(status_code=400, detail=f"Invalid XML syntax: {str(e)}")


# async def check_config_exists(customer_code: str) -> bool:
#     """Check if a sysmon config exists for the given customer."""
#     try:
#         await download_sysmon_config(customer_code)
#         return True
#     except HTTPException as e:
#         if e.status_code == 404:
#             return False
#         raise

async def check_config_exists(customer_code: str) -> bool:
    """
    Check if a sysmon config exists for the given customer.
    Creates the bucket if it doesn't exist.
    """
    from app.data_store.data_store_session import create_session

    bucket_name = "sysmon-configs"
    object_name = f"{customer_code}/sysmon_config.xml"

    try:
        # Get MinIO client
        client = await create_session()

        # Create bucket if it doesn't exist
        if not await client.bucket_exists(bucket_name):
            logger.info(f"Bucket {bucket_name} doesn't exist. Creating it.")
            await client.make_bucket(bucket_name)
            return False

        # Check if object exists directly using stat_object
        try:
            await client.stat_object(bucket_name, object_name)
            logger.info(f"Found existing sysmon config for customer {customer_code}")
            return True
        except Exception as e:
            # If stat_object fails, the file doesn't exist
            logger.info(f"No existing sysmon config found for customer {customer_code}")
            return False

    except Exception as e:
        logger.error(f"Error checking if config exists for customer {customer_code}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error checking config existence: {str(e)}"
        )


async def fetch_sysmon_config(customer_code: str) -> bytes:
    """Fetch a customer's sysmon config from MinIO storage."""
    try:
        config_data = await download_sysmon_config(customer_code)
        logger.info(f"Successfully fetched Sysmon config for {customer_code} from storage")
        return config_data
    except Exception as e:
        logger.error(f"Failed to fetch Sysmon config for {customer_code}: {str(e)}")
        raise


async def save_to_temp_file(data: bytes) -> str:
    """Save binary data to a temporary file and return the path."""
    temp_fd, temp_path = tempfile.mkstemp(suffix='.xml')
    try:
        with os.fdopen(temp_fd, 'wb') as temp_file:
            temp_file.write(data)
        logger.info(f"Saved data to temporary file: {temp_path}")
        return temp_path
    except Exception as e:
        # Clean up if we fail to write
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.error(f"Failed to save to temporary file: {str(e)}")
        raise


async def get_wazuh_endpoint(session: AsyncSession) -> str:
    """Get the Wazuh API endpoint for deploying sysmon configs."""
    # Get the base URL from connector
    wazuh_api_base_url = await get_connector_attribute(
        column_name="connector_url",
        connector_name="Wazuh-Manager",
        session=session
    )

    # Parse the URL to extract hostname
    parsed_url = urlparse(wazuh_api_base_url)
    hostname = parsed_url.netloc.split(':')[0]

    # Create endpoint with correct port and path
    endpoint = f"http://{hostname}:5003/provision_worker/sysmon-config"
    logger.info(f"Constructed Wazuh API endpoint: {endpoint}")

    return endpoint


async def upload_to_wazuh(
    endpoint: str,
    customer_code: str,
    file_path: str
) -> Tuple[bool, dict, Optional[str]]:
    """Upload a sysmon config file to the Wazuh master."""
    # Replace spaces with underscores
    wazuh_customer_code = customer_code.replace(" ", "_")

    logger.info(f"Uploading Sysmon config for customer {wazuh_customer_code} to {endpoint}")

    async with aiohttp.ClientSession() as http_session:
        # Create form data
        form_data = aiohttp.FormData()
        form_data.add_field('customer_code', wazuh_customer_code)

        # Add the file
        with open(file_path, 'rb') as file_to_upload:
            form_data.add_field(
                'sysmon_config',
                file_to_upload,
                filename="sysmon_config.xml",
                content_type='application/xml'
            )

            # Send the POST request
            async with http_session.post(endpoint, data=form_data) as response:
                if response.status == 200:
                    response_data = await response.json()
                    return True, response_data, None
                else:
                    error_text = await response.text()
                    return False, {}, error_text


async def deploy_sysmon_config_to_worker(
    customer_code: str,
    session: AsyncSession
) -> SysmonConfigDeploymentResult:
    """
    Fetch and deploy a customer's sysmon config to the Wazuh master.

    Args:
        customer_code: The customer code to deploy config for
        session: Database session for connector lookup

    Returns:
        SysmonConfigDeploymentResult: Results of the deployment operation
    """
    temp_path = None

    try:
        # Step 1: Fetch the config file
        try:
            config_data = await fetch_sysmon_config(customer_code)
        except Exception as fetch_error:
            return SysmonConfigDeploymentResult(
                success=False,
                message=f"Failed to fetch Sysmon config for {customer_code}",
                customer_code=customer_code,
                error_detail=str(fetch_error)
            )

        # Step 2: Save to temporary file
        try:
            temp_path = await save_to_temp_file(config_data)
        except Exception as temp_error:
            return SysmonConfigDeploymentResult(
                success=False,
                message=f"Failed to create temporary file",
                customer_code=customer_code,
                error_detail=str(temp_error)
            )

        # Step 3: Get Wazuh endpoint
        try:
            endpoint = await get_wazuh_endpoint(session)
        except Exception as endpoint_error:
            return SysmonConfigDeploymentResult(
                success=False,
                message=f"Failed to get Wazuh endpoint",
                customer_code=customer_code,
                error_detail=str(endpoint_error)
            )

        # Step 4: Upload to Wazuh
        success, response_data, error_text = await upload_to_wazuh(
            endpoint, customer_code, temp_path
        )

        if success:
            logger.info(f"Successfully deployed Sysmon config to Wazuh for {customer_code}")
            return SysmonConfigDeploymentResult(
                success=True,
                message=f"Sysmon config successfully deployed for {customer_code}",
                customer_code=customer_code,
                worker_success=response_data.get("success", True),
                worker_message=response_data.get("message", "Deployed successfully")
            )
        else:
            logger.error(f"Failed to deploy Sysmon config to Wazuh: {error_text}")
            return SysmonConfigDeploymentResult(
                success=False,
                message=f"Error from Wazuh master when deploying Sysmon config",
                customer_code=customer_code,
                error_detail=error_text
            )

    except Exception as e:
        error_msg = f"Error deploying Sysmon config: {str(e)}"
        logger.error(error_msg)
        return SysmonConfigDeploymentResult(
            success=False,
            message=f"Exception occurred during Sysmon config deployment",
            customer_code=customer_code,
            error_detail=str(e)
        )

    finally:
        # Clean up the temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.debug(f"Cleaned up temporary file: {temp_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temporary file {temp_path}: {str(cleanup_error)}")
