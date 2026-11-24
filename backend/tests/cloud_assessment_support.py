"""Shared harness for the cloud assessment tests (#1328): an in-memory SQLite database with the real
tables, the real router with only token decoding and user lookup replaced, a fake copilot-prowler
behind an ``httpx.MockTransport`` that keeps jobs by the runner's rules, and a fake MinIO."""

import asyncio
import hashlib
import json
import os
from types import SimpleNamespace
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
from cryptography.fernet import Fernet  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy import event  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import app.auth.models.users  # noqa: E402,F401 - registers user/role tables
import app.connectors.talon.models.talon_v2  # noqa: E402,F401 - talon_connector_settings
from app.auth.models.users import Role  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.cloud_assessment.models.cloud_assessment import (  # noqa: E402
    CloudAssessmentAccount,
)
from app.cloud_assessment.models.cloud_assessment import (  # noqa: E402
    CloudAssessmentScan,
)
from app.cloud_assessment.services import reports  # noqa: E402
from app.cloud_assessment.services import runner_client  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402

TOKEN = "t" * 40
RUNNER_URL = "http://runner.test"
USERS = {
    "admin": SimpleNamespace(id=1, username="admin", role_id=1),
    "ana": SimpleNamespace(id=2, username="ana", role_id=2),
    "portal": SimpleNamespace(id=4, username="portal", role_id=4),
    # A token still carrying "admin" after its user was made an analyst.
    "demoted": SimpleNamespace(id=5, username="demoted", role_id=2),
    "talon-analyst": SimpleNamespace(id=6, username="talon-analyst", role_id=2),
}
SCOPES = {"admin": ["admin"], "ana": ["analyst"], "portal": ["customer_user"], "demoted": ["admin"], "talon-analyst": ["analyst"]}
TABLES = (
    "user",
    "role",
    "user_customer_access",
    "customers",
    "talon_connector_settings",
    "cloud_assessment_account",
    "cloud_assessment_scan",
    "cloud_assessment_check_result",
    "cloud_assessment_finding",
)

AWS_KEYS = {"access_key_id": "AKIAABCDEFGHIJKLMNOP", "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"}
CLIENT_SECRET = "Abc8Q~very.secret-value_123"
ROLE_ARN = "arn:aws:iam::123456789012:role/ProwlerScan"
TENANT = "72f988bf-86f1-41af-91ab-2d7cd011db47"
CLIENT = "11111111-2222-3333-4444-555555555555"


def gcp_key(**overrides) -> Dict[str, Any]:
    key = {
        "type": "service_account",
        "project_id": "acme-prod-1",
        "private_key_id": "a" * 40,
        "private_key": "-----BEGIN PRIVATE KEY-----\n" + "MIIB" * 40 + "\n-----END PRIVATE KEY-----\n",
        "client_email": "prowler@acme-prod-1.iam.gserviceaccount.com",
        "client_id": "123456789012345678901",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/prowler%40acme-prod-1.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com",
    }
    key.update(overrides)
    return key


AWS_ROLE = {
    "name": "Production",
    "provider": "aws",
    "auth_method": "role",
    "config": {"role_arn": ROLE_ARN, "regions": ["eu-west-1"]},
    "secret": AWS_KEYS,
}
AWS_KEYS_ACCOUNT = {"name": "Keys", "provider": "aws", "auth_method": "access_keys", "config": {}, "secret": AWS_KEYS}
AZURE = {
    "name": "Azure",
    "provider": "azure",
    "auth_method": "client_secret",
    "config": {"tenant_id": TENANT, "client_id": CLIENT, "subscription_ids": [CLIENT]},
    "secret": {"client_secret": CLIENT_SECRET},
}
M365 = {
    "name": "M365",
    "provider": "m365",
    "auth_method": "client_secret",
    "config": {"tenant_id": TENANT, "client_id": CLIENT, "tenant_domain": "acme.onmicrosoft.com"},
    "secret": {"client_secret": CLIENT_SECRET},
    "secret_expires_at": "2027-01-31T00:00:00Z",
}
GCP = {
    "name": "GCP",
    "provider": "gcp",
    "auth_method": "service_account_key",
    "config": {"project_ids": ["acme-prod-1"]},
    "secret": {"service_account_key": gcp_key()},
}


# --- a fake copilot-prowler ------------------------------------------------------------------------


def finding(
    index: int,
    check_id: str = "iam_root_mfa_enabled",
    status: str = "FAIL",
    severity: str = "high",
    muted: bool = False,
    **extra,
) -> Dict[str, Any]:
    uid = extra.pop("uid", f"prowler-aws-{check_id}-123456789012-eu-west-1-resource{index}")
    item = {
        "finding_uid": uid,
        "finding_uid_sha256": hashlib.sha256(uid.encode()).hexdigest(),
        "check_id": check_id,
        "status": status,
        "severity": severity,
        "muted": muted,
        "status_extended": f"Resource {index} is not compliant.",
        "service": check_id.split("_")[0],
        "region": "eu-west-1",
        "cloud_account_uid": "123456789012",
        "cloud_account_name": "production",
        "resource_uid": f"arn:aws:iam::123456789012:user/resource{index}",
        "resource_name": f"resource{index}",
        "resource_type": "AwsIamUser",
        "resource_tags": ["env:prod"],
        "time": "2026-11-23T10:00:00.000000",
    }
    item.update(extra)
    return item


def summary(checks: List[Dict[str, Any]], totals: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    totals = totals or {"total": 10, "pass": 5, "fail": 3, "manual": 1, "muted": 1}
    return {
        "provider": "aws",
        "prowler_version": "5.52.0",
        "totals": totals,
        "fail_by_severity": {"critical": 1, "high": 2, "medium": 0, "low": 0, "informational": 0, "unknown": 0},
        "cloud_accounts": ["123456789012"],
        "skipped": 0,
        "checks": checks,
    }


def check(
    check_id: str,
    fail: int = 1,
    passed: int = 0,
    manual: int = 0,
    muted: int = 0,
    compliance: Optional[Dict[str, List[str]]] = None,
    **extra,
) -> Dict[str, Any]:
    entry = {
        "check_id": check_id,
        "title": f"Title of {check_id}",
        "description": "What it checks.",
        "service": check_id.split("_")[0],
        "severity": "high",
        "risk": "What could go wrong.",
        "remediation": "How to fix it.",
        "references": ["https://hub.prowler.com/check/" + check_id, "javascript:alert(1)"],
        "additional_urls": [],
        "categories": ["identity-access"],
        "types": [],
        "compliance": compliance if compliance is not None else {"CIS-5.0": ["1.1"]},
        "pass": passed,
        "fail": fail,
        "manual": manual,
        "muted": muted,
    }
    entry.update(extra)
    return entry


CATALOG = {
    "provider": "aws",
    "prowler_version": "5.52.0",
    "frameworks": [
        {
            "key": "CIS-5.0",
            "file": "cis_5.0_aws",
            "framework": "CIS",
            "version": "5.0",
            "name": "CIS Amazon Web Services Foundations Benchmark v5.0",
            "description": "The CIS benchmark.",
            "requirements": [
                {
                    "id": "1.1",
                    "name": "Maintain current contact details",
                    "description": "",
                    "section": "1 IAM",
                    "checks": ["iam_root_mfa_enabled"],
                },
                {
                    "id": "1.2",
                    "name": "Ensure security contact information is registered",
                    "description": "",
                    "section": "1 IAM",
                    "checks": ["account_security_contact"],
                },
                {"id": "1.3", "name": "A manual one", "description": "", "section": "1 IAM", "checks": []},
            ],
        },
    ],
    "skipped_files": 0,
}


class FakeRunner:
    """copilot-prowler, by its rules: a bearer token, job ids of 32 hex, ``{"detail", "code"}`` errors."""

    def __init__(self) -> None:
        self.requests: List[httpx.Request] = []
        self.bodies: List[Any] = []
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.counter = 0
        self.connection_verdict: Dict[str, Any] = {"ok": True, "code": None, "message": None, "prowler_error": None}
        self.start_error: Optional[tuple] = None  # (status, code)
        self.unreachable = False
        self.summary: Dict[str, Any] = summary(
            [check("iam_root_mfa_enabled", fail=2), check("s3_bucket_public", fail=1, compliance={"CIS-5.0": ["2.1"]})],
        )
        self.findings: List[Any] = [finding(1), finding(2), finding(3, check_id="s3_bucket_public", severity="critical")]
        self.artifacts: Dict[str, bytes] = {"html": b"<html><body>report</body></html>", "csv": b"a;b\n1;2\n"}
        self.catalog: Optional[Dict[str, Any]] = CATALOG
        self.deleted: List[str] = []

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def new_job(self, payload: Any) -> str:
        self.counter += 1
        job_id = f"{self.counter:032x}"
        self.jobs[job_id] = {"status": "running", "payload": payload, "error": None, "prowler_errors": [], "error_lines": 0}
        return job_id

    def public(self, job_id: str) -> Dict[str, Any]:
        job = self.jobs[job_id]
        error = {"code": job["error"], "message": "x", "prowler_errors": job["prowler_errors"]} if job["error"] else None
        return {
            "job_id": job_id,
            "provider": "aws",
            "status": job["status"],
            "prowler_version": "5.52.0",
            "created_at": "2026-11-23T10:00:00Z",
            "started_at": "2026-11-23T10:00:00Z",
            "finished_at": None,
            "timeout_seconds": 14400,
            "exit_code": None,
            "error": error,
            "logs": {"error_lines": job["error_lines"], "critical_lines": 0, "error_classes": []},
            "totals": None,
        }

    @staticmethod
    def error(status: int, code: str) -> httpx.Response:
        return httpx.Response(status, json={"detail": "fixed text", "code": code})

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.unreachable:
            raise httpx.ConnectError("refused")
        if request.headers.get("authorization") != f"Bearer {TOKEN}":
            return self.error(401, "unauthorized")
        path = request.url.path
        body = json.loads(request.content) if request.content else None
        self.bodies.append(body)
        if path == "/v1/health":
            return httpx.Response(
                200,
                json={
                    "status": "ok",
                    "runner_version": "0.1.0",
                    "prowler_version": "5.52.0",
                    "powershell": True,
                    "providers": ["aws", "azure", "gcp", "m365"],
                    "max_concurrent": 2,
                    "running": 0,
                    "jobs": 0,
                },
            )
        if path == "/v1/connection-test":
            return httpx.Response(200, json=self.connection_verdict)
        if path == "/v1/scans" and request.method == "POST":
            if self.start_error:
                return self.error(*self.start_error)
            return httpx.Response(202, json=self.public(self.new_job(body)))
        if path.startswith("/v1/compliance/"):
            return httpx.Response(200, json=self.catalog) if self.catalog else self.error(404, "unknown_provider")
        parts = path.split("/")
        if len(parts) >= 4 and parts[1:3] == ["v1", "scans"]:
            job_id = parts[3]
            if job_id not in self.jobs:
                return self.error(404, "not_found")
            job = self.jobs[job_id]
            if request.method == "DELETE":
                self.deleted.append(job_id)
                del self.jobs[job_id]
                return httpx.Response(204)
            if len(parts) == 4:
                return httpx.Response(200, json=self.public(job_id))
            if job["status"] != "completed":
                return self.error(409, "not_ready")
            if parts[4] == "summary":
                return httpx.Response(200, json=self.summary)
            if parts[4] == "findings":
                lines = [json.dumps(item) if not isinstance(item, (bytes, str)) else item for item in self.findings]
                content = "\n".join(line.decode() if isinstance(line, bytes) else line for line in lines) + "\n"
                return httpx.Response(200, content=content.encode(), headers={"content-type": "application/x-ndjson"})
            if parts[4] == "artifacts":
                data = self.artifacts.get(parts[5])
                return httpx.Response(200, content=data) if data is not None else self.error(404, "no_artifact")
        return self.error(404, "not_found")

    def finish(self, job_id: str, status: str = "completed", error: Optional[str] = None, prowler_errors=None) -> None:
        self.jobs[job_id].update(status=status, error=error, prowler_errors=prowler_errors or [])

    def paths(self, method: Optional[str] = None) -> List[str]:
        return [request.url.path for request in self.requests if method is None or request.method == method]


# --- a fake MinIO -----------------------------------------------------------------------------------


class _Content:
    def __init__(self, data: bytes) -> None:
        self.data = data

    async def iter_chunked(self, size: int):
        for start in range(0, len(self.data), size):
            yield self.data[start : start + size]


class _Response:
    def __init__(self, data: bytes) -> None:
        self.content = _Content(data)
        self.released = False

    def release(self) -> None:
        self.released = True


class FakeMinio:
    def __init__(self) -> None:
        self.objects: Dict[tuple, bytes] = {}
        self.buckets: set = set()
        self.removed: List[tuple] = []
        self.fail_put = False

    async def bucket_exists(self, bucket: str) -> bool:
        return bucket in self.buckets

    async def make_bucket(self, bucket: str) -> None:
        self.buckets.add(bucket)

    async def put_object(self, bucket, key, data, length, part_size=0, content_type=None, num_parallel_uploads=3):
        if self.fail_put:
            raise RuntimeError("minio down")
        assert length == -1 and part_size >= 5 << 20
        content = b""
        while True:
            chunk = data.read(part_size)
            if asyncio.iscoroutine(chunk):
                chunk = await chunk
            if not chunk:
                break
            content += chunk
        self.objects[(bucket, key)] = content

    async def get_object(self, bucket_name: str, object_name: str):
        if (bucket_name, object_name) not in self.objects:
            raise KeyError("NoSuchKey")
        return _Response(self.objects[(bucket_name, object_name)])

    async def remove_object(self, bucket: str, key: str) -> None:
        self.removed.append((bucket, key))
        self.objects.pop((bucket, key), None)

    async def close_session(self) -> None:
        return None


# --- the database and the app ---------------------------------------------------------------------


class Db:
    def __init__(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

        @event.listens_for(self.engine.sync_engine, "connect")
        def _foreign_keys(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self.factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def create(self) -> "Db":
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=[SQLModel.metadata.tables[name] for name in TABLES]))
        async with self.factory() as session:
            session.add_all(
                [Role(id=role_id, name=name, description=name) for role_id, name in ((1, "admin"), (2, "analyst"), (4, "customer_user"))],
            )
            await session.commit()
            session.add_all(
                [
                    User(id=1, username="admin", password="x" * 8, email="admin@example.com", role_id=1),
                    User(id=2, username="ana", password="x" * 8, email="ana@example.com", role_id=2),
                    User(id=5, username="demoted", password="x" * 8, email="demoted@example.com", role_id=2),
                    User(id=6, username="talon-analyst", password="x" * 8, email="talon@example.com", role_id=2),
                    Customers(customer_code="ACME", customer_name="Acme Corp"),
                    Customers(customer_code="GLOBEX", customer_name="Globex"),
                ],
            )
            await session.commit()
            session.add_all(
                [
                    UserCustomerAccess(user_id=2, customer_code="ACME"),
                    UserCustomerAccess(user_id=5, customer_code="ACME"),
                    UserCustomerAccess(user_id=6, customer_code="ACME"),
                ],
            )
            await session.commit()
        return self

    async def rows(self, model, *where) -> list:
        async with self.factory() as session:
            return list((await session.execute(select(model).where(*where))).scalars().all())

    async def scan(self, scan_id: int) -> CloudAssessmentScan:
        async with self.factory() as session:
            return await session.get(CloudAssessmentScan, scan_id)

    async def account(self, account_id: int) -> CloudAssessmentAccount:
        async with self.factory() as session:
            return await session.get(CloudAssessmentAccount, account_id)


def make_app(db: Db) -> FastAPI:
    from app.routers import cloud_assessment

    api = FastAPI()
    api.include_router(cloud_assessment.router)

    async def _session():
        async with db.factory() as session:
            yield session

    api.dependency_overrides[get_db] = _session
    return api


class World:
    """Everything a scenario uses."""

    def __init__(self, db: Db, client: httpx.AsyncClient, runner: FakeRunner, minio: FakeMinio) -> None:
        self.db = db
        self.client = client
        self.runner = runner
        self.minio = minio

    async def tick(self, now=None):
        from app.cloud_assessment.services.scans import run_tick

        return await run_tick(session_factory=self.db.factory, now=now)

    async def add(self, payload: Dict[str, Any], who: str = "admin", code: str = "ACME") -> httpx.Response:
        return await self.client.post(f"/cloud_assessment/{code}/accounts", json=payload, headers=as_user(who))


def as_user(name: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {name}"}


def run(scenario, monkeypatch, runner: Optional[FakeRunner] = None, minio: Optional[FakeMinio] = None, key: bool = True):
    """Run ``scenario(world)`` with the env, the fakes and a fresh database."""
    from app.cloud_assessment.services import scans

    runner = runner or FakeRunner()
    minio = minio or FakeMinio()
    if key:
        monkeypatch.setenv("CLOUD_ASSESSMENT_ENCRYPTION_KEY", Fernet.generate_key().decode())
    else:
        monkeypatch.delenv("CLOUD_ASSESSMENT_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("PROWLER_RUNNER_URL", RUNNER_URL)
    monkeypatch.setenv("PROWLER_RUNNER_TOKEN", TOKEN)
    monkeypatch.setattr(runner_client, "TRANSPORT", runner.transport())
    runner_client.clear_catalog_cache()

    async def fake_client():
        return minio

    monkeypatch.setattr(reports, "_client", fake_client)
    monkeypatch.setattr(scans, "_last_retention", None)

    async def _inner():
        db = await Db().create()
        try:
            transport = httpx.ASGITransport(app=make_app(db))

            async def resolve_user(self, request, username):
                return USERS.get(username)

            with patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))), patch.object(
                AuthHandler,
                "_resolve_user",
                resolve_user,
            ):
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    return await scenario(World(db, client, runner, minio))
        finally:
            await db.engine.dispose()

    return asyncio.run(_inner())
