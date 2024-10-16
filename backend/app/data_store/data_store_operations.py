import os
from typing import Optional

import aiofiles
import aiohttp
from fastapi import HTTPException
from fastapi import UploadFile
from loguru import logger

from app.data_store.data_store_schema import CaseDataStoreCreation
from app.data_store.data_store_schema import CaseReportTemplateDataStoreCreation
from app.data_store.data_store_session import create_session


async def create_bucket_if_not_exists(bucket_name: str) -> None:
    client = await create_session()
    if not await client.bucket_exists(bucket_name):
        await client.make_bucket(bucket_name)
        logger.info(f"Created bucket {bucket_name}")
    else:
        logger.info(f"Bucket {bucket_name} already exists")


async def upload_case_data_store(data: CaseDataStoreCreation, file: UploadFile) -> None:
    client = await create_session()
    logger.info(f"Uploading file {file.filename} to bucket {data.bucket_name}")

    # Define the temporary file path
    temp_file_path = os.path.join(os.getcwd(), file.filename)

    # Save the file to the temporary location
    async with aiofiles.open(temp_file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)

    # Upload the file to Minio
    await client.fput_object(
        bucket_name=data.bucket_name,
        object_name=f"{data.case_id}/{file.filename}",
        file_path=temp_file_path,
        content_type=data.content_type,
    )

    # Optionally, remove the temporary file after upload
    os.remove(temp_file_path)


async def upload_case_report_template_data_store(data: CaseReportTemplateDataStoreCreation, file: UploadFile) -> None:
    client = await create_session()
    logger.info(f"Uploading file {file.filename} to bucket {data.bucket_name}")

    # Define the temporary file path
    temp_file_path = os.path.join(os.getcwd(), file.filename)

    # Save the file to the temporary location
    async with aiofiles.open(temp_file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)

    # Upload the file to Minio
    await client.fput_object(
        bucket_name=data.bucket_name,
        object_name=f"{file.filename}",
        file_path=temp_file_path,
        content_type=data.content_type,
    )

    # Optionally, remove the temporary file after upload
    os.remove(temp_file_path)


async def download_data_store(bucket_name: str, object_name: str) -> bytes:
    client = await create_session()
    logger.info(f"Downloading file {object_name} from bucket {bucket_name}")
    try:
        # Check if the file exists
        await client.stat_object(bucket_name, object_name)

        # If no exception is raised, the file exists, proceed to download
        async with aiohttp.ClientSession() as session:
            response = await client.get_object(bucket_name, object_name, session)
            if response is None:
                raise Exception("Received None response from get_object")
            if not isinstance(response, aiohttp.ClientResponse):
                raise Exception("Response is not an instance of aiohttp.ClientResponse")
            data = await response.read()  # Ensure to read the data
            response.close()  # Close the response to release resources
            logger.info(f"Downloaded file {object_name} from bucket {bucket_name} and returning data")
            return data
    except Exception as e:
        # If an exception is raised, the file does not exist
        logger.info(f"Error: {e}")
        # List all objects in the bucket
        objects = client.list_objects(bucket_name, recursive=True)
        objects_list = [obj.object_name async for obj in objects]
        logger.info(f"Objects in bucket {bucket_name}: {objects_list}")
        raise HTTPException(status_code=404, detail=f"File {object_name} not found in bucket {bucket_name}")


async def list_case_data_store_files(bucket_name: str, case_id: int) -> list:
    client = await create_session()
    objects = await client.list_objects(bucket_name, prefix=f"{case_id}/")
    return objects


async def list_case_report_template_data_store_files(bucket_name: Optional[str] = "copilot-case-report-templates") -> list:
    client = await create_session()
    objects_list = []
    logger.info(f"Listing objects in bucket {bucket_name}")
    objects = await client.list_objects(bucket_name)
    for obj in objects:
        logger.info(f"Object: {obj.object_name}")
        objects_list.append(obj.object_name)
    return objects_list


async def create_buckets() -> None:
    await create_bucket_if_not_exists("copilot-cases")


async def delete_file(bucket_name: str, object_name: str) -> None:
    client = await create_session()
    try:
        # Check if the file exists
        await client.stat_object(bucket_name, object_name)
        # If no exception is raised, the file exists, proceed to delete
        await client.remove_object(bucket_name, object_name)
        logger.info(f"Deleted file {object_name} from bucket {bucket_name}")
    except Exception as e:
        # If an exception is raised, the file does not exist
        logger.info(f"Error: {e}")
        raise HTTPException(status_code=404, detail=f"File {object_name} not found in bucket {bucket_name}")
