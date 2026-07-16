from fastapi import HTTPException
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
    """Invoke the customer's Shuffle notification workflow for a case.

    This is triggered directly by an analyst ("Invoke Customer Notification"),
    so failures must be surfaced rather than swallowed — `execute_workflow`
    raises an HTTPException when Shuffle reports the workflow could not be
    retrieved/executed, and we let it propagate so the UI reflects the real
    result instead of a phantom success. See GitHub issue #963.
    """
    customer_notifications = await get_customer_notification(customer_code, session)
    logger.info(f"Sending case_payload {case_payload} to customer code {customer_code}")
    if not customer_notifications or not customer_notifications[0].enabled:
        raise HTTPException(
            status_code=400,
            detail=f"No enabled customer notification workflow is configured for customer '{customer_code}'.",
        )

    logger.info(f"Executing workflow for customer code {customer_code}")

    # Shuffle's variable-substitution engine can't index into arrays
    # ($exec...alerts.0.asset_payload returns the whole array), so also expose
    # the primary (first) alert's fields at the payload root. Issue #980 Feature 1.
    primary_alert = case_payload.alerts[0] if case_payload.alerts else None
    primary_context = primary_alert.alert_context_payload if primary_alert else None

    await execute_workflow(
        ExecuteWorkflowRequest(
            workflow_id=customer_notifications[0].shuffle_workflow_id,
            execution_arguments={
                "type": type,
                "customer_code": customer_code,
                "case_name": case_payload.case_name,
                "primary_asset": primary_alert.asset_payload if primary_alert else None,
                "primary_source": primary_alert.source if primary_alert else None,
                "primary_alert_title": primary_alert.alert_title_payload if primary_alert else None,
                "primary_timefield": primary_alert.timefield_payload if primary_alert else None,
                "primary_alert_id": primary_alert.alert_id if primary_alert else None,
                "primary_mitre_id": (primary_context or {}).get("rule_mitre_id") if primary_context else None,
                # Default rule level + normalized severity, from the primary alert
                # (null for non-Wazuh sources with no rule level). Issue #980 Feature 3.
                "rule_level": primary_alert.rule_level if primary_alert else None,
                "severity": primary_alert.severity if primary_alert else None,
                "alerts": case_payload.alerts,
            },
            start="",
        ),
    )
