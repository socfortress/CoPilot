from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.db.db_session import get_session
from app.integrations.alert_creation_settings.schema.alert_creation_settings import AlertCreationSettingsCreate, AlertCreationSettingsResponse
from app.integrations.alert_creation_settings.models.alert_creation_settings import AlertCreationSettings, EventOrder, AlertCreationEventConfig

alert_creation_settings_router = APIRouter()

@alert_creation_settings_router.post(
    "/create",
    response_model=AlertCreationSettings,
    description="Create a new alert creation setting.",
)
async def create_alert_creation_settings(
    alert_creation_settings: AlertCreationSettingsCreate,
    session: AsyncSession = Depends(get_session),
):
    logger.info(f"alert_creation_settings: {alert_creation_settings.dict()}")

    result = await session.execute(
        select(AlertCreationSettings).where(AlertCreationSettings.customer_code == alert_creation_settings.customer_code),
    )
    settings = result.scalars().first()

    if settings:
        logger.info(f"Alert creation settings already exist for customer_code: {alert_creation_settings.customer_code}")
        raise HTTPException(status_code=200, detail="Alert creation settings already exist.")

    alert_creation_settings_db = AlertCreationSettings(**alert_creation_settings.dict(exclude={"event_orders"}))

    if alert_creation_settings.event_orders is not None:
        for event_order in alert_creation_settings.event_orders:
            event_order_db = EventOrder(order_label=event_order.order_label, alert_creation_settings=alert_creation_settings_db)
            session.add(event_order_db)
            for event_config in event_order.event_configs:
                event_config_db = AlertCreationEventConfig(**event_config.dict(), event_order=event_order_db)
                session.add(event_config_db)

    session.add(alert_creation_settings_db)
    await session.commit()
    await session.refresh(alert_creation_settings_db)

    return alert_creation_settings_db


@alert_creation_settings_router.get(
    "/{customer_name}",
    response_model=AlertCreationSettingsResponse,
    description="Retrieve alert creation settings by customer name.",
)
async def get_alert_creation_settings(
    customer_name: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(AlertCreationSettings)
        .options(joinedload(AlertCreationSettings.event_orders).joinedload(EventOrder.event_configs))
        .where(AlertCreationSettings.customer_name == customer_name)
    )
    settings = result.scalars().first()

    if not settings:
        raise HTTPException(status_code=404, detail="Alert creation settings not found.")

    return settings
