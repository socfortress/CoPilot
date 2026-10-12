"""E2E per #1219 (ruolo Responder) — NON raccolto da pytest (serve un MySQL vivo); si lancia a mano.

    docker run -d --name copilot-e2e-mysql -p 13306:3306 \
        -e MYSQL_ROOT_PASSWORD=e2eroot -e MYSQL_DATABASE=copilot \
        -e MYSQL_USER=copilot -e MYSQL_PASSWORD=e2epass mysql:8.0

    cd backend && export MYSQL_URL=127.0.0.1:13306 MYSQL_USER=copilot \
        MYSQL_PASSWORD=e2epass MYSQL_ROOT_PASSWORD=e2eroot \
        JWT_SECRET=e2e-test-secret-not-the-default PYTHONPATH=$PWD
    .venv/bin/python -c "from app.db.db_setup import apply_migrations; apply_migrations()"
    .venv/bin/python tests/e2e/responder_role_e2e.py

Punta a un'istanza usa-e-getta sulla porta 13306: mai al MySQL della .env.

Router reali, JWT reali, MySQL reale; Velociraptor, il catalogo CoPilot Actions e il
worker Sysmon sono sostituiti da uno stub posto *dopo* il controllo di tenancy, così
"lo stub è stato chiamato" vuol dire "il server ha lasciato passare la richiesta".

  A) la migrazione ha creato il ruolo 5 "responder" e il token porta responder+analyst
  B) quarantena / comando: il responder agisce sui propri host e non su quelli altrui;
     l'analyst non agisce affatto; l'admin agisce ovunque
  C) CoPilot Actions: idem, un host altrui rifiuta l'intera richiesta; l'invoke è in audit
  D) Sysmon: il responder deploya il proprio cliente (in audit), non quello altrui;
     l'upload resta admin
  E) analyst e responder hanno sempre un cliente: registrazione, cambio ruolo e
     riassegnazione senza clienti sono 400 e non cambiano nulla; un admin non ne riceve
  F) un analyst rimasto senza clienti da prima di #1219 non vede nulla
"""
import asyncio
import datetime
import os
import sys
from unittest.mock import AsyncMock
from unittest.mock import patch

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
import jwt  # noqa: E402
from fastapi import APIRouter  # noqa: E402
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

import app.active_response.routes.sysmon_config as sysmon_routes  # noqa: E402
import app.connectors.velociraptor.routes.artifacts as artifact_routes  # noqa: E402
import app.integrations.copilot_action.routes.copilot_action as action_routes  # noqa: E402
from app.audit.models.audit import AuditLog  # noqa: E402
from app.auth.models.users import Role  # noqa: E402
from app.auth.models.users import User
from app.auth.models.users import UserCustomerAccess
from app.auth.utils import AuthHandler  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import Agents  # noqa: E402
from app.db.universal_models import Customers
from app.middleware.exception_handlers import (  # noqa: E402
    custom_http_exception_handler,
)
from app.middleware.exception_handlers import validation_exception_handler

PASSWORD = "E2ePassw0rd!x"
CUST_A, CUST_B = "E2E_RA", "E2E_RB"
HOST_A, HOST_B = "e2e-resp-host-a", "e2e-resp-host-b"
ADMIN = "e2e_resp_admin"
RESPONDER = "e2e_resp_responder"  # responder assegnato a E2E_RA
ANALYST = "e2e_resp_analyst"  # analyst assegnato a E2E_RA
LEGACY = "e2e_resp_legacy"  # analyst senza clienti, scritto direttamente nel DB
NEW_USER = "e2e_resp_new"  # creato via API dallo script
USERS = (ADMIN, RESPONDER, ANALYST, LEGACY, NEW_USER)

NOW = datetime.datetime(2026, 1, 1)
results = []


def check(name, passed, detail=""):
    results.append((name, passed, detail))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


async def cleanup(s: AsyncSession):
    for uname in USERS:
        u = (await s.execute(select(User).where(User.username == uname))).scalars().first()
        if u:
            await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id == u.id))
            await s.delete(u)
    await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.customer_code.in_([CUST_A, CUST_B])))
    await s.execute(delete(Agents).where(Agents.customer_code.in_([CUST_A, CUST_B])))
    await s.commit()
    await s.execute(delete(Customers).where(Customers.customer_code.in_([CUST_A, CUST_B])))
    await s.commit()


async def seed():
    auth = AuthHandler()
    async with AsyncSession(async_engine) as s:
        await cleanup(s)
        for code in (CUST_A, CUST_B):
            s.add(Customers(customer_code=code, customer_name=f"Customer {code}", customer_type="MSSP", logo_file=""))
        await s.commit()
        for i, (code, host) in enumerate(((CUST_A, HOST_A), (CUST_B, HOST_B)), start=1):
            s.add(
                Agents(
                    agent_id=f"e2er{i}",
                    ip_address=f"10.0.1.{i}",
                    os="Windows",
                    hostname=host,
                    label=host,
                    critical_asset=False,
                    customer_code=code,
                    quarantined=False,
                    velociraptor_id=f"C.e2e{i}",
                    velociraptor_org="root",
                    wazuh_last_seen=NOW,
                    velociraptor_last_seen=NOW,
                    wazuh_agent_version="4.x",
                    velociraptor_agent_version="0.7",
                ),
            )
        pw = auth.get_password_hash(PASSWORD)
        for uname, role_id in ((ADMIN, 1), (RESPONDER, 5), (ANALYST, 2), (LEGACY, 2)):
            s.add(User(username=uname, password=pw, email=f"{uname}@example.com", role_id=role_id))
        await s.commit()
        for uname in (RESPONDER, ANALYST):
            u = (await s.execute(select(User).where(User.username == uname))).scalars().one()
            s.add(UserCustomerAccess(user_id=u.id, customer_code=CUST_A))
        await s.commit()
    print(f"seed: {CUST_A}/{HOST_A}, {CUST_B}/{HOST_B}; responder e analyst su {CUST_A}; '{LEGACY}' senza clienti")


def build_app():
    from app.customers.routes.customers import customers_router
    from app.routers import active_response as active_response_routers
    from app.routers import auth as auth_routers
    from app.routers import copilot_action as copilot_action_routers
    from app.routers import velociraptor as velociraptor_routers

    api = APIRouter()
    api.include_router(auth_routers.router)
    api.include_router(customers_router, prefix="/customers")
    api.include_router(velociraptor_routers.router)
    api.include_router(copilot_action_routers.router)
    api.include_router(active_response_routers.router)
    app = FastAPI()
    app.include_router(api)
    app.add_exception_handler(HTTPException, custom_http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    return app


def reached():
    """Uno stub dopo il controllo di tenancy: se è chiamato, la richiesta è passata."""
    return AsyncMock(side_effect=HTTPException(status_code=418, detail="e2e stub reached"))


async def assigned(username):
    async with AsyncSession(async_engine) as s:
        u = (await s.execute(select(User).where(User.username == username))).scalars().first()
        if not u:
            return None
        rows = await s.execute(select(UserCustomerAccess.customer_code).where(UserCustomerAccess.user_id == u.id))
        return sorted(rows.scalars().all())


async def user_id(username):
    async with AsyncSession(async_engine) as s:
        return (await s.execute(select(User.id).where(User.username == username))).scalars().first()


async def audit_rows(action, actor, since_id):
    async with AsyncSession(async_engine) as s:
        rows = await s.execute(
            select(AuditLog).where(AuditLog.action == action, AuditLog.actor_username == actor, AuditLog.id > since_id),
        )
        return rows.scalars().all()


async def max_audit_id():
    async with AsyncSession(async_engine) as s:
        row = (await s.execute(select(AuditLog.id).order_by(AuditLog.id.desc()).limit(1))).scalars().first()
        return row or 0


async def main():
    await seed()
    app = build_app()
    transport = httpx.ASGITransport(app=app)
    auth = AuthHandler()
    tokens = {u: await auth.encode_token(u) for u in (ADMIN, RESPONDER, ANALYST, LEGACY)}

    def H(user):
        return {"Authorization": f"Bearer {tokens[user]}"}

    async with httpx.AsyncClient(transport=transport, base_url="http://e2e") as client:
        print("\n=== A) ruolo e token ===")
        async with AsyncSession(async_engine) as s:
            role = (await s.execute(select(Role).where(Role.id == 5))).scalars().first()
        check("ruolo 5 = responder (dalla migrazione)", bool(role) and role.name == "responder", str(role and role.name))
        scopes = jwt.decode(tokens[RESPONDER], options={"verify_signature": False}).get("scopes")
        check("token del responder: responder + analyst", scopes == ["responder", "analyst"], str(scopes))

        print("\n=== B) quarantena e comando ===")
        for path, body in (
            ("/artifacts/quarantine", {"action": "quarantine"}),
            ("/artifacts/command", {"command": "whoami", "artifact_name": "Windows.System.PowerShell"}),
        ):
            for user, host, expected, label in (
                (RESPONDER, HOST_A, "reached", "responder, host suo"),
                (RESPONDER, HOST_B, 403, "responder, host altrui"),
                (ANALYST, HOST_A, "denied", "analyst, host suo"),
                (ADMIN, HOST_B, "reached", "admin, qualunque host"),
            ):
                stub = reached()
                with patch.object(artifact_routes, "get_all_artifacts_for_hostname", new=stub):
                    r = await client.post(path, json={"hostname": host, **body}, headers=H(user))
                if expected == "reached":
                    ok = stub.called
                elif expected == "denied":
                    ok = r.status_code in (401, 403) and not stub.called
                else:
                    ok = r.status_code == expected and not stub.called
                check(f"{path}: {label}", ok, f"{r.status_code} stub={'chiamato' if stub.called else 'no'}")

        print("\n=== C) CoPilot Actions ===")
        since = await max_audit_id()
        for user, hosts, expected, label in (
            (RESPONDER, [HOST_A], "reached", "responder, host suo"),
            (RESPONDER, [HOST_A, HOST_B], 403, "responder, un host altrui rifiuta tutto"),
            (RESPONDER, [], 400, "responder, nessun host (mai un fan-out)"),
            (ANALYST, [HOST_A], "denied", "analyst"),
        ):
            stub = reached()
            with patch.object(action_routes, "get_agents_by_hostnames", new=stub):
                r = await client.post(
                    "/copilot_action/invoke",
                    json={"copilot_action_name": "e2e-action", "agent_names": hosts, "parameters": {}},
                    headers=H(user),
                )
            if expected == "reached":
                ok = stub.called
            elif expected == "denied":
                ok = r.status_code in (401, 403) and not stub.called
            else:
                ok = r.status_code == expected and not stub.called
            check(f"invoke: {label}", ok, f"{r.status_code} stub={'chiamato' if stub.called else 'no'}")
        rows = await audit_rows("response.copilot_action_invoke", RESPONDER, since)
        check("invoke del responder in audit (una riga, solo quella autorizzata)", len(rows) == 1, f"{len(rows)} righe")

        r = await client.get("/copilot_action/technologies", headers=H(RESPONDER))
        check("responder legge il catalogo (technologies)", r.status_code == 200, str(r.status_code))
        r = await client.get("/copilot_action/technologies", headers=H(ANALYST))
        check("analyst non legge il catalogo", r.status_code in (401, 403), str(r.status_code))

        print("\n=== D) Sysmon ===")
        since = await max_audit_id()
        for user, code, expected, label in (
            (RESPONDER, CUST_A, "reached", "responder, cliente suo"),
            (RESPONDER, CUST_B, 403, "responder, cliente altrui"),
            (ANALYST, CUST_A, "denied", "analyst"),
        ):
            stub = reached()
            with patch.object(sysmon_routes, "deploy_sysmon_config_to_worker", new=stub):
                r = await client.post(f"/sysmon_config/deploy/{code}", headers=H(user))
            if expected == "reached":
                ok = stub.called
            elif expected == "denied":
                ok = r.status_code in (401, 403) and not stub.called
            else:
                ok = r.status_code == expected and not stub.called
            check(f"deploy: {label}", ok, f"{r.status_code} stub={'chiamato' if stub.called else 'no'}")
        rows = await audit_rows("response.sysmon_deploy", RESPONDER, since)
        check("deploy del responder in audit", len(rows) == 1 and rows[0].customer_code == CUST_A, f"{len(rows)} righe")

        r = await client.post(
            "/sysmon_config/upload",
            data={"customer_code": CUST_A},
            files={"file": ("sysmon.xml", b"<Sysmon/>", "application/xml")},
            headers=H(RESPONDER),
        )
        check("upload Sysmon: responder respinto (resta admin)", r.status_code in (401, 403), str(r.status_code))

        print("\n=== E) analyst e responder hanno sempre un cliente ===")
        new = {"username": NEW_USER, "password": PASSWORD, "email": f"{NEW_USER}@example.com"}
        for role_id in (2, 5):
            r = await client.post("/auth/register", json={**new, "role_id": role_id}, headers=H(ADMIN))
            check(f"register ruolo {role_id} senza clienti -> 400", r.status_code == 400, f"{r.status_code} {r.text[:120]}")
        check("...e l'utente non esiste", await user_id(NEW_USER) is None)

        r = await client.post("/auth/register", json={**new, "role_id": 5, "customer_codes": ["E2E_NOPE"]}, headers=H(ADMIN))
        check("register con cliente inesistente -> 400", r.status_code == 400, f"{r.status_code} {r.text[:120]}")

        r = await client.post("/auth/register", json={**new, "role_id": 1, "customer_codes": [CUST_A]}, headers=H(ADMIN))
        check("register admin con clienti -> 400", r.status_code == 400, f"{r.status_code} {r.text[:120]}")

        r = await client.post("/auth/register", json={**new, "role_id": 5, "customer_codes": [CUST_A]}, headers=H(ADMIN))
        check("register responder con E2E_RA -> 201", r.status_code == 201, f"{r.status_code} {r.text[:120]}")
        check("...assegnato a E2E_RA", await assigned(NEW_USER) == [CUST_A], str(await assigned(NEW_USER)))

        new_id = await user_id(NEW_USER)
        r = await client.post(f"/auth/users/{new_id}/customers", json=[], headers=H(ADMIN))
        check("svuotare i clienti di un responder -> 400", r.status_code == 400, str(r.status_code))
        check("...e restano quelli di prima", await assigned(NEW_USER) == [CUST_A], str(await assigned(NEW_USER)))

        r = await client.put(
            f"/auth/users/{new_id}/role/by-name",
            json={"role_name": "analyst", "customer_codes": [CUST_B]},
            headers=H(ADMIN),
        )
        check("cambio ruolo a analyst con E2E_RB -> 200", r.status_code == 200, f"{r.status_code} {r.text[:120]}")
        check("...clienti sostituiti", await assigned(NEW_USER) == [CUST_B], str(await assigned(NEW_USER)))

        legacy_id = await user_id(LEGACY)
        r = await client.put(f"/auth/users/{legacy_id}/role/by-name", json={"role_name": "responder"}, headers=H(ADMIN))
        check("legacy senza clienti -> responder senza clienti: 400", r.status_code == 400, f"{r.status_code} {r.text[:120]}")
        async with AsyncSession(async_engine) as s:
            legacy_role = (await s.execute(select(User.role_id).where(User.id == legacy_id))).scalars().first()
        check("...e resta analyst", legacy_role == 2, str(legacy_role))

        admin_id = await user_id(ADMIN)
        r = await client.post(f"/auth/users/{admin_id}/customers", json=[CUST_A], headers=H(ADMIN))
        check("assegnare clienti a un admin -> 400", r.status_code == 400, str(r.status_code))

        r = await client.post(f"/auth/users/{admin_id}/customers", json=[CUST_A], headers=H(RESPONDER))
        check("il responder non assegna clienti", r.status_code in (401, 403), str(r.status_code))

        print("\n=== F) chi vede cosa ===")
        r = await client.get("/auth/me/customers", headers=H(LEGACY))
        body = r.json() if r.status_code == 200 else {}
        check(
            "legacy: /me/customers -> unassigned, nessun cliente",
            body.get("scope") == "unassigned" and not body.get("customer_codes"),
            str(body),
        )
        r = await client.get("/customers", headers=H(LEGACY))
        codes = {c["customer_code"] for c in r.json().get("customers", [])} if r.status_code == 200 else set()
        check("legacy: GET /customers non mostra nessun cliente", not codes & {CUST_A, CUST_B}, f"{r.status_code} {sorted(codes)}")
        r = await client.get(f"/customers/{CUST_A}", headers=H(LEGACY))
        check("legacy: GET /customers/E2E_RA -> 403", r.status_code == 403, str(r.status_code))

        r = await client.get("/auth/me/customers", headers=H(RESPONDER))
        body = r.json() if r.status_code == 200 else {}
        check(
            "responder: /me/customers -> assigned [E2E_RA]",
            body.get("scope") == "assigned" and body.get("customer_codes") == [CUST_A],
            str(body),
        )
        r = await client.get(f"/customers/{CUST_B}", headers=H(RESPONDER))
        check("responder: GET /customers/E2E_RB -> 403", r.status_code == 403, str(r.status_code))

        r = await client.get("/auth/me/customers", headers=H(ADMIN))
        body = r.json() if r.status_code == 200 else {}
        check("admin: /me/customers -> deployment", body.get("scope") == "deployment", str(body))

    async with AsyncSession(async_engine) as s:
        await cleanup(s)
    await async_engine.dispose()

    passed = sum(1 for _, p, _ in results if p)
    print(f"\n{'=' * 60}\nRISULTATO: {passed}/{len(results)} verifiche superate")
    failed = [(n, d) for n, p, d in results if not p]
    for n, d in failed:
        print(f"  FALLITA: {n} [{d}]")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
