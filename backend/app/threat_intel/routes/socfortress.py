from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.utils import AuthHandler
from app.threat_intel.schema.socfortress import IoCResponse, SocfortressThreatIntelRequest
from app.db.db_session import get_session
from app.db.universal_models import Customers, CustomersMeta
from app.threat_intel.services.socfortress import socfortress_threat_intel_lookup
from app.utils import get_connector_attribute

# App specific imports

threat_intel_socfortress_router = APIRouter()

async def ensure_api_key_exists(session: AsyncSession = Depends(get_session)) -> bool:
    """
    Ensures that the SocFortress API key exists in the database.

    Args:
        session (AsyncSession): The database session.

    Raises:
        HTTPException: Raised if the SocFortress API key is not found.

    Returns:
        bool: True if the API key exists, otherwise raises HTTPException.
    """
    api_key = await get_connector_attribute(connector_id=11, column_name="connector_api_key", session=session)
    # Close the session
    await session.close()
    if not api_key:
        raise HTTPException(status_code=500, detail="SocFortress API key not found in the database.")
    return True



@threat_intel_socfortress_router.post(
    "/socfortress",
    response_model=IoCResponse,
    description="SocFortress Threat Intel",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def threat_intel_socfortress(
    request: SocfortressThreatIntelRequest,
    session: AsyncSession = Depends(get_session),
    _key_exists: bool = Depends(ensure_api_key_exists)
):
    logger.info("Running SOCFortress Threat Intel")

    socfortress_lookup = await socfortress_threat_intel_lookup(request, session=session)
    return socfortress_lookup

