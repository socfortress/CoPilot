from datetime import timedelta
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from starlette.status import HTTP_401_UNAUTHORIZED

# App specific imports
from app.auth.routes.auth import auth_handler
from app.connectors.dfir_iris.schema.assets import AssetResponse
from app.connectors.dfir_iris.services.assets import get_case_assets
from app.connectors.dfir_iris.utils.universal import check_case_exists
from app.connectors.wazuh_indexer.utils.universal import collect_indices
from app.db.db_session import session


def verify_case_exists(case_id: int) -> int:
    if not check_case_exists(case_id):
        raise HTTPException(status_code=400, detail=f"Case {case_id} does not exist.")
    return case_id


assets_router = APIRouter()


@assets_router.get("/{case_id}", response_model=AssetResponse, description="Get all assets for a case")
async def get_case_assets_route(case_id: int = Depends(verify_case_exists)) -> AssetResponse:
    logger.info(f"Fetching assets for case {case_id}")
    return get_case_assets(case_id)
