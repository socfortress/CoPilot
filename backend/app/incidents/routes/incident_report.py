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
from typing import Any, Dict
from typing import List
from app.customers.routes.customers import get_customer
from datetime import datetime
from io import BytesIO, StringIO
import csv
from fastapi.responses import StreamingResponse
import pandas as pd

incidents_report_router = APIRouter()

# Constants
FIELDNAMES = [
    'Case ID', 'Case Name', 'Case Description', 'Case Creation Time', 'Case Status',
    'Case Assigned To', 'Case Customer Code', 'Alert ID', 'Alert Name', 'Alert Description',
    'Alert Status', 'Alert Creation Time', 'Alert Time Closed', 'Alert Source', 'Alert Assigned To',
    'Assets', 'Tags', 'Comments', 'Customer Code'
]

# Helper Functions
async def fetch_cases_with_related_data(session: AsyncSession) -> List[Case]:
    """Fetch cases with related alerts, assets, tags, and comments."""
    result = await session.execute(
        select(Case)
        .options(
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).options(
                selectinload(Alert.assets),
                selectinload(Alert.tags).selectinload(AlertToTag.tag),
                selectinload(Alert.comments)
            )
        )
    )
    return result.scalars().all()

async def fetch_cases_by_customer(
    session: AsyncSession, customer_code: str
) -> List[Case]:
    """Fetch cases for a specific customer with related data."""
    result = await session.execute(
        select(Case)
        .where(Case.customer_code == customer_code)
        .options(
            selectinload(Case.alerts).selectinload(CaseAlertLink.alert).options(
                selectinload(Alert.assets),
                selectinload(Alert.tags).selectinload(AlertToTag.tag),
                selectinload(Alert.comments)
            )
        )
    )
    return result.scalars().all()

def serialize_case_alert_to_row(case: Case, alert: Alert) -> Dict[str, Any]:
    """Serialize a case and its alert into a CSV row."""
    assets = ';'.join(asset.asset_name for asset in alert.assets or [])
    tags = ';'.join(alert_tag.tag.tag for alert_tag in alert.tags or [])
    comments = ';'.join(comment.comment for comment in alert.comments or [])

    return {
        'Case ID': case.id,
        'Case Name': case.case_name,
        'Case Description': case.case_description,
        'Case Creation Time': case.case_creation_time.strftime('%Y-%m-%d %H:%M:%S'),
        'Case Status': case.case_status,
        'Case Assigned To': case.assigned_to or '',
        'Case Customer Code': case.customer_code or '',
        'Alert ID': alert.id,
        'Alert Name': alert.alert_name,
        'Alert Description': alert.alert_description,
        'Alert Status': alert.status,
        'Alert Creation Time': alert.alert_creation_time.strftime('%Y-%m-%d %H:%M:%S'),
        'Alert Time Closed': alert.time_closed.strftime('%Y-%m-%d %H:%M:%S') if alert.time_closed else '',
        'Alert Source': alert.source,
        'Alert Assigned To': alert.assigned_to or '',
        'Assets': assets,
        'Tags': tags,
        'Comments': comments,
        'Customer Code': alert.customer_code
    }

def generate_csv_content(rows: List[Dict[str, Any]]) -> StringIO:
    """Generate CSV content from rows."""
    csv_stream = StringIO()
    writer = csv.DictWriter(csv_stream, fieldnames=FIELDNAMES, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    csv_stream.seek(0)
    return csv_stream

# Route Handler
@incidents_report_router.post(
    "/generate-report",
    description="Generate a report for all cases.",
)
async def get_cases_export_all_route(
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    cases = await fetch_cases_with_related_data(session)
    rows = [
        serialize_case_alert_to_row(case, alert_link.alert)
        for case in cases
        for alert_link in case.alerts
    ]
    csv_stream = generate_csv_content(rows)
    filename = f"cases_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response = StreamingResponse(csv_stream, media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@incidents_report_router.post(
    "/generate-report/{customer_code}",
    description="Generate a report for a customer",
)
async def get_cases_export_customer_route(
    customer_code: str,
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    await get_customer(customer_code=customer_code, session=session)
    cases = await fetch_cases_by_customer(session, customer_code)
    rows = [
        serialize_case_alert_to_row(case, alert_link.alert)
        for case in cases
        for alert_link in case.alerts
    ]
    csv_stream = generate_csv_content(rows)
    filename = f"cases_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response = StreamingResponse(csv_stream, media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response
