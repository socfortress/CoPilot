"""The Customer Portal Exposure page (#1289): vulnerabilities and compliance across a tenant.

Real routers, real in-memory database, real request parsing; Wazuh is ``tests/exposure_support``
(an indexer evaluating the page's query DSL, and a manager answering SCA per agent).

Pinned here:
- a missing switch row reads as off, and a disabled customer's agents are never named to Wazuh;
- only an admin flips the switch (audited); an analyst reads it for customers they see;
- a portal user's figures come from their own customer's agents only, filtered by Wazuh id
  *and* name: another tenant's agent sharing the id or the hostname never counts;
- counts per severity, totals, ranking (CVSS, then hosts), the severity filter, search,
  paging, a CVE's agents, the CSV (formula cells defused) and its limit;
- compliance per policy, the agents Wazuh could not answer for, the cache, a total outage;
- Wazuh's error text never reaches the browser;
- the pure query builders and parsers.

Run with: cd backend && python -m pytest tests/test_customer_portal_exposure.py
"""

import asyncio
import csv
import io
import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("JWT_SECRET", "test-only-secret-not-the-compromised-default")

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402

from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.customer_portal.services import exposure_compliance  # noqa: E402
from app.customer_portal.services import exposure_vulnerabilities as vulns  # noqa: E402
from app.customer_portal.services.exposure import ExposureScope  # noqa: E402
from app.customer_portal.services.exposure import ScopedAgent  # noqa: E402
from app.db.db_session import get_db  # noqa: E402
from app.db.universal_models import Agents  # noqa: E402
from app.db.universal_models import CustomerPortalExposureSettings  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from tests.exposure_support import FakeIndexer  # noqa: E402
from tests.exposure_support import FakeManager  # noqa: E402
from tests.exposure_support import sca  # noqa: E402
from tests.exposure_support import vuln  # noqa: E402
from tests.soc_management_support import Db  # noqa: E402

USERS = {
    "admin": SimpleNamespace(id=1, username="admin", role_id=1),
    "ana": SimpleNamespace(id=2, username="ana", role_id=2),
    "portal": SimpleNamespace(id=4, username="portal", role_id=4),
}
SCOPES = {"admin": ["admin"], "ana": ["analyst"], "portal": ["customer_user"]}
BASE = "/customer_portal/exposure"

# ACME has web-01 (001), db-01 (002) and vpn-01 (004). GLOBEX has an agent with ACME's
# hostname web-01 (003) and one with ACME's Wazuh id 001 (gx-01): neither may ever count.
AGENTS = [
    ("001", "web-01", "ACME"),
    ("002", "db-01", "ACME"),
    ("004", "vpn-01", "ACME"),
    ("003", "web-01", "GLOBEX"),
    ("001", "gx-01", "GLOBEX"),
]
DOCS = [
    vuln("001", "web-01", "CVE-2026-0001", "Critical", 9.8, package="openssl", version="1.0"),
    vuln("001", "web-01", "CVE-2026-0001", "Critical", 9.8, package="libssl", version="1.0", detected="2026-08-20T10:00:00Z"),
    vuln("002", "db-01", "CVE-2026-0001", "Critical", 9.8, package="openssl", version="1.1"),
    vuln("002", "db-01", "CVE-2026-0002", "High", 7.5, package="=cmd|'/c calc'!A1", version="2.0"),
    vuln("001", "web-01", "CVE-2026-0003", "Low", 3.1, package="curl", version="8.0"),
    vuln("003", "web-01", "CVE-2026-0001", "Critical", 9.8, package="openssl"),
    vuln("001", "gx-01", "CVE-2099-9999", "Critical", 10.0, package="secret-globex"),
    vuln("003", "web-01", "CVE-2099-8888", "High", 8.0, package="globex-only"),
]
EPSS = {"CVE-2026-0001": "0.97", "CVE-2026-0002": "0.12"}


def _app(db: Db) -> FastAPI:
    from app.routers import customer_portal

    app = FastAPI()
    app.include_router(customer_portal.router)

    async def _session():
        async with db.session() as session:
            yield session

    app.dependency_overrides[get_db] = _session
    return app


async def _seed(db: Db, enabled) -> None:
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
        for agent_id, hostname, code in AGENTS:
            session.add(
                Agents(
                    agent_id=agent_id,
                    hostname=hostname,
                    customer_code=code,
                    ip_address="10.0.0.1",
                    os="Linux",
                    label="",
                    wazuh_last_seen=datetime(2026, 10, 1),
                    wazuh_agent_version="4.9",
                ),
            )
        session.add_all([CustomerPortalExposureSettings(customer_code=code, enabled=True) for code in enabled])
        await session.commit()


def call(scenario, *, enabled=("ACME",), indexer=None, manager=None):
    indexer = indexer or FakeIndexer(DOCS)
    manager = manager or FakeManager(
        {"001": [sca("cis", 40), sca("pci", 90)], "002": [sca("cis", 60, failed=8)]},
        failing={"004"},
    )

    async def _inner():
        db = await Db().create()
        try:
            await _seed(db, enabled)
            transport = httpx.ASGITransport(app=_app(db))

            async def resolve_user(self, request, username):
                return USERS.get(username)

            exposure_compliance.clear_cache()
            with patch.object(AuthHandler, "decode_token", lambda self, token: (token, SCOPES.get(token, []))), patch.object(
                AuthHandler,
                "_resolve_user",
                resolve_user,
            ), patch.object(vulns, "indexer_search", indexer.search), patch.object(vulns, "indexer_scroll", indexer.scroll), patch.object(
                vulns,
                "epss_scores",
                AsyncMock(side_effect=lambda cves: {cve: EPSS[cve] for cve in cves if cve in EPSS}),
            ), patch.object(
                exposure_compliance,
                "collect_agent_sca",
                manager.collect_agent_sca,
            ):
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    return await scenario(client)
        finally:
            await db.dispose()

    return asyncio.run(_inner()), indexer, manager


def as_user(name):
    return {"Authorization": f"Bearer {name}"}


def severities(body):
    return {item["severity"]: (item["cves"], item["hosts"], item["findings"]) for item in body["severities"]}


# ── the switch ──────────────────────────────────────────────────────────────


def test_the_page_is_off_until_an_admin_turns_it_on():
    async def scenario(client):
        off = (await client.get(f"{BASE}/vulnerabilities", headers=as_user("portal"))).json()
        compliance = (await client.get(f"{BASE}/compliance", headers=as_user("portal"))).json()
        available = (await client.get(f"{BASE}/availability", headers=as_user("portal"))).json()
        with patch("app.customer_portal.routes.exposure.record_audit_event", AsyncMock()) as audit:
            refused = await client.put(f"{BASE}/settings/ACME", json={"enabled": True}, headers=as_user("ana"))
            turned_on = await client.put(f"{BASE}/settings/ACME", json={"enabled": True}, headers=as_user("admin"))
            again = await client.put(f"{BASE}/settings/ACME", json={"enabled": True}, headers=as_user("admin"))
        on = (await client.get(f"{BASE}/vulnerabilities", headers=as_user("portal"))).json()
        return off, compliance, available, refused, turned_on, again, audit, on

    (off, compliance, available, refused, turned_on, again, audit, on), indexer, manager = call(scenario, enabled=())
    assert off["enabled"] is False and compliance["enabled"] is False and available["enabled"] is False
    assert refused.status_code == 403
    assert turned_on.json()["settings"]["enabled"] is True and again.status_code == 200
    assert audit.await_count == 1 and audit.await_args.kwargs["new_value"] == {"enabled": True}
    assert on["enabled"] is True and on["customer_codes"] == ["ACME"]
    # Off, Wazuh was asked nothing; on, only ACME's agents.
    assert indexer.asked_agents() == {"001", "002", "004"}
    assert manager.asked == []


@pytest.mark.parametrize(
    "who, method, path, status",
    [
        ("ana", "get", "/settings/GLOBEX", 403),
        ("admin", "put", "/settings/NOPE", 404),
        ("portal", "put", "/settings/ACME", 403),
        ("portal", "get", "/settings/ACME", 403),
    ],
)
def test_who_may_read_and_flip_the_switch(who, method, path, status):
    async def scenario(client):
        kwargs = {"json": {"enabled": True}} if method == "put" else {}
        return await getattr(client, method)(f"{BASE}{path}", headers=as_user(who), **kwargs)

    response, _, _ = call(scenario)
    assert response.status_code == status


def test_the_portal_surface_writes_only_the_operators_switch():
    from app.routers import customer_portal

    writes = {
        (method, route.path)
        for route in customer_portal.router.routes
        if isinstance(route, APIRoute) and route.path.startswith("/customer_portal/exposure")
        for method in route.methods
        if method != "GET"
    }
    assert writes == {("PUT", "/customer_portal/exposure/settings/{customer_code}")}


# ── vulnerabilities ─────────────────────────────────────────────────────────


def test_a_portal_user_counts_their_own_agents_only():
    async def scenario(client):
        return (await client.get(f"{BASE}/vulnerabilities", headers=as_user("portal"))).json()

    body, indexer, _ = call(scenario, enabled=("ACME", "GLOBEX"))
    assert body["error"] is None and body["agents_in_scope"] == 3
    assert severities(body) == {"Critical": (1, 2, 3), "High": (1, 1, 1), "Medium": (0, 0, 0), "Low": (1, 1, 1)}
    assert body["totals"] == {"cves": 3, "hosts": 2, "findings": 5}
    assert [(row["cve_id"], row["cvss"], row["hosts"]) for row in body["cves"]] == [
        ("CVE-2026-0001", 9.8, 2),
        ("CVE-2026-0002", 7.5, 1),
        ("CVE-2026-0003", 3.1, 1),
    ]
    first = body["cves"][0]
    assert first["severity"] == "Critical" and first["epss"] == "0.97"
    assert first["packages"] == ["openssl", "libssl"] and first["first_detected"] == "2026-08-20T10:00:00Z"
    assert body["cves"][2]["epss"] is None
    # GLOBEX's agents share ACME's id (gx-01) or name (web-01 as 003): neither counted, neither asked.
    assert "CVE-2099" not in str(body)
    assert indexer.asked_agents() == {"001", "002", "004"}


def test_the_severity_filter_narrows_the_list_but_not_the_counts():
    async def scenario(client):
        return (await client.get(f"{BASE}/vulnerabilities", params={"severity": "High"}, headers=as_user("portal"))).json()

    body, _, _ = call(scenario)
    assert [row["cve_id"] for row in body["cves"]] == ["CVE-2026-0002"]
    assert body["totals"] == {"cves": 1, "hosts": 1, "findings": 1} and body["total_cves"] == 1
    assert severities(body)["Critical"] == (1, 2, 3)


@pytest.mark.parametrize(
    "search, expected",
    [("cve-2026-0003", ["CVE-2026-0003"]), ("SSL", ["CVE-2026-0001"]), ("cur", ["CVE-2026-0003"]), ("*", [])],
)
def test_search_by_cve_prefix_or_package(search, expected):
    async def scenario(client):
        return (await client.get(f"{BASE}/vulnerabilities", params={"search": search}, headers=as_user("portal"))).json()

    body, _, _ = call(scenario)
    assert [row["cve_id"] for row in body["cves"]] == expected


def test_pages_follow_the_ranking():
    async def scenario(client):
        return (await client.get(f"{BASE}/vulnerabilities", params={"page": 2, "page_size": 1}, headers=as_user("portal"))).json()

    body, _, _ = call(scenario)
    assert [row["cve_id"] for row in body["cves"]] == ["CVE-2026-0002"]
    assert body["total_cves"] == 3 and body["page"] == 2 and body["page_size"] == 1


def test_an_unreadable_indexer_is_an_error_without_its_text():
    async def scenario(client):
        return (await client.get(f"{BASE}/vulnerabilities", headers=as_user("portal"))).json()

    body, _, _ = call(scenario, indexer=FakeIndexer(DOCS, fail=True))
    assert body["error"] == vulns.READ_ERROR and body["cves"] == []
    assert "10.0.0.9" not in str(body)


def test_a_cve_lists_the_callers_agents_it_affects():
    async def scenario(client):
        detail = (await client.get(f"{BASE}/vulnerabilities/cve/CVE-2026-0001", headers=as_user("portal"))).json()
        foreign = (await client.get(f"{BASE}/vulnerabilities/cve/CVE-2099-9999", headers=as_user("portal"))).json()
        bad = await client.get(f"{BASE}/vulnerabilities/cve/..%2Fx", headers=as_user("portal"))
        return detail, foreign, bad

    (detail, foreign, bad), _, _ = call(scenario, enabled=("ACME", "GLOBEX"))
    assert [(a["agent_id"], a["hostname"], a["package"]) for a in detail["agents"]] == [
        ("002", "db-01", "openssl"),
        ("001", "web-01", "libssl"),
        ("001", "web-01", "openssl"),
    ]
    assert {a["customer_code"] for a in detail["agents"]} == {"ACME"}
    assert detail["epss"] == "0.97" and detail["cvss"] == 9.8 and detail["severity"] == "Critical"
    assert detail["references"] == ["https://example.org/a", "https://example.org/b"]
    # Another tenant's CVE is nothing at all to this caller.
    assert foreign["agents"] == [] and foreign["description"] is None
    assert bad.status_code in (404, 422)


def test_a_cve_is_refused_while_the_page_is_off():
    async def scenario(client):
        return await client.get(f"{BASE}/vulnerabilities/cve/CVE-2026-0001", headers=as_user("portal"))

    response, _, _ = call(scenario, enabled=())
    assert response.status_code == 404


def test_the_csv_has_a_row_per_finding_and_defuses_formulas():
    async def scenario(client):
        return await client.get(f"{BASE}/vulnerabilities/export", headers=as_user("portal"))

    response, _, _ = call(scenario)
    assert response.status_code == 200 and response.headers["x-export-truncated"] == "false"
    assert "attachment" in response.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == vulns.CSV_HEADER
    assert len(rows) == 6
    # Most severe first, then by CVE and host.
    assert [row[0] for row in rows[1:]] == ["CVE-2026-0001"] * 3 + ["CVE-2026-0002", "CVE-2026-0003"]
    formula = next(row for row in rows if row[0] == "CVE-2026-0002")
    assert formula[4].startswith("'=") and formula[3] == "0.12" and formula[6] == "db-01" and formula[7] == "ACME"
    assert "secret-globex" not in response.text


def test_the_csv_stops_at_its_limit_and_says_so():
    async def scenario(client):
        with patch.object(vulns, "EXPORT_LIMIT", 2):
            return await client.get(f"{BASE}/vulnerabilities/export", params={"severity": "Critical"}, headers=as_user("portal"))

    response, _, _ = call(scenario)
    assert response.headers["x-export-truncated"] == "true"
    assert len(list(csv.reader(io.StringIO(response.text)))) == 3


def test_the_csv_is_a_generic_502_when_the_indexer_fails_and_a_404_when_off():
    async def failing(client):
        return await client.get(f"{BASE}/vulnerabilities/export", headers=as_user("portal"))

    response, _, _ = call(failing, indexer=FakeIndexer(DOCS, fail=True))
    assert response.status_code == 502 and "10.0.0.9" not in response.text
    off, _, _ = call(failing, enabled=())
    assert off.status_code == 404


# ── compliance ──────────────────────────────────────────────────────────────


def test_compliance_by_policy_counts_the_agents_wazuh_could_not_answer_for():
    async def scenario(client):
        return (await client.get(f"{BASE}/compliance", headers=as_user("portal"))).json()

    body, _, manager = call(scenario, enabled=("ACME", "GLOBEX"))
    assert body["error"] is None and body["agents_in_scope"] == 3
    assert body["unavailable_agents"] == 1 and body["agents_assessed"] == 2
    assert body["average_score"] == 63.3 and body["weak_score"] == exposure_compliance.WEAK_SCORE
    assert [(p["policy_id"], p["average_score"], p["agents"], p["agents_below"], p["failed"]) for p in body["policies"]] == [
        ("cis", 50.0, 2, 1, 13),
        ("pci", 90.0, 1, 0, 5),
    ]
    assert sorted(manager.asked) == ["001", "002", "004"]
    assert "10.0.0.8" not in str(body)


def test_compliance_is_kept_a_while_then_read_again():
    async def scenario(client):
        await client.get(f"{BASE}/compliance", headers=as_user("portal"))
        await client.get(f"{BASE}/compliance/cis/agents", headers=as_user("portal"))
        await client.get(f"{BASE}/compliance", headers=as_user("portal"))
        with patch.object(exposure_compliance, "cache_ttl", lambda: 0):
            await client.get(f"{BASE}/compliance", headers=as_user("portal"))

    _, _, manager = call(scenario)
    assert len(manager.asked) == 6  # 3 agents, read twice: once at first, once when stale


def test_a_total_outage_is_an_error_and_is_not_kept():
    manager = FakeManager({}, failing={"001", "002", "004"})

    async def scenario(client):
        first = (await client.get(f"{BASE}/compliance", headers=as_user("portal"))).json()
        policy = (await client.get(f"{BASE}/compliance/cis/agents", headers=as_user("portal"))).json()
        return first, policy

    (first, policy), _, manager = call(scenario, manager=manager)
    assert first["error"] == exposure_compliance.READ_ERROR and first["policies"] == []
    assert policy["error"] == exposure_compliance.READ_ERROR
    assert len(manager.asked) == 6  # not cached: asked again for the policy


def test_a_policy_lists_its_agents_weakest_first():
    async def scenario(client):
        return (await client.get(f"{BASE}/compliance/cis/agents", headers=as_user("portal"))).json()

    body, _, _ = call(scenario)
    assert body["name"] == "Policy cis"
    assert [(a["hostname"], a["score"], a["failed"]) for a in body["agents"]] == [("web-01", 40, 5), ("db-01", 60, 8)]


# ── pure helpers ────────────────────────────────────────────────────────────


def _scope():
    return ExposureScope(customer_codes=["ACME"], agents=[ScopedAgent("001", "web-01", "ACME"), ScopedAgent("002", "db-01", "ACME")])


def test_every_query_names_the_scopes_agents_by_id_and_name():
    scope = _scope()
    for body in (
        vulns.overview_body(scope, "High", "ssl", 1, 25),
        vulns.details_body(scope, ["CVE-1"]),
        vulns.cve_body(scope, "CVE-1"),
        vulns.export_body(scope, None, None),
    ):
        filters = body["query"]["bool"]["filter"]
        assert {"terms": {"agent.id": ["001", "002"]}} in filters
        assert {"terms": {"agent.name": ["db-01", "web-01"]}} in filters
        (script,) = [clause["script"]["script"] for clause in filters if "script" in clause]
        assert script["params"]["pairs"] == {"001|web-01": 1, "002|db-01": 1}


def test_search_is_a_cve_prefix_or_an_escaped_package_wildcard():
    assert vulns.search_clause(" cve-2026-1 ") == {"prefix": {"vulnerability.id": "CVE-2026-1"}}
    assert vulns.search_clause("a*b?c\\") == {
        "wildcard": {"package.name": {"value": "*a\\*b\\?c\\\\*", "case_insensitive": True}},
    }
    assert vulns.search_clause("  ") is None
    assert len(vulns.search_clause("x" * 500)["wildcard"]["package.name"]["value"]) == vulns.SEARCH_MAX_LENGTH + 2


@pytest.mark.parametrize(
    "value, expected",
    [
        ("2026-09-01T10:00:00.123Z", "2026-09-01T10:00:00Z"),
        ("2026-09-01T12:00:00+02:00", "2026-09-01T10:00:00Z"),
        (1788256800000, "2026-09-01T10:00:00Z"),
        ("2026-09-01T10:00:00", "2026-09-01T10:00:00Z"),
        ("yesterday", None),
        (None, None),
    ],
)
def test_dates_are_read_as_utc(value, expected):
    assert vulns.utc_iso(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [(9.800000190734863, 9.8), (3.0999999046325684, 3.1), ("7.5", 7.5), (None, None), ("n/a", None)],
)
def test_cvss_is_read_to_its_one_decimal(value, expected):
    """The indexer keeps scores as 32-bit floats: found against OpenSearch by the indexer e2e."""
    assert vulns.cvss(value) == expected


def test_references_are_split_and_capped():
    assert vulns.references("a, b,,c") == ["a", "b", "c"]
    assert vulns.references(["x", " y "]) == ["x", "y"]
    assert len(vulns.references(",".join(str(i) for i in range(50)))) == 20
    assert vulns.references(None) == []


@pytest.mark.parametrize("value, expected", [("=1+1", "'=1+1"), ("+x", "'+x"), ("-1", "'-1"), ("@sum", "'@sum"), ("ok", "ok"), (None, "")])
def test_csv_cells_never_start_a_formula(value, expected):
    assert vulns.csv_cell(value) == expected


def test_a_document_pairing_one_agents_id_with_anothers_name_never_counts():
    """Two of the caller's customers, and a third customer's agent sharing an id and a name with them."""
    docs = [
        vuln("001", "web-01", "CVE-2026-0001"),
        vuln("002", "db-01", "CVE-2026-0002"),
        vuln("001", "db-01", "CVE-2099-0001", "Critical", 10.0),  # another manager's agent 001, named db-01
    ]

    async def scenario(client):
        return (await client.get(f"{BASE}/vulnerabilities", headers=as_user("admin"))).json()

    body, _, _ = call(scenario, enabled=("ACME",), indexer=FakeIndexer(docs))
    assert [row["cve_id"] for row in body["cves"]] == ["CVE-2026-0001", "CVE-2026-0002"]
    assert body["totals"]["findings"] == 2


def test_a_scope_owns_only_the_exact_id_and_name_pair():
    scope = _scope()
    assert scope.owner("001", "web-01").customer_code == "ACME"
    assert scope.owner("001", "db-01") is None
    assert scope.owner(None, None) is None
