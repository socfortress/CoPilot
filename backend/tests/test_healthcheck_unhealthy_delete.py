"""Deleting a customer's unhealthy agents from the healthcheck lists (#1291).

Real routers, real in-memory database, real request parsing; token decoding and user lookup are
replaced (as in test_customer_portal_activity), and so are the upstream deletions (Wazuh,
Velociraptor) and the audit writer, by recorders: nothing leaves the process.

Pinned here:
- the threshold is the caller's, explicit, at least 24 hours, bounded; agent ids are deduplicated
  and capped (50 to delete, 1000 to preview); unknown fields are refused;
- every agent is judged again at the request: unseen on the list's tool for longer than the
  threshold (never seen, or no Velociraptor client, counts as unseen; a time in the future does not),
  never the Wazuh manager, never another customer's (told apart from nothing);
- an agent the other tool still sees is skipped unless the caller includes it;
- the preview changes nothing and says exactly what the deletion would do;
- the deletion removes the agent from Wazuh, Velociraptor (only with a client) and CoPilot, audits
  each one with the threshold, keeps going past a failure, and reports upstreams that did not confirm;
- tenancy and roles: an analyst's other customer is a 403, a portal user is refused, the Talon
  service account may not delete;
- the healthcheck itself compares in UTC, whatever the host's timezone;
- the agents' existing bulk deletions are audited too.

Run with: cd backend && python -m pytest tests/test_healthcheck_unhealthy_delete.py
"""

import asyncio
import os
import time
from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import app.auth.models.users  # noqa: E402,F401 — registers user/role tables
import app.connectors.talon.models.talon_v2  # noqa: E402,F401 — the service account's settings row
from app.agents.services import deletion  # noqa: E402
from app.agents.services.deletion import AgentRef  # noqa: E402
from app.audit.models.audit import AuditAction  # noqa: E402
from app.audit.models.audit import AuditResult  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.connectors.talon.services import talon_service_account  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import AgentDataStore  # noqa: E402
from app.db.universal_models import Agents  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.healthchecks.agents.schema.agents import AgentModel  # noqa: E402
from app.healthchecks.agents.schema.agents import TimeCriteriaModel  # noqa: E402
from app.healthchecks.agents.schema.unhealthy_delete import (  # noqa: E402
    MAX_DELETE_PER_REQUEST,
)
from app.healthchecks.agents.schema.unhealthy_delete import (  # noqa: E402
    MAX_PREVIEW_PER_REQUEST,
)
from app.healthchecks.agents.schema.unhealthy_delete import AgentVerdict  # noqa: E402
from app.healthchecks.agents.schema.unhealthy_delete import NotSeenFor  # noqa: E402
from app.healthchecks.agents.schema.unhealthy_delete import (  # noqa: E402
    UnhealthyAgentsDeleteRequest,
)
from app.healthchecks.agents.schema.unhealthy_delete import (  # noqa: E402
    UnhealthyAgentsPreviewRequest,
)
from app.healthchecks.agents.services import unhealthy_delete as service  # noqa: E402
from app.healthchecks.agents.services.agents import (  # noqa: E402
    is_velociraptor_agent_unhealthy,
)
from app.healthchecks.agents.services.agents import (  # noqa: E402
    is_wazuh_agent_unhealthy,
)

#: The request's "now": every seeded time is relative to it.
NOW = datetime(2026, 10, 22, 12, 0, 0)
DAY = timedelta(days=1)

USERS = {
    "admin": SimpleNamespace(id=1, username="admin", role_id=1),
    "ana": SimpleNamespace(id=2, username="ana", role_id=2),
    "portal": SimpleNamespace(id=4, username="portal", role_id=4),
    "talon-analyst": SimpleNamespace(id=7, username="talon-analyst", role_id=2),
}
SCOPES = {"admin": ["admin"], "ana": ["analyst"], "portal": ["customer_user"], "talon-analyst": ["analyst"]}

TABLES = (
    "user",
    "role",
    "user_customer_access",
    "customers",
    "agents",
    "agent_datastore",
    "agent_vulnerabilities",
    "talon_connector_settings",
)


def ref(agent_id="001", *, wazuh=NOW - 40 * DAY, velo=NOW - 40 * DAY, client="C.0123456789abcdef", customer="ACME") -> AgentRef:
    return AgentRef(
        agent_id=agent_id,
        customer_code=customer,
        hostname=f"host-{agent_id}",
        velociraptor_id=client,
        wazuh_last_seen=wazuh,
        velociraptor_last_seen=velo,
    )


# ── the judgement: pure ─────────────────────────────────────────────────────────────────────────


THIRTY = timedelta(days=30)


def test_an_agent_unseen_by_both_tools_for_longer_than_the_threshold_is_deletable():
    assert service.judge(ref(), "wazuh", THIRTY, NOW) == AgentVerdict.DELETABLE
    assert service.judge(ref(), "velociraptor", THIRTY, NOW) == AgentVerdict.DELETABLE


def test_the_threshold_is_strict_like_the_healthcheck_list():
    exactly = ref(wazuh=NOW - THIRTY)
    assert service.judge(exactly, "wazuh", THIRTY, NOW) == AgentVerdict.SEEN_RECENTLY
    just_over = ref(wazuh=NOW - THIRTY - timedelta(seconds=1))
    assert service.judge(just_over, "wazuh", THIRTY, NOW) == AgentVerdict.DELETABLE


def test_an_agent_seen_within_the_threshold_on_the_lists_tool_is_kept():
    assert service.judge(ref(wazuh=NOW - DAY), "wazuh", THIRTY, NOW) == AgentVerdict.SEEN_RECENTLY
    assert service.judge(ref(velo=NOW - DAY), "velociraptor", THIRTY, NOW) == AgentVerdict.SEEN_RECENTLY


def test_a_time_in_the_future_is_a_clock_ahead_of_ours_not_a_gone_agent():
    assert service.judge(ref(wazuh=NOW + DAY), "wazuh", THIRTY, NOW) == AgentVerdict.SEEN_RECENTLY
    assert service.judge(ref(velo=NOW + DAY), "wazuh", THIRTY, NOW) == AgentVerdict.ACTIVE_ELSEWHERE


def test_an_agent_the_other_tool_still_sees_is_active_elsewhere():
    assert service.judge(ref(velo=NOW - DAY), "wazuh", THIRTY, NOW) == AgentVerdict.ACTIVE_ELSEWHERE
    assert service.judge(ref(wazuh=NOW - DAY), "velociraptor", THIRTY, NOW) == AgentVerdict.ACTIVE_ELSEWHERE


@pytest.mark.parametrize("client", [None, "", "Unknown"])
def test_no_velociraptor_client_is_never_seen_by_velociraptor(client):
    # Even with a stale time left in the column: without a client, Velociraptor sees nothing.
    recent = ref(client=client, velo=NOW - timedelta(hours=1))
    assert service.judge(recent, "velociraptor", THIRTY, NOW) == AgentVerdict.DELETABLE
    assert service.judge(recent, "wazuh", THIRTY, NOW) == AgentVerdict.DELETABLE


def test_never_seen_is_unseen():
    assert service.judge(ref(wazuh=None, velo=None), "wazuh", THIRTY, NOW) == AgentVerdict.DELETABLE


def test_the_wazuh_manager_and_an_unknown_agent_are_never_deletable():
    assert service.judge(ref("000"), "wazuh", THIRTY, NOW) == AgentVerdict.WAZUH_MANAGER
    assert service.judge(ref("000"), "velociraptor", THIRTY, NOW) == AgentVerdict.WAZUH_MANAGER
    assert service.judge(None, "wazuh", THIRTY, NOW) == AgentVerdict.NOT_FOUND


def test_verdicts_are_counted_by_kind():
    counts = service.count_verdicts([AgentVerdict.DELETABLE, AgentVerdict.DELETABLE, AgentVerdict.NOT_FOUND])
    assert counts.model_dump() == {"deletable": 2, "active_elsewhere": 0, "seen_recently": 0, "wazuh_manager": 0, "not_found": 1}


# ── the request: what the caller must say ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "threshold",
    [{"value": 23, "unit": "hours"}, {"value": 0, "unit": "days"}, {"value": 30, "unit": "minutes"}, {"value": 3651, "unit": "days"}],
)
def test_a_threshold_under_a_day_or_beyond_ten_years_is_refused(threshold):
    with pytest.raises(ValidationError):
        NotSeenFor(**threshold)


def test_a_huge_threshold_is_a_validation_error_not_an_overflow():
    with pytest.raises(ValidationError):
        NotSeenFor(value=10**12, unit="hours")


def test_the_threshold_reads_as_written():
    assert NotSeenFor(value=24, unit="hours").delta == DAY
    assert NotSeenFor(value=1, unit="days").label == "1 day"
    assert NotSeenFor(value=30, unit="days").label == "30 days"


def test_agent_ids_are_deduplicated_in_order_and_capped():
    body = UnhealthyAgentsDeleteRequest(agent_ids=[" 002", "001", "002"], not_seen_for={"value": 1, "unit": "days"})
    assert body.agent_ids == ["002", "001"]
    assert body.include_active_elsewhere is False
    with pytest.raises(ValidationError):
        UnhealthyAgentsDeleteRequest(
            agent_ids=[str(i) for i in range(MAX_DELETE_PER_REQUEST + 1)],
            not_seen_for={"value": 1, "unit": "days"},
        )
    UnhealthyAgentsPreviewRequest(agent_ids=[str(i) for i in range(MAX_PREVIEW_PER_REQUEST)], not_seen_for={"value": 1, "unit": "days"})
    with pytest.raises(ValidationError):
        UnhealthyAgentsPreviewRequest(
            agent_ids=[str(i) for i in range(MAX_PREVIEW_PER_REQUEST + 1)],
            not_seen_for={"value": 1, "unit": "days"},
        )


@pytest.mark.parametrize(
    "body",
    [
        {"agent_ids": [], "not_seen_for": {"value": 1, "unit": "days"}},
        {"agent_ids": ["001"]},
        {"agent_ids": [""], "not_seen_for": {"value": 1, "unit": "days"}},
        {"agent_ids": ["001"], "not_seen_for": {"value": 1, "unit": "days"}, "dry_run": True},
        {"agent_ids": ["001"], "not_seen_for": {"value": 1, "unit": "days", "minutes": 5}},
    ],
)
def test_an_incomplete_or_unknown_request_is_refused(body):
    with pytest.raises(ValidationError):
        UnhealthyAgentsDeleteRequest(**body)


# ── the routes: real routers over an in-memory database ─────────────────────────────────────────


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


def agent_row(agent_id, *, customer="ACME", wazuh_days=40, velo_days=40, client="C.0123456789abcdef") -> Agents:
    return Agents(
        agent_id=agent_id,
        ip_address="10.0.0.1",
        os="Windows",
        hostname=f"host-{agent_id}",
        label=f"label-{agent_id}",
        wazuh_last_seen=NOW - timedelta(days=wazuh_days),
        velociraptor_id=client,
        velociraptor_last_seen=NOW - timedelta(days=velo_days) if client else None,
        wazuh_agent_version="4.9.0",
        velociraptor_agent_version="0.7.0" if client else None,
        customer_code=customer,
    )


#: ACME's agents, as the healthcheck lists see them at NOW with a 30-day threshold.
SEED = [
    ("001", {}),  # gone from both: deletable
    ("002", {"velo_days": 1}),  # Wazuh gone, Velociraptor still sees it
    ("003", {"wazuh_days": 1, "velo_days": 1}),  # seen since the list was read
    ("004", {"client": None}),  # never had a Velociraptor client
    ("000", {}),  # the Wazuh manager
    ("101", {"customer": "GLOBEX"}),  # another customer's
]


async def seed(db: Db) -> None:
    async with db.session() as session:
        session.add_all(
            [
                User(id=1, username="admin", password="x" * 8, email="admin@example.com", role_id=1),
                User(id=2, username="ana", password="x" * 8, email="ana@example.com", role_id=2),
                User(id=4, username="portal", password="x" * 8, email="portal@example.com", role_id=4),
                User(id=7, username="talon-analyst", password="x" * 8, email="talon@example.com", role_id=2),
                Customers(customer_code="ACME", customer_name="Acme Corp"),
                Customers(customer_code="GLOBEX", customer_name="Globex"),
            ],
        )
        await session.commit()
        session.add_all([UserCustomerAccess(user_id=2, customer_code="ACME"), UserCustomerAccess(user_id=7, customer_code="ACME")])
        session.add_all([agent_row(agent_id, **fields) for agent_id, fields in SEED])
        await session.commit()
        session.add(
            AgentDataStore(
                agent_id="001",
                velociraptor_id="C.0123456789abcdef",
                artifact_name="Generic.Client.Info",
                flow_id="F.1",
                bucket_name="velociraptor-artifacts",
                object_key="k",
                file_name="f",
                file_size=1,
                content_type="application/zip",
                file_hash="h",
            ),
        )
        await session.commit()


class Upstreams:
    """Records what Wazuh and Velociraptor were asked to delete; a set of ids can refuse."""

    def __init__(self, *, wazuh_refuses=(), velociraptor_refuses=()):
        self.wazuh, self.velociraptor = [], []
        self.wazuh_refuses, self.velociraptor_refuses = set(wazuh_refuses), set(velociraptor_refuses)

    async def delete_wazuh(self, agent_id):
        self.wazuh.append(agent_id)
        if agent_id in self.wazuh_refuses:
            raise HTTPException(status_code=400, detail=f"Failed to delete agent {agent_id} from Wazuh Manager: no such agent")

    async def delete_velociraptor(self, client_id):
        self.velociraptor.append(client_id)
        if client_id in self.velociraptor_refuses:
            raise HTTPException(status_code=500, detail="Velociraptor unreachable")


def app_for(db: Db) -> FastAPI:
    from app.agents.routes.agents import agents_router
    from app.customers.routes.customers import customers_router

    api = FastAPI()
    api.include_router(customers_router, prefix="/customers")
    api.include_router(agents_router, prefix="/agents")

    async def _session():
        async with db.session() as session:
            yield session

    api.dependency_overrides[get_db] = _session
    return api


def call(scenario, *, upstreams=None):
    upstreams = upstreams or Upstreams()
    audit = AsyncMock()

    async def _inner():
        db = await Db().create()
        try:
            await seed(db)

            async def resolve_user(self, request, username):
                return USERS.get(username)

            with patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))), patch.object(
                AuthHandler,
                "_resolve_user",
                resolve_user,
            ), patch.object(service, "judgement_time", lambda: NOW), patch.object(
                deletion,
                "delete_agent_wazuh",
                upstreams.delete_wazuh,
            ), patch.object(
                deletion,
                "delete_agent_velociraptor",
                upstreams.delete_velociraptor,
            ), patch.object(
                deletion,
                "record_audit_event",
                audit,
            ):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app_for(db)), base_url="http://test") as client:
                    return await scenario(client, db)
        finally:
            await db.engine.dispose()

    result = asyncio.run(_inner())
    return result, upstreams, audit


def as_user(name):
    return {"Authorization": f"Bearer {name}"}


THRESHOLD = {"value": 30, "unit": "days"}
DELETE = "/customers/ACME/agents/healthcheck/wazuh/delete"
PREVIEW = "/customers/ACME/agents/healthcheck/wazuh/delete/preview"


async def agent_ids(db: Db):
    async with db.session() as session:
        return sorted((await session.execute(select(Agents.agent_id))).scalars().all())


def test_the_preview_judges_each_agent_in_order_and_changes_nothing():
    async def scenario(client, db):
        response = await client.post(
            PREVIEW,
            json={"agent_ids": ["001", "002", "003", "004", "000", "101", "999"], "not_seen_for": THRESHOLD},
            headers=as_user("admin"),
        )
        return response, await agent_ids(db)

    (response, remaining), upstreams, audit = call(scenario)
    assert response.status_code == 200, response.text
    body = response.json()
    assert [(a["agent_id"], a["verdict"]) for a in body["agents"]] == [
        ("001", "deletable"),
        ("002", "active_elsewhere"),
        ("003", "seen_recently"),
        ("004", "deletable"),
        ("000", "wazuh_manager"),
        ("101", "not_found"),
        ("999", "not_found"),
    ]
    assert body["counts"] == {"deletable": 2, "active_elsewhere": 1, "seen_recently": 1, "wazuh_manager": 1, "not_found": 2}
    assert body["cutoff"] == (NOW - timedelta(days=30)).isoformat()
    assert body["not_seen_for"] == THRESHOLD and body["source"] == "wazuh"
    first = body["agents"][0]
    assert first["hostname"] == "host-001" and first["label"] == "label-001" and first["os"] == "Windows"
    assert first["last_seen"] == (NOW - 40 * DAY).isoformat() and first["other_last_seen"] == (NOW - 40 * DAY).isoformat()
    # Another customer's agent is told apart from nothing: no name, no time.
    globex = body["agents"][5]
    assert globex == {
        "agent_id": "101",
        "verdict": "not_found",
        "hostname": None,
        "label": None,
        "os": None,
        "last_seen": None,
        "other_last_seen": None,
    }
    assert remaining == ["000", "001", "002", "003", "004", "101"]
    assert upstreams.wazuh == [] and upstreams.velociraptor == [] and audit.await_count == 0


def test_the_velociraptor_list_judges_by_velociraptor_and_looks_at_wazuh_for_the_rest():
    async def scenario(client, db):
        return await client.post(
            "/customers/ACME/agents/healthcheck/velociraptor/delete/preview",
            json={"agent_ids": ["001", "002", "003", "004"], "not_seen_for": THRESHOLD},
            headers=as_user("admin"),
        )

    (response), _, _ = call(scenario)
    agents = response.json()["agents"]
    assert [(a["agent_id"], a["verdict"]) for a in agents] == [
        ("001", "deletable"),
        ("002", "seen_recently"),
        ("003", "seen_recently"),
        ("004", "deletable"),
    ]
    # last_seen is the list's tool, other_last_seen the other one; no client means no Velociraptor time.
    assert agents[1]["last_seen"] == (NOW - DAY).isoformat() and agents[1]["other_last_seen"] == (NOW - 40 * DAY).isoformat()
    assert agents[3]["last_seen"] is None


def test_the_deletion_removes_only_what_is_still_deletable_everywhere_and_audits_each():
    async def scenario(client, db):
        response = await client.post(
            DELETE,
            json={"agent_ids": ["001", "002", "003", "004", "000", "101"], "not_seen_for": THRESHOLD},
            headers=as_user("admin"),
        )
        async with db.session() as session:
            datastore = (await session.execute(select(AgentDataStore))).scalars().all()
        return response, await agent_ids(db), datastore

    (response, remaining, datastore), upstreams, audit = call(scenario)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert (body["requested"], body["deleted"], body["skipped"], body["failed"], body["unconfirmed"]) == (6, 2, 4, 0, 0)
    assert body["message"] == "2 deleted, 4 skipped"
    assert [(r["agent_id"], r["outcome"], r["reason"]) for r in body["results"]] == [
        ("001", "deleted", None),
        ("002", "skipped", "active_elsewhere"),
        ("003", "skipped", "seen_recently"),
        ("004", "deleted", None),
        ("000", "skipped", "wazuh_manager"),
        ("101", "skipped", "not_found"),
    ]
    assert body["results"][5]["hostname"] is None
    assert remaining == ["000", "002", "003", "101"]
    assert datastore == []
    # Wazuh for both; Velociraptor only for the one with a client.
    assert upstreams.wazuh == ["001", "004"]
    assert upstreams.velociraptor == ["C.0123456789abcdef"]

    assert audit.await_count == 2
    first = audit.await_args_list[0].kwargs
    assert first["action"] == AuditAction.AGENT_DELETE and first["result"] == AuditResult.SUCCESS
    assert (first["actor_user_id"], first["actor_username"], first["customer_code"]) == (1, "admin", "ACME")
    assert (first["entity_type"], first["entity_id"]) == ("agent", "001")
    assert first["new_value"] == {"via": "healthcheck", "source": "wazuh", "not_seen_for": "30 days", "include_active_elsewhere": False}
    assert first["old_value"]["hostname"] == "host-001"
    assert first["old_value"]["wazuh_last_seen"] == (NOW - 40 * DAY).isoformat()
    assert first["details"] is None


def test_an_agent_active_elsewhere_is_deleted_only_when_the_caller_includes_it():
    async def scenario(client, db):
        response = await client.post(
            DELETE,
            json={"agent_ids": ["002", "003"], "not_seen_for": THRESHOLD, "include_active_elsewhere": True},
            headers=as_user("admin"),
        )
        return response, await agent_ids(db)

    (response, remaining), upstreams, audit = call(scenario)
    assert [(r["agent_id"], r["outcome"]) for r in response.json()["results"]] == [("002", "deleted"), ("003", "skipped")]
    assert "002" not in remaining and "003" in remaining
    assert audit.await_args_list[0].kwargs["new_value"]["include_active_elsewhere"] is True


def test_an_upstream_that_does_not_confirm_is_reported_and_the_agent_still_leaves_copilot():
    async def scenario(client, db):
        response = await client.post(DELETE, json={"agent_ids": ["001"], "not_seen_for": THRESHOLD}, headers=as_user("admin"))
        return response, await agent_ids(db)

    (response, remaining), _, audit = call(
        scenario,
        upstreams=Upstreams(wazuh_refuses={"001"}, velociraptor_refuses={"C.0123456789abcdef"}),
    )
    body = response.json()
    assert body["success"] is True and body["unconfirmed"] == 1 and body["message"] == "1 deleted, 1 not confirmed upstream"
    assert body["results"][0]["unconfirmed"] == ["wazuh", "velociraptor"]
    assert "001" not in remaining
    # The upstream texts stay in the audit row, never in the response.
    assert "no such agent" in audit.await_args.kwargs["details"] and "unreachable" in audit.await_args.kwargs["details"]
    assert "no such agent" not in response.text and "unreachable" not in response.text


def test_a_database_failure_fails_that_agent_only_and_the_rest_are_still_deleted():
    real = deletion.delete_agent_from_database

    async def failing(db, agent_id):
        if agent_id == "001":
            # What the real function does on a database error: roll back, then raise. The rollback
            # expires every row in the session, which the loop must survive.
            await db.rollback()
            raise HTTPException(status_code=500, detail="Failed to delete agent 001 from database: deadlock")
        return await real(db=db, agent_id=agent_id)

    async def scenario(client, db):
        with patch.object(deletion, "delete_agent_from_database", failing):
            response = await client.post(DELETE, json={"agent_ids": ["001", "004"], "not_seen_for": THRESHOLD}, headers=as_user("admin"))
        return response, await agent_ids(db)

    (response, remaining), _, audit = call(scenario)
    body = response.json()
    assert response.status_code == 200
    assert body["success"] is False and body["message"] == "1 deleted, 1 failed"
    assert [(r["agent_id"], r["outcome"]) for r in body["results"]] == [("001", "failed"), ("004", "deleted")]
    assert "001" in remaining and "004" not in remaining
    assert [c.kwargs["result"] for c in audit.await_args_list] == [AuditResult.FAILURE, AuditResult.SUCCESS]
    assert "deadlock" not in response.text


def test_an_analyst_deletes_only_within_their_customers():
    async def scenario(client, db):
        other = await client.post(
            "/customers/GLOBEX/agents/healthcheck/wazuh/delete",
            json={"agent_ids": ["101"], "not_seen_for": THRESHOLD},
            headers=as_user("ana"),
        )
        other_preview = await client.post(
            "/customers/GLOBEX/agents/healthcheck/wazuh/delete/preview",
            json={"agent_ids": ["101"], "not_seen_for": THRESHOLD},
            headers=as_user("ana"),
        )
        # Naming another customer's agent under one's own customer finds nothing.
        smuggled = await client.post(DELETE, json={"agent_ids": ["101", "001"], "not_seen_for": THRESHOLD}, headers=as_user("ana"))
        return other, other_preview, smuggled, await agent_ids(db)

    (other, other_preview, smuggled, remaining), upstreams, _ = call(scenario)
    assert other.status_code == 403 and other_preview.status_code == 403
    assert [(r["agent_id"], r["outcome"], r["reason"]) for r in smuggled.json()["results"]] == [
        ("101", "skipped", "not_found"),
        ("001", "deleted", None),
    ]
    assert "101" in remaining
    assert upstreams.wazuh == ["001"]


@pytest.mark.parametrize(
    "user, detail",
    [
        ("portal", "Insufficient permissions. Required one of: admin, analyst"),
        ("talon-analyst", talon_service_account.REFUSED),
    ],
)
def test_a_portal_user_and_the_talon_service_account_may_not_delete(user, detail):
    async def scenario(client, db):
        response = await client.post(DELETE, json={"agent_ids": ["001"], "not_seen_for": THRESHOLD}, headers=as_user(user))
        return response, await agent_ids(db)

    (response, remaining), upstreams, audit = call(scenario)
    assert response.status_code == 403 and response.json()["detail"] == detail
    assert "001" in remaining and upstreams.wazuh == [] and audit.await_count == 0


def test_an_unknown_customer_is_a_404_for_an_admin():
    async def scenario(client, db):
        delete = await client.post(
            "/customers/NOPE/agents/healthcheck/wazuh/delete",
            json={"agent_ids": ["001"], "not_seen_for": THRESHOLD},
            headers=as_user("admin"),
        )
        preview = await client.post(
            "/customers/NOPE/agents/healthcheck/wazuh/delete/preview",
            json={"agent_ids": ["001"], "not_seen_for": THRESHOLD},
            headers=as_user("admin"),
        )
        return delete, preview

    (delete, preview), upstreams, _ = call(scenario)
    assert delete.status_code == 404 and preview.status_code == 404
    assert upstreams.wazuh == []


@pytest.mark.parametrize(
    "path, body",
    [
        (DELETE, {"agent_ids": ["001"], "not_seen_for": {"value": 23, "unit": "hours"}}),
        (DELETE, {"agent_ids": ["001"]}),
        (DELETE, {"agent_ids": [str(i) for i in range(MAX_DELETE_PER_REQUEST + 1)], "not_seen_for": THRESHOLD}),
        ("/customers/ACME/agents/healthcheck/graylog/delete", {"agent_ids": ["001"], "not_seen_for": THRESHOLD}),
        (PREVIEW, {"agent_ids": ["001"], "not_seen_for": {"value": 1, "unit": "minutes"}}),
    ],
)
def test_a_request_outside_the_rules_is_refused_before_anything_is_deleted(path, body):
    async def scenario(client, db):
        response = await client.post(path, json=body, headers=as_user("admin"))
        return response, await agent_ids(db)

    (response, remaining), upstreams, audit = call(scenario)
    assert response.status_code == 422, response.text
    assert "001" in remaining and upstreams.wazuh == [] and audit.await_count == 0


def test_the_routes_refuse_the_talon_service_account_only_where_they_delete():
    from app.customers.routes.customers import customers_router

    def dependencies(path):
        (route,) = [r for r in customers_router.routes if r.path == path]
        return [d.dependency for d in route.dependencies]

    assert talon_service_account.refuse_talon_service_account_dependency in dependencies(
        "/{customer_code}/agents/healthcheck/{source}/delete",
    )
    # The preview only reads.
    assert talon_service_account.refuse_talon_service_account_dependency not in dependencies(
        "/{customer_code}/agents/healthcheck/{source}/delete/preview",
    )


# ── the agents' existing bulk deletions are audited too ─────────────────────────────────────────


def test_the_agents_bulk_deletions_are_audited_like_the_single_one():
    async def scenario(client, db):
        by_id = await client.post("/agents/bulk/delete", json={"agent_ids": ["001"]}, headers=as_user("admin"))
        by_filter = await client.post("/agents/bulk/delete/filter", json={"customer_code": "GLOBEX"}, headers=as_user("admin"))
        return by_id, by_filter, await agent_ids(db)

    (by_id, by_filter, remaining), _, audit = call(scenario)
    assert by_id.status_code == 200 and by_id.json()["successful_deletions"] == 1
    assert by_filter.status_code == 200 and by_filter.json()["successful_deletions"] == 1
    assert "001" not in remaining and "101" not in remaining
    assert [(c.kwargs["entity_id"], c.kwargs["new_value"], c.kwargs["actor_username"]) for c in audit.await_args_list] == [
        ("001", {"via": "bulk_delete"}, "admin"),
        ("101", {"via": "bulk_delete_filter"}, "admin"),
    ]


# ── the healthcheck itself compares in UTC ──────────────────────────────────────────────────────


def test_the_healthcheck_compares_in_utc_whatever_the_hosts_timezone(monkeypatch):
    """The columns hold naive UTC. A local ``datetime.now()`` on a host 14 hours ahead of UTC made an
    agent seen 30 minutes ago look 14 hours late."""
    seen = datetime.utcnow() - timedelta(minutes=30)
    agent = AgentModel(agent_id="001", hostname="h", wazuh_last_seen=seen, velociraptor_id="C.1", velociraptor_last_seen=seen)
    criteria = TimeCriteriaModel(minutes=60)
    original = os.environ.get("TZ")
    monkeypatch.setenv("TZ", "Pacific/Kiritimati")
    time.tzset()
    try:
        assert is_wazuh_agent_unhealthy(agent, criteria).unhealthy_wazuh_agent is False
        assert is_velociraptor_agent_unhealthy(agent, criteria).unhealthy_velociraptor_agent is False
    finally:
        if original is None:
            monkeypatch.delenv("TZ")
        else:
            monkeypatch.setenv("TZ", original)
        time.tzset()


def test_the_healthcheck_takes_the_moment_to_judge_at():
    agent = AgentModel(agent_id="001", wazuh_last_seen=NOW - timedelta(hours=2), velociraptor_id="C.1", velociraptor_last_seen=NOW)
    criteria = TimeCriteriaModel(minutes=60)
    assert is_wazuh_agent_unhealthy(agent, criteria, now=NOW).unhealthy_wazuh_agent is True
    assert is_velociraptor_agent_unhealthy(agent, criteria, now=NOW).unhealthy_velociraptor_agent is False
