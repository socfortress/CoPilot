"""E2E per il seguito di #1050 — NON raccolto da pytest (serve un MySQL vivo).

    docker run -d --name copilot-e2e-mysql -p 13306:3306 \
        -e MYSQL_ROOT_PASSWORD=e2eroot -e MYSQL_DATABASE=copilot \
        -e MYSQL_USER=copilot -e MYSQL_PASSWORD=e2epass mysql:8.0

    cd backend && export MYSQL_URL=127.0.0.1:13306 MYSQL_USER=copilot \
        MYSQL_PASSWORD=e2epass MYSQL_ROOT_PASSWORD=e2eroot \
        JWT_SECRET=e2e-test-secret-not-the-default PYTHONPATH=$PWD
    .venv/bin/python -c "from app.db.db_setup import apply_migrations; apply_migrations()"
    .venv/bin/python tests/e2e/analyst_object_scoping_e2e.py

Punta a un'istanza usa-e-getta sulla porta 13306: mai al MySQL della .env.

`analyst_scoping_e2e.py` copre le rotte con `{customer_code}` nel path. Questo copre
il resto, che è dove il bug è rimasto: i dati di un tenant quasi mai si indirizzano col
suo codice cliente. Si indirizzano con un agent id, un hostname, un report id, un job
id, un *nome* cliente — chiavi che lo scan di #1050 non poteva vedere.

Ogni verifica è nella forma "l'analyst assegnato a E2E_A chiede l'oggetto di E2E_B":
prima della fix rispondevano 200, ora devono rispondere 403.
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
from app.db.universal_models import AgentDataStore  # noqa: E402
from app.db.universal_models import Agents
from app.db.universal_models import AiAnalystJob
from app.db.universal_models import AiAnalystPalaceLesson
from app.db.universal_models import AiAnalystReport
from app.db.universal_models import CustomDashboardTemplates
from app.db.universal_models import Customers
from app.integrations.alert_creation_settings.models.alert_creation_settings import (  # noqa: E402
    AlertCreationSettings,
)

PASSWORD = "E2ePassw0rd!x"
CUST_A, CUST_B = "E2E_OA", "E2E_OB"
NAME_A, NAME_B = "E2E Owner A", "E2E Owner B"
SCOPED = "e2e_obj_scoped_analyst"  # assegnato a CUST_A
ADMIN = "e2e_obj_admin"

NOW = datetime.datetime(2026, 1, 1)
results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


async def seed():
    auth = AuthHandler()
    async with AsyncSession(async_engine) as s:
        for rid, rname in [(1, "admin"), (2, "analyst"), (3, "scheduler"), (4, "customer_user")]:
            if not (await s.execute(select(Role).where(Role.id == rid))).scalars().first():
                s.add(Role(id=rid, name=rname, description=rname))
        await s.commit()

        for uname in (SCOPED, ADMIN):
            u = (await s.execute(select(User).where(User.username == uname))).scalars().first()
            if u:
                await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id == u.id))
                await s.delete(u)
        await s.execute(delete(AgentDataStore).where(AgentDataStore.agent_id.in_(["e2eo1", "e2eo2"])))
        await s.execute(delete(AiAnalystPalaceLesson).where(AiAnalystPalaceLesson.customer_code.in_([CUST_A, CUST_B])))
        await s.execute(delete(AiAnalystReport).where(AiAnalystReport.customer_code.in_([CUST_A, CUST_B])))
        await s.execute(delete(AiAnalystJob).where(AiAnalystJob.customer_code.in_([CUST_A, CUST_B])))
        await s.execute(delete(Agents).where(Agents.customer_code.in_([CUST_A, CUST_B])))
        await s.execute(delete(CustomDashboardTemplates).where(CustomDashboardTemplates.template_key.like("e2eo_%")))
        await s.execute(delete(AlertCreationSettings).where(AlertCreationSettings.customer_code.in_([CUST_A, CUST_B])))
        await s.commit()
        for code in (CUST_A, CUST_B):
            c = (await s.execute(select(Customers).where(Customers.customer_code == code))).scalars().first()
            if c:
                await s.delete(c)
        await s.commit()

        for code, name in ((CUST_A, NAME_A), (CUST_B, NAME_B)):
            s.add(
                Customers(
                    customer_code=code,
                    customer_name=name,
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

        # one agent per tenant — the key most object routes are addressed by
        for agent_id, code in (("e2eo1", CUST_A), ("e2eo2", CUST_B)):
            s.add(
                Agents(
                    agent_id=agent_id,
                    ip_address="10.0.0.1",
                    os="Linux",
                    hostname=f"host-{code}",
                    label=f"host-{code}",
                    critical_asset=False,
                    customer_code=code,
                    quarantined=False,
                    velociraptor_id=f"C.{agent_id}",
                    velociraptor_org="root",
                    wazuh_last_seen=NOW,
                    velociraptor_last_seen=NOW,
                    wazuh_agent_version="4.x",
                    velociraptor_agent_version="0.7",
                ),
            )
        await s.commit()

        for agent_id, code in (("e2eo1", CUST_A), ("e2eo2", CUST_B)):
            s.add(
                AgentDataStore(
                    agent_id=agent_id,
                    velociraptor_id=f"C.{agent_id}",
                    artifact_name="Generic.Client.Info",
                    flow_id=f"F.{agent_id}",
                    bucket_name="velociraptor-artifacts",
                    object_key=f"{agent_id}/x.json",
                    file_name="x.json",
                    content_type="application/json",
                    file_size=1,
                    file_hash="deadbeef",
                    collection_time=NOW,
                    uploaded_by=1,
                ),
            )
            s.add(CustomDashboardTemplates(template_key=f"e2eo_dash_{code}", customer_code=code, title=f"Dash {code}", panels=[]))
            s.add(
                AlertCreationSettings(
                    customer_code=code,
                    customer_name=NAME_A if code == CUST_A else NAME_B,
                    office365_organization_id="",
                    iris_customer_id=1,
                    iris_customer_name="x",
                    grafana_org_id=1,
                    grafana_url="http://x",
                    wazuh_url="http://x",
                    graylog_url="http://x",
                    misp_url="http://x",
                    shuffle_url="http://x",
                    velociraptor_url="http://x",
                    influxdb_url="http://x",
                    portainer_url="http://x",
                ),
            )
        await s.commit()

        for code in (CUST_A, CUST_B):
            s.add(
                AiAnalystJob(
                    id=f"job-{code}",
                    alert_id=1 if code == CUST_A else 2,
                    customer_code=code,
                    status="completed",
                    triggered_by="manual",
                ),
            )
        await s.commit()
        for code in (CUST_A, CUST_B):
            s.add(
                AiAnalystReport(
                    job_id=f"job-{code}",
                    alert_id=1 if code == CUST_A else 2,
                    customer_code=code,
                    summary="s",
                ),
            )
        await s.commit()

        pw = auth.get_password_hash(PASSWORD)
        s.add(User(username=ADMIN, password=pw, email=f"{ADMIN}@e2e.example", role_id=1))
        s.add(User(username=SCOPED, password=pw, email=f"{SCOPED}@e2e.example", role_id=2))
        await s.commit()
        scoped = (await s.execute(select(User).where(User.username == SCOPED))).scalars().first()
        s.add(UserCustomerAccess(user_id=scoped.id, customer_code=CUST_A))
        await s.commit()

        report_b = (await s.execute(select(AiAnalystReport).where(AiAnalystReport.customer_code == CUST_B))).scalars().first()
        report_a = (await s.execute(select(AiAnalystReport).where(AiAnalystReport.customer_code == CUST_A))).scalars().first()
        art_b = (await s.execute(select(AgentDataStore).where(AgentDataStore.agent_id == "e2eo2"))).scalars().first()
        print(f"seed: 2 tenant, analyst '{SCOPED}' assegnato a {CUST_A}")
        return {"report_b": report_b.id, "report_a": report_a.id, "artifact_b": art_b.id}


def build_app():
    from app.agents.sca.routes.sca import sca_router
    from app.ai_analyst.routes.ai_analyst import ai_analyst_router
    from app.customers.routes.customers import customers_router
    from app.data_store.data_store_routes import agent_data_store_router
    from app.integrations.alert_creation_settings.routes.alert_creation_settings import (
        alert_creation_settings_router,
    )
    from app.siem.routes.dashboards import dashboards_router

    api = APIRouter()
    api.include_router(customers_router, prefix="/customers")
    api.include_router(agent_data_store_router, prefix="/agent_data_store")
    api.include_router(alert_creation_settings_router, prefix="/alert_settings")
    api.include_router(ai_analyst_router, prefix="/ai_analyst")
    api.include_router(dashboards_router, prefix="/siem/dashboards")
    api.include_router(sca_router, prefix="/sca")
    app = FastAPI()
    app.include_router(api)
    return app


async def main():
    ids = await seed()
    app = build_app()
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://e2e") as client:
        t_scoped = await AuthHandler().encode_token(SCOPED)
        t_admin = await AuthHandler().encode_token(ADMIN)
        H = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731

        print("\n=== 0) il caso di #1050 non deve regredire ===")
        r = await client.get("/customers", headers=H(t_scoped))
        codes = {c["customer_code"] for c in r.json().get("customers", [])} if r.status_code == 200 else set()
        check("GET /customers -> solo il proprio", codes == {CUST_A}, f"{r.status_code} {sorted(codes)}")

        print("\n=== 1) chiave = customer NAME (non code) ===")
        r = await client.get(f"/alert_settings/{NAME_B}", headers=H(t_scoped))
        check("GET /alert_settings/{altrui} -> 403", r.status_code == 403, str(r.status_code))
        r = await client.get(f"/alert_settings/{NAME_A}", headers=H(t_scoped))
        check("GET /alert_settings/{proprio} -> 200", r.status_code == 200, str(r.status_code))
        r = await client.delete(f"/alert_settings/{NAME_B}/event/whatever", headers=H(t_scoped))
        check("DELETE /alert_settings/{altrui}/event -> 403", r.status_code == 403, str(r.status_code))

        print("\n=== 2) chiave = agent id ===")
        r = await client.get("/agent_data_store/agent/e2eo2/artifacts", headers=H(t_scoped))
        check("GET artifacts di un agent altrui -> 403", r.status_code == 403, str(r.status_code))
        r = await client.get("/agent_data_store/agent/e2eo1/artifacts", headers=H(t_scoped))
        check("GET artifacts del proprio agent -> 200", r.status_code == 200, str(r.status_code))
        r = await client.get(f"/agent_data_store/agent/e2eo2/artifacts/{ids['artifact_b']}", headers=H(t_scoped))
        check("GET dettaglio artifact altrui -> 403", r.status_code == 403, str(r.status_code))
        r = await client.get(f"/agent_data_store/agent/e2eo2/artifacts/{ids['artifact_b']}/download", headers=H(t_scoped))
        check("DOWNLOAD artifact altrui -> 403", r.status_code == 403, str(r.status_code))
        r = await client.get("/agent_data_store/agent/ghost-agent/artifacts", headers=H(t_scoped))
        check("GET artifacts di un agent inesistente -> 403 (fail-closed)", r.status_code == 403, str(r.status_code))

        print("\n=== 3) chiave = id oggetto (AI analyst) ===")
        r = await client.get(f"/ai_analyst/jobs/job-{CUST_B}", headers=H(t_scoped))
        check("GET job altrui -> 403", r.status_code == 403, str(r.status_code))
        r = await client.get(f"/ai_analyst/jobs/job-{CUST_A}", headers=H(t_scoped))
        check("GET job proprio -> 200", r.status_code == 200, str(r.status_code))
        r = await client.get(f"/ai_analyst/reports/{ids['report_b']}", headers=H(t_scoped))
        check("GET report altrui -> 403", r.status_code == 403, str(r.status_code))
        r = await client.get(f"/ai_analyst/iocs/report/{ids['report_b']}", headers=H(t_scoped))
        check("GET IOC del report altrui -> 403", r.status_code == 403, str(r.status_code))
        r = await client.post(
            "/ai_analyst/palace_lessons",
            json={"customer_code": CUST_B, "lesson_type": "environment", "lesson_text": "x"},
            headers=H(t_scoped),
        )
        check("POST palace lesson per tenant altrui -> 403", r.status_code == 403, str(r.status_code))

        print("\n=== 4) chiave = template key (dashboard custom) ===")
        r = await client.get(f"/siem/dashboards/custom/e2eo_dash_{CUST_B}", headers=H(t_scoped))
        check("GET dashboard custom altrui -> 403", r.status_code == 403, str(r.status_code))
        r = await client.get(f"/siem/dashboards/custom/e2eo_dash_{CUST_A}", headers=H(t_scoped))
        check("GET dashboard custom propria -> 200", r.status_code == 200, str(r.status_code))
        r = await client.delete(f"/siem/dashboards/custom/e2eo_dash_{CUST_B}", headers=H(t_scoped))
        check("DELETE dashboard custom altrui -> 403", r.status_code == 403, str(r.status_code))
        r = await client.get(f"/siem/dashboards/custom/e2eo_dash_{CUST_B}/export", headers=H(t_scoped))
        check("EXPORT dashboard custom altrui -> 403", r.status_code == 403, str(r.status_code))

        print("\n=== 5) l'admin non regredisce ===")
        for label, url in (
            ("alert_settings altrui", f"/alert_settings/{NAME_B}"),
            ("artifacts altrui", "/agent_data_store/agent/e2eo2/artifacts"),
            ("job altrui", f"/ai_analyst/jobs/job-{CUST_B}"),
            ("dashboard custom altrui", f"/siem/dashboards/custom/e2eo_dash_{CUST_B}"),
        ):
            r = await client.get(url, headers=H(t_admin))
            check(f"admin GET {label} -> 200", r.status_code == 200, str(r.status_code))

    passed = sum(1 for _, ok, _ in results if ok)
    print("\n" + "=" * 60)
    print(f"RISULTATO: {passed}/{len(results)} verifiche superate")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
