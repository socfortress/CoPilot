"""E2E per #1050 — NON raccolto da pytest (serve un MySQL vivo); si lancia a mano.

    docker run -d --name copilot-e2e-mysql -p 13306:3306 \
        -e MYSQL_ROOT_PASSWORD=e2eroot -e MYSQL_DATABASE=copilot \
        -e MYSQL_USER=copilot -e MYSQL_PASSWORD=e2epass mysql:8.0

    cd backend && export MYSQL_URL=127.0.0.1:13306 MYSQL_USER=copilot \
        MYSQL_PASSWORD=e2epass MYSQL_ROOT_PASSWORD=e2eroot \
        JWT_SECRET=e2e-test-secret-not-the-default PYTHONPATH=$PWD
    .venv/bin/python -c "from app.db.db_setup import apply_migrations; apply_migrations()"
    .venv/bin/python tests/e2e/analyst_scoping_e2e.py

Punta a un'istanza usa-e-getta sulla porta 13306: mai al MySQL della .env.

Verifica le due assunzioni:
  A) analyst SENZA clienti assegnati -> vede tutto
  B) analyst CON clienti assegnati  -> vede solo quelli, anche quando la lista
     viene chiamata senza customer_code
"""
import asyncio
import datetime
import os

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
from fastapi import APIRouter  # noqa: E402
from fastapi import FastAPI
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.auth.models.users import Role  # noqa: E402
from app.auth.models.users import User
from app.auth.models.users import UserCustomerAccess
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import Agents  # noqa: E402
from app.db.universal_models import AgentVulnerabilities
from app.db.universal_models import CustomDashboardTemplates
from app.db.universal_models import Customers
from app.db.universal_models import NotificationTemplate

PASSWORD = "E2ePassw0rd!x"
CUST_A, CUST_B, CUST_C = "E2E_A", "E2E_B", "E2E_C"
SCOPED = "e2e_scoped_analyst"  # assegnato a E2E_A
UNSCOPED = "e2e_unscoped_analyst"  # nessuna assegnazione
ADMIN = "e2e_admin"

NOW = datetime.datetime(2026, 1, 1)
results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


async def seed():
    auth = AuthHandler()
    async with AsyncSession(async_engine) as s:
        # ruoli
        for rid, rname in [(1, "admin"), (2, "analyst"), (3, "scheduler"), (4, "customer_user")]:
            if not (await s.execute(select(Role).where(Role.id == rid))).scalars().first():
                s.add(Role(id=rid, name=rname, description=rname))
        await s.commit()

        # pulizia da run precedenti
        for uname in (SCOPED, UNSCOPED, ADMIN):
            u = (await s.execute(select(User).where(User.username == uname))).scalars().first()
            if u:
                await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id == u.id))
                await s.delete(u)
        await s.execute(delete(AgentVulnerabilities).where(AgentVulnerabilities.customer_code.in_([CUST_A, CUST_B, CUST_C])))
        await s.execute(delete(Agents).where(Agents.customer_code.in_([CUST_A, CUST_B, CUST_C])))
        await s.execute(delete(CustomDashboardTemplates).where(CustomDashboardTemplates.template_key.like("e2e_%")))
        await s.execute(delete(NotificationTemplate).where(NotificationTemplate.name.like("e2e_%")))
        await s.commit()
        for code in (CUST_A, CUST_B, CUST_C):
            c = (await s.execute(select(Customers).where(Customers.customer_code == code))).scalars().first()
            if c:
                await s.delete(c)
        await s.commit()

        # 3 clienti
        for code in (CUST_A, CUST_B, CUST_C):
            s.add(
                Customers(
                    customer_code=code,
                    customer_name=f"Customer {code}",
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

        # un agente per cliente, per provare una lista diversa da /customers
        for i, code in enumerate((CUST_A, CUST_B, CUST_C), start=1):
            s.add(
                Agents(
                    agent_id=f"e2e{i}",
                    ip_address=f"10.0.0.{i}",
                    os="Linux",
                    hostname=f"host-{code}",
                    label=f"host-{code}",
                    critical_asset=False,
                    customer_code=code,
                    quarantined=False,
                    velociraptor_id="",
                    velociraptor_org="root",
                    wazuh_last_seen=NOW,
                    velociraptor_last_seen=NOW,
                    wazuh_agent_version="4.x",
                    velociraptor_agent_version="0.7",
                ),
            )
        await s.commit()

        # una dashboard custom e un template per E2E_A e per E2E_B
        for code in (CUST_A, CUST_B):
            s.add(
                AgentVulnerabilities(
                    agent_id=("e2e1" if code == CUST_A else "e2e2"),
                    customer_code=code,
                    cve_id=f"CVE-{code}",
                    severity="High",
                    title=f"v {code}",
                    references="",
                    discovered_at=NOW,
                ),
            )
            s.add(CustomDashboardTemplates(template_key=f"e2e_dash_{code}", customer_code=code, title=f"Dash {code}", panels=[]))
            s.add(NotificationTemplate(name=f"e2e_tpl_{code}", customer_code=code, body_template="x"))
        await s.commit()

        # utenti
        pw = auth.get_password_hash(PASSWORD)
        s.add(User(username=ADMIN, password=pw, email=f"{ADMIN}@e2e.local", role_id=1))
        s.add(User(username=SCOPED, password=pw, email=f"{SCOPED}@e2e.local", role_id=2))
        s.add(User(username=UNSCOPED, password=pw, email=f"{UNSCOPED}@e2e.local", role_id=2))
        await s.commit()

        scoped = (await s.execute(select(User).where(User.username == SCOPED))).scalars().first()
        s.add(UserCustomerAccess(user_id=scoped.id, customer_code=CUST_A))
        await s.commit()
        print(f"seed: 3 clienti, 3 agenti, analyst '{SCOPED}' assegnato a {CUST_A}, analyst '{UNSCOPED}' senza assegnazioni")


def build_app():
    """Monta i router reali senza gli hook di startup (MinIO/connettori)."""
    from app.customers.routes.customers import customers_router
    from app.notifications.routes.notifications import notifications_router
    from app.routers.agents import router as agents_aggregate_router
    from app.siem.routes.dashboards import dashboards_router

    api = APIRouter()
    api.include_router(customers_router, prefix="/customers", tags=["customers"])
    api.include_router(agents_aggregate_router)
    api.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
    api.include_router(dashboards_router, prefix="/siem/dashboards", tags=["siem"])
    app = FastAPI()
    app.include_router(api)
    return app


async def token_for(username):
    return await AuthHandler().encode_token(username)


async def main():
    await seed()
    app = build_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://e2e") as client:
        t_scoped = await token_for(SCOPED)
        t_unscoped = await token_for(UNSCOPED)
        t_admin = await token_for(ADMIN)
        H = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731

        print("\n=== A) analyst SENZA clienti assegnati ===")
        r = await client.get("/customers", headers=H(t_unscoped))
        codes = {c["customer_code"] for c in r.json().get("customers", [])} if r.status_code == 200 else set()
        check(
            "GET /customers -> vede tutti e 3",
            r.status_code == 200 and {CUST_A, CUST_B, CUST_C} <= codes,
            f"{r.status_code} {sorted(codes)}",
        )

        r = await client.get(f"/customers/{CUST_B}", headers=H(t_unscoped))
        check("GET /customers/E2E_B -> 200", r.status_code == 200, str(r.status_code))

        print("\n=== B) analyst CON un cliente assegnato (E2E_A) ===")
        r = await client.get("/customers", headers=H(t_scoped))
        codes = {c["customer_code"] for c in r.json().get("customers", [])} if r.status_code == 200 else set()
        check("GET /customers -> solo E2E_A", r.status_code == 200 and codes == {CUST_A}, f"{r.status_code} {sorted(codes)}")

        r = await client.get(f"/customers/{CUST_A}", headers=H(t_scoped))
        check("GET /customers/E2E_A (suo) -> 200", r.status_code == 200, str(r.status_code))

        r = await client.get(f"/customers/{CUST_B}", headers=H(t_scoped))
        check("GET /customers/E2E_B (altrui) -> 403", r.status_code == 403, str(r.status_code))

        r = await client.get(f"/customers/{CUST_B}/agents", headers=H(t_scoped))
        check("GET /customers/E2E_B/agents (altrui) -> 403", r.status_code == 403, str(r.status_code))

        r = await client.get(f"/notifications/customers/{CUST_B}/notification_routes", headers=H(t_scoped))
        check("GET /notifications/.../E2E_B/... (altrui) -> 403", r.status_code == 403, str(r.status_code))

        print("\n=== B2) liste SENZA customer_code: filtrano da sole? ===")
        r = await client.get("/agents", headers=H(t_scoped))
        body = r.json() if r.status_code == 200 else {}
        agent_codes = {a.get("customer_code") for a in body.get("agents", [])}
        check(
            "GET /agents (nessun codice) -> solo E2E_A",
            r.status_code == 200 and agent_codes == {CUST_A},
            f"{r.status_code} {sorted(c for c in agent_codes if c)}",
        )

        r = await client.get("/siem/dashboards/custom", headers=H(t_scoped))
        keys = {d.get("template_key") for d in (r.json().get("custom_dashboards", []) if r.status_code == 200 else [])}
        e2e_keys = {k for k in keys if k and k.startswith("e2e_dash_")}
        check(
            "GET /siem/dashboards/custom (nessun codice) -> solo E2E_A",
            e2e_keys == {f"e2e_dash_{CUST_A}"},
            f"{r.status_code} {sorted(e2e_keys)}",
        )

        r = await client.get("/notifications/notifications/templates", headers=H(t_scoped))
        names = {t.get("name") for t in (r.json().get("templates", []) if r.status_code == 200 else [])}
        e2e_names = {n for n in names if n and n.startswith("e2e_tpl_")}
        check(
            "GET /notifications/templates (nessun codice) -> solo E2E_A",
            e2e_names == {f"e2e_tpl_{CUST_A}"},
            f"{r.status_code} {sorted(e2e_names)}",
        )

        r = await client.get("/vulnerabilities/stats", headers=H(t_scoped))
        total = r.json().get("total_vulnerabilities") if r.status_code == 200 else None
        check(
            "GET /vulnerabilities/stats (nessun codice) -> conta solo E2E_A",
            r.status_code == 200 and total == 1,
            f"{r.status_code} total={total}",
        )

        print("\n=== C) admin non regredisce ===")
        r = await client.get("/customers", headers=H(t_admin))
        codes = {c["customer_code"] for c in r.json().get("customers", [])} if r.status_code == 200 else set()
        check(
            "admin GET /customers -> vede tutti",
            r.status_code == 200 and {CUST_A, CUST_B, CUST_C} <= codes,
            f"{r.status_code} {sorted(codes)}",
        )

        r = await client.get(f"/customers/{CUST_B}", headers=H(t_admin))
        check("admin GET /customers/E2E_B -> 200", r.status_code == 200, str(r.status_code))

    passed = sum(1 for _, p, _ in results if p)
    print(f"\n{'=' * 60}\nRISULTATO: {passed}/{len(results)} verifiche superate")
    for n, p, d in results:
        if not p:
            print(f"  FALLITA: {n} [{d}]")


asyncio.run(main())
