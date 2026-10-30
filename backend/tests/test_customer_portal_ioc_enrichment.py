"""Threat Intel enrichment of a customer's own IOCs in the Customer Portal (#1318).

Real routers, real in-memory database, real request parsing; only token decoding, user lookup,
the audit writer and the two sources' transports are replaced (VirusTotal by an
``httpx.MockTransport``, OpenCTI's GraphQL call by a recorder).

Pinned here:
- off until an admin turns it on (audited), with an optional daily limit; on only with a source;
- reading an alert's IOCs asks no source; checking one asks each source once, caches per
  customer and value, and answers from the cache until it is older than the TTL;
- only an IOC on an alert of the caller's; another customer's cache is never read; the SOC
  can't use the portal routes; a read-only user may check;
- private addresses and names go nowhere; VirusTotal only for what it can look up, by GET only,
  a URL by its identifier; OpenCTI objects beyond a shareable TLP are withheld;
- the daily limit counts lookups that reached a source; a lookup still running is a 409; a
  lookup no source answered costs nothing and caches nothing; a failed refresh keeps the old answer;
- the pure rules: classification, projections, verdicts, refusals.

Run with: cd backend && python -m pytest tests/test_customer_portal_ioc_enrichment.py
"""

import asyncio
import base64
import gzip
import json
import os
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
from sqlmodel import select  # noqa: E402

from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.customer_portal.schema.ioc_enrichment import OpenCtiDetails  # noqa: E402
from app.customer_portal.schema.ioc_enrichment import VirusTotalDetails  # noqa: E402
from app.customer_portal.services import ioc_enrichment as service  # noqa: E402
from app.customer_portal.services import ioc_enrichment_sources as sources  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import CustomerPortalIocEnrichment  # noqa: E402
from app.db.universal_models import CustomerPortalIocEnrichmentSettings  # noqa: E402
from app.db.universal_models import CustomerPortalIocLookup  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.incidents.models import AlertToIoC  # noqa: E402
from app.incidents.models import IoC  # noqa: E402
from app.time_utils import now_utc  # noqa: E402
from tests.soc_management_support import _tables  # noqa: E402
from tests.soc_management_support import add_alert  # noqa: E402

PEOPLE = [(1, "admin", 1), (2, "ana", 2), (10, "jane", 4), (11, "reader", 4), (12, "gus", 4)]
USERS = {name: SimpleNamespace(id=uid, username=name, role_id=role) for uid, name, role in PEOPLE}
SCOPES = {name: ["customer_user"] if role == 4 else (["admin"] if role == 1 else ["analyst"]) for _, name, role in PEOPLE}
TABLES = {"customer_portal_ioc_enrichment_settings", "customer_portal_ioc_enrichment", "customer_portal_ioc_lookup"}
BASE = "/customer_portal/ioc_enrichment"
VT_URL = "https://vt.test/api/v3"
EVIL_IP = "45.155.205.233"
EVIL_HASH = "44D88612FEA8A8F36DE82E1278ABB02F"

VT_IP = {
    "data": {
        "id": EVIL_IP,
        "type": "ip_address",
        "links": {"self": "x"},
        "attributes": {
            "last_analysis_stats": {"malicious": 7, "suspicious": 1, "harmless": 60, "undetected": 25, "timeout": 1},
            "reputation": -42,
            "last_analysis_date": 1761638400,
            "tags": ["scanner", "bad‮name"],
            "country": "NL",
            "as_owner": "Example Hosting B.V.",
            "whois": "a long text the portal never shows",
        },
    },
}
OPENCTI_FOUND = {
    "stixCyberObservables": {
        "edges": [
            {
                "node": {
                    "entity_type": "IPv4-Addr",
                    "observable_value": EVIL_IP,
                    "x_opencti_score": 50,
                    "objectLabel": [{"value": "botnet"}],
                    "objectMarking": [{"definition": "TLP:GREEN"}],
                    "indicators": {
                        "edges": [
                            {
                                "node": {
                                    "name": "Botnet C2",
                                    "x_opencti_score": 85,
                                    "valid_until": "2027-01-01T00:00:00.000Z",
                                    "revoked": False,
                                    "objectMarking": [{"definition": "TLP:AMBER"}],
                                },
                            },
                            {
                                "node": {
                                    "name": "Secret feed",
                                    "x_opencti_score": 100,
                                    "revoked": False,
                                    "objectMarking": [{"definition": "TLP:RED"}],
                                },
                            },
                        ],
                    },
                    "reports": {
                        "edges": [
                            {"node": {"name": "Q3 botnet review", "published": "2026-09-30T00:00:00.000Z", "objectMarking": []}},
                            {"node": {"name": "Partner only", "published": None, "objectMarking": [{"definition": "TLP:AMBER+STRICT"}]}},
                        ],
                    },
                },
            },
        ],
    },
}


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
    from app.routers import customer_portal

    app = FastAPI()
    app.include_router(customer_portal.router)

    async def _session():
        async with db.session() as session:
            yield session

    app.dependency_overrides[get_db] = _session
    return app


async def _ioc(s, alert_id: int, value: str, kind: str = "IP") -> int:
    ioc = IoC(value=value, type=kind, description="")
    s.add(ioc)
    await s.commit()
    s.add(AlertToIoC(alert_id=alert_id, ioc_id=ioc.id))
    await s.commit()
    return ioc.id


async def _seed(db: Db, *, enabled=("ACME",), limit=None) -> dict:
    async with db.session() as s:
        s.add_all(User(id=uid, username=name, password="x" * 8, email=f"{name}@example.com", role_id=role) for uid, name, role in PEOPLE)
        s.add_all([Customers(customer_code="ACME", customer_name="Acme"), Customers(customer_code="GLOBEX", customer_name="Globex")])
        await s.commit()
        s.add_all(
            [
                UserCustomerAccess(user_id=10, customer_code="ACME"),
                UserCustomerAccess(user_id=11, customer_code="ACME", read_only=True),
                UserCustomerAccess(user_id=12, customer_code="GLOBEX"),
                UserCustomerAccess(user_id=2, customer_code="ACME"),
            ],
        )
        s.add_all(CustomerPortalIocEnrichmentSettings(customer_code=code, enabled=True, daily_lookup_limit=limit) for code in enabled)
        await s.commit()
        alert = await add_alert(s, name="Outbound to a botnet")
        other = await add_alert(s, name="Another one")
        globex = await add_alert(s, name="Globex alert", customer="GLOBEX")
        ids = {
            "alert": alert.id,
            "other": other.id,
            "globex": globex.id,
            "ip": await _ioc(s, alert.id, EVIL_IP),
            "hash": await _ioc(s, alert.id, EVIL_HASH, "HASH"),
            "private": await _ioc(s, alert.id, "10.20.30.40"),
            "email": await _ioc(s, alert.id, "ceo@example-corp.com", "EMAIL"),
            "url": await _ioc(s, alert.id, "https://bad.example.net/login?x=1", "URL"),
            "other_ip": await _ioc(s, other.id, "185.220.101.1"),
            "globex_ip": await _ioc(s, globex.id, EVIL_IP),
        }
        return ids


class Fake(SimpleNamespace):
    pass


def call(scenario, *, enabled=("ACME",), limit=None, vt=True, opencti=True):
    async def _inner():
        db = await Db().create()
        ids = await _seed(db, enabled=enabled, limit=limit)
        fake = Fake(
            db=db,
            ids=ids,
            audit=AsyncMock(),
            vt_requests=[],
            vt_answers={},
            opencti_calls=[],
            opencti_answer=OPENCTI_FOUND,
            opencti_ok=True,
        )

        def vt_handler(request: httpx.Request) -> httpx.Response:
            fake.vt_requests.append(request)
            answer = fake.vt_answers.get(request.url.path)
            if answer is None:
                return httpx.Response(404, json={"error": {"code": "NotFoundError"}})
            if isinstance(answer, httpx.Response):
                return answer
            status, body = answer
            return httpx.Response(status, json=body)

        async def graphql(query, variables=None, **kwargs):
            fake.opencti_calls.append(variables)
            if not fake.opencti_ok:
                return {"success": False, "message": "boom at http://opencti.internal", "data": None, "errors": []}
            return {"success": True, "message": "ok", "data": fake.opencti_answer, "errors": []}

        async def resolve_user(self, request, username):
            return USERS.get(username)

        async def credentials():
            return (VT_URL, "vt-key") if vt else None

        async def opencti_configured():
            return opencti

        with patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))), patch.object(
            AuthHandler,
            "_resolve_user",
            resolve_user,
        ), patch.object(sources, "virustotal_credentials", credentials), patch.object(
            sources,
            "opencti_configured",
            opencti_configured,
        ), patch.object(
            sources,
            "_virustotal_client",
            lambda: httpx.AsyncClient(transport=httpx.MockTransport(vt_handler)),
        ), patch.object(
            sources,
            "send_graphql_request",
            graphql,
        ), patch(
            "app.customer_portal.services.ioc_enrichment.record_audit_event",
            fake.audit,
        ), patch(
            "app.customer_portal.routes.ioc_enrichment.record_audit_event",
            fake.audit,
        ):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=_app(db)), base_url="http://test") as client:
                return await scenario(client, fake)

    return asyncio.run(_inner())


def as_user(name):
    return {"Authorization": f"Bearer {name}"}


async def rows(db: Db, model, *where):
    async with db.session() as s:
        return (await s.execute(select(model).where(*where))).scalars().all()


def check(client, alert_id, ioc_id, user="jane"):
    return client.post(f"{BASE}/alert/{alert_id}/ioc/{ioc_id}", headers=as_user(user))


def by_source(ioc: dict) -> dict:
    return {result["source"]: result for result in ioc["sources"]}


def vt_ip(fake, body=VT_IP, status=200):
    fake.vt_answers[f"/api/v3/ip_addresses/{EVIL_IP}"] = (status, body)


# ── the switch ────────────────────────────────────────────────────────────────


def test_off_until_an_admin_turns_it_on():
    async def scenario(client, fake):
        available = (await client.get(f"{BASE}/availability", headers=as_user("jane"))).json()
        listed = await client.get(f"{BASE}/alert/{fake.ids['alert']}", headers=as_user("jane"))
        checked = await check(client, fake.ids["alert"], fake.ids["ip"])
        by_analyst = await client.put(f"{BASE}/settings/ACME", json={"enabled": True}, headers=as_user("ana"))
        turned_on = await client.put(f"{BASE}/settings/ACME", json={"enabled": True, "daily_lookup_limit": 50}, headers=as_user("admin"))
        again = await client.put(f"{BASE}/settings/ACME", json={"enabled": True, "daily_lookup_limit": 50}, headers=as_user("admin"))
        read = (await client.get(f"{BASE}/settings/ACME", headers=as_user("ana"))).json()
        now_available = (await client.get(f"{BASE}/availability", params={"customer_code": "ACME"}, headers=as_user("jane"))).json()
        too_high = await client.put(f"{BASE}/settings/ACME", json={"enabled": True, "daily_lookup_limit": 10001}, headers=as_user("admin"))
        unknown = await client.put(f"{BASE}/settings/NOPE", json={"enabled": True}, headers=as_user("admin"))
        return available, listed, checked, by_analyst, turned_on, again, read, now_available, too_high, unknown

    available, listed, checked, by_analyst, turned_on, again, read, now_available, too_high, unknown = call(scenario, enabled=())
    assert available["enabled"] is False and available["sources"] == []
    assert listed.status_code == 403 and checked.status_code == 403
    assert by_analyst.status_code == 401 or by_analyst.status_code == 403
    assert turned_on.status_code == 200 and turned_on.json()["settings"]["daily_lookup_limit"] == 50
    assert read["settings"]["enabled"] is True and read["connectors"] == {"virustotal": True, "opencti": True} and read["cache_hours"] == 24
    assert now_available["enabled"] is True and now_available["sources"] == ["virustotal", "opencti"]
    assert too_high.status_code == 422 and unknown.status_code == 404
    assert again.status_code == 200


def test_the_switch_change_is_audited_once():
    async def scenario(client, fake):
        await client.put(f"{BASE}/settings/GLOBEX", json={"enabled": True, "daily_lookup_limit": 5}, headers=as_user("admin"))
        await client.put(f"{BASE}/settings/GLOBEX", json={"enabled": True, "daily_lookup_limit": 5}, headers=as_user("admin"))
        return fake.audit.await_args_list

    calls = call(scenario)
    assert len(calls) == 1
    kwargs = calls[0].kwargs
    assert kwargs["action"].value == "ioc_enrichment.settings_update" and kwargs["customer_code"] == "GLOBEX"
    assert kwargs["old_value"] == {"enabled": False, "daily_lookup_limit": None}
    assert kwargs["new_value"] == {"enabled": True, "daily_lookup_limit": 5}


def test_switched_on_without_a_verified_source_is_not_offered():
    async def scenario(client, fake):
        available = (await client.get(f"{BASE}/availability", params={"customer_code": "ACME"}, headers=as_user("jane"))).json()
        settings = (await client.get(f"{BASE}/settings/ACME", headers=as_user("admin"))).json()
        listed = (await client.get(f"{BASE}/alert/{fake.ids['alert']}", headers=as_user("jane"))).json()
        checked = (await check(client, fake.ids["alert"], fake.ids["ip"])).json()
        return available, settings, listed, checked, fake

    available, settings, listed, checked, fake = call(scenario, vt=False, opencti=False)
    assert available["enabled"] is False and available["sources"] == []
    assert settings["connectors"] == {"virustotal": False, "opencti": False}
    assert {r["status"] for r in listed["iocs"][0]["sources"]} == {"not_configured"}
    assert checked["ioc"]["can_check"] is False and fake.vt_requests == [] and fake.opencti_calls == []


def test_availability_for_a_customer_the_caller_does_not_have_is_refused():
    async def scenario(client, fake):
        return await client.get(f"{BASE}/availability", params={"customer_code": "GLOBEX"}, headers=as_user("jane"))

    assert call(scenario, enabled=("ACME", "GLOBEX")).status_code == 403


# ── reading and checking ──────────────────────────────────────────────────────


def test_reading_an_alert_asks_no_source():
    async def scenario(client, fake):
        vt_ip(fake)
        listed = await client.get(f"{BASE}/alert/{fake.ids['alert']}", headers=as_user("jane"))
        return listed.json(), fake

    listed, fake = call(scenario)
    assert fake.vt_requests == [] and fake.opencti_calls == []
    iocs = {ioc["value"]: ioc for ioc in listed["iocs"]}
    assert listed["sources"] == ["virustotal", "opencti"]
    assert set(iocs) == {EVIL_IP, EVIL_HASH, "10.20.30.40", "ceo@example-corp.com", "https://bad.example.net/login?x=1"}
    ip = iocs[EVIL_IP]
    assert ip["kind"] == "ip" and ip["verdict"] is None and ip["can_check"] is True and ip["checked_at"] is None
    assert {s: r["status"] for s, r in by_source(ip).items()} == {"virustotal": "not_checked", "opencti": "not_checked"}
    private = iocs["10.20.30.40"]
    assert private["kind"] == "internal" and private["can_check"] is False
    assert {r["status"] for r in private["sources"]} == {"internal"}
    email = iocs["ceo@example-corp.com"]
    assert email["kind"] == "other" and by_source(email)["virustotal"]["status"] == "unsupported"
    assert by_source(email)["opencti"]["status"] == "not_checked"


def test_checking_asks_each_source_once_then_answers_from_the_cache():
    async def scenario(client, fake):
        vt_ip(fake)
        first = await check(client, fake.ids["alert"], fake.ids["ip"])
        second = await check(client, fake.ids["alert"], fake.ids["ip"])
        listed = (await client.get(f"{BASE}/alert/{fake.ids['alert']}", headers=as_user("jane"))).json()
        cached = await rows(fake.db, CustomerPortalIocEnrichment)
        lookups = await rows(fake.db, CustomerPortalIocLookup)
        return first, second, listed, cached, lookups, fake

    first, second, listed, cached, lookups, fake = call(scenario)
    assert first.status_code == 200, first.text
    ioc = first.json()["ioc"]
    assert len(fake.vt_requests) == 1 and len(fake.opencti_calls) == 1
    assert ioc["verdict"] == "malicious" and ioc["can_check"] is False and ioc["next_check_at"]
    vt, cti = by_source(ioc)["virustotal"], by_source(ioc)["opencti"]
    assert vt["status"] == "found" and vt["verdict"] == "malicious"
    assert vt["virustotal"]["malicious"] == 7 and vt["virustotal"]["engines"] == 94 and vt["virustotal"]["reputation"] == -42
    assert vt["virustotal"]["tags"] == ["scanner", "badname"] and vt["virustotal"]["country"] == "NL"
    assert vt["virustotal"]["link"] == f"https://www.virustotal.com/gui/ip-address/{EVIL_IP}"
    assert vt["virustotal"]["last_analysis_at"] == "2025-10-28T08:00:00Z"
    assert "whois" not in str(vt)
    # OpenCTI: the TLP:RED indicator and the AMBER+STRICT report are withheld, and only their count shows.
    assert cti["verdict"] == "malicious" and cti["opencti"]["score"] == 85
    assert [i["name"] for i in cti["opencti"]["indicators"]] == ["Botnet C2"]
    assert [r["name"] for r in cti["opencti"]["reports"]] == ["Q3 botnet review"]
    assert cti["opencti"]["withheld"] == 2 and cti["opencti"]["labels"] == ["botnet"]
    assert "Secret feed" not in first.text and "Partner only" not in first.text
    # The second check and the alert's list read the cache.
    assert second.json()["ioc"] == ioc
    assert {i["ioc_id"]: i for i in listed["iocs"]}[ioc["ioc_id"]]["verdict"] == "malicious"
    assert {(row.customer_code, row.source, row.status) for row in cached} == {
        ("ACME", "virustotal", "found"),
        ("ACME", "opencti", "found"),
    }
    assert len(lookups) == 1 and lookups[0].completed_at is not None and lookups[0].requested_by_user_id == 10
    # VirusTotal is only ever read.
    assert {r.method for r in fake.vt_requests} == {"GET"}
    assert fake.vt_requests[0].headers["x-apikey"] == "vt-key"
    audit = fake.audit.await_args.kwargs
    assert audit["action"].value == "ioc_enrichment.lookup" and audit["entity_id"] == ioc["ioc_id"]
    assert audit["new_value"] == {"alert_id": listed["alert_id"], "value": EVIL_IP, "sources": {"virustotal": "found", "opencti": "found"}}


def test_a_stale_answer_is_asked_again():
    async def scenario(client, fake):
        vt_ip(fake)
        await check(client, fake.ids["alert"], fake.ids["ip"])
        async with fake.db.session() as s:
            for row in (await s.execute(select(CustomerPortalIocEnrichment))).scalars().all():
                row.checked_at = now_utc().replace(tzinfo=None) - service.CACHE_TTL - timedelta(minutes=1)
            await s.commit()
        listed = (await client.get(f"{BASE}/alert/{fake.ids['alert']}", headers=as_user("jane"))).json()
        again = (await check(client, fake.ids["alert"], fake.ids["ip"])).json()
        return listed, again, fake

    listed, again, fake = call(scenario)
    stale = {i["value"]: i for i in listed["iocs"]}[EVIL_IP]
    assert stale["can_check"] is True and stale["verdict"] == "malicious" and stale["next_check_at"] is None
    assert len(fake.vt_requests) == 2 and len(fake.opencti_calls) == 2
    assert again["ioc"]["can_check"] is False


def test_hash_and_url_go_to_virustotal_by_get_and_the_url_by_its_identifier():
    async def scenario(client, fake):
        await check(client, fake.ids["alert"], fake.ids["hash"])
        await check(client, fake.ids["alert"], fake.ids["url"])
        return fake

    fake = call(scenario)
    url_id = base64.urlsafe_b64encode(b"https://bad.example.net/login?x=1").decode().rstrip("=")
    assert [r.url.path for r in fake.vt_requests] == [f"/api/v3/files/{EVIL_HASH.lower()}", f"/api/v3/urls/{url_id}"]
    assert {r.method for r in fake.vt_requests} == {"GET"}
    assert fake.opencti_calls[0]["filters"]["filters"][0]["values"] == [EVIL_HASH.lower()]


def test_a_private_address_goes_nowhere_and_an_email_only_to_opencti():
    async def scenario(client, fake):
        fake.opencti_answer = {"stixCyberObservables": {"edges": []}}
        private = (await check(client, fake.ids["alert"], fake.ids["private"])).json()
        email = (await check(client, fake.ids["alert"], fake.ids["email"])).json()
        lookups = await rows(fake.db, CustomerPortalIocLookup)
        return private, email, lookups, fake

    private, email, lookups, fake = call(scenario)
    assert fake.vt_requests == [] and len(fake.opencti_calls) == 1
    assert private["ioc"]["can_check"] is False and {r["status"] for r in private["ioc"]["sources"]} == {"internal"}
    assert by_source(email["ioc"])["virustotal"]["status"] == "unsupported"
    assert by_source(email["ioc"])["opencti"]["status"] == "not_found"
    assert fake.opencti_calls[0]["filters"]["filters"][0]["values"] == ["ceo@example-corp.com"]
    assert len(lookups) == 1


def test_not_found_is_cached_and_reads_as_not_found():
    async def scenario(client, fake):
        fake.opencti_answer = {"stixCyberObservables": {"edges": []}}
        checked = (await check(client, fake.ids["alert"], fake.ids["ip"])).json()
        cached = await rows(fake.db, CustomerPortalIocEnrichment)
        return checked, cached

    checked, cached = call(scenario)
    assert checked["ioc"]["verdict"] == "not_found"
    assert {r["status"] for r in checked["ioc"]["sources"]} == {"not_found"}
    assert {row.status for row in cached} == {"not_found"} and len(cached) == 2


def test_an_observable_marked_red_is_as_good_as_not_found():
    async def scenario(client, fake):
        vt_ip(fake)
        node = dict(OPENCTI_FOUND["stixCyberObservables"]["edges"][0]["node"], objectMarking=[{"definition": "TLP:RED"}])
        fake.opencti_answer = {"stixCyberObservables": {"edges": [{"node": node}]}}
        return (await check(client, fake.ids["alert"], fake.ids["ip"])).json()

    checked = call(scenario)
    assert by_source(checked["ioc"])["opencti"]["status"] == "not_found"
    assert "botnet" not in str(by_source(checked["ioc"])["opencti"])


# ── who may ───────────────────────────────────────────────────────────────────


def test_only_an_ioc_on_one_of_the_callers_alerts():
    async def scenario(client, fake):
        not_on_alert = await check(client, fake.ids["alert"], fake.ids["other_ip"])
        other_customer = await check(client, fake.ids["globex"], fake.ids["globex_ip"])
        other_list = await client.get(f"{BASE}/alert/{fake.ids['globex']}", headers=as_user("jane"))
        missing = await check(client, 999999, fake.ids["ip"])
        by_analyst = await check(client, fake.ids["alert"], fake.ids["ip"], user="ana")
        by_analyst_list = await client.get(f"{BASE}/alert/{fake.ids['alert']}", headers=as_user("ana"))
        return not_on_alert, other_customer, other_list, missing, by_analyst, by_analyst_list, fake

    not_on_alert, other_customer, other_list, missing, by_analyst, by_analyst_list, fake = call(scenario, enabled=("ACME", "GLOBEX"))
    assert not_on_alert.status_code == 404 and not_on_alert.json()["detail"] == service.NOT_ON_ALERT
    assert other_customer.status_code == 403 and other_list.status_code == 403
    assert missing.status_code == 404
    assert by_analyst.status_code in (401, 403) and by_analyst_list.status_code in (401, 403)
    assert fake.vt_requests == [] and fake.opencti_calls == []


def test_the_cache_is_per_customer():
    async def scenario(client, fake):
        vt_ip(fake)
        await check(client, fake.ids["alert"], fake.ids["ip"])
        globex = (await client.get(f"{BASE}/alert/{fake.ids['globex']}", headers=as_user("gus"))).json()
        checked = (await check(client, fake.ids["globex"], fake.ids["globex_ip"], user="gus")).json()
        cached = await rows(fake.db, CustomerPortalIocEnrichment)
        return globex, checked, cached, fake

    globex, checked, cached, fake = call(scenario, enabled=("ACME", "GLOBEX"))
    assert globex["iocs"][0]["verdict"] is None and globex["iocs"][0]["checked_at"] is None
    assert checked["ioc"]["verdict"] == "malicious" and len(fake.vt_requests) == 2
    assert sorted({row.customer_code for row in cached}) == ["ACME", "GLOBEX"] and len(cached) == 4


def test_a_read_only_user_may_check():
    async def scenario(client, fake):
        vt_ip(fake)
        return await check(client, fake.ids["alert"], fake.ids["ip"], user="reader")

    assert call(scenario).status_code == 200


# ── limits and failures ───────────────────────────────────────────────────────


def test_the_daily_limit_counts_lookups_that_reached_a_source():
    async def scenario(client, fake):
        vt_ip(fake)
        first = await check(client, fake.ids["alert"], fake.ids["ip"])
        cached = await check(client, fake.ids["alert"], fake.ids["ip"])
        private = await check(client, fake.ids["alert"], fake.ids["private"])
        over = await check(client, fake.ids["alert"], fake.ids["hash"])
        return first, cached, private, over, fake

    first, cached, private, over, fake = call(scenario, limit=1)
    assert first.status_code == 200 and cached.status_code == 200 and private.status_code == 200
    assert over.status_code == 429 and over.json()["detail"] == service.LIMIT_REACHED
    assert len(fake.vt_requests) == 1


def test_a_lookup_still_running_is_refused():
    async def scenario(client, fake):
        digest = service.value_digest(EVIL_IP)
        async with fake.db.session() as s:
            s.add(CustomerPortalIocLookup(customer_code="ACME", value_sha256=digest, requested_at=now_utc().replace(tzinfo=None)))
            await s.commit()
        running = await check(client, fake.ids["alert"], fake.ids["ip"])
        async with fake.db.session() as s:
            row = (await s.execute(select(CustomerPortalIocLookup))).scalars().first()
            row.requested_at = row.requested_at - service.IN_PROGRESS - timedelta(seconds=1)
            await s.commit()
        dead = await check(client, fake.ids["alert"], fake.ids["ip"])
        return running, dead

    running, dead = call(scenario)
    assert running.status_code == 409 and running.json()["detail"] == service.BEING_CHECKED
    assert dead.status_code == 200


def test_a_lookup_no_source_answered_costs_nothing():
    async def scenario(client, fake):
        vt_ip(fake, body={"error": "boom"}, status=500)
        fake.opencti_ok = False
        failed = await check(client, fake.ids["alert"], fake.ids["ip"])
        cached = await rows(fake.db, CustomerPortalIocEnrichment)
        lookups = await rows(fake.db, CustomerPortalIocLookup)
        vt_ip(fake)
        fake.opencti_ok = True
        retried = await check(client, fake.ids["alert"], fake.ids["ip"])
        return failed, cached, lookups, retried, fake

    failed, cached, lookups, retried, fake = call(scenario, limit=1)
    assert failed.status_code == 200
    ioc = failed.json()["ioc"]
    assert {(r["status"], r["error"]) for r in ioc["sources"]} == {("error", "unavailable")}
    assert ioc["can_check"] is True and ioc["verdict"] is None
    assert "boom" not in failed.text and "opencti.internal" not in failed.text
    assert cached == [] and lookups == []
    assert fake.audit.await_args_list[0].kwargs["result"].value == "failure"
    # The limit of one was not spent by the failure.
    assert retried.status_code == 200 and retried.json()["ioc"]["verdict"] == "malicious"


def test_a_virustotal_rate_limit_is_its_own_error_and_opencti_still_answers():
    async def scenario(client, fake):
        vt_ip(fake, body={"error": {"code": "QuotaExceededError"}}, status=429)
        checked = (await check(client, fake.ids["alert"], fake.ids["ip"])).json()
        cached = await rows(fake.db, CustomerPortalIocEnrichment)
        return checked, cached

    checked, cached = call(scenario)
    vt, cti = by_source(checked["ioc"])["virustotal"], by_source(checked["ioc"])["opencti"]
    assert vt["status"] == "error" and vt["error"] == "rate_limited"
    assert cti["status"] == "found" and checked["ioc"]["verdict"] == "malicious"
    assert checked["ioc"]["can_check"] is True  # VirusTotal still has no answer
    assert [row.source for row in cached] == ["opencti"]


@pytest.mark.parametrize(
    "response",
    [
        lambda: httpx.Response(200, headers={"content-encoding": "gzip"}, content=gzip.compress(json.dumps(VT_IP).encode())),
        lambda: httpx.Response(200, content=b"{" + b" " * (sources.MAX_VIRUSTOTAL_BYTES + 1) + b"}"),
        lambda: httpx.Response(200, content=b"not json"),
        lambda: httpx.Response(401, json={"error": {"code": "WrongCredentialsError", "message": "key vt-key is wrong"}}),
    ],
    ids=["encoded", "too-large", "not-json", "key-refused"],
)
def test_an_unusable_virustotal_answer_is_unavailable(response):
    async def scenario(client, fake):
        fake.vt_answers[f"/api/v3/ip_addresses/{EVIL_IP}"] = response()
        checked = await check(client, fake.ids["alert"], fake.ids["ip"])
        return checked

    checked = call(scenario)
    vt = by_source(checked.json()["ioc"])["virustotal"]
    assert vt["status"] == "error" and vt["error"] == "unavailable"
    assert "WrongCredentials" not in checked.text and "vt-key" not in checked.text


def test_a_failed_refresh_keeps_the_older_answer_beside_the_error():
    async def scenario(client, fake):
        vt_ip(fake)
        await check(client, fake.ids["alert"], fake.ids["ip"])
        async with fake.db.session() as s:
            for row in (await s.execute(select(CustomerPortalIocEnrichment))).scalars().all():
                row.checked_at = now_utc().replace(tzinfo=None) - service.CACHE_TTL - timedelta(hours=1)
            await s.commit()
        vt_ip(fake, body={}, status=503)
        fake.opencti_ok = False
        return (await check(client, fake.ids["alert"], fake.ids["ip"])).json()

    checked = call(scenario)
    vt = by_source(checked["ioc"])["virustotal"]
    assert vt["status"] == "found" and vt["verdict"] == "malicious" and vt["error"] == "unavailable"
    assert checked["ioc"]["can_check"] is True


# ── the pure rules ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "value,kind,normalized",
    [
        (" 45.155.205.233 ", "ip", "45.155.205.233"),
        ("2001:4860:4860:0:0:0:0:8888", "ip", "2001:4860:4860::8888"),
        ("10.0.0.1", "internal", "10.0.0.1"),
        ("192.168.1.10", "internal", "192.168.1.10"),
        ("127.0.0.1", "internal", "127.0.0.1"),
        ("169.254.1.1", "internal", "169.254.1.1"),
        ("fe80::1", "internal", "fe80::1"),
        ("224.0.0.1", "internal", "224.0.0.1"),
        (EVIL_HASH, "hash", EVIL_HASH.lower()),
        ("a" * 40, "hash", "a" * 40),
        ("B" * 64, "hash", "b" * 64),
        ("Evil.Example.COM.", "domain", "evil.example.com"),
        ("xn--80ak6aa92e.com", "domain", "xn--80ak6aa92e.com"),
        ("dc01.acme.local", "internal", "dc01.acme.local"),
        ("files.corp", "internal", "files.corp"),
        ("https://bad.example.net/a?b=1", "url", "https://bad.example.net/a?b=1"),
        ("http://10.1.2.3/payload", "internal", "http://10.1.2.3/payload"),
        ("http://intranet/login", "internal", "http://intranet/login"),
        ("http://wiki.acme.lan/", "internal", "http://wiki.acme.lan/"),
        ("ceo@example.com", "other", "ceo@example.com"),
        ("srv01", "other", "srv01"),
        ("invoice.pdf.exe", "other", "invoice.pdf.exe"),
        ("Q3 layoffs.xlsx", "other", "Q3 layoffs.xlsx"),
        ("payload.docx", "other", "payload.docx"),
        ("", "invalid", ""),
        ("evil‮.com", "invalid", "evil‮.com"),
        ("x" * 2049, "invalid", "x" * 2049),
    ],
)
def test_classify(value, kind, normalized):
    assert sources.classify(value) == (kind, normalized)


def test_which_source_may_be_asked():
    assert [k for k in ("ip", "domain", "url", "hash", "other", "internal", "invalid") if sources.applicable("virustotal", k)] == [
        "ip",
        "domain",
        "url",
        "hash",
    ]
    assert [k for k in ("ip", "domain", "url", "hash", "other", "internal", "invalid") if sources.applicable("opencti", k)] == [
        "ip",
        "domain",
        "url",
        "hash",
        "other",
    ]


def test_virustotal_paths():
    assert sources.virustotal_path("ip", "8.8.8.8") == "/ip_addresses/8.8.8.8"
    assert sources.virustotal_path("domain", "example.com") == "/domains/example.com"
    assert sources.virustotal_path("hash", "ab" * 16) == "/files/" + "ab" * 16
    assert sources.virustotal_path("url", "http://a.example/") == "/urls/aHR0cDovL2EuZXhhbXBsZS8"


@pytest.mark.parametrize(
    "stats,verdict",
    [
        ({}, "unknown"),
        ({"malicious": 0, "suspicious": 0, "harmless": 70, "undetected": 20}, "clean"),
        ({"malicious": 1, "harmless": 80}, "suspicious"),
        ({"malicious": 2, "harmless": 80}, "suspicious"),
        ({"suspicious": 1, "harmless": 80}, "suspicious"),
        ({"malicious": 3, "harmless": 80}, "malicious"),
    ],
)
def test_virustotal_verdict(stats, verdict):
    details = sources.project_virustotal({"data": {"id": "x", "type": "domain", "attributes": {"last_analysis_stats": stats}}})
    assert sources.virustotal_verdict(details) == verdict


def test_virustotal_projection_is_bounded_and_clean():
    attributes = {
        "last_analysis_stats": {"malicious": "7", "harmless": True, "undetected": -3, "timeout": 2},
        "tags": [f"t{i}" for i in range(30)] + [None, "\u0000"],
        "country": "Netherlands",
        "as_owner": "x" * 500,
        "reputation": "bad",
        "last_analysis_date": "yesterday",
    }
    details = sources.project_virustotal({"data": {"id": "../../evil", "type": "domain", "attributes": attributes}})
    assert details.malicious == 0 and details.harmless == 0 and details.undetected == 0 and details.engines == 2
    assert details.tags == [f"t{i}" for i in range(10)]
    assert details.country is None and details.link is None and details.reputation is None and details.last_analysis_at is None
    assert len(details.as_owner) == 128 and details.as_owner.endswith("…")
    assert sources.project_virustotal({"data": "nope"}) is None and sources.project_virustotal([]) is None


@pytest.mark.parametrize(
    "markings,ok",
    [
        ([], True),
        (["TLP:CLEAR"], True),
        (["TLP:WHITE"], True),
        (["tlp:green"], True),
        (["TLP:AMBER", "PAP:GREEN"], True),
        (["TLP:AMBER+STRICT"], False),
        (["TLP:RED"], False),
        (["TLP:GREEN", "Statement: partners only"], False),
    ],
)
def test_shareable_markings(markings, ok):
    assert sources.shareable(markings) is ok


@pytest.mark.parametrize(
    "score,verdict",
    [(None, "known"), (0, "known"), (39, "known"), (40, "suspicious"), (69, "suspicious"), (70, "malicious")],
)
def test_opencti_verdict(score, verdict):
    assert sources.opencti_verdict(score) == verdict


def test_opencti_projection_ignores_revoked_scores_and_bad_values():
    data = {
        "stixCyberObservables": {
            "edges": [
                {
                    "node": {
                        "entity_type": "Domain-Name",
                        "x_opencti_score": 150,
                        "objectMarking": [],
                        "indicators": {"edges": [{"node": {"name": "old", "x_opencti_score": 95, "revoked": True, "objectMarking": []}}]},
                        "reports": {"edges": [{"node": {"name": "r", "published": "not a date", "objectMarking": []}}]},
                    },
                },
            ],
        },
    }
    details = sources.project_opencti(data)
    assert details.score is None and details.indicators[0].revoked is True and details.reports[0].published is None
    assert sources.project_opencti({"stixCyberObservables": {"edges": []}}) is None
    assert sources.project_opencti(None) is None


def test_refusals_in_order():
    on = CustomerPortalIocEnrichmentSettings(customer_code="ACME", enabled=True, daily_lookup_limit=2)
    off = CustomerPortalIocEnrichmentSettings(customer_code="ACME", enabled=False)
    assert service.refusal(None, False, 0).status_code == 403
    assert service.refusal(off, True, 99).status_code == 403
    assert service.refusal(on, True, 99).status_code == 409
    assert service.refusal(on, False, 2).status_code == 429
    assert service.refusal(on, False, 1) is None
    unlimited = CustomerPortalIocEnrichmentSettings(customer_code="ACME", enabled=True, daily_lookup_limit=None)
    assert service.refusal(unlimited, False, 10**6) is None


def test_build_enrichment_takes_the_worst_verdict_and_says_when_to_check_again():
    now = now_utc().replace(tzinfo=None)
    ioc = IoC(id=1, value="evil.example.com", type="DOMAIN")
    vt = CustomerPortalIocEnrichment(
        customer_code="ACME",
        value_sha256="x",
        value="evil.example.com",
        source="virustotal",
        status="found",
        verdict="clean",
        details=VirusTotalDetails(harmless=80, engines=80).model_dump(),
        checked_at=now - timedelta(hours=2),
    )
    cti = CustomerPortalIocEnrichment(
        customer_code="ACME",
        value_sha256="x",
        value="evil.example.com",
        source="opencti",
        status="found",
        verdict="suspicious",
        details=OpenCtiDetails(score=50).model_dump(),
        checked_at=now - timedelta(hours=1),
    )
    result = service.build_enrichment(ioc, {"virustotal": vt, "opencti": cti}, ["virustotal", "opencti"], now)
    assert result.verdict == "suspicious" and result.can_check is False
    assert result.checked_at == (now - timedelta(hours=1)).replace(microsecond=0).isoformat() + "Z"
    assert result.next_check_at == (now - timedelta(hours=2) + service.CACHE_TTL).replace(microsecond=0).isoformat() + "Z"
    # A row a later version cannot read shows no details, but keeps its status.
    vt.details = {"malicious": "lots"}
    broken = service.build_enrichment(ioc, {"virustotal": vt}, ["virustotal"], now)
    assert by_source(broken.model_dump())["virustotal"]["virustotal"] is None
    assert by_source(broken.model_dump())["opencti"]["status"] == "not_configured"
