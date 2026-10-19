"""File analysis only reaches endpoints the caller may see, in the endpoint's own Velociraptor org.

``/file_analysis/velociraptor/enumerate`` and ``/file_analysis/submit`` took a Velociraptor
``client_id`` (or hostname) from the request and ran a collection on it with no check that the
caller's customers own that endpoint, and always in the root org. ``resolve_endpoint`` now ties
the request to a CoPilot agent, applies the same owned-object rule as the artifact routes, and
hands the collection the agent's stored client id and org.

Uses a real in-memory SQLite ``agents`` table, so the client-id matching query runs for real;
customer access and Velociraptor are patched.

Run with: cd backend && python -m pytest tests/test_file_analysis_endpoint_access.py
"""

import asyncio
import os
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks
from fastapi import HTTPException

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")
os.environ.setdefault("MYSQL_PASSWORD", "test-only-password-not-the-default")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "test-only-password-not-the-default")

from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.file_analysis.routes as routes  # noqa: E402
from app.db.universal_models import Agents  # noqa: E402
from app.file_analysis.schema.analysis import EnumerateRequest  # noqa: E402
from app.file_analysis.schema.analysis import SubmitRequest  # noqa: E402
from app.file_analysis.services import orchestrator  # noqa: E402
from app.file_analysis.services import velociraptor_fetch  # noqa: E402
from app.middleware.customer_access import customer_access_handler  # noqa: E402

ANALYST_A = SimpleNamespace(id=2, username="analyst-a", role_id=2, customers={"cust_a"})
ADMIN = SimpleNamespace(id=1, username="admin", role_id=1, customers={"*"})

A_CLIENT = "C.aaaaaaaaaaaaaaaa"
B_CLIENT = "C.bbbbbbbbbbbbbbbb"
ORPHAN_CLIENT = "C.cccccccccccccccc"


def _agent(agent_id, hostname, velociraptor_id, org, customer):
    return Agents(
        agent_id=agent_id,
        ip_address="10.0.0.1",
        os="Windows 10",
        hostname=hostname,
        label="",
        wazuh_last_seen=datetime(2026, 10, 1),
        velociraptor_id=velociraptor_id,
        wazuh_agent_version="4.9",
        customer_code=customer,
        velociraptor_org=org,
    )


async def _session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: Agents.__table__.create(c))
    session = AsyncSession(engine)
    session.add_all(
        [
            # Customer A's endpoint, stored org-suffixed as the multi-org sync stores it.
            _agent("001", "A-HOST", f"{A_CLIENT}-OAAAA", "OAAAA", "cust_a"),
            _agent("002", "B-HOST", B_CLIENT, "OBBBB", "cust_b"),
            _agent("003", "ORPHAN", ORPHAN_CLIENT, "root", None),
        ],
    )
    await session.commit()
    return session


@pytest.fixture
def env(monkeypatch):
    calls = {"enumerate": [], "jobs": []}

    async def accessible(user, session):
        return set(user.customers)

    async def check(user, customer_code, session):
        return "*" in user.customers or customer_code in user.customers

    async def fake_enumerate(client_id, target_path, org_id="root"):
        calls["enumerate"].append((client_id, target_path, org_id))
        return [{"path": target_path, "name": "x.exe", "size": 1, "sha256": ""}]

    async def fake_dispatch(source, customer_code, tiers):
        return "job-1", True

    monkeypatch.setattr(customer_access_handler, "get_user_accessible_customers", accessible)
    monkeypatch.setattr(customer_access_handler, "check_customer_access", check)
    monkeypatch.setattr(velociraptor_fetch, "enumerate_matches", fake_enumerate)
    monkeypatch.setattr(orchestrator, "create_and_dispatch", fake_dispatch)
    return calls


def _enumerate(user, customer_code, client_id):
    async def run():
        session = await _session()
        body = EnumerateRequest(customer_code=customer_code, client_id=client_id, target_path="C:\\Users\\*\\x.exe")
        return await routes.velociraptor_enumerate(body, current_user=user, session=session)

    return asyncio.run(run())


def _submit(user, customer_code, client_id=None, hostname=None):
    async def run():
        session = await _session()
        background = BackgroundTasks()
        body = SubmitRequest(source="host_path", customer_code=customer_code, client_id=client_id, hostname=hostname, target_path="/tmp/x")
        response = await routes.submit(body, background, current_user=user, session=session)
        return response, background.tasks

    return asyncio.run(run())


def _status(call):
    with pytest.raises(HTTPException) as exc:
        call()
    return exc.value.status_code


# --- enumerate ------------------------------------------------------------------------


def test_analyst_enumerates_their_own_endpoint_in_its_org(env):
    response = _enumerate(ANALYST_A, "cust_a", A_CLIENT)  # the dropdown sends the bare id

    assert response.matches
    assert env["enumerate"] == [(f"{A_CLIENT}-OAAAA", "C:\\Users\\*\\x.exe", "OAAAA")]


def test_analyst_cannot_enumerate_another_customers_endpoint(env):
    # Naming their own customer does not help: the endpoint belongs to customer B.
    assert _status(lambda: _enumerate(ANALYST_A, "cust_a", B_CLIENT)) == 403
    # Naming customer B is refused before the endpoint is looked at.
    assert _status(lambda: _enumerate(ANALYST_A, "cust_b", B_CLIENT)) == 403
    assert env["enumerate"] == []


def test_an_unknown_client_id_is_refused(env):
    assert _status(lambda: _enumerate(ANALYST_A, "cust_a", "C.dddddddddddddddd")) == 404
    assert _status(lambda: _enumerate(ADMIN, "cust_a", "C.dddddddddddddddd")) == 404
    assert env["enumerate"] == []


def test_a_malformed_client_id_is_refused(env):
    assert _status(lambda: _enumerate(ADMIN, "cust_a", "C.aaaa%")) == 400
    assert _status(lambda: _enumerate(ADMIN, "cust_a", "C.1', artifacts=[]) FROM scope() --")) == 400
    assert env["enumerate"] == []


def test_an_unassigned_endpoint_needs_a_deployment_wide_caller(env):
    assert _status(lambda: _enumerate(ANALYST_A, "cust_a", ORPHAN_CLIENT)) == 403
    assert _enumerate(ADMIN, "cust_a", ORPHAN_CLIENT).matches
    assert env["enumerate"] == [(ORPHAN_CLIENT, "C:\\Users\\*\\x.exe", "root")]


def test_an_admin_cannot_file_one_customers_endpoint_under_another(env):
    assert _status(lambda: _enumerate(ADMIN, "cust_a", B_CLIENT)) == 403


# --- submit ---------------------------------------------------------------------------


def test_submit_resolves_the_endpoint_and_passes_its_org(env):
    response, tasks = _submit(ANALYST_A, "cust_a", client_id=A_CLIENT)

    assert response.job_id == "job-1"
    refs = tasks[0].kwargs["refs"]
    assert refs == {"client_id": f"{A_CLIENT}-OAAAA", "org_id": "OAAAA", "target_path": "/tmp/x", "hostname": "A-HOST"}


def test_submit_by_hostname_is_checked_too(env):
    _, tasks = _submit(ANALYST_A, "cust_a", hostname="A-HOST")
    assert tasks[0].kwargs["refs"]["org_id"] == "OAAAA"

    assert _status(lambda: _submit(ANALYST_A, "cust_a", hostname="B-HOST")) == 403
    assert _status(lambda: _submit(ANALYST_A, "cust_a", hostname="NO-SUCH-HOST")) == 404


def test_submit_refuses_another_customers_client_id(env):
    assert _status(lambda: _submit(ANALYST_A, "cust_a", client_id=B_CLIENT)) == 403
    assert _status(lambda: _submit(ANALYST_A, "cust_a", client_id="C.dddddddddddddddd")) == 404


def test_the_orchestrator_collects_in_the_resolved_org(monkeypatch):
    seen = {}

    async def fake_collect(client_id, target_path, customer_code, org_id="root"):
        seen.update(client_id=client_id, org_id=org_id)
        return None

    monkeypatch.setattr(velociraptor_fetch, "collect_and_fetch", fake_collect)
    job = SimpleNamespace(source="host_path", customer_code="cust_a")
    refs = {"client_id": f"{A_CLIENT}-OAAAA", "org_id": "OAAAA", "target_path": "/tmp/x", "hostname": "A-HOST"}

    asyncio.run(orchestrator._resolve_sample(job, refs))

    assert seen == {"client_id": f"{A_CLIENT}-OAAAA", "org_id": "OAAAA"}


def test_the_orchestrator_refuses_unresolved_refs(monkeypatch):
    async def fake_collect(*args, **kwargs):
        raise AssertionError("must not collect without a resolved agent")

    monkeypatch.setattr(velociraptor_fetch, "collect_and_fetch", fake_collect)
    job = SimpleNamespace(source="host_path", customer_code="cust_a")

    assert asyncio.run(orchestrator._resolve_sample(job, {"hostname": "A-HOST", "target_path": "/tmp/x"})) is None
