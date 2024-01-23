from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
import datetime
import os
import json
import hashlib
import hashlib
import io
from zipfile import ZipFile
import hmac
import requests
import base64
import aiofiles
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
import uuid

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.integrations.mimecast.schema.mimecast import MimecastRequest, MimecastResponse, MimecastAuthKeys, MimecastAPIEndpointResponse
from app.integrations.alert_escalation.services.general_alert import create_alert
from app.integrations.routes import get_customer_integrations_by_customer_code, find_customer_integration
from app.integrations.schema import CustomerIntegrationsResponse, CustomerIntegrations
from typing import Dict
from app.integrations.utils.collection import send_get_request, send_post_request

async def get_checkpoint_filename(customer_code: str):
    """
    Retrieves the checkpoint filename for the Mimecast integration.
    If the checkpoint file does not exist, it will be created asynchronously.
    """
    # Relative path from the current script to the checkpoint directory
    checkpoint_directory = os.path.join(os.path.dirname(__file__), '..', 'checkpoint')
    checkpoint_filename = os.path.join(checkpoint_directory, f"mimecast_{customer_code}.checkpoint")

    # Normalize the path to remove relative path components
    checkpoint_filename = os.path.normpath(checkpoint_filename)

    # Create the checkpoint directory if it does not exist
    if not os.path.exists(checkpoint_directory):
        os.makedirs(checkpoint_directory)

    # Create the checkpoint file if it does not exist
    if not os.path.exists(checkpoint_filename):
        async with aiofiles.open(checkpoint_filename, "w") as f:
            await f.write("")

    return checkpoint_filename

async def get_log_file_path(customer_code: str):
    """
    Retrieves the log file path for the Mimecast integration and customer.

    Args:
        customer_code (str): The code of the customer.

    Returns:
        str: The log file path for the Mimecast integration and customer.
    """
    # Relative path from the current script to the log directory
    log_directory = os.path.join(os.path.dirname(__file__), '..', 'logs')
    # Normalize the path to remove relative path components
    log_directory = os.path.abspath(log_directory)

    # Create a directory for the customer if it does not exist
    customer_log_directory = os.path.join(log_directory, customer_code)
    if not os.path.exists(customer_log_directory):
        os.makedirs(customer_log_directory)

    # Return the customer directory
    return customer_log_directory


async def read_file(filename: str):
    """
    Reads the contents of the given file.
    """
    async with aiofiles.open(filename, "r") as f:
        return await f.read()

async def get_hdr_date():
    return datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S UTC")

async def get_base_url(mimecast_auth_keys: MimecastAuthKeys) -> MimecastAPIEndpointResponse:
    """
    Retrieves the base URL for the Mimecast integration.
    """
    post_body = dict()
    post_body["data"] = [{}]
    post_body["data"][0]["emailAddress"] = mimecast_auth_keys.EMAIL_ADDRESS

    # Create variables required for request headers
    request_id = str(uuid.uuid4())
    request_date = await get_hdr_date()
    headers = {
        "x-mc-app-id": mimecast_auth_keys.APP_ID,
        "x-mc-req-id": request_id,
        "x-mc-date": request_date,
    }
    try:
        response = await send_post_request(
            endpoint="https://api.mimecast.com/api/login/discover-authentication",
            headers=headers,
            data=post_body,
        )
        if response['success'] == True:
            logger.info(f"Successfully retrieved base URL for Mimecast integration. Response: {response}")
            return MimecastAPIEndpointResponse(**response)
        else:
            logger.error(f"Unable to retrieve base URL for Mimecast integration. Response: {response}")
            raise HTTPException(status_code=400, detail="Unable to retrieve base URL for Mimecast integration.")
    except Exception as e:
        logger.error(f"Unable to retrieve base URL for Mimecast integration. Exception: {e}")
        raise HTTPException(status_code=400, detail="Unable to retrieve base URL for Mimecast integration.")

async def get_mta_siem_logs(checkpoint_filename: str, base_url: str, auth_keys: MimecastAuthKeys):
    """
    Retrieves the MTA SIEM logs from the Mimecast integration.
    """
    # Build post body for request
    post_body = dict()
    post_body["data"] = [{}]
    post_body["data"][0]["type"] = "MTA"
    post_body["data"][0]["compress"] = True
    post_body["data"][0]["token"] = await read_file(checkpoint_filename)


    # Create variables required for request headers
    request_id = str(uuid.uuid4())
    request_date = await get_hdr_date()

    unsigned_auth_header = "{date}:{req_id}:{uri}:{app_key}".format(
        date=request_date,
        req_id=request_id,
        uri=auth_keys.URI,
        app_key=auth_keys.APP_KEY,
    )
    hmac_sha1 = hmac.new(
        base64.b64decode(auth_keys.SECRET_KEY),
        unsigned_auth_header.encode(),
        digestmod=hashlib.sha1,
    ).digest()
    sig = base64.encodebytes(hmac_sha1).rstrip()
    headers = {
        "Authorization": "MC " + auth_keys.ACCESS_KEY + ":" + sig.decode(),
        "x-mc-app-id": auth_keys.APP_ID,
        "x-mc-date": request_date,
        "x-mc-req-id": request_id,
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(
            url=base_url + auth_keys.URI,
            headers=headers,
            data=json.dumps(post_body),
        )
        return response.content, response.headers
    except Exception as e:
        logger.error(f"Unable to retrieve MTA SIEM logs from Mimecast integration. Exception: {e}")
        raise HTTPException(status_code=400, detail="Unable to retrieve MTA SIEM logs from Mimecast integration.")

async def process_response(response, checkpoint_filename: str, log_file_path: str):
    """
    Processes the response body from the Mimecast integration.
    """
    if response != "error":
        resp_body = response[0]
        resp_headers = response[1]
        content_type = resp_headers["Content-Type"]

        # End if response is JSON as there is no log file to download
        if content_type == "application/json":
            logger.info("No more logs available")
            return False
        # Process log file
        elif content_type == "application/octet-stream":
            logger.info("Content-Type: application/octet-stream")
            file_name = resp_headers["Content-Disposition"].split('="')
            file_name = file_name[1][:-1]

            # Save mc-siem-token page token to check point directory
            await write_checkpoint_file(checkpoint_filename, resp_headers["mc-siem-token"])
            log_filename = os.path.join(log_file_path, file_name)
            await write_log_file(log_filename, resp_body)
            return None

async def write_checkpoint_file(filename: str, data: str):
    """
    Writes the given data to the given file.
    """
    async with aiofiles.open(filename, "w") as f:
        await f.write(data)

async def write_log_file(filename: str, resp_body):
    """
    Writes the given data to the given file.
    """
    if ".zip" in filename:
        try:
            byte_content = io.BytesIO(resp_body)
            zip_file = ZipFile(byte_content)
            zip_file.extractall(filename)
        except Exception as e:
            logger.error(f"Unable to extract zip file. Exception: {e}")
            raise HTTPException(status_code=400, detail="Unable to extract zip file.")
    else:
        async with aiofiles.open(filename, "w") as f:
            await f.write(resp_body)





async def invoke_mimecast(mimecast_request: MimecastRequest, auth_keys: MimecastAuthKeys, session: AsyncSession) -> MimecastResponse:
    """
    Invokes the Mimecast integration.
    """
    mimecast_base_url = await get_base_url(auth_keys)
    try:
        logger.info(f"mimecast_base_url: {mimecast_base_url.data.data[0].region.api}")
    except Exception as e:
        logger.error(f"Unable to retrieve base URL for Mimecast integration. Exception: {e}")
        raise HTTPException(status_code=400, detail="Unable to retrieve base URL for Mimecast integration.")
    checkpoint_filename = await get_checkpoint_filename(mimecast_request.customer_code)
    log_file_path = await get_log_file_path(mimecast_request.customer_code)
    response = await get_mta_siem_logs(checkpoint_filename, mimecast_base_url.data.data[0].region.api, auth_keys)

    await process_response(response, checkpoint_filename, log_file_path)
    return None
