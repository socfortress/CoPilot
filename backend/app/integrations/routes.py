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
    IntegrationMetadata,
)

integrations_router = APIRouter()
