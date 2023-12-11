from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.utils import AuthHandler
from app.db.db_session import get_session
from app.db.universal_models import Customers
from app.db.universal_models import CustomersMeta
from app.integrations.ask_socfortress.schema.ask_socfortress import AskSocfortressSigmaRequest, AskSocfortressRequest
from app.integrations.ask_socfortress.schema.ask_socfortress import AskSocfortressSigmaResponse

from app.integrations.ask_socfortress.services.ask_socfortress import ask_socfortress_lookup
from app.utils import get_connector_attribute

# App specific imports

ask_socfortress_router = APIRouter()


async def ensure_api_key_exists(session: AsyncSession = Depends(get_session)) -> bool:
    """
    Ensures that the Ask SocFortress API key exists in the database.

    Args:
        session (AsyncSession): The database session.

    Raises:
        HTTPException: Raised if the SocFortress API key is not found.

    Returns:
        bool: True if the API key exists, otherwise raises HTTPException.
    """
    api_key = await get_connector_attribute(connector_id=10, column_name="connector_api_key", session=session)
    # Close the session
    await session.close()
    if not api_key:
        raise HTTPException(status_code=500, detail="Ask SocFortress API key not found in the database.")
    return True


@ask_socfortress_router.post(
    "/sigma",
    response_model=AskSocfortressSigmaResponse,
    description="Ask SOCFortress for a Sigma rule.",
    dependencies=[Security(AuthHandler().require_any_scope("admin", "analyst"))],
)
async def ask_socfortress_sigma(
    alert: AskSocfortressRequest,
    session: AsyncSession = Depends(get_session),
    _key_exists: bool = Depends(ensure_api_key_exists),
):
    logger.info("Running Ask SOCFortress Sigma lookup.")

    ask_socfortress_result = await ask_socfortress_lookup(alert, session=session)
    return ask_socfortress_result
