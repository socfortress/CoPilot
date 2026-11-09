from loguru import logger

from app.data_store.data_store_operations import SYSMON_CONFIG_DEFAULTS_BUCKET
from app.data_store.data_store_session import create_session


async def create_bucket_if_not_exists(bucket_name: str) -> None:
    client = await create_session()
    if not await client.bucket_exists(bucket_name):
        await client.make_bucket(bucket_name)
        logger.info(f"Created bucket {bucket_name}")
    else:
        logger.info(f"Bucket {bucket_name} already exists")


async def create_buckets() -> None:
    await create_bucket_if_not_exists("copilot-cases")
    await create_bucket_if_not_exists("copilot-case-report-templates")
    await create_bucket_if_not_exists("sysmon-configs")
    # This CoPilot's default Sysmon config, apart from the customers' ones
    await create_bucket_if_not_exists(SYSMON_CONFIG_DEFAULTS_BUCKET)
    await create_bucket_if_not_exists("velociraptor-artifacts")
    await create_bucket_if_not_exists("incident-management-reports")
