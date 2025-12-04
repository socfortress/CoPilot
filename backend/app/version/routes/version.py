from fastapi import APIRouter
from app.version.schema.version import VersionCheckResponse
from app.version.services.version import check_version_outdated
from loguru import logger

version_router = APIRouter()

@version_router.get(
    "/check",
    response_model=VersionCheckResponse,
    description="Check if CoPilot version is up to date"
)
async def check_version() -> VersionCheckResponse:
    """
    Check if the current CoPilot version is outdated.

    This endpoint compares the current version with the latest release
    from the GitHub repository.

    **Returns:**
    - Current version
    - Latest available version
    - Whether an update is available
    - Link to release notes if outdated
    """
    logger.info("Checking CoPilot version")
    result = await check_version_outdated()
    return VersionCheckResponse(**result)
