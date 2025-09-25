import io
import mimetypes
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import HTTPException
from fastapi import Query
from fastapi import UploadFile
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.users import User
from app.auth.services.universal import select_all_users
from app.auth.utils import AuthHandler
from app.connectors.wazuh_indexer.utils.universal import (
    get_available_indices_via_source,
)
from app.connectors.wazuh_indexer.utils.universal import get_index_mappings_key_names
from app.connectors.wazuh_indexer.utils.universal import get_index_source
from app.customer_provisioning.routes.provision import check_customer_exists
from app.data_store.data_store_operations import (
    list_case_report_template_data_store_files,
)
from app.db.db_session import get_db
from app.db.universal_models import Customers
from app.incidents.models import Alert
from app.incidents.models import Comment
from app.incidents.models import FieldName
from app.incidents.schema.db_operations import AlertContextCreate
from app.incidents.schema.db_operations import AlertContextResponse
from app.incidents.schema.db_operations import AlertCreate
from app.incidents.schema.db_operations import AlertIoCCreate
from app.incidents.schema.db_operations import AlertIoCDelete
from app.incidents.schema.db_operations import AlertIoCResponse
from app.incidents.schema.db_operations import AlertOutResponse
from app.incidents.schema.db_operations import AlertResponse
from app.incidents.schema.db_operations import AlertStatus
from app.incidents.schema.db_operations import AlertTagCreate
from app.incidents.schema.db_operations import AlertTagDelete
from app.incidents.schema.db_operations import AlertTagResponse
from app.incidents.schema.db_operations import AssetCreate
from app.incidents.schema.db_operations import AssetResponse
from app.incidents.schema.db_operations import AssignedToAlert
from app.incidents.schema.db_operations import AssignedToCase
from app.incidents.schema.db_operations import AvailableIndicesResponse
from app.incidents.schema.db_operations import AvailableSourcesResponse
from app.incidents.schema.db_operations import AvailableUsersResponse
from app.incidents.schema.db_operations import CaseAlertLinkCreate
from app.incidents.schema.db_operations import CaseAlertLinkResponse
from app.incidents.schema.db_operations import CaseAlertLinksCreate
from app.incidents.schema.db_operations import CaseAlertLinksResponse
from app.incidents.schema.db_operations import CaseAlertUnLink
from app.incidents.schema.db_operations import CaseAlertUnLinkResponse
from app.incidents.schema.db_operations import CaseCreate
from app.incidents.schema.db_operations import CaseCreateFromAlert
from app.incidents.schema.db_operations import CaseDataStoreResponse
from app.incidents.schema.db_operations import CaseNotificationCreate
from app.incidents.schema.db_operations import CaseNotificationResponse
from app.incidents.schema.db_operations import CaseOutResponse
from app.incidents.schema.db_operations import CaseReportTemplateDataStoreListResponse
from app.incidents.schema.db_operations import CaseReportTemplateDataStoreResponse
from app.incidents.schema.db_operations import CaseResponse
from app.incidents.schema.db_operations import CommentCreate
from app.incidents.schema.db_operations import CommentEdit
from app.incidents.schema.db_operations import CommentResponse
from app.incidents.schema.db_operations import ConfiguredSourcesResponse
from app.incidents.schema.db_operations import DefaultReportTemplateFileNames
from app.incidents.schema.db_operations import DeleteAlertsRequest
from app.incidents.schema.db_operations import DeleteAlertsResponse
from app.incidents.schema.db_operations import FieldAndAssetNames
from app.incidents.schema.db_operations import FieldAndAssetNamesResponse
from app.incidents.schema.db_operations import ListCaseDataStoreResponse
from app.incidents.schema.db_operations import MappingsResponse
from app.incidents.schema.db_operations import NotificationResponse
from app.incidents.schema.db_operations import PutNotification
from app.incidents.schema.db_operations import SocfortressRecommendsWazuhAlertTitleName
from app.incidents.schema.db_operations import SocfortressRecommendsWazuhAssetName
from app.incidents.schema.db_operations import SocfortressRecommendsWazuhFieldNames
from app.incidents.schema.db_operations import SocfortressRecommendsWazuhIoCFieldNames
from app.incidents.schema.db_operations import SocfortressRecommendsWazuhResponse
from app.incidents.schema.db_operations import SocfortressRecommendsWazuhTimeFieldName
from app.incidents.schema.db_operations import UpdateAlertStatus
from app.incidents.schema.db_operations import UpdateCaseStatus
from app.incidents.schema.incident_alert import CreatedAlertPayload
from app.incidents.schema.incident_alert import CreatedCaseNotificationPayload

# from app.incidents.services.db_operations import list_alerts
# from app.incidents.services.db_operations import alerts_open_multiple_filters
# from app.incidents.services.db_operations import alerts_in_progress_multiple_filters
# from app.incidents.services.db_operations import alerts_closed_multiple_filters
from app.incidents.services.db_operations import add_alert_title_name
from app.incidents.services.db_operations import add_asset_name
from app.incidents.services.db_operations import add_field_name
from app.incidents.services.db_operations import add_ioc_name
from app.incidents.services.db_operations import add_timefield_name
from app.incidents.services.db_operations import alert_total
from app.incidents.services.db_operations import alert_total_by_alert_title
from app.incidents.services.db_operations import alert_total_by_assest_name
from app.incidents.services.db_operations import alert_total_by_customer_codes
from app.incidents.services.db_operations import alerts_closed
from app.incidents.services.db_operations import alerts_closed_by_alert_title
from app.incidents.services.db_operations import alerts_closed_by_asset_name
from app.incidents.services.db_operations import alerts_closed_by_assigned_to
from app.incidents.services.db_operations import alerts_closed_by_customer_code
from app.incidents.services.db_operations import alerts_closed_by_customer_codes
from app.incidents.services.db_operations import alerts_closed_by_ioc
from app.incidents.services.db_operations import alerts_closed_by_source
from app.incidents.services.db_operations import alerts_closed_by_tag
from app.incidents.services.db_operations import alerts_in_progress
from app.incidents.services.db_operations import alerts_in_progress_by_alert_title
from app.incidents.services.db_operations import alerts_in_progress_by_assest_name
from app.incidents.services.db_operations import alerts_in_progress_by_assigned_to
from app.incidents.services.db_operations import alerts_in_progress_by_customer_code
from app.incidents.services.db_operations import alerts_in_progress_by_customer_codes
from app.incidents.services.db_operations import alerts_in_progress_by_ioc
from app.incidents.services.db_operations import alerts_in_progress_by_source
from app.incidents.services.db_operations import alerts_in_progress_by_tag
from app.incidents.services.db_operations import alerts_open
from app.incidents.services.db_operations import alerts_open_by_alert_title
from app.incidents.services.db_operations import alerts_open_by_assest_name
from app.incidents.services.db_operations import alerts_open_by_assigned_to
from app.incidents.services.db_operations import alerts_open_by_customer_code
from app.incidents.services.db_operations import alerts_open_by_customer_codes
from app.incidents.services.db_operations import alerts_open_by_ioc
from app.incidents.services.db_operations import alerts_open_by_source
from app.incidents.services.db_operations import alerts_open_by_tag
from app.incidents.services.db_operations import alerts_total_by_assigned_to
from app.incidents.services.db_operations import alerts_total_by_customer_code
from app.incidents.services.db_operations import alerts_total_by_ioc
from app.incidents.services.db_operations import alerts_total_by_source
from app.incidents.services.db_operations import alerts_total_by_tag
from app.incidents.services.db_operations import alerts_total_multiple_filters
from app.incidents.services.db_operations import case_alert_unlink
from app.incidents.services.db_operations import create_alert
from app.incidents.services.db_operations import create_alert_context
from app.incidents.services.db_operations import create_alert_ioc
from app.incidents.services.db_operations import create_alert_tag
from app.incidents.services.db_operations import create_asset
from app.incidents.services.db_operations import create_case
from app.incidents.services.db_operations import create_case_alert_link
from app.incidents.services.db_operations import create_case_alert_links_bulk
from app.incidents.services.db_operations import create_case_from_alert
from app.incidents.services.db_operations import create_comment
from app.incidents.services.db_operations import delete_alert
from app.incidents.services.db_operations import delete_alert_ioc
from app.incidents.services.db_operations import delete_alert_tag
from app.incidents.services.db_operations import delete_alert_title_name
from app.incidents.services.db_operations import delete_asset_name
from app.incidents.services.db_operations import delete_case
from app.incidents.services.db_operations import delete_comment
from app.incidents.services.db_operations import delete_field_name
from app.incidents.services.db_operations import delete_file_from_case
from app.incidents.services.db_operations import delete_ioc_name
from app.incidents.services.db_operations import delete_report_template
from app.incidents.services.db_operations import delete_timefield_name
from app.incidents.services.db_operations import download_file_from_case
from app.incidents.services.db_operations import download_report_template
from app.incidents.services.db_operations import edit_comment
from app.incidents.services.db_operations import file_exists
from app.incidents.services.db_operations import get_alert_by_id
from app.incidents.services.db_operations import get_alert_context_by_id
from app.incidents.services.db_operations import get_alert_title_names
from app.incidents.services.db_operations import get_asset_names
from app.incidents.services.db_operations import get_case_by_id
from app.incidents.services.db_operations import get_customer_notification
from app.incidents.services.db_operations import get_field_names
from app.incidents.services.db_operations import get_ioc_names
from app.incidents.services.db_operations import get_timefield_names
from app.incidents.services.db_operations import increment_case_notification_count
from app.incidents.services.db_operations import is_alert_linked_to_case
from app.incidents.services.db_operations import list_alert_by_assigned_to
from app.incidents.services.db_operations import list_alert_by_status
from app.incidents.services.db_operations import list_alerts_by_asset_name
from app.incidents.services.db_operations import list_alerts_by_customer_code
from app.incidents.services.db_operations import list_alerts_by_ioc
from app.incidents.services.db_operations import list_alerts_by_source
from app.incidents.services.db_operations import list_alerts_by_tag
from app.incidents.services.db_operations import list_alerts_by_title
from app.incidents.services.db_operations import list_alerts_for_user
from app.incidents.services.db_operations import list_alerts_multiple_filters
from app.incidents.services.db_operations import list_all_files
from app.incidents.services.db_operations import list_cases_by_asset_name
from app.incidents.services.db_operations import list_cases_by_assigned_to
from app.incidents.services.db_operations import list_cases_by_customer_code
from app.incidents.services.db_operations import list_cases_by_status
from app.incidents.services.db_operations import list_cases_for_user
from app.incidents.services.db_operations import list_files_by_case_id
from app.incidents.services.db_operations import put_customer_notification
from app.incidents.services.db_operations import replace_alert_title_name
from app.incidents.services.db_operations import replace_asset_name
from app.incidents.services.db_operations import replace_field_name
from app.incidents.services.db_operations import replace_ioc_name
from app.incidents.services.db_operations import replace_timefield_name
from app.incidents.services.db_operations import report_template_exists
from app.incidents.services.db_operations import update_alert_assigned_to
from app.incidents.services.db_operations import update_alert_status
from app.incidents.services.db_operations import update_case_assigned_to
from app.incidents.services.db_operations import update_case_customer_code
from app.incidents.services.db_operations import update_case_status
from app.incidents.services.db_operations import upload_file_to_case
from app.incidents.services.db_operations import upload_report_template
from app.incidents.services.db_operations import upload_report_template_to_data_store
from app.incidents.services.db_operations import validate_source_exists
from app.incidents.services.incident_case import handle_customer_notifications_case
from app.middleware.customer_access import customer_access_handler

incidents_db_operations_router = APIRouter()


@incidents_db_operations_router.get("/notification/{customer_code}", response_model=NotificationResponse)
async def get_customer_notification_endpoint(
    customer_code: str,
    _customer: Customers = Depends(check_customer_exists),
    db: AsyncSession = Depends(get_db),
):
    return NotificationResponse(
        notifications=await get_customer_notification(customer_code, db),
        success=True,
        message="Notification retrieved successfully",
    )


@incidents_db_operations_router.put("/notification", response_model=NotificationResponse)
async def put_customer_notification_endpoint(
    notification: PutNotification,
    _customer: Customers = Depends(check_customer_exists),
    db: AsyncSession = Depends(get_db),
):
    await put_customer_notification(notification, db)
    return NotificationResponse(
        notifications=await get_customer_notification(notification.customer_code, db),
        success=True,
        message="Notification updated successfully",
    )


@incidents_db_operations_router.get("/available-source/{index_name}", response_model=AvailableSourcesResponse)
async def get_available_source_values(index_name: str, session: AsyncSession = Depends(get_db)):
    return AvailableSourcesResponse(source=await get_index_source(index_name), success=True, message="Source retrieved successfully")


@incidents_db_operations_router.get("/available-indices/{source}", response_model=AvailableIndicesResponse)
async def get_available_indices(source: str, session: AsyncSession = Depends(get_db)):
    return AvailableIndicesResponse(
        indices=await get_available_indices_via_source(source),
        success=True,
        message="Indices retrieved successfully",
    )


@incidents_db_operations_router.get("/socfortress/recommends/wazuh", response_model=SocfortressRecommendsWazuhResponse)
async def get_socfortress_recommends_wazuh(session: AsyncSession = Depends(get_db)):
    return SocfortressRecommendsWazuhResponse(
        field_names=[field.value for field in SocfortressRecommendsWazuhFieldNames],
        asset_name=SocfortressRecommendsWazuhAssetName.agent_name.value,
        timefield_name=SocfortressRecommendsWazuhTimeFieldName.timestamp_utc.value,
        alert_title_name=SocfortressRecommendsWazuhAlertTitleName.rule_description.value,
        ioc_field_names=[ioc.value for ioc in SocfortressRecommendsWazuhIoCFieldNames],
        source="wazuh",
        success=True,
        message="Field names and asset names retrieved successfully",
    )


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
    ioc_names = await get_ioc_names(source, session)

    logger.info(
        f"Field names found: {field_names}, Asset name found: {asset_name}, Timefield name found: {timefield_name}, Alert title name found: {alert_title_name}",
    )

    for field_name in field_names:
        await delete_field_name(source, field_name, session)

    await delete_asset_name(source, asset_name, session)

    await delete_timefield_name(source, timefield_name, session)

    await delete_alert_title_name(source, alert_title_name, session)

    if ioc_names:
        for ioc_name in ioc_names:
            await delete_ioc_name(ioc_name=ioc_name, source=source, session=session)

    logger.info(f"Field names and asset names deleted successfully for source {source}. Committing changes to the database")

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
        ioc_field_names=await get_ioc_names(source, session),
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

    if names.ioc_field_names:
        for ioc_name in names.ioc_field_names:
            await add_ioc_name(names.source, ioc_name, session)

    logger.info(f"Field names, asset names, and timefield name created successfully for source {names.source}")

    await session.commit()

    return {"message": "Field names and asset names created successfully", "success": True}


@incidents_db_operations_router.put("/fields-assets-title-and-timefield")
async def update_fields_and_assets(names: FieldAndAssetNames, session: AsyncSession = Depends(get_db)):
    await replace_field_name(names.source, names.field_names, session)

    await replace_asset_name(names.source, names.asset_name, session)

    await replace_timefield_name(names.source, names.timefield_name, session)

    await replace_alert_title_name(names.source, names.alert_title_name, session)

    await replace_ioc_name(names.source, names.ioc_field_names, session)

    return {"message": "Field names and asset names created successfully", "success": True}


@incidents_db_operations_router.delete("/delete-fields-assets-title-and-timefield")
async def delete_wazuh_fields_and_assets(names: FieldAndAssetNames, session: AsyncSession = Depends(get_db)):
    for field_name in names.field_names:
        await delete_field_name(names.source, field_name, session)

    await delete_asset_name(names.source, names.asset_name, session)

    await delete_timefield_name(names.source, names.timefield_name, session)

    await delete_alert_title_name(names.source, names.alert_title_name, session)

    if names.ioc_field_names:
        logger.info(f"Deleting IoC field names: {names.ioc_field_names}")
        for ioc_name in names.ioc_field_names:
            await delete_ioc_name(ioc_value=ioc_name, source=names.source, session=session)
    logger.info(f"Field names and asset names deleted successfully for source {names.source}. Committing changes to the database")
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
async def create_comment_endpoint(
    comment: CommentCreate,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get the alert to check customer access
    alert = await get_alert_by_id(comment.alert_id, db)

    # Check if user has access to this alert's customer
    if not await customer_access_handler.check_customer_access(current_user, alert.customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to alert {comment.alert_id} - insufficient customer permissions")

    return CommentResponse(comment=await create_comment(comment, db), success=True, message="Comment created successfully")


@incidents_db_operations_router.put("/alert/comment", response_model=CommentResponse)
async def edit_comment_endpoint(
    comment: CommentEdit,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get the alert to check customer access
    alert = await get_alert_by_id(comment.alert_id, db)

    # Check if user has access to this alert's customer
    if not await customer_access_handler.check_customer_access(current_user, alert.customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to alert {comment.alert_id} - insufficient customer permissions")

    return CommentResponse(comment=await edit_comment(comment, db), success=True, message="Comment edited successfully")


@incidents_db_operations_router.delete("/alert/comment/{comment_id}")
async def delete_comment_endpoint(
    comment_id: int,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # First get the comment to find the alert_id
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalars().first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Get the alert to check customer access
    alert = await get_alert_by_id(comment.alert_id, db)

    # Check if user has access to this alert's customer
    if not await customer_access_handler.check_customer_access(current_user, alert.customer_code, db):
        raise HTTPException(
            status_code=403,
            detail=f"Access denied to comment on alert {comment.alert_id} - insufficient customer permissions",
        )

    await delete_comment(comment_id, db)
    return {"message": "Comment deleted successfully", "success": True}


@incidents_db_operations_router.get("/alert/available-users", response_model=AvailableUsersResponse)
async def get_available_users(db: AsyncSession = Depends(get_db)):
    all_users = await select_all_users()
    return AvailableUsersResponse(
        available_users=[user.username for user in all_users],
        success=True,
        message="Available users retrieved successfully",
    )


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
        alert_context=await create_alert_context(alert_context, db),
        success=True,
        message="Alert context created successfully",
    )


@incidents_db_operations_router.get("/alert/context/{alert_context_id}", response_model=AlertContextResponse)
async def get_alert_context_by_id_endpoint(alert_context_id: int, db: AsyncSession = Depends(get_db)):
    return AlertContextResponse(
        alert_context=await get_alert_context_by_id(alert_context_id, db),
        success=True,
        message="Alert context retrieved successfully",
    )


@incidents_db_operations_router.post("/alert/asset", response_model=AssetResponse)
async def create_asset_endpoint(asset: AssetCreate, db: AsyncSession = Depends(get_db)):
    return AssetResponse(asset=await create_asset(asset, db), success=True, message="Asset created successfully")


@incidents_db_operations_router.post("/alert/ioc", response_model=AlertIoCResponse)
async def create_alert_ioc_endpoint(ioc: AlertIoCCreate, db: AsyncSession = Depends(get_db)):
    return AlertIoCResponse(alert_ioc=await create_alert_ioc(ioc, db), success=True, message="Alert IoC created successfully")


@incidents_db_operations_router.get("/alert/ioc/{ioc_value}", response_model=AlertOutResponse)
async def list_alerts_by_ioc_value_endpoint(
    ioc_value: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List alerts by IoC value with customer access filtering"""
    logger.info(f"Listing alerts by IoC {ioc_value} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get customer access filtering
    accessible_customers = await customer_access_handler.get_user_accessible_customers(current_user, db)

    if "*" in accessible_customers:
        # Admin/analyst - no filtering needed
        alerts = await list_alerts_by_ioc(ioc_value, db, page, page_size)
        total = await alerts_total_by_ioc(db, ioc_value)
        open_alerts = await alerts_open_by_ioc(db, ioc_value)
        in_progress = await alerts_in_progress_by_ioc(db, ioc_value)
        closed = await alerts_closed_by_ioc(db, ioc_value)
    else:
        # Customer user - filter by accessible customers
        alerts = await list_alerts_multiple_filters(
            ioc_value=ioc_value,
            customer_code=accessible_customers[0] if len(accessible_customers) == 1 else None,
            db=db,
            page=page,
            page_size=page_size,
            order="desc",
        )
        total = await alert_total_by_customer_codes(db, accessible_customers)
        open_alerts = await alerts_open_by_customer_codes(db, accessible_customers)
        in_progress = await alerts_in_progress_by_customer_codes(db, accessible_customers)
        closed = await alerts_closed_by_customer_codes(db, accessible_customers)

    return AlertOutResponse(
        alerts=alerts,
        total=total,
        open=open_alerts,
        in_progress=in_progress,
        closed=closed,
        success=True,
        message="Alerts retrieved successfully",
    )


@incidents_db_operations_router.delete("/alert/ioc", response_model=AlertIoCResponse)
async def delete_alert_ioc_endpoint(ioc: AlertIoCDelete, db: AsyncSession = Depends(get_db)):
    return AlertIoCResponse(
        alert_ioc=await delete_alert_ioc(ioc=ioc, db=db),
        success=True,
        message="Alert IoC deleted successfully",
    )


@incidents_db_operations_router.post("/alert/tag", response_model=AlertTagResponse)
async def create_alert_tag_endpoint(alert_tag: AlertTagCreate, db: AsyncSession = Depends(get_db)):
    return AlertTagResponse(alert_tag=await create_alert_tag(alert_tag, db), success=True, message="Alert tag created successfully")


@incidents_db_operations_router.get("/alert/tag/{tag}", response_model=AlertOutResponse)
async def list_alerts_by_tag_endpoint(
    tag: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List alerts by tag with customer access filtering"""
    logger.info(f"Listing alerts by tag {tag} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get customer access filtering
    accessible_customers = await customer_access_handler.get_user_accessible_customers(current_user, db)

    if "*" in accessible_customers:
        # Admin/analyst - no filtering needed
        alerts = await list_alerts_by_tag(tag, db, page, page_size)
        total = await alerts_total_by_tag(db, tag)
        open_alerts = await alerts_open_by_tag(db, tag)
        in_progress = await alerts_in_progress_by_tag(db, tag)
        closed = await alerts_closed_by_tag(db, tag)
    else:
        # Customer user - filter by accessible customers
        alerts = await list_alerts_multiple_filters(
            tags=[tag],
            customer_code=accessible_customers[0] if len(accessible_customers) == 1 else None,
            db=db,
            page=page,
            page_size=page_size,
            order="desc",
        )
        total = await alert_total_by_customer_codes(db, accessible_customers)
        open_alerts = await alerts_open_by_customer_codes(db, accessible_customers)
        in_progress = await alerts_in_progress_by_customer_codes(db, accessible_customers)
        closed = await alerts_closed_by_customer_codes(db, accessible_customers)

    return AlertOutResponse(
        alerts=alerts,
        total=total,
        open=open_alerts,
        in_progress=in_progress,
        closed=closed,
        success=True,
        message="Alert's tags retrieved successfully",
    )


@incidents_db_operations_router.delete("/alert/tag", response_model=AlertTagResponse)
async def delete_alert_tag_endpoint(alert_tag: AlertTagDelete, db: AsyncSession = Depends(get_db)):
    return AlertTagResponse(
        alert_tag=await delete_alert_tag(alert_tag.alert_id, alert_tag.tag_id, db),
        success=True,
        message="Alert tag deleted successfully",
    )


@incidents_db_operations_router.post("/case/create", response_model=CaseResponse)
async def create_case_endpoint(case: CaseCreate, db: AsyncSession = Depends(get_db)):
    return CaseResponse(case=await create_case(case, db), success=True, message="Case created successfully")


@incidents_db_operations_router.post("/case/alert-link", response_model=CaseAlertLinkResponse)
async def create_case_alert_link_endpoint(case_alert_link: CaseAlertLinkCreate, db: AsyncSession = Depends(get_db)):
    return CaseAlertLinkResponse(
        case_alert_link=await create_case_alert_link(case_alert_link, db),
        success=True,
        message="Case alert link created successfully",
    )


@incidents_db_operations_router.post("/case/alert-links", response_model=CaseAlertLinksResponse)
async def create_case_alert_links_endpoint(case_alert_links: CaseAlertLinksCreate, db: AsyncSession = Depends(get_db)):
    return CaseAlertLinksResponse(
        case_alert_links=await create_case_alert_links_bulk(case_alert_links, db),
        success=True,
        message="Case alert links created successfully",
    )


@incidents_db_operations_router.post("/case/alert-unlink", response_model=CaseAlertUnLinkResponse)
async def case_alert_unlink_endpoint(case_alert_link: CaseAlertUnLink, db: AsyncSession = Depends(get_db)):
    return await case_alert_unlink(case_alert_link, db)


@incidents_db_operations_router.post("/case/from-alert", response_model=CaseAlertLinkResponse)
async def create_case_from_alert_endpoint(alert_id: CaseCreateFromAlert, db: AsyncSession = Depends(get_db)):
    case = await create_case_from_alert(alert_id.alert_id, db)
    if case is None:
        return CaseResponse(case=None, success=False, message="Case not created")
    return CaseAlertLinkResponse(
        case_alert_link=await create_case_alert_link(CaseAlertLinkCreate(case_id=case.id, alert_id=alert_id.alert_id), db),
        success=True,
        message="Case created from alert successfully",
    )


# @incidents_db_operations_router.get("/alerts", response_model=AlertOutResponse)
# async def list_alerts_endpoint(
#     page: int = Query(1, ge=1),
#     page_size: int = Query(25, ge=1),
#     order: str = Query("desc", regex="^(asc|desc)$"),
#     db: AsyncSession = Depends(get_db),
# ):
#     return AlertOutResponse(
#         alerts=await list_alerts(db, page=page, page_size=page_size, order=order),
#         total=await alert_total(db),
#         open=await alerts_open(db),
#         in_progress=await alerts_in_progress(db),
#         closed=await alerts_closed(db),
#         success=True,
#         message="Alerts retrieved successfully",
#     )


@incidents_db_operations_router.get("/alerts", response_model=AlertOutResponse)
async def list_alerts_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1),
    order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(AuthHandler().get_current_user),  # Get the full user object
    db: AsyncSession = Depends(get_db),
):
    logger.info(f"Listing alerts for user: {current_user.username} with role_id: {current_user.role_id}")
    """List alerts with automatic customer filtering"""
    alerts = await list_alerts_for_user(current_user, db, page, page_size, order)

    # Get totals with customer filtering
    accessible_customers = await customer_access_handler.get_user_accessible_customers(current_user, db)

    logger.info(f"User {current_user.username} has access to customers: {accessible_customers}")
    if "*" in accessible_customers:
        # Admin/analyst - use existing total functions
        total = await alert_total(db)
        open_alerts = await alerts_open(db)
        in_progress = await alerts_in_progress(db)
        closed = await alerts_closed(db)
    else:
        # Customer user - filter totals by their customers
        total = await alert_total_by_customer_codes(db, accessible_customers)
        open_alerts = await alerts_open_by_customer_codes(db, accessible_customers)
        in_progress = await alerts_in_progress_by_customer_codes(db, accessible_customers)
        closed = await alerts_closed_by_customer_codes(db, accessible_customers)

    return AlertOutResponse(
        alerts=alerts,
        total=total,
        open=open_alerts,
        in_progress=in_progress,
        closed=closed,
        success=True,
        message="Alerts retrieved successfully",
    )


@incidents_db_operations_router.get("/alert/{alert_id}", response_model=AlertOutResponse)
async def get_alert_by_id_endpoint(
    alert_id: int,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get alert by ID with customer access validation"""
    logger.info(f"Getting alert {alert_id} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get the alert first
    alert = await get_alert_by_id(alert_id, db)

    # Check if user has access to this alert's customer
    if not await customer_access_handler.check_customer_access(current_user, alert.customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to alert {alert_id} - insufficient customer permissions")

    return AlertOutResponse(alerts=[alert], success=True, message="Alert retrieved successfully")


@incidents_db_operations_router.delete("/alert/{alert_id}")
async def delete_alert_endpoint(
    alert_id: int,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete alert with customer access validation"""
    logger.info(f"Deleting alert {alert_id} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get the alert first to check customer access
    alert = await get_alert_by_id(alert_id, db)

    # Check if user has access to this alert's customer
    if not await customer_access_handler.check_customer_access(current_user, alert.customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to alert {alert_id} - insufficient customer permissions")

    await is_alert_linked_to_case(alert_id, db)
    await delete_alert(alert_id, db)
    return {"message": "Alert deleted successfully", "success": True}


@incidents_db_operations_router.delete("/alerts", response_model=DeleteAlertsResponse)
async def delete_alerts_endpoint(request: DeleteAlertsRequest, db: AsyncSession = Depends(get_db)):
    """
    Endpoint to delete alerts.

    This endpoint deletes alerts based on the provided list of alert IDs. If an alert is linked to a case, it will not be deleted and will be skipped.

    Args:
        request (DeleteAlertsRequest): Request object containing the list of alert IDs to be deleted.
        db (AsyncSession, optional): Database session dependency.

    Returns:
        DeleteAlertsResponse: Response object containing the status of the deletion process, including lists of successfully deleted alert IDs and those that were not deleted.

    Raises:
        HTTPException: If an error occurs during the deletion process that is not related to an alert being linked to a case.
    """
    deleted_alert_ids = []
    not_deleted_alert_ids = []
    for alert_id in request.alert_ids:
        try:
            await is_alert_linked_to_case(alert_id, db)
            await delete_alert(alert_id, db)
            deleted_alert_ids.append(alert_id)
        except HTTPException as e:
            if e.status_code == 400:
                logger.info(f"Alert {alert_id} is linked to a case and cannot be deleted. Skipping.")
                not_deleted_alert_ids.append(alert_id)
            else:
                raise e
    return DeleteAlertsResponse(
        message="Alerts processed successfully",
        deleted_alert_ids=deleted_alert_ids,
        not_deleted_alert_ids=not_deleted_alert_ids,
        success=True,
    )


@incidents_db_operations_router.get("/alerts/status/{status}", response_model=AlertOutResponse)
async def list_alerts_by_status_endpoint(
    status: AlertStatus,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1),
    order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List alerts by status with customer access filtering"""
    if status not in AlertStatus:
        raise HTTPException(status_code=400, detail="Invalid status")

    logger.info(f"Listing alerts by status {status} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get customer access filtering
    accessible_customers = await customer_access_handler.get_user_accessible_customers(current_user, db)

    if "*" in accessible_customers:
        # Admin/analyst - no filtering needed
        alerts = await list_alert_by_status(status.value, db, page=page, page_size=page_size, order=order)
        total = await alert_total(db)
        open_alerts = await alerts_open(db)
        in_progress = await alerts_in_progress(db)
        closed = await alerts_closed(db)
    else:
        # Customer user - filter by accessible customers
        # We need to create filtered versions of these functions or use the existing filter functionality
        # For now, let's use the multiple filters function with customer codes
        alerts = await list_alerts_multiple_filters(
            status=status.value,
            customer_code=accessible_customers[0] if len(accessible_customers) == 1 else None,
            db=db,
            page=page,
            page_size=page_size,
            order=order,
        )
        total = await alert_total_by_customer_codes(db, accessible_customers)
        open_alerts = await alerts_open_by_customer_codes(db, accessible_customers)
        in_progress = await alerts_in_progress_by_customer_codes(db, accessible_customers)
        closed = await alerts_closed_by_customer_codes(db, accessible_customers)

    return AlertOutResponse(
        alerts=alerts,
        total=total,
        open=open_alerts,
        in_progress=in_progress,
        closed=closed,
        success=True,
        message="Alerts retrieved successfully",
    )


@incidents_db_operations_router.get("/alerts/assigned-to/{assigned_to}", response_model=AlertOutResponse)
async def list_alerts_by_assigned_to_endpoint(
    assigned_to: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1),
    order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List alerts by assigned user with customer access filtering"""
    logger.info(f"Listing alerts assigned to {assigned_to} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get customer access filtering
    accessible_customers = await customer_access_handler.get_user_accessible_customers(current_user, db)

    if "*" in accessible_customers:
        # Admin/analyst - no filtering needed
        alerts = await list_alert_by_assigned_to(assigned_to, db, page=page, page_size=page_size, order=order)
        total = await alerts_total_by_assigned_to(db, assigned_to)
        open_alerts = await alerts_open_by_assigned_to(db, assigned_to)
        in_progress = await alerts_in_progress_by_assigned_to(db, assigned_to)
        closed = await alerts_closed_by_assigned_to(db, assigned_to)
    else:
        # Customer user - filter by accessible customers
        alerts = await list_alerts_multiple_filters(
            assigned_to=assigned_to,
            customer_code=accessible_customers[0] if len(accessible_customers) == 1 else None,
            db=db,
            page=page,
            page_size=page_size,
            order=order,
        )
        total = await alert_total_by_customer_codes(db, accessible_customers)
        open_alerts = await alerts_open_by_customer_codes(db, accessible_customers)
        in_progress = await alerts_in_progress_by_customer_codes(db, accessible_customers)
        closed = await alerts_closed_by_customer_codes(db, accessible_customers)

    return AlertOutResponse(
        alerts=alerts,
        total=total,
        open=open_alerts,
        in_progress=in_progress,
        closed=closed,
        success=True,
        message="Alerts retrieved successfully",
    )


@incidents_db_operations_router.get("/alerts/asset/{asset_name}", response_model=AlertOutResponse)
async def list_alerts_by_asset_name_endpoint(
    asset_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1),
    order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List alerts by asset name with customer access filtering"""
    logger.info(f"Listing alerts by asset {asset_name} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get customer access filtering
    accessible_customers = await customer_access_handler.get_user_accessible_customers(current_user, db)

    if "*" in accessible_customers:
        # Admin/analyst - no filtering needed
        alerts = await list_alerts_by_asset_name(asset_name, db, page=page, page_size=page_size, order=order)
        total = await alert_total_by_assest_name(db, asset_name)
        open_alerts = await alerts_open_by_assest_name(db, asset_name)
        in_progress = await alerts_in_progress_by_assest_name(db, asset_name)
        closed = await alerts_closed_by_asset_name(db, asset_name)
    else:
        # Customer user - filter by accessible customers
        alerts = await list_alerts_multiple_filters(
            asset_name=asset_name,
            customer_code=accessible_customers[0] if len(accessible_customers) == 1 else None,
            db=db,
            page=page,
            page_size=page_size,
            order=order,
        )
        total = await alert_total_by_customer_codes(db, accessible_customers)
        open_alerts = await alerts_open_by_customer_codes(db, accessible_customers)
        in_progress = await alerts_in_progress_by_customer_codes(db, accessible_customers)
        closed = await alerts_closed_by_customer_codes(db, accessible_customers)

    return AlertOutResponse(
        alerts=alerts,
        total=total,
        open=open_alerts,
        in_progress=in_progress,
        closed=closed,
        success=True,
        message="Alerts retrieved successfully",
    )


@incidents_db_operations_router.get("/alerts/title/{title}", response_model=AlertOutResponse)
async def list_alerts_by_title_endpoint(
    title: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1),
    order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List alerts by title with customer access filtering"""
    logger.info(f"Listing alerts by title {title} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get customer access filtering
    accessible_customers = await customer_access_handler.get_user_accessible_customers(current_user, db)

    if "*" in accessible_customers:
        # Admin/analyst - no filtering needed
        alerts = await list_alerts_by_title(title, db, page=page, page_size=page_size, order=order)
        total = await alert_total_by_alert_title(db, title)
        open_alerts = await alerts_open_by_alert_title(db, title)
        in_progress = await alerts_in_progress_by_alert_title(db, title)
        closed = await alerts_closed_by_alert_title(db, title)
    else:
        # Customer user - filter by accessible customers
        alerts = await list_alerts_multiple_filters(
            alert_title=title,
            customer_code=accessible_customers[0] if len(accessible_customers) == 1 else None,
            db=db,
            page=page,
            page_size=page_size,
            order=order,
        )
        total = await alert_total_by_customer_codes(db, accessible_customers)
        open_alerts = await alerts_open_by_customer_codes(db, accessible_customers)
        in_progress = await alerts_in_progress_by_customer_codes(db, accessible_customers)
        closed = await alerts_closed_by_customer_codes(db, accessible_customers)

    return AlertOutResponse(
        alerts=alerts,
        total=total,
        open=open_alerts,
        in_progress=in_progress,
        closed=closed,
        success=True,
        message="Alerts retrieved successfully",
    )


# @incidents_db_operations_router.get("/alerts/customer/{customer_code}", response_model=AlertOutResponse)
# async def list_alerts_by_customer_code_endpoint(
#     customer_code: str,
#     page: int = Query(1, ge=1),
#     page_size: int = Query(25, ge=1),
#     order: str = Query("desc", regex="^(asc|desc)$"),
#     db: AsyncSession = Depends(get_db),
# ):
#     return AlertOutResponse(
#         alerts=await list_alerts_by_customer_code(customer_code, db, page=page, page_size=page_size, order=order),
#         total=await alerts_total_by_customer_code(db, customer_code),
#         open=await alerts_open_by_customer_code(db, customer_code),
#         in_progress=await alerts_in_progress_by_customer_code(db, customer_code),
#         closed=await alerts_closed_by_customer_code(db, customer_code),
#         success=True,
#         message="Alerts retrieved successfully",
#     )


@incidents_db_operations_router.get("/alerts/customer/{customer_code}", response_model=AlertOutResponse)
async def list_alerts_by_customer_code_endpoint(
    customer_code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1),
    order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(customer_access_handler.require_customer_access()),
    db: AsyncSession = Depends(get_db),
):
    """List alerts for specific customer (with access validation)"""
    # Verify user has access to this specific customer
    if not await customer_access_handler.check_customer_access(current_user, customer_code, db):
        raise HTTPException(status_code=403, detail="Access denied to this customer")

    return AlertOutResponse(
        alerts=await list_alerts_by_customer_code(customer_code, db, page, page_size, order),
        total=await alerts_total_by_customer_code(db, customer_code),
        open=await alerts_open_by_customer_code(db, customer_code),
        in_progress=await alerts_in_progress_by_customer_code(db, customer_code),
        closed=await alerts_closed_by_customer_code(db, customer_code),
        success=True,
        message="Alerts retrieved successfully",
    )


@incidents_db_operations_router.get("/alerts/source/{source}", response_model=AlertOutResponse)
async def list_alerts_by_source_endpoint(
    source: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1),
    order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List alerts by source with customer access filtering"""
    logger.info(f"Listing alerts by source {source} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get customer access filtering
    accessible_customers = await customer_access_handler.get_user_accessible_customers(current_user, db)

    if "*" in accessible_customers:
        # Admin/analyst - no filtering needed
        alerts = await list_alerts_by_source(source, db, page=page, page_size=page_size, order=order)
        total = await alerts_total_by_source(db, source)
        open_alerts = await alerts_open_by_source(db, source)
        in_progress = await alerts_in_progress_by_source(db, source)
        closed = await alerts_closed_by_source(db, source)
    else:
        # Customer user - filter by accessible customers
        alerts = await list_alerts_multiple_filters(
            source=source,
            customer_code=accessible_customers[0] if len(accessible_customers) == 1 else None,
            db=db,
            page=page,
            page_size=page_size,
            order=order,
        )
        total = await alert_total_by_customer_codes(db, accessible_customers)
        open_alerts = await alerts_open_by_customer_codes(db, accessible_customers)
        in_progress = await alerts_in_progress_by_customer_codes(db, accessible_customers)
        closed = await alerts_closed_by_customer_codes(db, accessible_customers)

    return AlertOutResponse(
        alerts=alerts,
        total=total,
        open=open_alerts,
        in_progress=in_progress,
        closed=closed,
        success=True,
        message="Alerts retrieved successfully",
    )


@incidents_db_operations_router.get("/alerts/filter", response_model=AlertOutResponse)
async def list_alerts_multiple_filters_endpoint(
    assigned_to: Optional[str] = Query(None),
    alert_title: Optional[str] = Query(None),
    customer_code: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    asset_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    tags: Optional[List[str]] = Query(None),
    ioc_value: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1),
    order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint to list alerts with multiple filters and customer access control.

    Parameters:
    - assigned_to (str, optional): Filter by assigned user.
    - alert_title (str, optional): Filter by alert title.
    - customer_code (str, optional): Filter by customer code.
    - source (str, optional): Filter by source.
    - asset_name (str, optional): Filter by asset name.
    - status (str, optional): Filter by status.
    - tags (List[str], optional): Filter by tags.
    - ioc_value (str, optional): Filter by IoC value.
    - page (int, default=1): Page number.
    - page_size (int, default=25): Number of alerts per page.
    - order (str, default='desc'): Sorting order ('asc' or 'desc').
    - current_user (User): Current authenticated user.
    - db (AsyncSession): Database session.

    Returns:
    - alerts (List[AlertOut]): List of alerts matching the filters.
    - total (int): Total number of alerts matching the filters.
    - open (int): Number of open alerts matching the filters.
    - in_progress (int): Number of alerts in progress matching the filters.
    - closed (int): Number of closed alerts matching the filters.
    - success (bool): Indicates if the operation was successful.
    - message (str): Success message.
    """
    logger.info(f"Listing alerts with filters for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get customer access filtering
    accessible_customers = await customer_access_handler.get_user_accessible_customers(current_user, db)

    # Apply customer filtering if user is not admin/analyst
    if "*" not in accessible_customers:
        # If user provided customer_code, validate they have access to it
        if customer_code and customer_code not in accessible_customers:
            raise HTTPException(status_code=403, detail=f"Access denied to customer {customer_code}")

        # If no customer_code specified, use the first accessible customer for single customer users
        # For multi-customer users, we'll need to modify the query to handle multiple customers
        if not customer_code and len(accessible_customers) == 1:
            customer_code = accessible_customers[0]

    alerts = await list_alerts_multiple_filters(
        assigned_to=assigned_to,
        alert_title=alert_title,
        customer_code=customer_code,
        source=source,
        asset_name=asset_name,
        status=status,
        tags=tags,
        ioc_value=ioc_value,
        db=db,
        page=page,
        page_size=page_size,
        order=order,
    )

    # Get totals with customer filtering
    if "*" in accessible_customers:
        # Admin/analyst - use existing total functions
        total = await alerts_total_multiple_filters(
            assigned_to=assigned_to,
            alert_title=alert_title,
            customer_code=customer_code,
            source=source,
            asset_name=asset_name,
            status=status,
            tags=tags,
            ioc_value=ioc_value,
            db=db,
        )
        open_alerts = await alerts_open(db)
        in_progress = await alerts_in_progress(db)
        closed = await alerts_closed(db)
        total_unfiltered = await alert_total(db)
    else:
        # Customer user - filter totals by their customers
        total = await alerts_total_multiple_filters(
            assigned_to=assigned_to,
            alert_title=alert_title,
            customer_code=customer_code,
            source=source,
            asset_name=asset_name,
            status=status,
            tags=tags,
            ioc_value=ioc_value,
            db=db,
        )
        open_alerts = await alerts_open_by_customer_codes(db, accessible_customers)
        in_progress = await alerts_in_progress_by_customer_codes(db, accessible_customers)
        closed = await alerts_closed_by_customer_codes(db, accessible_customers)
        total_unfiltered = await alert_total_by_customer_codes(db, accessible_customers)

    return AlertOutResponse(
        alerts=alerts,
        total_filtered=total,
        open=open_alerts,
        in_progress=in_progress,
        closed=closed,
        total=total_unfiltered,
        success=True,
        message="Alerts retrieved successfully",
    )


@incidents_db_operations_router.get("/cases", response_model=CaseOutResponse)
async def list_cases_endpoint(current_user: User = Depends(AuthHandler().get_current_user), db: AsyncSession = Depends(get_db)):
    """List cases with automatic customer filtering"""
    logger.info(f"Listing cases for user: {current_user.username} with role_id: {current_user.role_id}")

    cases = await list_cases_for_user(current_user, db)
    return CaseOutResponse(cases=cases, success=True, message="Cases retrieved successfully")


@incidents_db_operations_router.put("/case/status", response_model=CaseOutResponse)
async def update_case_status_endpoint(
    case_status: UpdateCaseStatus,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update case status with customer access validation"""
    logger.info(f"Updating case {case_status.case_id} status for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get the case first to check customer access
    case = await get_case_by_id(case_status.case_id, db)

    # Check if user has access to this case's customer
    if not await customer_access_handler.check_customer_access(current_user, case.customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to case {case_status.case_id} - insufficient customer permissions")

    # Update the case status
    await update_case_status(case_status, db)

    # Re-fetch the case with full data structure
    updated_case = await get_case_by_id(case_status.case_id, db)
    return CaseOutResponse(cases=[updated_case], success=True, message="Case status updated successfully")


@incidents_db_operations_router.put("/case/assigned-to", response_model=CaseOutResponse)
async def update_case_assigned_to_endpoint(
    assigned_to: AssignedToCase,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update case assigned_to with customer access validation"""
    logger.info(f"Updating case {assigned_to.case_id} assigned_to for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get the case first to check customer access
    case = await get_case_by_id(assigned_to.case_id, db)

    # Check if user has access to this case's customer
    if not await customer_access_handler.check_customer_access(current_user, case.customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to case {assigned_to.case_id} - insufficient customer permissions")

    all_users = await select_all_users()
    user_names = [user.username for user in all_users]
    if assigned_to.assigned_to not in user_names:
        raise HTTPException(status_code=400, detail="User does not exist")

    # Update the case assigned_to
    await update_case_assigned_to(assigned_to.case_id, assigned_to.assigned_to, db)

    # Re-fetch the case with full data structure
    updated_case = await get_case_by_id(assigned_to.case_id, db)
    return CaseOutResponse(
        cases=[updated_case],
        success=True,
        message="Case assigned to user successfully",
    )


@incidents_db_operations_router.put("/case/customer-code", response_model=CaseOutResponse)
async def update_case_customer_code_endpoint(
    case_id: int,
    customer_code: str,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update case customer_code with customer access validation"""
    logger.info(f"Updating case {case_id} customer_code for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get the case first to check current customer access
    case = await get_case_by_id(case_id, db)

    # Check if user has access to the current case's customer
    if not await customer_access_handler.check_customer_access(current_user, case.customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to case {case_id} - insufficient customer permissions")

    # Also check if user has access to the new customer code (for non-admin users)
    accessible_customers = await customer_access_handler.get_user_accessible_customers(current_user, db)
    if "*" not in accessible_customers and customer_code not in accessible_customers:
        raise HTTPException(status_code=403, detail=f"Access denied - cannot assign case to customer {customer_code}")

    # Update the case customer code
    await update_case_customer_code(case_id, customer_code, db)

    # Re-fetch the case with full data structure
    updated_case = await get_case_by_id(case_id, db)
    return CaseOutResponse(
        cases=[updated_case],
        success=True,
        message="Case customer code updated successfully",
    )


@incidents_db_operations_router.delete("/case/{case_id}")
async def delete_case_endpoint(
    case_id: int,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete case with customer access validation"""
    logger.info(f"Deleting case {case_id} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get the case first to check customer access
    case = await get_case_by_id(case_id, db)

    # Check if user has access to this case's customer
    if not await customer_access_handler.check_customer_access(current_user, case.customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to case {case_id} - insufficient customer permissions")

    await delete_case(case_id, db)
    return {"message": "Case deleted successfully", "success": True}


@incidents_db_operations_router.get("/case/status/{status}", response_model=CaseOutResponse)
async def list_cases_by_status_endpoint(
    status: AlertStatus,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List cases by status with customer access filtering"""
    if status not in AlertStatus:
        raise HTTPException(status_code=400, detail="Invalid status")

    logger.info(f"Listing cases by status {status} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get customer access filtering
    accessible_customers = await customer_access_handler.get_user_accessible_customers(current_user, db)

    if "*" in accessible_customers:
        # Admin/analyst - no filtering needed
        cases = await list_cases_by_status(status.value, db)
    else:
        # Customer user - we need to filter, but there's no direct function for this
        # We'll need to get all cases for the user and then filter by status
        all_user_cases = await list_cases_for_user(current_user, db)
        cases = [case for case in all_user_cases if case.case_status == status.value]

    return CaseOutResponse(cases=cases, success=True, message="Cases retrieved successfully")


@incidents_db_operations_router.get("/case/assigned-to/{assigned_to}", response_model=CaseOutResponse)
async def list_cases_by_assigned_to_endpoint(
    assigned_to: str,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List cases by assigned user with customer access filtering"""
    logger.info(f"Listing cases assigned to {assigned_to} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get customer access filtering
    accessible_customers = await customer_access_handler.get_user_accessible_customers(current_user, db)

    if "*" in accessible_customers:
        # Admin/analyst - no filtering needed
        cases = await list_cases_by_assigned_to(assigned_to, db)
    else:
        # Customer user - filter by accessible customers
        all_user_cases = await list_cases_for_user(current_user, db)
        cases = [case for case in all_user_cases if case.assigned_to == assigned_to]

    return CaseOutResponse(cases=cases, success=True, message="Cases retrieved successfully")


@incidents_db_operations_router.get("/case/asset/{asset_name}", response_model=CaseOutResponse)
async def list_cases_by_asset_name_endpoint(
    asset_name: str,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List cases by asset name with customer access filtering"""
    logger.info(f"Listing cases by asset {asset_name} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get customer access filtering
    accessible_customers = await customer_access_handler.get_user_accessible_customers(current_user, db)

    if "*" in accessible_customers:
        # Admin/analyst - no filtering needed
        cases = await list_cases_by_asset_name(asset_name, db)
    else:
        # Customer user - filter by accessible customers and asset name
        all_user_cases = await list_cases_for_user(current_user, db)
        cases = []
        for case in all_user_cases:
            # Check if any alert in the case has the specified asset name
            for alert in case.alerts:
                if alert.assets and any(asset.asset_name == asset_name for asset in alert.assets):
                    cases.append(case)
                    break

    return CaseOutResponse(cases=cases, success=True, message="Cases retrieved successfully")


@incidents_db_operations_router.get("/case/customer/{customer_code}", response_model=CaseOutResponse)
async def list_cases_by_customer_code_endpoint(
    customer_code: str,
    current_user: User = Depends(customer_access_handler.require_customer_access()),
    db: AsyncSession = Depends(get_db),
):
    """List cases for specific customer (with access validation)"""
    logger.info(f"Listing cases for customer {customer_code} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Verify user has access to this specific customer
    if not await customer_access_handler.check_customer_access(current_user, customer_code, db):
        raise HTTPException(status_code=403, detail="Access denied to this customer")

    return CaseOutResponse(cases=await list_cases_by_customer_code(customer_code, db), success=True, message="Cases retrieved successfully")


@incidents_db_operations_router.get("/case/data-store", response_model=ListCaseDataStoreResponse)
async def list_all_case_data_store_files_endpoint(db: AsyncSession = Depends(get_db)):
    logger.info("Listing all files in the data store")
    return ListCaseDataStoreResponse(case_data_store=await list_all_files(db), success=True, message="Files retrieved successfully")


@incidents_db_operations_router.get("/case/data-store/{case_id}", response_model=ListCaseDataStoreResponse)
async def list_case_data_store_files_endpoint(
    case_id: int,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List case data store files with customer access validation"""
    logger.info(f"Listing files for case {case_id} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get the case first to check customer access
    case = await get_case_by_id(case_id, db)

    # Check if user has access to this case's customer
    if not await customer_access_handler.check_customer_access(current_user, case.customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to case {case_id} - insufficient customer permissions")

    return ListCaseDataStoreResponse(
        case_data_store=await list_files_by_case_id(case_id, db),
        success=True,
        message="Files retrieved successfully",
    )


@incidents_db_operations_router.get("/case/data-store/download/{case_id}/{file_name}")
async def download_case_data_store_file_endpoint(
    case_id: int,
    file_name: str,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Download case data store file with customer access validation"""
    logger.info(f"Downloading file {file_name} from case {case_id} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get the case first to check customer access
    case = await get_case_by_id(case_id, db)

    # Check if user has access to this case's customer
    if not await customer_access_handler.check_customer_access(current_user, case.customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to case {case_id} - insufficient customer permissions")

    file_bytes, file_content_type = await download_file_from_case(case_id, file_name, db)
    logger.info(f"Streaming file {file_name} from case {case_id}")
    output = io.BytesIO(file_bytes)
    output.seek(0)

    return StreamingResponse(output, media_type=file_content_type, headers={"Content-Disposition": f"attachment; filename={file_name}"})


@incidents_db_operations_router.post("/case/data-store/upload", response_model=CaseDataStoreResponse)
async def upload_case_data_store_endpoint(
    case_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload file to case data store with customer access validation"""
    logger.info(f"Uploading file {file.filename} to case {case_id} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get the case first to check customer access
    case = await get_case_by_id(case_id, db)

    # Check if user has access to this case's customer
    if not await customer_access_handler.check_customer_access(current_user, case.customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to case {case_id} - insufficient customer permissions")

    if await file_exists(case_id, file.filename, db):
        raise HTTPException(status_code=400, detail="File name already exists for this case")

    return CaseDataStoreResponse(
        case_data_store=await upload_file_to_case(case_id, file, db),
        success=True,
        message="File uploaded successfully",
    )


@incidents_db_operations_router.delete("/case/data-store/{case_id}/{file_name}")
async def delete_case_data_store_file_endpoint(
    case_id: int,
    file_name: str,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete case data store file with customer access validation"""
    logger.info(f"Deleting file {file_name} from case {case_id} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get the case first to check customer access
    case = await get_case_by_id(case_id, db)

    # Check if user has access to this case's customer
    if not await customer_access_handler.check_customer_access(current_user, case.customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to case {case_id} - insufficient customer permissions")

    await delete_file_from_case(case_id, file_name, db)
    return {"message": "File deleted successfully", "success": True}


@incidents_db_operations_router.get("/case/{case_id}", response_model=CaseOutResponse)
async def get_case_by_id_endpoint(
    case_id: int,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get case by ID with customer access validation"""
    logger.info(f"Getting case {case_id} for user: {current_user.username} with role_id: {current_user.role_id}")

    # Get the case first
    case = await get_case_by_id(case_id, db)

    # Check if user has access to this case's customer
    if not await customer_access_handler.check_customer_access(current_user, case.customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to case {case_id} - insufficient customer permissions")

    return CaseOutResponse(cases=[case], success=True, message="Case retrieved successfully")


@incidents_db_operations_router.post("/case/notification", response_model=CaseNotificationResponse)
async def create_case_notification_endpoint(
    request: CaseNotificationCreate,
    current_user: User = Depends(AuthHandler().get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create case notification with customer access validation.

    This function collects the case details and then invokes the create_case_notification function to create a new case notification within the Shuffle Workflow.

    Args:
        request (CaseNotificationCreate): The request object containing the case details.
        current_user (User): Current authenticated user.
        db (AsyncSession, optional): The database session dependency.

    Returns:
        CaseNotificationResponse: The response object containing the created case notification.
    """
    logger.info(
        f"Creating case notification for case {request.case_id} for user: {current_user.username} with role_id: {current_user.role_id}",
    )

    case_details = await get_case_by_id(request.case_id, db)

    # Check if user has access to this case's customer
    if not await customer_access_handler.check_customer_access(current_user, case_details.customer_code, db):
        raise HTTPException(status_code=403, detail=f"Access denied to case {request.case_id} - insufficient customer permissions")

    case_notification_payload = CreatedCaseNotificationPayload(
        case_name=case_details.case_name,
        case_description=case_details.case_description,
        case_creation_time=case_details.case_creation_time,
        alerts=[
            CreatedAlertPayload(
                alert_context_payload=(await get_alert_context_by_id(alert.assets[0].alert_context_id, db)).context
                if alert.assets
                else None,  # Populate with actual alert context data
                asset_payload=alert.assets[0].asset_name if alert.assets else "",  # Populate with actual asset data
                timefield_payload="",  # Populate with actual timefield data
                alert_title_payload=alert.alert_name,  # Populate with actual alert title data
                ioc_payload={ioc.value: ioc.type for ioc in alert.iocs} if alert.iocs else {},  # Populate with actual IoC data if available
                source=alert.source,
            )
            for alert in case_details.alerts
        ],
    )

    logger.info(f"Creating case notification for case {case_notification_payload}")
    await handle_customer_notifications_case(customer_code=case_details.customer_code, case_payload=case_notification_payload, session=db)
    await increment_case_notification_count(request.case_id, db)
    return CaseNotificationResponse(success=True, message="Case notification created successfully")


@incidents_db_operations_router.get("/case-report-template", response_model=CaseReportTemplateDataStoreListResponse)
async def list_case_report_template_data_store_files_endpoint(db: AsyncSession = Depends(get_db)):
    logger.info("Listing all files in the data store")
    return CaseReportTemplateDataStoreListResponse(
        case_report_template_data_store=await list_case_report_template_data_store_files(),
        success=True,
        message="Files retrieved successfully",
    )


@incidents_db_operations_router.get("/case-report-template/do-default-template-exists")
async def check_default_case_report_template_exists_endpoint(db: AsyncSession = Depends(get_db)):
    """
    Endpoint to check if any of the default case report template files exist in the data store.

    If any of them do, return True, else return False.

    Returns:
    - success (bool): Indicates if the operation was successful.
    - message (str): Success message.
    - default_template_exists (bool): Indicates if any of the default case report template files exist in the data store.
    """
    for template in DefaultReportTemplateFileNames:
        if await report_template_exists(template.value, db):
            return {"success": True, "message": "Default case report template exists", "default_template_exists": True}

    return {"success": True, "message": "No default case report templates exist", "default_template_exists": False}


@incidents_db_operations_router.post("/case-report-template/default-template", response_model=CaseReportTemplateDataStoreListResponse)
async def create_default_case_report_template_endpoint(db: AsyncSession = Depends(get_db)):
    """
    Create a default case report template in the data store.

    Returns:
        CaseReportTemplateDataStoreListResponse: The response containing the created case report template data store.

    Raises:
        None
    """
    logger.info("Creating default file in the data store")
    return CaseReportTemplateDataStoreListResponse(
        case_report_template_data_store=await upload_report_template_to_data_store(db),
        success=True,
        message="Default file created successfully",
    )


@incidents_db_operations_router.get("/case-report-template/download/{file_name}")
async def download_case_report_template_endpoint(file_name: str, db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    file_bytes, file_content_type = await download_report_template(file_name, db)
    logger.info(f"Streaming file {file_name}")
    output = io.BytesIO(file_bytes)
    output.seek(0)

    return StreamingResponse(output, media_type=file_content_type, headers={"Content-Disposition": f"attachment; filename={file_name}"})


@incidents_db_operations_router.post("/case-report-template/upload", response_model=CaseReportTemplateDataStoreResponse)
async def upload_case_report_template_endpoint(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # Check if the file type is a .docx or .html
    mime_type, _ = mimetypes.guess_type(file.filename)
    allowed_mime_types = ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/html"]  # .docx  # .html
    if mime_type not in allowed_mime_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only .docx and .html files are allowed.")

    if await report_template_exists(file.filename, db):
        raise HTTPException(status_code=400, detail="File name already exists for this template")

    return CaseReportTemplateDataStoreResponse(
        case_report_template_data_store=await upload_report_template(file, db),
        success=True,
        message="File uploaded successfully",
    )


@incidents_db_operations_router.delete("/case-report-template/{file_name}")
async def delete_case_report_template_endpoint(file_name: str, db: AsyncSession = Depends(get_db)):
    await delete_report_template(file_name, db)
    return {"message": "File deleted successfully", "success": True}
