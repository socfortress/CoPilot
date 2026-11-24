"""E2E for cloud security assessment on real MySQL (#1328). NOT collected by pytest: it needs a live,
disposable MySQL at the migration head.

    docker run -d --name copilot-e2e-mysql -p 13306:3306 \\
        -e MYSQL_ROOT_PASSWORD=e2eroot -e MYSQL_DATABASE=copilot \\
        -e MYSQL_USER=copilot -e MYSQL_PASSWORD=e2epass mysql:8.4.13

    cd backend && export MYSQL_URL=127.0.0.1:13306 MYSQL_USER=copilot \\
        MYSQL_PASSWORD=e2epass MYSQL_ROOT_PASSWORD=e2eroot \\
        JWT_SECRET=e2e-test-secret-not-the-default PYTHONPATH=$PWD
    alembic upgrade head   # or run tests/e2e/cloud_assessment_migration_e2e.py first
    .venv/bin/python tests/e2e/cloud_assessment_e2e.py

Point it at a throwaway instance on 13306, never at the MySQL in .env: it creates and deletes
customers, accounts and scans. copilot-prowler and MinIO are the unit tests' fakes
(``tests/cloud_assessment_support.py``); the routers, services, job and database are real.

What it proves, on MySQL (what SQLite in the unit tests can't):
- two requests starting a scan of one account at once make one scan (the row lock), and two job
  ticks racing for one queued scan hand it to the runner once (the guarded UPDATE);
- a completed scan's checks and findings are stored with their JSON and utf8mb4 text intact,
  None as SQL NULL, and the next scan's new and resolved counts and carried first-seen times;
- retention prunes the older scan's findings; deleting the account takes every row with it.
"""

import asyncio
import os
import sys
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
from cryptography.fernet import Fernet  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.auth.utils import AuthHandler  # noqa: E402
from app.cloud_assessment.services import reports  # noqa: E402
from app.cloud_assessment.services import runner_client  # noqa: E402
from app.cloud_assessment.services import scans  # noqa: E402
from app.cloud_assessment.utils import utc_now  # noqa: E402
from app.db.db_session import AsyncSessionLocal  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.routers import cloud_assessment  # noqa: E402
from tests.cloud_assessment_support import AWS_ROLE  # noqa: E402
from tests.cloud_assessment_support import RUNNER_URL  # noqa: E402
from tests.cloud_assessment_support import TOKEN  # noqa: E402
from tests.cloud_assessment_support import FakeMinio  # noqa: E402
from tests.cloud_assessment_support import FakeRunner  # noqa: E402
from tests.cloud_assessment_support import finding  # noqa: E402

assert os.environ["MYSQL_URL"].endswith(":13306"), "a disposable MySQL on 13306 only"
CUSTOMER = "E2E_CA"
ADMIN = SimpleNamespace(id=1, username="e2e-admin", role_id=1)
results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


async def q(sql, **params):
    async with AsyncSessionLocal() as session:
        result = await session.execute(text(sql), params)
        rows = result.fetchall() if result.returns_rows else None
        await session.commit()
        return rows


async def main() -> int:
    runner = FakeRunner()
    minio = FakeMinio()
    os.environ["CLOUD_ASSESSMENT_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    os.environ["PROWLER_RUNNER_URL"] = RUNNER_URL
    os.environ["PROWLER_RUNNER_TOKEN"] = TOKEN
    os.environ["CLOUD_ASSESSMENT_KEEP_FINDINGS_SCANS"] = "1"
    runner_client.TRANSPORT = runner.transport()

    async def fake_minio():
        return minio

    reports._client = fake_minio
    api = FastAPI()
    api.include_router(cloud_assessment.router)

    async def resolve_user(self, request, username):
        return ADMIN

    await q("DELETE FROM customers WHERE customer_code = :c", c=CUSTOMER)
    await q("INSERT INTO customers (customer_code, customer_name, created_at) VALUES (:c, 'E2E cloud', NOW())", c=CUSTOMER)
    base = f"/cloud_assessment/{CUSTOMER}"
    with patch.object(AuthHandler, "decode_token", lambda self, token: ("e2e-admin", ["admin"])), patch.object(
        AuthHandler,
        "_resolve_user",
        resolve_user,
    ):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api),
            base_url="http://e2e",
            headers={"Authorization": "Bearer x"},
        ) as client:
            print("== an account, and two scans started at once")
            account = (await client.post(f"{base}/accounts", json=AWS_ROLE)).json()["account"]
            check(
                "the account is saved with a generated External ID",
                account["external_id"].startswith("copilot-"),
                account["external_id"],
            )
            runner.start_error = (429, "busy")  # keep both queued, so the race is the lock's
            raced = await asyncio.gather(*[client.post(f"{base}/accounts/{account['id']}/scans") for _ in range(2)])
            codes = sorted(answer.status_code for answer in raced)
            check("two starts at once make one scan", codes == [200, 409], codes)

            print("== two ticks racing for one queued scan")
            runner.start_error = None
            await asyncio.gather(scans.run_tick(), scans.run_tick())
            check("the runner got the scan once", len(runner.jobs) == 1, len(runner.jobs))

            print("== storing a completed scan")
            runner.findings = [
                finding(1, resource_name="sérvér-🔥-\u202eevil", resource_tags=["owner:équipe"]),
                finding(2),
                finding(3, check_id="s3_bucket_public", severity="critical", resource_tags=[]),
            ]
            runner.finish(next(iter(runner.jobs)))
            await scans.run_tick()
            first = (await client.get(f"{base}/scans")).json()["scans"][0]
            check("the scan completed", first["status"] == "completed", first["status"])
            stored = await q(
                "SELECT resource_name, JSON_EXTRACT(resource_tags, '$[0]'), resource_tags IS NULL FROM cloud_assessment_finding "
                "WHERE scan_id = :s ORDER BY id",
                s=first["id"],
            )
            check(
                "utf8mb4 text and JSON round-trip",
                stored[0][0] == "sérvér-🔥-\u202eevil" and stored[0][1] == '"owner:équipe"',
                stored[0][:2],
            )
            check("an empty list is SQL NULL", stored[2][2] == 1, stored[2])
            compliance = await q(
                "SELECT JSON_EXTRACT(compliance, '$.\"CIS-5.0\"[0]') FROM cloud_assessment_check_result WHERE scan_id = :s ORDER BY check_id",
                s=first["id"],
            )
            check("a check's compliance mapping is JSON", compliance[0][0] == '"1.1"', compliance)

            print("== the next scan")
            before = dict(await q("SELECT finding_uid_hash, first_seen_at FROM cloud_assessment_finding WHERE scan_id = :s", s=first["id"]))
            runner.findings = [finding(1, resource_name="sérvér-🔥-\u202eevil"), finding(4)]
            await client.post(f"{base}/accounts/{account['id']}/scans")
            runner.finish(next(iter(runner.jobs)))
            scans._last_retention = None
            await scans.run_tick(now=utc_now() + timedelta(seconds=2))
            second = (await client.get(f"{base}/scans")).json()["scans"][0]
            check(
                "one new failure and two resolved",
                (second["counts"]["new_failed"], second["counts"]["resolved_failed"]) == (1, 2),
                second["counts"],
            )
            after = await q(
                "SELECT finding_uid_hash, first_seen_at, is_new FROM cloud_assessment_finding WHERE scan_id = :s",
                s=second["id"],
            )
            carried = sorted((first_seen == before.get(uid_hash), bool(is_new)) for uid_hash, first_seen, is_new in after)
            check("a finding still failing keeps its first-seen time, a new one is new", carried == [(False, True), (True, False)], carried)

            print("== retention and deletion")
            pruned = await q(
                "SELECT findings_pruned_at IS NOT NULL, (SELECT COUNT(*) FROM cloud_assessment_finding WHERE scan_id = :s) FROM cloud_assessment_scan WHERE id = :s",
                s=first["id"],
            )
            check("the older scan's findings are pruned, its counts kept", pruned == [(1, 0)], pruned)
            deleted = await client.delete(f"{base}/accounts/{account['id']}")
            left = await q(
                "SELECT (SELECT COUNT(*) FROM cloud_assessment_account WHERE customer_code = :c), (SELECT COUNT(*) FROM cloud_assessment_scan WHERE customer_code = :c), "
                "(SELECT COUNT(*) FROM cloud_assessment_finding WHERE customer_code = :c)",
                c=CUSTOMER,
            )
            check("deleting the account deletes its rows", deleted.status_code == 200 and left == [(0, 0, 0)], left)
    await q("DELETE FROM customers WHERE customer_code = :c", c=CUSTOMER)
    await async_engine.dispose()
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
