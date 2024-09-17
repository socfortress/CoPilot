from fastapi import APIRouter
from fastapi import Depends
from fastapi import Security
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.utils import AuthHandler
from app.db.db_session import get_db
from app.incidents.schema.alert_collection import AlertsPayload
from app.incidents.schema.incident_alert import AlertDetailsResponse
from app.incidents.schema.incident_alert import AlertTimelineResponse
from app.incidents.schema.incident_alert import AutoCreateAlertResponse
from app.incidents.schema.incident_alert import CreateAlertRequest
from app.incidents.schema.incident_alert import CreateAlertRequestRoute
from app.incidents.schema.incident_alert import CreateAlertResponse
from app.incidents.schema.incident_alert import IndexNamesResponse
from app.incidents.services.alert_collection import add_copilot_alert_id
from app.incidents.services.alert_collection import get_alerts_not_created_in_copilot
from app.incidents.services.alert_collection import get_graylog_event_indices
from app.incidents.services.alert_collection import get_original_alert_id
from app.incidents.services.alert_collection import get_original_alert_index_name
from sqlalchemy.orm import selectinload
from app.incidents.services.incident_alert import create_alert
from app.incidents.models import Alert
from app.incidents.models import AlertContext
from app.incidents.models import AlertTag
from app.incidents.models import AlertTitleFieldName
from app.data_store.data_store_schema import CaseDataStoreCreation
from app.data_store.data_store_operations import upload_case_data_store, delete_file, download_case_data_store
from app.incidents.models import AlertToTag
from app.incidents.models import Asset
from app.incidents.models import AssetFieldName
from app.incidents.models import Case
from app.incidents.models import CaseAlertLink
from app.incidents.models import Comment, CaseDataStore
from app.incidents.models import CustomerCodeFieldName
from app.incidents.models import FieldName
from app.incidents.models import Notification
from app.incidents.models import TimestampFieldName
from app.incidents.services.incident_alert import get_single_alert_details
from app.incidents.services.incident_alert import retrieve_alert_timeline
from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from datetime import datetime
from io import BytesIO
from fastapi.responses import StreamingResponse
import pandas as pd

incidents_report_router = APIRouter()



@incidents_report_router.post(
    "/generate-report/{customer_code}",
    description="Generate a report for a customer",
)
async def get_alert_timeline_route(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> AlertTimelineResponse:
    """
    Get the timeline of an alert. This route obtains the process_id from the alert details if it exists
    and queries the Indexer for all events with the same process_id and hostname within a 24 hour period.

    Args:
        create_alert_request (CreateAlertRequestRoute): The request object containing the details of the alert to be created.


    Returns:
        class AlertTimelineResponse(BaseModel): The response object containing the details of the alert.
    """
    # Fetch all cases for the customer
    cases = session.execute(
        select(Case)
        .where(
            Case.alerts.any(
                CaseAlertLink.alert.has(
                    Alert.customer_code == customer_code
                )
            )
        )
        .options(
            selectinload(Case.alerts)
            .selectinload(CaseAlertLink.alert)
            .selectinload(Alert.comments),
            selectinload(Case.alerts)
            .selectinload(CaseAlertLink.alert)
            .selectinload(Alert.tags)
            .selectinload(AlertToTag.tag),
            selectinload(Case.alerts)
            .selectinload(CaseAlertLink.alert)
            .selectinload(Alert.assets),
            selectinload(Case.data_store)
        )
    ).all()

    if not cases:
        raise HTTPException(status_code=404, detail="No cases found for the customer.")

    # Create a BytesIO stream to hold the Excel file
    output = BytesIO()

    # Create an Excel writer using pandas
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for case in cases:
            # Fetch related data
            alerts = [link.alert for link in case.alerts]
            data_store_items = case.data_store

            # Create DataFrames for each type of data
            case_data = {
                'Case ID': [case.id],
                'Case Name': [case.case_name],
                'Case Description': [case.case_description],
                'Case Creation Time': [case.case_creation_time],
                'Case Status': [case.case_status],
                'Assigned To': [case.assigned_to],
            }
            df_case = pd.DataFrame(case_data)

            # Alerts DataFrame
            alerts_data = []
            for alert in alerts:
                alert_info = {
                    'Alert ID': alert.id,
                    'Alert Name': alert.alert_name,
                    'Description': alert.alert_description,
                    'Status': alert.status,
                    'Creation Time': alert.alert_creation_time,
                    'Assigned To': alert.assigned_to,
                }
                alerts_data.append(alert_info)
            df_alerts = pd.DataFrame(alerts_data)

            # Comments DataFrame
            comments_data = []
            for alert in alerts:
                for comment in alert.comments:
                    comment_info = {
                        'Alert ID': alert.id,
                        'Comment ID': comment.id,
                        'User Name': comment.user_name,
                        'Comment': comment.comment,
                        'Created At': comment.created_at,
                    }
                    comments_data.append(comment_info)
            df_comments = pd.DataFrame(comments_data)

            # Tags DataFrame
            tags_data = []
            for alert in alerts:
                for tag_link in alert.tags:
                    tag_info = {
                        'Alert ID': alert.id,
                        'Tag': tag_link.tag.tag,
                    }
                    tags_data.append(tag_info)
            df_tags = pd.DataFrame(tags_data)

            # Assets DataFrame
            assets_data = []
            for alert in alerts:
                for asset in alert.assets:
                    asset_info = {
                        'Alert ID': alert.id,
                        'Asset ID': asset.id,
                        'Asset Name': asset.asset_name,
                        'Agent ID': asset.agent_id,
                        'Customer Code': asset.customer_code,
                        'Index Name': asset.index_name,
                        'Index ID': asset.index_id,
                    }
                    assets_data.append(asset_info)
            df_assets = pd.DataFrame(assets_data)

            # Write DataFrames to Excel sheets
            sheet_name = f"Case {case.id}"
            # Write case data
            df_case.to_excel(writer, sheet_name=sheet_name, startrow=0, index=False)
            # Write alerts data
            alerts_start_row = len(df_case) + 2
            df_alerts.to_excel(writer, sheet_name=sheet_name, startrow=alerts_start_row, index=False)
            # Write comments data
            comments_start_row = alerts_start_row + len(df_alerts) + 2
            df_comments.to_excel(writer, sheet_name=sheet_name, startrow=comments_start_row, index=False)
            # Write tags data
            tags_start_row = comments_start_row + len(df_comments) + 2
            df_tags.to_excel(writer, sheet_name=sheet_name, startrow=tags_start_row, index=False)
            # Write assets data
            assets_start_row = tags_start_row + len(df_tags) + 2
            df_assets.to_excel(writer, sheet_name=sheet_name, startrow=assets_start_row, index=False)

            # Optionally, adjust column widths and formatting
            workbook  = writer.book
            worksheet = writer.sheets[sheet_name]

            for df in [df_case, df_alerts, df_comments, df_tags, df_assets]:
                for idx, col in enumerate(df.columns):
                    column_len = df[col].astype(str).str.len().max()
                    column_len = max(column_len, len(col)) + 2
                    worksheet.set_column(idx, idx, column_len)

    output.seek(0)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"Report_{customer_code}_{timestamp}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )
