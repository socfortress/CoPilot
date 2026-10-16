"""The portal's report poll (#1263): a light status read, and errors a customer may read.

The portal used to learn a report was ready by reloading the whole report list every few
seconds. ``GET /incidents/customer_reports/status?ids=…`` answers for the reports it waits
for only, under the same visibility as the list. A failed report's stored error is the
exception's own text (storage, database, PDF renderer): the SOC reads it, a customer
reads a generic message, in the status and in the list alike.

No DB, no network: the query is run against a recording session. The routes, the real
database and the visibility rules end to end are tests/e2e/customer_report_status_e2e.py.

Run with: cd backend && python -m pytest tests/test_customer_report_status.py
"""

import asyncio
import os
from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import mysql

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from app.data_store.data_store_session import minio_endpoint  # noqa: E402
from app.db.universal_models import IncidentManagementCustomerReport  # noqa: E402
from app.incidents.services import customer_report as service  # noqa: E402
from app.incidents.services.customer_report import (  # noqa: E402
    CUSTOMER_FAILURE_MESSAGE,
)
from app.incidents.services.customer_report import public_error  # noqa: E402
from app.incidents.services.customer_report import report_statuses  # noqa: E402
from app.incidents.services.customer_report import (  # noqa: E402
    report_visibility_filters,
)

NOW = datetime(2026, 10, 16, 10, 0, 0)


def _sql(filters) -> str:
    return " AND ".join(str(f.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True})) for f in filters)


class TestPublicError:
    def test_only_a_failed_report_has_an_error(self):
        assert public_error("processing", "stale text", for_customer=False) is None
        assert public_error("completed", "stale text", for_customer=True) is None

    def test_the_soc_reads_the_stored_error_a_customer_a_generic_one(self):
        raw = "Failed to store report in MinIO: S3 operation failed; code: AccessDenied, resource: /incident-management-reports"
        assert public_error("failed", raw, for_customer=False) == raw
        assert public_error("failed", raw, for_customer=True) == CUSTOMER_FAILURE_MESSAGE
        assert "MinIO" not in CUSTOMER_FAILURE_MESSAGE

    def test_the_list_says_the_same_as_the_poll(self):
        report = IncidentManagementCustomerReport(
            id=7,
            report_name="r",
            customer_code="A",
            object_key="A/r.pdf",
            file_name="r.pdf",
            generated_by=1,
            date_from=NOW,
            date_to=NOW,
            generated_at=NOW,
            status="failed",
            error_message="(pymysql.err.OperationalError) (1205, 'Lock wait timeout') [SQL: SELECT …]",
        )
        assert service.to_response(report, for_customer=True).error_message == CUSTOMER_FAILURE_MESSAGE
        assert "SQL" in service.to_response(report).error_message


class TestVisibility:
    def test_a_caller_with_no_customer_sees_nothing(self):
        assert report_visibility_filters([], only_customer_visible=False) is None

    def test_deployment_wide_sees_everything(self):
        assert report_visibility_filters(["*"], only_customer_visible=False) == []

    def test_a_portal_user_sees_their_customers_own_and_shared_reports(self):
        sql = _sql(report_visibility_filters(["A", "B"], only_customer_visible=True))
        assert "customer_code IN ('A', 'B')" in sql
        assert "visible_to_customer IS true" in sql
        assert "generated_by_role = 'customer_user'" in sql

    def test_an_analyst_sees_every_report_of_their_customers(self):
        sql = _sql(report_visibility_filters(["A"], only_customer_visible=False))
        assert "customer_code IN ('A')" in sql
        assert "visible_to_customer" not in sql


class RecordingSession:
    """Answers the status query with fixed rows and keeps the statement it was given."""

    def __init__(self, rows):
        self.rows = rows
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return SimpleNamespace(all=lambda: self.rows)


def _row(report_id, status, started=NOW - timedelta(minutes=2), error=None):
    return SimpleNamespace(
        id=report_id,
        report_name=f"report {report_id}",
        file_name=f"report-{report_id}.pdf",
        status=status,
        error_message=error,
        generated_at=started,
    )


def _statuses(rows, ids, accessible=("A",), portal=True):
    session = RecordingSession(rows)
    result = asyncio.run(report_statuses(session, ids, list(accessible), portal, NOW))
    return result, session


class TestStatuses:
    def test_answers_in_the_order_asked_once_each_and_names_the_missing(self):
        (reports, missing), _ = _statuses([_row(2, "completed"), _row(1, "processing")], [1, 9, 2, 1])
        assert [r.id for r in reports] == [1, 2]
        assert missing == [9]

    def test_reads_only_what_a_poller_needs_in_one_query(self):
        (_, _), session = _statuses([_row(1, "processing")], [1])
        assert len(session.statements) == 1
        sql = str(session.statements[0].compile(dialect=mysql.dialect()))
        selected = sql.split("FROM")[0]
        for column in ("filters_json", "object_key", "file_hash", "total_alerts"):
            assert column not in selected
        assert "visible_to_customer" in sql  # the portal's visibility is in the same query

    def test_a_running_report_says_since_when_and_for_how_long(self):
        (reports, _), _ = _statuses([_row(1, "processing", started=NOW - timedelta(minutes=3, seconds=5))], [1])
        status = reports[0]
        assert status.running_seconds == 185
        assert status.download_url is None
        assert status.model_dump(mode="json")["started_at"] == "2026-10-16T09:56:55Z"

    def test_a_clock_ahead_of_the_database_never_reads_negative(self):
        (reports, _), _ = _statuses([_row(1, "processing", started=NOW + timedelta(seconds=30))], [1])
        assert reports[0].running_seconds == 0

    def test_a_finished_report_has_no_running_time_and_a_download_when_completed(self):
        (reports, _), _ = _statuses([_row(1, "completed"), _row(2, "failed", error="wkhtmltopdf exited with code 1")], [1, 2])
        completed, failed = reports
        assert (completed.running_seconds, completed.download_url) == (None, "/api/incidents/customer_reports/1/download")
        assert (failed.running_seconds, failed.download_url) == (None, None)
        assert failed.error_message == CUSTOMER_FAILURE_MESSAGE

    def test_the_soc_reads_the_real_error(self):
        (reports, _), _ = _statuses([_row(2, "failed", error="wkhtmltopdf exited with code 1")], [2], portal=False)
        assert reports[0].error_message == "wkhtmltopdf exited with code 1"

    def test_a_caller_with_no_customer_never_reaches_the_database(self):
        (reports, missing), session = _statuses([_row(1, "completed")], [1, 2], accessible=())
        assert (reports, missing, session.statements) == ([], [1, 2], [])


class TestUrls:
    """The URLs a generation answers with lead to real routes (they said /api/v1, which none is under)."""

    @pytest.fixture(scope="class")
    def paths(self):
        import copilot

        return {route.path for route in copilot.app.routes}

    def test_status_and_download_urls_name_mounted_routes(self, paths):
        status = service.STATUS_URL_TEMPLATE.format(report_id=5)
        download = service.DOWNLOAD_URL_TEMPLATE.format(report_id=5)
        assert status.split("?")[0] in paths and status.endswith("?ids=5")
        assert download.replace("/5/", "/{report_id}/") in paths


class TestMinioEndpoint:
    def test_a_bare_host_gets_minios_port_and_a_host_with_a_port_keeps_it(self):
        assert minio_endpoint("copilot-minio") == "copilot-minio:9000"
        assert minio_endpoint("10.255.255.5") == "10.255.255.5:9000"
        assert minio_endpoint("127.0.0.1:19000") == "127.0.0.1:19000"
