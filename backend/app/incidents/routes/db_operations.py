from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Security
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.services.universal import select_all_users
from app.auth.utils import AuthHandler
from app.connectors.wazuh_indexer.utils.universal import get_index_mappings_key_names, get_index_source, get_available_indices_via_source
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
from app.incidents.schema.db_operations import AlertContextCreate
from app.incidents.schema.db_operations import AlertContextResponse
from app.incidents.schema.db_operations import AlertCreate
from app.incidents.schema.db_operations import AlertOut
from app.incidents.schema.db_operations import AlertOutResponse
from app.incidents.schema.db_operations import AlertResponse, AvailableUsersResponse
from app.incidents.schema.db_operations import AlertStatus
from app.incidents.schema.db_operations import AlertTagCreate
from app.incidents.schema.db_operations import AlertTagResponse
from app.incidents.schema.db_operations import AssetBase
from app.incidents.schema.db_operations import AssetCreate
from app.incidents.schema.db_operations import AssetResponse
from app.incidents.schema.db_operations import AssignedToAlert
from app.incidents.schema.db_operations import CaseAlertLinkCreate
from app.incidents.schema.db_operations import CaseAlertLinkResponse
from app.incidents.schema.db_operations import CaseCreate
from app.incidents.schema.db_operations import CaseOut
from app.incidents.schema.db_operations import CaseOutResponse
from app.incidents.schema.db_operations import CaseResponse
from app.incidents.schema.db_operations import CommentBase, AvailableIndicesResponse
from app.incidents.schema.db_operations import CommentCreate
from app.incidents.schema.db_operations import CommentResponse
from app.incidents.schema.db_operations import ConfiguredSourcesResponse, AvailableSourcesResponse
from app.incidents.schema.db_operations import FieldAndAssetNames
from app.incidents.schema.db_operations import FieldAndAssetNamesResponse
from app.incidents.schema.db_operations import MappingsResponse
from app.incidents.schema.db_operations import UpdateAlertStatus
from app.incidents.services.db_operations import add_alert_title_name
from app.incidents.services.db_operations import add_asset_name
from app.incidents.services.db_operations import add_field_name
from app.incidents.services.db_operations import add_timefield_name
from app.incidents.services.db_operations import create_alert
from app.incidents.services.db_operations import create_alert_context
from app.incidents.services.db_operations import create_alert_tag
from app.incidents.services.db_operations import create_asset
from app.incidents.services.db_operations import create_case
from app.incidents.services.db_operations import create_case_alert_link
from app.incidents.services.db_operations import create_comment
from app.incidents.services.db_operations import delete_alert
from app.incidents.services.db_operations import delete_alert_tag
from app.incidents.services.db_operations import delete_alert_title_name
from app.incidents.services.db_operations import delete_asset_name
from app.incidents.services.db_operations import delete_field_name
from app.incidents.services.db_operations import delete_timefield_name
from app.incidents.services.db_operations import get_alert_context_by_id
from app.incidents.services.db_operations import get_alert_title_names
from app.incidents.services.db_operations import get_asset_names
from app.incidents.services.db_operations import get_field_names
from app.incidents.services.db_operations import get_timefield_names
from app.incidents.services.db_operations import list_alert_by_assigned_to
from app.incidents.services.db_operations import list_alert_by_status
from app.incidents.services.db_operations import list_alerts
from app.incidents.services.db_operations import list_alerts_by_asset_name
from app.incidents.services.db_operations import list_alerts_by_tag
from app.incidents.services.db_operations import list_cases
from app.incidents.services.db_operations import update_alert_assigned_to
from app.incidents.services.db_operations import update_alert_status
from app.incidents.services.db_operations import validate_source_exists

incidents_db_operations_router = APIRouter()

@incidents_db_operations_router.get("/available-source/{index_name}", response_model=AvailableSourcesResponse)
async def get_available_source_values(index_name: str, session: AsyncSession = Depends(get_db)):
    return AvailableSourcesResponse(source=await get_index_source(index_name), success=True, message="Source retrieved successfully")

@incidents_db_operations_router.get("/available-indices/{source}", response_model=AvailableIndicesResponse)
async def get_available_indices(source: str, session: AsyncSession = Depends(get_db)):
    return AvailableIndicesResponse(indices=await get_available_indices_via_source(source), success=True, message="Indices retrieved successfully")

@incidents_db_operations_router.get("/configured/sources", response_model=ConfiguredSourcesResponse)
async def get_configured_sources(session: AsyncSession = Depends(get_db)):
    query = select(FieldName.source).distinct()
    result = await session.execute(query)
    return ConfiguredSourcesResponse(sources=[row[0] for row in result], success=True, message="Configured sources retrieved successfully")


@incidents_db_operations_router.delete("/configured/sources/{source}")
async def delete_configured_source(source: str, session: AsyncSession = Depends(get_db)):
    # Fully deletes the configured sources `field_names`, `asset_name`, timefield_name`, alert_title_name`
    field_names = await get_field_names(source, session)
    asset_name = await get_asset_names(source, session)
    timefield_name = await get_timefield_names(source, session)
    alert_title_name = await get_alert_title_names(source, session)

    for field_name in field_names:
        await delete_field_name(source, field_name, session)

    await delete_asset_name(source, asset_name, session)

    await delete_timefield_name(source, timefield_name, session)

    await delete_alert_title_name(source, alert_title_name, session)

    await session.commit()

    return {"message": f"Configured source {source} deleted successfully", "success": True}


@incidents_db_operations_router.get("/mappings/fields-assets-title-and-timefield", response_model=MappingsResponse)
async def get_wazuh_fields_and_assets(index_name: str, session: AsyncSession = Depends(get_db)):
    index_mapping = await get_index_mappings_key_names(index_name)
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


@incidents_db_operations_router.delete("/field_name/{field_name}/{source}", deprecated=True)
async def delete_field_name_endpoint(field_name: str, source: str, db: AsyncSession = Depends(get_db)):
    return await delete_field_name(source, field_name, db)


@incidents_db_operations_router.delete("/asset_name/{asset_name}/{source}", deprecated=True)
async def delete_asset_name_endpoint(asset_name: str, source: str, db: AsyncSession = Depends(get_db)):
    return await delete_asset_name(source, asset_name, db)


@incidents_db_operations_router.delete("/timefield_name/{timefield_name}/{source}", deprecated=True)
async def delete_timefield_name_endpoint(timefield_name: str, source: str, db: AsyncSession = Depends(get_db)):
    return await delete_timefield_name(source, timefield_name, db)


@incidents_db_operations_router.delete("/alert_title_name/{alert_title_name}/{source}", deprecated=True)
async def delete_alert_title_name_endpoint(alert_title_name: str, source: str, db: AsyncSession = Depends(get_db)):
    return await delete_alert_title_name(source, alert_title_name, db)


@incidents_db_operations_router.post("/alert", response_model=Alert)
async def create_alert_endpoint(alert: AlertCreate, db: AsyncSession = Depends(get_db)):
    return await create_alert(alert, db)


@incidents_db_operations_router.put("/alert/status", response_model=AlertResponse)
async def update_alert_status_endpoint(alert_status: UpdateAlertStatus, db: AsyncSession = Depends(get_db)):
    return AlertResponse(alert=await update_alert_status(alert_status, db), success=True, message="Alert status updated successfully")


@incidents_db_operations_router.post("/alert/comment", response_model=CommentResponse)
async def create_comment_endpoint(comment: CommentCreate, db: AsyncSession = Depends(get_db)):
    return CommentResponse(comment=await create_comment(comment, db), success=True, message="Comment created successfully")

@incidents_db_operations_router.get("/alert/available-users", response_model=AvailableUsersResponse)
async def get_available_users(db: AsyncSession = Depends(get_db)):
    all_users = await select_all_users()
    return AvailableUsersResponse(available_users=[user.username for user in all_users], success=True, message="Available users retrieved successfully")

@incidents_db_operations_router.put("/alert/assigned-to", response_model=AlertResponse)
async def update_assigned_to_endpoint(assigned_to: AssignedToAlert, db: AsyncSession = Depends(get_db)):
    all_users = await select_all_users()
    user_names = [user.username for user in all_users]
    if assigned_to.assigned_to not in user_names:
        raise HTTPException(status_code=400, detail="User does not exist")
    return AlertResponse(
        alert=await update_alert_assigned_to(assigned_to.alert_id, assigned_to.assigned_to, db),
        success=True,
        message="Alert assigned to user successfully",
    )


@incidents_db_operations_router.post("/alert/context", response_model=AlertContextResponse)
async def create_alert_context_endpoint(alert_context: AlertContextCreate, db: AsyncSession = Depends(get_db)):
    return AlertContextResponse(
        alert_context=await create_alert_context(alert_context, db), success=True, message="Alert context created successfully",
    )


@incidents_db_operations_router.get("/alert/context/{alert_context_id}", response_model=AlertContextResponse)
async def get_alert_context_by_id_endpoint(alert_context_id: int, db: AsyncSession = Depends(get_db)):
    return AlertContextResponse(
        alert_context=await get_alert_context_by_id(alert_context_id, db), success=True, message="Alert context retrieved successfully",
    )


@incidents_db_operations_router.post("/alert/asset", response_model=AssetResponse)
async def create_asset_endpoint(asset: AssetCreate, db: AsyncSession = Depends(get_db)):
    return AssetResponse(asset=await create_asset(asset, db), success=True, message="Asset created successfully")


@incidents_db_operations_router.post("/alert/tag", response_model=AlertTagResponse)
async def create_alert_tag_endpoint(alert_tag: AlertTagCreate, db: AsyncSession = Depends(get_db)):
    return AlertTagResponse(alert_tag=await create_alert_tag(alert_tag, db), success=True, message="Alert tag created successfully")


@incidents_db_operations_router.get("/alert/tag/{tag}", response_model=AlertOutResponse)
async def list_alerts_by_tag_endpoint(tag: str, db: AsyncSession = Depends(get_db)):
    return AlertOutResponse(alerts=await list_alerts_by_tag(tag, db), success=True, message="Alerts retrieved successfully")


@incidents_db_operations_router.delete("/alert/tag", response_model=AlertTagResponse)
async def delete_alert_tag_endpoint(alert_tag: AlertTagCreate, db: AsyncSession = Depends(get_db)):
    return AlertTagResponse(
        alert_tag=await delete_alert_tag(alert_tag.alert_id, alert_tag.tag, db), success=True, message="Alert tag deleted successfully",
    )


@incidents_db_operations_router.post("/case/create", response_model=CaseResponse)
async def create_case_endpoint(case: CaseCreate, db: AsyncSession = Depends(get_db)):
    return CaseResponse(case=await create_case(case, db), success=True, message="Case created successfully")


@incidents_db_operations_router.post("/case/alert-link", response_model=CaseAlertLinkResponse)
async def create_case_alert_link_endpoint(case_alert_link: CaseAlertLinkCreate, db: AsyncSession = Depends(get_db)):
    return CaseAlertLinkResponse(
        case_alert_link=await create_case_alert_link(case_alert_link, db), success=True, message="Case alert link created successfully",
    )


@incidents_db_operations_router.get("/alerts", response_model=AlertOutResponse)
async def list_alerts_endpoint(db: AsyncSession = Depends(get_db)):
    return AlertOutResponse(alerts=await list_alerts(db), success=True, message="Alerts retrieved successfully")


@incidents_db_operations_router.delete("/alert/{alert_id}")
async def delete_alert_endpoint(alert_id: int, db: AsyncSession = Depends(get_db)):
    await delete_alert(alert_id, db)
    return {"message": "Alert deleted successfully", "success": True}


@incidents_db_operations_router.get("/alerts/status/{status}", response_model=AlertOutResponse)
async def list_alerts_by_status_endpoint(status: AlertStatus, db: AsyncSession = Depends(get_db)):
    if status not in AlertStatus:
        raise HTTPException(status_code=400, detail="Invalid status")
    return AlertOutResponse(alerts=await list_alert_by_status(status.value, db), success=True, message="Alerts retrieved successfully")


@incidents_db_operations_router.get("/alerts/assigned-to/{assigned_to}", response_model=AlertOutResponse)
async def list_alerts_by_assigned_to_endpoint(assigned_to: str, db: AsyncSession = Depends(get_db)):
    return AlertOutResponse(alerts=await list_alert_by_assigned_to(assigned_to, db), success=True, message="Alerts retrieved successfully")


@incidents_db_operations_router.get("/alerts/asset/{asset_name}", response_model=AlertOutResponse)
async def list_alerts_by_asset_name_endpoint(asset_name: str, db: AsyncSession = Depends(get_db)):
    return AlertOutResponse(alerts=await list_alerts_by_asset_name(asset_name, db), success=True, message="Alerts retrieved successfully")


@incidents_db_operations_router.get("/cases", response_model=CaseOutResponse)
async def list_cases_endpoint(db: AsyncSession = Depends(get_db)):
    return CaseOutResponse(cases=await list_cases(db), success=True, message="Cases retrieved successfully")
