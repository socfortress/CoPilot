"""E2E for #1166 (customer WAF) — NOT collected by pytest (needs a live MySQL); run by hand.

    docker run -d --name copilot-e2e-mysql -p 13306:3306 \
        -e MYSQL_ROOT_PASSWORD=e2eroot -e MYSQL_DATABASE=copilot \
        -e MYSQL_USER=copilot -e MYSQL_PASSWORD=e2epass mysql:8.0

    cd backend && export MYSQL_URL=127.0.0.1:13306 MYSQL_USER=copilot \
        MYSQL_PASSWORD=e2epass MYSQL_ROOT_PASSWORD=e2eroot \
        JWT_SECRET=e2e-test-secret-not-the-default PYTHONPATH=$PWD
    .venv/bin/python -c "from app.db.db_setup import apply_migrations; apply_migrations()"
    .venv/bin/python tests/e2e/customer_waf_e2e.py

Optionally point it at a real SOCFortress WAF to exercise the WAF-facing routes too
(without these, those checks are skipped and only config/tenancy/crypto run):

    export WAF_E2E_URL=http://127.0.0.1:18777 WAF_E2E_VIEWER_TOKEN=wafst_...

Targets a disposable instance on port 13306: never the MySQL from .env.

Real routers, real MySQL, real JWTs. What it proves that the unit tests can't: the
token is stored encrypted and never returned; a scoped analyst can reach neither
another tenant's customer path nor another tenant's WAF id under their own path;
configuration writes are admin-only; missing / rotated WAF_TOKEN_ENCRYPTION_KEY
behave as documented; and deleting a customer cascades to its WAFs.
"""
import asyncio
import os

os.environ.setdefault("MYSQL_URL", "127.0.0.1:13306")
os.environ.setdefault("MYSQL_USER", "copilot")
os.environ.setdefault("MYSQL_PASSWORD", "e2epass")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "e2eroot")
os.environ.setdefault("JWT_SECRET", "e2e-test-secret-not-the-default")

import httpx  # noqa: E402
from cryptography.fernet import Fernet  # noqa: E402
from fastapi import APIRouter  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.auth.models.users import Role  # noqa: E402
from app.auth.models.users import User  # noqa: E402
from app.auth.models.users import UserCustomerAccess  # noqa: E402
from app.auth.utils import AuthHandler  # noqa: E402
from app.customer_waf.services import crypto  # noqa: E402
from app.db.db_session import async_engine  # noqa: E402
from app.db.universal_models import Customers  # noqa: E402
from app.db.universal_models import CustomerWafInstance  # noqa: E402

assert "13306" in os.environ["MYSQL_URL"], "refusing to run against anything but the disposable e2e MySQL"

CUST_A, CUST_B = "E2E_WAF_A", "E2E_WAF_B"
SCOPED = "e2e_waf_scoped_analyst"  # assigned to CUST_A
ADMIN = "e2e_waf_admin"
PASSWORD = "E2ePassw0rd!x"

WAF_URL = os.environ.get("WAF_E2E_URL")
REAL_TOKEN = os.environ.get("WAF_E2E_VIEWER_TOKEN")
LIVE = bool(WAF_URL and REAL_TOKEN)
TOKEN = REAL_TOKEN or "wafst_" + "E" * 43
API_URL = WAF_URL or "http://127.0.0.1:1"  # unreachable when no live WAF

results = []


def check(name, passed, detail=""):
    results.append((name, passed))
    print(f"  {'PASS' if passed else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


async def _cleanup(s: AsyncSession):
    await s.execute(delete(CustomerWafInstance).where(CustomerWafInstance.customer_code.in_([CUST_A, CUST_B])))
    for uname in (SCOPED, ADMIN):
        u = (await s.execute(select(User).where(User.username == uname))).scalars().first()
        if u:
            await s.execute(delete(UserCustomerAccess).where(UserCustomerAccess.user_id == u.id))
            await s.delete(u)
    await s.commit()
    await s.execute(delete(Customers).where(Customers.customer_code.in_([CUST_A, CUST_B])))
    await s.commit()


async def seed():
    auth = AuthHandler()
    async with AsyncSession(async_engine) as s:
        for rid, rname in [(1, "admin"), (2, "analyst"), (3, "scheduler"), (4, "customer_user")]:
            if not (await s.execute(select(Role).where(Role.id == rid))).scalars().first():
                s.add(Role(id=rid, name=rname, description=rname))
        await s.commit()
        await _cleanup(s)
        for code in (CUST_A, CUST_B):
            s.add(
                Customers(
                    customer_code=code,
                    customer_name=f"{code} name",
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
        pw = auth.get_password_hash(PASSWORD)
        s.add(User(username=ADMIN, password=pw, email=f"{ADMIN}@e2e.example", role_id=1))
        s.add(User(username=SCOPED, password=pw, email=f"{SCOPED}@e2e.example", role_id=2))
        await s.commit()
        scoped = (await s.execute(select(User).where(User.username == SCOPED))).scalars().first()
        s.add(UserCustomerAccess(user_id=scoped.id, customer_code=CUST_A))
        await s.commit()
    print(f"seed: 2 tenants, analyst '{SCOPED}' assigned to {CUST_A}; live WAF: {WAF_URL if LIVE else 'no (WAF-facing checks skipped)'}")


async def stored_row(waf_id):
    async with AsyncSession(async_engine) as s:
        return await s.get(CustomerWafInstance, waf_id)


def build_app():
    from app.customer_waf.routes.customer_waf import customer_waf_router

    api = APIRouter()
    api.include_router(customer_waf_router, prefix="/customer_waf")
    app = FastAPI()
    app.include_router(api)
    return app


async def main():
    os.environ[crypto.KEY_ENV_VAR] = Fernet.generate_key().decode()
    await seed()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=build_app()), base_url="http://e2e") as c:
        auth = AuthHandler()
        H_ADMIN = {"Authorization": f"Bearer {await auth.encode_token(ADMIN)}"}
        H_SCOPED = {"Authorization": f"Bearer {await auth.encode_token(SCOPED)}"}
        body = {"name": "prod", "api_url": API_URL, "service_token": TOKEN, "verify_tls": True}

        print("\n=== 1) create: encrypted at rest, never returned ===")
        r = await c.post(f"/customer_waf/{CUST_A}", json=body, headers=H_ADMIN)
        check("admin POST -> 201", r.status_code == 201, str(r.status_code))
        id_a = r.json()["instance"]["id"]
        check("token absent from response", TOKEN not in r.text and "service_token" not in r.text)
        check("token_prefix shown", r.json()["instance"]["token_prefix"] == TOKEN[:12] + "...")
        row = await stored_row(id_a)
        check("stored as ciphertext", row.service_token_encrypted != TOKEN and TOKEN not in row.service_token_encrypted)
        check("ciphertext decrypts to the token", crypto.decrypt_token(row.service_token_encrypted) == TOKEN)
        v = r.json()["verification"]
        if LIVE:
            check("create ran verify", v and v["authenticated"] and "viewer" in v["waf_roles"], str(v and v.get("waf_roles")))
            check("role cached on row", row.last_verified_role == "viewer", str(row.last_verified_role))
        else:
            check("create saves even when WAF unreachable", r.json()["success"] and v and v["reason"] == "unreachable", str(v))
        check("http:// URL warned", any("clear text" in w for w in r.json()["warnings"]) == API_URL.startswith("http://"))

        r = await c.post(f"/customer_waf/{CUST_A}", json=body, headers=H_ADMIN)
        check("duplicate name -> 409", r.status_code == 409, str(r.status_code))
        r = await c.post(f"/customer_waf/{CUST_B}", json={**body, "name": "b-prod"}, headers=H_ADMIN)
        check("admin POST for B -> 201", r.status_code == 201, str(r.status_code))
        id_b = r.json()["instance"]["id"]
        r = await c.post(f"/customer_waf/{CUST_A}", json={**body, "name": "x", "service_token": "eyJhbGciOi.x.y"}, headers=H_ADMIN)
        check("non-wafst token -> 400", r.status_code == 400, str(r.status_code))

        print("\n=== 2) tenancy + admin-only writes ===")
        r = await c.post(f"/customer_waf/{CUST_A}", json={**body, "name": "analyst-made"}, headers=H_SCOPED)
        check("analyst POST (own customer) -> 403", r.status_code == 403, str(r.status_code))
        r = await c.put(f"/customer_waf/{CUST_A}/{id_a}", json={"enabled": False}, headers=H_SCOPED)
        check("analyst PUT -> 403", r.status_code == 403, str(r.status_code))
        r = await c.delete(f"/customer_waf/{CUST_A}/{id_a}", headers=H_SCOPED)
        check("analyst DELETE -> 403", r.status_code == 403, str(r.status_code))
        r = await c.get(f"/customer_waf/{CUST_A}", headers=H_SCOPED)
        check("analyst GET own list -> 200, 1 WAF", r.status_code == 200 and len(r.json()["instances"]) == 1, str(r.status_code))
        check("list carries no token", TOKEN not in r.text)
        r = await c.get(f"/customer_waf/{CUST_B}", headers=H_SCOPED)
        check("analyst GET other customer's list -> 403", r.status_code == 403, str(r.status_code))
        for path in ("sites", "events", "stats", "threat-intel"):
            r = await c.get(f"/customer_waf/{CUST_A}/{id_b}/{path}", headers=H_SCOPED)
            check(f"other tenant's WAF id under own path /{path} -> 404", r.status_code == 404, str(r.status_code))
        r = await c.post(f"/customer_waf/{CUST_A}/{id_b}/verify", headers=H_SCOPED)
        check("other tenant's WAF id verify -> 404", r.status_code == 404, str(r.status_code))
        r = await c.get(f"/customer_waf/{CUST_B}/{id_b}/events", headers=H_SCOPED)
        check("other tenant's path -> 403", r.status_code == 403, str(r.status_code))
        r = await c.put(f"/customer_waf/{CUST_A}/{id_b}", json={"enabled": False}, headers=H_ADMIN)
        check("admin PUT B's id under A's path -> 404", r.status_code == 404, str(r.status_code))

        print("\n=== 3) WAF-facing reads ===")
        if LIVE:
            for path in ("sites", "events", "stats", "threat-intel"):
                r = await c.get(f"/customer_waf/{CUST_A}/{id_a}/{path}", headers=H_SCOPED)
                check(f"analyst GET /{path} -> 200", r.status_code == 200, f"{r.status_code} {r.json().get('message')}")
            r = await c.post(f"/customer_waf/{CUST_A}/{id_a}/verify", headers=H_SCOPED)
            caps = r.json()["verification"]["capabilities"]
            check("verify -> viewer is read-only", r.status_code == 200 and caps["can_read"] and not caps["can_block"], str(caps))
        else:
            r = await c.get(f"/customer_waf/{CUST_A}/{id_a}/events", headers=H_SCOPED)
            check("unreachable WAF -> 502 unreachable (not 401)", r.status_code == 502 and r.json()["reason"] == "unreachable", r.text)

        print("\n=== 4) write-only token on update ===")
        before = (await stored_row(id_a)).service_token_encrypted
        r = await c.put(f"/customer_waf/{CUST_A}/{id_a}", json={"service_token": "", "enabled": False}, headers=H_ADMIN)
        after = (await stored_row(id_a)).service_token_encrypted
        check("blank token keeps stored ciphertext", r.status_code == 200 and before == after, str(r.status_code))
        r = await c.get(f"/customer_waf/{CUST_A}/{id_a}/events", headers=H_SCOPED)
        check("disabled WAF -> 409 disabled", r.status_code == 409 and r.json()["reason"] == "disabled", str(r.status_code))
        r = await c.put(f"/customer_waf/{CUST_A}/{id_a}", json={"service_token": "wafst_" + "Z" * 43, "enabled": True}, headers=H_ADMIN)
        check(
            "new token saved even though it fails verify",
            r.status_code == 200 and r.json()["instance"]["token_prefix"] == "wafst_ZZZZZZ...",
        )
        if LIVE:
            check("  verify reported token_rejected", r.json()["verification"]["reason"] == "token_rejected", str(r.json()["verification"]))
            r = await c.get(f"/customer_waf/{CUST_A}/{id_a}/events", headers=H_SCOPED)
            check(
                "rejected token -> 502 token_rejected (never 401)",
                r.status_code == 502 and r.json()["reason"] == "token_rejected",
                str(r.status_code),
            )
        await c.put(f"/customer_waf/{CUST_A}/{id_a}", json={"service_token": TOKEN}, headers=H_ADMIN)

        print("\n=== 5) encryption key ===")
        key = os.environ[crypto.KEY_ENV_VAR]
        os.environ[crypto.KEY_ENV_VAR] = ""
        r = await c.post(f"/customer_waf/{CUST_A}", json={**body, "name": "no-key"}, headers=H_ADMIN)
        check("missing key -> 400 naming the variable", r.status_code == 400 and crypto.KEY_ENV_VAR in r.text, str(r.status_code))
        r = await c.get(f"/customer_waf/{CUST_A}", headers=H_ADMIN)
        check("list reports key not configured", r.json()["encryption_key_configured"] is False)
        os.environ[crypto.KEY_ENV_VAR] = Fernet.generate_key().decode()
        r = await c.get(f"/customer_waf/{CUST_A}/{id_a}/events", headers=H_SCOPED)
        check("rotated key -> 409 token_crypto 're-enter'", r.status_code == 409 and "Re-enter" in r.text, str(r.status_code))
        os.environ[crypto.KEY_ENV_VAR] = key

        print("\n=== 6) delete + cascade ===")
        r = await c.delete(f"/customer_waf/{CUST_A}/{id_a}", headers=H_ADMIN)
        check("admin DELETE -> 200, reminds to revoke", r.status_code == 200 and "revoke" in r.text.lower(), str(r.status_code))
        check("row gone", await stored_row(id_a) is None)
        async with AsyncSession(async_engine) as s:
            await s.execute(delete(Customers).where(Customers.customer_code == CUST_B))
            await s.commit()
        check("deleting customer B cascades its WAF", await stored_row(id_b) is None)

    async with AsyncSession(async_engine) as s:
        await _cleanup(s)
    await async_engine.dispose()
    failed = [n for n, p in results if not p]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed" + (f" — FAILED: {failed}" if failed else ""))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
