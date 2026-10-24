"""The Customer Portal Audit Log page (#1298): a customer admin's view of their tenant's audit trail.

Real routers, real in-memory database, real request parsing; only token decoding and user
lookup are replaced (as in test_customer_portal_activity).

Pinned here:
- a missing switch row reads as off; only an admin flips it (audited once); an analyst reads it;
- only a customer admin reads the log, and only for customers they administer whose switch is on;
- which rows: the customer's own data actions, their portal users' account events, never the SOC's
  internal events, never another customer's rows, never a hidden SOC report's name;
- who: a portal user by name with their address, the SOC as "SOC" with neither, another portal
  user as such, an unknown account as unknown; a customer outside the scope is never named;
- what: labels, targets, status before and after; ``details`` and comment text never leave;
- filters, paging, the CSV (formula guard, truncation, no-store);
- the incident, report and 2FA events the routes now write.

Run with: cd backend && python -m pytest tests/test_customer_portal_audit.py
"""

import asyncio
import csv
import io
import os
from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from app.audit.models.audit import AuditAction  # noqa: E402
from app.audit.models.audit import AuditLog  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.customer_portal.services import audit as service  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import CustomerPortalAuditSettings  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.db.universal_models import IncidentManagementCustomerReport  # noqa: E402

TABLES = (
    "user",
    "role",
    "user_customer_access",
    "customers",
    "customer_portal_audit_settings",
    "incident_management_customer_reports",
    "audit_log",
)

#: id, username, role: SOC admin, SOC analyst; ACME's customer admin, another ACME user (also on
#: GLOBEX), a GLOBEX-only user, a portal user who has since left ACME, and a portal user who
#: administers GLOBEX only.
PEOPLE = [
    (1, "admin", 1),
    (2, "ana", 2),
    (10, "boss", 4),
    (11, "mia", 4),
    (12, "gx", 4),
    (13, "former", 4),
    (14, "gboss", 4),
]
USERS = {name: SimpleNamespace(id=uid, username=name, role_id=role) for uid, name, role in PEOPLE}
SCOPES = {name: ["customer_user"] if role == 4 else (["admin"] if role == 1 else ["analyst"]) for _, name, role in PEOPLE}

T = datetime(2026, 10, 1, 12, 0, 0)
AUDIT = "/customer_portal/audit"


class Db:
    def __init__(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def create(self) -> "Db":
        tables = [SQLModel.metadata.tables[name] for name in TABLES]
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=tables))
        return self

    def session(self) -> AsyncSession:
        return self.factory()

    async def dispose(self) -> None:
        await self.engine.dispose()


def _app(db: Db) -> FastAPI:
    from app.routers import customer_portal

    app = FastAPI()
    app.include_router(customer_portal.router)

    async def _session():
        async with db.session() as session:
            yield session

    app.dependency_overrides[get_db] = _session
    return app


def row(minutes: int, action, *, actor=None, customer=None, entity_type=None, entity_id=None, **fields) -> AuditLog:
    """An audit row ``minutes`` before T, by ``actor`` (a username from PEOPLE) or by nobody."""
    who = USERS.get(actor)
    return AuditLog(
        timestamp=T - timedelta(minutes=minutes),
        action=getattr(action, "value", action),
        actor_user_id=who.id if who else fields.pop("actor_user_id", None),
        actor_username=who.username if who else fields.pop("actor_username", None),
        customer_code=customer,
        entity_type=entity_type,
        entity_id=None if entity_id is None else str(entity_id),
        **fields,
    )


def report(report_id: int, name: str, *, customer="ACME", visible=False, by_role="admin") -> IncidentManagementCustomerReport:
    return IncidentManagementCustomerReport(
        id=report_id,
        report_name=name,
        customer_code=customer,
        object_key=f"{customer}/{name}.pdf",
        file_name=f"{name}.pdf",
        generated_by=1,
        generated_by_role=by_role,
        date_from=T - timedelta(days=30),
        date_to=T,
        visible_to_customer=visible,
        status="completed",
    )


#: The seeded rows, newest first, by label: what ACME's log must show, and what it must not.
SHOWN = "shown"
HIDDEN = "hidden"


def seed_rows():
    return [
        # ACME data actions, by a member, the SOC and a former member.
        (
            SHOWN,
            row(
                1,
                AuditAction.ALERT_STATUS_CHANGE,
                actor="mia",
                customer="ACME",
                entity_type="alert",
                entity_id=7,
                old_value={"status": "OPEN"},
                new_value={"status": "CLOSED"},
                source_ip="203.0.113.7",
            ),
        ),
        (
            SHOWN,
            row(
                2,
                AuditAction.CASE_STATUS_CHANGE,
                actor="ana",
                customer="ACME",
                entity_type="case",
                entity_id=3,
                old_value={"status": "OPEN"},
                new_value={"status": "PENDING_CUSTOMER"},
                source_ip="10.0.0.5",
            ),
        ),
        (
            SHOWN,
            row(
                3,
                AuditAction.CASE_CREATE,
                actor="ana",
                customer="ACME",
                entity_type="case",
                entity_id=3,
                new_value={"case_name": "Ransomware on web-01", "customer_code": "ACME", "alert_id": 7},
            ),
        ),
        (
            SHOWN,
            row(
                4,
                AuditAction.ALERT_COMMENT_CREATE,
                actor="former",
                customer="ACME",
                entity_type="alert",
                entity_id=7,
                new_value={"comment_id": 99},
                details="secret comment text",
            ),
        ),
        (SHOWN, row(5, AuditAction.AI_ANALYSIS_REQUEST, actor="boss", customer="ACME", entity_type="alert", entity_id=7)),
        # Reports: the SOC's visible one shown, its hidden one never; a member's own always.
        (
            SHOWN,
            row(
                6,
                AuditAction.REPORT_GENERATE,
                actor="admin",
                customer="ACME",
                entity_type="report",
                entity_id=1,
                new_value={"report_name": "Monthly review"},
            ),
        ),
        (
            HIDDEN,
            row(
                7,
                AuditAction.REPORT_GENERATE,
                actor="admin",
                customer="ACME",
                entity_type="report",
                entity_id=2,
                new_value={"report_name": "Internal: weak spots"},
            ),
        ),
        (
            HIDDEN,
            row(
                8,
                AuditAction.REPORT_DELETE,
                actor="admin",
                customer="ACME",
                entity_type="report",
                entity_id=4,
                new_value={"report_name": "Deleted SOC draft"},
            ),
        ),
        (
            SHOWN,
            row(
                9,
                AuditAction.REPORT_DOWNLOAD,
                actor="mia",
                customer="ACME",
                entity_type="report",
                entity_id=5,
                new_value={"report_name": "=HYPERLINK(1)"},
            ),
        ),
        # Account events of ACME's users, wherever they were filed.
        (
            SHOWN,
            row(10, AuditAction.AUTH_LOGIN, actor="mia", customer="GLOBEX", entity_type="user", entity_id="mia", source_ip="203.0.113.7"),
        ),
        (
            SHOWN,
            row(
                11,
                AuditAction.AUTH_LOGIN_FAILED,
                customer=None,
                entity_type="user",
                entity_id="boss",
                result="failure",
                actor_username="boss",
                source_ip="198.51.100.9",
            ),
        ),
        (SHOWN, row(12, AuditAction.USER_UPDATE, actor="mia", entity_type="user", entity_id="mia", details="Self-service password change")),
        (SHOWN, row(13, AuditAction.USER_TOTP_ENABLE, actor="mia", entity_type="user", entity_id="mia")),
        (
            SHOWN,
            row(
                14,
                AuditAction.USER_DISABLE,
                actor="admin",
                entity_type="user",
                entity_id="mia",
                details="Portal user disabled by a SOC admin",
            ),
        ),
        (
            SHOWN,
            row(
                15,
                AuditAction.CUSTOMER_ADMIN_UPDATE,
                actor="admin",
                customer="ACME",
                entity_type="user",
                entity_id="boss",
                new_value={"is_customer_admin": True},
            ),
        ),
        (
            SHOWN,
            row(
                16,
                AuditAction.CUSTOMER_USER_INVITE,
                actor="boss",
                customer="ACME",
                entity_type="user",
                entity_id="mia",
                new_value={"username": "mia", "email": "mia@acme.test", "customer_codes": ["ACME"]},
            ),
        ),
        # Never: the SOC's internal events, other customers, SOC users' sign-ins.
        (HIDDEN, row(17, AuditAction.ALERT_VERDICT_SET, actor="ana", customer="ACME", entity_type="alert", entity_id=7)),
        (HIDDEN, row(18, AuditAction.CONNECTOR_UPDATE, actor="admin", customer="ACME", entity_type="connector", entity_id="Wazuh")),
        (
            HIDDEN,
            row(
                19,
                AuditAction.ACTIVITY_SETTINGS_UPDATE,
                actor="admin",
                customer="ACME",
                entity_type="customer_portal_activity_settings",
                entity_id="ACME",
            ),
        ),
        (
            HIDDEN,
            row(
                20,
                AuditAction.ALERT_STATUS_CHANGE,
                actor="gx",
                customer="GLOBEX",
                entity_type="alert",
                entity_id=8,
                old_value={"status": "OPEN"},
                new_value={"status": "CLOSED"},
            ),
        ),
        (HIDDEN, row(21, AuditAction.AUTH_LOGIN, actor="gx", customer="GLOBEX", entity_type="user", entity_id="gx")),
        (HIDDEN, row(22, AuditAction.AUTH_LOGIN, actor="ana", entity_type="user", entity_id="ana")),
        (HIDDEN, row(23, AuditAction.TALON_ACTION_APPROVE, actor="ana", customer="ACME", entity_type="talon_action", entity_id="x")),
    ]


async def _seed(db: Db, *, enabled=("ACME",), extra=()) -> None:
    async with db.session() as session:
        session.add_all(
            User(id=uid, username=name, password="x" * 8, email=f"{name}@example.com", role_id=role) for uid, name, role in PEOPLE
        )
        session.add_all(
            [Customers(customer_code="ACME", customer_name="Acme Corp"), Customers(customer_code="GLOBEX", customer_name="Globex")],
        )
        await session.commit()
        session.add_all(
            [
                UserCustomerAccess(user_id=10, customer_code="ACME", is_customer_admin=True),
                UserCustomerAccess(user_id=11, customer_code="ACME"),
                UserCustomerAccess(user_id=11, customer_code="GLOBEX"),
                UserCustomerAccess(user_id=12, customer_code="GLOBEX"),
                UserCustomerAccess(user_id=14, customer_code="GLOBEX", is_customer_admin=True),
                UserCustomerAccess(user_id=2, customer_code="ACME"),
            ],
        )
        session.add_all(CustomerPortalAuditSettings(customer_code=code, enabled=True) for code in enabled)
        session.add_all(
            [
                report(1, "Monthly review", visible=True),
                report(2, "Internal: weak spots", visible=False),
                report(5, "=HYPERLINK(1)", by_role="customer_user"),
            ],
        )
        session.add_all(entry for _, entry in seed_rows())
        session.add_all(extra)
        await session.commit()


def call(scenario, *, enabled=("ACME",), extra=()):
    async def _inner():
        db = await Db().create()
        try:
            await _seed(db, enabled=enabled, extra=extra)
            transport = httpx.ASGITransport(app=_app(db))

            async def resolve_user(self, request, username):
                return USERS.get(username)

            with patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))), patch.object(
                AuthHandler,
                "_resolve_user",
                resolve_user,
            ):
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    return await scenario(client)
        finally:
            await db.dispose()

    return asyncio.run(_inner())


def as_user(name):
    return {"Authorization": f"Bearer {name}"}


def get(path, user="boss", **params):
    async def scenario(client):
        return await client.get(path, params=params, headers=as_user(user))

    return scenario


def expected_actions():
    return [entry.action for verdict, entry in seed_rows() if verdict == SHOWN]


# ── the switch ────────────────────────────────────────────────────────────────


def test_the_page_is_off_until_an_admin_turns_it_on():
    async def scenario(client):
        refused = await client.get(AUDIT, headers=as_user("boss"))
        available = (await client.get(f"{AUDIT}/availability", headers=as_user("boss"))).json()
        settings = (await client.get(f"{AUDIT}/settings/ACME", headers=as_user("ana"))).json()
        with patch("app.customer_portal.routes.audit.record_audit_event", AsyncMock()) as audit:
            by_analyst = await client.put(f"{AUDIT}/settings/ACME", json={"enabled": True}, headers=as_user("ana"))
            by_portal = await client.put(f"{AUDIT}/settings/ACME", json={"enabled": True}, headers=as_user("boss"))
            turned_on = await client.put(f"{AUDIT}/settings/ACME", json={"enabled": True}, headers=as_user("admin"))
            again = await client.put(f"{AUDIT}/settings/ACME", json={"enabled": True}, headers=as_user("admin"))
        on = await client.get(AUDIT, headers=as_user("boss"))
        now_available = (await client.get(f"{AUDIT}/availability", headers=as_user("boss"))).json()
        return refused, available, settings, by_analyst, by_portal, turned_on, again, audit, on, now_available

    refused, available, settings, by_analyst, by_portal, turned_on, again, audit, on, now_available = call(scenario, enabled=())
    assert refused.status_code == 403
    assert available["available"] is False and available["customers"] == []
    assert settings["settings"] == {"customer_code": "ACME", "enabled": False, "updated_at": None, "updated_by": None}
    assert by_analyst.status_code == 403 and by_portal.status_code == 403
    assert turned_on.status_code == 200 and turned_on.json()["settings"]["enabled"] is True
    assert again.status_code == 200
    assert audit.await_count == 1
    assert audit.await_args.kwargs["action"] == AuditAction.AUDIT_SETTINGS_UPDATE
    assert audit.await_args.kwargs["old_value"] == {"enabled": False} and audit.await_args.kwargs["new_value"] == {"enabled": True}
    assert on.status_code == 200
    assert now_available == {
        "available": True,
        "customers": [{"customer_code": "ACME", "customer_name": "Acme Corp"}],
        "success": True,
        "message": "The audit log is available",
    }


def test_an_analyst_reads_the_switch_only_of_their_customers_and_an_unknown_customer_is_a_404():
    async def scenario(client):
        other = await client.get(f"{AUDIT}/settings/GLOBEX", headers=as_user("ana"))
        missing = await client.put(f"{AUDIT}/settings/NOPE", json={"enabled": True}, headers=as_user("admin"))
        return other, missing

    other, missing = call(scenario)
    assert other.status_code == 403
    assert missing.status_code == 404


@pytest.mark.parametrize("user", ["mia", "gx", "admin", "ana"])
def test_only_a_customer_admin_reads_the_log(user):
    response = call(get(AUDIT, user=user))
    assert response.status_code == 403


def test_a_customer_admin_whose_customer_has_it_off_reads_nothing():
    # gboss administers GLOBEX, whose switch is off.
    assert call(get(AUDIT, user="gboss")).status_code == 403
    assert call(get(f"{AUDIT}/availability", user="gboss")).json()["available"] is False
    # Asking for a customer they do not administer narrows the scope to nothing.
    assert call(get(AUDIT, customer_codes="GLOBEX")).status_code == 403


# ── which rows, who and what ──────────────────────────────────────────────────


def test_the_log_shows_the_customers_actions_and_its_users_account_events_only():
    body = call(get(AUDIT, page_size=100)).json()
    assert [entry["action"] for entry in body["entries"]] == expected_actions()
    assert body["total"] == len(expected_actions())
    assert body["retention_days"] == 90
    assert body["members"] == [{"id": 10, "username": "boss"}, {"id": 11, "username": "mia"}]


def test_the_soc_is_never_named_and_its_addresses_never_shown():
    entries = {entry["action"] + ":" + str(entry["id"]): entry for entry in call(get(AUDIT, page_size=100)).json()["entries"]}
    by_action = {}
    for entry in entries.values():
        by_action.setdefault(entry["action"], []).append(entry)

    status = by_action["alert.status_change"][0]
    assert status["actor"] == {"kind": "member", "username": "mia"}
    assert status["source_ip"] == "203.0.113.7"
    assert (status["from_value"], status["to_value"]) == ("OPEN", "CLOSED")
    assert status["target"] == {"type": "alert", "id": "7", "label": None}
    assert status["label"] == "Alert status changed" and status["category"] == "alerts"

    soc = by_action["case.status_change"][0]
    assert soc["actor"] == {"kind": "soc", "username": None}
    assert soc["source_ip"] is None
    assert (soc["from_value"], soc["to_value"]) == ("OPEN", "PENDING_CUSTOMER")

    created = by_action["case.create"][0]
    assert created["target"] == {"type": "case", "id": "3", "label": "Ransomware on web-01"}
    assert created["from_value"] is None and created["to_value"] is None

    assert by_action["alert.comment_create"][0]["actor"] == {"kind": "other", "username": None}
    failed = by_action["auth.login_failed"][0]
    assert failed["actor"] == {"kind": "unknown", "username": None}
    assert failed["source_ip"] is None and failed["result"] == "failure"
    assert failed["target"] == {"type": "user", "id": "boss", "label": "boss"}

    login = by_action["auth.login"][0]
    # Filed under GLOBEX, which boss does not administer: never named.
    assert login["customer_code"] is None
    assert login["label"] == "Signed in" and login["category"] == "account"

    assert by_action["user.update"][0]["label"] == "Password changed"
    assert by_action["user.totp_enable"][0]["label"] == "Two-factor authentication turned on"
    assert by_action["user.disable"][0]["actor"]["kind"] == "soc"
    assert by_action["customer_admin.update"][0]["label"] == "Made a customer administrator"
    assert by_action["report.generate"][0]["target"]["label"] == "Monthly review"


def test_stored_details_values_and_comment_text_never_leave():
    text = call(get(AUDIT, page_size=100)).text
    for secret in ("secret comment text", "Self-service password change", "mia@acme.test", "Portal user disabled", "10.0.0.5"):
        assert secret not in text
    assert "details" not in text and "new_value" not in text


def test_a_soc_report_shows_while_the_customer_sees_it():
    # Shown to the customer now: the SOC's "Internal: weak spots" generation appears.
    async def scenario(client):
        before = (await client.get(AUDIT, params={"category": "reports"}, headers=as_user("boss"))).json()
        return before

    labels = [entry["target"]["label"] for entry in call(scenario)["entries"]]
    assert labels == ["Monthly review", "=HYPERLINK(1)"]

    shared = report(2, "Internal: weak spots", visible=True)

    async def shared_scenario(client):
        return (await client.get(AUDIT, params={"category": "reports"}, headers=as_user("boss"))).json()

    async def run():
        db = await Db().create()
        try:
            await _seed(db)
            async with db.session() as session:
                found = await session.get(IncidentManagementCustomerReport, 2)
                found.visible_to_customer = shared.visible_to_customer
                await session.commit()
            transport = httpx.ASGITransport(app=_app(db))

            async def resolve_user(self, request, username):
                return USERS.get(username)

            with patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))), patch.object(
                AuthHandler,
                "_resolve_user",
                resolve_user,
            ):
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    return await shared_scenario(client)
        finally:
            await db.dispose()

    labels = [entry["target"]["label"] for entry in asyncio.run(run())["entries"]]
    assert labels == ["Monthly review", "Internal: weak spots", "=HYPERLINK(1)"]


# ── filters and paging ────────────────────────────────────────────────────────


def test_category_user_and_period_filters():
    accounts = call(get(AUDIT, category="account", page_size=100)).json()["entries"]
    assert {entry["category"] for entry in accounts} == {"account"}
    assert len(accounts) == 4

    mia = call(get(AUDIT, user_id=11, page_size=100)).json()["entries"]
    # What mia did, and what was done to her account.
    assert {entry["action"] for entry in mia} == {
        "alert.status_change",
        "report.download",
        "auth.login",
        "user.update",
        "user.totp_enable",
        "user.disable",
        "customer_user.invite",
    }

    window = call(
        get(AUDIT, since=(T - timedelta(minutes=5)).isoformat() + "Z", until=(T - timedelta(minutes=2)).isoformat() + "Z"),
    ).json()["entries"]
    # [T-5, T-2): minutes 5, 4 and 3 before T; the end is exclusive.
    assert [entry["action"] for entry in window] == ["case.create", "alert.comment_create", "ai_analysis.request"]


def test_a_user_who_is_not_one_of_theirs_is_a_404_and_a_reversed_period_a_422():
    assert call(get(AUDIT, user_id=12)).status_code == 404
    assert call(get(AUDIT, user_id=2)).status_code == 404
    reversed_period = call(get(AUDIT, since=T.isoformat() + "Z", until=(T - timedelta(days=1)).isoformat() + "Z"))
    assert reversed_period.status_code == 422
    assert call(get(AUDIT, category="connectors")).status_code == 422
    assert call(get(AUDIT, page_size=101)).status_code == 422


def test_pages_are_newest_first_and_the_total_counts_every_page():
    first = call(get(AUDIT, page_size=5)).json()
    second = call(get(AUDIT, page=2, page_size=5)).json()
    assert first["total"] == second["total"] == len(expected_actions())
    assert [entry["action"] for entry in first["entries"] + second["entries"]] == expected_actions()[:10]
    assert call(get(AUDIT)).headers["cache-control"] == "no-store"


# ── the CSV ───────────────────────────────────────────────────────────────────


def test_the_export_is_the_filtered_log_with_formulas_defused():
    response = call(get(f"{AUDIT}/export", category="reports"))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["x-export-truncated"] == "false"
    assert response.headers["cache-control"] == "no-store"
    assert "attachment" in response.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == service.CSV_HEADER
    assert rows[1][3:6] == ["Report generated", "SOC", "Report #1 (Monthly review)"]
    # Inside the cell, not at its start: a spreadsheet reads it as text.
    assert rows[2][3:6] == ["Report downloaded", "mia", "Report #5 (=HYPERLINK(1))"]
    assert rows[2][9] == ""


def test_a_cell_that_starts_like_a_formula_is_defused():
    entry = service.PortalAuditEntry(
        id=1,
        timestamp="2026-10-01T12:00:00Z",
        action="alert.status_change",
        label="Alert status changed",
        category="alerts",
        actor=service.PortalAuditActor(kind="soc"),
        customer_code="ACME",
        from_value="=cmd|'/c calc'!A1",
        to_value="+1",
        result="success",
    )
    row_ = service.csv_row(entry)
    assert row_[6:8] == ["'=cmd|'/c calc'!A1", "'+1"]


def test_the_export_says_when_it_was_cut():
    with patch("app.customer_portal.services.audit.EXPORT_LIMIT", 3):
        # The default is bound at definition time: patch the function's default too.
        with patch.object(service.export_csv, "__kwdefaults__", {**service.export_csv.__kwdefaults__, "limit": 3}):
            response = call(get(f"{AUDIT}/export"))
    assert response.headers["x-export-truncated"] == "true"
    assert len(list(csv.reader(io.StringIO(response.text)))) == 4


def test_the_export_is_refused_like_the_log():
    assert call(get(f"{AUDIT}/export", user="mia")).status_code == 403


# ── the pure helpers ──────────────────────────────────────────────────────────


def test_every_shown_action_has_a_category_and_a_label_and_none_is_internal():
    internal = {AuditAction.CONNECTOR_UPDATE, AuditAction.ALERT_VERDICT_SET, AuditAction.TALON_ACTION_APPROVE, AuditAction.UBA_ROLLBACK}
    assert not {action.value for action in internal} & set(service.ACTIONS)
    for action, spec in service.ACTIONS.items():
        assert AuditAction(action)
        assert spec.label and spec.category in ("alerts", "cases", "reports", "users", "account")


def test_actor_text_and_target_text():
    assert service.actor_text(service.PortalAuditActor(kind="soc")) == "SOC"
    assert service.actor_text(service.PortalAuditActor(kind="member", username="mia")) == "mia"
    assert service.actor_text(service.PortalAuditActor(kind="unknown")) == "Unknown"
    assert service.target_text(service.PortalAuditTarget(type="user", id="mia", label="mia")) == "User mia"
    assert service.target_text(service.PortalAuditTarget(type="alert", id="7")) == "Alert #7"


# ── the events the routes now write ───────────────────────────────────────────


def test_status_changes_are_recorded_once_per_object_that_moved(audit_rows):
    from app.incidents.services.audit_trail import record_status_changes

    user = SimpleNamespace(id=11, username="mia")
    asyncio.run(record_status_changes("alert", user, [(7, "ACME", "OPEN", "CLOSED"), (8, "ACME", "CLOSED", "CLOSED")]))
    asyncio.run(record_status_changes("case", user, [(3, "ACME", "OPEN", "IN_PROGRESS")]))
    assert [(r.action, r.entity_id, r.old_value, r.new_value, r.customer_code) for r in audit_rows] == [
        ("alert.status_change", "7", {"status": "OPEN"}, {"status": "CLOSED"}, "ACME"),
        ("case.status_change", "3", {"status": "OPEN"}, {"status": "IN_PROGRESS"}, "ACME"),
    ]
    assert {r.actor_username for r in audit_rows} == {"mia"}


def test_nothing_is_written_when_nothing_moved(audit_rows):
    from app.incidents.services.audit_trail import record_status_changes

    asyncio.run(record_status_changes("alert", SimpleNamespace(id=1, username="a"), [(7, "ACME", "OPEN", "OPEN")]))
    assert audit_rows == []


def test_a_report_is_audited_by_name_and_period_read_before_it_is_deleted(audit_rows):
    from app.incidents.routes.customer_report import _audit_report
    from app.incidents.routes.customer_report import _report_snapshot

    snapshot = _report_snapshot(report(9, "Q3 review"))
    asyncio.run(_audit_report(AuditAction.REPORT_DELETE, SimpleNamespace(id=10, username="boss"), snapshot))
    (written,) = audit_rows
    assert (written.action, written.entity_type, written.entity_id, written.customer_code) == ("report.delete", "report", "9", "ACME")
    assert written.new_value["report_name"] == "Q3 review"
    assert written.new_value["date_to"] == T.isoformat()


def test_own_two_factor_changes_are_audited_with_the_address(audit_rows):
    from app.auth.routes.totp import _audit_own_totp

    request = SimpleNamespace(headers={"x-forwarded-for": "203.0.113.7, 10.0.0.1"}, client=None)
    asyncio.run(_audit_own_totp(AuditAction.USER_TOTP_DISABLE, SimpleNamespace(id=11, username="mia"), request))
    (written,) = audit_rows
    assert (written.action, written.entity_type, written.entity_id, written.source_ip) == (
        "user.totp_disable",
        "user",
        "mia",
        "203.0.113.7",
    )
