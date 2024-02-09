from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.db.db_session import get_db
from app.integrations.alert_creation_settings.models.alert_creation_settings import (
    AlertCreationEventConfig,
)
from app.integrations.alert_creation_settings.models.alert_creation_settings import (
    AlertCreationSettings,
)
from app.integrations.alert_creation_settings.models.alert_creation_settings import (
    EventOrder,
)
from app.integrations.alert_creation_settings.schema.alert_creation_settings import (
    AlertCreationEventConfigResponse,
)
from app.integrations.alert_creation_settings.schema.alert_creation_settings import (
    AlertCreationSettingsCreate,
)
from app.integrations.alert_creation_settings.schema.alert_creation_settings import (
    AlertCreationSettingsResponse,
)
from app.integrations.alert_creation_settings.schema.alert_creation_settings import (
    EventOrderCreate,
)
from app.integrations.alert_creation_settings.schema.alert_creation_settings import (
    EventOrderResponse,
)
from app.utils import get_customer_alert_event_configs

alert_creation_settings_router = APIRouter()


@alert_creation_settings_router.get(
    "/{customer_code}/event_configs",
    response_model=List[List[AlertCreationEventConfigResponse]],
    description="Get all alert event configs for a customer.",
)
async def get_customer_event_configs(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Retrieve all alert event configurations for a specific customer.

    Args:
        customer_code (str): The code of the customer.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        List[List[AlertCreationEventConfigResponse]]: A list of alert event configurations.

    Raises:
        HTTPException: If no event configurations are found for the customer.
    """
    event_configs = await get_customer_alert_event_configs(customer_code, session)

    if not event_configs:
        raise HTTPException(
            status_code=404,
            detail="No event configs found for this customer.",
        )

    return event_configs


@alert_creation_settings_router.post(
    "/create",
    response_model=AlertCreationSettings,
    description="Create a new alert creation setting.",
)
async def create_alert_creation_settings(
    alert_creation_settings: AlertCreationSettingsCreate,
    session: AsyncSession = Depends(get_db),
):
    """
    Create a new alert creation setting.

    Args:
        alert_creation_settings (AlertCreationSettingsCreate): The data for creating the alert creation setting.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        AlertCreationSettings: The created alert creation setting.
    """
    logger.info(f"alert_creation_settings: {alert_creation_settings.dict()}")

    result = await session.execute(
        select(AlertCreationSettings).where(
            AlertCreationSettings.customer_code == alert_creation_settings.customer_code,
        ),
    )
    settings = result.scalars().first()

    if settings:
        logger.info(
            f"Alert creation settings already exist for customer_code: {alert_creation_settings.customer_code}",
        )
        raise HTTPException(
            status_code=200,
            detail="Alert creation settings already exist.",
        )

    alert_creation_settings_db = AlertCreationSettings(
        **alert_creation_settings.dict(exclude={"event_orders"}),
    )

    if alert_creation_settings.event_orders is not None:
        for event_order in alert_creation_settings.event_orders:
            event_order_db = EventOrder(
                order_label=event_order.order_label,
                alert_creation_settings=alert_creation_settings_db,
            )
            session.add(event_order_db)
            for event_config in event_order.event_configs:
                event_config_db = AlertCreationEventConfig(
                    **event_config.dict(),
                    event_order=event_order_db,
                )
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
    session: AsyncSession = Depends(get_db),
):
    """
    Retrieve alert creation settings by customer name.

    Args:
        customer_name (str): The name of the customer.

    Returns:
        AlertCreationSettings: The alert creation settings for the specified customer.

    Raises:
        HTTPException: If the alert creation settings are not found.
    """
    result = await session.execute(
        select(AlertCreationSettings)
        .options(
            joinedload(AlertCreationSettings.event_orders).joinedload(
                EventOrder.event_configs,
            ),
        )
        .where(AlertCreationSettings.customer_name == customer_name),
    )
    settings = result.scalars().first()

    if not settings:
        raise HTTPException(
            status_code=404,
            detail="Alert creation settings not found.",
        )

    return settings


@alert_creation_settings_router.post(
    "/{customer_name}/event",
    response_model=EventOrderResponse,
    description="Add a new event to a customer's alert creation settings.",
)
async def add_event_order(
    customer_name: str,
    event_order: EventOrderCreate,
    session: AsyncSession = Depends(get_db),
):
    """
    Add a new event to a customer's alert creation settings.

    Args:
        customer_name (str): The name of the customer.
        event_order (EventOrderCreate): The event order to be added.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        EventOrder: The newly created event order.
    """
    result = await session.execute(
        select(AlertCreationSettings)
        .options(
            joinedload(AlertCreationSettings.event_orders).joinedload(
                EventOrder.event_configs,
            ),
        )
        .where(AlertCreationSettings.customer_name == customer_name),
    )
    settings = result.scalars().first()

    if not settings:
        raise HTTPException(
            status_code=404,
            detail="Alert creation settings not found.",
        )

    # Create new event order and configs
    event_order_db = EventOrder(
        order_label=event_order.order_label,
        alert_creation_settings=settings,
    )
    session.add(event_order_db)
    for event_config in event_order.event_configs:
        event_config_db = AlertCreationEventConfig(
            **event_config.dict(),
            event_order=event_order_db,
        )
        session.add(event_config_db)

    await session.commit()

    # Query the EventOrder instance again to ensure event_configs are loaded
    result = await session.execute(
        select(EventOrder).options(joinedload(EventOrder.event_configs)).where(EventOrder.id == event_order_db.id),
    )
    event_order_db = result.scalars().first()

    return event_order_db


@alert_creation_settings_router.put(
    "/{customer_name}",
    response_model=AlertCreationSettingsResponse,
    description="Update a customer's event orders.",
)
async def update_event_orders(
    customer_name: str,
    event_orders: List[EventOrderCreate],
    session: AsyncSession = Depends(get_db),
):
    """
    Update a customer's event orders.

    Args:
        customer_name (str): The name of the customer.
        event_orders (List[EventOrderCreate]): The list of event orders to update.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        AlertCreationSettings: The updated alert creation settings.
    """
    result = await session.execute(
        select(AlertCreationSettings)
        .options(
            joinedload(AlertCreationSettings.event_orders).joinedload(
                EventOrder.event_configs,
            ),
        )
        .where(AlertCreationSettings.customer_name == customer_name),
    )
    settings = result.scalars().first()

    if not settings:
        raise HTTPException(
            status_code=404,
            detail="Alert creation settings not found.",
        )

    # Create new event orders and configs or add to existing ones
    for event_order in event_orders:
        # Check if an EventOrder with the given order_label already exists
        existing_order = next(
            (order for order in settings.event_orders if order.order_label == event_order.order_label),
            None,
        )

        if existing_order:
            # If it does, add the new EventConfig instances to it
            for event_config in event_order.event_configs:
                event_config_db = AlertCreationEventConfig(
                    **event_config.dict(),
                    event_order=existing_order,
                )
                session.add(event_config_db)
        else:
            # If it doesn't, return a 404
            raise HTTPException(
                status_code=404,
                detail=f"Event order with order_label: {event_order.order_label} not found.",
            )

    await session.commit()
    await session.refresh(settings)

    return settings


@alert_creation_settings_router.delete(
    "/{customer_name}/event/{order_label}",
    description="Delete an event order by order_label.",
)
async def delete_event_order(
    customer_name: str,
    order_label: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Delete an event order by order_label.

    Args:
        customer_name (str): The name of the customer.
        order_label (str): The label of the event order.
        session (AsyncSession, optional): The database session. Defaults to Depends(get_db).

    Returns:
        dict: A dictionary containing the success message.
    """
    result = await session.execute(
        select(AlertCreationSettings)
        .options(
            joinedload(AlertCreationSettings.event_orders).joinedload(
                EventOrder.event_configs,
            ),
        )
        .where(AlertCreationSettings.customer_name == customer_name),
    )
    settings = result.scalars().first()

    if not settings:
        raise HTTPException(
            status_code=404,
            detail="Alert creation settings not found.",
        )

    # Check if an EventOrder with the given order_label exists
    existing_order = next(
        (order for order in settings.event_orders if order.order_label == order_label),
        None,
    )

    if existing_order:
        # If it does, delete its AlertCreationEventConfig instances
        for config in existing_order.event_configs:
            await session.delete(config)

        # Then delete the EventOrder itself
        await session.delete(existing_order)
    else:
        # If it doesn't, return a 404
        raise HTTPException(
            status_code=404,
            detail=f"Event order with order_label: {order_label} not found.",
        )

    await session.commit()

    return {
        "message": f"Event order with order_label: {order_label} and related alert creation event configs deleted.",
        "success": True,
    }
