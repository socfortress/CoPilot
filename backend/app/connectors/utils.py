from typing import Any
from typing import Dict
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.connectors import cache as connector_cache
from app.connectors.models import Connectors
from app.connectors.schema import ConnectorResponse


# ! New with Async
async def get_connector_info_from_db(
    connector_name: str,
    db: AsyncSession,
) -> Optional[Dict[str, Any]]:
    """
    Fetches connector information from the database based on the given connector name.

    Served from a process-wide cache when possible (#1072, level 4): this is the
    single funnel for connector credentials, called from 89 sites, and at ~135ms
    per round-trip on this deployment it was the largest remaining source of
    database work — 3.4 queries per request. See `app/connectors/cache.py` for
    why connector rows are safe to cache and where they are invalidated.

    Args:
        connector_name (str): The name of the connector to fetch.
        db (AsyncSession): The database session.

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing the connector information if found,
        otherwise None.
    """

    async def load() -> Optional[Dict[str, Any]]:
        logger.info(f"Fetching connector {connector_name} from database")
        query = select(Connectors).where(Connectors.connector_name == connector_name)
        result = await db.execute(query)
        connector = result.scalars().first()
        if connector:
            return ConnectorResponse.from_orm(connector).model_dump()
        logger.warning("No connector found.")
        return None

    return await connector_cache.get_or_load(connector_name, load)


async def is_connector_verified(connector_name: str, db: AsyncSession) -> bool:
    """
    Checks if a connector is verified.

    Reads through the same cache as `get_connector_info_from_db` rather than
    issuing its own query: it asks about the same row, and the callers that use
    it are the ones that then immediately fetch that row's credentials.

    Args:
        connector_name (str): The name of the connector to check.
        db (AsyncSession): The database session.

    Returns:
        bool: True if the connector is verified, otherwise False.
    """
    logger.info(f"Checking if connector {connector_name} is verified")
    connector = await get_connector_info_from_db(connector_name, db)
    if connector:
        return connector["connector_verified"]
    else:
        logger.warning("No connector found.")
        return False
