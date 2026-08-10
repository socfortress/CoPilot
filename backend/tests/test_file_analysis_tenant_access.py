"""Tenancy and scope guarantees for the file analysis API (#1067).

Hiding rows in a list is not access control. A caller handed a job UUID for
another tenant must be refused at the API, which is why ``get_job`` enforces
after reading the row rather than relying on the list filter (#974 §E).

The scope surface is pinned too: Phase 1 is admin/analyst only. Adding
``customer_user`` to these routes would hand every portal user every tenant's
submissions, because the handlers trust the scope check and do no second one --
the same trap ``app/ai_analyst/routes`` documents.

Unit tests against mocked sessions; no database is touched.
Run with: cd backend && python -m pytest tests/test_file_analysis_tenant_access.py
"""

import ast
import asyncio
import os
import pathlib
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

from fastapi import HTTPException  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.file_analysis.services import analysis as svc  # noqa: E402

ROUTES_PATH = pathlib.Path(__file__).resolve().parent.parent / "app" / "file_analysis" / "routes" / "file_analysis.py"


def _session_returning(job):
    """A session whose single execute() yields ``job`` (or nothing)."""
    session = MagicMock()
    scalars = MagicMock()
    scalars.first.return_value = job
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars
    session.execute = AsyncMock(return_value=execute_result)
    return session


def _job(customer_code: str):
    return SimpleNamespace(id=1, job_uuid="11111111-1111-1111-1111-111111111111", customer_code=customer_code)


# ---------------------------------------------------------------------------
# get_job — the endpoint a guessed UUID would hit
# ---------------------------------------------------------------------------


def test_job_from_another_tenant_is_refused():
    user = SimpleNamespace(id=7, role_id=2, username="scoped-analyst")
    session = _session_returning(_job("CUSTOMER_B"))

    with patch.object(
        svc.customer_access_handler,
        "get_user_accessible_customers",
        AsyncMock(return_value=["CUSTOMER_A"]),
    ):
        with pytest.raises(HTTPException) as excinfo:
            asyncio.run(svc.get_job("11111111-1111-1111-1111-111111111111", user, session))

    assert excinfo.value.status_code == 403


def test_job_from_an_accessible_tenant_is_returned():
    user = SimpleNamespace(id=7, role_id=2, username="scoped-analyst")
    job = _job("CUSTOMER_A")
    session = _session_returning(job)

    with patch.object(
        svc.customer_access_handler,
        "get_user_accessible_customers",
        AsyncMock(return_value=["CUSTOMER_A"]),
    ):
        result = asyncio.run(svc.get_job(job.job_uuid, user, session))

    assert result is job


def test_missing_job_is_404_not_403():
    """A 403 on a nonexistent id would leak which UUIDs exist."""
    user = SimpleNamespace(id=7, role_id=2, username="scoped-analyst")
    session = _session_returning(None)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(svc.get_job("no-such-uuid", user, session))

    assert excinfo.value.status_code == 404


def test_admin_reaches_every_tenant():
    # role_id 1 is admin, which get_user_accessible_customers answers with the
    # wildcard without consulting assignments.
    user = SimpleNamespace(id=1, role_id=1, username="admin")
    job = _job("CUSTOMER_B")
    session = _session_returning(job)

    with patch.object(
        svc.customer_access_handler,
        "get_user_accessible_customers",
        AsyncMock(return_value=["*"]),
    ):
        assert asyncio.run(svc.get_job(job.job_uuid, user, session)) is job


# ---------------------------------------------------------------------------
# list_jobs — scoping must be delegated, not hand-rolled
# ---------------------------------------------------------------------------


def test_list_jobs_delegates_scoping_to_the_shared_handler():
    """Hand-rolled filtering is how one query ends up missing the check.

    The assertion is that the shared helper is called with the job table's
    customer_code column, so list_jobs inherits every future fix to the access
    rules rather than drifting from them.
    """
    user = SimpleNamespace(id=7, role_id=2, username="scoped-analyst")

    session = MagicMock()
    session.scalar = AsyncMock(return_value=0)
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=execute_result)

    # A real Select, not a MagicMock: list_jobs builds a COUNT over
    # scoped.subquery(), and SQLAlchemy rejects anything that is not a genuine
    # FROM expression.
    scoped_query = select(svc.FileAnalysisJob)

    with patch.object(
        svc.customer_access_handler,
        "filter_query_by_customer_access",
        AsyncMock(return_value=scoped_query),
    ) as filter_mock:
        asyncio.run(svc.list_jobs(user=user, session=session, customer_code="CUSTOMER_A"))

    filter_mock.assert_awaited_once()
    kwargs = filter_mock.await_args.kwargs
    assert kwargs["requested_customers"] == ["CUSTOMER_A"]
    assert kwargs["customer_code_field"] is svc.FileAnalysisJob.customer_code


# ---------------------------------------------------------------------------
# Upload limits
# ---------------------------------------------------------------------------


class _FakeUpload:
    """Minimal UploadFile stand-in that streams a fixed payload in chunks."""

    def __init__(self, payload: bytes, chunk: int = 8):
        self._payload = payload
        self._chunk = chunk
        self._offset = 0

    async def read(self, size: int = -1) -> bytes:
        take = self._chunk if size in (-1, 0) else min(size, self._chunk)
        data = self._payload[self._offset : self._offset + take]
        self._offset += len(data)
        return data


def test_oversized_upload_is_refused_with_413():
    upload = _FakeUpload(b"x" * 1024)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(svc._read_capped(upload, max_size=64))

    assert excinfo.value.status_code == 413


def test_upload_within_the_limit_is_read_whole():
    payload = b"y" * 100
    assert asyncio.run(svc._read_capped(_FakeUpload(payload), max_size=1024)) == payload


def test_unknown_customer_is_rejected_before_anything_is_stored():
    """Regression: the FK rejected the row *after* MinIO already held the object.

    customer_code is a real FK, so an unknown code failed on INSERT with a 500
    and left a blob in the bucket that no row would ever reference or clean up.
    The route's scope dependency cannot catch this -- it answers "may this
    caller reach this tenant", not "does this tenant exist".
    """
    session = MagicMock()
    session.scalar = AsyncMock(return_value=None)  # customer not found

    upload = _FakeUpload(b"content")

    with patch.object(svc, "store_file_in_minio", AsyncMock()) as store_mock:
        with pytest.raises(HTTPException) as excinfo:
            asyncio.run(svc.create_job("NOPE", upload, "tester", session))

    assert excinfo.value.status_code == 404
    store_mock.assert_not_awaited()


# ---------------------------------------------------------------------------
# Scope surface
# ---------------------------------------------------------------------------


def _declared_scopes():
    """Every scope string passed to require_any_scope in the routes module."""
    tree = ast.parse(ROUTES_PATH.read_text(), filename=str(ROUTES_PATH))
    scopes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "require_any_scope":
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    scopes.append(arg.value)
    return scopes


def test_routes_are_admin_and_analyst_only():
    scopes = _declared_scopes()

    assert scopes, "no require_any_scope call found — the routes may be unprotected"
    assert set(scopes) == {"admin", "analyst"}
    assert "customer_user" not in scopes


def test_every_route_declares_a_scope_check():
    """A route added without a scope dependency would be open to any caller."""
    tree = ast.parse(ROUTES_PATH.read_text(), filename=str(ROUTES_PATH))

    route_count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) and not isinstance(node, ast.AsyncFunctionDef):
            continue
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if isinstance(func, ast.Attribute) and func.attr in {"get", "post", "patch", "put", "delete"}:
                route_count += 1
                source = ast.dump(decorator)
                assert "require_any_scope" in source, f"{node.name} has no scope dependency"

    assert route_count >= 5
