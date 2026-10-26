"""The roles of an alert's or a case's comment authors, for their role badges (#1305).

Real routers, a real in-memory database; only token decoding and user lookup are replaced.

Pinned here:
- each author of the alert's or case's comments is named with their role; a name that is no
  user (an ingest pipeline's signature) is left out; an alert or case without comments, none;
- the checks are those of reading the alert or case: another customer's is a 403, an unknown
  one a 404, and a portal user's token is refused (the route is the SOC's);
- only the authors of that alert's or case's comments are ever named.

Run with: cd backend && python -m pytest tests/test_comment_authors.py
"""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.incidents.models import CaseComment  # noqa: E402
from app.incidents.models import Comment  # noqa: E402
from app.incidents.services.comment_authors import roles_by_username  # noqa: E402
from tests.soc_management_support import _tables  # noqa: E402
from tests.soc_management_support import add_alert  # noqa: E402
from tests.soc_management_support import add_case  # noqa: E402

PEOPLE = [(1, "admin", 1), (2, "ana", 2), (3, "gina", 2), (4, "ron", 5), (10, "jane", 4), (11, "other", 4)]
USERS = {name: SimpleNamespace(id=uid, username=name, role_id=role) for uid, name, role in PEOPLE}
SCOPES = {
    "admin": ["admin"],
    "ana": ["analyst"],
    "gina": ["analyst"],
    "ron": ["responder", "analyst"],
    "jane": ["customer_user"],
    "other": ["customer_user"],
}
BASE = "/incidents/db_operations"


def _app(factory) -> FastAPI:
    from app.routers import incidents

    app = FastAPI()
    app.include_router(incidents.router)

    async def _session():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _session
    return app


async def _seed(factory) -> dict:
    async with factory() as s:
        s.add_all(User(id=uid, username=name, password="x" * 8, email=f"{name}@example.com", role_id=role) for uid, name, role in PEOPLE)
        s.add_all([Customers(customer_code="ACME", customer_name="Acme"), Customers(customer_code="GLOBEX", customer_name="Globex")])
        await s.commit()
        s.add_all(
            [
                UserCustomerAccess(user_id=2, customer_code="ACME"),
                UserCustomerAccess(user_id=4, customer_code="ACME"),
                UserCustomerAccess(user_id=3, customer_code="GLOBEX"),
                UserCustomerAccess(user_id=10, customer_code="ACME"),
            ],
        )
        alert = await add_alert(s, name="Odd login")
        quiet = await add_alert(s, name="Quiet alert")
        case = await add_case(s, name="Investigation")
        await s.commit()
        s.add_all(
            [
                Comment(alert_id=alert.id, user_name="jane", comment="Is this ours?"),
                Comment(alert_id=alert.id, user_name="ana", comment="Looking"),
                Comment(alert_id=alert.id, user_name="ana", comment="Still looking"),
                # An ingest pipeline's signature: no such user.
                Comment(alert_id=alert.id, user_name="velociraptor-ingest", comment="payload"),
                CaseComment(case_id=case.id, user_name="ron", comment="Quarantined"),
                CaseComment(case_id=case.id, user_name="admin", comment="Approved"),
                # The other portal user commented on a quiet alert only: never named elsewhere.
                Comment(alert_id=quiet.id, user_name="other", comment="hello"),
            ],
        )
        await s.commit()
        return {"alert": alert.id, "quiet": quiet.id, "case": case.id}


def call(scenario):
    async def _inner():
        engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        async with engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=_tables()))
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        ids = await _seed(factory)

        async def resolve_user(self, request, username):
            return USERS.get(username)

        with patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))), patch.object(
            AuthHandler,
            "_resolve_user",
            resolve_user,
        ):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_app(factory)), base_url="http://test") as client:
                return await scenario(client, ids, factory)

    return asyncio.run(_inner())


def as_user(name):
    return {"Authorization": f"Bearer {name}"}


def test_each_author_of_an_alerts_comments_is_named_with_their_role():
    async def scenario(client, ids, _):
        return await client.get(f"{BASE}/alert/{ids['alert']}/comment-authors", headers=as_user("ana"))

    res = call(scenario)
    assert res.status_code == 200
    # The pipeline's signature is no user, so it has no role; "other" never commented here.
    assert res.json()["authors"] == {"jane": "customer_user", "ana": "analyst"}


def test_each_author_of_a_cases_comments_is_named_with_their_role():
    async def scenario(client, ids, _):
        return await client.get(f"{BASE}/case/{ids['case']}/comment-authors", headers=as_user("admin"))

    res = call(scenario)
    assert res.status_code == 200
    assert res.json()["authors"] == {"ron": "responder", "admin": "admin"}


def test_a_responder_reads_them_like_an_analyst():
    async def scenario(client, ids, _):
        return await client.get(f"{BASE}/case/{ids['case']}/comment-authors", headers=as_user("ron"))

    assert call(scenario).status_code == 200


def test_another_customers_alert_or_case_is_refused_and_an_unknown_one_is_not_found():
    async def scenario(client, ids, _):
        alert = await client.get(f"{BASE}/alert/{ids['alert']}/comment-authors", headers=as_user("gina"))
        case = await client.get(f"{BASE}/case/{ids['case']}/comment-authors", headers=as_user("gina"))
        missing_alert = await client.get(f"{BASE}/alert/999999/comment-authors", headers=as_user("admin"))
        missing_case = await client.get(f"{BASE}/case/999999/comment-authors", headers=as_user("admin"))
        return alert, case, missing_alert, missing_case

    alert, case, missing_alert, missing_case = call(scenario)
    assert alert.status_code == 403 and case.status_code == 403
    assert "authors" not in alert.json() and "authors" not in case.json()
    assert missing_alert.status_code == 404 and missing_case.status_code == 404


def test_a_portal_users_token_is_refused():
    async def scenario(client, ids, _):
        alert = await client.get(f"{BASE}/alert/{ids['alert']}/comment-authors", headers=as_user("jane"))
        case = await client.get(f"{BASE}/case/{ids['case']}/comment-authors", headers=as_user("jane"))
        return alert, case

    alert, case = call(scenario)
    assert (alert.status_code, case.status_code) == (403, 403)


def test_an_alert_without_comments_names_nobody():
    async def scenario(client, ids, factory):
        async with factory() as s:
            empty = await add_alert(s, name="Fresh alert")
            await s.commit()
        return await client.get(f"{BASE}/alert/{empty.id}/comment-authors", headers=as_user("admin"))

    res = call(scenario)
    assert res.status_code == 200 and res.json()["authors"] == {}


def test_roles_by_username_skips_blanks_and_unknown_names():
    async def scenario(client, ids, factory):
        async with factory() as s:
            none = await roles_by_username([], s)
            some = await roles_by_username(["", None, "jane", "jane", "nobody"], s)
        return none, some

    none, some = call(scenario)
    assert none == {}
    assert some == {"jane": "customer_user"}
