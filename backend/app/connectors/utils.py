from typing import Any
from typing import Dict
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlmodel import Session
from sqlmodel import select

from app.connectors.models import Connectors
from app.connectors.schema import ConnectorResponse
from app.db.db_session import engine  # Import the shared engine

# ! Old without Async
# def get_connector_info_from_db(connector_name: str) -> Dict[str, Any]:
#     with Session(engine) as session:
#         query = select(Connectors).where(Connectors.connector_name == connector_name)
#         connector = session.exec(query).first()
#         if connector:
#             connector_pydantic = ConnectorResponse.from_orm(connector)
#             connector_dict = connector_pydantic.dict()
#             return connector_dict
#         else:
#             logger.warning("No connector found.")
#             return None


# ! New with Async
async def get_connector_info_from_db(connector_name: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
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
