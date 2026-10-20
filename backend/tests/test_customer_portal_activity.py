"""The Customer Portal Activity page (#1284): opt-in, tenant-scoped, counted from opened_at.

Real routers, real in-memory database, real request parsing; only token decoding and
user lookup are replaced (as in test_customer_portal_sla).

Pinned here:
- a missing switch row reads as off, and a disabled customer adds nothing to any figure;
- only an admin flips the switch (audited); an analyst reads it for customers they see;
- a portal user counts their own customers' alerts and cases only;
- alerts are counted from their SLA clock's ``opened_at``, never ``alert_creation_time``;
- an alert with two assets or two tags is one alert per slice; a NULL severity is the
  deployment default; verdict rates use reviewed alerts only;
- each section fails on its own;
- the alerts list takes the same window and the exact alert name, so a click on a slice
  lists exactly what it counted;
- the pure shaping helpers.

Run with: cd backend && python -m pytest tests/test_customer_portal_activity.py
"""

import asyncio
import os
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402
from sqlalchemy.dialects import mysql  # noqa: E402

from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.customer_portal.services import activity as service  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import CustomerPortalActivitySettings  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.incidents.models import AlertTag  # noqa: E402
from app.incidents.models import AlertToTag  # noqa: E402
from app.incidents.models import Asset  # noqa: E402
from app.incidents.services.db_operations import _alert_criteria  # noqa: E402
from tests.soc_management_support import AlertSlaTracking  # noqa: E402
from tests.soc_management_support import CaseSlaTracking  # noqa: E402
from tests.soc_management_support import Db  # noqa: E402
from tests.soc_management_support import add_alert  # noqa: E402
from tests.soc_management_support import add_case  # noqa: E402
from tests.soc_management_support import tracking_row  # noqa: E402

USERS = {
    "admin": SimpleNamespace(id=1, username="admin", role_id=1),
    "ana": SimpleNamespace(id=2, username="ana", role_id=2),
    "portal": SimpleNamespace(id=4, username="portal", role_id=4),
}
SCOPES = {"admin": ["admin"], "ana": ["analyst"], "portal": ["customer_user"]}

#: The request's "now": the 30-day period is [NOW - 30d, NOW), the previous one the 30 days before.
NOW = datetime(2026, 10, 1, 12, 0, 0)
IN_PERIOD = NOW - timedelta(days=3)
IN_PREVIOUS = NOW - timedelta(days=40)
TOO_OLD = NOW - timedelta(days=70)

ACTIVITY = "/customer_portal/activity"


def _app(db: Db) -> FastAPI:
    from app.routers import customer_portal

    app = FastAPI()
    app.include_router(customer_portal.router)

    async def _session():
        async with db.session() as session:
            yield session

    app.dependency_overrides[get_db] = _session
    return app


async def _alert(session, *, opened: datetime, customer="ACME", assets=(), tags=(), **fields):
    alert = await add_alert(session, customer=customer, **fields)
    session.add(tracking_row(AlertSlaTracking, alert.id, opened=opened))
    for name in assets:
        session.add(
            Asset(
                alert_linked=alert.id,
                asset_name=name,
                alert_context_id=1,
                customer_code=customer,
                index_name="idx",
                index_id="1",
            ),
        )
    for tag in tags:
        session.add(AlertToTag(alert_id=alert.id, tag_id=await _tag(session, tag)))
    await session.commit()
    return alert


async def _tag(session, name: str) -> int:
    from sqlmodel import select

    found = (await session.execute(select(AlertTag).where(AlertTag.tag == name))).scalars().first()
    if found:
        return found.id
    tag = AlertTag(tag=name)
    session.add(tag)
    await session.flush()
    return tag.id


async def _case(session, *, opened: datetime, customer="ACME", **fields):
    case = await add_case(session, customer=customer, **fields)
    session.add(tracking_row(CaseSlaTracking, case.id, opened=opened))
    await session.commit()
    return case


async def _seed(db: Db, *, enabled=("ACME",)) -> None:
    async with db.session() as session:
        session.add_all(
            [
                User(id=1, username="admin", password="x" * 8, email="admin@example.com", role_id=1),
                User(id=2, username="ana", password="x" * 8, email="ana@example.com", role_id=2),
                User(id=4, username="portal", password="x" * 8, email="portal@example.com", role_id=4),
                Customers(customer_code="ACME", customer_name="Acme Corp"),
                Customers(customer_code="GLOBEX", customer_name="Globex"),
            ],
        )
        await session.commit()
        session.add_all([UserCustomerAccess(user_id=4, customer_code="ACME"), UserCustomerAccess(user_id=2, customer_code="ACME")])
        session.add_all([CustomerPortalActivitySettings(customer_code=code, enabled=True) for code in enabled])
        await session.commit()

        # ACME, this period: four alerts.
        await _alert(
            session,
            opened=IN_PERIOD,
            name="Brute force",
            source="wazuh",
            severity="Critical",
            assets=["web-01", "web-01-alias"],
            tags=["auth", "ssh"],
            verdict="TRUE_POSITIVE",
        )
        await _alert(
            session,
            opened=IN_PERIOD,
            name="Brute force",
            source="wazuh",
            severity=None,
            assets=["web-01"],
            tags=["auth"],
            verdict="FALSE_POSITIVE",
            created=NOW - timedelta(days=200),
        )
        await _alert(session, opened=IN_PERIOD, name="Odd login", source="office365", severity="low", assets=["db-01"])
        # Reached the SOC long ago, last seen yesterday: ingest moved its creation time.
        await _alert(session, opened=TOO_OLD, name="Old but busy", source="wazuh", created=NOW - timedelta(days=1))
        # ACME, the previous period: one alert.
        await _alert(session, opened=IN_PREVIOUS, name="Brute force", source="wazuh", severity="High", assets=["web-01"])
        # GLOBEX, this period: never visible to the portal user.
        await _alert(session, customer="GLOBEX", opened=IN_PERIOD, name="Globex only", source="crowdstrike", assets=["gx-01"])

        await _case(session, opened=IN_PERIOD, name="[INC] Ransomware on web-01", status="CLOSED")
        await _case(session, opened=IN_PERIOD, name="Question about a login", status="PENDING_CUSTOMER")
        await _case(session, opened=IN_PREVIOUS, name="[rfi] Firewall change", status="OPEN")
        await _case(session, customer="GLOBEX", opened=IN_PERIOD, name="[INC] Globex", status="OPEN")


def call(scenario, *, enabled=("ACME",)):
    async def _inner():
        db = await Db().create()
        try:
            await _seed(db, enabled=enabled)
            transport = httpx.ASGITransport(app=_app(db))

            async def resolve_user(self, request, username):
                return USERS.get(username)

            with patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))), patch.object(
                AuthHandler,
                "_resolve_user",
                resolve_user,
            ), patch("app.customer_portal.routes.activity.now_utc", lambda: NOW.replace(tzinfo=timezone.utc)):
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    return await scenario(client)
        finally:
            await db.dispose()

    return asyncio.run(_inner())


def as_user(name):
    return {"Authorization": f"Bearer {name}"}


def by_key(items):
    return {item["key"]: (item["count"], item["previous"]) for item in items}


# ── the switch ──────────────────────────────────────────────────────────────


def test_the_page_is_off_until_an_admin_turns_it_on():
    async def scenario(client):
        off = (await client.get(ACTIVITY, headers=as_user("portal"))).json()
        available = (await client.get(f"{ACTIVITY}/availability", headers=as_user("portal"))).json()
        settings = (await client.get(f"{ACTIVITY}/settings/ACME", headers=as_user("ana"))).json()
        with patch("app.customer_portal.routes.activity.record_audit_event", AsyncMock()) as audit:
            refused = await client.put(f"{ACTIVITY}/settings/ACME", json={"enabled": True}, headers=as_user("ana"))
            turned_on = await client.put(f"{ACTIVITY}/settings/ACME", json={"enabled": True}, headers=as_user("admin"))
            again = await client.put(f"{ACTIVITY}/settings/ACME", json={"enabled": True}, headers=as_user("admin"))
        on = (await client.get(ACTIVITY, headers=as_user("portal"))).json()
        return off, available, settings, refused, turned_on, again, audit, on

    off, available, settings, refused, turned_on, again, audit, on = call(scenario, enabled=())
    assert off["enabled"] is False and off["alerts"]["opened"]["count"] == 0
    assert available["enabled"] is False
    assert settings["settings"] == {"customer_code": "ACME", "enabled": False, "updated_at": None, "updated_by": None}
    assert refused.status_code == 403
    assert turned_on.status_code == 200 and turned_on.json()["settings"]["enabled"] is True
    assert again.status_code == 200
    # Audited once: setting it to what it already is changes nothing.
    assert audit.await_count == 1
    assert audit.await_args.kwargs["old_value"] == {"enabled": False}
    assert audit.await_args.kwargs["new_value"] == {"enabled": True}
    assert on["enabled"] is True and on["customer_codes"] == ["ACME"]


def test_an_analyst_cannot_read_the_switch_of_a_customer_they_do_not_have():
    async def scenario(client):
        return await client.get(f"{ACTIVITY}/settings/GLOBEX", headers=as_user("ana"))

    assert call(scenario).status_code == 403


def test_a_switch_for_a_customer_that_does_not_exist_is_a_404():
    async def scenario(client):
        return await client.put(f"{ACTIVITY}/settings/NOPE", json={"enabled": True}, headers=as_user("admin"))

    assert call(scenario).status_code == 404


def test_a_portal_user_cannot_flip_the_switch():
    async def scenario(client):
        return await client.put(f"{ACTIVITY}/settings/ACME", json={"enabled": True}, headers=as_user("portal"))

    assert call(scenario).status_code == 403


def test_a_range_outside_the_three_is_refused():
    async def scenario(client):
        return await client.get(ACTIVITY, params={"range": "1y"}, headers=as_user("portal"))

    assert call(scenario).status_code == 422


# ── the figures ─────────────────────────────────────────────────────────────


def test_a_portal_user_sees_their_customer_counted_from_opened_at():
    async def scenario(client):
        return (await client.get(ACTIVITY, params={"range": "30d"}, headers=as_user("portal"))).json()

    body = call(scenario, enabled=("ACME", "GLOBEX"))
    assert body["enabled"] is True and body["customer_codes"] == ["ACME"]
    assert body["since"] == "2026-09-01T12:00:00Z"
    assert body["until"] == "2026-10-01T12:00:00Z"
    assert body["previous_since"] == "2026-08-02T12:00:00Z"

    alerts = body["alerts"]
    assert alerts["error"] is None
    # "Old but busy" reached the SOC 70 days ago: its moved creation time does not count it.
    assert alerts["opened"] == {"count": 3, "previous": 1}
    assert by_key(alerts["by_source"]) == {"wazuh": (2, 1), "office365": (1, 0)}
    assert alerts["other_sources"] == {"count": 0, "previous": 0}
    # Every level, most severe first; the NULL severity is the default (High); "low" is Low.
    assert [item["key"] for item in alerts["by_severity"]] == ["Critical", "High", "Medium", "Low", "Informational"]
    assert by_key(alerts["by_severity"]) == {
        "Critical": (1, 0),
        "High": (1, 1),
        "Medium": (0, 0),
        "Low": (1, 0),
        "Informational": (0, 0),
    }
    assert [(item["key"], item["count"], item["previous"]) for item in alerts["top_detections"]] == [
        ("Brute force", 2, 1),
        ("Odd login", 1, 0),
    ]
    # Two asset rows on one alert are still one alert for that asset.
    assert by_key(alerts["top_assets"]) == {"web-01": (2, 1), "web-01-alias": (1, 0), "db-01": (1, 0)}
    assert alerts["top_assets"][0]["key"] == "web-01"
    assert by_key(alerts["top_tags"]) == {"auth": (2, 0), "ssh": (1, 0)}
    assert "Globex only" not in str(body) and "gx-01" not in str(body)


def test_verdicts_use_reviewed_alerts_only():
    async def scenario(client):
        return (await client.get(ACTIVITY, headers=as_user("portal"))).json()

    verdicts = call(scenario)["verdicts"]
    assert verdicts["error"] is None
    assert verdicts["current"] == {
        "total": 3,
        "reviewed": 2,
        "true_positive": 1,
        "false_positive": 1,
        "untriaged": 1,
        "false_positive_rate": 50.0,
        "coverage_rate": 66.7,
    }
    # Nothing reviewed before: no rate, never 0%.
    assert verdicts["previous"]["reviewed"] == 0 and verdicts["previous"]["false_positive_rate"] is None
    assert verdicts["reasons"] == [{"key": "UNSPECIFIED", "label": "Unspecified", "count": 1, "previous": 0}]
    assert verdicts["noisy_detections"] == [
        {"name": "Brute force", "false_positives": 1, "reviewed": 2, "false_positive_rate": 50.0},
    ]


def test_cases_by_type_and_status():
    async def scenario(client):
        return (await client.get(ACTIVITY, headers=as_user("portal"))).json()

    cases = call(scenario)["cases"]
    assert cases["error"] is None
    assert cases["opened"] == {"count": 2, "previous": 1}
    assert [(item["key"], item["label"], item["count"], item["previous"]) for item in cases["by_type"]] == [
        ("INC", "Incident", 1, 0),
        ("RFI", "Request for information", 0, 1),
        ("OTHER", "Other", 1, 0),
    ]
    assert by_key(cases["by_status"]) == {"CLOSED": (1, 0), "PENDING_CUSTOMER": (1, 0), "OPEN": (0, 1)}


def test_a_disabled_customer_adds_nothing_even_for_an_admin():
    async def scenario(client):
        return (await client.get(ACTIVITY, headers=as_user("admin"))).json()

    body = call(scenario, enabled=("ACME",))
    assert body["customer_codes"] == ["ACME"]
    assert "crowdstrike" not in by_key(body["alerts"]["by_source"])
    assert body["cases"]["opened"]["count"] == 2


def test_the_seven_day_range_moves_both_windows():
    async def scenario(client):
        return (await client.get(ACTIVITY, params={"range": "7d"}, headers=as_user("portal"))).json()

    body = call(scenario)
    assert body["since"] == "2026-09-24T12:00:00Z" and body["previous_since"] == "2026-09-17T12:00:00Z"
    assert body["alerts"]["opened"] == {"count": 3, "previous": 0}


def test_a_failing_section_leaves_the_others():
    async def scenario(client):
        with patch.object(service, "alerts_section", AsyncMock(side_effect=RuntimeError("SELECT boom FROM secrets"))):
            return (await client.get(ACTIVITY, headers=as_user("portal"))).json()

    body = call(scenario)
    assert body["alerts"]["error"] == "Failed to load the alerts"
    assert "secrets" not in str(body)
    assert body["verdicts"]["error"] is None and body["verdicts"]["current"]["total"] == 3
    assert body["cases"]["opened"]["count"] == 2


def test_the_portal_surface_writes_only_the_operators_switch():
    from app.routers import customer_portal

    writes = {
        (method, route.path)
        for route in customer_portal.router.routes
        if isinstance(route, APIRoute) and route.path.startswith("/customer_portal/activity")
        for method in route.methods
        if method != "GET"
    }
    assert writes == {("PUT", "/customer_portal/activity/settings/{customer_code}")}


# ── the alerts list takes the same window ───────────────────────────────────


def _sql(filters) -> str:
    from sqlalchemy import and_

    return str(and_(*filters).compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}))


def test_the_alert_filter_bounds_opened_at_and_matches_the_name_exactly():
    sql = _sql(_alert_criteria(alert_name="Brute force", opened_from=IN_PREVIOUS, opened_before=NOW))
    assert "incident_management_alert.alert_name = 'Brute force'" in sql
    assert "soc_sla_alert_tracking.opened_at >= '2026-08-22 12:00:00'" in sql
    assert "soc_sla_alert_tracking.opened_at < '2026-10-01 12:00:00'" in sql
    assert "incident_management_alert.id IN (SELECT soc_sla_alert_tracking.alert_id" in sql
    # The search keeps its own meaning.
    assert "alert_name LIKE '%%Brute%%'" in _sql(_alert_criteria(alert_title="Brute"))


def test_either_bound_of_the_opened_window_works_alone():
    assert "opened_at >=" in _sql(_alert_criteria(opened_from=IN_PREVIOUS)) and "opened_at <" not in _sql(
        _alert_criteria(opened_from=IN_PREVIOUS),
    )
    assert "opened_at <" in _sql(_alert_criteria(opened_before=NOW))
    assert _alert_criteria() == []


# ── pure helpers ────────────────────────────────────────────────────────────


def test_the_window_is_the_range_and_the_one_before_it():
    previous_since, since, until = service.activity_window("90d", datetime(2026, 10, 1, 12, 0, 0, 999))
    assert until == datetime(2026, 10, 1, 12, 0, 0)
    assert since == until - timedelta(days=90) and previous_since == until - timedelta(days=180)


def test_sources_beyond_the_limit_are_added_up_including_those_only_seen_before():
    rows = [(f"src-{i}", 10 - i, 1) for i in range(service.SOURCE_LIMIT)] + [("rare", 1, 2), ("gone", 0, 5), (None, 1, 0)]
    shown, other = service.fold_sources(rows)
    assert [item.key for item in shown] == [f"src-{i}" for i in range(service.SOURCE_LIMIT)]
    # "rare" and "Unknown" (a NULL source) both have 1 and sort by name; "gone" has 0 now.
    assert other.count == 2 and other.previous == 7


def test_a_source_spelled_null_and_unknown_is_one_slice():
    shown, _ = service.fold_sources([(None, 1, 0), ("Unknown", 2, 1)])
    assert [(item.key, item.count, item.previous) for item in shown] == [("Unknown", 3, 1)]


def test_severity_resolves_null_and_case_and_keeps_every_level(monkeypatch):
    monkeypatch.setenv("DEFAULT_ALERT_SEVERITY", "Medium")
    levels = service.severity_counts([(None, 2, 1), ("CRITICAL", 1, 0), ("bogus", 1, 0)])
    assert [(item.key, item.count, item.previous) for item in levels] == [
        ("Critical", 1, 0),
        ("High", 0, 0),
        ("Medium", 3, 1),
        ("Low", 0, 0),
        ("Informational", 0, 0),
    ]


def test_verdict_figures_have_no_rate_without_reviews():
    current, previous = service.verdict_section_figures([(None, 4, 0), ("FALSE_POSITIVE", 0, 2), ("TRUE_POSITIVE", 0, 2)])
    assert current.false_positive_rate is None and current.coverage_rate == 0.0 and current.untriaged == 4
    assert previous.false_positive_rate == 50.0 and previous.coverage_rate == 100.0


def test_case_breakdown_reads_the_type_prefix_anywhere_in_any_case():
    section = service.case_breakdown(
        [("Re: [cti] feed", "OPEN", True), ("[CONF] Change", "CLOSED", False), (None, None, True)],
    )
    assert section.opened.count == 2 and section.opened.previous == 1
    assert [(item.key, item.count, item.previous) for item in section.by_type] == [
        ("CONF", 0, 1),
        ("CTI", 1, 0),
        ("OTHER", 1, 0),
    ]
    assert {item.key for item in section.by_status} == {"OPEN", "CLOSED", "UNKNOWN"}


def test_ranked_leaves_out_what_is_quiet_now_and_breaks_ties_by_name():
    assert service.ranked({"b": (2, 0), "a": (2, 9), "c": (0, 5)}) == [("a", 2, 9), ("b", 2, 0)]
    assert service.ranked({"b": (2, 0), "a": (2, 9)}, limit=1) == [("a", 2, 9)]


@pytest.mark.parametrize("name, expected", [("[INC] x", "INC"), ("x [Rfi]", "RFI"), ("nothing", None), (None, None)])
def test_case_type_key_is_shared_with_the_pdf(name, expected):
    from app.incidents.services.customer_report_aggregations import case_type_key

    assert case_type_key(name) == expected
