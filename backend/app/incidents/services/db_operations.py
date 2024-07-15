from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from typing import List
from app.incidents.models import (
    Alert, Comment, Asset, AlertContext, FieldName, AssetFieldName, Case, CaseAlertLink, AlertTag, AlertToTag, TimestampFieldName
)
from app.incidents.schema.db_operations import CaseAlertLinkCreate, CaseCreate, AlertTagCreate, AlertTagBase, CommentCreate, AssetCreate, CommentBase, AssetBase, AlertOut, AlertCreate, AlertContextCreate, CaseOut

async def get_field_names(source: str, session: AsyncSession):
    result = await session.execute(
        select(FieldName.field_name).where(FieldName.source == source).distinct()
    )
    return result.scalars().all()

async def get_asset_names(source: str, session: AsyncSession):
    result = await session.execute(
        select(AssetFieldName.field_name).where(AssetFieldName.source == source).distinct()
    )
    return result.scalars().all()

async def get_timefield_names(source: str, session: AsyncSession):
    result = await session.execute(
        select(TimestampFieldName.field_name).where(TimestampFieldName.source == source).distinct()
    )
    return result.scalars().all()

async def add_field_name(source: str, field_name: str, session: AsyncSession):
    result = await session.execute(select(FieldName).where((FieldName.source == source) & (FieldName.field_name == field_name)))
    existing_field = result.scalars().first()
    if existing_field is None:
        field = FieldName(source=source, field_name=field_name)
        session.add(field)

async def add_asset_name(source: str, asset_name: str, session: AsyncSession):
    result = await session.execute(select(AssetFieldName).where((AssetFieldName.source == source) & (AssetFieldName.field_name == asset_name)))
    existing_asset = result.scalars().first()
    if existing_asset is None:
        asset = AssetFieldName(source=source, field_name=asset_name)
        session.add(asset)

async def add_timefield_name(source: str, timefield_name: str, session: AsyncSession):
    result = await session.execute(select(TimestampFieldName).where((TimestampFieldName.source == source) & (TimestampFieldName.field_name == timefield_name)))
    existing_timefield = result.scalars().first()
    if existing_timefield is None:
        timefield = TimestampFieldName(source=source, field_name=timefield_name)
        session.add(timefield)

async def delete_field_name(source: str, field_name: str, session: AsyncSession):
    field = await session.execute(
        select(FieldName).where((FieldName.source == source) & (FieldName.field_name == field_name))
    )
    field = field.scalar_one_or_none()
    if field:
        await session.delete(field)

async def delete_asset_name(source: str, asset_name: str, session: AsyncSession):
    asset = await session.execute(
        select(AssetFieldName).where((AssetFieldName.source == source) & (AssetFieldName.field_name == asset_name))
    )
    asset = asset.scalar_one_or_none()
    if asset:
        await session.delete(asset)

async def delete_timefield_name(source: str, timefield_name: str, session: AsyncSession):
    timefield = await session.execute(
        select(TimestampFieldName).where((TimestampFieldName.source == source) & (TimestampFieldName.field_name == timefield_name))
    )
    timefield = timefield.scalar_one_or_none()
    if timefield:
        await session.delete(timefield)

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


async def list_alerts(db: AsyncSession) -> List[AlertOut]:
    result = await db.execute(
        select(Alert).options(
            selectinload(Alert.comments),
            selectinload(Alert.assets),
            selectinload(Alert.cases),
            selectinload(Alert.tags).selectinload(AlertToTag.tag)
        )
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
            tags=tags
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


async def list_cases(db: AsyncSession) -> List[CaseOut]:
    result = await db.execute(
        select(Case).options(
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.comments),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.assets),
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).selectinload(Alert.tags).selectinload(AlertToTag.tag)
        )
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
                tags=tags
            )
            alerts_out.append(alert_out)
        case_out = CaseOut(
            id=case.id,
            case_name=case.case_name,
            case_description=case.case_description,
            assigned_to=case.assigned_to,
            alerts=alerts_out
        )
        cases_out.append(case_out)
    return cases_out
