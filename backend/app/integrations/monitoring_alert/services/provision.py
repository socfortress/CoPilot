from app.integrations.monitoring_alert.schema.provision import ProvisionWazuhMonitoringAlertResponse, AvailableMonitoringAlerts, AvailableMonitoringAlertsResponse, GraylogAlertWebhookNotificationModel, GraylogAlertProvisionModel
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.connectors.graylog.routes.monitoring import get_all_event_notifications
from app.connectors.graylog.schema.monitoring import GraylogEventNotificationsResponse
from loguru import logger
from app.connectors.graylog.utils.universal import send_post_request

async def check_if_event_notification_exists(event_notification: str) -> bool:
    """
    Check if the event notification exists.

    Args:
        event_notification (str): The event notification to check.

    Returns:
        bool: True if the event notification exists, False otherwise.
    """
    event_notifications_response = await get_all_event_notifications()
    if not event_notifications_response.success:
        raise HTTPException(status_code=500, detail="Failed to collect event notifications")
    event_notifications_response = GraylogEventNotificationsResponse(**event_notifications_response.dict())
    logger.info(f"Event notifications collected: {event_notifications_response.event_notifications}")
    if event_notification in [event_notification.title for event_notification in event_notifications_response.event_notifications.notifications]:
        return True
    return False

async def provision_webhook(webhook_model: GraylogAlertWebhookNotificationModel) -> bool:
    """
    Provisions a webhook for Graylog alerts.

    Args:
        webhook_model (GraylogAlertWebhookNotificationModel): The webhook model.

    Returns:
        bool: True if the webhook was provisioned successfully, False otherwise.
    """
    response = await send_post_request(endpoint="/api/events/notifications", data=webhook_model.dict())
    if response["success"]:
        return True
    return False

async def provision_wazuh_monitoring_alert(session: AsyncSession) -> ProvisionWazuhMonitoringAlertResponse:
    """
    Provisions Wazuh monitoring alerts.

    Returns:
        ProvisionWazuhMonitoringAlertResponse: The response indicating the success of provisioning the monitoring alerts.
    """
    #
    notification_exists = await check_if_event_notification_exists("SEND TO COPILOT")
    if not notification_exists:
        logger.info("Provisioning SEND TO COPILOT Webhook")
        await provision_webhook(GraylogAlertWebhookNotificationModel(
            title="SEND TO COPILOT",
            description="Send alert to Copilot",
            config={"url": "https://localhost:123", "type": "http-notification-v1"},
            )
        )



    return ProvisionWazuhMonitoringAlertResponse(success=True, message="Wazuh monitoring alerts provisioned successfully")
