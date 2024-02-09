from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.integrations.monitoring_alert.models.monitoring_alert import MonitoringAlerts


async def remove_alert_id(alert_id: str, session: AsyncSession) -> None:
    """
    Remove the alert with the given alert_id from the database.

    Args:
        alert_id (str): The alert_id.
        session (AsyncSession): The database session.
    """
    logger.info(f"Removing alert with alert_id: {alert_id}")

    alert = await session.execute(
        select(MonitoringAlerts).where(MonitoringAlerts.alert_id == alert_id),
    )
    alert = alert.scalars().first()

    if not alert:
        logger.error(f"Alert with alert_id: {alert_id} not found")

    await session.delete(alert)
    await session.commit()
    logger.info(f"Alert with alert_id: {alert_id} removed")
    return None
