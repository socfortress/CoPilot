"""E2E for #1291 (delete a customer's unhealthy agents from the healthcheck lists) — NOT collected by
pytest (needs a live MySQL); run by hand.

The disposable MySQL on 13306 (see analyst_object_scoping_e2e.py's docstring), then:

    cd backend && PYTHONPATH=$PWD .venv/bin/python tests/e2e/healthcheck_unhealthy_delete_e2e.py

Real routers, real JWTs, real SQL, CoPilot's own exception handlers and audit writer; only the
Wazuh and Velociraptor deletions are replaced, in process, by a recorder (nothing reaches either).
It checks, on the routes a browser calls:

  A) the healthcheck list and the preview agree at the same threshold: every agent the preview may
     delete is one the list calls unhealthy (a time in the future is listed, never deleted);
  B) the preview judges each agent and changes nothing;
  C) the deletion removes only what is still deletable, from the recorder's Wazuh and Velociraptor
     and from MySQL (its data-store and vulnerability rows too), never another customer's agent, and
     writes one ``agent.delete`` audit row each, with the threshold and the actor;
  D) an agent active elsewhere is deleted only when included;
  E) a scoped analyst: another customer is a 403, their own works; the Talon service account and a
     portal user are refused;
  F) the request's rules: under 24 hours, 51 agents, an unknown list, all 422 with a reason;
  G) a real database failure (a row locked by another transaction): that agent fails and is audited
     as a failure, the next one in the same request is still deleted;
  H) 55 agents in two requests of 50 and 5, as the browser chunks them, within nginx's 60 s.

Exits non-zero when a check fails.
"""

import asyncio
import os
import sys
import time
from datetime import timedelta

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

from unittest.mock import patch  # noqa: E402

import httpx  # noqa: E402
from fastapi import APIRouter  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import func  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.agents.services import deletion  # noqa: E402
from app.audit.models.audit import AuditLog  # noqa: E402
from app.auth.models.users import Role  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.connectors.talon.services.talon_service_account import REFUSED  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import AgentDataStore  # noqa: E402
from app.db.universal_models import Agents  # noqa: E402
from app.db.universal_models import AgentVulnerabilities  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.middleware.exception_handlers import (  # noqa: E402
    custom_http_exception_handler,
)
from app.middleware.exception_handlers import validation_exception_handler  # noqa: E402
from app.time_utils import now_utc  # noqa: E402
from app.time_utils import to_naive_utc  # noqa: E402

CUST_A, CUST_B = "E2E_HDA", "E2E_HDB"
PREFIX = "e2ehd-"
# Not healthcheck_delete_seed.py's admin: the cleanup below deletes these, and the browser spec
# signs in as that one.
ADMIN, ANALYST, PORTAL = "e2e_hdx_admin", "e2e_hdx_analyst", "e2e_hdx_portal"
TALON = "talon-analyst"
PASSWORD = "E2ePassw0rd!hd"
NOW = to_naive_utc(now_utc())
BULK = [f"{PREFIX}bulk-{i:03d}" for i in range(55)]
THIRTY_DAYS = {"value": 30, "unit": "days"}

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not passed else ""))


class Recorder:
    """Stands in for Wazuh and Velociraptor: records each deletion asked of it."""

    def __init__(self):
        self.wazuh, self.velociraptor = [], []

    async def delete_wazuh(self, agent_id):
        self.wazuh.append(agent_id)

    async def delete_velociraptor(self, client_id):
        self.velociraptor.append(client_id)

    def reset(self):
        self.wazuh.clear()
        self.velociraptor.clear()


def agent(agent_id, customer, *, wazuh, velo, client=True):
    return Agents(
        agent_id=agent_id,
        ip_address="10.0.0.1",
        os="Windows",
        hostname=f"host-{agent_id}",
        label=f"label-{agent_id}",
        critical_asset=False,
        customer_code=customer,
        quarantined=False,
        velociraptor_id=f"C.{agent_id}" if client else None,
        velociraptor_org="root" if client else None,
        wazuh_last_seen=wazuh,
        velociraptor_last_seen=velo if client else None,
        wazuh_agent_version="4.9.0",
        velociraptor_agent_version="0.7.0" if client else None,
    )


async def cleanup(*, created_talon: bool):
    async with AsyncSession(async_engine) as s:
        await s.execute(delete(AuditLog).where(AuditLog.entity_id.like(f"{PREFIX}%")))
        await s.execute(delete(AgentVulnerabilities).where(AgentVulnerabilities.agent_id.like(f"{PREFIX}%")))
        await s.execute(delete(AgentDataStore).where(AgentDataStore.agent_id.like(f"{PREFIX}%")))
        await s.execute(delete(Agents).where(Agents.customer_code.in_([CUST_A, CUST_B])))
        names = [ADMIN, ANALYST, PORTAL] + ([TALON] if created_talon else [])
        ids = [row[0] for row in (await s.execute(select(User.id).where(User.username.in_(names)))).all()]
        if ids:
            await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id.in_(ids)))
            await s.execute(delete(User).where(User.id.in_(ids)))
        await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.customer_code.in_([CUST_A, CUST_B])))
        await s.execute(delete(Customers).where(Customers.customer_code.in_([CUST_A, CUST_B])))
        await s.commit()


async def seed() -> bool:
    """Seed both tenants; True when this run created the Talon service account (and must remove it)."""
    auth = AuthHandler()
    async with AsyncSession(async_engine) as s:
        for rid, name in [(1, "admin"), (2, "analyst"), (3, "scheduler"), (4, "customer_user"), (5, "responder")]:
            if not (await s.execute(select(Role).where(Role.id == rid))).scalars().first():
                s.add(Role(id=rid, name=name, description=name))
        await s.commit()

        for code in (CUST_A, CUST_B):
            s.add(
                Customers(
                    customer_code=code,
                    customer_name=f"E2E {code}",
                    contact_first_name="E2E",
                    contact_last_name="Tester",
                    phone="000",
                    address_line1="a",
                    address_line2="b",
                    city="c",
                    state="d",
                    postal_code="1",
                    country="IT",
                    customer_type="MSSP",
                    logo_file="",
                ),
            )
        await s.commit()

        old, recent = NOW - timedelta(days=40), NOW - timedelta(hours=1)
        s.add_all(
            [
                agent(f"{PREFIX}gone", CUST_A, wazuh=old, velo=old),
                agent(f"{PREFIX}wzgone", CUST_A, wazuh=old, velo=recent),
                agent(f"{PREFIX}fresh", CUST_A, wazuh=recent, velo=recent),
                agent(f"{PREFIX}novelo", CUST_A, wazuh=old, velo=None, client=False),
                agent(f"{PREFIX}future", CUST_A, wazuh=NOW + timedelta(days=1), velo=old),
                agent(f"{PREFIX}locked", CUST_A, wazuh=old, velo=old),
                agent(f"{PREFIX}after-lock", CUST_A, wazuh=old, velo=old),
                agent(f"{PREFIX}b-gone", CUST_B, wazuh=old, velo=old),
                *[agent(agent_id, CUST_A, wazuh=old, velo=old) for agent_id in BULK],
            ],
        )
        await s.commit()
        s.add(
            AgentDataStore(
                agent_id=f"{PREFIX}gone",
                velociraptor_id=f"C.{PREFIX}gone",
                artifact_name="Generic.Client.Info",
                flow_id="F.e2ehd",
                bucket_name="velociraptor-artifacts",
                object_key="e2ehd/x.json",
                file_name="x.json",
                content_type="application/json",
                file_size=1,
                file_hash="deadbeef",
                collection_time=NOW,
                uploaded_by=1,
            ),
        )
        s.add(
            AgentVulnerabilities(
                agent_id=f"{PREFIX}gone",
                customer_code=CUST_A,
                cve_id="CVE-2026-0001",
                title="e2e",
                references="",
                discovered_at=NOW,
            ),
        )

        password = auth.get_password_hash(PASSWORD)
        s.add(User(username=ADMIN, password=password, email=f"{ADMIN}@e2e.example", role_id=1))
        s.add(User(username=ANALYST, password=password, email=f"{ANALYST}@e2e.example", role_id=2))
        s.add(User(username=PORTAL, password=password, email=f"{PORTAL}@e2e.example", role_id=4))
        talon_exists = (await s.execute(select(User).where(func.lower(User.username) == TALON))).scalars().first() is not None
        if not talon_exists:
            s.add(User(username=TALON, password=password, email="talon-analyst@e2e.example", role_id=2))
        await s.commit()
        for username in (ANALYST, PORTAL) + (() if talon_exists else (TALON,)):
            user = (await s.execute(select(User).where(User.username == username))).scalars().first()
            s.add(UserCustomerAccess(user_id=user.id, customer_code=CUST_A))
        await s.commit()
    return not talon_exists


def build_app() -> FastAPI:
    from app.customers.routes.customers import customers_router

    api = APIRouter()
    api.include_router(customers_router, prefix="/customers")
    app = FastAPI()
    app.include_router(api)
    app.add_exception_handler(HTTPException, custom_http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    return app


async def remaining(*agent_ids):
    async with AsyncSession(async_engine) as s:
        rows = await s.execute(select(Agents.agent_id).where(Agents.agent_id.in_(agent_ids)))
        return sorted(rows.scalars().all())


async def audit_rows(agent_id):
    async with AsyncSession(async_engine) as s:
        rows = await s.execute(select(AuditLog).where(AuditLog.entity_id == agent_id).order_by(AuditLog.id))
        return rows.scalars().all()


def url(customer, source="wazuh", preview=False):
    return f"/customers/{customer}/agents/healthcheck/{source}/delete" + ("/preview" if preview else "")


async def main():
    await cleanup(created_talon=False)
    created_talon = await seed()
    recorder = Recorder()
    auth = AuthHandler()
    t_admin, t_analyst, t_portal, t_talon = [
        {"Authorization": f"Bearer {await auth.encode_token(name)}"} for name in (ADMIN, ANALYST, PORTAL, TALON)
    ]
    a_ids = [f"{PREFIX}{name}" for name in ("gone", "wzgone", "fresh", "novelo", "future")]

    try:
        with patch.object(deletion, "delete_agent_wazuh", recorder.delete_wazuh), patch.object(
            deletion,
            "delete_agent_velociraptor",
            recorder.delete_velociraptor,
        ):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e", timeout=120) as client:
                print("A) the list and the preview agree")
                listed = await client.get(
                    f"/customers/{CUST_A}/agents/healthcheck/wazuh",
                    params={"days": 30, "hours": 0, "minutes": 0},
                    headers=t_admin,
                )
                unhealthy = {a["agent_id"] for a in listed.json()["unhealthy_wazuh_agents"]}
                preview = await client.post(
                    url(CUST_A, preview=True),
                    json={"agent_ids": a_ids, "not_seen_for": THIRTY_DAYS},
                    headers=t_admin,
                )
                verdicts = {a["agent_id"]: a["verdict"] for a in preview.json()["agents"]}
                check("the preview answers 200", preview.status_code == 200, preview.text)
                check(
                    "every agent the preview may delete is listed unhealthy",
                    {i for i, v in verdicts.items() if v in ("deletable", "active_elsewhere")} <= unhealthy,
                    f"{verdicts} vs {unhealthy}",
                )
                check(
                    "a time in the future is listed unhealthy but never deleted",
                    f"{PREFIX}future" in unhealthy and verdicts[f"{PREFIX}future"] == "seen_recently",
                    str(verdicts),
                )
                check("a fresh agent is neither", f"{PREFIX}fresh" not in unhealthy and verdicts[f"{PREFIX}fresh"] == "seen_recently")

                print("B) the preview changes nothing")
                check(
                    "every verdict as expected",
                    verdicts
                    == {
                        f"{PREFIX}gone": "deletable",
                        f"{PREFIX}wzgone": "active_elsewhere",
                        f"{PREFIX}fresh": "seen_recently",
                        f"{PREFIX}novelo": "deletable",
                        f"{PREFIX}future": "seen_recently",
                    },
                    str(verdicts),
                )
                check("no agent deleted", await remaining(*a_ids) == sorted(a_ids))
                check("nothing asked of Wazuh or Velociraptor", recorder.wazuh == [] and recorder.velociraptor == [])

                print("C) the deletion")
                response = await client.post(
                    url(CUST_A),
                    json={"agent_ids": a_ids + [f"{PREFIX}b-gone"], "not_seen_for": THIRTY_DAYS},
                    headers=t_admin,
                )
                body = response.json()
                check("answers 200", response.status_code == 200, response.text)
                check("2 deleted, 4 skipped", (body["deleted"], body["skipped"], body["failed"]) == (2, 4, 0), body["message"])
                check(
                    "only the deletable left MySQL",
                    await remaining(*a_ids, f"{PREFIX}b-gone")
                    == sorted([f"{PREFIX}wzgone", f"{PREFIX}fresh", f"{PREFIX}future", f"{PREFIX}b-gone"]),
                )
                check(
                    "another customer's agent is not found, with no name",
                    [r for r in body["results"] if r["agent_id"] == f"{PREFIX}b-gone"]
                    == [{"agent_id": f"{PREFIX}b-gone", "hostname": None, "outcome": "skipped", "reason": "not_found", "unconfirmed": []}],
                )
                async with AsyncSession(async_engine) as s:
                    datastore = (await s.execute(select(AgentDataStore).where(AgentDataStore.agent_id == f"{PREFIX}gone"))).scalars().all()
                    vulns = (
                        (await s.execute(select(AgentVulnerabilities).where(AgentVulnerabilities.agent_id == f"{PREFIX}gone")))
                        .scalars()
                        .all()
                    )
                check("its data-store and vulnerability rows went with it", datastore == [] and vulns == [])
                check("Wazuh asked for both", recorder.wazuh == [f"{PREFIX}gone", f"{PREFIX}novelo"], str(recorder.wazuh))
                check(
                    "Velociraptor only for the one with a client",
                    recorder.velociraptor == [f"C.{PREFIX}gone"],
                    str(recorder.velociraptor),
                )
                rows = await audit_rows(f"{PREFIX}gone")
                check(
                    "one agent.delete audit row, with the actor, customer and threshold",
                    len(rows) == 1
                    and rows[0].action == "agent.delete"
                    and rows[0].result == "success"
                    and rows[0].actor_username == ADMIN
                    and rows[0].customer_code == CUST_A
                    and rows[0].new_value
                    == {"via": "healthcheck", "source": "wazuh", "not_seen_for": "30 days", "include_active_elsewhere": False}
                    and rows[0].old_value["hostname"] == f"host-{PREFIX}gone",
                    str([(r.action, r.result, r.new_value) for r in rows]),
                )
                check("no audit row for a skipped agent", await audit_rows(f"{PREFIX}wzgone") == [])

                print("D) active elsewhere, included")
                recorder.reset()
                response = await client.post(
                    url(CUST_A),
                    json={"agent_ids": [f"{PREFIX}wzgone"], "not_seen_for": THIRTY_DAYS, "include_active_elsewhere": True},
                    headers=t_admin,
                )
                check("deleted when included", response.json()["deleted"] == 1 and await remaining(f"{PREFIX}wzgone") == [], response.text)
                check(
                    "the audit row says it was included",
                    (await audit_rows(f"{PREFIX}wzgone"))[0].new_value["include_active_elsewhere"] is True,
                )

                print("E) who may")
                other = await client.post(
                    url(CUST_B),
                    json={"agent_ids": [f"{PREFIX}b-gone"], "not_seen_for": THIRTY_DAYS},
                    headers=t_analyst,
                )
                other_preview = await client.post(
                    url(CUST_B, preview=True),
                    json={"agent_ids": [f"{PREFIX}b-gone"], "not_seen_for": THIRTY_DAYS},
                    headers=t_analyst,
                )
                check("an analyst's other customer is a 403", other.status_code == 403 and other_preview.status_code == 403, other.text)
                own = await client.post(
                    url(CUST_A, preview=True),
                    json={"agent_ids": [f"{PREFIX}fresh"], "not_seen_for": THIRTY_DAYS},
                    headers=t_analyst,
                )
                check("their own customer answers", own.status_code == 200, own.text)
                talon = await client.post(url(CUST_A), json={"agent_ids": [BULK[0]], "not_seen_for": THIRTY_DAYS}, headers=t_talon)
                check(
                    "the Talon service account is refused",
                    talon.status_code == 403 and talon.json()["message"] == REFUSED,
                    talon.text,
                )
                portal = await client.post(url(CUST_A), json={"agent_ids": [BULK[0]], "not_seen_for": THIRTY_DAYS}, headers=t_portal)
                check("a portal user is refused", portal.status_code == 403, portal.text)
                check("none of them deleted anything", await remaining(f"{PREFIX}b-gone", BULK[0]) == sorted([f"{PREFIX}b-gone", BULK[0]]))

                print("F) the request's rules")
                short = await client.post(
                    url(CUST_A),
                    json={"agent_ids": [BULK[0]], "not_seen_for": {"value": 23, "unit": "hours"}},
                    headers=t_admin,
                )
                check(
                    "under 24 hours: 422 naming the rule",
                    short.status_code == 422 and "at least 24 hours" in short.json()["message"],
                    short.text,
                )
                too_many = await client.post(url(CUST_A), json={"agent_ids": BULK[:51], "not_seen_for": THIRTY_DAYS}, headers=t_admin)
                check("51 agents: 422", too_many.status_code == 422, too_many.text)
                unknown = await client.post(
                    url(CUST_A, source="graylog"),
                    json={"agent_ids": [BULK[0]], "not_seen_for": THIRTY_DAYS},
                    headers=t_admin,
                )
                check("an unknown list: 422", unknown.status_code == 422, unknown.text)
                check("none deleted", BULK[0] in await remaining(BULK[0]))

                print("G) a real database failure")
                await check_database_failure(client, t_admin)

                print("H) 55 agents in chunks of 50")
                recorder.reset()
                started = time.monotonic()
                first = await client.post(url(CUST_A), json={"agent_ids": BULK[:50], "not_seen_for": THIRTY_DAYS}, headers=t_admin)
                second = await client.post(url(CUST_A), json={"agent_ids": BULK[50:], "not_seen_for": THIRTY_DAYS}, headers=t_admin)
                elapsed = time.monotonic() - started
                check("both chunks answer 200", first.status_code == 200 and second.status_code == 200, first.text[:200])
                check("all 55 deleted", first.json()["deleted"] + second.json()["deleted"] == 55 and await remaining(*BULK) == [])
                check("55 audit rows", sum([len(await audit_rows(agent_id)) for agent_id in BULK]) == 55)
                check("within nginx's 60 s per request", elapsed < 60, f"{elapsed:.1f}s")
                print(f"       ({elapsed:.1f}s for 55 agents, the upstreams answering at once)")
    finally:
        await cleanup(created_talon=created_talon)

    failed = [name for name, passed, _ in results if not passed]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


async def check_database_failure(client, t_admin):
    """Lock one agent's row from another transaction: CoPilot's delete of it waits, times out (1 s
    for this session only), rolls back and fails; the next agent in the request is still deleted."""
    locked, after = f"{PREFIX}locked", f"{PREFIX}after-lock"
    real = deletion.delete_agent_from_database

    async def short_wait(db, agent_id):
        await db.execute(text("SET SESSION innodb_lock_wait_timeout = 1"))
        try:
            return await real(db=db, agent_id=agent_id)
        finally:
            await db.execute(text("SET SESSION innodb_lock_wait_timeout = @@GLOBAL.innodb_lock_wait_timeout"))

    async with AsyncSession(async_engine) as holder:
        row_id = (await holder.execute(select(Agents.id).where(Agents.agent_id == locked))).scalar_one()
        await holder.commit()
        await holder.execute(text("SELECT id FROM agents WHERE id = :id FOR UPDATE"), {"id": row_id})
        with patch.object(deletion, "delete_agent_from_database", short_wait):
            response = await client.post(url(CUST_A), json={"agent_ids": [locked, after], "not_seen_for": THIRTY_DAYS}, headers=t_admin)
        await holder.rollback()

    body = response.json()
    check("answers 200 with success false", response.status_code == 200 and body["success"] is False, response.text)
    check(
        "the locked agent failed, the next one was deleted",
        [(r["agent_id"], r["outcome"]) for r in body["results"]] == [(locked, "failed"), (after, "deleted")],
        str(body["results"]),
    )
    check("the locked agent is still there", await remaining(locked, after) == [locked])
    failure = await audit_rows(locked)
    check(
        "its audit row is a failure naming the database",
        len(failure) == 1 and failure[0].result == "failure" and "database" in (failure[0].details or ""),
        str([(r.result, r.details) for r in failure]),
    )
    check("no database text in the response", "Lock wait timeout" not in response.text and "database" not in response.text)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
