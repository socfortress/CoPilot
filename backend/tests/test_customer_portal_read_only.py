"""Read-only portal users (#1312): a customer_user who may only read one of their customers' data.

Real routers, real in-memory database, real request parsing; only token decoding, user lookup,
the SLA recorder (its own sessions), notifications and the audit writer are replaced.

Pinned here:
- every write a portal user may make on a customer's data is refused (403 ``READ_ONLY``) for a
  user who may only read that customer, and nothing is written; the same user still writes on a
  customer they are not read-only on; their own things (language, preferences) stay theirs;
- the split of ``ALLOWED_CUSTOMER_USER_WRITES`` into refused and kept writes is exhaustive, and
  every refused route carries the check;
- the SOC sets the flag per customer (admin only, audited only when it changes, never together
  with the customer admin role, only for a portal user of that customer); the Security list shows it;
- a customer admin sets it for the users they manage, and can invite a user read-only;
- ``/customer_portal/me`` says it per customer; the customer's audit log names the change.

Run with: cd backend && python -m pytest tests/test_customer_portal_read_only.py
"""

import asyncio
import inspect
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402
from sqlmodel import select  # noqa: E402

from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.services import read_only  # noqa: E402
from app.auth.services.read_only import READ_ONLY  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.customer_portal.services.audit import label_for  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import CustomerPortalSocRequest  # noqa: E402
from app.db.universal_models import CustomerPortalSocRequestSettings  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import Case  # noqa: E402
from app.incidents.models import CaseAlertLink  # noqa: E402
from app.incidents.models import CaseComment  # noqa: E402
from app.incidents.models import Comment  # noqa: E402
from app.soc_management.services.lifecycle import SlaLifecycleRecorder  # noqa: E402
from tests.soc_management_support import _tables  # noqa: E402
from tests.soc_management_support import add_alert  # noqa: E402
from tests.soc_management_support import add_case  # noqa: E402
from tests.test_customer_user_write_allowlist import (  # noqa: E402
    ALLOWED_CUSTOMER_USER_WRITES,
)

# id, username, role. "reader" may only read ACME and works on GLOBEX; "writer" works on ACME;
# "boss" administers ACME's portal users; "admin" and "ana" are the SOC.
PEOPLE = [(1, "admin", 1), (2, "ana", 2), (10, "reader", 4), (11, "writer", 4), (12, "boss", 4), (13, "solo", 4)]
SCOPES = {name: ["customer_user"] if role == 4 else (["admin"] if role == 1 else ["analyst"]) for _, name, role in PEOPLE}
TABLES = {"customer_portal_soc_request", "customer_portal_soc_request_settings", "user_totp", "customer_portal_language_settings"}
DB = "/incidents/db_operations"
NEW_CASE = {"case_name": "x", "case_description": "x", "case_creation_time": "2026-10-27T08:00:00", "case_status": "OPEN"}

# Every write the portal makes on a customer's data, refused for a read-only user (#1312).
REFUSED = frozenset(
    {
        ("PUT", "/api/incidents/db_operations/alert/status"),
        ("PUT", "/api/incidents/db_operations/alerts/status"),
        ("POST", "/api/incidents/db_operations/alert/comment"),
        ("PUT", "/api/incidents/db_operations/alert/comment"),
        ("DELETE", "/api/incidents/db_operations/alert/comment/{comment_id}"),
        ("POST", "/api/incidents/db_operations/case/create"),
        ("POST", "/api/incidents/db_operations/case/from-alert"),
        ("PUT", "/api/incidents/db_operations/case/status"),
        ("PUT", "/api/incidents/db_operations/case/assigned-to"),
        ("POST", "/api/incidents/db_operations/case/alert-link"),
        ("POST", "/api/incidents/db_operations/case/alert-unlink"),
        ("POST", "/api/incidents/db_operations/case/comment"),
        ("PUT", "/api/incidents/db_operations/case/comment"),
        ("DELETE", "/api/incidents/db_operations/case/comment/{comment_id}"),
        ("POST", "/api/incidents/db_operations/case/data-store/upload"),
        ("POST", "/api/incidents/customer_reports/generate/background"),
        ("DELETE", "/api/incidents/customer_reports/{report_id}"),
        ("POST", "/api/customer_portal/ai_reports/alert/{alert_id}/investigate"),
        ("POST", "/api/customer_portal/soc_requests/alert/{alert_id}"),
        ("POST", "/api/customer_portal/soc_requests/case/{case_id}"),
        ("POST", "/api/agents/{agent_id}/critical"),
        ("POST", "/api/agents/{agent_id}/noncritical"),
    },
)

# Kept for a read-only user: their own account, preferences and saved searches, a customer
# admin's management of users (an admin is never read-only), and reads that take a body.
KEPT = ALLOWED_CUSTOMER_USER_WRITES - REFUSED

# Where a refused route's check lives when it is not in the route's own source.
CHECKED_IN = {
    (
        "POST",
        "/api/customer_portal/ai_reports/alert/{alert_id}/investigate",
    ): "app.customer_portal.services.ai_requests.request_alert_analysis",
    ("POST", "/api/customer_portal/soc_requests/alert/{alert_id}"): "app.customer_portal.services.soc_requests._reserve",
    ("POST", "/api/customer_portal/soc_requests/case/{case_id}"): "app.customer_portal.services.soc_requests._reserve",
}
MARKERS = ("ensure_may_write", "write=True", "is_read_only_for")


class Db:
    def __init__(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def create(self) -> "Db":
        tables = _tables() + [SQLModel.metadata.tables[name] for name in TABLES]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
        return self

    def session(self) -> AsyncSession:
        return self.factory()


def _app(db: Db) -> FastAPI:
    from app.routers import auth
    from app.routers import customer_portal
    from app.routers import incidents

    app = FastAPI()
    app.include_router(customer_portal.router)
    app.include_router(incidents.router)
    app.include_router(auth.router)

    async def _session():
        async with db.session() as session:
            yield session

    app.dependency_overrides[get_db] = _session
    return app


async def _seed(db: Db) -> dict:
    async with db.session() as s:
        s.add_all(User(id=uid, username=name, password="x" * 8, email=f"{name}@example.com", role_id=role) for uid, name, role in PEOPLE)
        s.add_all([Customers(customer_code="ACME", customer_name="Acme"), Customers(customer_code="GLOBEX", customer_name="Globex")])
        await s.commit()
        s.add_all(
            [
                UserCustomerAccess(user_id=2, customer_code="ACME"),
                UserCustomerAccess(user_id=10, customer_code="ACME", read_only=True),
                UserCustomerAccess(user_id=10, customer_code="GLOBEX"),
                UserCustomerAccess(user_id=11, customer_code="ACME"),
                UserCustomerAccess(user_id=12, customer_code="ACME", is_customer_admin=True),
                UserCustomerAccess(user_id=13, customer_code="ACME"),
            ],
        )
        s.add_all(CustomerPortalSocRequestSettings(customer_code=code, enabled=True) for code in ("ACME", "GLOBEX"))
        await s.commit()
        alert = await add_alert(s, name="Acme alert")
        other = await add_alert(s, name="Acme other alert")
        case = await add_case(s, name="Acme case")
        s.add(CaseAlertLink(case_id=case.id, alert_id=alert.id))
        globex_alert = await add_alert(s, name="Globex alert", customer="GLOBEX")
        globex_case = await add_case(s, name="Globex case", customer="GLOBEX")
        await s.commit()
        comment = Comment(alert_id=alert.id, comment="mine", user_name="reader")
        case_comment = CaseComment(case_id=case.id, comment="mine", user_name="reader")
        s.add_all([comment, case_comment])
        await s.commit()
        return {
            "alert": alert.id,
            "other": other.id,
            "case": case.id,
            "comment": comment.id,
            "case_comment": case_comment.id,
            "globex_alert": globex_alert.id,
            "globex_case": globex_case.id,
        }


class Recorded(SimpleNamespace):
    pass


def call(scenario):
    async def _inner():
        db = await Db().create()
        ids = await _seed(db)
        rec = Recorded(audit=AsyncMock(), db=db, ids=ids)

        async def resolve_user(self, request, username):
            async with db.session() as s:
                return (await s.execute(select(User).where(User.username == username))).scalars().first()

        recorder = {
            name: AsyncMock()
            for name in ("alert_opened", "case_opened", "alert_action", "alerts_action", "case_action", "case_links_changed")
        }
        audit_writers = [
            "app.auth.routes.security_admin.record_audit_event",
            "app.customer_portal.services.tenant_users.record_audit_event",
            "app.customer_portal.services.soc_requests.record_audit_event",
            "app.customer_portal.services.ai_requests.record_audit_event",
            "app.incidents.routes.db_operations.record_audit_event",
            "app.incidents.routes.db_operations.record_incident_event",
            "app.incidents.routes.db_operations.record_status_changes",
        ]
        patches = [patch(target, rec.audit) for target in audit_writers]
        patches += [
            patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))),
            patch.object(AuthHandler, "_resolve_user", resolve_user),
            patch.multiple(SlaLifecycleRecorder, **recorder),
            patch("app.incidents.routes.db_operations.notify_status_change", lambda *a, **k: None),
            patch("app.customer_portal.services.soc_requests.emit", lambda event: None),
        ]
        for p in patches:
            p.start()
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_app(db)), base_url="http://test") as client:
                return await scenario(client, rec)
        finally:
            for p in reversed(patches):
                p.stop()

    return asyncio.run(_inner())


def as_user(name):
    return {"Authorization": f"Bearer {name}"}


async def rows(db: Db, model, *where):
    async with db.session() as s:
        return (await s.execute(select(model).where(*where))).scalars().all()


def refused(response) -> bool:
    return response.status_code == 403 and response.json().get("detail") == READ_ONLY


# ── the split of the portal's writes ──────────────────────────────────────────


def test_every_portal_write_is_either_refused_to_a_reader_or_their_own():
    assert REFUSED <= ALLOWED_CUSTOMER_USER_WRITES, sorted(REFUSED - ALLOWED_CUSTOMER_USER_WRITES)
    own = {path for _, path in KEPT}
    # What a reader keeps is theirs: account, preferences, searches, user management, and reads
    # (a Threat Intel lookup of an IOC changes nothing of the customer's, #1318).
    for path in own:
        assert any(
            part in path
            for part in (
                "/auth/",
                "/languages/me",
                "/notifications/",
                "/event_search/",
                "/customer_portal/users",
                "/panel-data",
                "/copilot_searches/",
                "/ioc_enrichment/",
            )
        ), path


def test_every_refused_route_carries_the_read_only_check():
    import importlib

    from fastapi.routing import APIRoute

    import copilot

    routes = {(method, route.path): route for route in copilot.app.routes if isinstance(route, APIRoute) for method in route.methods}
    for key in REFUSED:
        assert key in routes, key
        target = CHECKED_IN.get(key)
        if target:
            module, name = target.rsplit(".", 1)
            source = inspect.getsource(getattr(importlib.import_module(module), name))
        else:
            source = inspect.getsource(routes[key].endpoint)
        assert any(marker in source for marker in MARKERS), key


# ── the check itself ──────────────────────────────────────────────────────────


def test_only_a_portal_user_can_be_read_only():
    async def scenario(client, rec):
        async with rec.db.session() as s:
            soc = await s.get(User, 2)
            reader = await s.get(User, 10)
            return (
                await read_only.read_only_customer_codes(soc, s),
                await read_only.read_only_customer_codes(reader, s),
                await read_only.is_read_only_for(reader, None, s),
            )

    soc, reader, none = call(scenario)
    assert soc == frozenset() and reader == frozenset({"ACME"}) and none is False


def test_the_read_only_customers_are_read_once_per_request():
    async def scenario(client, rec):
        async with rec.db.session() as s:
            reader = await s.get(User, 10)
            await read_only.read_only_customer_codes(reader, s)
            with patch.object(s, "execute", AsyncMock(side_effect=AssertionError("read twice"))):
                again = await read_only.read_only_customer_codes(reader, s)
            read_only.forget_read_only(s, 10)
            return again, 10 in s.info.get("read_only_customer_codes", {})

    again, still_cached = call(scenario)
    assert again == frozenset({"ACME"}) and still_cached is False


def test_ensure_may_write_refuses_with_a_fixed_text():
    async def scenario(client, rec):
        async with rec.db.session() as s:
            reader = await s.get(User, 10)
            await read_only.ensure_may_write(reader, "GLOBEX", s)
            with pytest.raises(HTTPException) as raised:
                await read_only.ensure_may_write(reader, "ACME", s)
            return raised.value

    error = call(scenario)
    assert error.status_code == 403 and error.detail == READ_ONLY


# ── alerts ────────────────────────────────────────────────────────────────────


def test_a_reader_cannot_change_an_alerts_status_but_can_on_another_customer():
    async def scenario(client, rec):
        ids = rec.ids
        mine = await client.put(f"{DB}/alert/status", json={"alert_id": ids["alert"], "status": "CLOSED"}, headers=as_user("reader"))
        bulk = await client.put(
            f"{DB}/alerts/status",
            json={"alert_ids": [ids["alert"], ids["globex_alert"]], "status": "IN_PROGRESS"},
            headers=as_user("reader"),
        )
        writer = await client.put(f"{DB}/alert/status", json={"alert_id": ids["other"], "status": "CLOSED"}, headers=as_user("writer"))
        stored = {a.id: a.status for a in await rows(rec.db, Alert)}
        return mine, bulk, writer, stored, ids

    mine, bulk, writer, stored, ids = call(scenario)
    assert refused(mine)
    assert bulk.status_code == 200
    assert bulk.json()["not_updated_alert_ids"] == [ids["alert"]] and bulk.json()["updated_alert_ids"] == [ids["globex_alert"]]
    assert writer.status_code == 200
    assert stored[ids["alert"]] == "OPEN" and stored[ids["globex_alert"]] == "IN_PROGRESS" and stored[ids["other"]] == "CLOSED"


def test_a_reader_cannot_comment_edit_or_delete_on_an_alert():
    async def scenario(client, rec):
        ids = rec.ids
        create = await client.post(
            f"{DB}/alert/comment",
            json={"alert_id": ids["alert"], "comment": "hi", "user_name": "x"},
            headers=as_user("reader"),
        )
        edit = await client.put(
            f"{DB}/alert/comment",
            json={
                "alert_id": ids["alert"],
                "comment_id": ids["comment"],
                "comment": "edited",
                "user_name": "x",
                "created_at": "2026-10-27T08:00:00",
            },
            headers=as_user("reader"),
        )
        delete = await client.delete(f"{DB}/alert/comment/{ids['comment']}", headers=as_user("reader"))
        elsewhere = await client.post(
            f"{DB}/alert/comment",
            json={"alert_id": ids["globex_alert"], "comment": "hi", "user_name": "x"},
            headers=as_user("reader"),
        )
        comments = await rows(rec.db, Comment)
        return create, edit, delete, elsewhere, comments

    create, edit, delete, elsewhere, comments = call(scenario)
    assert refused(create) and refused(edit) and refused(delete)
    assert elsewhere.status_code == 200
    by_alert = sorted((c.comment, c.user_name) for c in comments)
    assert by_alert == [("hi", "reader"), ("mine", "reader")]


# ── cases ─────────────────────────────────────────────────────────────────────


def test_a_reader_cannot_open_link_move_assign_or_comment_on_a_case():
    async def scenario(client, rec):
        ids = rec.ids
        h = as_user("reader")
        results = {
            "create": await client.post(f"{DB}/case/create", json={**NEW_CASE, "customer_code": "ACME"}, headers=h),
            "from_alert": await client.post(f"{DB}/case/from-alert", json={"alert_id": ids["other"]}, headers=h),
            "status": await client.put(f"{DB}/case/status", json={"case_id": ids["case"], "status": "CLOSED"}, headers=h),
            "assign": await client.put(f"{DB}/case/assigned-to", json={"case_id": ids["case"], "assigned_to": "reader"}, headers=h),
            "link": await client.post(f"{DB}/case/alert-link", json={"case_id": ids["case"], "alert_id": ids["other"]}, headers=h),
            "unlink": await client.post(f"{DB}/case/alert-unlink", json={"case_id": ids["case"], "alert_id": ids["alert"]}, headers=h),
            "comment": await client.post(f"{DB}/case/comment", json={"case_id": ids["case"], "comment": "hi", "user_name": "x"}, headers=h),
            "edit": await client.put(
                f"{DB}/case/comment",
                json={
                    "case_id": ids["case"],
                    "comment_id": ids["case_comment"],
                    "comment": "e",
                    "user_name": "x",
                    "created_at": "2026-10-27T08:00:00",
                },
                headers=h,
            ),
            "delete": await client.delete(f"{DB}/case/comment/{ids['case_comment']}", headers=h),
            "upload": await client.post(
                f"{DB}/case/data-store/upload",
                params={"case_id": ids["case"]},
                files={"file": ("note.txt", b"hello", "text/plain")},
                headers=h,
            ),
        }
        cases = await rows(rec.db, Case)
        links = await rows(rec.db, CaseAlertLink)
        return results, cases, links

    results, cases, links = call(scenario)
    for name, response in results.items():
        assert refused(response), (name, response.status_code, response.text)
    assert sorted(c.case_name for c in cases) == ["Acme case", "Globex case"]
    assert next(c for c in cases if c.case_name == "Acme case").case_status == "OPEN"
    assert len(links) == 1


def test_a_reader_still_opens_a_case_for_a_customer_they_work_on():
    async def scenario(client, rec):
        return await client.post(
            f"{DB}/case/create",
            json={**NEW_CASE, "case_name": "Globex question", "customer_code": "GLOBEX"},
            headers=as_user("reader"),
        )

    response = call(scenario)
    assert response.status_code == 200 and response.json()["case"]["customer_code"] == "GLOBEX"


# ── portal requests ───────────────────────────────────────────────────────────


def test_a_reader_cannot_ask_the_soc_or_the_ai_analyst_and_the_refusal_is_audited():
    async def scenario(client, rec):
        ids = rec.ids
        h = as_user("reader")
        on_alert = await client.post(f"/customer_portal/soc_requests/alert/{ids['alert']}", json={"question": "Is this ours?"}, headers=h)
        on_case = await client.post(f"/customer_portal/soc_requests/case/{ids['case']}", json={"question": "Is this ours?"}, headers=h)
        ai = await client.post(f"/customer_portal/ai_reports/alert/{ids['alert']}/investigate", headers=h)
        stored = await rows(rec.db, CustomerPortalSocRequest)
        return on_alert, on_case, ai, stored, rec.audit.await_args_list

    on_alert, on_case, ai, stored, audits = call(scenario)
    assert refused(on_alert) and refused(on_case) and refused(ai)
    assert stored == []
    failures = [c.kwargs for c in audits if c.kwargs.get("details") == READ_ONLY]
    assert len(failures) == 3
    assert {f["action"].value for f in failures} == {"soc_request.create", "ai_analysis.request"}


# ── what a reader keeps ───────────────────────────────────────────────────────


def test_a_reader_keeps_their_own_preferences():
    async def scenario(client, rec):
        return await client.put(
            "/customer_portal/notifications/preferences",
            json={"preferences": [{"event": "case_closed", "in_app": True}]},
            headers=as_user("reader"),
        )

    response = call(scenario)
    assert response.status_code != 403, response.text


# ── the SOC sets it ───────────────────────────────────────────────────────────


SOC = "/auth/security/customers"


def test_an_admin_makes_a_portal_user_read_only_on_one_customer_audited_once():
    async def scenario(client, rec):
        on = await client.put(f"{SOC}/ACME/users/11/read-only", json={"read_only": True}, headers=as_user("admin"))
        again = await client.put(f"{SOC}/ACME/users/11/read-only", json={"read_only": True}, headers=as_user("admin"))
        listed = (await client.get(f"{SOC}/ACME/users", headers=as_user("admin"))).json()["users"]
        refused_now = await client.put(
            f"{DB}/alert/status",
            json={"alert_id": rec.ids["other"], "status": "CLOSED"},
            headers=as_user("writer"),
        )
        off = await client.put(f"{SOC}/ACME/users/11/read-only", json={"read_only": False}, headers=as_user("admin"))
        allowed_again = await client.put(
            f"{DB}/alert/status",
            json={"alert_id": rec.ids["other"], "status": "CLOSED"},
            headers=as_user("writer"),
        )
        audits = [
            c.kwargs
            for c in rec.audit.await_args_list
            if c.kwargs.get("action") and c.kwargs["action"].value == "customer_user.read_only_update"
        ]
        return on, again, listed, refused_now, off, allowed_again, audits

    on, again, listed, refused_now, off, allowed_again, audits = call(scenario)
    assert on.status_code == 200 and again.status_code == 200 and off.status_code == 200
    assert on.json()["message"] == "writer can now only read this customer's data."
    assert off.json()["message"] == "writer can change this customer's data again."
    assert {u["username"]: u["read_only"] for u in listed} == {"ana": False, "reader": True, "writer": True, "boss": False, "solo": False}
    assert refused(refused_now) and allowed_again.status_code == 200
    assert [(a["old_value"], a["new_value"], a["customer_code"], a["entity_id"]) for a in audits] == [
        ({"read_only": False}, {"read_only": True}, "ACME", "writer"),
        ({"read_only": True}, {"read_only": False}, "ACME", "writer"),
    ]


def test_an_admin_cant_be_read_only_nor_a_read_only_user_an_admin():
    async def scenario(client, rec):
        admin_read_only = await client.put(f"{SOC}/ACME/users/12/read-only", json={"read_only": True}, headers=as_user("admin"))
        reader_admin = await client.put(f"{SOC}/ACME/users/10/customer-admin", json={"is_customer_admin": True}, headers=as_user("admin"))
        return admin_read_only, reader_admin

    admin_read_only, reader_admin = call(scenario)
    assert admin_read_only.status_code == 409 and reader_admin.status_code == 409
    assert "can't be read-only" in admin_read_only.json()["detail"]


def test_only_an_admin_sets_it_and_only_for_a_portal_user_of_that_customer():
    async def scenario(client, rec):
        by_analyst = await client.put(f"{SOC}/ACME/users/11/read-only", json={"read_only": True}, headers=as_user("ana"))
        by_portal = await client.put(f"{SOC}/ACME/users/11/read-only", json={"read_only": True}, headers=as_user("boss"))
        soc_user = await client.put(f"{SOC}/ACME/users/2/read-only", json={"read_only": True}, headers=as_user("admin"))
        other_customer = await client.put(f"{SOC}/GLOBEX/users/11/read-only", json={"read_only": True}, headers=as_user("admin"))
        unknown = await client.put(f"{SOC}/ACME/users/999/read-only", json={"read_only": True}, headers=as_user("admin"))
        return by_analyst, by_portal, soc_user, other_customer, unknown

    by_analyst, by_portal, soc_user, other_customer, unknown = call(scenario)
    assert by_analyst.status_code == 403 and by_portal.status_code == 403
    assert soc_user.status_code == 400 and other_customer.status_code == 400 and unknown.status_code == 404


# ── a customer admin sets it ──────────────────────────────────────────────────


def test_a_customer_admin_makes_a_user_they_manage_read_only():
    async def scenario(client, rec):
        made = await client.put("/customer_portal/users/13/read-only", json={"read_only": True}, headers=as_user("boss"))
        listed = (await client.get("/customer_portal/users", headers=as_user("boss"))).json()["users"]
        not_theirs = await client.put("/customer_portal/users/10/read-only", json={"read_only": True}, headers=as_user("boss"))
        themselves = await client.put("/customer_portal/users/12/read-only", json={"read_only": True}, headers=as_user("boss"))
        by_plain_user = await client.put("/customer_portal/users/13/read-only", json={"read_only": False}, headers=as_user("writer"))
        audits = [
            c.kwargs
            for c in rec.audit.await_args_list
            if c.kwargs.get("action") and c.kwargs["action"].value == "customer_user.read_only_update"
        ]
        return made, listed, not_theirs, themselves, by_plain_user, audits

    made, listed, not_theirs, themselves, by_plain_user, audits = call(scenario)
    assert made.status_code == 200 and made.json()["user"]["read_only"] is True
    assert made.json()["user"]["customers"] == [
        {"customer_code": "ACME", "customer_name": "Acme", "is_customer_admin": False, "read_only": True},
    ]
    assert {u["username"]: u["read_only"] for u in listed}["solo"] is True
    # The reader also belongs to GLOBEX, which the boss does not administer: the SOC manages them.
    assert not_theirs.status_code == 403 and themselves.status_code == 403 and by_plain_user.status_code == 403
    assert [(a["new_value"], a["customer_code"], a["entity_id"], a["actor_username"]) for a in audits] == [
        ({"read_only": True}, "ACME", "solo", "boss"),
    ]


def test_a_customer_admin_invites_a_user_read_only():
    async def scenario(client, rec):
        with patch("app.customer_portal.services.tenant_users.password_change.record_change_required", AsyncMock()):
            invited = await client.post(
                "/customer_portal/users",
                json={"username": "auditor", "email": "auditor@example.com", "customer_codes": ["ACME"], "read_only": True},
                headers=as_user("boss"),
            )
        access = await rows(rec.db, UserCustomerAccess, UserCustomerAccess.customer_code == "ACME")
        return invited, access

    invited, access = call(scenario)
    assert invited.status_code == 201 and invited.json()["user"]["read_only"] is True
    assert any(row.read_only for row in access if row.user_id not in (2, 10, 11, 12, 13))


# ── the portal learns it ──────────────────────────────────────────────────────


def test_me_says_which_customers_are_read_only():
    async def scenario(client, rec):
        return (await client.get("/customer_portal/me", headers=as_user("reader"))).json()

    me = call(scenario)
    assert {c["customer_code"]: c["read_only"] for c in me["customers"]} == {"ACME": True, "GLOBEX": False}


def test_the_customers_audit_log_names_the_change():
    row = SimpleNamespace(action="customer_user.read_only_update", new_value={"read_only": True}, details=None)
    assert label_for(row) == "Made read-only"
    assert label_for(SimpleNamespace(action=row.action, new_value={"read_only": False}, details=None)) == "Can change data again"
    assert label_for(SimpleNamespace(action=row.action, new_value=None, details=None)) == "Read-only access changed"


def test_the_portal_never_offers_an_ai_analysis_to_a_reader():
    from app.customer_portal.services import ai_reports

    settings = SimpleNamespace(enabled=True, allow_customer_requests=True, daily_request_limit=None)

    async def scenario(client, rec):
        async with rec.db.session() as s:
            reader = await s.get(User, 10)
            with patch.object(ai_reports, "get_ai_report_settings", AsyncMock(return_value=settings)), patch.object(
                ai_reports,
                "get_alert_analysis",
                AsyncMock(return_value=(None, None, [])),
            ):
                on_acme = await ai_reports.get_portal_alert_analysis(rec.ids["alert"], reader, s)
                on_globex = await ai_reports.get_portal_alert_analysis(rec.ids["globex_alert"], reader, s)
        return on_acme, on_globex

    on_acme, on_globex = call(scenario)
    assert on_acme.can_request is False and on_globex.can_request is True
