import os

from loguru import logger
from miniopy_async import Minio
from app.data_store.data_store_session import create_session
from fastapi import UploadFile
from app.data_store.data_store_schema import CaseDataStoreCreation
import aiofiles


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
    async with aiofiles.open(temp_file_path, 'wb') as out_file:
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


async def create_buckets() -> None:
    await create_bucket_if_not_exists("copilot-cases")

