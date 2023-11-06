from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger

from app.auth.utils import AuthHandler
from app.connectors.dfir_iris.schema.assets import AssetResponse
from app.connectors.dfir_iris.services.assets import get_case_assets
from app.connectors.dfir_iris.utils.universal import check_case_exists

# App specific imports


def verify_case_exists(case_id: int) -> int:
    if not check_case_exists(case_id):
        raise HTTPException(status_code=400, detail=f"Case {case_id} does not exist.")
    return case_id


dfir_iris_assets_router = APIRouter()


@dfir_iris_assets_router.get(
    "/{case_id}",
    response_model=AssetResponse,
    description="Get all assets for a case",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_case_assets_route(case_id: int = Depends(verify_case_exists)) -> AssetResponse:
    logger.info(f"Fetching assets for case {case_id}")
    return get_case_assets(case_id)
