from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.db.db_session import get_db
from app.integrations.models.customer_integration_settings import (
    CustomerIntegrations,
)
from app.integrations.models.customer_integration_settings import (
    IntegrationService,
)
from app.integrations.models.customer_integration_settings import (
    IntegrationSubscription,
)
from app.integrations.models.customer_integration_settings import (
    IntegrationConfig,
)
from app.integrations.models.customer_integration_settings import (
    IntegrationMetadata, AvailableIntegrations
)
from app.integrations.schema import AvailableIntegrationsResponse

integration_settings_router = APIRouter()

async def fetch_available_integrations(session: AsyncSession):
    """
    Fetches available integrations from the database.

    Args:
        session (AsyncSession): The database session.

    Returns:
        List[AvailableIntegrations]: A list of available integrations.
    """
    stmt = select(AvailableIntegrations)
    result = await session.execute(stmt)
    return result.scalars().all()

@integration_settings_router.get(
    "/available_integrations",
    response_model=AvailableIntegrationsResponse,
    description="Get a list of available integrations."
)
async def get_available_integrations(
    session: AsyncSession = Depends(get_db),
):
    """
    Endpoint to get a list of available integrations.
    """
    available_integrations = await fetch_available_integrations(session)
    return AvailableIntegrationsResponse(
        available_integrations=available_integrations,
        message="Available integrations successfully retrieved.",
        success=True,
    )
