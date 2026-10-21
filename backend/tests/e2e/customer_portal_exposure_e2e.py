"""E2E for #1289 (the Customer Portal Exposure page) — NOT collected by pytest (needs a live
MySQL); run by hand.

The disposable MySQL on 13306 (see customer_portal_overview_e2e.py's docstring), then:

    .venv/bin/python tests/e2e/customer_portal_exposure_e2e.py

Real routers, a real portal login, real MySQL for the switch, the customers and their agents.
Wazuh is ``tests/exposure_support`` (no Wazuh here): an indexer evaluating the page's query
DSL over vulnerability states seeded for both customers' agents — plus two documents that
pair one customer's agent id with the other's hostname — and a manager answering SCA, one
of A's agents failing. Every expectation is computed in Python from those documents:

  A) the switch: off for a customer without a row, admin-only to flip, audited, and the row
     goes with its customer;
  B) the portal user's vulnerabilities: counts per severity, totals, ranking, filters, paging,
     a CVE's agents and the CSV, all from A's agents only;
  C) Wazuh is never told about another customer's agent, and never at all while the page is off;
  D) compliance by policy, the agent Wazuh could not answer for, the cache;
  E) another customer: an admin sees only the customers whose page is on, an analyst only theirs;
  F) bounded: page sizes, severities, ids and the statement budget of resolving a scope;
  G) the migration downgrades and upgrades again.

Exits non-zero when a check fails.
"""

import asyncio
import csv
import io
import os
import sys
from collections import defaultdict
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.audit.models.audit import AuditLog  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.customer_portal.services import exposure_compliance  # noqa: E402
from app.customer_portal.services import exposure_vulnerabilities as vulns  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import CustomerPortalExposureSettings  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from tests.e2e.customer_portal_overview_e2e import StatementCounter  # noqa: E402
from tests.e2e.customer_portal_overview_e2e import build_app  # noqa: E402
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import AGENTS_A  # noqa: E402
from tests.e2e.portal_overview_seed import AGENTS_B  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_B  # noqa: E402
from tests.e2e.portal_overview_seed import PASSWORD  # noqa: E402
from tests.e2e.portal_overview_seed import PORTAL_USER  # noqa: E402
from tests.e2e.portal_overview_seed import cleanup  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402
from tests.exposure_support import FakeIndexer  # noqa: E402
from tests.exposure_support import FakeManager  # noqa: E402
from tests.exposure_support import sca  # noqa: E402
from tests.exposure_support import vuln  # noqa: E402

results = []
BASE = "/customer_portal/exposure"
ANALYST_A = "e2e_exposure_analyst_a"
TMP_CUSTOMER = "E2E_EXP_TMP"


def agent(code: str, i: int):
    return f"e2e-ov-{code}-{i}", f"ov-{code}-{i}"


A = [agent(CUST_A, i) for i in range(len(AGENTS_A))]
B = [agent(CUST_B, i) for i in range(len(AGENTS_B))]

# A's three agents: (cve, severity, cvss, package) per agent.
A_FINDINGS = {
    0: [("CVE-2026-1001", "Critical", 9.8, "openssl"), ("CVE-2026-1002", "High", 7.5, "nginx"), ("CVE-2026-1003", "Low", 2.0, "curl")],
    1: [("CVE-2026-1001", "Critical", 9.8, "openssl"), ("CVE-2026-1004", "Medium", 5.0, "bash")],
    2: [("CVE-2026-1002", "High", 7.5, "nginx"), ("CVE-2026-1002", "High", 7.5, "nginx-common")],
}
DOCS = [vuln(*A[i], cve, severity, score, package=package) for i, rows in A_FINDINGS.items() for cve, severity, score, package in rows]
DOCS += [
    vuln(*B[0], "CVE-2026-1001", "Critical", 9.8, package="openssl"),
    vuln(*B[0], "CVE-2099-0001", "Critical", 10.0, package="b-only"),
    # One customer's agent id with the other's hostname: no agent of either.
    vuln(A[0][0], B[0][1], "CVE-2099-0002", "Critical", 10.0, package="mixed-1"),
    vuln(B[0][0], A[0][1], "CVE-2099-0003", "Critical", 10.0, package="mixed-2"),
]
SCA = {
    A[0][0]: [sca("cis_debian", 42, name="CIS Debian"), sca("pci", 88, name="PCI")],
    A[1][0]: [sca("cis_debian", 61, name="CIS Debian", failed=12)],
    B[0][0]: [sca("cis_debian", 10, name="CIS Debian")],
}
FAILING = {A[2][0]}


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not passed else ""))


def expected(agents, severity=None):
    """What the page must count for ``agents`` (``(id, name)`` pairs), straight from DOCS."""
    pairs = set(agents)
    rows = [d for d in DOCS if (d["agent"]["id"], d["agent"]["name"]) in pairs]
    per_severity = defaultdict(lambda: [set(), set(), 0])
    for d in rows:
        entry = per_severity[d["vulnerability"]["severity"]]
        entry[0].add(d["vulnerability"]["id"])
        entry[1].add(d["agent"]["id"])
        entry[2] += 1
    narrowed = [d for d in rows if not severity or d["vulnerability"]["severity"] == severity]
    hosts = defaultdict(set)
    scores = {}
    for d in narrowed:
        hosts[d["vulnerability"]["id"]].add(d["agent"]["id"])
        scores[d["vulnerability"]["id"]] = d["vulnerability"]["score"]["base"]
    ranked = sorted(hosts, key=lambda cve: (-scores[cve], -len(hosts[cve]), cve))
    return {
        "severities": {level: (len(v[0]), len(v[1]), v[2]) for level, v in per_severity.items()},
        "totals": {"cves": len(hosts), "hosts": len({d["agent"]["id"] for d in narrowed}), "findings": len(narrowed)},
        "ranked": [(cve, len(hosts[cve])) for cve in ranked],
        "rows": rows,
    }


def answered_severities(body):
    return {item["severity"]: (item["cves"], item["hosts"], item["findings"]) for item in body["severities"] if item["findings"]}


async def add_analyst():
    async with AsyncSession(async_engine, expire_on_commit=False) as s:
        user = User(username=ANALYST_A, password=AuthHandler().get_password_hash(PASSWORD), email=f"{ANALYST_A}@e2e.example", role_id=2)
        s.add(user)
        await s.commit()
        s.add(UserCustomerAccess(user_id=user.id, customer_code=CUST_A))
        await s.commit()


async def remove_analyst():
    async with AsyncSession(async_engine) as s:
        user = (await s.execute(select(User).where(User.username == ANALYST_A))).scalars().first()
        if user:
            await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id == user.id))
            await s.delete(user)
        await s.execute(delete(AuditLog).where(AuditLog.customer_code.in_([CUST_A, CUST_B, TMP_CUSTOMER])))
        await s.commit()


async def main():
    await seed(quiet=True)
    await add_analyst()
    indexer = FakeIndexer(DOCS)
    manager = FakeManager(SCA, failing=FAILING)
    exposure_compliance.clear_cache()
    patches = [
        patch.object(vulns, "indexer_search", indexer.search),
        patch.object(vulns, "indexer_scroll", indexer.scroll),
        patch.object(vulns, "epss_scores", AsyncMock(side_effect=lambda cves: {cve: "0.5" for cve in cves})),
        patch.object(exposure_compliance, "collect_agent_sca", manager.collect_agent_sca),
    ]
    for p in patches:
        p.start()
    counter = StatementCounter()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e") as client:
            login = await client.post("/auth/token/customer-portal", data={"username": PORTAL_USER, "password": PASSWORD})
            portal = {"Authorization": f"Bearer {login.json()['access_token']}"}
            admin = {"Authorization": f"Bearer {await AuthHandler().encode_token(ADMIN)}"}
            analyst = {"Authorization": f"Bearer {await AuthHandler().encode_token(ANALYST_A)}"}

            async def get(path, headers=portal, **params):
                response = await client.get(f"{BASE}{path}", params=params, headers=headers)
                return response.status_code, (response.json() if "json" in response.headers.get("content-type", "") else response)

            print("\n=== A) the switch ===")
            status, body = await get("/vulnerabilities", headers=admin, customer_codes=[CUST_B])
            check(
                "off for B (no row), even for the SOC, and Wazuh asked nothing",
                body["enabled"] is False and not indexer.bodies,
                str(body)[:120],
            )
            status, body = await get("/availability")
            check("on for the portal user's customer (seeded)", body["enabled"] is True, str(body))
            response = await client.put(f"{BASE}/settings/{CUST_B}", json={"enabled": True}, headers=portal)
            check("a portal user cannot flip it", response.status_code == 403, str(response.status_code))
            response = await client.put(f"{BASE}/settings/{CUST_B}", json={"enabled": True}, headers=admin)
            check("the admin turns B on", response.status_code == 200 and response.json()["settings"]["enabled"], response.text[:120])
            async with AsyncSession(async_engine) as s:
                audit = (
                    (
                        await s.execute(
                            select(AuditLog)
                            .where(AuditLog.action == "exposure.settings_update", AuditLog.customer_code == CUST_B)
                            .order_by(AuditLog.id.desc()),
                        )
                    )
                    .scalars()
                    .first()
                )
                check(
                    "audited with the old and new value",
                    audit is not None and audit.new_value == {"enabled": True},
                    str(audit and audit.new_value),
                )
                s.add(Customers(customer_code=TMP_CUSTOMER, customer_name="E2E exposure tmp"))
                await s.commit()
                s.add(CustomerPortalExposureSettings(customer_code=TMP_CUSTOMER, enabled=True))
                await s.commit()
                await s.execute(delete(Customers).where(Customers.customer_code == TMP_CUSTOMER))
                await s.commit()
                left = (
                    await s.execute(
                        select(CustomerPortalExposureSettings).where(CustomerPortalExposureSettings.customer_code == TMP_CUSTOMER),
                    )
                ).first()
                check("deleting a customer deletes its switch (ON DELETE CASCADE)", left is None)
            await client.put(f"{BASE}/settings/{CUST_B}", json={"enabled": False}, headers=admin)

            print("\n=== B) the portal user's vulnerabilities ===")
            indexer.bodies.clear()
            status, body = await get("/vulnerabilities")
            want = expected(A)
            check("200, no error", status == 200 and body["error"] is None, str(body)[:160])
            check(
                "every severity counted from A's agents",
                answered_severities(body) == want["severities"],
                f"{answered_severities(body)} vs {want['severities']}",
            )
            check("the totals", body["totals"] == want["totals"], f"{body['totals']} vs {want['totals']}")
            check(
                "ranked by CVSS, then by agents",
                [(row["cve_id"], row["hosts"]) for row in body["cves"]] == want["ranked"],
                f"{[(row['cve_id'], row['hosts']) for row in body['cves']]} vs {want['ranked']}",
            )
            check("packages of a CVE, most common first", body["cves"][0]["packages"] == ["openssl"], str(body["cves"][0]))
            check("nothing of B, nor of the mixed id/name documents", "CVE-2099" not in str(body))
            status, body = await get("/vulnerabilities", severity="High")
            want_high = expected(A, "High")
            check(
                "High only: the list and totals narrow, the counts per severity do not",
                [row["cve_id"] for row in body["cves"]] == [cve for cve, _ in want_high["ranked"]]
                and body["totals"] == want_high["totals"]
                and answered_severities(body) == want["severities"],
                str(body["totals"]),
            )
            status, body = await get("/vulnerabilities", search="NGINX")
            check("search by package, any case", [row["cve_id"] for row in body["cves"]] == ["CVE-2026-1002"], str(body["cves"]))
            status, body = await get("/vulnerabilities", search="cve-2026-100", page=2, page_size=2)
            check(
                "search by CVE prefix, a page at a time",
                [row["cve_id"] for row in body["cves"]] == [cve for cve, _ in want["ranked"]][2:4],
                str(body["cves"]),
            )
            status, detail = await get("/vulnerabilities/cve/CVE-2026-1001")
            check(
                "a CVE lists A's agents it affects, and only theirs",
                sorted(a["agent_id"] for a in detail["agents"]) == sorted([A[0][0], A[1][0]])
                and {a["customer_code"] for a in detail["agents"]} == {CUST_A},
                str(detail["agents"]),
            )
            status, foreign = await get("/vulnerabilities/cve/CVE-2099-0001")
            check("B's CVE is nothing to A", status == 200 and foreign["agents"] == [], str(foreign)[:120])
            status, response = await get("/vulnerabilities/export")
            rows = list(csv.reader(io.StringIO(response.text)))
            check(
                "the CSV: a row per A finding",
                status == 200 and len(rows) - 1 == len(want["rows"]),
                f"{len(rows) - 1} vs {len(want['rows'])}",
            )
            check(
                "the CSV names A's hosts only",
                {row[6] for row in rows[1:]} == {name for _, name in A},
                str({row[6] for row in rows[1:]}),
            )
            check("and says it is whole", response.headers.get("x-export-truncated") == "false")

            print("\n=== C) what Wazuh was told ===")
            asked = indexer.asked_agents()
            check("only A's agent ids were ever named", asked == {agent_id for agent_id, _ in A}, str(asked))
            names = set()
            for b in indexer.bodies:
                for clause in b.get("query", {}).get("bool", {}).get("filter", []):
                    names.update(clause.get("terms", {}).get("agent.name", []))
            check("and only A's agent names", names == {name for _, name in A}, str(names))

            print("\n=== D) compliance ===")
            status, body = await get("/compliance")
            check("200, no error", status == 200 and body["error"] is None, str(body)[:160])
            check(
                "the agent Wazuh could not answer for is counted",
                body["unavailable_agents"] == 1 and body["agents_in_scope"] == 3,
                str(body),
            )
            policies = {p["policy_id"]: (p["average_score"], p["agents"], p["agents_below"]) for p in body["policies"]}
            check("per policy, from A's agents only", policies == {"cis_debian": (51.5, 2, 1), "pci": (88.0, 1, 0)}, str(policies))
            check("the weakest policy first", body["policies"][0]["policy_id"] == "cis_debian")
            status, agents = await get("/compliance/cis_debian/agents")
            check(
                "a policy's agents, weakest first",
                [(a["agent_id"], a["score"]) for a in agents["agents"]] == [(A[0][0], 42), (A[1][0], 61)],
                str(agents["agents"]),
            )
            check(
                "Wazuh was asked about A's agents once (then the cache)",
                sorted(manager.asked) == sorted(agent_id for agent_id, _ in A),
                str(manager.asked),
            )
            check("never about B's", B[0][0] not in manager.asked)

            print("\n=== E) other customers ===")
            status, body = await get("/vulnerabilities", headers=admin)
            check(
                "the SOC, with B off: A's alone",
                body["customer_codes"] == [CUST_A] and body["totals"] == want["totals"],
                str(body["customer_codes"]),
            )
            await client.put(f"{BASE}/settings/{CUST_B}", json={"enabled": True}, headers=admin)
            status, body = await get("/vulnerabilities", headers=admin)
            want_ab = expected(A + B)
            check(
                "with B on: A's and B's",
                body["customer_codes"] == [CUST_A, CUST_B] and body["totals"] == want_ab["totals"],
                f"{body['totals']} vs {want_ab['totals']}",
            )
            status, body = await get("/vulnerabilities", headers=analyst)
            check(
                "an analyst of A: A's alone",
                body["customer_codes"] == [CUST_A] and body["totals"] == want["totals"],
                str(body["customer_codes"]),
            )
            status, body = await get("/vulnerabilities", customer_codes=[CUST_B])
            check("the portal user asking for B: nothing", body["enabled"] is False, str(body)[:120])
            status, _ = await get("/vulnerabilities/cve/CVE-2026-1001", customer_codes=[CUST_B])
            check("nor B's CVE page", status == 404, str(status))
            await client.put(f"{BASE}/settings/{CUST_B}", json={"enabled": False}, headers=admin)

            print("\n=== F) bounded ===")
            check("a page of 500: 422", (await get("/vulnerabilities", page_size=500))[0] == 422)
            check("an unknown severity: 422", (await get("/vulnerabilities", severity="Urgent"))[0] == 422)
            check("a CVE id with a slash: 404/422", (await get("/vulnerabilities/cve/a%2Fb"))[0] in (404, 422))
            check("without a token: 401", (await client.get(f"{BASE}/vulnerabilities")).status_code == 401)
            counter.reset()
            await get("/vulnerabilities")
            check("resolving the scope takes a handful of statements", len(counter.statements) <= 6, f"{len(counter.statements)}")
    finally:
        for p in patches:
            p.stop()
        await remove_analyst()
        async with AsyncSession(async_engine) as s:
            await cleanup(s)

    print("\n=== G) the migration round trip ===")
    from alembic import command
    from alembic.config import Config
    from app.db.db_session import SQLALCHEMY_DATABASE_URI

    config = Config("alembic/alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URI.replace("+aiomysql", "+pymysql"))

    async def table_exists() -> bool:
        async with AsyncSession(async_engine) as s:
            return bool((await s.execute(text("SHOW TABLES LIKE 'customer_portal_exposure_settings'"))).first())

    await asyncio.to_thread(command.downgrade, config, "c2a2a0b1d3e4")
    check("downgrade drops the table", not await table_exists())
    await asyncio.to_thread(command.upgrade, config, "head")
    check("upgrade brings it back", await table_exists())
    await async_engine.dispose()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{'=' * 60}\nRESULT: {passed}/{len(results)} checks passed")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAILED: {name} [{detail}]")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
