from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors.graylog.services.content_packs import get_content_packs
from app.connectors.graylog.services.management import get_system_info
from app.network_connectors.models.network_connectors import CustomerNetworkConnectors
from app.network_connectors.models.network_connectors import (
    CustomerNetworkConnectorsMeta,
)
from app.stack_provisioning.graylog.schema.provision import AvailableContentPacks


async def get_graylog_version() -> str:
    """
    Get the version of the Graylog instance.

    Returns:
        str: The version of the Graylog instance.
    """
    system_info = await get_system_info()
    return system_info.version


async def system_version_check(compatible_version: str) -> bool:
    """
    Check if the Graylog version is compatible with the content pack.

    Args:
        compatible_version (str): The version of the Graylog instance.

    Returns:
        bool: True if the version is compatible, False if it is not.
    """
    system_version = await get_graylog_version()
    logger.info(f"Graylog System version: {system_version}")

    # Split the version strings at the '+' character and compare the parts before the '+'
    system_version = system_version.split("+")[0]
    compatible_version = compatible_version.split("+")[0]

    # Split these parts at the '.' character and convert them to integers
    system_version_parts = list(map(int, system_version.split(".")))
    compatible_version_parts = list(map(int, compatible_version.split(".")))

    if system_version_parts >= compatible_version_parts:
        return True
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Graylog version {system_version} is not compatible with the content pack",
        )


async def is_content_pack_available(content_pack_name: str) -> bool:
    """
    Check if the content pack is available for provisioning.

    Args:
        content_pack_name (str): The name of the content pack to check.

    Returns:
        bool: True if the content pack is available, False if it is not.
    """
    available_content_packs = [pack.name for pack in AvailableContentPacks]
    if content_pack_name in available_content_packs:
        logger.info(f"Content pack {content_pack_name} is available")
        return True
    else:
        logger.info(f"Content pack {content_pack_name} is not available")
        raise HTTPException(
            status_code=400,
            detail=f"Content pack {content_pack_name} is not available",
        )


async def does_content_pack_exist(content_pack_name: str) -> bool:
    """
    Check if the content pack exists in the list of content packs.

    Args:
        content_pack_name (str): The name of the content pack to check.

    Returns:
        bool: True if the content pack exists, False if it does not.
    """
    content_packs = await get_content_packs()
    for content_pack in content_packs:
        logger.info(f"Checking content pack {content_pack.name}")
        if content_pack.name == content_pack_name:
            logger.info(f"Content pack {content_pack_name} exists")
            if "PROCESSING_PIPELINE" in content_pack.name:
                return True
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Content pack {content_pack_name} already exists",
                )
    logger.info(f"Content pack {content_pack_name} does not exist")
    return False


async def insert_into_customer_network_connectors_meta_table(
    customer_network_connectors_meta: CustomerNetworkConnectorsMeta,
    session: AsyncSession,
) -> None:
    """
    Insert the customer network connectors meta into the database.

    Args:
        customer_network_connectors_meta (CustomerNetworkConnectorsMeta): The customer network connectors meta to insert.
        session (AsyncSession): The async session object for database operations.

    Returns:
        None
    """
    await session.add(customer_network_connectors_meta)
    await session.commit()


async def set_deployed_flag(customer_code: str, network_connector_service_name: str, flag: bool, session: AsyncSession) -> None:
    """
    Set the deployed flag to True for the specified customer code and for Fortinet.

    Args:
        customer_code (str): The customer code.
        network_connector_service_name (str): The network connector service name.
        session (AsyncSession): The async session object for database operations.

    Returns:
        None
    """
    # Retrieve the customer network connectors object for the customer code and network connector service name
    customer_network_connectors = await session.execute(
        select(CustomerNetworkConnectors).filter_by(
            customer_code=customer_code,
            network_connector_service_name=network_connector_service_name,
        ),
    )
    customer_network_connectors = customer_network_connectors.scalars().first()
    # Update the deployed flag to True
    customer_network_connectors.deployed = flag
    await session.commit()
    return None
