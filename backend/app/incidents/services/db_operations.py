import hashlib
import io
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from fastapi import UploadFile
from loguru import logger
from sqlalchemy import asc
from sqlalchemy import delete
from sqlalchemy import desc
from sqlalchemy import distinct
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.auth.models.users import User
from app.data_store.data_store_operations import delete_file
from app.data_store.data_store_operations import download_data_store
from app.data_store.data_store_operations import upload_case_data_store
from app.data_store.data_store_operations import upload_case_report_template_data_store
from app.data_store.data_store_schema import CaseDataStoreCreation
from app.data_store.data_store_schema import CaseReportTemplateDataStoreCreation
from app.incidents.models import Alert
from app.incidents.models import AlertContext
from app.incidents.models import AlertTag
from app.incidents.models import AlertTitleFieldName
from app.incidents.models import AlertToIoC
from app.incidents.models import AlertToTag
from app.incidents.models import Asset
from app.incidents.models import AssetFieldName
from app.incidents.models import Case
from app.incidents.models import CaseAlertLink
from app.incidents.models import CaseDataStore
from app.incidents.models import CaseReportTemplateDataStore
from app.incidents.models import Comment
from app.incidents.models import CustomerCodeFieldName
from app.incidents.models import FieldName
from app.incidents.models import IoC
from app.incidents.models import IoCFieldName
from app.incidents.models import Notification
from app.incidents.models import TimestampFieldName
from app.incidents.schema.db_operations import AlertContextCreate
from app.incidents.schema.db_operations import AlertCreate
from app.incidents.schema.db_operations import AlertIoCCreate
from app.incidents.schema.db_operations import AlertIoCDelete
from app.incidents.schema.db_operations import AlertOut
from app.incidents.schema.db_operations import AlertTagBase
from app.incidents.schema.db_operations import AlertTagCreate
from app.incidents.schema.db_operations import AssetBase
from app.incidents.schema.db_operations import AssetCreate
from app.incidents.schema.db_operations import CaseAlertLinkCreate
from app.incidents.schema.db_operations import CaseAlertLinksCreate
from app.incidents.schema.db_operations import CaseAlertUnLink
from app.incidents.schema.db_operations import CaseAlertUnLinkResponse
from app.incidents.schema.db_operations import CaseCreate
from app.incidents.schema.db_operations import CaseOut
from app.incidents.schema.db_operations import CaseReportTemplateDataStoreListResponse
from app.incidents.schema.db_operations import CommentBase
from app.incidents.schema.db_operations import CommentCreate
from app.incidents.schema.db_operations import CommentEdit
from app.incidents.schema.db_operations import IoCBase
from app.incidents.schema.db_operations import LinkedCaseCreate
from app.incidents.schema.db_operations import PutNotification
from app.incidents.schema.db_operations import UpdateAlertStatus
from app.incidents.schema.db_operations import UpdateCaseStatus
from app.integrations.alert_creation_settings.models.alert_creation_settings import (
    AlertCreationSettings,
)
from app.middleware.customer_access import customer_access_handler


async def customer_code_valid(customer_code: str, db: AsyncSession) -> bool:
    result = await db.execute(select(AlertCreationSettings).where(AlertCreationSettings.customer_code == customer_code))
    if result.scalars().first():
        return True
    raise HTTPException(status_code=404, detail="Customer code not found")


async def alert_total(db: AsyncSession) -> int:
    result = await db.execute(select(Alert))
    return len(result.scalars().all())


async def alerts_closed(db: AsyncSession) -> int:
    result = await db.execute(select(Alert).where(Alert.status == "CLOSED"))
    return len(result.scalars().all())


async def alerts_in_progress(db: AsyncSession) -> int:
    result = await db.execute(select(Alert).where(Alert.status == "IN_PROGRESS"))
    return len(result.scalars().all())


async def alerts_open(db: AsyncSession) -> int:
    result = await db.execute(select(Alert).where(Alert.status == "OPEN"))
    return len(result.scalars().all())


async def alert_total_by_assest_name(db: AsyncSession, asset_name: str) -> int:
    result = await db.execute(select(Alert).join(Asset, Alert.id == Asset.alert_linked).where(Asset.asset_name == asset_name))
    return len(result.scalars().all())


async def alerts_closed_by_asset_name(db: AsyncSession, asset_name: str) -> int:
    result = await db.execute(
        select(Alert).join(Asset, Alert.id == Asset.alert_linked).where((Alert.status == "CLOSED") & (Asset.asset_name == asset_name)),
    )
    return len(result.scalars().all())


async def alerts_in_progress_by_assest_name(db: AsyncSession, asset_name: str) -> int:
    result = await db.execute(
        select(Alert).join(Asset, Alert.id == Asset.alert_linked).where((Alert.status == "IN_PROGRESS") & (Asset.asset_name == asset_name)),
    )
    return len(result.scalars().all())


async def alerts_open_by_assest_name(db: AsyncSession, asset_name: str) -> int:
    result = await db.execute(
        select(Alert).join(Asset, Alert.id == Asset.alert_linked).where((Alert.status == "OPEN") & (Asset.asset_name == asset_name)),
    )
    return len(result.scalars().all())


async def alert_total_by_alert_title(db: AsyncSession, alert_title: str) -> int:
    result = await db.execute(select(Alert).where(Alert.alert_name.like(f"%{alert_title}%")))
    return len(result.scalars().all())


async def alerts_closed_by_alert_title(db: AsyncSession, alert_title: str) -> int:
    result = await db.execute(select(Alert).where((Alert.status == "CLOSED") & (Alert.alert_name.like(f"%{alert_title}%"))))
    return len(result.scalars().all())


async def alerts_in_progress_by_alert_title(db: AsyncSession, alert_title: str) -> int:
    result = await db.execute(select(Alert).where((Alert.status == "IN_PROGRESS") & (Alert.alert_name.like(f"%{alert_title}%"))))
    return len(result.scalars().all())


async def alerts_open_by_alert_title(db: AsyncSession, alert_title: str) -> int:
    result = await db.execute(select(Alert).where((Alert.status == "OPEN") & (Alert.alert_name.like(f"%{alert_title}%"))))
    return len(result.scalars().all())


async def alerts_total_by_assigned_to(db: AsyncSession, assigned_to: str) -> int:
    result = await db.execute(select(Alert).where(Alert.assigned_to == assigned_to))
    return len(result.scalars().all())


async def alerts_closed_by_assigned_to(db: AsyncSession, assigned_to: str) -> int:
    result = await db.execute(select(Alert).where((Alert.status == "CLOSED") & (Alert.assigned_to == assigned_to)))
    return len(result.scalars().all())


async def alerts_in_progress_by_assigned_to(db: AsyncSession, assigned_to: str) -> int:
    result = await db.execute(select(Alert).where((Alert.status == "IN_PROGRESS") & (Alert.assigned_to == assigned_to)))
    return len(result.scalars().all())


async def alerts_open_by_assigned_to(db: AsyncSession, assigned_to: str) -> int:
    result = await db.execute(select(Alert).where((Alert.status == "OPEN") & (Alert.assigned_to == assigned_to)))
    return len(result.scalars().all())


async def alerts_total_by_customer_code(db: AsyncSession, customer_code: str) -> int:
    result = await db.execute(select(Alert).where(Alert.customer_code == customer_code))
    return len(result.scalars().all())


async def alerts_closed_by_customer_code(db: AsyncSession, customer_code: str) -> int:
    result = await db.execute(select(Alert).where((Alert.status == "CLOSED") & (Alert.customer_code == customer_code)))
    return len(result.scalars().all())


async def alerts_in_progress_by_customer_code(db: AsyncSession, customer_code: str) -> int:
    result = await db.execute(select(Alert).where((Alert.status == "IN_PROGRESS") & (Alert.customer_code == customer_code)))
    return len(result.scalars().all())


async def alerts_open_by_customer_code(db: AsyncSession, customer_code: str) -> int:
    result = await db.execute(select(Alert).where((Alert.status == "OPEN") & (Alert.customer_code == customer_code)))
    return len(result.scalars().all())


async def alerts_total_by_source(db: AsyncSession, source: str) -> int:
    result = await db.execute(select(Alert).where(Alert.source == source))
    return len(result.scalars().all())


async def alerts_closed_by_source(db: AsyncSession, source: str) -> int:
    result = await db.execute(select(Alert).where((Alert.status == "CLOSED") & (Alert.source == source)))
    return len(result.scalars().all())


async def alerts_in_progress_by_source(db: AsyncSession, source: str) -> int:
    result = await db.execute(select(Alert).where((Alert.status == "IN_PROGRESS") & (Alert.source == source)))
    return len(result.scalars().all())


async def alerts_open_by_source(db: AsyncSession, source: str) -> int:
    result = await db.execute(select(Alert).where((Alert.status == "OPEN") & (Alert.source == source)))
    return len(result.scalars().all())


async def alert_total_by_customer_codes(db: AsyncSession, customer_codes: List[str]) -> int:
    """Get total alerts for multiple customer codes"""
    result = await db.execute(select(Alert).where(Alert.customer_code.in_(customer_codes)))
    return len(result.scalars().all())


async def alerts_closed_by_customer_codes(db: AsyncSession, customer_codes: List[str]) -> int:
    """Get closed alerts for multiple customer codes"""
    result = await db.execute(select(Alert).where((Alert.status == "CLOSED") & (Alert.customer_code.in_(customer_codes))))
    return len(result.scalars().all())


async def alerts_in_progress_by_customer_codes(db: AsyncSession, customer_codes: List[str]) -> int:
    """Get in-progress alerts for multiple customer codes"""
    result = await db.execute(select(Alert).where((Alert.status == "IN_PROGRESS") & (Alert.customer_code.in_(customer_codes))))
    return len(result.scalars().all())


async def alerts_open_by_customer_codes(db: AsyncSession, customer_codes: List[str]) -> int:
    """Get open alerts for multiple customer codes"""
    result = await db.execute(select(Alert).where((Alert.status == "OPEN") & (Alert.customer_code.in_(customer_codes))))
    return len(result.scalars().all())


async def alerts_total_multiple_filters(
    db: AsyncSession,
    assigned_to: Optional[str] = None,
    alert_title: Optional[str] = None,
    customer_code: Optional[str] = None,
    source: Optional[str] = None,
    asset_name: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    ioc_value: Optional[str] = None,
) -> int:
    # Build dynamic filters
    filters = []
    if assigned_to:
        filters.append(Alert.assigned_to == assigned_to)
    if alert_title:
        filters.append(Alert.alert_name.like(f"%{alert_title}%"))
    if customer_code:
        filters.append(Alert.customer_code == customer_code)
    if source:
        filters.append(Alert.source == source)
    if asset_name:
        filters.append(Asset.asset_name == asset_name)
    if status:
        filters.append(Alert.status == status)
    if tags:
        filters.append(AlertTag.tag.in_(tags))
    if ioc_value:
        filters.append(IoC.value == ioc_value)

    # Build the query with dynamic filters
    query = (
        select(func.count(distinct(Alert.id)))
        .select_from(Alert)
        .join(Asset, Asset.alert_linked == Alert.id, isouter=True)  # Join with Asset table
        .join(AlertToTag, AlertToTag.alert_id == Alert.id, isouter=True)  # Join with AlertToTag table
        .join(AlertTag, AlertToTag.tag_id == AlertTag.id, isouter=True)  # Join with AlertTag table
        .join(AlertToIoC, AlertToIoC.alert_id == Alert.id, isouter=True)  # Join with AlertToIoC table
        .join(IoC, AlertToIoC.ioc_id == IoC.id, isouter=True)  # Join with IoC table
        .where(*filters)
    )

    result = await db.execute(query)
    total = result.scalar_one()
    return total


async def alerts_closed_multiple_filters(
    db: AsyncSession,
    assigned_to: Optional[str] = None,
    alert_title: Optional[str] = None,
    customer_code: Optional[str] = None,
    source: Optional[str] = None,
    asset_name: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    ioc_value: Optional[str] = None,
) -> int:
    # Include the status filter
    filters = [Alert.status == "CLOSED"]
    if assigned_to:
        filters.append(Alert.assigned_to == assigned_to)
    if alert_title:
        filters.append(Alert.alert_name.like(f"%{alert_title}%"))
    if customer_code:
        filters.append(Alert.customer_code == customer_code)
    if source:
        filters.append(Alert.source == source)
    if asset_name:
        filters.append(Asset.asset_name == asset_name)
    if status:
        filters.append(Alert.status == status)
    if tags:
        filters.append(AlertTag.tag.in_(tags))
    if ioc_value:
        filters.append(IoC.value == ioc_value)

    # Build the query with dynamic filters
    query = (
        select(func.count(distinct(Alert.id)))
        .select_from(Alert)
        .join(Asset, Asset.alert_linked == Alert.id, isouter=True)  # Join with Asset table
        .join(AlertToTag, AlertToTag.alert_id == Alert.id, isouter=True)  # Join with AlertToTag table
        .join(AlertTag, AlertToTag.tag_id == AlertTag.id, isouter=True)  # Join with AlertTag table
        .join(AlertToIoC, AlertToIoC.alert_id == Alert.id, isouter=True)  # Join with AlertToIoC table
        .join(IoC, AlertToIoC.ioc_id == IoC.id, isouter=True)  # Join with IoC table
        .where(*filters)
    )

    result = await db.execute(query)
    closed_count = result.scalar_one()
    return closed_count


async def alerts_in_progress_multiple_filters(
    db: AsyncSession,
    assigned_to: Optional[str] = None,
    alert_title: Optional[str] = None,
    customer_code: Optional[str] = None,
    source: Optional[str] = None,
    asset_name: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    ioc_value: Optional[str] = None,
) -> int:
    filters = [Alert.status == "IN_PROGRESS"]
    if assigned_to:
        filters.append(Alert.assigned_to == assigned_to)
    if alert_title:
        filters.append(Alert.alert_name.like(f"%{alert_title}%"))
    if customer_code:
        filters.append(Alert.customer_code == customer_code)
    if source:
        filters.append(Alert.source == source)
    if asset_name:
        filters.append(Asset.asset_name == asset_name)
    if status:
        filters.append(Alert.status == status)
    if tags:
        filters.append(AlertTag.tag.in_(tags))
    if ioc_value:
        filters.append(IoC.value == ioc_value)

    query = (
        select(func.count(distinct(Alert.id)))
        .select_from(Alert)
        .join(Asset, Asset.alert_linked == Alert.id, isouter=True)  # Join with Asset table
        .join(AlertToTag, AlertToTag.alert_id == Alert.id, isouter=True)  # Join with AlertToTag table
        .join(AlertTag, AlertToTag.tag_id == AlertTag.id, isouter=True)  # Join with AlertTag table
        .join(AlertToIoC, AlertToIoC.alert_id == Alert.id, isouter=True)  # Join with AlertToIoC table
        .join(IoC, AlertToIoC.ioc_id == IoC.id, isouter=True)  # Join with IoC table
        .where(*filters)
    )

    result = await db.execute(query)
    in_progress_count = result.scalar_one()
    return in_progress_count


async def alerts_open_multiple_filters(
    db: AsyncSession,
    assigned_to: Optional[str] = None,
    alert_title: Optional[str] = None,
    customer_code: Optional[str] = None,
    source: Optional[str] = None,
    asset_name: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    ioc_value: Optional[str] = None,
) -> int:
    filters = [Alert.status == "OPEN"]
    if assigned_to:
        filters.append(Alert.assigned_to == assigned_to)
    if alert_title:
        filters.append(Alert.alert_name.like(f"%{alert_title}%"))
    if customer_code:
        filters.append(Alert.customer_code == customer_code)
    if source:
        filters.append(Alert.source == source)
    if asset_name:
        filters.append(Asset.asset_name == asset_name)
    if status:
        filters.append(Alert.status == status)
    if tags:
        filters.append(AlertTag.tag.in_(tags))
    if ioc_value:
        filters.append(IoC.value == ioc_value)

    query = (
        select(func.count(distinct(Alert.id)))
        .select_from(Alert)
        .join(Asset, Asset.alert_linked == Alert.id, isouter=True)  # Join with Asset table
        .join(AlertToTag, AlertToTag.alert_id == Alert.id, isouter=True)  # Join with AlertToTag table
        .join(AlertTag, AlertToTag.tag_id == AlertTag.id, isouter=True)  # Join with AlertTag table
        .join(AlertToIoC, AlertToIoC.alert_id == Alert.id, isouter=True)  # Join with AlertToIoC table
        .join(IoC, AlertToIoC.ioc_id == IoC.id, isouter=True)  # Join with IoC table
        .where(*filters)
    )

    result = await db.execute(query)
    open_count = result.scalar_one()
    return open_count


async def alerts_total_by_ioc(db: AsyncSession, ioc_value: str) -> int:
    result = await db.execute(
        select(Alert)
        .join(AlertToIoC, Alert.id == AlertToIoC.alert_id)
        .join(IoC, AlertToIoC.ioc_id == IoC.id)
        .where(IoC.value == ioc_value),
    )
    return len(result.scalars().all())


async def alerts_closed_by_ioc(db: AsyncSession, ioc_value: str) -> int:
    result = await db.execute(
        select(Alert)
        .join(AlertToIoC, Alert.id == AlertToIoC.alert_id)
        .join(IoC, AlertToIoC.ioc_id == IoC.id)
        .where((Alert.status == "CLOSED") & (IoC.value == ioc_value)),
    )
    return len(result.scalars().all())


async def alerts_in_progress_by_ioc(db: AsyncSession, ioc_value: str) -> int:
    result = await db.execute(
        select(Alert)
        .join(AlertToIoC, Alert.id == AlertToIoC.alert_id)
        .join(IoC, AlertToIoC.ioc_id == IoC.id)
        .where((Alert.status == "IN_PROGRESS") & (IoC.value == ioc_value)),
    )
    return len(result.scalars().all())


async def alerts_open_by_ioc(db: AsyncSession, ioc_value: str) -> int:
    result = await db.execute(
        select(Alert)
        .join(AlertToIoC, Alert.id == AlertToIoC.alert_id)
        .join(IoC, AlertToIoC.ioc_id == IoC.id)
        .where((Alert.status == "OPEN") & (IoC.value == ioc_value)),
    )
    return len(result.scalars().all())


async def alerts_total_by_tag(db: AsyncSession, tag: str) -> int:
    result = await db.execute(
        select(Alert)
        .join(AlertToTag, Alert.id == AlertToTag.alert_id)
        .join(AlertTag, AlertToTag.tag_id == AlertTag.id)
        .where(AlertTag.tag == tag),
    )
    return len(result.scalars().all())


async def alerts_closed_by_tag(db: AsyncSession, tag: str) -> int:
    result = await db.execute(
        select(Alert)
        .join(AlertToTag, Alert.id == AlertToTag.alert_id)
        .join(AlertTag, AlertToTag.tag_id == AlertTag.id)
        .where((Alert.status == "CLOSED") & (AlertTag.tag == tag)),
    )
    return len(result.scalars().all())


async def alerts_in_progress_by_tag(db: AsyncSession, tag: str) -> int:
    result = await db.execute(
        select(Alert)
        .join(AlertToTag, Alert.id == AlertToTag.alert_id)
        .join(AlertTag, AlertToTag.tag_id == AlertTag.id)
        .where((Alert.status == "IN_PROGRESS") & (AlertTag.tag == tag)),
    )
    return len(result.scalars().all())


async def alerts_open_by_tag(db: AsyncSession, tag: str) -> int:
    result = await db.execute(
        select(Alert)
        .join(AlertToTag, Alert.id == AlertToTag.alert_id)
        .join(AlertTag, AlertToTag.tag_id == AlertTag.id)
        .where((Alert.status == "OPEN") & (AlertTag.tag == tag)),
    )
    return len(result.scalars().all())


async def validate_source_exists(source: str, session: AsyncSession):
    # Check each of the FieldName tables and ensure each contains at least one entry for the source
    field_names = await get_field_names(source, session)
    asset_names = await get_asset_names(source, session)
    timefield_names = await get_timefield_names(source, session)
    alert_title_names = await get_alert_title_names(source, session)

    if not field_names or not asset_names or not timefield_names or not alert_title_names:
        raise HTTPException(status_code=400, detail="Source does not exist")


async def get_field_names(source: str, session: AsyncSession):
    result = await session.execute(select(FieldName.field_name).where(FieldName.source == source).distinct())
    return result.scalars().all()


async def get_asset_names(source: str, session: AsyncSession):
    result = await session.execute(select(AssetFieldName.field_name).where(AssetFieldName.source == source).distinct())
    return result.scalars().first()


async def get_timefield_names(source: str, session: AsyncSession):
    result = await session.execute(select(TimestampFieldName.field_name).where(TimestampFieldName.source == source).distinct())
    return result.scalars().first()


async def get_ioc_names(source: str, session: AsyncSession):
    result = await session.execute(select(IoCFieldName.field_name).where(IoCFieldName.source == source).distinct())
    return result.scalars().all()


async def get_alert_title_names(source: str, session: AsyncSession):
    result = await session.execute(select(AlertTitleFieldName.field_name).where(AlertTitleFieldName.source == source).distinct())
    return result.scalars().first()


# ! NOT USING FOR NOW. GETTING THE CUSTOMER CODE FROM THE ALERTS SOURCE FIELD INSTEAD ! #
async def get_customer_code_names(source: str, session: AsyncSession):
    result = await session.execute(select(CustomerCodeFieldName.field_name).where(CustomerCodeFieldName.source == source).distinct())
    return result.scalars().first()


async def get_customer_notification(customer_code: str, session: AsyncSession):
    result = await session.execute(select(Notification).where(Notification.customer_code == customer_code))
    notification = result.scalars().first()
    logger.info(f"Notification: {notification}")
    return [notification] if notification is not None else []


async def put_customer_notification(notification: PutNotification, session: AsyncSession):
    result = await session.execute(select(Notification).where(Notification.customer_code == notification.customer_code))
    existing_notification = result.scalars().first()
    if existing_notification is None:
        new_notification = Notification(**notification.dict())
        session.add(new_notification)
    else:
        existing_notification.customer_code = notification.customer_code
        existing_notification.shuffle_workflow_id = notification.shuffle_workflow_id
        existing_notification.enabled = notification.enabled
    await session.commit()


async def add_field_name(source: str, field_name: str, session: AsyncSession):
    result = await session.execute(select(FieldName).where((FieldName.source == source) & (FieldName.field_name == field_name)))
    existing_field = result.scalars().first()
    if existing_field is None:
        field = FieldName(source=source, field_name=field_name)
        session.add(field)


async def add_asset_name(source: str, asset_name: str, session: AsyncSession):
    result = await session.execute(
        select(AssetFieldName).where((AssetFieldName.source == source) & (AssetFieldName.field_name == asset_name)),
    )
    existing_asset = result.scalars().first()
    if existing_asset is None:
        asset = AssetFieldName(source=source, field_name=asset_name)
        session.add(asset)


async def add_timefield_name(source: str, timefield_name: str, session: AsyncSession):
    result = await session.execute(
        select(TimestampFieldName).where((TimestampFieldName.source == source) & (TimestampFieldName.field_name == timefield_name)),
    )
    existing_timefield = result.scalars().first()
    if existing_timefield is None:
        timefield = TimestampFieldName(source=source, field_name=timefield_name)
        session.add(timefield)


async def add_alert_title_name(source: str, alert_title_name: str, session: AsyncSession):
    result = await session.execute(
        select(AlertTitleFieldName).where((AlertTitleFieldName.source == source) & (AlertTitleFieldName.field_name == alert_title_name)),
    )
    existing_alert_title = result.scalars().first()
    if existing_alert_title is None:
        alert_title = AlertTitleFieldName(source=source, field_name=alert_title_name)
        session.add(alert_title)


async def add_ioc_name(source: str, ioc_name: str, session: AsyncSession):
    result = await session.execute(
        select(IoCFieldName).where((IoCFieldName.source == source) & (IoCFieldName.field_name == ioc_name)),
    )
    existing_ioc = result.scalars().first()
    if existing_ioc is None:
        ioc = IoCFieldName(source=source, field_name=ioc_name)
        session.add(ioc)


# ! NOT USING FOR NOW. GETTING THE CUSTOMER CODE FROM THE ALERTS SOURCE FIELD INSTEAD ! #
async def add_customer_code_name(source: str, customer_code_name: str, session: AsyncSession):
    result = await session.execute(
        select(CustomerCodeFieldName).where(
            (CustomerCodeFieldName.source == source) & (CustomerCodeFieldName.field_name == customer_code_name),
        ),
    )
    existing_customer_code = result.scalars().first()
    if existing_customer_code is None:
        customer_code = CustomerCodeFieldName(source=source, field_name=customer_code_name)
        session.add(customer_code)


async def replace_field_name(source: str, field_names: List[str], session: AsyncSession):
    # First delete all the field names for this source, then add the new field names
    result = await session.execute(select(FieldName).where(FieldName.source == source))
    fields = result.scalars().all()

    # Delete all the field names for this source
    for field in fields:
        await session.delete(field)

    # Add the new field names
    for field_name in field_names:
        await add_field_name(source, field_name, session)

    # Commit the changes
    await session.commit()


async def replace_ioc_name(source: str, ioc_names: List[str], session: AsyncSession):
    # First delete all the ioc names for this source, then add the new ioc names
    result = await session.execute(select(IoCFieldName).where(IoCFieldName.source == source))
    iocs = result.scalars().all()

    # Delete all the ioc names for this source
    for ioc in iocs:
        await session.delete(ioc)

    # Add the new ioc names
    for ioc_name in ioc_names:
        await add_ioc_name(source, ioc_name, session)

    # Commit the changes
    await session.commit()


async def replace_asset_name(source: str, asset_name: str, session: AsyncSession):
    # Load the current asset for this source from the DB, then delete it and replace it with `asset_name`
    result = await session.execute(select(AssetFieldName).where(AssetFieldName.source == source))
    assets = result.scalars().all()

    # Assuming you want to update the field_name for all assets matching the source
    for asset in assets:
        asset.field_name = asset_name

    # Commit the changes
    await session.commit()


async def replace_timefield_name(source: str, timefield_name: str, session: AsyncSession):
    # Load the current timefield for this source from the DB, then delete it and replace it with `timefield_name`
    result = await session.execute(select(TimestampFieldName).where(TimestampFieldName.source == source))
    timefields = result.scalars().all()

    # Assuming you want to update the field_name for all timefields matching the source
    for timefield in timefields:
        timefield.field_name = timefield_name

    # Commit the changes
    await session.commit()


async def replace_alert_title_name(source: str, alert_title_name: str, session: AsyncSession):
    # Load the current alert_title for this source from the DB, then delete it and replace it with `alert_title_name`
    result = await session.execute(select(AlertTitleFieldName).where(AlertTitleFieldName.source == source))
    alert_titles = result.scalars().all()

    # Assuming you want to update the field_name for all alert_titles matching the source
    for alert_title in alert_titles:
        alert_title.field_name = alert_title_name

    # Commit the changes
    await session.commit()


# ! NOT USING FOR NOW. GETTING THE CUSTOMER CODE FROM THE ALERTS SOURCE FIELD INSTEAD ! #
async def replace_customer_code_name(source: str, customer_code_name: str, session: AsyncSession):
    # Load the current customer_code for this source from the DB, then delete it and replace it with `customer_code_name`
    result = await session.execute(select(CustomerCodeFieldName).where(CustomerCodeFieldName.source == source))
    customer_codes = result.scalars().all()

    # Assuming you want to update the field_name for all customer_codes matching the source
    for customer_code in customer_codes:
        customer_code.field_name = customer_code_name

    # Commit the changes
    await session.commit()


async def delete_field_name(source: str, field_name: str, session: AsyncSession):
    logger.info(f"Deleting field name {field_name} for source {source}")
    field = await session.execute(select(FieldName).where((FieldName.source == source) & (FieldName.field_name == field_name)))
    field = field.scalar_one_or_none()
    if field:
        await session.delete(field)


async def delete_ioc_name(source: str, ioc_name: str, session: AsyncSession):
    logger.info(f"Deleting ioc name {ioc_name} for source {source}")
    ioc = await session.execute(
        select(IoCFieldName).where((IoCFieldName.source == source) & (IoCFieldName.field_name == ioc_name)),
    )
    ioc = ioc.scalar_one_or_none()
    if ioc:
        await session.delete(ioc)


async def delete_asset_name(source: str, asset_name: str, session: AsyncSession):
    logger.info(f"Deleting asset name {asset_name} for source {source}")
    asset = await session.execute(
        select(AssetFieldName).where((AssetFieldName.source == source) & (AssetFieldName.field_name == asset_name)),
    )
    asset = asset.scalar_one_or_none()
    if asset:
        await session.delete(asset)


async def delete_timefield_name(source: str, timefield_name: str, session: AsyncSession):
    logger.info(f"Deleting timefield name {timefield_name} for source {source}")
    timefield = await session.execute(
        select(TimestampFieldName).where((TimestampFieldName.source == source) & (TimestampFieldName.field_name == timefield_name)),
    )
    timefield = timefield.scalar_one_or_none()
    if timefield:
        await session.delete(timefield)


async def delete_alert_title_name(source: str, alert_title_name: str, session: AsyncSession):
    logger.info(f"Deleting alert title name {alert_title_name} for source {source}")
    alert_title = await session.execute(
        select(AlertTitleFieldName).where((AlertTitleFieldName.source == source) & (AlertTitleFieldName.field_name == alert_title_name)),
    )
    alert_title = alert_title.scalar_one_or_none()
    if alert_title:
        await session.delete(alert_title)


# ! NOT USING FOR NOW. GETTING THE CUSTOMER CODE FROM THE ALERTS SOURCE FIELD INSTEAD ! #
async def delete_customer_code_name(source: str, customer_code_name: str, session: AsyncSession):
    logger.info(f"Deleting customer code name {customer_code_name} for source {source}")
    customer_code = await session.execute(
        select(CustomerCodeFieldName).where(
            (CustomerCodeFieldName.source == source) & (CustomerCodeFieldName.field_name == customer_code_name),
        ),
    )
    customer_code = customer_code.scalar_one_or_none()
    if customer_code:
        await session.delete(customer_code)


async def create_alert(alert: AlertCreate, db: AsyncSession) -> Alert:
    db_alert = Alert(**alert.dict())
    db.add(db_alert)
    try:
        await db.flush()
        await db.refresh(db_alert)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Alert already exists")
    return db_alert


async def update_alert_status(update_alert_status: UpdateAlertStatus, db: AsyncSession) -> Alert:
    result = await db.execute(select(Alert).where(Alert.id == update_alert_status.alert_id))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = update_alert_status.status
    await db.commit()
    return alert


async def update_case_status(update_case_status: UpdateCaseStatus, db: AsyncSession) -> Case:
    result = await db.execute(select(Case).where(Case.id == update_case_status.case_id))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case.case_status = update_case_status.status
    await db.commit()
    return case


async def update_case_assigned_to(case_id: int, assigned_to: str, db: AsyncSession) -> Case:
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case.assigned_to = assigned_to
    await db.commit()
    return case


async def update_case_customer_code(case_id: int, customer_code: str, db: AsyncSession) -> Case:
    await customer_code_valid(customer_code, db)
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case.customer_code = customer_code
    await db.commit()
    return case


async def update_alert_assigned_to(alert_id: int, assigned_to: str, db: AsyncSession) -> Alert:
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.assigned_to = assigned_to
    await db.commit()
    return alert


async def increment_case_notification_count(case_id: int, db: AsyncSession) -> Case:
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Initialize notification_invoked_number to 0 if it is None
    if case.notification_invoked_number is None:
        case.notification_invoked_number = 0

    case.notification_invoked_number += 1
    await db.commit()
    return case


async def create_comment(comment: CommentCreate, db: AsyncSession) -> Comment:
    # Check if the alert exists
    result = await db.execute(select(Alert).options(selectinload(Alert.comments)).where(Alert.id == comment.alert_id))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Create comment with automatic timestamp if not provided
    comment_data = comment.dict()
    if comment_data.get("created_at") is None:
        comment_data["created_at"] = datetime.utcnow()

    db_comment = Comment(**comment_data)
    db.add(db_comment)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Comment already exists")
    return db_comment


async def edit_comment(comment: CommentEdit, db: AsyncSession) -> Comment:
    result = await db.execute(select(Comment).where(Comment.id == comment.comment_id))
    db_comment = result.scalars().first()
    if not db_comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    db_comment.comment = comment.comment
    db_comment.user_name = comment.user_name
    await db.commit()
    return db_comment


async def delete_comment(comment_id: int, db: AsyncSession) -> Comment:
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalars().first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    await db.execute(delete(Comment).where(Comment.id == comment_id))
    await db.commit()
    return comment


async def create_asset(asset: AssetCreate, db: AsyncSession) -> Asset:
    # Check if the alert exists
    result = await db.execute(select(Alert).options(selectinload(Alert.assets)).where(Alert.id == asset.alert_linked))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Check that the alert_context exists
    result = await db.execute(select(AlertContext).where(AlertContext.id == asset.alert_context_id))
    alert_context = result.scalars().first()
    if not alert_context:
        raise HTTPException(status_code=404, detail="Alert context not found")

    db_asset = Asset(**asset.dict())
    db.add(db_asset)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Asset already exists")
    return db_asset


async def create_alert_ioc(alert_ioc: AlertIoCCreate, db: AsyncSession) -> AlertToIoC:
    # Create the IoC instance
    db_alert_ioc = IoC(
        value=alert_ioc.ioc_value,
        type=alert_ioc.ioc_type,
        description=alert_ioc.ioc_description,
    )
    db.add(db_alert_ioc)
    await db.flush()

    # Create the AlertToIoC instance
    db_alert_to_ioc = AlertToIoC(alert_id=alert_ioc.alert_id, ioc_id=db_alert_ioc.id)
    db.add(db_alert_to_ioc)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Alert IoC already exists")
    return AlertToIoC(alert_id=db_alert_to_ioc.alert_id, ioc_id=db_alert_to_ioc.ioc_id)


async def delete_alert_ioc(ioc: AlertIoCDelete, db: AsyncSession) -> AlertToIoC:
    result = await db.execute(select(AlertToIoC).where((AlertToIoC.alert_id == ioc.alert_id) & (AlertToIoC.ioc_id == ioc.ioc_id)))
    alert_ioc = result.scalars().first()
    if not alert_ioc:
        raise HTTPException(status_code=404, detail="Alert IoC not found")

    await db.execute(delete(AlertToIoC).where((AlertToIoC.alert_id == ioc.alert_id) & (AlertToIoC.ioc_id == ioc.ioc_id)))

    # Delete the IoC from the IoC table
    await db.execute(delete(IoC).where(IoC.id == ioc.ioc_id))

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Error deleting alert IoC")

    return alert_ioc


async def create_alert_tag(alert_tag: AlertTagCreate, db: AsyncSession) -> AlertTag:
    # Create the AlertTag instance
    db_alert_tag = AlertTag(**alert_tag.dict())
    db.add(db_alert_tag)
    await db.flush()

    # Create the AlertToTag instance
    db_alert_to_tag = AlertToTag(alert_id=alert_tag.alert_id, tag_id=db_alert_tag.id)
    db.add(db_alert_to_tag)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Alert tag already exists")
    return db_alert_tag


async def add_alert_tag_if_not_exists(alert_tag: AlertTagCreate, db: AsyncSession) -> AlertTag:
    # Check if the tag already exists
    result = await db.execute(select(AlertTag).where(AlertTag.tag == alert_tag.tag))
    existing_tag = result.scalars().first()

    if existing_tag:
        logger.info(f"Tag {alert_tag.tag} already exists with ID {alert_tag.alert_id}")
        return None

    # If it doesn't exist, create a new one
    return await create_alert_tag(alert_tag, db)


async def delete_alert_tag(alert_id: int, tag_id: int, db: AsyncSession):
    result = await db.execute(select(AlertTag).where(AlertTag.id == tag_id))
    alert_tag = result.scalars().first()
    if not alert_tag:
        raise HTTPException(status_code=404, detail="Alert tag not found")

    result = await db.execute(select(AlertToTag).where((AlertToTag.alert_id == alert_id) & (AlertToTag.tag_id == tag_id)))
    alert_to_tag = result.scalars().first()
    if not alert_to_tag:
        raise HTTPException(status_code=404, detail="Alert to tag link not found")

    await db.execute(delete(AlertToTag).where((AlertToTag.alert_id == alert_id) & (AlertToTag.tag_id == tag_id)))

    # Delete the tag from the AlertTag table
    await db.execute(delete(AlertTag).where(AlertTag.id == tag_id))

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Error deleting alert tag")

    return alert_tag


async def create_alert_context(alert_context: AlertContextCreate, db: AsyncSession) -> AlertContext:
    db_alert_context = AlertContext(**alert_context.dict())
    db.add(db_alert_context)
    try:
        await db.flush()
        await db.refresh(db_alert_context)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Alert context already exists")
    return db_alert_context


async def get_alert_by_id(alert_id: int, db: AsyncSession) -> AlertOut:
    result = await db.execute(
        select(Alert)
        .where(Alert.id == alert_id)
        .options(
            selectinload(Alert.comments),
            selectinload(Alert.assets),
            selectinload(Alert.cases).selectinload(CaseAlertLink.case),
            selectinload(Alert.tags).selectinload(AlertToTag.tag),
        ),
    )
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
    assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
    tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
    linked_cases = [LinkedCaseCreate(**case_alert_link.case.__dict__) for case_alert_link in alert.cases]

    alert_out = AlertOut(
        id=alert.id,
        alert_creation_time=alert.alert_creation_time,
        time_closed=alert.time_closed,
        alert_name=alert.alert_name,
        alert_description=alert.alert_description,
        status=alert.status,
        customer_code=alert.customer_code,
        source=alert.source,
        assigned_to=alert.assigned_to,
        comments=comments,
        assets=assets,
        tags=tags,
        linked_cases=linked_cases,
    )

    return alert_out


async def list_alerts(db: AsyncSession, page: int = 1, page_size: int = 25, order: str = "desc") -> List[AlertOut]:
    offset = (page - 1) * page_size
    order_by = asc(Alert.id) if order == "asc" else desc(Alert.id)

    result = await db.execute(
        select(Alert)
        .options(
            selectinload(Alert.comments),
            selectinload(Alert.assets),
            selectinload(Alert.cases).selectinload(CaseAlertLink.case),
            selectinload(Alert.tags).selectinload(AlertToTag.tag),
            selectinload(Alert.iocs).selectinload(AlertToIoC.ioc),
        )
        .order_by(order_by)
        .offset(offset)
        .limit(page_size),
    )

    alerts = result.scalars().all()
    alerts_out = []
    for alert in alerts:
        comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
        assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
        tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
        iocs = [IoCBase(**alert_to_ioc.ioc.__dict__) for alert_to_ioc in alert.iocs]
        linked_cases = [LinkedCaseCreate(**case_alert_link.case.__dict__) for case_alert_link in alert.cases]
        alert_out = AlertOut(
            id=alert.id,
            alert_creation_time=alert.alert_creation_time,
            time_closed=alert.time_closed,
            alert_name=alert.alert_name,
            alert_description=alert.alert_description,
            status=alert.status,
            customer_code=alert.customer_code,
            source=alert.source,
            assigned_to=alert.assigned_to,
            comments=comments,
            assets=assets,
            tags=tags,
            iocs=iocs,
            linked_cases=linked_cases,
        )
        alerts_out.append(alert_out)
    return alerts_out


async def create_case(case: CaseCreate, db: AsyncSession) -> Case:
    db_case = Case(**case.dict())
    db.add(db_case)
    try:
        await db.flush()
        await db.refresh(db_case)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Case already exists")
    return db_case


async def create_case_from_alert(alert_id: int, db: AsyncSession) -> Case:
    logger.info(f"Creating case from alert {alert_id}")
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    case = Case(
        case_name=alert.alert_name,
        case_description=alert.alert_description,
        case_status=alert.status,
        assigned_to=alert.assigned_to,
        customer_code=alert.customer_code,
    )
    db.add(case)
    try:
        await db.flush()
        await db.refresh(case)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Case already exists")
    return case


async def create_case_alert_link(case_alert_link: CaseAlertLinkCreate, db: AsyncSession) -> CaseAlertLink:
    # Check if the case exists
    result = await db.execute(select(Case).where(Case.id == case_alert_link.case_id))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Check if the alert exists
    result = await db.execute(select(Alert).where(Alert.id == case_alert_link.alert_id))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    db_case_alert_link = CaseAlertLink(**case_alert_link.dict())
    db.add(db_case_alert_link)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Case alert link already exists")
    return db_case_alert_link


async def case_alert_unlink(case_alert_unlink: CaseAlertUnLink, db: AsyncSession) -> CaseAlertUnLinkResponse:
    result = await db.execute(
        select(CaseAlertLink).where(
            (CaseAlertLink.case_id == case_alert_unlink.case_id) & (CaseAlertLink.alert_id == case_alert_unlink.alert_id),
        ),
    )
    case_alert_link = result.scalars().first()
    if not case_alert_link:
        raise HTTPException(status_code=404, detail="Case alert link not found")
    await db.execute(
        delete(CaseAlertLink).where(
            (CaseAlertLink.case_id == case_alert_unlink.case_id) & (CaseAlertLink.alert_id == case_alert_unlink.alert_id),
        ),
    )
    await db.commit()
    return CaseAlertUnLinkResponse(success=True, message="Case alert link deleted successfully")


async def create_case_alert_links_bulk(case_alert_links: CaseAlertLinksCreate, db: AsyncSession) -> List[CaseAlertLink]:
    db_case_alert_links = [CaseAlertLink(case_id=case_alert_links.case_id, alert_id=alert_id) for alert_id in case_alert_links.alert_ids]
    db.add_all(db_case_alert_links)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Case alert links already exist")
    return db_case_alert_links


async def get_case_by_id(case_id: int, db: AsyncSession) -> CaseOut:
    result = await db.execute(
        select(Case)
        .where(Case.id == case_id)
        .options(
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.comments),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.assets),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.tags).selectinload(AlertToTag.tag),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.cases).selectinload(CaseAlertLink.case),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.iocs).selectinload(AlertToIoC.ioc),
        ),
    )
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    alerts_out = []
    for case_alert_link in case.alerts:
        alert = case_alert_link.alert
        comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
        assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
        tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
        linked_cases = [LinkedCaseCreate(**case_alert_link.case.__dict__) for case_alert_link in alert.cases]
        iocs = [IoCBase(**alert_to_ioc.ioc.__dict__) for alert_to_ioc in alert.iocs]
        alert_out = AlertOut(
            id=alert.id,
            alert_creation_time=alert.alert_creation_time,
            time_closed=alert.time_closed,
            alert_name=alert.alert_name,
            alert_description=alert.alert_description,
            status=alert.status,
            customer_code=alert.customer_code,
            source=alert.source,
            assigned_to=alert.assigned_to,
            comments=comments,
            assets=assets,
            tags=tags,
            linked_cases=linked_cases,
            iocs=iocs,
        )
        alerts_out.append(alert_out)
    case_out = CaseOut(
        id=case.id,
        case_name=case.case_name,
        case_description=case.case_description,
        assigned_to=case.assigned_to,
        alerts=alerts_out,
        case_creation_time=case.case_creation_time,
        customer_code=case.customer_code,
        notification_invoked_number=case.notification_invoked_number or 0,
    )
    return case_out


async def list_cases(db: AsyncSession) -> List[CaseOut]:
    result = await db.execute(
        select(Case).options(
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.comments),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.assets),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.tags).selectinload(AlertToTag.tag),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.cases).selectinload(CaseAlertLink.case),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.iocs).selectinload(AlertToIoC.ioc),
        ),
    )
    cases = result.scalars().all()
    cases_out = []
    for case in cases:
        alerts_out = []
        for case_alert_link in case.alerts:
            alert = case_alert_link.alert
            comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
            assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
            tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
            linked_cases = [LinkedCaseCreate(**case_alert_link.case.__dict__) for case_alert_link in alert.cases]
            iocs = [IoCBase(**alert_to_ioc.ioc.__dict__) for alert_to_ioc in alert.iocs]
            alert_out = AlertOut(
                id=alert.id,
                alert_creation_time=alert.alert_creation_time,
                time_closed=alert.time_closed,
                alert_name=alert.alert_name,
                alert_description=alert.alert_description,
                status=alert.status,
                customer_code=alert.customer_code,
                source=alert.source,
                assigned_to=alert.assigned_to,
                comments=comments,
                assets=assets,
                tags=tags,
                linked_cases=linked_cases,
                iocs=iocs,
            )
            alerts_out.append(alert_out)
        case_out = CaseOut(
            id=case.id,
            case_name=case.case_name,
            case_description=case.case_description,
            assigned_to=case.assigned_to,
            alerts=alerts_out,
            case_creation_time=case.case_creation_time,
            case_status=case.case_status,
            customer_code=case.customer_code,
            notification_invoked_number=case.notification_invoked_number or 0,
        )
        cases_out.append(case_out)
    return cases_out


async def list_cases_by_status(status: str, db: AsyncSession) -> List[CaseOut]:
    result = await db.execute(
        select(Case)
        .where(Case.case_status == status)
        .options(
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.comments),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.assets),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.tags).selectinload(AlertToTag.tag),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.cases).selectinload(CaseAlertLink.case),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.iocs).selectinload(AlertToIoC.ioc),
        ),
    )
    cases = result.scalars().all()
    cases_out = []
    for case in cases:
        alerts_out = []
        for case_alert_link in case.alerts:
            alert = case_alert_link.alert
            comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
            assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
            tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
            linked_cases = [LinkedCaseCreate(**case_alert_link.case.__dict__) for case_alert_link in alert.cases]
            iocs = [IoCBase(**alert_to_ioc.ioc.__dict__) for alert_to_ioc in alert.iocs]
            alert_out = AlertOut(
                id=alert.id,
                alert_creation_time=alert.alert_creation_time,
                time_closed=alert.time_closed,
                alert_name=alert.alert_name,
                alert_description=alert.alert_description,
                status=alert.status,
                customer_code=alert.customer_code,
                source=alert.source,
                assigned_to=alert.assigned_to,
                comments=comments,
                assets=assets,
                tags=tags,
                linked_cases=linked_cases,
                iocs=iocs,
            )
            alerts_out.append(alert_out)
        case_out = CaseOut(
            id=case.id,
            case_name=case.case_name,
            case_description=case.case_description,
            assigned_to=case.assigned_to,
            alerts=alerts_out,
            customer_code=case.customer_code,
        )
        cases_out.append(case_out)
    return cases_out


async def list_cases_by_assigned_to(assigned_to: str, db: AsyncSession) -> List[CaseOut]:
    result = await db.execute(
        select(Case)
        .where(Case.assigned_to == assigned_to)
        .options(
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.comments),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.assets),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.tags).selectinload(AlertToTag.tag),
        ),
    )
    cases = result.scalars().all()
    cases_out = []
    for case in cases:
        alerts_out = []
        for case_alert_link in case.alerts:
            alert = case_alert_link.alert
            comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
            assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
            tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
            alert_out = AlertOut(
                id=alert.id,
                alert_creation_time=alert.alert_creation_time,
                time_closed=alert.time_closed,
                alert_name=alert.alert_name,
                alert_description=alert.alert_description,
                status=alert.status,
                customer_code=alert.customer_code,
                source=alert.source,
                assigned_to=alert.assigned_to,
                comments=comments,
                assets=assets,
                tags=tags,
            )
            alerts_out.append(alert_out)
        case_out = CaseOut(
            id=case.id,
            case_name=case.case_name,
            case_description=case.case_description,
            assigned_to=case.assigned_to,
            alerts=alerts_out,
            customer_code=case.customer_code,
        )
        cases_out.append(case_out)
    return cases_out


async def list_cases_by_asset_name(asset_name: str, db: AsyncSession) -> List[CaseOut]:
    result = await db.execute(
        select(Case)
        .join(CaseAlertLink)
        .join(Alert)
        .join(Asset)
        .where(Asset.asset_name == asset_name)
        .options(
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.comments),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.assets),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.tags).selectinload(AlertToTag.tag),
        ),
    )
    cases = result.scalars().all()
    cases_out = []
    for case in cases:
        alerts_out = []
        for case_alert_link in case.alerts:
            alert = case_alert_link.alert
            comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
            assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
            tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
            alert_out = AlertOut(
                id=alert.id,
                alert_creation_time=alert.alert_creation_time,
                time_closed=alert.time_closed,
                alert_name=alert.alert_name,
                alert_description=alert.alert_description,
                status=alert.status,
                customer_code=alert.customer_code,
                source=alert.source,
                assigned_to=alert.assigned_to,
                comments=comments,
                assets=assets,
                tags=tags,
            )
            alerts_out.append(alert_out)
        case_out = CaseOut(
            id=case.id,
            case_name=case.case_name,
            case_description=case.case_description,
            assigned_to=case.assigned_to,
            alerts=alerts_out,
            customer_code=case.customer_code,
        )
        cases_out.append(case_out)
    return cases_out


async def list_cases_by_customer_code(customer_code: str, db: AsyncSession) -> List[CaseOut]:
    result = await db.execute(
        select(Case)
        .where(Case.customer_code == customer_code)
        .options(
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.comments),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.assets),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.tags).selectinload(AlertToTag.tag),
        ),
    )
    cases = result.scalars().all()
    cases_out = []
    for case in cases:
        alerts_out = []
        for case_alert_link in case.alerts:
            alert = case_alert_link.alert
            comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
            assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
            tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
            alert_out = AlertOut(
                id=alert.id,
                alert_creation_time=alert.alert_creation_time,
                time_closed=alert.time_closed,
                alert_name=alert.alert_name,
                alert_description=alert.alert_description,
                status=alert.status,
                customer_code=alert.customer_code,
                source=alert.source,
                assigned_to=alert.assigned_to,
                comments=comments,
                assets=assets,
                tags=tags,
            )
            alerts_out.append(alert_out)
        case_out = CaseOut(
            id=case.id,
            case_name=case.case_name,
            case_description=case.case_description,
            assigned_to=case.assigned_to,
            alerts=alerts_out,
            customer_code=case.customer_code,
        )
        cases_out.append(case_out)
    return cases_out


async def get_alert_context_by_id(alert_context_id: int, db: AsyncSession) -> AlertContext:
    result = await db.execute(select(AlertContext).where(AlertContext.id == alert_context_id))
    alert_context = result.scalars().first()
    if not alert_context:
        raise HTTPException(status_code=404, detail="Alert context not found")
    return alert_context


async def list_alerts_by_ioc(ioc_value: str, db: AsyncSession, page: int = 1, page_size: int = 25, order: str = "desc") -> List[AlertOut]:
    offset = (page - 1) * page_size
    order_by = asc(Alert.id) if order == "asc" else desc(Alert.id)
    logger.info(f"Listing alerts by IoC {ioc_value}")

    result = await db.execute(
        select(Alert)
        .join(AlertToIoC)
        .join(IoC)
        .where(IoC.value == ioc_value)
        .options(
            selectinload(Alert.comments),
            selectinload(Alert.assets),
            selectinload(Alert.cases),
            selectinload(Alert.tags).selectinload(AlertToTag.tag),
            selectinload(Alert.iocs).selectinload(AlertToIoC.ioc),
        )
        .order_by(order_by)
        .offset(offset)
        .limit(page_size),
    )

    alerts = result.scalars().all()
    alerts_out = []
    for alert in alerts:
        comments: List[CommentBase] = [CommentBase(**comment.__dict__) for comment in alert.comments]
        assets: List[AssetBase] = [AssetBase(**asset.__dict__) for asset in alert.assets]
        tags: List[AlertTagBase] = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
        iocs: List[IoCBase] = [IoCBase(**alert_to_ioc.ioc.__dict__) for alert_to_ioc in alert.iocs]
        alert_out = AlertOut(
            id=alert.id,
            alert_creation_time=alert.alert_creation_time,
            time_closed=alert.time_closed,
            alert_name=alert.alert_name,
            alert_description=alert.alert_description,
            status=alert.status,
            customer_code=alert.customer_code,
            source=alert.source,
            assigned_to=alert.assigned_to,
            comments=comments,
            assets=assets,
            tags=tags,
            iocs=iocs,
        )
        alerts_out.append(alert_out)
    return alerts_out


async def list_alerts_by_tag(tag: str, db: AsyncSession, page: int = 1, page_size: int = 25, order: str = "desc") -> List[AlertOut]:
    offset = (page - 1) * page_size
    order_by = asc(Alert.id) if order == "asc" else desc(Alert.id)

    result = await db.execute(
        select(Alert)
        .join(AlertToTag)
        .join(AlertTag)
        .where(AlertTag.tag == tag)
        .options(
            selectinload(Alert.comments),
            selectinload(Alert.assets),
            selectinload(Alert.cases),
            selectinload(Alert.tags).selectinload(AlertToTag.tag),
            selectinload(Alert.iocs).selectinload(AlertToIoC.ioc),
        )
        .order_by(order_by)
        .offset(offset)
        .limit(page_size),
    )
    alerts = result.scalars().all()
    alerts_out = []
    for alert in alerts:
        comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
        assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
        tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
        iocs = [IoCBase(**alert_to_ioc.ioc.__dict__) for alert_to_ioc in alert.iocs]
        alert_out = AlertOut(
            id=alert.id,
            alert_creation_time=alert.alert_creation_time,
            time_closed=alert.time_closed,
            alert_name=alert.alert_name,
            alert_description=alert.alert_description,
            status=alert.status,
            customer_code=alert.customer_code,
            source=alert.source,
            assigned_to=alert.assigned_to,
            comments=comments,
            assets=assets,
            tags=tags,
            iocs=iocs,
        )
        alerts_out.append(alert_out)
    return alerts_out


async def list_alert_by_status(status: str, db: AsyncSession, page: int = 1, page_size: int = 25, order: str = "desc") -> List[AlertOut]:
    offset = (page - 1) * page_size
    order_by = asc(Alert.id) if order == "asc" else desc(Alert.id)

    result = await db.execute(
        select(Alert)
        .where(Alert.status == status)
        .options(
            selectinload(Alert.comments),
            selectinload(Alert.assets),
            selectinload(Alert.cases),
            selectinload(Alert.tags).selectinload(AlertToTag.tag),
            selectinload(Alert.iocs).selectinload(AlertToIoC.ioc),
        )
        .order_by(order_by)
        .offset(offset)
        .limit(page_size),
    )

    alerts = result.scalars().all()
    alerts_out = []
    for alert in alerts:
        comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
        assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
        tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
        iocs = [IoCBase(**alert_to_ioc.ioc.__dict__) for alert_to_ioc in alert.iocs]
        alert_out = AlertOut(
            id=alert.id,
            alert_creation_time=alert.alert_creation_time,
            time_closed=alert.time_closed,
            alert_name=alert.alert_name,
            alert_description=alert.alert_description,
            status=alert.status,
            customer_code=alert.customer_code,
            source=alert.source,
            assigned_to=alert.assigned_to,
            comments=comments,
            assets=assets,
            tags=tags,
            iocs=iocs,
        )
        alerts_out.append(alert_out)
    return alerts_out


async def list_alerts_by_asset_name(
    asset_name: str,
    db: AsyncSession,
    page: int = 1,
    page_size: int = 25,
    order: str = "desc",
) -> List[AlertOut]:
    offset = (page - 1) * page_size
    order_by = asc(Alert.id) if order == "asc" else desc(Alert.id)

    result = await db.execute(
        select(Alert)
        .join(Asset)
        .where(Asset.asset_name == asset_name)
        .options(
            selectinload(Alert.comments),
            selectinload(Alert.assets),
            selectinload(Alert.cases),
            selectinload(Alert.tags).selectinload(AlertToTag.tag),
        )
        .order_by(order_by)
        .offset(offset)
        .limit(page_size),
    )
    alerts = result.scalars().all()
    alerts_out = []
    for alert in alerts:
        comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
        assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
        tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
        alert_out = AlertOut(
            id=alert.id,
            alert_creation_time=alert.alert_creation_time,
            time_closed=alert.time_closed,
            alert_name=alert.alert_name,
            alert_description=alert.alert_description,
            status=alert.status,
            customer_code=alert.customer_code,
            source=alert.source,
            assigned_to=alert.assigned_to,
            comments=comments,
            assets=assets,
            tags=tags,
        )
        alerts_out.append(alert_out)
    return alerts_out


async def list_alert_by_assigned_to(
    assigned_to: str,
    db: AsyncSession,
    page: int = 1,
    page_size: int = 25,
    order: str = "desc",
) -> List[AlertOut]:
    offset = (page - 1) * page_size
    order_by = asc(Alert.id) if order == "asc" else desc(Alert.id)

    result = await db.execute(
        select(Alert)
        .where(Alert.assigned_to == assigned_to)
        .options(
            selectinload(Alert.comments),
            selectinload(Alert.assets),
            selectinload(Alert.cases),
            selectinload(Alert.tags).selectinload(AlertToTag.tag),
        )
        .order_by(order_by)
        .offset(offset)
        .limit(page_size),
    )
    alerts = result.scalars().all()
    alerts_out = []
    for alert in alerts:
        comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
        assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
        tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
        alert_out = AlertOut(
            id=alert.id,
            alert_creation_time=alert.alert_creation_time,
            time_closed=alert.time_closed,
            alert_name=alert.alert_name,
            alert_description=alert.alert_description,
            status=alert.status,
            customer_code=alert.customer_code,
            source=alert.source,
            assigned_to=alert.assigned_to,
            comments=comments,
            assets=assets,
            tags=tags,
        )
        alerts_out.append(alert_out)
    return alerts_out


async def list_alerts_by_title(
    alert_title: str,
    db: AsyncSession,
    page: int = 1,
    page_size: int = 25,
    order: str = "desc",
) -> List[AlertOut]:
    offset = (page - 1) * page_size
    order_by = asc(Alert.id) if order == "asc" else desc(Alert.id)

    result = await db.execute(
        select(Alert)
        .where(Alert.alert_name.like(f"%{alert_title}%"))
        .options(
            selectinload(Alert.comments),
            selectinload(Alert.assets),
            selectinload(Alert.cases),
            selectinload(Alert.tags).selectinload(AlertToTag.tag),
        )
        .order_by(order_by)
        .offset(offset)
        .limit(page_size),
    )
    alerts = result.scalars().all()
    alerts_out = []
    for alert in alerts:
        comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
        assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
        tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
        alert_out = AlertOut(
            id=alert.id,
            alert_creation_time=alert.alert_creation_time,
            time_closed=alert.time_closed,
            alert_name=alert.alert_name,
            alert_description=alert.alert_description,
            status=alert.status,
            customer_code=alert.customer_code,
            source=alert.source,
            assigned_to=alert.assigned_to,
            comments=comments,
            assets=assets,
            tags=tags,
        )
        alerts_out.append(alert_out)
    return alerts_out


async def list_alerts_by_customer_code(
    customer_code: str,
    db: AsyncSession,
    page: int = 1,
    page_size: int = 25,
    order: str = "desc",
) -> List[AlertOut]:
    offset = (page - 1) * page_size
    order_by = asc(Alert.id) if order == "asc" else desc(Alert.id)

    result = await db.execute(
        select(Alert)
        .where(Alert.customer_code == customer_code)
        .options(
            selectinload(Alert.comments),
            selectinload(Alert.assets),
            selectinload(Alert.cases),
            selectinload(Alert.tags).selectinload(AlertToTag.tag),
        )
        .order_by(order_by)
        .offset(offset)
        .limit(page_size),
    )
    alerts = result.scalars().all()
    alerts_out = []
    for alert in alerts:
        comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
        assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
        tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
        alert_out = AlertOut(
            id=alert.id,
            alert_creation_time=alert.alert_creation_time,
            time_closed=alert.time_closed,
            alert_name=alert.alert_name,
            alert_description=alert.alert_description,
            status=alert.status,
            customer_code=alert.customer_code,
            source=alert.source,
            assigned_to=alert.assigned_to,
            comments=comments,
            assets=assets,
            tags=tags,
        )
        alerts_out.append(alert_out)
    return alerts_out


async def list_alerts_by_source(
    source: str,
    db: AsyncSession,
    page: int = 1,
    page_size: int = 25,
    order: str = "desc",
) -> List[AlertOut]:
    offset = (page - 1) * page_size
    order_by = asc(Alert.id) if order == "asc" else desc(Alert.id)

    result = await db.execute(
        select(Alert)
        .where(Alert.source == source)
        .options(
            selectinload(Alert.comments),
            selectinload(Alert.assets),
            selectinload(Alert.cases),
            selectinload(Alert.tags).selectinload(AlertToTag.tag),
        )
        .order_by(order_by)
        .offset(offset)
        .limit(page_size),
    )
    alerts = result.scalars().all()
    alerts_out = []
    for alert in alerts:
        comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
        assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
        tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
        alert_out = AlertOut(
            id=alert.id,
            alert_creation_time=alert.alert_creation_time,
            time_closed=alert.time_closed,
            alert_name=alert.alert_name,
            alert_description=alert.alert_description,
            status=alert.status,
            customer_code=alert.customer_code,
            source=alert.source,
            assigned_to=alert.assigned_to,
            comments=comments,
            assets=assets,
            tags=tags,
        )
        alerts_out.append(alert_out)
    return alerts_out


async def list_alerts_multiple_filters(
    db: AsyncSession,
    assigned_to: Optional[str] = None,
    alert_title: Optional[str] = None,
    customer_code: Optional[str] = None,
    source: Optional[str] = None,
    asset_name: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    ioc_value: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
    order: str = "desc",
) -> List[AlertOut]:
    offset = (page - 1) * page_size
    order_by = asc(Alert.id) if order == "asc" else desc(Alert.id)

    # Build dynamic filters
    filters = []
    if assigned_to:
        filters.append(Alert.assigned_to == assigned_to)
    if alert_title:
        filters.append(Alert.alert_name.like(f"%{alert_title}%"))
    if customer_code:
        filters.append(Alert.customer_code == customer_code)
    if source:
        filters.append(Alert.source == source)
    if asset_name:
        filters.append(Asset.asset_name == asset_name)
    if status:
        filters.append(Alert.status == status)
    if tags:
        filters.append(AlertTag.tag.in_(tags))
    if ioc_value:
        filters.append(IoC.value == ioc_value)

    # Build the query with dynamic filters
    query = (
        select(Alert)
        .distinct(Alert.id)
        .join(Asset, Asset.alert_linked == Alert.id, isouter=True)  # Join with Asset table
        .join(AlertToTag, AlertToTag.alert_id == Alert.id, isouter=True)  # Join with AlertToTag table
        .join(AlertTag, AlertToTag.tag_id == AlertTag.id, isouter=True)  # Join with AlertTag table
        .join(AlertToIoC, AlertToIoC.alert_id == Alert.id, isouter=True)  # Join with AlertToIoC table
        .join(IoC, AlertToIoC.ioc_id == IoC.id, isouter=True)  # Join with IoC table
        .where(*filters)
        .options(
            selectinload(Alert.comments),
            selectinload(Alert.assets),
            selectinload(Alert.cases).selectinload(CaseAlertLink.case),
            selectinload(Alert.tags).selectinload(AlertToTag.tag),
            selectinload(Alert.iocs).selectinload(AlertToIoC.ioc),
        )
        .order_by(order_by)
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    alerts = result.scalars().all()

    alerts_out = []
    for alert in alerts:
        comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
        assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
        tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
        iocs = [IoCBase(**alert_to_ioc.ioc.__dict__) for alert_to_ioc in alert.iocs]
        linked_cases = [LinkedCaseCreate(**case_alert_link.case.__dict__) for case_alert_link in alert.cases]
        alert_out = AlertOut(
            id=alert.id,
            alert_creation_time=alert.alert_creation_time,
            time_closed=alert.time_closed,
            alert_name=alert.alert_name,
            alert_description=alert.alert_description,
            status=alert.status,
            customer_code=alert.customer_code,
            source=alert.source,
            assigned_to=alert.assigned_to,
            comments=comments,
            assets=assets,
            tags=tags,
            iocs=iocs,
            linked_cases=linked_cases,
        )
        alerts_out.append(alert_out)

    return alerts_out


async def list_alerts_for_user(
    user: User,
    session: AsyncSession,
    page: int = 1,
    page_size: int = 25,
    order: str = "desc",
) -> List[AlertOut]:
    """List alerts filtered by user's customer access"""

    base_query = select(Alert).options(
        selectinload(Alert.comments),
        selectinload(Alert.assets),
        selectinload(Alert.cases).selectinload(CaseAlertLink.case),
        selectinload(Alert.tags).selectinload(AlertToTag.tag),
    )

    # Apply customer filtering
    filtered_query = await customer_access_handler.filter_query_by_customer_access(user, session, base_query, Alert.customer_code)

    offset = (page - 1) * page_size
    order_by = asc(Alert.id) if order == "asc" else desc(Alert.id)

    final_query = filtered_query.order_by(order_by).offset(offset).limit(page_size)
    result = await session.execute(final_query)
    alerts = result.scalars().all()

    # Convert to AlertOut objects
    alerts_out = []
    for alert in alerts:
        comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
        assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
        tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
        linked_cases = [LinkedCaseCreate(**case_alert_link.case.__dict__) for case_alert_link in alert.cases]

        alert_out = AlertOut(
            id=alert.id,
            alert_creation_time=alert.alert_creation_time,
            time_closed=alert.time_closed,
            alert_name=alert.alert_name,
            alert_description=alert.alert_description,
            status=alert.status,
            customer_code=alert.customer_code,
            source=alert.source,
            assigned_to=alert.assigned_to,
            comments=comments,
            assets=assets,
            tags=tags,
            linked_cases=linked_cases,
        )
        alerts_out.append(alert_out)

    return alerts_out


async def list_cases_for_user(
    user: User,
    session: AsyncSession,
) -> List[CaseOut]:
    """List cases filtered by user's customer access"""

    base_query = select(Case).options(
        selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.comments),
        selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.assets),
        selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.tags).selectinload(AlertToTag.tag),
        selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.cases).selectinload(CaseAlertLink.case),
        selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.iocs).selectinload(AlertToIoC.ioc),
    )

    # Apply customer filtering
    filtered_query = await customer_access_handler.filter_query_by_customer_access(user, session, base_query, Case.customer_code)

    result = await session.execute(filtered_query)
    cases = result.scalars().all()

    # Convert to CaseOut objects (using same logic as list_cases)
    cases_out = []
    for case in cases:
        alerts_out = []
        for case_alert_link in case.alerts:
            alert = case_alert_link.alert
            comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
            assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
            tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
            linked_cases = [LinkedCaseCreate(**case_alert_link.case.__dict__) for case_alert_link in alert.cases]
            iocs = [IoCBase(**alert_to_ioc.ioc.__dict__) for alert_to_ioc in alert.iocs]
            alert_out = AlertOut(
                id=alert.id,
                alert_creation_time=alert.alert_creation_time,
                time_closed=alert.time_closed,
                alert_name=alert.alert_name,
                alert_description=alert.alert_description,
                status=alert.status,
                customer_code=alert.customer_code,
                source=alert.source,
                assigned_to=alert.assigned_to,
                comments=comments,
                assets=assets,
                tags=tags,
                linked_cases=linked_cases,
                iocs=iocs,
            )
            alerts_out.append(alert_out)
        case_out = CaseOut(
            id=case.id,
            case_name=case.case_name,
            case_description=case.case_description,
            assigned_to=case.assigned_to,
            alerts=alerts_out,
            case_creation_time=case.case_creation_time,
            case_status=case.case_status,
            customer_code=case.customer_code,
            notification_invoked_number=case.notification_invoked_number or 0,
        )
        cases_out.append(case_out)
    return cases_out


async def delete_comments(alert_id: int, db: AsyncSession):
    result = await db.execute(select(Comment).where(Comment.alert_id == alert_id))
    comments = result.scalars().all()
    for comment in comments:
        await db.execute(delete(Comment).where(Comment.id == comment.id))


async def delete_assets(alert_id: int, db: AsyncSession):
    result = await db.execute(select(Asset).where(Asset.alert_linked == alert_id))
    assets = result.scalars().all()
    for asset in assets:
        await db.execute(delete(Asset).where(Asset.id == asset.id))
        context_result = await db.execute(select(Asset).where(Asset.alert_context_id == asset.alert_context_id))
        if not context_result.scalars().all():
            await db.execute(delete(AlertContext).where(AlertContext.id == asset.alert_context_id))


async def delete_tags(alert_id: int, db: AsyncSession):
    result = await db.execute(select(AlertToTag).where(AlertToTag.alert_id == alert_id))
    alert_to_tags = result.scalars().all()
    for alert_to_tag in alert_to_tags:
        await db.execute(
            delete(AlertToTag).where((AlertToTag.alert_id == alert_to_tag.alert_id) & (AlertToTag.tag_id == alert_to_tag.tag_id)),
        )


async def delete_iocs(alert_id: int, db: AsyncSession):
    result = await db.execute(select(AlertToIoC).where(AlertToIoC.alert_id == alert_id))
    alert_to_iocs = result.scalars().all()
    for alert_to_ioc in alert_to_iocs:
        await db.execute(
            delete(AlertToIoC).where((AlertToIoC.alert_id == alert_to_ioc.alert_id) & (AlertToIoC.ioc_id == alert_to_ioc.ioc_id)),
        )


async def is_alert_linked_to_case(alert_id: int, db: AsyncSession) -> bool:
    result = await db.execute(select(CaseAlertLink).where(CaseAlertLink.alert_id == alert_id))
    linked_cases = result.scalars().all()

    if linked_cases:
        raise HTTPException(status_code=400, detail="Alert is linked to a case, and cannot be deleted")
    return False


async def delete_alert(alert_id: int, db: AsyncSession):
    """
    Delete an alert from the database.

    Args:
        alert_id (int): The ID of the alert to be deleted.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the alert is not found or there is an error deleting the alert.

    """
    logger.info(f"Deleting alert {alert_id}")
    result = await db.execute(
        select(Alert)
        .options(
            selectinload(Alert.comments),
            selectinload(Alert.assets).selectinload(Asset.alert_context),
            selectinload(Alert.tags),
            selectinload(Alert.iocs),
        )
        .where(Alert.id == alert_id),
    )
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await delete_comments(alert_id, db)
    await delete_assets(alert_id, db)
    await delete_tags(alert_id, db)
    await delete_iocs(alert_id, db)

    await db.execute(delete(Alert).where(Alert.id == alert.id))

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Error deleting alert")


async def delete_case(case_id: int, db: AsyncSession):
    """
    Delete a case from the database.

    Args:
        case_id (int): The ID of the case to be deleted.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the case is not found or there is an error deleting the case.
    """
    result = await db.execute(
        select(Case).options(selectinload(Case.alerts), selectinload(Case.data_store)).where(Case.id == case_id),
    )
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Delete entries from CaseAlertLink table
    await db.execute(delete(CaseAlertLink).where(CaseAlertLink.case_id == case_id))

    # Delete entries from CaseDataStore table
    await db.execute(delete(CaseDataStore).where(CaseDataStore.case_id == case_id))

    # Delete the case
    await db.execute(delete(Case).where(Case.id == case.id))

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Error deleting case")


async def list_all_files(db: AsyncSession) -> List[CaseDataStore]:
    query = select(CaseDataStore)
    result = await db.execute(query)
    return result.scalars().all()


async def list_files_by_case_id(case_id: int, db: AsyncSession) -> List[CaseDataStore]:
    query = select(CaseDataStore).where(CaseDataStore.case_id == case_id)
    result = await db.execute(query)
    return result.scalars().all()


async def file_exists(case_id: int, file_name: str, db: AsyncSession) -> bool:
    query = select(CaseDataStore).where(CaseDataStore.case_id == case_id, CaseDataStore.file_name == file_name)
    result = await db.execute(query)
    return result.scalars().first() is not None


async def report_template_exists(file_name: str, db: AsyncSession) -> bool:
    query = select(CaseReportTemplateDataStore).where(CaseReportTemplateDataStore.report_template_name == file_name)
    result = await db.execute(query)
    return result.scalars().first() is not None


async def sha256_hash_file(file: UploadFile) -> str:
    await file.seek(0)
    file_content = await file.read()
    file_hash = hashlib.sha256(file_content).hexdigest()
    return file_hash


async def get_file_size(file: UploadFile) -> int:
    await file.seek(0)
    content = await file.read()
    return len(content)


async def add_file_to_db(case_id: int, file: UploadFile, file_size: int, file_hash: str, db: AsyncSession) -> None:
    db_file = CaseDataStore(
        case_id=case_id,
        bucket_name="copilot-cases",
        object_key=f"{case_id}/{file.filename}",
        file_name=file.filename,
        content_type=file.content_type,
        file_size=file_size,
        file_hash=file_hash,
    )
    db.add(db_file)
    await db.commit()
    return db_file


async def add_report_template_to_db(file: UploadFile, file_size: int, file_hash: str, db: AsyncSession) -> None:
    db_file = CaseReportTemplateDataStore(
        report_template_name=file.filename,
        bucket_name="copilot-case-report-templates",
        object_key=file.filename,
        content_type=file.content_type,
        file_name=file.filename,
        file_size=file_size,
        file_hash=file_hash,
    )
    db.add(db_file)
    await db.commit()
    return db_file


async def upload_file_to_case(case_id: int, file: UploadFile, db: AsyncSession) -> CaseDataStore:
    file_size = await get_file_size(file)
    file_hash = await sha256_hash_file(file)
    await file.seek(0)
    # Upload the file to Minio
    await upload_case_data_store(
        data=CaseDataStoreCreation(
            case_id=case_id,
            bucket_name="copilot-cases",
            object_key=file.filename,
            file_name=file.filename,
            content_type=file.content_type,
            file_hash=file_hash,
        ),
        file=file,
    )

    # Add the file to the database
    return await add_file_to_db(case_id, file, file_size, file_hash, db)


async def upload_report_template(file: UploadFile, db: AsyncSession) -> CaseReportTemplateDataStore:
    file_size = await get_file_size(file)
    file_hash = await sha256_hash_file(file)
    await file.seek(0)
    # Upload the file to Minio
    await upload_case_report_template_data_store(
        data=CaseReportTemplateDataStoreCreation(
            report_template_name=file.filename,
            bucket_name="copilot-case-report-templates",
            object_key=file.filename,
            file_name=file.filename,
            content_type=file.content_type,
            file_hash=file_hash,
        ),
        file=file,
    )

    # Add the file to the database
    return await add_report_template_to_db(file, file_size, file_hash, db)


async def get_file_by_case_id_and_name(case_id: int, file_name: str, db: AsyncSession) -> CaseDataStore:
    logger.info(f"Getting file {file_name} from case {case_id}")
    query = select(CaseDataStore).where(CaseDataStore.case_id == case_id, CaseDataStore.file_name == file_name)
    result = await db.execute(query)
    return result.scalars().first()


async def get_report_template_by_name(file_name: str, db: AsyncSession) -> CaseReportTemplateDataStore:
    logger.info(f"Getting file {file_name}")
    query = select(CaseReportTemplateDataStore).where(CaseReportTemplateDataStore.report_template_name == file_name)
    result = await db.execute(query)
    return result.scalars().first()


async def remove_file_from_db(file_id: int, db: AsyncSession) -> None:
    await db.execute(delete(CaseDataStore).where(CaseDataStore.id == file_id))
    await db.commit()


async def remove_report_template_from_db(file_id: int, db: AsyncSession) -> None:
    await db.execute(delete(CaseReportTemplateDataStore).where(CaseReportTemplateDataStore.id == file_id))
    await db.commit()


async def delete_file_from_case(case_id: int, file_name: str, db: AsyncSession) -> None:
    file = await get_file_by_case_id_and_name(case_id, file_name, db)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    await delete_file(file.bucket_name, file.object_key)
    await remove_file_from_db(file.id, db)


async def download_file_from_case(case_id: int, file_name: str, db: AsyncSession) -> Tuple[bytes, str]:
    file = await get_file_by_case_id_and_name(case_id, file_name, db)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    file_content = await download_data_store(file.bucket_name, file.object_key)
    return file_content, file.content_type


async def delete_report_template(file_name: str, db: AsyncSession) -> None:
    file = await get_report_template_by_name(file_name, db)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    await delete_file(file.bucket_name, file.object_key)
    await remove_report_template_from_db(file.id, db)


async def download_report_template(file_name: str, db: AsyncSession) -> Tuple[bytes, str]:
    file = await get_report_template_by_name(file_name, db)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    file_content = await download_data_store(file.bucket_name, file.object_key)
    return file_content, file.content_type


async def upload_report_template_to_data_store(db: AsyncSession) -> CaseReportTemplateDataStoreListResponse:
    current_dir = Path(os.getcwd())
    templates_dir = current_dir.parent / "backend" / "app" / "incidents" / "templates"

    templates_list = []

    for file in templates_dir.iterdir():
        logger.info(f"Uploading report template {file.name} to Minio")
        if file.is_file():
            if await report_template_exists(file.name, db):
                raise HTTPException(status_code=400, detail="File name already exists for this template")
            with open(file, "rb") as f:
                content = f.read()
                content_type = mimetypes.guess_type(file)[0]
                upload_file = UploadFile(filename=file.name, file=io.BytesIO(content))
                await upload_case_report_template_data_store(
                    data=CaseReportTemplateDataStoreCreation(
                        report_template_name=file.name,
                        bucket_name="copilot-case-report-templates",
                        object_key=file.name,
                        file_name=file.name,
                        content_type=content_type,
                        file_hash=hashlib.sha256(content).hexdigest(),
                    ),
                    file=upload_file,
                )
            templates_list.append(file.name)
            await add_report_template_to_db(upload_file, len(content), hashlib.sha256(content).hexdigest(), db)

    return templates_list
