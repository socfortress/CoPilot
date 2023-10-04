from contextlib import contextmanager
from datetime import datetime
from typing import Any
from typing import Dict
from typing import Generator
from typing import List
from typing import Optional
from typing import Type

from loguru import logger
from pydantic import BaseModel
from sqlmodel import Session
from sqlmodel import select

from app.connectors.models import Connectors
from app.connectors.schema import ConnectorResponse
from app.db.db_session import engine  # Import the shared engine


def get_connector_info_from_db(connector_name: str) -> Dict[str, Any]:
    with Session(engine) as session:
        query = select(Connectors).where(Connectors.connector_name == connector_name)
        connector = session.exec(query).first()
        if connector:
            connector_pydantic = ConnectorResponse.from_orm(connector)
            connector_dict = connector_pydantic.dict()
            return connector_dict
        else:
            logger.warning("No connector found.")
            return None
