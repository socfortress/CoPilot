import json
from typing import List

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.connectors.sublime.models.alerts import FlaggedRule
from app.connectors.sublime.models.alerts import Mailbox
from app.connectors.sublime.models.alerts import Recipient
from app.connectors.sublime.models.alerts import Sender
from app.connectors.sublime.models.alerts import SublimeAlerts
from app.connectors.sublime.models.alerts import TriggeredAction
from app.connectors.sublime.schema.alerts import AlertRequestBody
from app.connectors.sublime.schema.alerts import AlertResponseBody
from app.connectors.sublime.schema.alerts import SublimeAlertsResponse
from app.connectors.sublime.schema.alerts import SublimeAlertsSchema
from app.connectors.sublime.utils.universal import send_get_request


def create_sublime_alert(alert_request_body: AlertRequestBody) -> SublimeAlerts:
    return SublimeAlerts(
        api_version=alert_request_body.api_version,
        created_at=alert_request_body.created_at,
        event_id=alert_request_body.id,
        type=alert_request_body.type,
        message_id=alert_request_body.data.message.id,
        canonical_id=alert_request_body.data.message.canonical_id,
        external_id=alert_request_body.data.message.external_id,
        message_source_id=alert_request_body.data.message.message_source_id,
    )


def create_flagged_rules(alert_request_body: AlertRequestBody, sublime_alert_id: int) -> List[FlaggedRule]:
    flagged_rules = []
    for rule in alert_request_body.data.flagged_rules:
        tags_str = json.dumps(rule.tags)
        flagged_rules.append(
            FlaggedRule(rule_id=rule.id, name=rule.name, severity=rule.severity, tags=tags_str, sublime_alert_id=sublime_alert_id),
        )
    return flagged_rules


def create_mailbox(alert_request_body: AlertRequestBody, sublime_alert_id: int) -> Mailbox:
    return Mailbox(
        external_id=alert_request_body.data.message.mailbox.external_id,
        mailbox_id=alert_request_body.data.message.mailbox.id,
        sublime_alert_id=sublime_alert_id,
    )


def create_triggered_actions(alert_request_body: AlertRequestBody, sublime_alert_id: int) -> List[TriggeredAction]:
    triggered_actions = []
    for action in alert_request_body.data.triggered_actions:
        triggered_actions.append(
            TriggeredAction(action_id=action.id, name=action.name, type=action.type, sublime_alert_id=sublime_alert_id),
        )
    return triggered_actions


async def store_sublime_alert(session: AsyncSession, alert_request_body: AlertRequestBody) -> AlertResponseBody:
    try:
        sublime_alert = create_sublime_alert(alert_request_body)
        session.add(sublime_alert)
        await session.flush()  # Flush to obtain the ID of the new alert

        flagged_rules = create_flagged_rules(alert_request_body, sublime_alert.id)
        mailbox = create_mailbox(alert_request_body, sublime_alert.id)
        triggered_actions = create_triggered_actions(alert_request_body, sublime_alert.id)
        sender = await create_sender(alert_request_body, sublime_alert.id)
        recipient = await create_recipient(alert_request_body, sublime_alert.id)

        session.add_all(flagged_rules)
        session.add(mailbox)
        session.add_all(triggered_actions)
        session.add(sender)
        session.add(recipient)

        logger.info(f"Preparing to store: {sublime_alert}")
        await session.commit()  # Commit the changes asynchronously
        logger.info(f"Alert {alert_request_body.id} stored in the database")

        return AlertResponseBody(success=True, message=f"Alert {alert_request_body.id} stored in the database")
    except Exception as e:
        # Rollback in case of error
        await session.rollback()
        logger.error(f"Failed to store alert {alert_request_body.id} in the database: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store alert {alert_request_body.id} in the database: {e}")


async def create_sender(alert_request_body: AlertRequestBody, sublime_alert_id: int) -> Sender:
    return Sender(email=await collect_sender(alert_request_body.data.message.id), name="n/a", sublime_alert_id=sublime_alert_id)


async def create_recipient(alert_request_body: AlertRequestBody, sublime_alert_id: int) -> Recipient:
    return Recipient(email=await collect_recipient(alert_request_body.data.message.id), name="n/a", sublime_alert_id=sublime_alert_id)


async def collect_sender(message_id: str) -> Sender:
    """
    Get a single Sublime Alert from the database
    """
    logger.info(f"Getting Sublime Alert with message_id {message_id}")
    message_details = await send_get_request(f"/v0/messages/{message_id}")
    if not message_details["success"]:
        logger.error(f"Failed to get Sublime Alert with message_id {message_id}: {message_details['message']}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Sublime Alert with message_id {message_id}: {message_details['message']}",
        )
    logger.info(f"Successfully retrieved Sublime Alert with message_id {message_id}")
    return message_details["data"]["sender"]["email"]


async def collect_recipient(message_id: str) -> Recipient:
    """
    Get a single Sublime Alert from the database
    """
    logger.info(f"Getting Sublime Alert with message_id {message_id}")
    message_details = await send_get_request(f"/v0/messages/{message_id}")
    if not message_details["success"]:
        logger.error(f"Failed to get Sublime Alert with message_id {message_id}: {message_details['message']}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Sublime Alert with message_id {message_id}: {message_details['message']}",
        )
    logger.info(f"Successfully retrieved Sublime Alert with message_id {message_id}")
    return message_details["data"]["recipients"][0]["email"]


async def collect_alerts(session: AsyncSession) -> List[SublimeAlertsResponse]:
    """
    Get all Sublime Alerts from the database asynchronously.

    Args:
        session (AsyncSession): The database session.

    Returns:
        List[SublimeAlertsResponse]: A list of SublimeAlertsResponse objects.
    """
    logger.info("Getting all Sublime Alerts")
    try:
        # Asynchronous query to load all alerts and their related objects
        stmt = select(SublimeAlerts).options(
            selectinload(SublimeAlerts.flagged_rules),
            selectinload(SublimeAlerts.mailbox),
            selectinload(SublimeAlerts.triggered_actions),
            selectinload(SublimeAlerts.sender),
            selectinload(SublimeAlerts.recipients),
        )
        result = await session.execute(stmt)
        alerts = result.scalars().all()

        logger.info("Successfully retrieved all Sublime Alerts")
        return SublimeAlertsResponse(
            success=True,
            message="Successfully retrieved all Sublime Alerts",
            sublime_alerts=[SublimeAlertsSchema.from_orm(alert) for alert in alerts],
        )
    except Exception as e:
        logger.error(f"Failed to get all Sublime Alerts with error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get all Sublime Alerts with error: {e}")
