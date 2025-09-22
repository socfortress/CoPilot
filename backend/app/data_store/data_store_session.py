from loguru import logger
from miniopy_async import Minio

from settings import MINIO_REGION
from settings import MINIO_ROOT_PASSWORD
from settings import MINIO_ROOT_USER
from settings import MINIO_SECURE
from settings import MINIO_URL


async def create_session() -> Minio:
    logger.info("Initializing MinIO client via centralized settings")
    client = Minio(
        MINIO_URL,
        access_key=MINIO_ROOT_USER,
        secret_key=MINIO_ROOT_PASSWORD,
        secure=MINIO_SECURE,
        region=MINIO_REGION,
    )
    return client
