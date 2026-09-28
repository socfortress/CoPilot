"""E2E for #1181 (Customer Portal query budget) — NOT collected by pytest (needs a live MySQL); run by hand.

    docker run -d --name copilot-e2e-mysql -p 13306:3306 \
        -e MYSQL_ROOT_PASSWORD=e2eroot -e MYSQL_DATABASE=copilot \
        -e MYSQL_USER=copilot -e MYSQL_PASSWORD=e2epass mysql:8.0

    cd backend && export MYSQL_URL=127.0.0.1:13306 MYSQL_USER=copilot \
        MYSQL_PASSWORD=e2epass MYSQL_ROOT_PASSWORD=e2eroot \
        JWT_SECRET=e2e-test-secret-not-the-default PYTHONPATH=$PWD
    .venv/bin/python -c "from app.db.db_setup import apply_migrations; apply_migrations()"
    .venv/bin/python tests/e2e/customer_portal_overview_e2e.py

Points at a throwaway instance on port 13306: never at the MySQL in .env. Exits
non-zero when a check fails.

Real routers, real MySQL, real JWTs. The unit tests mock the session; this is where
the SQL itself is exercised:

  A) GET /customer_portal/overview returns exactly what the four calls it replaces
     return (alert/case lists + counts, agents, AI insights), for a portal user and
     an admin;
  B) the numbers are the seeded ones — grouped status counts included;
  C) query budget: the Overview stays within MAX_OVERVIEW_STATEMENTS and reads
     user_customer_access once;
  D) a change of customer assignments, of the AI switch or of branding is visible on
     the very next request (memo and cache never serve a stale answer after a write).
"""

import asyncio
import os
import sys

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy import event  # noqa: E402
from sqlalchemy import update  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import CustomerPortalBranding  # noqa: E402
from tests.e2e.portal_overview_seed import ADMIN  # noqa: E402
from tests.e2e.portal_overview_seed import ALERTS_A  # noqa: E402
from tests.e2e.portal_overview_seed import ALERTS_B  # noqa: E402
from tests.e2e.portal_overview_seed import CASES_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_A  # noqa: E402
from tests.e2e.portal_overview_seed import CUST_B  # noqa: E402
from tests.e2e.portal_overview_seed import PORTAL_USER  # noqa: E402
from tests.e2e.portal_overview_seed import cleanup  # noqa: E402
from tests.e2e.portal_overview_seed import seed  # noqa: E402
from tests.e2e.portal_overview_seed import status_counts  # noqa: E402

# Measured 11 for a portal user on a dev database; the margin absorbs an extra
# lookup, not a return to one count per status or to loading every agent.
MAX_OVERVIEW_STATEMENTS = 12

results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def build_app():
    """The real routers, without the startup hooks (MinIO, connectors, scheduler)."""
    from app.routers import agents
    from app.routers import auth
    from app.routers import customer_portal
    from app.routers import incidents

    app = FastAPI()
    for module in (auth, incidents, agents, customer_portal):
        app.include_router(module.router)
    return app


class StatementCounter:
    def __init__(self):
        self.statements = []
        event.listen(async_engine.sync_engine, "before_cursor_execute", self._record)

    def _record(self, conn, cursor, statement, *args):
        self.statements.append(statement)

    def reset(self):
        self.statements.clear()


def projected_counts(body):
    return {key: body.get(key) for key in ("total", "open", "in_progress", "closed")}


async def check_parity(client, headers, who):
    """The Overview must say exactly what the four calls it replaces say."""
    page = {"page": 1, "page_size": 6, "order": "desc"}
    overview = (await client.get("/customer_portal/overview", headers=headers)).json()
    alerts = (await client.get("/incidents/db_operations/alerts", headers=headers, params=page)).json()
    cases = (await client.get("/incidents/db_operations/cases", headers=headers, params=page)).json()
    agents = (await client.get("/agents", headers=headers)).json().get("agents") or []
    insights = (await client.get("/customer_portal/ai_reports/insights", headers=headers, params={"limit": 3})).json()

    ov_alerts, ov_cases = overview["alerts"]["recent"], overview["cases"]["recent"]
    online = sum(agent["wazuh_agent_status"] == "active" for agent in agents)
    check(f"{who}: no section reports an error", all(overview[k]["error"] is None for k in ("alerts", "cases", "agents", "ai")))
    check(f"{who}: alert counts = /alerts", overview["alerts"]["counts"] == projected_counts(alerts), str(overview["alerts"]["counts"]))
    check(f"{who}: recent alerts = /alerts page 1", [a["id"] for a in ov_alerts] == [a["id"] for a in alerts["alerts"]])
    check(
        f"{who}: alert rows (name, status, time, source, assets)",
        [(a["alert_name"], a["status"], a["alert_creation_time"], a["source"], a["asset_names"]) for a in ov_alerts]
        == [
            (a["alert_name"], a["status"], a["alert_creation_time"], a["source"], [x["asset_name"] for x in a["assets"]])
            for a in alerts["alerts"]
        ],
    )
    check(f"{who}: case counts = /cases", overview["cases"]["counts"] == projected_counts(cases), str(overview["cases"]["counts"]))
    check(
        f"{who}: case rows (id, status, time, assignee, alert count)",
        [(c["id"], c["case_status"], c["case_creation_time"], c["assigned_to"], c["alert_count"]) for c in ov_cases]
        == [(c["id"], c["case_status"], c["case_creation_time"], c["assigned_to"], len(c["alerts"])) for c in cases["cases"]],
    )
    expected_agents = {
        "total": len(agents),
        "online": online,
        "offline": len(agents) - online,
        "critical": sum(bool(a["critical_asset"]) for a in agents),
        "error": None,
    }
    check(f"{who}: agent counts = /agents", overview["agents"] == expected_agents, str(overview["agents"]))
    check(
        f"{who}: AI section = /ai_reports/insights",
        {k: overview["ai"][k] for k in ("total_reports", "severity_counts", "recent")}
        == {k: insights[k] for k in ("total_reports", "severity_counts", "recent")},
    )
    return overview


async def main():
    portal_id = await seed()
    counter = StatementCounter()
    auth = AuthHandler()
    admin = {"Authorization": f"Bearer {await auth.encode_token(ADMIN)}"}
    portal = {"Authorization": f"Bearer {await auth.encode_token(PORTAL_USER)}"}

    async def overview(headers, **params):
        response = await client.get("/customer_portal/overview", headers=headers, params=params)
        assert response.status_code == 200, (response.status_code, response.text[:300])
        return response.json()

    async def assign(codes):
        response = await client.post(f"/auth/users/{portal_id}/customers", headers=admin, json=codes)
        assert response.status_code == 200, (response.status_code, response.text[:300])

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e") as client:
        print("\n=== A) Overview = the four calls it replaces ===")
        await check_parity(client, portal, "portal user")
        await check_parity(client, admin, "admin")

        print("\n=== B) the numbers are the seeded ones ===")
        ov = await overview(portal)
        check("alert counts per status (one GROUP BY)", ov["alerts"]["counts"] == status_counts(ALERTS_A), str(ov["alerts"]["counts"]))
        check("case counts per status (one GROUP BY)", ov["cases"]["counts"] == status_counts(CASES_A), str(ov["cases"]["counts"]))
        expected_agents = {"total": 3, "online": 2, "offline": 1, "critical": 1, "error": None}
        check("agents counted in SQL", ov["agents"] == expected_agents, str(ov["agents"]))
        check(
            "AI: only the latest report per alert counts",
            ov["ai"]["severity_counts"] == {"High": 1, "Medium": 1},
            str(ov["ai"]["severity_counts"]),
        )
        recent = {a["alert_name"]: a["asset_names"] for a in ov["alerts"]["recent"]}
        check(
            "assets of the recent alerts",
            recent.get(f"{CUST_A} alert 0") == ["host-a1", "host-a2"],
            str(recent.get(f"{CUST_A} alert 0")),
        )
        check("never another tenant's rows", all(a["customer_code"] == CUST_A for a in ov["alerts"]["recent"] + ov["cases"]["recent"]))
        stats = (await client.get("/customer_portal/dashboard/alert-stats", headers=portal)).json()
        check("/dashboard/alert-stats agrees", projected_counts(stats) == status_counts(ALERTS_A), str(projected_counts(stats)))
        stats = (await client.get("/customer_portal/dashboard/case-stats", headers=portal)).json()
        check("/dashboard/case-stats agrees", projected_counts(stats) == status_counts(CASES_A), str(projected_counts(stats)))
        ov_b = await overview(admin, customer_codes=CUST_B)
        check("customer filter narrows the admin view", ov_b["alerts"]["counts"] == status_counts(ALERTS_B), str(ov_b["alerts"]["counts"]))

        print("\n=== C) query budget ===")
        await overview(portal)  # warm the per-process caches (user lookup, branding) first
        counter.reset()
        await overview(portal)
        statements = len(counter.statements)
        check(
            f"Overview within {MAX_OVERVIEW_STATEMENTS} SQL statements",
            statements <= MAX_OVERVIEW_STATEMENTS,
            f"{statements} statements",
        )
        access_reads = sum("user_customer_access" in s and s.lstrip().upper().startswith("SELECT") for s in counter.statements)
        check("user_customer_access read once per request", access_reads == 1, f"{access_reads} reads")
        grouped = sum("GROUP BY" in s.upper() and "COUNT(" in s.upper() and "incident_management_" in s for s in counter.statements)
        per_status = sum("COUNT(" in s.upper() and ".status = " in s for s in counter.statements)
        check(
            "status counts are grouped, not one COUNT per status",
            grouped >= 2 and per_status == 0,
            f"grouped={grouped} per_status={per_status}",
        )

        print("\n=== D) writes are visible on the next request ===")
        await assign([CUST_A, CUST_B])
        ov = await overview(portal)
        check(
            "new customer assignment seen at once",
            ov["alerts"]["counts"]["total"] == len(ALERTS_A) + len(ALERTS_B),
            str(ov["alerts"]["counts"]),
        )
        await assign([])
        ov = await overview(portal)
        empty = all(ov[k]["error"] is None for k in ("alerts", "cases", "agents", "ai"))
        check(
            "no assignment: empty sections, no errors",
            empty and ov["alerts"]["counts"]["total"] == 0 and ov["agents"]["total"] == 0 and ov["ai"]["total_reports"] == 0,
            str(ov["alerts"]["counts"]),
        )
        await assign([CUST_A])

        await client.put(f"/customer_portal/ai_reports/settings/{CUST_A}", headers=admin, json={"enabled": False})
        ov = await overview(portal)
        check("AI switch off hides the findings", ov["ai"]["total_reports"] == 0, str(ov["ai"]["total_reports"]))
        await client.put(f"/customer_portal/ai_reports/settings/{CUST_A}", headers=admin, json={"enabled": True})
        ov = await overview(portal)
        check("AI switch back on shows them again", ov["ai"]["total_reports"] == 2, str(ov["ai"]["total_reports"]))

        async def portal_title():
            return (await client.get("/customer_portal/settings/effective", headers=portal)).json()["settings"]["title"]

        await client.put(f"/customer_portal/branding/{CUST_A}", headers=admin, json={"enabled": True, "title": "E2E Before"})
        check("saved branding is served", await portal_title() == "E2E Before")
        async with AsyncSession(async_engine) as s:
            await s.execute(update(CustomerPortalBranding).where(CustomerPortalBranding.customer_code == CUST_A).values(title="E2E Direct"))
            await s.commit()
        title = await portal_title()
        check("branding is served from the cache (a direct DB edit is not seen)", title == "E2E Before", title)
        await client.put(f"/customer_portal/branding/{CUST_A}", headers=admin, json={"enabled": True, "title": "E2E After"})
        title = await portal_title()
        check("saving branding invalidates the cache at once", title == "E2E After", title)
        await client.delete(f"/customer_portal/branding/{CUST_A}", headers=admin)
        check("removing the override is seen at once", await portal_title() != "E2E After")

    async with AsyncSession(async_engine) as s:
        await cleanup(s)
    await async_engine.dispose()

    passed = sum(1 for _, ok, _ in results if ok)
    print(f"\n{'=' * 60}\nRESULT: {passed}/{len(results)} checks passed")
    for name, ok, detail in results:
        if not ok:
            print(f"  FAILED: {name} [{detail}]")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if asyncio.run(main()) else 1)
