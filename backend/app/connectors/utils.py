from typing import Any
from typing import Dict
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors.models import Connectors
from app.connectors.schema import ConnectorResponse


# ! New with Async
async def get_connector_info_from_db(
    connector_name: str,
    db: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    Fetches connector information from the database based on the given connector name.

    Args:
        connector_name (str): The name of the connector to fetch.
        db (AsyncSession): The database session.

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing the connector information if found,
        otherwise None.
    """
    logger.info(f"Fetching connector {connector_name} from database")
    query = select(Connectors).where(Connectors.connector_name == connector_name)
    result = await db.execute(query)
    connector = result.scalars().first()
    if connector:
        connector_pydantic = ConnectorResponse.from_orm(connector)
        return connector_pydantic.dict()
    else:
        logger.warning("No connector found.")
        return None

async def is_connector_verified(connector_name: str, db: AsyncSession) -> bool:
    """
    Checks if a connector is verified.

    Args:
        connector_name (str): The name of the connector to check.
        db (AsyncSession): The database session.

    Returns:
        bool: True if the connector is verified, otherwise False.
    """
    logger.info(f"Checking if connector {connector_name} is verified")
    query = select(Connectors).where(Connectors.connector_name == connector_name)
    result = await db.execute(query)
    connector = result.scalars().first()
    if connector:
        return connector.connector_verified
    else:
        logger.warning("No connector found.")
        return False
