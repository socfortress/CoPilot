"""Indexer reads keep a scoped caller to their own customers.

Since #1219 an analyst or a responder sees only the customers assigned to them, but the routes that
read the indexer took an index, a pattern or a document id from the caller, or searched every index,
and returned whatever came back. Pinned here (``app/middleware/document_access.py``):

- a document's customer is decided as ingest decides it (an agent label first, then the syslog
  customer, the customer code, the Office 365 tenant, the AWS account, the Wazuh worker), and a
  document that names no customer is nobody's but an admin's;
- searches carry a filter on those fields for a scoped caller, whatever index was named, matched
  exactly (through ``.keyword`` where a field is analysed); an admin's searches carry none;
- single documents (by index and id) of another customer read like missing ones;
- Wazuh's state indices (packages) are filtered by the caller's agents, by id, name and exact pair;
- index names (shards, field mappings) are matched to customers by whole words, not substrings;
- the ingest backlog is admin-only, and the AI Chatbot has no local server left to read every
  customer's data (the copilot-mcp container was removed);
- the Detections Catalog's deployment-wide hit counts are an admin's view.

Real routers, a real in-memory database, a fake indexer that applies the customer filter's clauses
exactly and lets the rest of each query through; only token decoding and user lookup are replaced.

Run with: cd backend && python -m pytest tests/test_analyst_index_scoping.py
"""

import asyncio
import fnmatch
import os
from contextlib import ExitStack
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
import pytest  # noqa: E402
from elasticsearch7.exceptions import NotFoundError  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import app.auth.models.users  # noqa: E402,F401 — registers user/role tables
import app.connectors.talon.models.talon_v2  # noqa: E402,F401 — talon_connector_settings
import app.incidents.models  # noqa: E402,F401 — the threshold timeline's metadata table
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.connectors.wazuh_indexer.schema.monitoring import Shards  # noqa: E402
from app.connectors.wazuh_indexer.schema.monitoring import ShardsResponse  # noqa: E402
from app.connectors.wazuh_indexer.utils.customer_index import (  # noqa: E402
    index_matches_customer,
)
from app.customer_portal.services.exposure_vulnerabilities import (  # noqa: E402
    PAIR_SCRIPT,
)
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import Agents  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.integrations.models.customer_integration_settings import (  # noqa: E402
    CustomerIntegrations,
)
from app.integrations.models.customer_integration_settings import (  # noqa: E402
    IntegrationAuthKeys,
)
from app.integrations.models.customer_integration_settings import (  # noqa: E402
    IntegrationService,
)
from app.integrations.models.customer_integration_settings import (  # noqa: E402
    IntegrationSubscription,
)
from app.middleware import document_access  # noqa: E402

USERS = {
    "admin": SimpleNamespace(id=1, username="admin", role_id=1),
    "ana": SimpleNamespace(id=2, username="ana", role_id=2),
    "rex": SimpleNamespace(id=5, username="rex", role_id=5),
    "nobody": SimpleNamespace(id=6, username="nobody", role_id=2),
}
SCOPES = {"admin": ["admin"], "ana": ["analyst"], "rex": ["responder", "analyst"], "nobody": ["analyst"]}
SCOPED = ("ana", "rex")
TABLES = (
    "user",
    "role",
    "user_customer_access",
    "customers",
    "agents",
    "customer_integrations",
    "integration_services",
    "integration_subscriptions",
    "integration_auth_keys",
    "talon_connector_settings",
    "incident_management_threshold_alert_metadata",
)


def doc(doc_id, index, **fields):
    source = {
        "timestamp": "2026-11-20T10:00:00Z",
        "syslog_type": "wazuh",
        "syslog_level": "ALERT",
        "rule_description": f"rule {doc_id}",
        "agent_name": "web-01",
    }
    source.update(fields)
    return {"_index": index, "_id": doc_id, "_version": 1, "_source": source}


#: What each document is, by ingest's rule, and so who may see it.
DOCS = [
    doc("acme", "wazuh-acme_1", agent_labels_customer="ACME", process_id="42"),
    doc("globex", "wazuh-globex_1", agent_labels_customer="GLOBEX", process_id="42"),
    # In an index named like ACME's: the document's customer decides, not the index name.
    doc("globex-in-acme-index", "wazuh-acme_1", agent_labels_customer="GLOBEX", process_id="42"),
    # The label decides when there is one, as at ingest: the syslog customer doesn't count.
    doc("label-wins", "wazuh-acme_1", agent_labels_customer="GLOBEX", syslog_customer="ACME"),
    doc("syslog-acme", "sonicwall-acme_0", syslog_customer="ACME"),
    doc("nested-acme", "wazuh-alerts-4.x-2026.11.20", agent={"labels": {"customer": "ACME"}}),
    doc("o365-acme", "office365-acme_0", data_office365_OrganizationId="tenant-acme"),
    doc("o365-globex", "office365-globex_0", data_office365_OrganizationId="tenant-globex"),
    doc("aws-acme", "aws-acme_0", aws_account_id="111111111111"),
    # Claimed by both customers: ingest routes it to nobody.
    doc("aws-shared", "aws-shared_0", aws_account_id="222222222222"),
    doc("worker-acme", "wazuh-acme_1", cluster_node="wazuh.worker.acme"),
    doc("worker-acme2", "wazuh-acme2_1", cluster_node="wazuh.worker.acme2"),
    doc("nobody", "wazuh-misc_1"),
]
ACME_IDS = {"acme", "syslog-acme", "nested-acme", "o365-acme", "aws-acme", "worker-acme"}
ALL_IDS = {d["_id"] for d in DOCS}


# --- a fake indexer that applies the customer filter exactly ------------------------------------


def _value(source, field):
    field = field[: -len(".keyword")] if field.endswith(".keyword") else field
    if field in source:
        return source[field]
    node = source
    for part in field.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def matches(source, clause):
    """The clauses ``customer_filter`` and ``agent_filters`` use, and matches, exactly; any other
    clause (time ranges, query strings) is let through, so a test sees what the scope does."""
    if not clause:
        return True
    if isinstance(clause, list):
        return all(matches(source, c) for c in clause)
    ((kind, body),) = clause.items()
    if kind == "bool":

        def listed(key):
            value = body.get(key, [])
            return value if isinstance(value, list) else [value]

        required = listed("must") + listed("filter")
        should = listed("should")
        if not all(matches(source, c) for c in required):
            return False
        if any(matches(source, c) for c in listed("must_not")):
            return False
        minimum = body.get("minimum_should_match", 0 if required else (1 if should else 0))
        return sum(1 for c in should if matches(source, c)) >= minimum
    if kind == "match_all":
        return True
    if kind == "terms":
        ((field, wanted),) = body.items()
        value = _value(source, field)
        return value is not None and str(value) in {str(w) for w in wanted}
    if kind == "term":
        ((field, wanted),) = body.items()
        wanted = wanted.get("value") if isinstance(wanted, dict) else wanted
        return _value(source, field) == wanted
    if kind == "prefix":
        ((field, wanted),) = body.items()
        value = _value(source, field)
        return isinstance(value, str) and value.startswith(wanted)
    if kind == "exists":
        return _value(source, body["field"]) is not None
    if kind in ("match", "match_phrase"):
        ((field, wanted),) = body.items()
        wanted = wanted.get("query") if isinstance(wanted, dict) else wanted
        return str(_value(source, field)) == str(wanted)
    if kind == "script":
        script = body["script"]
        assert script["source"] == PAIR_SCRIPT, "only the agent pair script is known here"
        agent = source.get("agent") or {}
        return f"{agent.get('id', '')}|{agent.get('name', '')}" in script["params"]["pairs"]
    return True


def _index_matches(pattern, index):
    return any(fnmatch.fnmatchcase(index, part.strip()) for part in str(pattern or "*").split(",") if part and not part.startswith("-"))


class FakeIndexer:
    def __init__(self, docs, text_fields=()):
        self.docs = docs
        self.text_fields = set(text_fields)
        self.searches = []

    def search(self, index=None, body=None, size=None, **_):
        self.searches.append({"index": index, "body": body})
        query = (body or {}).get("query", {"match_all": {}})
        hits = [d for d in self.docs if _index_matches(index, d["_index"]) and matches(d["_source"], query)]
        return {"hits": {"hits": hits[: size or 10_000], "total": {"value": len(hits)}}}

    def get(self, index=None, id=None, **_):
        for d in self.docs:
            if d["_index"] == index and d["_id"] == id:
                return d
        raise NotFoundError(404, "not_found", {})

    def field_caps(self, index=None, fields=None, **_):
        return {"fields": {name: {"text": {}} for name in self.text_fields}}


class _AsyncClient:
    def __init__(self, fake):
        self.fake = fake

    async def search(self, **kwargs):
        return self.fake.search(**kwargs)

    async def get(self, **kwargs):
        return self.fake.get(**kwargs)

    async def field_caps(self, **kwargs):
        return self.fake.field_caps(**kwargs)

    async def close(self):
        return None


class _SyncClient:
    def __init__(self, fake):
        self.fake = fake
        self.indices = SimpleNamespace(get_alias=lambda *a, **k: {d["_index"]: {} for d in fake.docs})

    def search(self, **kwargs):
        return self.fake.search(**kwargs)

    def close(self):
        return None


@contextmanager
def indexer(docs=DOCS, text_fields=()):
    fake = FakeIndexer(docs, text_fields)
    async_client = AsyncMock(return_value=_AsyncClient(fake))
    sync_client = AsyncMock(return_value=_SyncClient(fake))
    targets = {
        "app.connectors.wazuh_indexer.utils.universal.create_wazuh_indexer_client": sync_client,
        "app.connectors.wazuh_indexer.utils.universal.create_wazuh_indexer_client_async": async_client,
        "app.connectors.wazuh_indexer.services.alerts.create_wazuh_indexer_client": sync_client,
        "app.connectors.wazuh_indexer.services.alerts.create_wazuh_indexer_client_async": async_client,
        "app.incidents.services.incident_alert.create_wazuh_indexer_client": sync_client,
        "app.incidents.services.incident_alert.create_wazuh_indexer_client_async": async_client,
        "app.agents.wazuh.syscollector.services.packages.create_wazuh_indexer_client_async": async_client,
    }
    document_access._field_types_cache.clear()
    with ExitStack() as stack:
        for target, replacement in targets.items():
            stack.enter_context(patch(target, replacement))
        yield fake
    document_access._field_types_cache.clear()


# --- database and app ---------------------------------------------------------------------------


class Db:
    def __init__(self):
        self.engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        self.factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

    async def create(self) -> "Db":
        async with self.engine.begin() as conn:
            await conn.run_sync(lambda c: SQLModel.metadata.create_all(c, tables=[SQLModel.metadata.tables[n] for n in TABLES]))
        return self


def agent_row(agent_id, hostname, customer):
    return Agents(
        agent_id=agent_id,
        ip_address="10.0.0.1",
        os="Linux",
        hostname=hostname,
        label=hostname,
        wazuh_last_seen=datetime(2026, 11, 20),
        velociraptor_id="C.0123456789abcdef",
        velociraptor_last_seen=datetime(2026, 11, 20),
        wazuh_agent_version="4.9.0",
        velociraptor_agent_version="0.7.0",
        customer_code=customer,
    )


async def _integration(session, code, service_name, key, value, deployed=True):
    customer = CustomerIntegrations(
        customer_code=code,
        customer_name=code,
        integration_service_id=1,
        integration_service_name=service_name,
        deployed=deployed,
    )
    session.add(customer)
    await session.flush()
    service = IntegrationService(service_name=service_name, auth_type="API Key")
    session.add(service)
    await session.flush()
    subscription = IntegrationSubscription(customer_id=customer.id, integration_service_id=service.id)
    session.add(subscription)
    await session.flush()
    session.add(IntegrationAuthKeys(subscription_id=subscription.id, auth_key_name=key, auth_value=value))


async def _seed(db: Db) -> None:
    async with db.factory() as session:
        session.add_all(
            [Customers(customer_code="ACME", customer_name="Acme Corp"), Customers(customer_code="GLOBEX", customer_name="Globex")],
        )
        await session.commit()
        session.add_all(
            [
                UserCustomerAccess(user_id=2, customer_code="ACME"),
                UserCustomerAccess(user_id=5, customer_code="ACME"),
                # Agent ids are unique per manager only: GLOBEX has an 001 too.
                agent_row("001", "web-01", "ACME"),
                agent_row("001", "db-01", "GLOBEX"),
                agent_row("002", "mail-01", "GLOBEX"),
            ],
        )
        await _integration(session, "ACME", "Office365", "TENANT_ID", "tenant-acme")
        await _integration(session, "GLOBEX", "Office365", "TENANT_ID", "tenant-globex")
        await _integration(session, "ACME", "AWS", "AWS_ACCOUNT_ID", "111111111111")
        await _integration(session, "ACME", "AWS", "AWS_ACCOUNT_ID", "222222222222")
        await _integration(session, "GLOBEX", "AWS", "AWS_ACCOUNT_ID", "222222222222")
        await session.commit()


def _app(db: Db) -> FastAPI:
    from app.routers import agents
    from app.routers import copilot_mcp
    from app.routers import copilot_searches
    from app.routers import graylog
    from app.routers import incidents
    from app.routers import threat_intel
    from app.routers import wazuh_indexer
    from app.routers import wazuh_manager

    api = FastAPI()
    for module in (agents, copilot_mcp, copilot_searches, graylog, incidents, threat_intel, wazuh_indexer, wazuh_manager):
        api.include_router(module.router)

    async def _session():
        async with db.factory() as session:
            yield session

    api.dependency_overrides[get_db] = _session
    return api


def call(scenario):
    async def _inner():
        db = await Db().create()
        try:
            await _seed(db)
            transport = httpx.ASGITransport(app=_app(db))

            async def resolve_user(self, request, username):
                return USERS.get(username)

            with patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))), patch.object(
                AuthHandler,
                "_resolve_user",
                resolve_user,
            ):
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    return await scenario(client, db)
        finally:
            await db.engine.dispose()

    return asyncio.run(_inner())


def as_user(name):
    return {"Authorization": f"Bearer {name}"}


def ids_in(alerts_summary):
    return {alert["_id"] for item in alerts_summary for alert in item["alerts"]}


def detail(response) -> str:
    body = response.json()
    return body.get("detail") or body.get("message") or ""


# --- index names --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("index_name", "expected"),
    [
        ("wazuh-lab_0", True),
        ("lab-alerts_3", True),
        ("huntress_lab", True),
        ("collaboration_0", False),
        ("lab2_1", False),
        ("wazuh-lab2_0", False),
        ("wazuh-alabama_1", False),
    ],
)
def test_an_index_belongs_to_a_customer_by_a_whole_word(index_name, expected):
    assert index_matches_customer(index_name, ["lab"]) is expected


# --- who a document belongs to ------------------------------------------------------------------


@pytest.mark.parametrize("who", SCOPED)
def test_a_scoped_caller_sees_exactly_their_customers_documents(who):
    async def scenario(client, db):
        async with db.factory() as session:
            user = USERS[who]
            visible = {d["_id"] for d in DOCS if await document_access.document_visible(user, d["_source"], session)}
            scope = await document_access.customer_filter(user, session)
        assert visible == ACME_IDS
        # The search filter agrees with the one-document rule, document by document.
        assert {d["_id"] for d in DOCS if matches(d["_source"], scope)} == ACME_IDS

    with indexer():
        call(scenario)


def test_an_admin_sees_every_document_and_searches_unfiltered():
    async def scenario(client, db):
        async with db.factory() as session:
            visible = {d["_id"] for d in DOCS if await document_access.document_visible(USERS["admin"], d["_source"], session)}
            scope = await document_access.customer_filter(USERS["admin"], session)
        assert visible == ALL_IDS
        assert scope is None

    with indexer():
        call(scenario)


def test_a_caller_with_no_customer_sees_nothing():
    async def scenario(client, db):
        async with db.factory() as session:
            scope = await document_access.customer_filter(USERS["nobody"], session)
            visible = [d for d in DOCS if await document_access.document_visible(USERS["nobody"], d["_source"], session)]
        assert scope == document_access.MATCH_NONE and visible == []

    with indexer():
        call(scenario)


def test_an_analysed_field_is_matched_through_its_keyword_subfield_only():
    # ``terms`` on a text field compares tokens: "acme" would match a GLOBEX value "acme-2".
    async def scenario(client, db):
        async with db.factory() as session:
            scope = await document_access.customer_filter(USERS["ana"], session, "wazuh-*")
        clauses = str(scope)
        assert "'agent_labels_customer.keyword'" in clauses
        assert "{'terms': {'agent_labels_customer': [" not in clauses
        assert "{'terms': {'syslog_customer': [" in clauses  # still keyword-typed

    with indexer(text_fields={"agent_labels_customer"}):
        call(scenario)


# --- the indexer alert routes -------------------------------------------------------------------


SEARCH = {"size": 50, "timerange": "24h", "alert_field": "syslog_level", "alert_value": "ALERT", "timestamp_field": "timestamp"}


@pytest.mark.parametrize("who", SCOPED)
@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/alerts", SEARCH),
        ("/alerts/host", {**SEARCH, "agent_name": "web-01"}),
        ("/alerts/index", {**SEARCH, "index_name": "wazuh-acme_1"}),
    ],
)
def test_alert_searches_return_only_the_callers_customers_documents(who, path, body):
    async def scenario(client, db):
        response = await client.post(path, json=body, headers=as_user(who))
        assert response.status_code == 200, response.text
        return ids_in(response.json()["alerts_summary"])

    with indexer():
        found = call(scenario)
    assert found and found <= ACME_IDS


def test_an_admins_alert_search_reads_every_customer():
    async def scenario(client, db):
        response = await client.post("/alerts", json=SEARCH, headers=as_user("admin"))
        return ids_in(response.json()["alerts_summary"])

    with indexer():
        assert call(scenario) == ALL_IDS


@pytest.mark.parametrize(
    ("path", "key"),
    [
        ("/alerts/hosts/all", "alerts_by_host"),
        ("/alerts/rules/all", "alerts_by_rule"),
        ("/alerts/rules/hosts/all", "alerts_by_rule_per_host"),
    ],
)
def test_alert_counts_cover_only_the_callers_customers(path, key):
    async def scenario(client, db):
        response = await client.post(path, json=SEARCH, headers=as_user("ana"))
        assert response.status_code == 200, response.text
        return response.json()[key]

    with indexer():
        rows = call(scenario)
    counted = sum(row["number_of_alerts"] for row in rows)
    rules = {row["rule"] for row in rows if "rule" in row}
    assert counted == len(ACME_IDS)
    assert "rule globex" not in rules


@pytest.mark.parametrize(
    ("who", "doc_id", "index", "found"),
    [("ana", "globex", "wazuh-globex_1", False), ("ana", "acme", "wazuh-acme_1", True), ("admin", "globex", "wazuh-globex_1", True)],
)
def test_a_document_by_id_of_another_customer_reads_like_a_missing_one(who, doc_id, index, found):
    async def scenario(client, db):
        response = await client.post("/alerts/by-id", json={"index_name": index, "alert_id": doc_id}, headers=as_user(who))
        assert response.status_code == 200, response.text
        return response.json()

    with indexer():
        body = call(scenario)
    assert body["success"] is found
    if not found:
        assert body["alert"]["_source"] == {"message": "alert not found"}
        assert body["message"] == f"Alert {doc_id} not found in index {index}"


# --- incidents: details, timeline, manual creation, the backlog ----------------------------------


@pytest.mark.parametrize(
    ("who", "doc_id", "index", "status"),
    [("ana", "globex", "wazuh-globex_1", 404), ("ana", "acme", "wazuh-acme_1", 200), ("admin", "globex", "wazuh-globex_1", 200)],
)
def test_alert_details_of_another_customer_are_refused(who, doc_id, index, status):
    async def scenario(client, db):
        return await client.post("/incidents/alerts/alert/details", json={"index_name": index, "index_id": doc_id}, headers=as_user(who))

    with indexer():
        response = call(scenario)
    assert response.status_code == status, response.text
    if status == 404:
        assert detail(response) == document_access.DOCUMENT_NOT_FOUND
        assert "GLOBEX" not in response.text


def test_a_timeline_holds_only_the_callers_customers_events():
    # Anchored on GLOBEX's document: its process on web-01 matches events of both customers.
    async def scenario(client, db):
        response = await client.post(
            "/incidents/alerts/alert/timeline",
            json={"index_name": "wazuh-acme_1", "index_id": "acme"},
            headers=as_user("ana"),
        )
        assert response.status_code == 200, response.text
        return {hit["_id"] for hit in response.json()["alert_timeline"]}

    with indexer():
        assert call(scenario) == {"acme"}


@pytest.mark.parametrize(
    ("who", "doc_id", "index", "reached"),
    [("ana", "globex", "wazuh-globex_1", False), ("ana", "acme", "wazuh-acme_1", True), ("admin", "globex", "wazuh-globex_1", True)],
)
def test_a_manual_alert_is_filed_only_under_one_of_the_callers_customers(who, doc_id, index, reached):
    # Past the check, alert creation goes on to the customer's settings: stopped there with a 418.
    settings = AsyncMock(side_effect=HTTPException(status_code=418, detail="reached creation"))

    async def scenario(client, db):
        with patch("app.incidents.services.incident_alert.validate_syslog_type_source", AsyncMock()), patch(
            "app.incidents.services.incident_alert.is_customer_code_valid",
            settings,
        ):
            return await client.post(
                "/incidents/alerts/create/manual",
                json={"index_name": index, "alert_id": doc_id},
                headers=as_user(who),
            )

    with indexer():
        response = call(scenario)
    assert response.status_code == (418 if reached else 404), response.text
    assert settings.await_count == (1 if reached else 0)


def test_the_ingest_backlog_is_an_admins_view():
    backlog = AsyncMock(return_value=SimpleNamespace(alerts=[]))

    async def scenario(client, db):
        with patch("app.incidents.routes.incident_alert.get_alerts_not_created_in_copilot", backlog):
            refused = await client.get("/incidents/alerts/alerts/not-created", headers=as_user("ana"))
        return refused

    with indexer():
        refused = call(scenario)
    assert refused.status_code == 403
    backlog.assert_not_awaited()


# --- the AI routes send nothing of another customer's -------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["/threat_intel/ai/analyze-alert", "/threat_intel/ai/wazuh-exclusion-rule", "/threat_intel/ai/velociraptor-artifact-recommendation"],
)
def test_an_ai_route_never_sends_another_customers_document(path):
    lookups = AsyncMock()

    async def scenario(client, db):
        with patch("app.threat_intel.routes.socfortress.socfortress_ai_alert_lookup", lookups), patch(
            "app.threat_intel.routes.socfortress.socfortress_wazuh_exclusion_rule_lookup",
            lookups,
        ), patch("app.threat_intel.routes.socfortress.socfortress_velociraptor_recommendation_lookup", lookups):
            return await client.post(path, json={"index_name": "wazuh-globex_1", "index_id": "globex"}, headers=as_user("ana"))

    with indexer():
        response = call(scenario)
    assert response.status_code == 404
    lookups.assert_not_awaited()


# --- MITRE, CoPilot Searches, packages, Graylog events ------------------------------------------


@pytest.mark.parametrize(("who", "scoped"), [("ana", True), ("admin", False)])
def test_mitre_searches_carry_the_callers_customers(who, scoped):
    techniques = AsyncMock(return_value={"total_alerts": 0, "techniques_count": 0, "techniques": [], "field_used": "rule_mitre_id"})
    alerts = AsyncMock(
        return_value={"alerts": [], "total_alerts": 0, "technique_id": "T1047", "technique_name": "", "field_used": "rule_mitre_id"},
    )

    async def scenario(client, db):
        with patch("app.connectors.wazuh_manager.routes.mitre.search_mitre_techniques_in_alerts", techniques), patch(
            "app.connectors.wazuh_manager.routes.mitre.get_alerts_by_mitre_id",
            alerts,
        ):
            await client.get("/wazuh_manager/mitre/techniques/alerts?index_pattern=*", headers=as_user(who))
            await client.get("/wazuh_manager/mitre/techniques/T1047/alerts?index_pattern=*", headers=as_user(who))

    with indexer():
        call(scenario)
    for mock in (techniques, alerts):
        filters = mock.await_args.kwargs["additional_filters"]
        carried = [f for f in filters if "bool" in f]
        if scoped:
            assert len(carried) == 1
            assert {d["_id"] for d in DOCS if matches(d["_source"], carried[0])} == ACME_IDS
        else:
            assert carried == []


@pytest.mark.parametrize(("who", "scoped"), [("ana", True), ("admin", False)])
def test_a_rule_search_is_narrowed_to_the_callers_customers(who, scoped):
    execute = AsyncMock(
        return_value={
            "rule_id": "r",
            "rule_name": "r",
            "total_hits": 0,
            "returned_hits": 0,
            "took_ms": 0,
            "hits": [],
            "query_executed": {},
        },
    )

    async def scenario(client, db):
        with patch("app.integrations.copilot_searches.routes.copilot_searches.execute_rule_search", execute):
            await client.post(
                "/copilot_searches/execute",
                json={"rule_id": "r", "index_pattern": "*", "parameters": {}},
                headers=as_user(who),
            )

    with indexer():
        call(scenario)
    scope = execute.await_args.kwargs["scope"]
    assert (scope is not None) is scoped
    if scoped:
        assert {d["_id"] for d in DOCS if matches(d["_source"], scope)} == ACME_IDS


def test_a_rule_search_wraps_the_rules_query_in_the_scope():
    from app.integrations.copilot_searches.schema.copilot_searches import (
        ExecuteSearchRequest,
    )
    from app.integrations.copilot_searches.services import copilot_searches as service

    rule_query = {"match": {"rule_description": "rule acme"}}
    rule = {"id": "r", "name": "r", "search": {"query": rule_query}}
    scope = {"terms": {"agent_labels_customer": ["ACME"]}}
    fake = FakeIndexer(DOCS)
    with patch.object(service.rules_cache, "ensure_loaded", AsyncMock()), patch.object(
        service.rules_cache,
        "get_rule_by_id",
        lambda rule_id: rule,
    ), patch.object(
        service,
        "_validate_parameters",
        lambda r, params: (params, []),
    ), patch.object(
        service,
        "create_wazuh_indexer_client_async",
        AsyncMock(return_value=_AsyncClient(fake)),
    ):
        result = asyncio.run(service.execute_rule_search(ExecuteSearchRequest(rule_id="r", index_pattern="*", parameters={}), scope=scope))
    assert fake.searches[0]["body"]["query"] == {"bool": {"must": [rule_query], "filter": [scope]}}
    assert [hit.id for hit in result.hits] == ["acme"]


@pytest.mark.parametrize(
    ("who", "expected"),
    [("ana", {("001", "web-01")}), ("admin", {("001", "web-01"), ("001", "db-01"), ("002", "mail-01")})],
)
def test_the_package_search_keeps_to_the_callers_agents_by_exact_pair(who, expected):
    packages = [
        {
            "_index": "wazuh-states-inventory-packages-x",
            "_id": f"p{i}",
            "_source": {"agent": {"id": agent_id, "name": name}, "package": {"name": "openssl"}},
        }
        for i, (agent_id, name) in enumerate([("001", "web-01"), ("001", "db-01"), ("002", "mail-01")])
    ]

    async def scenario(client, db):
        response = await client.get("/syscollector/search/packages?package_name=openssl", headers=as_user(who))
        assert response.status_code == 200, response.text
        return {(p["agent"]["id"], p["agent"]["name"]) for p in response.json()["packages"]}

    with indexer(docs=packages):
        assert call(scenario) == expected


def _graylog_event(event_id, customer):
    fields = {"CUSTOMER_CODE": customer} if customer else {}
    return {
        "event": {
            "alert": True,
            "event_definition_id": f"def-{event_id}",
            "event_definition_type": "aggregation-v1",
            "fields": fields,
            "group_by_fields": {},
            "id": event_id,
            "key_tuple": [],
            "message": f"event {event_id}",
            "origin_context": "",
            "priority": 2,
            "source": "graylog",
            "source_streams": [f"stream-{event_id}"],
            "streams": [],
            "timestamp": "2026-11-20T10:00:00Z",
            "timestamp_processing": "2026-11-20T10:00:00Z",
        },
        "index_name": "gl-events_0",
        "index_type": "message",
    }


def test_graylog_events_are_asked_and_kept_for_the_callers_customers_only():
    sent = {}

    async def fake_post(endpoint, data):
        sent["query"] = data["query"]
        events = [_graylog_event("e1", "ACME"), _graylog_event("e2", "GLOBEX"), _graylog_event("e3", None)]
        return {
            "success": True,
            "data": {
                "context": {
                    "event_definitions": {},
                    "streams": {f"stream-{e}": {"id": f"stream-{e}", "title": e, "description": ""} for e in ("e1", "e2", "e3")},
                },
                "duration": 1,
                "events": events,
                "parameters": {
                    "page": 1,
                    "per_page": 100,
                    "query": data["query"],
                    "sort_by": "timestamp",
                    "sort_direction": "desc",
                    "timerange": {"range": 86400, "type": "relative"},
                    "filter": {"alerts": "only", "event_definitions": []},
                },
                "total_events": 3,
                "used_indices": ["gl-events_0"],
            },
        }

    async def scenario(client, db):
        with patch("app.connectors.graylog.services.events.send_post_request", fake_post):
            response = await client.post("/graylog/event/alerts", json={"query": "source:fw"}, headers=as_user("ana"))
        assert response.status_code == 200, response.text
        return response.json()["alerts"]

    with indexer():
        alerts = call(scenario)
    assert sent["query"] == '(source:fw) AND fields.CUSTOMER_CODE:("ACME")'
    assert [e["event"]["id"] for e in alerts["events"]] == ["e1"]
    assert alerts["total_events"] == 1
    assert set(alerts["context"]["streams"]) == {"stream-e1"}


# --- names, agents, MCP, the catalog ------------------------------------------------------------


def test_shards_list_only_the_callers_customers_indices():
    listed = ShardsResponse(
        shards=[
            Shards(index=name, shard=0, state="STARTED") for name in ("wazuh-acme_1", "wazuh-globex_1", "acme-corp_0", "wazuh-acme2_0")
        ],
        message="ok",
        success=True,
    )

    async def scenario(client, db):
        with patch("app.connectors.wazuh_indexer.routes.monitoring.shards", AsyncMock(return_value=listed)):
            ana = await client.get("/wazuh_indexer/shards", headers=as_user("ana"))
        return {s["index"] for s in ana.json()["shards"]}

    with indexer():
        # acme2 is another customer's code, not ACME's: a whole-word match only.
        assert call(scenario) == {"wazuh-acme_1", "acme-corp_0"}


@pytest.mark.parametrize(("index_name", "status"), [("wazuh-globex_1", 404), ("wazuh-acme_1", 200)])
def test_field_mappings_are_read_only_for_the_callers_customers_indices(index_name, status):
    async def scenario(client, db):
        with patch("app.incidents.routes.db_operations.get_index_mappings_key_names", AsyncMock(return_value=["agent_name"])), patch(
            "app.incidents.routes.db_operations.get_index_source",
            AsyncMock(return_value="wazuh"),
        ):
            mappings = await client.get(
                f"/incidents/db_operations/mappings/fields-assets-title-and-timefield?index_name={index_name}",
                headers=as_user("ana"),
            )
            source = await client.get(f"/incidents/db_operations/available-source/{index_name}", headers=as_user("ana"))
        return mappings, source

    with indexer():
        mappings, source = call(scenario)
    assert mappings.status_code == status and source.status_code == status


def test_another_customers_agent_vulnerabilities_are_refused():
    service = AsyncMock(return_value={"vulnerabilities": [], "total_count": 0, "success": True, "message": "ok"})

    async def scenario(client, db):
        with patch("app.agents.vulnerabilities.routes.vulnerabilities.get_vulnerabilities_by_agent", service):
            return await client.get("/vulnerabilities/agent/002", headers=as_user("ana"))

    with indexer():
        response = call(scenario)
    assert response.status_code == 403
    service.assert_not_awaited()


#: The AI Chatbot's local servers, which the removed copilot-mcp container answered from every
#: customer's data with deployment-wide credentials.
REMOVED_MCP_SERVERS = ("wazuh-indexer", "wazuh-manager", "copilot", "velociraptor")


def test_the_chatbot_reaches_no_local_data_server():
    from app.integrations.copilot_mcp.schema.copilot_mcp import MCPServerType
    from app.integrations.copilot_mcp.services.copilot_mcp import MCPService

    cloud = {server.value for server in MCPServerType}
    assert cloud == {"threat-intel", "cyber-news", "knowledgebase", "attack-surface"}
    assert all(MCPService.build_full_url(server).startswith("https://mcp.socfortress.co/") for server in MCPServerType)
    execute = AsyncMock(return_value={"success": True, "message": "ok", "result": "", "execution_time": 0.0})

    async def scenario(client, db):
        with patch("app.integrations.copilot_mcp.routes.copilot_mcp.MCPService.execute_query", execute):
            listed = [await client.get("/copilot_mcp/servers", headers=as_user(who)) for who in ("ana", "admin")]
            refused = [
                await client.post("/copilot_mcp/query", json={"input": "list alerts", "mcp_server": server}, headers=as_user("admin"))
                for server in REMOVED_MCP_SERVERS
            ]
        return listed, refused

    with indexer():
        listed, refused = call(scenario)
    # An analyst and an admin see the same servers: all of them cloud ones.
    assert [{s["value"] for s in response.json()["servers"]} for response in listed] == [cloud, cloud]
    # Naming a removed server is refused, for an admin too, before anything is asked.
    assert [response.status_code for response in refused] == [400] * len(REMOVED_MCP_SERVERS)
    execute.assert_not_awaited()


@pytest.mark.parametrize(("who", "withheld"), [("ana", True), ("admin", False)])
def test_the_catalogs_deployment_wide_hit_counts_are_an_admins_view(who, withheld):
    rules = {
        "rules": [
            {
                "id": 1,
                "level": 3,
                "status": "enabled",
                "description": "r",
                "filename": "f",
                "relative_dirname": "d",
                "groups": [],
                "mitre": [],
                "hits_7d": 5,
                "hits_30d": 9,
                "last_seen": "2026-11-20T10:00:00Z",
            },
        ],
        "total": 1,
        "available": True,
        "unavailable_reason": None,
        "last_refresh": None,
        "firing_stats_available": True,
        "firing_stats_unavailable_reason": None,
        "firing_stats_last_refresh": None,
        "firing_stats_loading": False,
        "customer_firing_stats_status": None,
        "customer_firing_stats_error": None,
        "customer_code": "",
    }

    async def scenario(client, db):
        with patch(
            "app.integrations.copilot_searches.routes.copilot_searches.list_wazuh_rules",
            AsyncMock(return_value={**rules, "rules": [dict(rules["rules"][0])]}),
        ):
            return await client.get("/copilot_searches/catalog/wazuh-rules", headers=as_user(who))

    with indexer():
        body = call(scenario).json()
    assert body["firing_stats_available"] is not withheld
    assert body["rules"][0]["hits_30d"] == (0 if withheld else 9)


# --- every route that reads the indexer is in this file -----------------------------------------

#: The audited routes and what keeps each to the caller's customers. A new route reading the
#: indexer belongs here, with a test above.
INDEXER_ROUTES = {
    ("POST", "/alerts/by-id"): "document_visible",
    ("POST", "/alerts"): "customer_filter",
    ("POST", "/alerts/host"): "customer_filter",
    ("POST", "/alerts/index"): "customer_filter",
    ("POST", "/alerts/hosts/all"): "customer_filter",
    ("POST", "/alerts/rules/all"): "customer_filter",
    ("POST", "/alerts/rules/hosts/all"): "customer_filter",
    ("POST", "/alerts/alerts/graylog/index"): "resolve_effective_customers",
    ("POST", "/alerts/alerts/graylog"): "resolve_effective_customers",
    ("GET", "/wazuh_manager/mitre/techniques/alerts"): "customer_filter",
    ("GET", "/wazuh_manager/mitre/techniques/{technique_id}/alerts"): "customer_filter",
    ("POST", "/copilot_searches/execute"): "customer_filter",
    ("POST", "/incidents/alerts/alert/details"): "ensure_document_access",
    ("POST", "/incidents/alerts/alert/timeline"): "customer_filter",
    ("POST", "/incidents/alerts/create/manual"): "acting_user",
    ("POST", "/threat_intel/ai/analyze-alert"): "_alert_for_ai",
    ("POST", "/threat_intel/ai/wazuh-exclusion-rule"): "_alert_for_ai",
    ("POST", "/threat_intel/ai/velociraptor-artifact-recommendation"): "_alert_for_ai",
    ("POST", "/graylog/event/alerts"): "keep_customer_events",
    ("GET", "/syscollector/search/packages"): "agent_filters",
}


def test_every_indexer_alert_route_is_accounted_for():
    from fastapi.routing import APIRoute

    from app.connectors.wazuh_indexer.routes.alerts import wazuh_indexer_alerts_router

    declared = {
        (method, "/alerts" + route.path)
        for route in wazuh_indexer_alerts_router.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }
    assert declared <= set(INDEXER_ROUTES), sorted(declared - set(INDEXER_ROUTES))


@pytest.mark.parametrize(("route", "guard"), sorted(INDEXER_ROUTES.items()))
def test_each_audited_route_uses_its_guard(route, guard):
    import inspect

    from fastapi.routing import APIRoute

    from app.routers import agents
    from app.routers import copilot_searches
    from app.routers import graylog
    from app.routers import incidents
    from app.routers import threat_intel
    from app.routers import wazuh_indexer
    from app.routers import wazuh_manager

    api = FastAPI()
    for module in (agents, copilot_searches, graylog, incidents, threat_intel, wazuh_indexer, wazuh_manager):
        api.include_router(module.router)
    method, path = route
    matched = [r for r in api.routes if isinstance(r, APIRoute) and r.path == path and method in r.methods]
    assert len(matched) == 1, f"{method} {path} not found"
    assert guard in inspect.getsource(matched[0].endpoint), f"{method} {path} no longer uses {guard}"
