from sqlmodel import Session, select
from contextlib import contextmanager
from app.db.db_session import engine  # Import the shared engine
from app.connectors.models import Connectors
from app.connectors.schema import ConnectorResponse
from datetime import datetime
from typing import List, Optional, Generator, Type
from loguru import logger
from pydantic import BaseModel
from typing import Dict, Any

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