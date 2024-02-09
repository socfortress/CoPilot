import base64
import datetime
import hashlib
import hmac
import io
import json
import os
import shutil
import time
import uuid
from zipfile import ZipFile

import aiofiles
import requests
from fastapi import HTTPException
from loguru import logger

from app.integrations.mimecast.schema.mimecast import DataItem
from app.integrations.mimecast.schema.mimecast import MimecastAPIEndpointResponse
from app.integrations.mimecast.schema.mimecast import MimecastAuthKeys
from app.integrations.mimecast.schema.mimecast import MimecastRequest
from app.integrations.mimecast.schema.mimecast import MimecastResponse
from app.integrations.mimecast.schema.mimecast import MimecastTTPURLSRequest
from app.integrations.mimecast.schema.mimecast import RequestBody
from app.integrations.mimecast.schema.mimecast import TtpURLResponseBody
from app.integrations.utils.collection import send_post_request
from app.integrations.utils.event_shipper import event_shipper
from app.integrations.utils.schema import EventShipperPayload


async def get_checkpoint_filename(customer_code: str):
    """
    Retrieves the checkpoint filename for the Mimecast integration.
    If the checkpoint file does not exist, it will be created asynchronously.
    """
    # Relative path from the current script to the checkpoint directory
    checkpoint_directory = os.path.join(os.path.dirname(__file__), "..", "checkpoint")
    checkpoint_filename = os.path.join(
        checkpoint_directory,
        f"mimecast_{customer_code}.checkpoint",
    )

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
    log_directory = os.path.join(os.path.dirname(__file__), "..", "logs")
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


async def get_base_url(
    mimecast_auth_keys: MimecastAuthKeys,
) -> MimecastAPIEndpointResponse:
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
        if response["success"] is True:
            logger.info(
                f"Successfully retrieved base URL for Mimecast integration. Response: {response}",
            )
            return MimecastAPIEndpointResponse(**response)
        else:
            logger.error(
                f"Unable to retrieve base URL for Mimecast integration. Response: {response}",
            )
            raise HTTPException(
                status_code=400,
                detail="Unable to retrieve base URL for Mimecast integration.",
            )
    except Exception as e:
        logger.error(
            f"Unable to retrieve base URL for Mimecast integration. Exception: {e}",
        )
        raise HTTPException(
            status_code=400,
            detail="Unable to retrieve base URL for Mimecast integration.",
        )


async def get_mta_siem_logs(
    checkpoint_filename: str,
    base_url: str,
    auth_keys: MimecastAuthKeys,
):
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
        logger.error(
            f"Unable to retrieve MTA SIEM logs from Mimecast integration. Exception: {e}",
        )
        raise HTTPException(
            status_code=400,
            detail="Unable to retrieve MTA SIEM logs from Mimecast integration.",
        )


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
            await write_checkpoint_file(
                checkpoint_filename,
                resp_headers["mc-siem-token"],
            )
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


async def process_log_file(
    filename: str,
    filename2: str,
    log_file_path: str,
    customer_code: str,
):
    """
    Process a log file by reading its contents and shipping events.
    """
    log_file_full_path = build_log_file_path(log_file_path, filename, filename2)
    file_creation_time = get_file_creation_time(log_file_full_path)
    logger.info(f"File creation time: {file_creation_time} and filename: {filename2}")

    await read_and_ship_log_file(log_file_full_path, customer_code)
    await safely_delete_file(log_file_full_path)


def build_log_file_path(log_file_path: str, filename: str, filename2: str) -> str:
    """
    Constructs the full path for a log file.
    """
    return os.path.join(log_file_path, filename, filename2)


def get_file_creation_time(file_path: str) -> str:
    """
    Returns the creation time of a file.
    """
    return time.ctime(os.path.getctime(file_path))


async def read_and_ship_log_file(file_path: str, customer_code: str):
    """
    Reads a log file line by line, converts each line to JSON, and ships the event.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            log_entry = convert_to_json(line)
            message = EventShipperPayload(
                customer_code=customer_code,
                integration="mimecast",
                version="1.0",
                **log_entry,
            )
            await event_shipper(message)


async def safely_delete_file(file_path: str):
    """
    Attempts to delete a file and logs the outcome.
    """
    try:
        os.remove(file_path)
        logger.info(f"Successfully deleted the file: {file_path}")
    except OSError as e:
        logger.error(f"Error: {e.strerror}. File: {file_path}")


def convert_to_json(log_line: str) -> dict:
    """
    Converts a log line to a JSON object.
    """
    log_dict = {}
    for pair in log_line.split("|"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            log_dict[key.strip()] = value.strip()
    return log_dict


async def delete_log_directory(log_file_path: str):
    """
    Deletes the log directory for the given customer.
    """
    try:
        shutil.rmtree(log_file_path)
        logger.info(f"Successfully deleted the directory: {log_file_path}")
    except OSError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error: {e.strerror}. Directory: {log_file_path}",
        )


async def invoke_mimecast(
    mimecast_request: MimecastRequest,
    auth_keys: MimecastAuthKeys,
) -> MimecastResponse:
    """
    Invokes the Mimecast integration.
    """
    mimecast_base_url = await get_base_url(auth_keys)
    try:
        logger.info(f"mimecast_base_url: {mimecast_base_url.data.data[0].region.api}")
    except Exception as e:
        logger.error(
            f"Unable to retrieve base URL for Mimecast integration. Exception: {e}",
        )
        raise HTTPException(
            status_code=400,
            detail="Unable to retrieve base URL for Mimecast integration.",
        )
    checkpoint_filename = await get_checkpoint_filename(mimecast_request.customer_code)
    log_file_path = await get_log_file_path(mimecast_request.customer_code)
    response = await get_mta_siem_logs(
        checkpoint_filename,
        mimecast_base_url.data.data[0].region.api,
        auth_keys,
    )

    await process_response(response, checkpoint_filename, log_file_path)
    for filename in os.listdir(log_file_path):
        if os.path.isdir(os.path.join(log_file_path, filename)):
            for filename2 in os.listdir(os.path.join(log_file_path, filename)):
                await process_log_file(
                    filename,
                    filename2,
                    log_file_path,
                    customer_code=mimecast_request.customer_code,
                )
            logger.info(f"Log file path: {log_file_path}")
        else:
            await process_log_file(filename, filename2, log_file_path)

    await delete_log_directory(log_file_path)
    return MimecastResponse(
        success=True,
        message="Successfully invoked Mimecast integration.",
    )


# ! TTP URLS ! #
async def custom_datetime_format(dt: datetime.datetime) -> str:
    """Format a datetime object to a custom ISO-like string."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S%z").replace("+00:00", "+0000")


async def create_ttp_request_body(
    mimecast_request: MimecastTTPURLSRequest,
) -> RequestBody:
    """Create a request body for the Mimecast API call."""
    meta_data = {}
    if mimecast_request.pagination_token:
        meta_data["pagination"] = {"pageToken": mimecast_request.pagination_token}
    return RequestBody(
        meta=meta_data,
        data=[
            DataItem(
                oldestFirst=False,
                from_=mimecast_request.lower_bound,
                route="all",
                to=mimecast_request.upper_bound,
                scanResult="all",
            ),
        ],
    )


async def invoke_mimecast_api_ttp_urls(
    mimecast_request: MimecastTTPURLSRequest,
) -> TtpURLResponseBody:
    """Invoke the Mimecast API call to get TTP URLs."""
    logger.info("Mimecast TTP URL request received")
    request_body = await create_ttp_request_body(mimecast_request)
    request_dict = request_body.dict(by_alias=True)
    logger.info(f"Request: {request_dict}")
    for item in request_dict["data"]:
        item["from"] = await custom_datetime_format(item["from"])
        item["to"] = await custom_datetime_format(item["to"])
    response = requests.post(
        url=mimecast_request.BaseURL + "/api/ttp/url/get-logs",
        headers=mimecast_request.headers.dict(by_alias=True),
        data=str(request_dict),
    )
    return TtpURLResponseBody(**response.json())


async def get_ttp_urls(
    mimecast_request: MimecastTTPURLSRequest,
    customer_code: str,
) -> MimecastResponse:
    logger.info("Mimecast TTP URL request received")
    # Get the BaseURL for the Mimecast integration
    mimecast_base_url = await get_base_url(
        MimecastAuthKeys(
            APP_ID=mimecast_request.ApplicationID,
            APP_KEY=mimecast_request.ApplicationKey,
            ACCESS_KEY=mimecast_request.AccessKey,
            SECRET_KEY=mimecast_request.SecretKey,
            EMAIL_ADDRESS=mimecast_request.EmailAddress,
            URI="/api/login/discover-authentication",
        ),
    )
    # Add it to the request object
    mimecast_request.BaseURL = mimecast_base_url.data.data[0].region.api

    mimecast_request.pagination_token = None  # Initialize pagination_token to None

    while True:
        response = await invoke_mimecast_api_ttp_urls(mimecast_request)
        logger.info(f"Response: {response}")

        for data in response.data[0].clickLogs:
            message = EventShipperPayload(
                customer_code=customer_code,
                integration="mimecast",
                version="1.0",
                **data.dict(by_alias=True),
            )
            await event_shipper(message)

        # Check if there is a "next" page token in the response
        next_page_token = response.meta.pagination.next

        if not next_page_token:
            break  # No more pages, break the loop

        # Update the pagination_token for the next API call
        mimecast_request.pagination_token = next_page_token

    return MimecastResponse(
        success=True,
        message="Mimecast TTP URL request successful",
    )
