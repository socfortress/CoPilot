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


async def verify_case_exists(case_id: int) -> int:
    """
    Verify if a case exists based on the given case ID.

    Args:
        case_id (int): The ID of the case to verify.

    Returns:
        int: The verified case ID.

    Raises:
        HTTPException: If the case does not exist.
    """
    if not await check_case_exists(case_id):
        raise HTTPException(status_code=400, detail=f"Case {case_id} does not exist.")
    return case_id


dfir_iris_assets_router = APIRouter()


@dfir_iris_assets_router.get(
    "/{case_id}",
    response_model=AssetResponse,
    description="Get all assets for a case",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def get_case_assets_route(
    case_id: int = Depends(verify_case_exists),
) -> AssetResponse:
    """
    Retrieve all assets for a given case.

    Args:
        case_id (int): The ID of the case.

    Returns:
        AssetResponse: The response containing the assets for the case.
    """
    logger.info(f"Fetching assets for case {case_id}")
    return await get_case_assets(case_id)
