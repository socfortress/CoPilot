"""E2E for #1263 (the portal's report poll) — NOT collected by pytest (needs a live MySQL
and MinIO); run by hand.

The disposable MySQL on 13306 of customer_portal_overview_e2e.py (see its docstring), the
same seed, and a disposable MinIO on 19000 — never the MinIO in .env:

    docker run -d --name copilot-e2e-minio -p 127.0.0.1:19000:9000 \\
        -e MINIO_ROOT_USER=e2eminio -e MINIO_ROOT_PASSWORD=e2eminio-secret \\
        minio/minio:RELEASE.2024-09-13T20-26-02Z server /data

    .venv/bin/python tests/e2e/customer_report_status_e2e.py

Real routers, a real portal login, real PDF rendering (wkhtmltopdf) and real storage:

  A) the portal user generates a report: the answer's status URL is a real route, the
     poll reports it completed, and its download link returns the PDF;
  B) the poll answers for the reports asked only: a running one with its start and
     running time, a completed one with its download, a failed one with a generic error;
  C) what the list hides, the poll hides: another customer's report, an analyst report
     not shared with the portal, a report that does not exist, all reported missing alike;
  D) a failed report's own error (here a storage failure) reaches the SOC, never the
     customer, in the poll and in the list;
  E) the request is bounded and light: at least one id, at most 50; one query for the
     reports, however many are asked.

Exits non-zero when a check fails.
"""

import asyncio
import datetime
import os
import sys
from unittest.mock import patch

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")
# Set before the app reads .env (python-dotenv never overrides what is already set).
os.environ["MINIO_URL"] = os.environ.get("E2E_MINIO_URL", "127.0.0.1:19000")
os.environ["MINIO_ROOT_USER"] = os.environ.get("E2E_MINIO_USER", "e2eminio")
os.environ["MINIO_ROOT_PASSWORD"] = os.environ.get("E2E_MINIO_PASSWORD", "e2eminio-secret")
os.environ["MINIO_SECURE"] = "False"

import httpx  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

import app.incidents.services.customer_report as report_service  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import IncidentManagementCustomerReport  # noqa: E402
from app.time_utils import now_utc  # noqa: E402
from app.time_utils import to_naive_utc  # noqa: E402
from tests.e2e.customer_portal_overview_e2e import StatementCounter  # noqa: E402
from tests.e2e.customer_portal_overview_e2e import build_app  # noqa: E402
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_B  # noqa: E402
from tests.e2e.portal_overview_seed import PASSWORD  # noqa: E402
from tests.e2e.portal_overview_seed import PORTAL_USER  # noqa: E402
from tests.e2e.portal_overview_seed import cleanup  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

results = []
STATUS = "/incidents/customer_reports/status"


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


async def add_reports(portal_user_id: int) -> dict:
    """The rows the poll is asked about, beside the seed's completed ones."""
    now = to_naive_utc(now_utc()).replace(microsecond=0)

    def row(name, code, status, role="customer_user", visible=False, started=now, error=None):
        return IncidentManagementCustomerReport(
            report_name=name,
            customer_code=code,
            object_key=f"{code}/{name}.pdf",
            file_name=f"{name}.pdf",
            generated_at=started,
            generated_by=portal_user_id,
            generated_by_role=role,
            visible_to_customer=visible,
            date_from=now - datetime.timedelta(days=7),
            date_to=now,
            status=status,
            error_message=error,
        )

    rows = {
        "running": row("e2e running", CUST_A, "processing", started=now - datetime.timedelta(minutes=3)),
        "failed": row(
            "e2e failed",
            CUST_A,
            "failed",
            error="Failed to store report in MinIO: S3 operation failed; code: AccessDenied, bucket: incident-management-reports",
        ),
        "shared": row("e2e shared", CUST_A, "processing", role="analyst", visible=True),
        "hidden": row("e2e hidden", CUST_A, "processing", role="analyst", visible=False),
        "theirs": row("e2e theirs", CUST_B, "processing"),
    }
    async with AsyncSession(async_engine) as s:
        s.add_all(rows.values())
        await s.flush()
        report_ids = {key: report.id for key, report in rows.items()}
        await s.commit()
        return report_ids


def poll(client, headers, *ids):
    return client.get(STATUS, params=[("ids", str(i)) for i in ids], headers=headers)


async def main():
    ids = await seed()
    rows = await add_reports(ids["portal_user_id"])
    counter = StatementCounter()

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e", timeout=120) as client:
        login = await client.post("/auth/token/customer-portal", data={"username": PORTAL_USER, "password": PASSWORD})
        portal = {"Authorization": f"Bearer {login.json()['access_token']}"}
        admin = {"Authorization": f"Bearer {await AuthHandler().encode_token(ADMIN)}"}

        print("\n=== A) a report generated for real, polled and downloaded ===")
        today = datetime.date.today()
        generate = await client.post(
            "/incidents/customer_reports/generate/background",
            json={
                "customer_code": CUST_A,
                "date_from": (today - datetime.timedelta(days=30)).isoformat() + "T00:00:00Z",
                "date_to": today.isoformat() + "T23:59:59Z",
                "report_name": "e2e generated",
                "report_template": "executive",
            },
            headers=portal,
        )
        body = generate.json()
        check("generate: 200", generate.status_code == 200, generate.text[:160])
        generated = body.get("report_id")
        check(
            "its status URL is the poll, on a mounted route",
            body.get("check_status_url") == f"/api{STATUS}?ids={generated}",
            body.get("check_status_url"),
        )
        # The background task has run by now: the ASGI transport waits for it.
        response = await client.get(body["check_status_url"].removeprefix("/api"), headers=portal)
        status = (response.json().get("reports") or [{}])[0]
        check("the poll reports it completed", status.get("status") == "completed", str(status)[:200])
        check(
            "with no running time and its download link",
            status.get("running_seconds") is None and status.get("download_url") == body.get("download_url"),
            str(status)[:200],
        )
        pdf = await client.get(status["download_url"].removeprefix("/api"), headers=portal)
        check(
            "the link downloads the PDF",
            pdf.status_code == 200 and pdf.content[:5] == b"%PDF-",
            f"{pdf.status_code} {pdf.content[:8]!r}",
        )

        print("\n=== B) the reports asked, and only them ===")
        response = await poll(client, portal, rows["running"], generated, rows["failed"], rows["running"])
        body = response.json()
        by_id = {r["id"]: r for r in body.get("reports", [])}
        check("200", response.status_code == 200, response.text[:120])
        check("in the order asked, once each", [r["id"] for r in body["reports"]] == [rows["running"], generated, rows["failed"]])
        running = by_id[rows["running"]]
        check("a running report: processing, no download", running["status"] == "processing" and running["download_url"] is None)
        check("…running for about three minutes", 175 <= (running["running_seconds"] or 0) <= 240, str(running["running_seconds"]))
        check("…since an instant with its offset", running["started_at"].endswith("Z"), running["started_at"])
        check("…and named, for the notification", running["report_name"] == "e2e running" and running["file_name"] == "e2e running.pdf")
        check("nothing missing", body["missing"] == [])

        print("\n=== C) what the list hides, the poll hides ===")
        unknown = 987654321
        response = await poll(client, portal, rows["shared"], rows["hidden"], rows["theirs"], unknown)
        body = response.json()
        check("a shared analyst report is answered", [r["id"] for r in body["reports"]] == [rows["shared"]], str(body)[:200])
        check(
            "a hidden one, another customer's and an unknown id are missing alike",
            body["missing"] == [rows["hidden"], rows["theirs"], unknown],
            str(body["missing"]),
        )
        listed = {r["id"] for r in (await client.get("/incidents/customer_reports", headers=portal)).json()["reports"]}
        check("the same as the list", rows["shared"] in listed and not ({rows["hidden"], rows["theirs"]} & listed), str(sorted(listed)))
        response = await poll(client, admin, rows["hidden"], rows["theirs"])
        check("the SOC sees both", [r["id"] for r in response.json()["reports"]] == [rows["hidden"], rows["theirs"]])

        print("\n=== D) a failed report's own error is the SOC's ===")
        failed_portal = (await poll(client, portal, rows["failed"])).json()["reports"][0]
        failed_admin = (await poll(client, admin, rows["failed"])).json()["reports"][0]
        check(
            "the customer reads a generic error",
            failed_portal["error_message"] == report_service.CUSTOMER_FAILURE_MESSAGE,
            failed_portal["error_message"],
        )
        check("the SOC reads the real one", "AccessDenied" in (failed_admin["error_message"] or ""), failed_admin["error_message"])
        listed = {r["id"]: r for r in (await client.get("/incidents/customer_reports", headers=portal)).json()["reports"]}
        check("the list says the same to the customer", listed[rows["failed"]]["error_message"] == report_service.CUSTOMER_FAILURE_MESSAGE)
        listed = {r["id"]: r for r in (await client.get("/incidents/customer_reports", headers=admin)).json()["reports"]}
        check("…and to the SOC", "AccessDenied" in (listed[rows["failed"]]["error_message"] or ""))

        async def broken_storage(**_kwargs):
            return {"success": False, "error": "S3 operation failed; code: NoSuchBucket, endpoint 10.0.0.9:9000"}

        with patch.object(report_service, "store_file_in_minio", broken_storage):
            broken = await client.post(
                "/incidents/customer_reports/generate/background",
                json={
                    "customer_code": CUST_A,
                    "date_from": (today - datetime.timedelta(days=7)).isoformat() + "T00:00:00Z",
                    "date_to": today.isoformat() + "T23:59:59Z",
                    "report_name": "e2e storage down",
                },
                headers=portal,
            )
        broken_id = broken.json()["report_id"]
        portal_view = (await poll(client, portal, broken_id)).json()["reports"][0]
        admin_view = (await poll(client, admin, broken_id)).json()["reports"][0]
        check("a generation that really fails: failed", portal_view["status"] == "failed", str(portal_view)[:160])
        check("…its endpoint never reaches the customer", "10.0.0.9" not in str(portal_view) and "NoSuchBucket" not in str(portal_view))
        check("…but the SOC can tell why", "NoSuchBucket" in (admin_view["error_message"] or ""), admin_view["error_message"])

        print("\n=== E) bounded and light ===")
        for name, params in (
            ("no id: 422", []),
            ("51 ids: 422", [("ids", str(i)) for i in range(1, 52)]),
            ("an id that is not a number: 422", [("ids", "abc")]),
        ):
            response = await client.get(STATUS, params=params, headers=portal)
            check(name, response.status_code == 422, f"{response.status_code} {response.text[:80]}")
        response = await poll(client, portal, *range(1, 51))
        check("50 ids: 200", response.status_code == 200, str(response.status_code))
        check("without a token: 401", (await client.get(STATUS, params=[("ids", "1")])).status_code == 401)

        counter.reset()
        await poll(client, portal, *[rows[k] for k in ("running", "failed", "shared", "hidden", "theirs")], generated)
        report_reads = [s for s in counter.statements if "incident_management_customer_reports" in s]
        check("one query reads the reports, however many are asked", len(report_reads) == 1, str(len(report_reads)))
        check(
            "and only the columns a poller needs",
            "filters_json" not in report_reads[0].split("FROM")[0] and "file_hash" not in report_reads[0].split("FROM")[0],
            report_reads[0][:200],
        )
        check("the whole request stays small", len(counter.statements) <= 4, f"{len(counter.statements)} statements")

        deleted = await client.delete(f"/incidents/customer_reports/{generated}", headers=portal)
        check("the generated report deletes, its file with it", deleted.status_code == 200, deleted.text[:120])
        check("then the poll reports it missing", (await poll(client, portal, generated)).json()["missing"] == [generated])

    async with AsyncSession(async_engine) as s:
        await cleanup(s)
    await async_engine.dispose()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{'=' * 60}\nRESULT: {passed}/{len(results)} checks passed")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAILED: {name} [{detail}]")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
