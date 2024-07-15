from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from app.incidents.models import (
    Alert, Comment, Asset, AlertContext, FieldName, AssetFieldName, Case, CaseAlertLink
)
from app.incidents.schema.db_operations import CommentCreate, AssetCreate, CommentBase, AssetBase, AlertOut, AlertCreate, AlertContextCreate

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


async def list_alerts(db: AsyncSession) -> list[AlertOut]:
    result = await db.execute(select(Alert).options(selectinload(Alert.comments), selectinload(Alert.assets), selectinload(Alert.cases)))
    alerts = result.scalars().all()
    alerts_out = []
    for alert in alerts:
        comments = [CommentBase(**comment.__dict__) for comment in alert.comments]
        assets = [AssetBase(**asset.__dict__) for asset in alert.assets]
        alert_out = AlertOut(id=alert.id, alert_creation_time=alert.alert_creation_time, time_closed=alert.time_closed, alert_name=alert.alert_name, alert_description=alert.alert_description, status=alert.status, customer_code=alert.customer_code, source=alert.source, comments=comments, assets=assets)
        alerts_out.append(alert_out)
    return alerts_out
