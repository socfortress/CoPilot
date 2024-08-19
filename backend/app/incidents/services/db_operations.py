from typing import List

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import delete
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.incidents.models import Alert
from app.incidents.models import AlertContext
from app.incidents.models import AlertTag
from app.incidents.models import AlertTitleFieldName
from app.incidents.models import AlertToTag
from app.incidents.models import Asset
from app.incidents.models import AssetFieldName
from app.incidents.models import Case
from app.incidents.models import CaseAlertLink
from app.incidents.models import Comment
from app.incidents.models import FieldName, Notification, CustomerCodeFieldName
from app.incidents.models import TimestampFieldName
from app.incidents.schema.db_operations import AlertContextCreate
from app.incidents.schema.db_operations import AlertCreate
from app.incidents.schema.db_operations import AlertOut
from app.incidents.schema.db_operations import AlertTagBase
from app.incidents.schema.db_operations import AlertTagCreate
from app.incidents.schema.db_operations import AssetBase
from app.incidents.schema.db_operations import AssetCreate
from app.incidents.schema.db_operations import CaseAlertLinkCreate, PutNotification
from app.incidents.schema.db_operations import CaseCreate, LinkedCaseCreate
from app.incidents.schema.db_operations import CaseOut
from app.incidents.schema.db_operations import CommentBase
from app.incidents.schema.db_operations import CommentCreate
from app.incidents.schema.db_operations import UpdateAlertStatus
from app.incidents.schema.db_operations import UpdateCaseStatus

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

# ! NOT USING FOR NOW. GETTING THE CUSTOMER CODE FROM THE ALERTS SOURCE FIELD INSTEAD ! #
async def add_customer_code_name(source: str, customer_code_name: str, session: AsyncSession):
    result = await session.execute(
        select(CustomerCodeFieldName).where((CustomerCodeFieldName.source == source) & (CustomerCodeFieldName.field_name == customer_code_name)),
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
        select(CustomerCodeFieldName).where((CustomerCodeFieldName.source == source) & (CustomerCodeFieldName.field_name == customer_code_name)),
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


async def update_alert_assigned_to(alert_id: int, assigned_to: str, db: AsyncSession) -> Alert:
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.assigned_to = assigned_to
    await db.commit()
    return alert


async def create_comment(comment: CommentCreate, db: AsyncSession) -> Comment:
    # Check if the alert exists
    result = await db.execute(select(Alert).options(selectinload(Alert.comments)).where(Alert.id == comment.alert_id))
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    db_comment = Comment(**comment.dict())
    db.add(db_comment)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Comment already exists")
    return db_comment


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


# async def list_alerts(db: AsyncSession) -> List[AlertOut]:
#     result = await db.execute(
#         select(Alert).options(
#             selectinload(Alert.comments),
#             selectinload(Alert.assets),
#             selectinload(Alert.cases).selectinload(CaseAlertLink.case),
#             selectinload(Alert.tags).selectinload(AlertToTag.tag),
#         ),
#     )
#     alerts = result.scalars().all()
#     alerts_out = []
#     for alert in alerts:
#         comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
#         assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
#         tags = [AlertTagBase(**alert_to_tag.tag.__dict__) for alert_to_tag in alert.tags]
#         linked_cases = [LinkedCaseCreate(**case_alert_link.case.__dict__) for case_alert_link in alert.cases]
#         alert_out = AlertOut(
#             id=alert.id,
#             alert_creation_time=alert.alert_creation_time,
#             time_closed=alert.time_closed,
#             alert_name=alert.alert_name,
#             alert_description=alert.alert_description,
#             status=alert.status,
#             customer_code=alert.customer_code,
#             source=alert.source,
#             assigned_to=alert.assigned_to,
#             comments=comments,
#             assets=assets,
#             tags=tags,
#             linked_cases=linked_cases,
#         )
#         alerts_out.append(alert_out)
#     return alerts_out

async def list_alerts(db: AsyncSession, page: int = 1, page_size: int = 25) -> List[AlertOut]:
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Alert)
        .options(
            selectinload(Alert.comments),
            selectinload(Alert.assets),
            selectinload(Alert.cases).selectinload(CaseAlertLink.case),
            selectinload(Alert.tags).selectinload(AlertToTag.tag),
        )
        .offset(offset)
        .limit(page_size)
    )
    alerts = result.scalars().all()
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


async def get_case_by_id(case_id: int, db: AsyncSession) -> CaseOut:
    result = await db.execute(
        select(Case)
        .where(Case.id == case_id)
        .options(
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.comments),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.assets),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.tags).selectinload(AlertToTag.tag),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.cases).selectinload(CaseAlertLink.case),
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
    case_out = CaseOut(
        id=case.id,
        case_name=case.case_name,
        case_description=case.case_description,
        assigned_to=case.assigned_to,
        alerts=alerts_out,
        case_creation_time=case.case_creation_time,
    )
    return case_out


async def list_cases(db: AsyncSession) -> List[CaseOut]:
    result = await db.execute(
        select(Case).options(
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.comments),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.assets),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.tags).selectinload(AlertToTag.tag),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.cases).selectinload(CaseAlertLink.case),
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
        case_out = CaseOut(
            id=case.id,
            case_name=case.case_name,
            case_description=case.case_description,
            assigned_to=case.assigned_to,
            alerts=alerts_out,
            case_creation_time=case.case_creation_time,
            case_status=case.case_status,
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
        )
        cases_out.append(case_out)
    return cases_out


async def get_alert_context_by_id(alert_context_id: int, db: AsyncSession) -> AlertContext:
    result = await db.execute(select(AlertContext).where(AlertContext.id == alert_context_id))
    alert_context = result.scalars().first()
    if not alert_context:
        raise HTTPException(status_code=404, detail="Alert context not found")
    return alert_context


async def list_alerts_by_tag(tag: str, db: AsyncSession) -> List[AlertOut]:
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
        ),
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


async def list_alert_by_status(status: str, db: AsyncSession, page: int = 1, page_size: int = 25) -> List[AlertOut]:
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Alert)
        .where(Alert.status == status)
        .options(
            selectinload(Alert.comments),
            selectinload(Alert.assets),
            selectinload(Alert.cases),
            selectinload(Alert.tags).selectinload(AlertToTag.tag),
        )
        .offset(offset)
        .limit(page_size)
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


async def list_alerts_by_asset_name(asset_name: str, db: AsyncSession, page: int = 1, page_size: int = 25) -> List[AlertOut]:
    offset = (page - 1) * page_size
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
        .offset(offset)
        .limit(page_size)
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


async def list_alert_by_assigned_to(assigned_to: str, db: AsyncSession, page: int = 1, page_size: int = 25) -> List[AlertOut]:
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Alert)
        .where(Alert.assigned_to == assigned_to)
        .options(
            selectinload(Alert.comments),
            selectinload(Alert.assets),
            selectinload(Alert.cases),
            selectinload(Alert.tags).selectinload(AlertToTag.tag),
        )
        .offset(offset)
        .limit(page_size)
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

async def list_alerts_by_title(alert_title: str, db: AsyncSession, page: int = 1, page_size: int = 25) -> List[AlertOut]:
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Alert)
        .where(Alert.alert_name.like(f"%{alert_title}%"))
        .options(
            selectinload(Alert.comments),
            selectinload(Alert.assets),
            selectinload(Alert.cases),
            selectinload(Alert.tags).selectinload(AlertToTag.tag),
        )
        .offset(offset)
        .limit(page_size)
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
        .options(selectinload(Alert.comments), selectinload(Alert.assets).selectinload(Asset.alert_context), selectinload(Alert.tags))
        .where(Alert.id == alert_id),
    )
    alert = result.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await delete_comments(alert_id, db)
    await delete_assets(alert_id, db)
    await delete_tags(alert_id, db)

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
        select(Case).options(selectinload(Case.alerts)).where(Case.id == case_id),
    )
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Delete entries from CaseAlertLink table
    await db.execute(delete(CaseAlertLink).where(CaseAlertLink.case_id == case_id))

    # Delete the case
    await db.execute(delete(Case).where(Case.id == case.id))

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Error deleting case")
