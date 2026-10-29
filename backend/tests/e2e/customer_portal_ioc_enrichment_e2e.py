"""E2E for #1318 (Threat Intel enrichment of a customer's IOCs in the Customer Portal) — NOT
collected by pytest (needs a live MySQL); run by hand.

The disposable MySQL on 13306 and the seed of customer_portal_overview_e2e.py (see its
docstring), then:

    .venv/bin/python tests/e2e/customer_portal_ioc_enrichment_e2e.py

Real routers, real JWTs, real SQL, and the real VirusTotal and OpenCTI clients, pointed by their
connector rows at a fake of both on localhost (no other network): the rows are created for the
run and removed after it. It checks, on the routes a browser calls:

  A) the migration: the three tables, the cache's unique key, the cascades from customers;
  B) the switch: off by default (403), admin only to change (audited), an analyst reads it with
     the connectors' state; availability needs a verified source;
  C) reading an alert's IOCs asks no source;
  D) checking one: VirusTotal by GET (the URL by its identifier), OpenCTI by GraphQL with the
     value in the variables; verdicts, the TLP filter, the cache rows, the audit row; a second
     check and the list come from the cache;
  E) the cache is per customer: customer B starts from nothing for the same value;
  F) private addresses and names reach no source; an e-mail reaches OpenCTI only;
  G) two checks of the same IOC at once: one lookup; two users racing for the last lookup of
     the day: exactly one wins; a cached answer costs nothing;
  H) failures: VirusTotal's 429, OpenCTI down, both down (nothing cached, nothing counted);
  I) refusals: another customer's alert, an IOC not on the alert, the SOC on the portal routes;
  J) the migration downgrades and upgrades again.

Exits non-zero when a check fails.
"""

import asyncio
import base64
import json
import os
import sys

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import or_  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy import update  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.audit.models.audit import AuditLog  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.connectors import cache as connector_cache  # noqa: E402
from app.connectors.models import Connectors  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import CustomerPortalIocEnrichment  # noqa: E402
from app.db.universal_models import CustomerPortalIocEnrichmentSettings  # noqa: E402
from app.db.universal_models import CustomerPortalIocLookup  # noqa: E402
from app.incidents.models import Alert  # noqa: E402
from app.incidents.models import AlertToIoC  # noqa: E402
from app.incidents.models import IoC  # noqa: E402
from app.middleware.exception_handlers import (  # noqa: E402
    custom_http_exception_handler,
)
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_B  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402

results = []
PREFIX = "e2e_ti_"
JANE = f"{PREFIX}jane"
BOB = f"{PREFIX}bob"
BETA = f"{PREFIX}beta"
ANALYST_A = f"{PREFIX}ana"
PASSWORD = "Threat-Intel-2026!x"
PREVIOUS = "f1312a0b1c2d"
BASE = "/customer_portal/ioc_enrichment"
IOC_DESCRIPTION = f"{PREFIX}ioc"
TABLES = ("customer_portal_ioc_enrichment_settings", "customer_portal_ioc_enrichment", "customer_portal_ioc_lookup")
CONNECTORS = ("VirusTotal", "OpenCTI")

EVIL_IP = "45.155.205.233"
SLOW_IP = "185.220.101.7"
EVIL_URL = "https://login.bad-example.net/office?u=1"
VT_IP = {
    "data": {
        "id": EVIL_IP,
        "type": "ip_address",
        "attributes": {
            "last_analysis_stats": {"malicious": 9, "suspicious": 0, "harmless": 61, "undetected": 24},
            "reputation": -55,
            "last_analysis_date": 1761638400,
            "tags": ["scanner"],
            "country": "NL",
            "as_owner": "Example Hosting",
            "whois": "never shown",
        },
    },
}


def opencti_node(value, marking="TLP:GREEN", indicators=(), reports=()):
    return {
        "node": {
            "entity_type": "IPv4-Addr",
            "observable_value": value,
            "x_opencti_score": 30,
            "objectLabel": [{"value": "botnet"}],
            "objectMarking": [{"definition": marking}] if marking else [],
            "indicators": {"edges": [{"node": node} for node in indicators]},
            "reports": {"edges": [{"node": node} for node in reports]},
        },
    }


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not passed else ""))


def session():
    return AsyncSession(async_engine)


def build_app():
    from app.routers import auth
    from app.routers import customer_portal

    app = FastAPI()
    for module in (auth, customer_portal):
        app.include_router(module.router)
    app.add_exception_handler(HTTPException, custom_http_exception_handler)
    return app


class FakeThreatIntel:
    """VirusTotal's v3 GET API and OpenCTI's GraphQL endpoint on one localhost port, recording every request."""

    def __init__(self):
        self.requests = []  # (method, path, headers, body)
        self.vt = {}  # path → (status, body, delay)
        self.opencti = {}  # value → list of edges
        self.opencti_status = 200
        self.server = None

    async def start(self) -> str:
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        return f"http://127.0.0.1:{self.server.sockets[0].getsockname()[1]}"

    def calls(self, kind):
        return [r for r in self.requests if (r[1].startswith("/api/v3/") if kind == "vt" else r[1] == "/graphql")]

    async def _handle(self, reader, writer):
        try:
            head = await reader.readuntil(b"\r\n\r\n")
            lines = head.decode("latin-1").split("\r\n")
            method, path, _ = lines[0].split(" ", 2)
            headers = {k.strip().lower(): v.strip() for k, v in (line.split(":", 1) for line in lines[1:] if ":" in line)}
            body = await reader.readexactly(int(headers.get("content-length", "0")))
            self.requests.append((method, path, headers, body))
            status, payload, delay = 404, {"error": {"code": "NotFoundError"}}, 0
            if path == "/graphql" and method == "POST":
                value = json.loads(body)["variables"]["filters"]["filters"][0]["values"][0]
                status = self.opencti_status
                payload = (
                    {"data": {"stixCyberObservables": {"edges": self.opencti.get(value, [])}}}
                    if status == 200
                    else {"errors": [{"message": "down"}]}
                )
            elif path in self.vt:
                status, payload, delay = self.vt[path]
            if delay:
                await asyncio.sleep(delay)
            raw = json.dumps(payload).encode()
            writer.write(
                f"HTTP/1.1 {status} X\r\nContent-Type: application/json\r\nContent-Length: {len(raw)}\r\nConnection: close\r\n\r\n".encode()
                + raw,
            )
            await writer.drain()
        finally:
            writer.close()

    async def stop(self):
        self.server.close()
        await self.server.wait_closed()


async def set_connectors(base_url: str, verified: bool = True) -> None:
    async with session() as s:
        for name in CONNECTORS:
            url = f"{base_url}/api/v3" if name == "VirusTotal" else base_url
            row = (await s.execute(select(Connectors).where(Connectors.connector_name == name))).scalars().first()
            if row is None:
                row = Connectors(connector_name=name, connector_type="3", connector_url=url, connector_description=f"{PREFIX}connector")
                s.add(row)
            row.connector_url, row.connector_api_key, row.connector_verified, row.connector_configured = url, f"{PREFIX}key", verified, True
        await s.commit()
    for name in CONNECTORS:
        connector_cache.invalidate(name)


async def cleanup() -> None:
    async with session() as s:
        ids = [row[0] for row in (await s.execute(select(User.id).where(User.username.like(f"{PREFIX}%")))).all()]
        if ids:
            await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id.in_(ids)))
            await s.execute(delete(User).where(User.id.in_(ids)))
        ioc_ids = (await s.execute(select(IoC.id).where(IoC.description == IOC_DESCRIPTION))).scalars().all()
        if ioc_ids:
            await s.execute(delete(AlertToIoC).where(AlertToIoC.ioc_id.in_(ioc_ids)))
            await s.execute(delete(IoC).where(IoC.id.in_(ioc_ids)))
        names = {row[0] for row in (await s.execute(text("SHOW TABLES LIKE 'customer_portal_ioc_%'"))).all()}
        for model in (CustomerPortalIocEnrichment, CustomerPortalIocLookup, CustomerPortalIocEnrichmentSettings):
            if model.__tablename__ in names:
                await s.execute(delete(model).where(model.customer_code.in_([CUST_A, CUST_B])))
        await s.execute(
            delete(AuditLog).where(
                or_(
                    AuditLog.actor_username.like(f"{PREFIX}%"),
                    AuditLog.action.in_(["ioc_enrichment.settings_update", "ioc_enrichment.lookup"]),
                ),
            ),
        )
        await s.execute(delete(Connectors).where(Connectors.connector_description == f"{PREFIX}connector"))
        await s.commit()
    for name in CONNECTORS:
        connector_cache.invalidate(name)


async def alembic(target: str) -> None:
    from alembic import command
    from alembic.config import Config
    from app.db.db_session import SQLALCHEMY_DATABASE_URI

    config = Config("alembic/alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql"))
    await async_engine.dispose()
    await asyncio.to_thread(command.downgrade if target != "head" else command.upgrade, config, target)


async def tables_present() -> tuple:
    async with session() as s:
        names = {row[0] for row in (await s.execute(text("SHOW TABLES LIKE 'customer_portal_ioc_%'"))).all()}
    return tuple(name in names for name in TABLES)


async def add_iocs(alert_id: int, values) -> dict:
    async with session() as s:
        made = {}
        for value in values:
            ioc = IoC(value=value, type="e2e", description=IOC_DESCRIPTION)
            s.add(ioc)
            await s.flush()
            s.add(AlertToIoC(alert_id=alert_id, ioc_id=ioc.id))
            made[value] = ioc.id
        await s.commit()
        return made


def by_source(ioc: dict) -> dict:
    return {result["source"]: result for result in ioc["sources"]}


async def main():
    await alembic("head")
    await seed(quiet=True)
    await cleanup()
    fake = FakeThreatIntel()
    base_url = await fake.start()
    await set_connectors(base_url)
    admin = {"Authorization": f"Bearer {await AuthHandler().encode_token(ADMIN)}"}
    try:
        await run(fake, admin)
    finally:
        await fake.stop()
        await cleanup()

    print("\n=== J) the migration round trip ===")
    await alembic(PREVIOUS)
    check("downgrade drops the three tables", await tables_present() == (False, False, False))
    await alembic("head")
    check("upgrade brings them back", await tables_present() == (True, True, True))

    failed = [name for name, passed, _ in results if not passed]
    print("\n" + "=" * 60)
    print(f"RESULT: {len(results) - len(failed)}/{len(results)} checks passed")
    for name in failed:
        print(f"  FAILED: {name}")
    await async_engine.dispose()
    return 1 if failed else 0


async def run(fake: FakeThreatIntel, admin: dict) -> None:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e") as client:

        def bearer(token):
            return {"Authorization": f"Bearer {token}"}

        async def portal(username):
            response = await client.post("/auth/token/customer-portal", data={"username": username, "password": PASSWORD})
            return bearer(response.json()["access_token"])

        for username, role, codes in ((JANE, 4, [CUST_A]), (BOB, 4, [CUST_A]), (BETA, 4, [CUST_B]), (ANALYST_A, 2, [CUST_A])):
            created = await client.post(
                "/auth/register",
                json={
                    "username": username,
                    "password": PASSWORD,
                    "email": f"{username}@e2e.example",
                    "role_id": role,
                    "customer_codes": codes,
                },
                headers=admin,
            )
            if created.status_code != 201:
                check(f"create {username}", False, f"{created.status_code} {created.text[:200]}")
                return
        async with session() as s:
            await s.execute(update(User).where(User.username.like(f"{PREFIX}%")).values(must_change_password=False))
            await s.commit()
        jane, bob, beta = await portal(JANE), await portal(BOB), await portal(BETA)
        ana = bearer(await AuthHandler().encode_token(ANALYST_A))

        async with session() as s:
            a_alerts = (await s.execute(select(Alert.id).where(Alert.customer_code == CUST_A).order_by(Alert.id))).scalars().all()
            b_alert = (await s.execute(select(Alert.id).where(Alert.customer_code == CUST_B))).scalars().first()
        alert, second_alert = a_alerts[0], a_alerts[1]
        a = await add_iocs(
            alert,
            [EVIL_IP, EVIL_URL, "10.1.2.3", "fileserver.acme.local", "ceo@example-corp.com", SLOW_IP, "44d88612fea8a8f36de82e1278abb02f"],
        )
        racers = await add_iocs(second_alert, ["93.184.216.34", "151.101.1.69"])
        b = await add_iocs(b_alert, [EVIL_IP])

        def check_ioc(ioc_id, headers=jane, alert_id=alert):
            return client.post(f"{BASE}/alert/{alert_id}/ioc/{ioc_id}", headers=headers)

        print("\n=== A) the migration ===")
        check("the three tables exist", await tables_present() == (True, True, True))
        async with session() as s:
            rules = (
                await s.execute(
                    text(
                        "SELECT TABLE_NAME, DELETE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS "
                        "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME LIKE 'customer_portal_ioc_%'",
                    ),
                )
            ).all()
            unique = (
                (
                    await s.execute(
                        text(
                            "SELECT COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() "
                            "AND TABLE_NAME = 'customer_portal_ioc_enrichment' AND INDEX_NAME = 'uq_customer_portal_ioc_enrichment_customer_value_source' "
                            "ORDER BY SEQ_IN_INDEX",
                        ),
                    )
                )
                .scalars()
                .all()
            )
        check("every table cascades from customers", sorted(rules) == sorted((t, "CASCADE") for t in TABLES), str(rules))
        check("the cache is unique on customer, value and source", unique == ["customer_code", "value_sha256", "source"], str(unique))

        print("\n=== B) the switch ===")
        available = (await client.get(f"{BASE}/availability", headers=jane)).json()
        check("off by default", available["enabled"] is False, str(available))
        listed = await client.get(f"{BASE}/alert/{alert}", headers=jane)
        refused = await check_ioc(a[EVIL_IP])
        check("reading and checking are refused while off (403)", (listed.status_code, refused.status_code) == (403, 403))
        by_analyst = await client.put(f"{BASE}/settings/{CUST_A}", json={"enabled": True}, headers=ana)
        check("an analyst cannot turn it on", by_analyst.status_code in (401, 403), str(by_analyst.status_code))
        for code in (CUST_A, CUST_B):
            on = await client.put(f"{BASE}/settings/{code}", json={"enabled": True, "daily_lookup_limit": None}, headers=admin)
            check(f"an admin turns it on for {code}", on.status_code == 200, on.text[:200])
        read = (await client.get(f"{BASE}/settings/{CUST_A}", headers=ana)).json()
        check(
            "an analyst reads it, with both connectors verified",
            read["settings"]["enabled"] and read["connectors"] == {"virustotal": True, "opencti": True},
            str(read),
        )
        async with session() as s:
            audited = (
                (await s.execute(select(AuditLog.entity_id).where(AuditLog.action == "ioc_enrichment.settings_update"))).scalars().all()
            )
        check("audited", sorted(audited) == sorted([CUST_A, CUST_B]), str(audited))
        available = (await client.get(f"{BASE}/availability", params={"customer_code": CUST_A}, headers=jane)).json()
        check(
            "now available, from both sources",
            available["enabled"] and available["sources"] == ["virustotal", "opencti"],
            str(available),
        )

        print("\n=== C) reading asks no source ===")
        listed = (await client.get(f"{BASE}/alert/{alert}", headers=jane)).json()
        check("every IOC of the alert is listed", sorted(i["ioc_id"] for i in listed["iocs"]) == sorted(a.values()))
        check("and nothing reached a source", fake.requests == [], str(fake.requests[:2]))

        print("\n=== D) checking an IOC ===")
        fake.vt[f"/api/v3/ip_addresses/{EVIL_IP}"] = (200, VT_IP, 0)
        fake.opencti[EVIL_IP] = [
            opencti_node(
                EVIL_IP,
                indicators=[
                    {
                        "name": "C2 server",
                        "x_opencti_score": 90,
                        "valid_until": None,
                        "revoked": False,
                        "objectMarking": [{"definition": "TLP:AMBER"}],
                    },
                    {"name": "Restricted", "x_opencti_score": 100, "revoked": False, "objectMarking": [{"definition": "TLP:RED"}]},
                ],
                reports=[{"name": "Weekly botnet digest", "published": "2026-10-01T00:00:00.000Z", "objectMarking": []}],
            ),
            opencti_node(EVIL_IP, marking="TLP:RED"),
        ]
        checked = await check_ioc(a[EVIL_IP])
        ioc = checked.json().get("ioc", {})
        vt, cti = by_source(ioc).get("virustotal", {}), by_source(ioc).get("opencti", {})
        check("answered", checked.status_code == 200, checked.text[:300])
        check(
            "VirusTotal was read by GET with the connector's key",
            [(r[0], r[1], r[2].get("x-apikey")) for r in fake.calls("vt")] == [("GET", f"/api/v3/ip_addresses/{EVIL_IP}", f"{PREFIX}key")],
        )
        graphql = fake.calls("opencti")
        check(
            "OpenCTI was asked once, the value in the variables",
            len(graphql) == 1
            and EVIL_IP not in json.loads(graphql[0][3])["query"]
            and graphql[0][2].get("authorization") == f"Bearer {PREFIX}key",
        )
        check(
            "VirusTotal: malicious, 9 of 94 engines",
            (vt.get("verdict"), vt.get("virustotal", {}).get("malicious"), vt.get("virustotal", {}).get("engines")) == ("malicious", 9, 94),
            str(vt),
        )
        check(
            "OpenCTI: malicious by its live indicator's score",
            (cti.get("verdict"), cti.get("opencti", {}).get("score")) == ("malicious", 90),
            str(cti),
        )
        check(
            "what TLP:RED marks is withheld, and counted",
            "Restricted" not in checked.text
            and cti.get("opencti", {}).get("withheld") == 1
            and [r["name"] for r in cti["opencti"]["reports"]] == ["Weekly botnet digest"],
            str(cti),
        )
        check("whois is never shown", "never shown" not in checked.text)
        check(
            "the overall verdict is malicious and no check is offered",
            (ioc.get("verdict"), ioc.get("can_check")) == ("malicious", False),
        )
        async with session() as s:
            cached = (
                (await s.execute(select(CustomerPortalIocEnrichment).where(CustomerPortalIocEnrichment.customer_code == CUST_A)))
                .scalars()
                .all()
            )
            lookups = (
                (await s.execute(select(CustomerPortalIocLookup).where(CustomerPortalIocLookup.customer_code == CUST_A))).scalars().all()
            )
            audit = (await s.execute(select(AuditLog).where(AuditLog.action == "ioc_enrichment.lookup"))).scalars().all()
        check(
            "one cache row per source",
            sorted((row.source, row.status) for row in cached) == [("opencti", "found"), ("virustotal", "found")],
        )
        check("one lookup, completed", len(lookups) == 1 and lookups[0].completed_at is not None)
        check(
            "audited as the user, with the alert and the sources",
            len(audit) == 1
            and audit[0].actor_username == JANE
            and audit[0].customer_code == CUST_A
            and (audit[0].new_value or {}).get("sources") == {"virustotal": "found", "opencti": "found"}
            and (audit[0].new_value or {}).get("alert_id") == alert,
            str([(a.actor_username, a.new_value) for a in audit]),
        )
        before = len(fake.requests)
        again = await check_ioc(a[EVIL_IP], headers=bob)
        relisted = (await client.get(f"{BASE}/alert/{alert}", headers=bob)).json()
        check("a second check, by another user, comes from the cache", again.json()["ioc"] == ioc and len(fake.requests) == before)
        check("so does the list", {i["ioc_id"]: i for i in relisted["iocs"]}[a[EVIL_IP]]["verdict"] == "malicious")
        url_checked = await check_ioc(a[EVIL_URL])
        url_id = base64.urlsafe_b64encode(EVIL_URL.encode()).decode().rstrip("=")
        check(
            "a URL is read by its identifier, never submitted",
            url_checked.status_code == 200
            and [(r[0], r[1]) for r in fake.calls("vt")][-1] == ("GET", f"/api/v3/urls/{url_id}")
            and all(r[0] == "GET" for r in fake.calls("vt")),
        )
        check("not found anywhere reads as not found", url_checked.json()["ioc"]["verdict"] == "not_found", url_checked.text[:300])

        print("\n=== E) the cache is per customer ===")
        b_listed = (await client.get(f"{BASE}/alert/{b_alert}", headers=beta)).json()
        check(
            "customer B sees nothing of A's answer for the same value",
            b_listed["iocs"][0]["checked_at"] is None and b_listed["iocs"][0]["verdict"] is None,
        )
        before = len(fake.calls("vt"))
        b_checked = await check_ioc(b[EVIL_IP], headers=beta, alert_id=b_alert)
        check("and asks the sources itself", b_checked.status_code == 200 and len(fake.calls("vt")) == before + 1)

        print("\n=== F) what never leaves ===")
        before = len(fake.requests)
        for value in ("10.1.2.3", "fileserver.acme.local"):
            response = (await check_ioc(a[value])).json()["ioc"]
            check(
                f"{value} is internal and reaches no source",
                response["kind"] == "internal" and {r["status"] for r in response["sources"]} == {"internal"},
            )
        check("nothing was sent", len(fake.requests) == before)
        vt_before, cti_before = len(fake.calls("vt")), len(fake.calls("opencti"))
        email = (await check_ioc(a["ceo@example-corp.com"])).json()["ioc"]
        check(
            "an e-mail goes to OpenCTI only",
            by_source(email)["virustotal"]["status"] == "unsupported"
            and (len(fake.calls("vt")), len(fake.calls("opencti"))) == (vt_before, cti_before + 1),
        )

        print("\n=== G) races and the daily limit ===")
        fake.vt[f"/api/v3/ip_addresses/{SLOW_IP}"] = (200, VT_IP, 1.5)
        first, second = await asyncio.gather(check_ioc(a[SLOW_IP]), check_ioc(a[SLOW_IP], headers=bob))
        statuses = sorted([first.status_code, second.status_code])
        check("two checks of one IOC at once: one lookup, the other told it is running (409)", statuses == [200, 409], str(statuses))
        check("VirusTotal was asked once for it", len([r for r in fake.calls("vt") if r[1].endswith(SLOW_IP)]) == 1)
        async with session() as s:
            used = (
                (await s.execute(select(CustomerPortalIocLookup.id).where(CustomerPortalIocLookup.customer_code == CUST_A))).scalars().all()
            )
        await client.put(f"{BASE}/settings/{CUST_A}", json={"enabled": True, "daily_lookup_limit": len(used) + 1}, headers=admin)
        one, two = await asyncio.gather(
            check_ioc(racers["93.184.216.34"], alert_id=second_alert),
            check_ioc(racers["151.101.1.69"], headers=bob, alert_id=second_alert),
        )
        statuses = sorted([one.status_code, two.status_code])
        check(
            "two users racing for the last lookup: exactly one wins (200, 429)",
            statuses == [200, 429],
            f"{statuses} {one.text[:120]} {two.text[:120]}",
        )
        cached_answer = await check_ioc(a[EVIL_IP])
        check("a cached answer costs nothing, even at the limit", cached_answer.status_code == 200)
        await client.put(f"{BASE}/settings/{CUST_A}", json={"enabled": True, "daily_lookup_limit": None}, headers=admin)

        print("\n=== H) failures ===")
        rate_limited_hash = "44d88612fea8a8f36de82e1278abb02f"
        fake.vt[f"/api/v3/files/{rate_limited_hash}"] = (429, {"error": {"code": "QuotaExceededError", "message": "quota for key"}}, 0)
        fake.opencti_status = 500
        failed = await check_ioc(a[rate_limited_hash])
        sources = by_source(failed.json()["ioc"])
        check(
            "VirusTotal's 429 is rate_limited, OpenCTI down is unavailable",
            (sources["virustotal"]["error"], sources["opencti"]["error"]) == ("rate_limited", "unavailable"),
            failed.text[:300],
        )
        check("no source text reaches the portal", "Quota" not in failed.text and "quota" not in failed.text)
        async with session() as s:
            digest_rows = (
                (await s.execute(select(CustomerPortalIocEnrichment.id).where(CustomerPortalIocEnrichment.value == rate_limited_hash)))
                .scalars()
                .all()
            )
            open_lookups = (
                (
                    await s.execute(
                        select(CustomerPortalIocLookup.id).where(
                            CustomerPortalIocLookup.customer_code == CUST_A,
                            CustomerPortalIocLookup.completed_at.is_(None),
                        ),
                    )
                )
                .scalars()
                .all()
            )
        check("nothing cached, and the lookup costs nothing", digest_rows == [] and open_lookups == [], f"{digest_rows} {open_lookups}")
        fake.opencti_status = 200
        retried = await check_ioc(a[rate_limited_hash])
        check(
            "checking again asks again",
            retried.status_code == 200 and by_source(retried.json()["ioc"])["opencti"]["status"] == "not_found",
        )

        print("\n=== I) refusals ===")
        other = await check_ioc(b[EVIL_IP], alert_id=b_alert)
        check("another customer's alert (403)", other.status_code == 403, str(other.status_code))
        not_on = await check_ioc(b[EVIL_IP])
        check("an IOC not on the alert (404)", not_on.status_code == 404, str(not_on.status_code))
        soc = await check_ioc(a[EVIL_IP], headers=ana)
        soc_list = await client.get(f"{BASE}/alert/{alert}", headers=ana)
        check(
            "the SOC can't use the portal routes",
            soc.status_code in (401, 403) and soc_list.status_code in (401, 403),
            f"{soc.status_code} {soc_list.status_code}",
        )


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
