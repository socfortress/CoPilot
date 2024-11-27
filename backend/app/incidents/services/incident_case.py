from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.shuffle.schema.integrations import ExecuteWorkflowRequest
from app.connectors.shuffle.services.integrations import execute_workflow
from app.incidents.schema.incident_alert import CreatedCaseNotificationPayload
from app.incidents.services.db_operations import get_customer_notification


async def handle_customer_notifications_case(
    customer_code: str,
    case_payload: CreatedCaseNotificationPayload,
    session: AsyncSession,
    type: str = "case",
) -> None:
    customer_notifications = await get_customer_notification(customer_code, session)
    logger.info(f"Sending case_payload {case_payload} to customer code {customer_code}")
    if customer_notifications and customer_notifications[0].enabled:
        logger.info(f"Executing workflow for customer code {customer_code}")
        await execute_workflow(
            ExecuteWorkflowRequest(
                workflow_id=customer_notifications[0].shuffle_workflow_id,
                execution_arguments={
                    "type": type,
                    "customer_code": customer_code,
                    "case_name": case_payload.case_name,
                    "alerts": case_payload.alerts,
                },
                start="",
            ),
        )
