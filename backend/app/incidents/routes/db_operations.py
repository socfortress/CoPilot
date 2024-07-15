from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from typing import List
from fastapi import Security
from loguru import logger
from app.auth.utils import AuthHandler
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.db_session import get_db
from app.incidents.models import (
    Alert, Comment, Asset, AlertContext, FieldName, AssetFieldName, Case, CaseAlertLink, AlertTag
)
from app.incidents.schema.db_operations import CommentCreate, AssetCreate, CommentBase, AssetBase, AlertOut, FieldAndAssetNames, AlertCreate, AlertContextCreate, AlertTagCreate
from app.incidents.services.db_operations import create_alert, create_comment, create_asset, list_alerts, create_alert_context, create_alert_tag

incidents_db_operations_router = APIRouter()

@incidents_db_operations_router.post("/create-wazuh-fields-and-assets")
async def create_wazuh_fields_and_assets(names: FieldAndAssetNames, session: AsyncSession = Depends(get_db)):
    for field_name in names.field_names:
        field = FieldName(source="wazuh", field_name=field_name)
        session.add(field)

    for asset_name in names.asset_names:
        asset = AssetFieldName(source="wazuh", field_name=asset_name)
        session.add(asset)

    await session.commit()

    return {"message": "Field names and asset names created successfully"}

@incidents_db_operations_router.post("/alert/", response_model=Alert)
async def create_alert_endpoint(alert: AlertCreate, db: AsyncSession = Depends(get_db)):
    return await create_alert(alert, db)

@incidents_db_operations_router.post("/alert/comment/", response_model=Comment)
async def create_comment_endpoint(comment: CommentCreate, db: AsyncSession = Depends(get_db)):
    return await create_comment(comment, db)

@incidents_db_operations_router.post("/alert/context", response_model=AlertContext)
async def create_alert_context_endpoint(alert_context: AlertContextCreate, db: AsyncSession = Depends(get_db)):
    return await create_alert_context(alert_context, db)

@incidents_db_operations_router.post("/alert/asset", response_model=Asset)
async def create_asset_endpoint(asset: AssetCreate, db: AsyncSession = Depends(get_db)):
    return await create_asset(asset, db)

@incidents_db_operations_router.post("/alert/tag", response_model=AlertTag)
async def create_alert_tag_endpoint(alert_tag: AlertTagCreate, db: AsyncSession = Depends(get_db)):
    return await create_alert_tag(alert_tag, db)

@incidents_db_operations_router.get("/alerts/", response_model=List[AlertOut])
async def list_alerts_endpoint(db: AsyncSession = Depends(get_db)):
    return await list_alerts(db)
