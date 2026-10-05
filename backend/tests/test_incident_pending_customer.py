"""PENDING_CUSTOMER ("Waiting on customer") outside the SLA domain (#1187).

Pinned here:
- status counts bucket it apart, and every count response carries the bucket, so totals
  add up in every list;
- reopening into any status but CLOSED clears the closed timestamp (a stale one made
  reports count a case reopened to IN_PROGRESS or PENDING_CUSTOMER as closed);
- customer reports label it and colour it apart;
- a customer may not set it: it is the SOC asking them for something.

Run with: cd backend && python -m pytest tests/test_incident_pending_customer.py
"""

import asyncio
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402

from app.customer_portal.schema.dashboard import (  # noqa: E402
    CustomerDashboardAlertStatsResponse,
)
from app.customer_portal.schema.dashboard import (  # noqa: E402
    CustomerDashboardCaseStatsResponse,
)
from app.customer_portal.schema.overview import OverviewStatusCounts  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import Case  # noqa: E402
from app.incidents.schema.db_operations import AlertOutResponse  # noqa: E402
from app.incidents.schema.db_operations import AlertStatus  # noqa: E402
from app.incidents.schema.db_operations import CaseOutResponse  # noqa: E402
from app.incidents.schema.db_operations import UpdateAlertStatus  # noqa: E402
from app.incidents.schema.db_operations import UpdateCaseStatus  # noqa: E402
from app.incidents.services.customer_reply import (  # noqa: E402
    ensure_customer_may_set_status,
)
from app.incidents.services.customer_report import _status_label  # noqa: E402
from app.incidents.services.customer_report_charts import STATUS_COLORS  # noqa: E402
from app.incidents.services.customer_report_charts import _colors_for  # noqa: E402
from app.incidents.services.db_operations import StatusCounts  # noqa: E402
from app.incidents.services.db_operations import _status_counts  # noqa: E402
from app.incidents.services.db_operations import update_alert_status  # noqa: E402
from app.incidents.services.db_operations import update_case_status  # noqa: E402
from tests.soc_management_support import Db  # noqa: E402
from tests.soc_management_support import add_alert  # noqa: E402
from tests.soc_management_support import add_case  # noqa: E402

PORTAL = SimpleNamespace(username="portal", role_id=4)
ANALYST = SimpleNamespace(username="ana", role_id=2)


# ── counts ───────────────────────────────────────────────────────────────────


def test_status_counts_bucket_waiting_on_customer_apart():
    counts = _status_counts([("OPEN", 3), ("IN_PROGRESS", 2), ("PENDING_CUSTOMER", 4), ("CLOSED", 5), ("SOMETHING_ELSE", 1)])
    assert counts == StatusCounts(total=15, open=3, in_progress=2, closed=5, pending_customer=4)
    assert counts.open + counts.in_progress + counts.closed + counts.pending_customer == counts.total - 1  # the unknown one


@pytest.mark.parametrize(
    "model",
    [AlertOutResponse, CaseOutResponse, CustomerDashboardAlertStatsResponse, CustomerDashboardCaseStatsResponse, OverviewStatusCounts],
)
def test_every_count_response_carries_the_bucket(model):
    assert "pending_customer" in model.model_fields


def test_the_dashboard_responses_take_the_counts_as_they_come():
    counts = StatusCounts(total=9, open=1, in_progress=2, closed=3, pending_customer=3)
    response = CustomerDashboardAlertStatsResponse(**counts._asdict(), success=True, message="")
    assert response.pending_customer == 3
    assert OverviewStatusCounts(**counts._asdict()).pending_customer == 3


# ── closed timestamps ────────────────────────────────────────────────────────


def run(scenario):
    async def _inner():
        db = await Db().create()
        try:
            return await scenario(db)
        finally:
            await db.dispose()

    return asyncio.run(_inner())


@pytest.mark.parametrize("reopened_to", ["OPEN", "IN_PROGRESS", "PENDING_CUSTOMER"])
def test_reopening_an_alert_into_any_status_clears_its_closed_time(reopened_to):
    async def scenario(db):
        async with db.session() as session:
            alert = await add_alert(session)
            closed = await update_alert_status(UpdateAlertStatus(alert_id=alert.id, status="CLOSED"), session)
            closed_at = closed.time_closed
            reopened = await update_alert_status(UpdateAlertStatus(alert_id=alert.id, status=reopened_to), session)
            return closed_at, (await session.get(Alert, reopened.id)).time_closed

    closed_at, after = run(scenario)
    assert closed_at is not None and after is None


@pytest.mark.parametrize("reopened_to", ["OPEN", "IN_PROGRESS", "PENDING_CUSTOMER"])
def test_reopening_a_case_into_any_status_clears_its_closed_time(reopened_to):
    async def scenario(db):
        async with db.session() as session:
            case = await add_case(session)
            closed = await update_case_status(UpdateCaseStatus(case_id=case.id, status="CLOSED"), session)
            closed_at = closed.case_closed_time
            await update_case_status(UpdateCaseStatus(case_id=case.id, status=reopened_to), session)
            return closed_at, (await session.get(Case, case.id)).case_closed_time

    closed_at, after = run(scenario)
    assert closed_at is not None and after is None


# ── customer reports ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "case_status, closed_time, label",
    [
        ("CLOSED", "2026-09-01", "CLOSED"),
        ("PENDING_CUSTOMER", None, "WAITING ON CUSTOMER"),
        ("IN_PROGRESS", None, "OPEN"),
        ("OPEN", None, "OPEN"),
    ],
)
def test_report_case_cards_label_waiting_on_customer(case_status, closed_time, label):
    assert _status_label(SimpleNamespace(case_status=case_status, case_closed_time=closed_time)) == label


def test_report_charts_colour_waiting_on_customer_apart():
    colours = _colors_for(["OPEN", "IN_PROGRESS", "PENDING_CUSTOMER", "CLOSED"], status_aware=True)
    assert colours[2] == STATUS_COLORS["PENDING_CUSTOMER"]
    assert len(set(colours)) == 4


# ── who may set it ───────────────────────────────────────────────────────────


def test_a_customer_may_not_set_waiting_on_customer():
    with pytest.raises(HTTPException) as refused:
        ensure_customer_may_set_status(PORTAL, AlertStatus.PENDING_CUSTOMER)
    assert refused.value.status_code == 403 and "reply with a comment" in refused.value.detail
    ensure_customer_may_set_status(PORTAL, AlertStatus.IN_PROGRESS)
    ensure_customer_may_set_status(PORTAL, "CLOSED")
    ensure_customer_may_set_status(ANALYST, AlertStatus.PENDING_CUSTOMER)
