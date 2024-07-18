from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.connectors.wazuh_indexer.utils.universal import get_index_mappings_key_names
from app.db.db_session import get_db
from app.incidents.models import Alert
from app.incidents.models import AlertContext
from app.incidents.models import AlertTag
from app.incidents.models import Asset
from app.incidents.models import AssetFieldName
from app.incidents.models import Case
from app.incidents.models import CaseAlertLink
from app.incidents.models import Comment
from app.incidents.models import FieldName
from app.incidents.schema.db_operations import AlertContextCreate, AlertStatus
from app.incidents.schema.db_operations import AlertCreate
from app.incidents.schema.db_operations import AlertOut
from app.incidents.schema.db_operations import AlertTagCreate
from app.incidents.schema.db_operations import AssetBase
from app.incidents.schema.db_operations import AssetCreate
from app.incidents.schema.db_operations import CaseAlertLinkCreate
from app.incidents.schema.db_operations import CaseCreate
from app.incidents.schema.db_operations import CaseOut
from app.incidents.schema.db_operations import CommentBase
from app.incidents.schema.db_operations import CommentCreate
from app.incidents.schema.db_operations import FieldAndAssetNames
from app.incidents.schema.db_operations import FieldAndAssetNamesResponse, AlertOutResponse
from app.incidents.schema.db_operations import MappingsResponse
from app.incidents.services.db_operations import add_alert_title_name
from app.incidents.services.db_operations import add_asset_name
from app.incidents.services.db_operations import add_field_name
from app.incidents.services.db_operations import add_timefield_name
from app.incidents.services.db_operations import create_alert, list_alerts_by_asset_name
from app.incidents.services.db_operations import create_alert_context
from app.incidents.services.db_operations import create_alert_tag, list_alerts_by_tag
from app.incidents.services.db_operations import create_asset
from app.incidents.services.db_operations import create_case
from app.incidents.services.db_operations import create_case_alert_link, list_alert_by_status
from app.incidents.services.db_operations import create_comment
from app.incidents.services.db_operations import delete_alert_title_name
from app.incidents.services.db_operations import delete_asset_name
from app.incidents.services.db_operations import delete_field_name
from app.incidents.services.db_operations import delete_timefield_name
from app.incidents.services.db_operations import get_alert_context_by_id
from app.incidents.services.db_operations import get_alert_title_names, delete_alert
from app.incidents.services.db_operations import get_asset_names
from app.incidents.services.db_operations import get_field_names
from app.incidents.services.db_operations import get_timefield_names
from app.incidents.services.db_operations import list_alerts
from app.incidents.services.db_operations import list_cases
from app.incidents.services.db_operations import validate_source_exists

incidents_db_operations_router = APIRouter()


@incidents_db_operations_router.get("/mappings/fields-assets-title-and-timefield", response_model=MappingsResponse)
async def get_wazuh_fields_and_assets(index_id: str, session: AsyncSession = Depends(get_db)):
    index_mapping = await get_index_mappings_key_names(index_id)
    return MappingsResponse(available_mappings=index_mapping, success=True, message="Field names and asset names retrieved successfully")


@incidents_db_operations_router.get("/fields-assets-title-and-timefield", response_model=FieldAndAssetNamesResponse)
async def get_source_fields_and_assets(source: str, session: AsyncSession = Depends(get_db)):
    await validate_source_exists(source, session)
    return FieldAndAssetNamesResponse(
        field_names=await get_field_names(source, session),
        asset_name=await get_asset_names(source, session),
        timefield_name=await get_timefield_names(source, session),
        alert_title_name=await get_alert_title_names(source, session),
        source=source,
        success=True,
        message="Field names and asset names retrieved successfully",
    )


@incidents_db_operations_router.post("/fields-assets-title-and-timefield")
async def create_wazuh_fields_and_assets(names: FieldAndAssetNames, session: AsyncSession = Depends(get_db)):
    for field_name in names.field_names:
        await add_field_name(names.source, field_name, session)

    await add_asset_name(names.source, names.asset_name, session)

    await add_timefield_name(names.source, names.timefield_name, session)

    await add_alert_title_name(names.source, names.alert_title_name, session)

    await session.commit()

    return {"message": "Field names and asset names created successfully", "success": True}


@incidents_db_operations_router.delete("/delete-fields-assets-title-and-timefield")
async def delete_wazuh_fields_and_assets(names: FieldAndAssetNames, session: AsyncSession = Depends(get_db)):
    for field_name in names.field_names:
        await delete_field_name(names.source, field_name, session)

    await delete_asset_name(names.source, names.asset_name, session)

    await delete_timefield_name(names.source, names.timefield_name, session)

    await delete_alert_title_name(names.source, names.alert_title_name, session)

    await session.commit()

    return {"message": "Field names and asset names deleted successfully", "success": True}


@incidents_db_operations_router.post("/alert", response_model=Alert)
async def create_alert_endpoint(alert: AlertCreate, db: AsyncSession = Depends(get_db)):
    return await create_alert(alert, db)


@incidents_db_operations_router.post("/alert/comment", response_model=Comment)
async def create_comment_endpoint(comment: CommentCreate, db: AsyncSession = Depends(get_db)):
    return await create_comment(comment, db)


@incidents_db_operations_router.post("/alert/context", response_model=AlertContext)
async def create_alert_context_endpoint(alert_context: AlertContextCreate, db: AsyncSession = Depends(get_db)):
    return await create_alert_context(alert_context, db)


@incidents_db_operations_router.get("/alert/context/{alert_context_id}", response_model=AlertContext)
async def get_alert_context_by_id_endpoint(alert_context_id: int, db: AsyncSession = Depends(get_db)):
    return await get_alert_context_by_id(alert_context_id, db)


@incidents_db_operations_router.post("/alert/asset", response_model=Asset)
async def create_asset_endpoint(asset: AssetCreate, db: AsyncSession = Depends(get_db)):
    return await create_asset(asset, db)


@incidents_db_operations_router.post("/alert/tag", response_model=AlertTag)
async def create_alert_tag_endpoint(alert_tag: AlertTagCreate, db: AsyncSession = Depends(get_db)):
    return await create_alert_tag(alert_tag, db)

@incidents_db_operations_router.get("/alert/tag/{tag}", response_model=List[AlertOut])
async def list_alerts_by_tag_endpoint(tag: str, db: AsyncSession = Depends(get_db)):
    return await list_alerts_by_tag(tag, db)


@incidents_db_operations_router.post("/case/create", response_model=Case)
async def create_case_endpoint(case: CaseCreate, db: AsyncSession = Depends(get_db)):
    return await create_case(case, db)


@incidents_db_operations_router.post("/case/alert-link", response_model=CaseAlertLink)
async def create_case_alert_link_endpoint(case_alert_link: CaseAlertLinkCreate, db: AsyncSession = Depends(get_db)):
    return await create_case_alert_link(case_alert_link, db)


@incidents_db_operations_router.get("/alerts", response_model=AlertOutResponse)
async def list_alerts_endpoint(db: AsyncSession = Depends(get_db)):
    return AlertOutResponse(alerts=await list_alerts(db), success=True, message="Alerts retrieved successfully")

@incidents_db_operations_router.delete("/alert/{alert_id}")
async def delete_alert_endpoint(alert_id: int, db: AsyncSession = Depends(get_db)):
    return await delete_alert(alert_id, db)

@incidents_db_operations_router.get("/alerts/status/{status}", response_model=List[AlertOut])
async def list_alerts_by_status_endpoint(status: AlertStatus, db: AsyncSession = Depends(get_db)):
    if status not in AlertStatus:
        raise HTTPException(status_code=400, detail="Invalid status")
    return await list_alert_by_status(status.value, db)

@incidents_db_operations_router.get("/alerts/asset/{asset_name}", response_model=List[AlertOut])
async def list_alerts_by_asset_name_endpoint(asset_name: str, db: AsyncSession = Depends(get_db)):
    return await list_alerts_by_asset_name(asset_name, db)


@incidents_db_operations_router.get("/cases", response_model=List[CaseOut])
async def list_cases_endpoint(db: AsyncSession = Depends(get_db)):
    return await list_cases(db)
